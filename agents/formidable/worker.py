"""Fargate worker for the async codex job.

Triggered by Fargate via run_fargate.sh or main.py (ecs.run_task).
Reads job parameters from environment variables, downloads input from S3,
runs codex exec, uploads all artifacts to S3, updates DynamoDB.

Entry: python3 worker.py
Environment: JOB_ID, JOBS_BUCKET, INPUT_KEY, FILENAME, USER_ID, AWS_REGION
"""

import json
import logging
import os
import shutil
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boto3

PROMPT_PATH    = Path(__file__).parent / "prompts" / "codex_prompt.md"
RENDER_TOOL    = Path(__file__).parent / "tools" / "render_page.py"
CODEX_TIMEOUT  = 540
DYNAMO_TABLE   = "formidable-jobs"
S3_PREFIX      = "formidable"

# ── Logging: file first, then S3 upload on exit ────────────────────────────────
LOG_PATH = Path("/tmp/run.log")
logging.basicConfig(
    filename=str(LOG_PATH),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


def _bootstrap_codex_auth() -> None:
    secret_name = os.environ.get("CODEX_SECRET_NAME", "formidable/codex-auth")
    region      = os.environ.get("AWS_REGION", "ap-south-1")
    try:
        sm   = boto3.client("secretsmanager", region_name=region)
        resp = sm.get_secret_value(SecretId=secret_name)
        auth = json.loads(resp["SecretString"])
        auth_dir = Path.home() / ".codex"
        auth_dir.mkdir(parents=True, exist_ok=True)
        (auth_dir / "auth.json").write_text(json.dumps(auth))
        if auth.get("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = auth["OPENAI_API_KEY"]
        log.info("codex credentials bootstrapped from Secrets Manager")
    except Exception as exc:
        log.warning("could not fetch codex auth: %s", exc)


def _build_prompt(input_name: str) -> str:
    template = PROMPT_PATH.read_text()
    return (
        template
        .replace("{input_file}", input_name)
        .replace("{render_tool}", str(RENDER_TOOL))
    )


def _count_pdf_pages(input_path: Path) -> int:
    try:
        import fitz
        doc = fitz.open(str(input_path))
        n = doc.page_count
        doc.close()
        return n
    except Exception:
        return 0


def _run_codex(workdir: Path, input_name: str, on_page=None, on_tick=None) -> tuple[bool, str]:
    """Run codex exec, calling on_page(seen) each time a new page_N.png appears,
    and on_tick() every ~30 s (6 poll ticks) for mid-run log flushing."""
    prompt        = _build_prompt(input_name)
    last_msg_path = workdir / "last_message.txt"

    try:
        proc = subprocess.Popen(
            [
                "codex", "exec",
                "--dangerously-bypass-approvals-and-sandbox",
                "--skip-git-repo-check",
                "-C", str(workdir),
                "-o", str(last_msg_path),
                "-",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(workdir),
            env={**os.environ},
        )
    except FileNotFoundError:
        return False, "codex binary not found"

    # Drain stdout/stderr in threads to prevent pipe-buffer deadlock
    out_buf: list[str] = []
    err_buf: list[str] = []
    threading.Thread(target=lambda: out_buf.append(proc.stdout.read()), daemon=True).start()
    threading.Thread(target=lambda: err_buf.append(proc.stderr.read()), daemon=True).start()

    proc.stdin.write(prompt)
    proc.stdin.close()

    # Poll for page_N.png files while codex runs
    seen: set[str] = set()
    deadline = time.time() + CODEX_TIMEOUT
    tick = 0
    while proc.poll() is None:
        if time.time() > deadline:
            proc.kill()
            return False, f"codex timed out after {CODEX_TIMEOUT}s"
        current = {f.name for f in workdir.glob("page_*.png")}
        if new := current - seen:
            seen = current
            if on_page:
                on_page(len(seen))
        tick += 1
        if on_tick and tick % 6 == 0:
            on_tick()
        time.sleep(5)

    stdout = out_buf[0] if out_buf else ""
    stderr = err_buf[0] if err_buf else ""
    if stdout:
        log.info("codex stdout (tail): %s", stdout[-3000:])
    if stderr:
        log.warning("codex stderr: %s", stderr[-1000:])

    last_msg = last_msg_path.read_text() if last_msg_path.exists() else ""
    log.info("codex rc=%d last_msg=%r", proc.returncode, last_msg[:300])

    if proc.returncode != 0:
        return False, f"codex exited {proc.returncode}: {stderr[:400]}\n{last_msg}"
    return True, last_msg


def _upload_log(s3, bucket: str, job_id: str, shutdown: bool = True):
    try:
        if shutdown:
            logging.shutdown()
        for h in logging.getLogger().handlers:
            h.flush()
        s3.upload_file(str(LOG_PATH), bucket, f"{S3_PREFIX}/jobs/{job_id}/run.log")
    except Exception as exc:
        print(f"[worker] WARNING: could not upload run.log: {exc}")


def _update_dynamo(dynamo, job_id: str, user_id: str, update_expr: str,
                   attr_values: dict, attr_names: dict | None = None):
    kwargs = dict(
        TableName=DYNAMO_TABLE,
        Key={"user_id": {"S": user_id}, "job_id": {"S": job_id}},
        UpdateExpression=update_expr,
        ExpressionAttributeValues=attr_values,
    )
    if attr_names:
        kwargs["ExpressionAttributeNames"] = attr_names
    try:
        dynamo.update_item(**kwargs)
    except Exception as exc:
        log.error("DynamoDB update failed: %s", exc)


def _parse_metadata(workdir: Path) -> dict:
    """Read metadata.json; normalise to flat {gps, grid_no, date} from any format codex emits."""
    meta_path = workdir / "metadata.json"
    if not meta_path.exists():
        return {}
    try:
        raw = json.loads(meta_path.read_text())
    except Exception:
        return {}

    if "gps" in raw or "grid_no" in raw or "date" in raw:
        return raw

    for key in ("pages", "forms", "entries"):
        entries = raw.get(key)
        if isinstance(entries, list) and entries:
            first = entries[0]
            return {
                "gps":     first.get("gps"),
                "grid_no": first.get("grid_no"),
                "date":    first.get("date"),
            }

    return {}


# Total attachment budget — SES SendRawEmail caps a message at 10 MB (base64
# inflates ~1.37×), so keep raw attachment bytes well under that.
_MAX_ATTACH_BYTES = 7 * 1024 * 1024


def _send_email(to_addr: str, subject: str, body_text: str,
                body_html: str | None = None,
                attachments: list[Path] | None = None) -> None:
    """Send an email via AWS SES. Uses SendRawEmail (MIME) when attachments are
    present, else the simpler SendEmail. Non-blocking — silently logs on failure.

    SES setup (one-time):
      1. Verify the FROM address (NOTIFICATION_FROM_EMAIL):
           aws ses verify-email-identity --email-address prashanth@tech4goodcommunity.com --region ap-south-1
      2. In the SES sandbox (default), each recipient must also be verified:
           aws ses verify-email-identity --email-address user@example.com --region ap-south-1
         Request production access (SES console → Account Dashboard) to send to anyone.
      IAM: the Fargate task role needs ses:SendEmail AND ses:SendRawEmail
      (see deploy/fargate-task-policy.json).
    """
    from_addr = os.environ.get("NOTIFICATION_FROM_EMAIL", "prashanth@tech4goodcommunity.com")
    region    = os.environ.get("AWS_REGION", "ap-south-1")
    attachments = [p for p in (attachments or []) if p and Path(p).exists()]

    try:
        ses = boto3.client("ses", region_name=region)

        if not attachments:
            ses.send_email(
                Source=from_addr,
                Destination={"ToAddresses": [to_addr]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Text": {"Data": body_text, "Charset": "UTF-8"},
                        **({"Html": {"Data": body_html, "Charset": "UTF-8"}} if body_html else {}),
                    },
                },
            )
            log.info("email sent to %s via SES (no attachments)", to_addr)
            return

        import mimetypes
        from email.mime.application import MIMEApplication
        from email.mime.image import MIMEImage
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"]    = from_addr
        msg["To"]      = to_addr

        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            alt.attach(MIMEText(body_html, "html", "utf-8"))
        msg.attach(alt)

        budget = _MAX_ATTACH_BYTES
        for path in attachments:
            path = Path(path)
            data = path.read_bytes()
            if len(data) > budget:
                log.warning("skipping attachment %s (%d bytes) — over budget", path.name, len(data))
                continue
            budget -= len(data)
            ctype, _ = mimetypes.guess_type(path.name)
            maintype = (ctype or "application/octet-stream").split("/")[0]
            if maintype == "image":
                part = MIMEImage(data, _subtype=path.suffix.lstrip(".") or "png")
            else:
                part = MIMEApplication(data)
            part.add_header("Content-Disposition", "attachment", filename=path.name)
            msg.attach(part)

        ses.send_raw_email(
            Source=from_addr,
            Destinations=[to_addr],
            RawMessage={"Data": msg.as_string()},
        )
        log.info("email sent to %s via SES (%d attachments)", to_addr, len(attachments))
    except Exception as exc:
        log.warning("failed to send SES email to %s: %s", to_addr, exc)


def _send_notification_email(to_addr: str, job_name: str, success: bool) -> None:
    """Per-job completion notification (no attachments)."""
    pwa_url   = os.environ.get("PWA_URL", "https://formidable.netlify.app")
    form_name = job_name.rsplit(".", 1)[0]

    if success:
        subject   = f"Your form is ready — {form_name}"
        body_html = (
            f"<p>Your form <strong>{form_name}</strong> has been processed and is ready to review.</p>"
            f'<p><a href="{pwa_url}">Open Formidable</a> to view the extracted data and download your spreadsheet.</p>'
        )
        body_text = f"Your form '{form_name}' has been processed. Open Formidable to review: {pwa_url}"
    else:
        subject   = f"Form processing failed — {form_name}"
        body_html = (
            f"<p>Processing failed for <strong>{form_name}</strong>.</p>"
            f'<p><a href="{pwa_url}">Open Formidable</a> to view the error details and retry.</p>'
        )
        body_text = f"Processing failed for '{form_name}'. Open Formidable to retry: {pwa_url}"

    _send_email(to_addr, subject, body_text, body_html)


def handler(job_id: str, bucket: str, input_key: str, filename: str, user_id: str):
    log.info("worker start job=%s input=%s user=%s", job_id, input_key, user_id)
    notification_email = os.environ.get("NOTIFICATION_EMAIL", "")

    region = os.environ.get("AWS_REGION", "ap-south-1")
    s3     = boto3.client("s3",       region_name=region)
    dynamo = boto3.client("dynamodb", region_name=region)

    workdir = Path(f"/tmp/work-{uuid.uuid4().hex}")
    workdir.mkdir(parents=True, exist_ok=True)

    def _s3_prefix(suffix):
        return f"{S3_PREFIX}/jobs/{job_id}/{suffix}"

    def _write_progress(step: str, pct: int):
        """Upload progress.json to S3. Non-blocking — silently skips on failure."""
        payload = json.dumps({
            "step": step,
            "pct":  pct,
            "ts":   datetime.now(timezone.utc).isoformat(),
        }).encode()
        try:
            s3.put_object(
                Bucket=bucket,
                Key=_s3_prefix("progress.json"),
                Body=payload,
                ContentType="application/json",
            )
        except Exception as exc:
            log.warning("progress write failed: %s", exc)

    try:
        # Mark processing in DynamoDB
        _update_dynamo(dynamo, job_id, user_id,
                       "SET #st = :s",
                       {":s": {"S": "processing"}},
                       {"#st": "status"})
        _write_progress("Starting job", 5)

        # Bootstrap codex credentials
        _bootstrap_codex_auth()
        _write_progress("Setting up", 10)

        # Download input from S3
        suffix     = Path(filename).suffix.lower() or ".pdf"
        input_name = f"input{suffix}"
        s3.download_file(bucket, input_key, str(workdir / input_name))
        log.info("input downloaded: %s", input_name)
        _write_progress("Downloading form", 15)

        # Copy render tool into workdir
        shutil.copy(str(RENDER_TOOL), str(workdir / "render_page.py"))

        n_pages  = _count_pdf_pages(workdir / input_name)
        page_note = f": split into {n_pages} page{'s' if n_pages != 1 else ''}" if n_pages > 1 else ""
        _write_progress(f"Analysing form{page_note}", 20)

        def _on_page(seen: int) -> None:
            label = f"Analysing page {seen} of {n_pages}" if n_pages else f"Analysing page {seen}"
            pct   = 20 + int(60 * seen / max(n_pages, seen))
            _write_progress(label, min(pct, 80))

        def _flush_log() -> None:
            _upload_log(s3, bucket, job_id, shutdown=False)

        ok, msg = _run_codex(workdir, input_name,
                             on_page=_on_page if n_pages else None,
                             on_tick=_flush_log)

        output_path   = workdir / "output.xlsx"
        manifest_path = workdir / "crops_manifest.json"

        if ok and output_path.exists():
            _write_progress("Saving results", 85)

            s3.upload_file(str(output_path), bucket, _s3_prefix("output.xlsx"))

            page_files = sorted(workdir.glob("page_*.png"))
            crop_files = sorted(workdir.glob("crop_*.png"))
            for f in page_files:
                s3.upload_file(str(f), bucket, _s3_prefix(f"pages/{f.name}"))
            for f in crop_files:
                s3.upload_file(str(f), bucket, _s3_prefix(f"crops/{f.name}"))

            if manifest_path.exists():
                s3.upload_file(str(manifest_path), bucket, _s3_prefix("crops_manifest.json"))

            meta = _parse_metadata(workdir)
            if meta:
                s3.put_object(
                    Bucket=bucket,
                    Key=_s3_prefix("metadata.json"),
                    Body=json.dumps(meta).encode(),
                    ContentType="application/json",
                )

            n_pages = len(page_files)
            n_crops = len(crop_files)
            log.info("complete pages=%d crops=%d meta=%s", n_pages, n_crops, meta)

            _write_progress("Finishing up", 95)

            update_parts = ["#st = :s", "pages = :p", "crops = :c"]
            attr_names   = {"#st": "status"}
            attr_values  = {
                ":s": {"S": "complete"},
                ":p": {"N": str(n_pages)},
                ":c": {"N": str(n_crops)},
            }

            if meta.get("gps") and len(meta["gps"]) == 2:
                update_parts.append("gps = :g")
                attr_values[":g"] = {"L": [{"N": str(v)} for v in meta["gps"]]}

            if meta.get("grid_no"):
                update_parts.append("grid_no = :gn")
                attr_values[":gn"] = {"S": str(meta["grid_no"])}

            if meta.get("date"):
                update_parts.append("#dt = :d")
                attr_names["#dt"] = "date"
                attr_values[":d"] = {"S": str(meta["date"])}

            _update_dynamo(dynamo, job_id, user_id,
                           "SET " + ", ".join(update_parts),
                           attr_values, attr_names)
            if notification_email:
                _send_notification_email(notification_email, filename, success=True)

        else:
            error = msg if not ok else f"output.xlsx not produced; last_msg={msg[:300]}"
            log.error("job failed: %s", error[:300])
            _update_dynamo(dynamo, job_id, user_id,
                           "SET #st = :s, #e = :e",
                           {":s": {"S": "failed"}, ":e": {"S": error[:500]}},
                           {"#st": "status", "#e": "error"})
            if notification_email:
                _send_notification_email(notification_email, filename, success=False)

    finally:
        _upload_log(s3, bucket, job_id)
        shutil.rmtree(workdir, ignore_errors=True)


def run_regression() -> int:
    """Nightly regression: run codex on a frozen golden form, tolerant-diff the
    result against the known-good xlsx, and email a report with the xlsx + page
    images attached. Returns 0 on PASS, 1 on FAIL — but always sends the email.

    Env:
      JOBS_BUCKET            (default formidable-storage)
      REGRESSION_PDF_KEY     S3 key of the source PDF   (default formidable/regression/source.pdf)
      REGRESSION_GOLDEN_KEY  S3 key of the golden xlsx  (default formidable/regression/golden.xlsx)
      REGRESSION_EMAIL       report recipient           (default prashanth@tech4goodcommunity.com)
      REGRESSION_MIN_*       tolerant-diff thresholds   (see xlsx_diff.py)
    """
    region     = os.environ.get("AWS_REGION", "ap-south-1")
    bucket     = os.environ.get("JOBS_BUCKET", "formidable-storage")
    pdf_key    = os.environ.get("REGRESSION_PDF_KEY", f"{S3_PREFIX}/regression/source.pdf")
    golden_key = os.environ.get("REGRESSION_GOLDEN_KEY", f"{S3_PREFIX}/regression/golden.xlsx")
    to_addr    = os.environ.get("REGRESSION_EMAIL", "prashanth@tech4goodcommunity.com")
    stamp      = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    log.info("regression start bucket=%s pdf=%s golden=%s", bucket, pdf_key, golden_key)
    s3 = boto3.client("s3", region_name=region)

    workdir = Path(f"/tmp/regression-{uuid.uuid4().hex}")
    workdir.mkdir(parents=True, exist_ok=True)
    run_prefix = f"{S3_PREFIX}/regression/runs/{stamp}"

    def _finish(passed: bool, subject: str, body: str, attachments: list[Path]):
        # Send first, THEN upload the log, so run.log records the email result
        # (send is non-blocking — this is the only place its outcome is captured).
        _send_email(to_addr, subject, body, attachments=attachments)
        try:
            for h in logging.getLogger().handlers:
                h.flush()
            s3.upload_file(str(LOG_PATH), bucket, f"{run_prefix}/run.log")
        except Exception as exc:
            log.warning("could not upload regression run.log: %s", exc)
        shutil.rmtree(workdir, ignore_errors=True)
        return 0 if passed else 1

    try:
        _bootstrap_codex_auth()

        input_name = "input.pdf"
        golden_path = workdir / "golden.xlsx"
        try:
            s3.download_file(bucket, pdf_key, str(workdir / input_name))
            s3.download_file(bucket, golden_key, str(golden_path))
        except Exception as exc:
            body = (f"Nightly regression could not start — fixture missing in S3.\n\n"
                    f"  bucket: {bucket}\n  pdf:    {pdf_key}\n  golden: {golden_key}\n\n"
                    f"Error: {exc}\n\nRun regression/upload_golden.sh to (re)upload the fixture.")
            return _finish(False, "[FAIL] Formidable nightly regression — fixture missing", body, [])

        shutil.copy(str(RENDER_TOOL), str(workdir / "render_page.py"))

        ok, msg = _run_codex(workdir, input_name)
        output_path = workdir / "output.xlsx"

        # Upload whatever artifacts codex produced (for history / debugging).
        page_files = sorted(workdir.glob("page_*.png"))
        for f in [output_path, *page_files, workdir / "crops_manifest.json", workdir / "metadata.json"]:
            if f.exists():
                try:
                    s3.upload_file(str(f), bucket, f"{run_prefix}/{f.name}")
                except Exception:
                    pass

        if not (ok and output_path.exists()):
            error = msg if not ok else "codex finished but output.xlsx was not produced"
            body = (f"Nightly regression FAILED — codex did not produce a spreadsheet.\n\n"
                    f"Run: {stamp}\nArtifacts: s3://{bucket}/{run_prefix}/\n\n"
                    f"codex output (tail):\n{error[-1500:]}")
            return _finish(False, "[FAIL] Formidable nightly regression — no output", body,
                           page_files[:3])

        # Tolerant diff against the golden.
        import xlsx_diff
        result = xlsx_diff.compare(str(golden_path), str(output_path))
        passed = result["passed"]
        tag    = "PASS" if passed else "FAIL"

        body = (
            f"Formidable nightly regression — {tag}\n"
            f"Run: {stamp}\n"
            f"Artifacts: s3://{bucket}/{run_prefix}/\n\n"
            f"{result['report']}\n\n"
            f"Attached: output.xlsx (this run) + page renders. "
            f"Spot-check the spreadsheet against the form when you have a moment.\n"
        )
        subject = f"[{tag}] Formidable nightly regression — {stamp}"
        attachments = [output_path, *page_files[:3]]
        return _finish(passed, subject, body, attachments)

    except Exception as exc:
        log.exception("regression crashed")
        body = f"Nightly regression crashed unexpectedly.\n\nRun: {stamp}\nError: {exc}"
        _send_email(to_addr, "[FAIL] Formidable nightly regression — crashed", body)
        shutil.rmtree(workdir, ignore_errors=True)
        return 1


if __name__ == "__main__":
    import sys

    if os.environ.get("MODE") == "regression":
        sys.exit(run_regression())

    _bootstrap_codex_auth()
    handler(
        job_id    = os.environ["JOB_ID"],
        bucket    = os.environ.get("JOBS_BUCKET", "formidable-storage"),
        input_key = os.environ["INPUT_KEY"],
        filename  = os.environ.get("FILENAME", "input.pdf"),
        user_id   = os.environ.get("USER_ID", "dev-user"),
    )
    sys.exit(0)
