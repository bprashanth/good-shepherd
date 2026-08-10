"""Formidable HTTP API — runs in Lambda behind Lambda Web Adapter.

Routes:
  GET  /vision/health
  POST /vision/extract          — submit a form (file + optional name), returns 202 + job_id
  GET  /api/jobs                — list authenticated user's jobs (DynamoDB)
  GET  /api/jobs/{id}/status    — poll job status (DynamoDB)
  GET  /api/jobs/{id}/manifest  — crops_manifest.json (S3, ownership-checked)
  GET  /api/jobs/{id}/pages/{f} — page PNG (S3, ownership-checked)
  GET  /api/jobs/{id}/crops/{f} — crop PNG (S3, ownership-checked)
  GET  /api/jobs/{id}/xlsx      — excel download (corrected if exists, else output)
  POST /api/jobs/{id}/submit    — store corrections + write corrected.xlsx
  POST /api/jobs/{id}/rerun     — reset failed job and re-launch Fargate
  GET  /api/jobs/{id}/progress  — structured progress update (step, pct, ts)
  DELETE /api/jobs/{id}         — delete job (S3 artifacts + DynamoDB record)
"""

import io
import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
from fastapi import Body, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse

JOBS_BUCKET  = os.environ.get("JOBS_BUCKET",  "formidable-storage")
S3_PREFIX    = os.environ.get("S3_PREFIX",     "formidable")
DYNAMO_TABLE = os.environ.get("DYNAMO_TABLE",  "formidable-jobs")
ECS_CLUSTER  = os.environ.get("ECS_CLUSTER",   "form-idable-agents")
FARGATE_TASK = os.environ.get("FARGATE_TASK",  "formidable-worker")
FARGATE_TASK_HIGH = os.environ.get("FARGATE_TASK_HIGH", "formidable-high-worker")
ECS_SG_NAME  = os.environ.get("ECS_SG_NAME",   "form-idable-agents-sg")
AWS_REGION   = os.environ.get("AWS_REGION",    "ap-south-1")
ECS_SUBNET   = os.environ.get("ECS_SUBNET",    "")

app = FastAPI(title="Formidable API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── AWS clients (module-level, reused across Lambda warm invocations) ──────────
_s3_client     = None
_dynamo_client = None
_ecs_client    = None
_ec2_client    = None
_sg_id_cache   = None


def _s3():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3", region_name=AWS_REGION)
    return _s3_client


def _dynamo():
    global _dynamo_client
    if _dynamo_client is None:
        _dynamo_client = boto3.client("dynamodb", region_name=AWS_REGION)
    return _dynamo_client


def _ecs():
    global _ecs_client
    if _ecs_client is None:
        _ecs_client = boto3.client("ecs", region_name=AWS_REGION)
    return _ecs_client


def _ec2():
    global _ec2_client
    if _ec2_client is None:
        _ec2_client = boto3.client("ec2", region_name=AWS_REGION)
    return _ec2_client


# ── Auth helpers ───────────────────────────────────────────────────────────────

def _get_user_context(request: Request) -> tuple[str, str]:
    """Return (user_id, email) from the Cognito JWT claims in the request context."""
    ctx_raw = request.headers.get("x-amzn-request-context", "")
    if ctx_raw:
        try:
            claims = (
                json.loads(ctx_raw)
                    .get("authorizer", {})
                    .get("jwt", {})
                    .get("claims", {})
            )
            uid   = claims.get("sub", "")
            email = claims.get("email", "")
            if uid:
                return uid, email
        except Exception:
            pass
    return os.environ.get("DEV_USER_ID", "dev-user"), ""


def _get_user_id(request: Request) -> str:
    return _get_user_context(request)[0]


# ── S3 / DynamoDB helpers ──────────────────────────────────────────────────────

def _job_key(job_id: str, suffix: str) -> str:
    return f"{S3_PREFIX}/jobs/{job_id}/{suffix}"


def _s3_get(key: str) -> bytes:
    try:
        obj = _s3().get_object(Bucket=JOBS_BUCKET, Key=key)
        return obj["Body"].read()
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("NoSuchKey", "404"):
            raise HTTPException(404, f"not found: {key}")
        raise HTTPException(500, str(e))


def _check_ownership(user_id: str, job_id: str) -> dict:
    """Fetch DynamoDB item; raise 403 if not found (wrong user or unknown job)."""
    resp = _dynamo().get_item(
        TableName=DYNAMO_TABLE,
        Key={"user_id": {"S": user_id}, "job_id": {"S": job_id}},
    )
    item = resp.get("Item")
    if not item:
        raise HTTPException(403, "job not found or access denied")
    return item


def _item_to_job(item: dict) -> dict:
    def _s(k):  return item.get(k, {}).get("S") or None
    def _n(k):  return int(item.get(k, {}).get("N") or 0)
    def _l(k):
        v = item.get(k, {}).get("L", [])
        return [float(x.get("N", 0)) for x in v] if v else None
    def _m(k):
        v = item.get(k, {}).get("M", {})
        return {kk: vv.get("S", "") for kk, vv in v.items()} if v else {}

    return {
        "job_id":       _s("job_id"),
        "name":         _s("name") or "untitled",
        "status":       _s("status") or "queued",
        "review_state": _s("review_state") or "unreviewed",
        "effort":       _s("effort") or "low",
        "pages":        _n("pages"),
        "crops":        _n("crops"),
        "gps":          _l("gps"),
        "grid_no":      _s("grid_no"),
        "date":         _s("date"),
        "created_at":   _s("created_at"),
        "error":        _s("error"),
        "corrections":  _m("corrections"),
    }


# ── Fargate launch ─────────────────────────────────────────────────────────────

def _sg_id() -> str:
    global _sg_id_cache
    if _sg_id_cache is None:
        resp = _ec2().describe_security_groups(
            Filters=[{"Name": "group-name", "Values": [ECS_SG_NAME]}]
        )
        _sg_id_cache = resp["SecurityGroups"][0]["GroupId"]
    return _sg_id_cache


def _get_subnet() -> str:
    if ECS_SUBNET:
        return ECS_SUBNET
    # Discover first subnet in the default VPC
    vpcs = _ec2().describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])
    vpc_id = vpcs["Vpcs"][0]["VpcId"]
    subnets = _ec2().describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])
    return subnets["Subnets"][0]["SubnetId"]


def _launch_fargate(job_id: str, input_key: str, filename: str, user_id: str,
                    notification_email: str = "", effort: str = "low"):
    env = [
        {"name": "JOB_ID",     "value": job_id},
        {"name": "INPUT_KEY",  "value": input_key},
        {"name": "FILENAME",   "value": filename},
        {"name": "USER_ID",    "value": user_id},
    ]
    if notification_email:
        env.append({"name": "NOTIFICATION_EMAIL", "value": notification_email})
    task_definition = FARGATE_TASK_HIGH if effort == "high" else FARGATE_TASK
    container_name = "high-worker" if effort == "high" else "worker"
    return _ecs().run_task(
        cluster=ECS_CLUSTER,
        taskDefinition=task_definition,
        launchType="FARGATE",
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets":        [_get_subnet()],
                "securityGroups": [_sg_id()],
                "assignPublicIp": "ENABLED",
            }
        },
        overrides={"containerOverrides": [{"name": container_name, "environment": env}]},
    )


# ── Corrections / xlsx ─────────────────────────────────────────────────────────

def _apply_corrections(job_id: str, corrections: dict):
    """Apply user corrections to output.xlsx and upload as corrected.xlsx."""
    import openpyxl
    xlsx_bytes = _s3_get(_job_key(job_id, "output.xlsx"))
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb.active
    for key, value in corrections.items():
        try:
            parts = key.split(":")
            if len(parts) == 3:
                page_str, row_str, col_str = parts
                ws = wb.worksheets[max(0, int(page_str) - 1)]
            else:
                row_str, col_str = parts
                ws = wb.active
            # rowNum is 1-indexed xlsx row; colIdx is 0-indexed (SheetJS XLSX.utils.decode_cell)
            ws.cell(row=int(row_str), column=int(col_str) + 1).value = value
        except Exception:
            pass
    buf = io.BytesIO()
    wb.save(buf)
    _s3().put_object(
        Bucket=JOBS_BUCKET,
        Key=_job_key(job_id, "corrected.xlsx"),
        Body=buf.getvalue(),
    )


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/vision/health")
def health():
    return {"status": "ok"}


@app.post("/vision/extract", status_code=202)
async def extract(request: Request, body: dict = Body(...)):
    """Step 1: create the job record and return a presigned S3 URL for direct upload.
    The client uploads the file to upload_url, then calls POST /api/jobs/{job_id}/start."""
    user_id, cognito_email = _get_user_context(request)
    filename           = body.get("filename", "input.pdf")
    display            = body.get("name") or filename
    notification_email = body.get("notification_email", "")
    effort             = str(body.get("effort") or "low").strip().casefold()
    if effort not in {"low", "high"}:
        raise HTTPException(400, "effort must be 'low' or 'high'")

    job_id    = str(uuid.uuid4())
    ext       = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ".pdf"
    input_key = _job_key(job_id, f"input{ext}")

    upload_url = _s3().generate_presigned_url(
        "put_object",
        Params={"Bucket": JOBS_BUCKET, "Key": input_key, "ContentType": "application/octet-stream"},
        ExpiresIn=300,
    )

    now  = datetime.now(timezone.utc).isoformat()
    item = {
        "user_id":      {"S": user_id},
        "job_id":       {"S": job_id},
        "name":         {"S": display},
        "status":       {"S": "uploading"},
        "review_state": {"S": "unreviewed"},
        "effort":       {"S": effort},
        "created_at":   {"S": now},
        "pages":        {"N": "0"},
        "crops":        {"N": "0"},
        "input_key":    {"S": input_key},
    }
    if cognito_email:
        item["email"] = {"S": cognito_email}
    if notification_email:
        item["notification_email"] = {"S": notification_email}
    _dynamo().put_item(TableName=DYNAMO_TABLE, Item=item)

    return JSONResponse({"job_id": job_id, "upload_url": upload_url, "status": "uploading"}, status_code=202)


@app.post("/api/jobs/{job_id}/start")
def start_job(job_id: str, request: Request):
    """Step 3: called after client uploads to S3. Checks S3 first — if file missing,
    returns {needs_upload, upload_url} so the client can re-upload (crash recovery)."""
    user_id = _get_user_id(request)
    item    = _check_ownership(user_id, job_id)
    input_key = item.get("input_key", {}).get("S", "")
    filename  = item.get("name", {}).get("S", "input.pdf")
    if not input_key:
        raise HTTPException(400, "input_key missing — upload may not have completed")

    try:
        _s3().head_object(Bucket=JOBS_BUCKET, Key=input_key)
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
            upload_url = _s3().generate_presigned_url(
                "put_object",
                Params={"Bucket": JOBS_BUCKET, "Key": input_key, "ContentType": "application/octet-stream"},
                ExpiresIn=300,
            )
            return JSONResponse({"needs_upload": True, "upload_url": upload_url})
        raise HTTPException(500, str(e))

    _dynamo().update_item(
        TableName=DYNAMO_TABLE,
        Key={"user_id": {"S": user_id}, "job_id": {"S": job_id}},
        UpdateExpression="SET #st = :s",
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={":s": {"S": "queued"}},
    )
    notification_email = item.get("notification_email", {}).get("S", "")
    effort = item.get("effort", {}).get("S", "low")
    _launch_fargate(job_id, input_key, filename, user_id, notification_email, effort)
    task_family = FARGATE_TASK_HIGH if effort == "high" else FARGATE_TASK
    return {"status": "queued", "effort": effort, "task_family": task_family}


@app.get("/api/jobs")
def list_jobs(request: Request):
    user_id = _get_user_id(request)
    resp = _dynamo().query(
        TableName=DYNAMO_TABLE,
        KeyConditionExpression="user_id = :uid",
        ExpressionAttributeValues={":uid": {"S": user_id}},
    )
    jobs = [_item_to_job(item) for item in resp.get("Items", [])]
    # The table sort key is job_id (a random UUID), so DynamoDB's own ordering is
    # arbitrary. Order by submission time instead — created_at is ISO8601, so a
    # lexicographic sort is chronological. Newest first.
    jobs.sort(key=lambda j: j.get("created_at") or "", reverse=True)
    return jobs


@app.get("/api/jobs/{job_id}/status")
def get_status(job_id: str, request: Request):
    user_id = _get_user_id(request)
    item    = _check_ownership(user_id, job_id)
    j       = _item_to_job(item)
    return {"status": j["status"], "pages": j["pages"], "crops": j["crops"],
            "error": j["error"], "effort": j["effort"]}


def _high_artifact(job_id: str, request: Request, filename: str):
    user_id = _get_user_id(request)
    item = _check_ownership(user_id, job_id)
    if item.get("effort", {}).get("S", "low") != "high":
        raise HTTPException(404, "artifact is available only for high-effort jobs")
    return JSONResponse(json.loads(_s3_get(_job_key(job_id, filename))))


@app.get("/api/jobs/{job_id}/review-manifest")
def get_review_manifest(job_id: str, request: Request):
    return _high_artifact(job_id, request, "review_manifest.json")


@app.get("/api/jobs/{job_id}/analytics")
def get_analytics(job_id: str, request: Request):
    return _high_artifact(job_id, request, "analytics.json")


@app.get("/api/jobs/{job_id}/manifest")
def get_manifest(job_id: str, request: Request):
    user_id = _get_user_id(request)
    _check_ownership(user_id, job_id)
    data = _s3_get(_job_key(job_id, "crops_manifest.json"))
    return JSONResponse(json.loads(data))


@app.get("/api/jobs/{job_id}/pages/{filename}")
def get_page(job_id: str, filename: str, request: Request):
    """Return a short-lived presigned S3 GET URL — avoids streaming large PNGs through Lambda."""
    user_id = _get_user_id(request)
    _check_ownership(user_id, job_id)
    url = _s3().generate_presigned_url(
        "get_object",
        Params={"Bucket": JOBS_BUCKET, "Key": _job_key(job_id, f"pages/{filename}")},
        ExpiresIn=300,
    )
    return {"url": url}


@app.get("/api/jobs/{job_id}/crops/{filename}")
def get_crop(job_id: str, filename: str, request: Request):
    user_id = _get_user_id(request)
    _check_ownership(user_id, job_id)
    url = _s3().generate_presigned_url(
        "get_object",
        Params={"Bucket": JOBS_BUCKET, "Key": _job_key(job_id, f"crops/{filename}")},
        ExpiresIn=300,
    )
    return {"url": url}


@app.get("/api/jobs/{job_id}/xlsx")
def get_xlsx(job_id: str, request: Request):
    user_id = _get_user_id(request)
    item    = _check_ownership(user_id, job_id)
    display = item.get("name", {}).get("S", "output")
    safe_name = display.rsplit(".", 1)[0] + ".xlsx"
    for suffix in ("corrected.xlsx", "output.xlsx"):
        key = _job_key(job_id, suffix)
        try:
            _s3().head_object(Bucket=JOBS_BUCKET, Key=key)
        except ClientError:
            continue
        url = _s3().generate_presigned_url(
            "get_object",
            Params={
                "Bucket": JOBS_BUCKET,
                "Key": key,
                "ResponseContentDisposition": f'attachment; filename="{safe_name}"',
            },
            ExpiresIn=300,
        )
        return {"url": url, "filename": safe_name}
    raise HTTPException(404, "xlsx not found")


@app.post("/api/jobs/{job_id}/submit")
async def submit_review(job_id: str, request: Request):
    user_id = _get_user_id(request)
    _check_ownership(user_id, job_id)
    body        = await request.json()
    corrections = body.get("corrections", {})

    corrections_dynamo = {k: {"S": v} for k, v in corrections.items()}
    _dynamo().update_item(
        TableName=DYNAMO_TABLE,
        Key={"user_id": {"S": user_id}, "job_id": {"S": job_id}},
        UpdateExpression="SET review_state = :rs, corrections = :c",
        ExpressionAttributeValues={
            ":rs": {"S": "reviewed"},
            ":c":  {"M": corrections_dynamo},
        },
    )

    if corrections:
        _apply_corrections(job_id, corrections)

    return {"status": "reviewed"}


@app.post("/api/jobs/{job_id}/rerun")
async def rerun_job(job_id: str, request: Request):
    """Rerun = create a NEW job from the source job's input PDF, leaving the
    original untouched (it may be terminal — complete/failed). The user can
    delete the old job if they no longer want it."""
    user_id, cognito_email = _get_user_context(request)
    item = _check_ownership(user_id, job_id)

    name          = item.get("name", {}).get("S", "input.pdf")
    src_input_key = item.get("input_key", {}).get("S", "")
    if not src_input_key:
        # Legacy jobs predate input_key — reconstruct from the display name's ext.
        ext = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ".pdf"
        src_input_key = _job_key(job_id, f"input{ext}")
    ext = ("." + src_input_key.rsplit(".", 1)[-1]) if "." in src_input_key else ".pdf"

    new_job_id    = str(uuid.uuid4())
    new_input_key = _job_key(new_job_id, f"input{ext}")

    # Copy the source input into the new job's prefix (server-side S3 copy).
    _s3().copy_object(
        Bucket=JOBS_BUCKET,
        CopySource={"Bucket": JOBS_BUCKET, "Key": src_input_key},
        Key=new_input_key,
    )

    now  = datetime.now(timezone.utc).isoformat()
    new_item = {
        "user_id":      {"S": user_id},
        "job_id":       {"S": new_job_id},
        "name":         {"S": name},
        "status":       {"S": "queued"},
        "review_state": {"S": "unreviewed"},
        "effort":       {"S": item.get("effort", {}).get("S", "low")},
        "created_at":   {"S": now},
        "pages":        {"N": "0"},
        "crops":        {"N": "0"},
        "input_key":    {"S": new_input_key},
    }
    if cognito_email:
        new_item["email"] = {"S": cognito_email}
    notification_email = item.get("notification_email", {}).get("S", "")
    if notification_email:
        new_item["notification_email"] = {"S": notification_email}
    _dynamo().put_item(TableName=DYNAMO_TABLE, Item=new_item)

    effort = new_item["effort"]["S"]
    _launch_fargate(new_job_id, new_input_key, name, user_id, notification_email, effort)
    return JSONResponse({"job_id": new_job_id, "status": "queued"}, status_code=202)


@app.get("/api/jobs/{job_id}/progress")
def get_progress(job_id: str, request: Request):
    user_id = _get_user_id(request)
    _check_ownership(user_id, job_id)
    try:
        data = _s3_get(_job_key(job_id, "progress.json"))
        return JSONResponse(json.loads(data))
    except HTTPException:
        # No progress file yet — job is queued and hasn't started Fargate
        return JSONResponse({"step": "Queued, waiting to start…", "pct": 0, "ts": None})


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str, request: Request):
    user_id = _get_user_id(request)
    _check_ownership(user_id, job_id)

    # Delete all S3 artifacts under the job prefix
    prefix = _job_key(job_id, "")
    paginator = _s3().get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=JOBS_BUCKET, Prefix=prefix):
        objects = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
        if objects:
            _s3().delete_objects(Bucket=JOBS_BUCKET, Delete={"Objects": objects})

    _dynamo().delete_item(
        TableName=DYNAMO_TABLE,
        Key={"user_id": {"S": user_id}, "job_id": {"S": job_id}},
    )
    return {"status": "deleted"}


@app.get("/vision/jobs/{job_id}")
def get_vision_job(job_id: str, request: Request):
    """Legacy polling endpoint kept for run_fargate.sh compatibility."""
    user_id = _get_user_id(request)
    try:
        item = _check_ownership(user_id, job_id)
    except HTTPException:
        raise HTTPException(404, "job not found")
    j = _item_to_job(item)
    if j["status"] == "complete":
        try:
            data = _s3_get(_job_key(job_id, "corrected.xlsx"))
        except HTTPException:
            data = _s3_get(_job_key(job_id, "output.xlsx"))
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={job_id}.xlsx"},
        )
    if j["status"] == "failed":
        return JSONResponse({"status": "failed", "error": j.get("error", "")}, status_code=500)
    return JSONResponse({"status": j["status"]}, status_code=202)
