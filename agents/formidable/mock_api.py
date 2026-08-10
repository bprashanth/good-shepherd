"""Local mock API for the review UX. Serves job data from S3.

Run:
  cd good-shepherd/agents/formidable
  uvicorn mock_api:app --port 8072 --reload

Vite dev server proxies /api and /vision → localhost:8072.
"""

import copy
import json
import uuid

import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

OLD_BUCKET = "form-idable-jobs-024848460644"
NEW_BUCKET = "formidable-storage"
NEW_PREFIX = "formidable"

REGION = "ap-south-1"
s3 = boto3.client("s3", region_name=REGION)

OLD_JOB_IDS = {
    "5092d717-0aab-4ac8-8c8d-029318822b28",
    "40b7dfee-6763-43b8-aac2-0d31c12a3f94",
}

_INITIAL_JOBS = [
    {
        "job_id":       "5092d717-0aab-4ac8-8c8d-029318822b28",
        "name":         "GridVegetation_100mx100m.pdf",
        "status":       "complete",
        "review_state": "unreviewed",
        "effort":       "low",
        "pages":        3,
        "crops":        6,
        "gps":          [10.31490, 76.83122],
        "grid_no":      "M15",
        "date":         "28.4.2016",
        "created_at":   "2026-06-01T00:00:00Z",
        "error":        None,
        "corrections":  {},
    },
    {
        "job_id":       "40b7dfee-6763-43b8-aac2-0d31c12a3f94",
        "name":         "LeafLitterBiomass.pdf",
        "status":       "complete",
        "review_state": "unreviewed",
        "effort":       "low",
        "pages":        4,
        "crops":        11,
        "gps":          [10.3210, 76.8045],
        "grid_no":      None,
        "date":         None,
        "created_at":   "2026-06-02T00:00:00Z",
        "error":        None,
        "corrections":  {},
    },
    {
        "job_id":       "dc2de090-c3e8-472f-be0e-924e581010ea",
        "name":         "RegenerationPlot5mx5m.pdf",
        "status":       "complete",
        "review_state": "unreviewed",
        "effort":       "high",
        "pages":        3,
        "crops":        12,
        "gps":          [10.30217, 76.84301],
        "grid_no":      "A01",
        "date":         "15/10/18",
        "created_at":   "2026-06-17T15:00:00Z",
        "error":        None,
        "corrections":  {},
    },
    {
        "job_id":       "1df20100-7a1b-476e-a123-97ae0ff1b63f",
        "name":         "TreePlots20mx20m.pdf",
        "status":       "complete",
        "review_state": "unreviewed",
        "effort":       "low",
        "pages":        3,
        "crops":        9,
        "gps":          [10.30217, 76.84301],
        "grid_no":      "A01",
        "date":         "15/10/18",
        "created_at":   "2026-06-17T15:05:00Z",
        "error":        None,
        "corrections":  {},
    },
    {
        "job_id":       "661e2210-d7b2-4116-98bf-83f687fe385e",
        "name":         "SaplingSurvivalMonitoring.pdf",
        "status":       "complete",
        "review_state": "unreviewed",
        "effort":       "low",
        "pages":        2,
        "crops":        12,
        "gps":          None,
        "grid_no":      "Matha Junction",
        "date":         None,
        "created_at":   "2026-06-17T15:10:00Z",
        "error":        None,
        "corrections":  {},
    },
]

MOCK_JOBS: list = copy.deepcopy(_INITIAL_JOBS)


def _s3_key(job_id: str, suffix: str) -> tuple[str, str]:
    if job_id in OLD_JOB_IDS:
        return OLD_BUCKET, f"jobs/{job_id}/{suffix}"
    return NEW_BUCKET, f"{NEW_PREFIX}/jobs/{job_id}/{suffix}"


def _s3_get(job_id: str, suffix: str) -> bytes:
    bucket, key = _s3_key(job_id, suffix)
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        return obj["Body"].read()
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            raise HTTPException(404, f"not found: s3://{bucket}/{key}")
        raise HTTPException(500, str(e))


# ── Dev reset (used by Playwright beforeEach) ──────────────────────────────────

@app.get("/api/dev/reset")
def dev_reset():
    global MOCK_JOBS
    MOCK_JOBS = copy.deepcopy(_INITIAL_JOBS)
    return {"status": "reset", "count": len(MOCK_JOBS)}


# ── Job CRUD ───────────────────────────────────────────────────────────────────

@app.get("/api/jobs")
def list_jobs():
    return MOCK_JOBS


@app.get("/api/jobs/{job_id}/status")
def get_status(job_id: str):
    job = next((j for j in MOCK_JOBS if j["job_id"] == job_id), None)
    if not job:
        raise HTTPException(404, "job not found")
    return {"status": job["status"], "pages": job["pages"], "crops": job["crops"],
            "error": job["error"], "effort": job.get("effort", "low")}


@app.get("/api/jobs/{job_id}/progress")
def get_progress(job_id: str):
    job = next((j for j in MOCK_JOBS if j["job_id"] == job_id), None)
    if not job:
        raise HTTPException(404, "job not found")
    status = job["status"]
    if status == "complete":
        return {"step": "Complete", "pct": 100, "ts": None}
    if status == "failed":
        return {"step": "Failed", "pct": 0, "ts": None}
    # queued or processing — return a fixed mock progress
    return {"step": "Analysing form (this takes a few minutes)", "pct": 20, "ts": None}


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str):
    job = next((j for j in MOCK_JOBS if j["job_id"] == job_id), None)
    if not job:
        raise HTTPException(404, "job not found")
    MOCK_JOBS[:] = [j for j in MOCK_JOBS if j["job_id"] != job_id]
    return {"status": "deleted"}


# ── Artifact proxies ───────────────────────────────────────────────────────────

@app.get("/api/jobs/{job_id}/manifest")
def get_manifest(job_id: str):
    data = _s3_get(job_id, "crops_manifest.json")
    return JSONResponse(json.loads(data))


def _high_artifact(job_id: str, suffix: str):
    job = next((j for j in MOCK_JOBS if j["job_id"] == job_id), None)
    if not job or job.get("effort", "low") != "high":
        raise HTTPException(404, "artifact is available only for high-effort jobs")
    return JSONResponse(json.loads(_s3_get(job_id, suffix)))


@app.get("/api/jobs/{job_id}/review-manifest")
def get_review_manifest(job_id: str):
    return _high_artifact(job_id, "review_manifest.json")


@app.get("/api/jobs/{job_id}/analytics")
def get_analytics(job_id: str):
    return _high_artifact(job_id, "analytics.json")


@app.get("/api/jobs/{job_id}/pages/{filename}")
def get_page(job_id: str, filename: str):
    bucket, key = _s3_key(job_id, f"pages/{filename}")
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=300,
    )
    return {"url": url}


@app.get("/api/jobs/{job_id}/crops/{filename}")
def get_crop(job_id: str, filename: str):
    bucket, key = _s3_key(job_id, f"crops/{filename}")
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=300,
    )
    return {"url": url}


@app.get("/api/jobs/{job_id}/xlsx")
def get_xlsx(job_id: str):
    job  = next((j for j in MOCK_JOBS if j["job_id"] == job_id), {})
    name = job.get("name", "output").rsplit(".", 1)[0] + ".xlsx"
    for suffix in ("corrected.xlsx", "output.xlsx"):
        bucket, key = _s3_key(job_id, suffix)
        try:
            s3.head_object(Bucket=bucket, Key=key)
        except ClientError:
            continue
        url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": bucket,
                "Key": key,
                "ResponseContentDisposition": f'attachment; filename="{name}"',
            },
            ExpiresIn=300,
        )
        return {"url": url, "filename": name}
    raise HTTPException(404, "xlsx not found")


@app.post("/api/jobs/{job_id}/submit")
async def submit_review(job_id: str, request: Request):
    job = next((j for j in MOCK_JOBS if j["job_id"] == job_id), None)
    if not job:
        raise HTTPException(404, "job not found")
    body = await request.json()
    job["review_state"] = "reviewed"
    job["corrections"] = body.get("corrections", {})
    return {"status": "reviewed"}


# ── Form submission ────────────────────────────────────────────────────────────

@app.post("/vision/extract", status_code=202)
async def extract(body: dict):
    job_id  = str(uuid.uuid4())
    display = body.get("name") or body.get("filename") or "upload.pdf"
    effort = str(body.get("effort") or "low").casefold()
    if effort not in {"low", "high"}:
        raise HTTPException(400, "effort must be 'low' or 'high'")
    new_job = {
        "job_id":       job_id,
        "name":         display,
        "status":       "uploading",
        "review_state": "unreviewed",
        "effort":       effort,
        "pages":        0,
        "crops":        0,
        "gps":          None,
        "grid_no":      None,
        "date":         None,
        "created_at":   "2026-06-18T00:00:00Z",
        "error":        None,
        "corrections":  {},
    }
    MOCK_JOBS.insert(0, new_job)
    # Return a mock upload URL pointing back at this server
    upload_url = f"http://localhost:8072/mock/upload/{job_id}"
    return JSONResponse({"job_id": job_id, "upload_url": upload_url, "status": "uploading"}, status_code=202)


@app.put("/mock/upload/{job_id}", status_code=200)
async def mock_upload(job_id: str, request: Request):
    await request.body()  # drain the body
    return {"ok": True}


@app.post("/api/jobs/{job_id}/start")
def start_job(job_id: str):
    job = next((j for j in MOCK_JOBS if j["job_id"] == job_id), None)
    if not job:
        raise HTTPException(404, "job not found")
    job["status"] = "queued"
    return {"status": "queued", "effort": job.get("effort", "low")}
