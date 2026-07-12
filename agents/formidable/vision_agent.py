"""HTTP-layer logic: save input to S3 and invoke the worker Lambda async.

The actual codex execution happens in worker.py (a separate Lambda function).
This module is loaded by main.py (FastAPI), which runs behind the Lambda Web
Adapter. All it does is:
  1. Upload the file to S3 with a fresh job_id.
  2. Invoke form-idable-vision-worker asynchronously (InvocationType=Event).
  3. Return the job_id so the caller can poll GET /vision/jobs/{job_id}.
"""

import json
import os
import uuid
from pathlib import Path

import boto3

JOBS_BUCKET     = os.environ.get("JOBS_BUCKET", "")
WORKER_FUNCTION = os.environ.get("WORKER_FUNCTION", "form-idable-vision-worker")
AWS_REGION      = os.environ.get("AWS_REGION", "ap-south-1")


def _s3() -> "boto3.client":
    return boto3.client("s3", region_name=AWS_REGION)


def _lambda_client() -> "boto3.client":
    return boto3.client("lambda", region_name=AWS_REGION)


def submit_job(file_bytes: bytes, filename: str, page: int) -> str:
    """Upload input to S3 and fire the worker Lambda async. Returns job_id."""
    if not JOBS_BUCKET:
        raise RuntimeError("JOBS_BUCKET env var not set")

    job_id = str(uuid.uuid4())
    suffix = Path(filename).suffix.lower() or ".pdf"
    input_key = f"jobs/{job_id}/input{suffix}"

    s3 = _s3()
    s3.put_object(
        Bucket=JOBS_BUCKET,
        Key=input_key,
        Body=file_bytes,
    )
    s3.put_object(
        Bucket=JOBS_BUCKET,
        Key=f"jobs/{job_id}/status.json",
        Body=json.dumps({"status": "queued"}),
        ContentType="application/json",
    )

    payload = {
        "job_id":    job_id,
        "bucket":    JOBS_BUCKET,
        "input_key": input_key,
        "filename":  filename,
        "page":      page,
    }
    _lambda_client().invoke(
        FunctionName=WORKER_FUNCTION,
        InvocationType="Event",   # async — returns immediately
        Payload=json.dumps(payload).encode(),
    )

    print(f"[submit] job={job_id} input_key={input_key} worker={WORKER_FUNCTION}")
    return job_id


def get_job_result(job_id: str) -> dict:
    """Poll S3 for job status. Returns dict with 'status' key.

    Possible statuses: queued | running | complete | failed | not_found
    When status is 'complete', 'xlsx_bytes' key holds the xlsx content.
    When status is 'failed', 'error' key has the message.
    """
    if not JOBS_BUCKET:
        raise RuntimeError("JOBS_BUCKET env var not set")

    s3 = _s3()

    # Check status first
    try:
        resp = s3.get_object(Bucket=JOBS_BUCKET, Key=f"jobs/{job_id}/status.json")
        status_data = json.loads(resp["Body"].read())
        status = status_data.get("status", "unknown")
    except s3.exceptions.NoSuchKey:
        return {"status": "not_found"}
    except Exception:
        return {"status": "not_found"}

    if status == "complete":
        try:
            xlsx = s3.get_object(Bucket=JOBS_BUCKET, Key=f"jobs/{job_id}/output.xlsx")
            return {"status": "complete", "xlsx_bytes": xlsx["Body"].read()}
        except Exception as exc:
            return {"status": "failed", "error": f"output.xlsx missing: {exc}"}

    if status == "failed":
        try:
            err = s3.get_object(Bucket=JOBS_BUCKET, Key=f"jobs/{job_id}/error.json")
            error_data = json.loads(err["Body"].read())
            return {"status": "failed", "error": error_data.get("error", "unknown")}
        except Exception:
            return {"status": "failed", "error": "unknown"}

    return {"status": status}
