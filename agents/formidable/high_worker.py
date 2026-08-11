"""High-effort Fargate worker: dual literal readers plus ecology review."""
from __future__ import annotations

import copy
import json
import logging
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import boto3
from PIL import Image

AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
JOBS_BUCKET = os.environ.get("JOBS_BUCKET", "formidable-storage")
S3_PREFIX = os.environ.get("S3_PREFIX", "formidable")
DYNAMO_TABLE = os.environ.get("DYNAMO_TABLE", "formidable-jobs")
PROVIDER_SECRET_NAME = os.environ.get(
    "PROVIDER_SECRET_NAME", "formidable/openrouter-api-key")
CODEX_SECRET_NAME = os.environ.get("CODEX_SECRET_NAME", "formidable/codex-auth")
PIPELINE_DIR = Path(os.environ.get("FORMIDABLE_HIGH_PIPELINE_DIR", Path(__file__).parent / "high_pipeline"))
LOG_PATH = Path("/tmp/high-run.log")

logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def _job_key(job_id: str, suffix: str) -> str:
    return f"{S3_PREFIX}/jobs/{job_id}/{suffix}"


def _load_provider_key() -> None:
    secret = boto3.client("secretsmanager", region_name=AWS_REGION).get_secret_value(
        SecretId=PROVIDER_SECRET_NAME)["SecretString"]
    try:
        value = json.loads(secret)
        key = value.get("api_key") or value.get("OPENROUTER_API_KEY")
    except json.JSONDecodeError:
        key = secret
    if not key:
        raise RuntimeError("provider secret does not contain an OpenRouter API key")
    os.environ["OPENROUTER_API_KEY"] = key


def _bootstrap_codex_auth() -> None:
    """Install the same subscription credential used by the frozen low worker."""
    secret = boto3.client("secretsmanager", region_name=AWS_REGION).get_secret_value(
        SecretId=CODEX_SECRET_NAME)["SecretString"]
    auth = json.loads(secret)
    auth_dir = Path.home() / ".codex"
    auth_dir.mkdir(parents=True, exist_ok=True)
    (auth_dir / "auth.json").write_text(json.dumps(auth))


def _modules():
    sys.path.insert(0, str(PIPELINE_DIR))
    os.environ.setdefault("FORMIDABLE_RENDER_TOOL", str(Path(__file__).parent / "tools" / "render_page.py"))
    import analytics_manifest
    import canonical
    import ecology_review
    import primary_bridge
    import review_manifest
    import structured_pipeline
    return (analytics_manifest, canonical, ecology_review, primary_bridge,
            review_manifest, structured_pipeline)


def _as_pdf(source: Path, destination: Path) -> None:
    if source.suffix.casefold() == ".pdf":
        shutil.copy2(source, destination)
        return
    with Image.open(source) as image:
        image.convert("RGB").save(destination, "PDF", resolution=200)


def _write_progress(s3, job_id: str, step: str, pct: int) -> None:
    value = {"step": step, "pct": pct, "ts": datetime.now(timezone.utc).isoformat()}
    s3.put_object(Bucket=JOBS_BUCKET, Key=_job_key(job_id, "progress.json"),
                  Body=json.dumps(value).encode(), ContentType="application/json")


def _update_job(dynamo, user_id: str, job_id: str, expression: str, values: dict,
                names: dict | None = None) -> None:
    args = dict(TableName=DYNAMO_TABLE,
                Key={"user_id": {"S": user_id}, "job_id": {"S": job_id}},
                UpdateExpression=expression, ExpressionAttributeValues=values)
    if names:
        args["ExpressionAttributeNames"] = names
    dynamo.update_item(**args)


def _union_bbox(items: list[dict]) -> list[float] | None:
    boxes = [item.get("bbox") for item in items
             if isinstance(item.get("bbox"), list) and len(item["bbox"]) == 4]
    if not boxes:
        return None
    return [max(0, min(box[0] for box in boxes) - .006),
            max(0, min(box[1] for box in boxes) - .006),
            min(1, max(box[2] for box in boxes) + .006),
            min(1, max(box[3] for box in boxes) + .006)]


def _build_crops(document: dict, form_dir: Path, workdir: Path) -> dict:
    """Create useful broad review crops without weakening cell-level boxes."""
    pages_dir, crops_dir = workdir / "pages", workdir / "crops"
    pages_dir.mkdir(exist_ok=True)
    crops_dir.mkdir(exist_ok=True)
    manifest_pages = []
    for page in document["pages"]:
        number = page["page_number"]
        source_page = form_dir / "canonical_tiles" / f"page_{number}_overview.png"
        destination = pages_dir / f"page_{number}.png"
        shutil.copy2(source_page, destination)
        entries = []
        with Image.open(source_page) as image:
            groups = []
            fields = page.get("metadata_fields") or []
            if fields:
                groups.append(("Header fields", fields))
            for item in page.get("free_text_regions") or []:
                groups.append((f"Note: {item.get('label') or item['id']}", [item]))
            for table in page.get("tables") or []:
                rows = table.get("rows") or []
                for start in range(0, len(rows), 12):
                    chunk = rows[start:start + 12]
                    groups.append((table.get("title") or table["id"], chunk))
            for index, (label, items) in enumerate(groups, 1):
                region = _union_bbox(items)
                xlsx_rows = []
                for item in items:
                    if item.get("xlsx_row") is not None:
                        xlsx_rows.append(item["xlsx_row"])
                    xlsx_rows.extend(cell["xlsx_row"] for cell in item.get("cells") or []
                                     if cell.get("xlsx_row") is not None)
                if not region or not xlsx_rows:
                    continue
                x0, y0, x1, y1 = region
                pixels = (round(x0 * image.width), round(y0 * image.height),
                          round(x1 * image.width), round(y1 * image.height))
                filename = f"crop_p{number}_{index:02d}.png"
                image.crop(pixels).save(crops_dir / filename)
                entries.append({"file": filename, "bbox": region,
                                "rows": f"{min(xlsx_rows)}:{max(xlsx_rows)}",
                                "note": label})
        manifest_pages.append({"page": number, "render": destination.name,
                               "crops": entries})
    return {"pages": manifest_pages}


def _run_agentic_primary(input_pdf: Path, primary_dir: Path, *, on_page=None) -> Path:
    """Run the frozen low workflow inside high without changing the low task."""
    from worker import _run_codex

    primary_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(input_pdf, primary_dir / "input.pdf")
    shutil.copy2(Path(__file__).parent / "tools" / "render_page.py",
                 primary_dir / "render_page.py")
    ok, message = _run_codex(primary_dir, "input.pdf", on_page=on_page)
    output = primary_dir / "output.xlsx"
    if not ok or not output.exists():
        detail = message[-1000:] if message else "output.xlsx was not produced"
        raise RuntimeError(f"agentic primary failed: {detail}")
    return output


def _document_items(document: dict):
    for page in document.get("pages") or []:
        yield from page.get("metadata_fields") or []
        yield from page.get("free_text_regions") or []
        for table in page.get("tables") or []:
            for row in table.get("rows") or []:
                yield from row.get("cells") or []


def _select_complete_reader(document: dict, canonical) -> tuple[dict, str, dict]:
    """Select a fallback reader by literal coverage, without domain knowledge."""
    models = list(document.get("models") or [])
    if not models:
        raise RuntimeError("structured extraction has no reader models")
    coverage = {}
    for model in models:
        coverage[model] = sum(
            str(next((reading.get("value") for reading in item.get("readings") or []
                      if reading.get("model") == model), None) or "").strip() != ""
            for item in _document_items(document))
    # Stable ordering prefers the declared reader. A small difference in filled
    # cells is normal reader variance and can reward hallucinated content; only
    # switch when another reader recovers at least 10% more literal evidence.
    selected = models[0]
    leader = max(models, key=lambda model: coverage[model])
    if coverage[leader] >= max(1, coverage[selected]) * 1.10:
        selected = leader
    fallback = copy.deepcopy(document)
    fallback["models"] = [selected, *(model for model in models if model != selected)]
    canonical.resolve(fallback)
    return fallback, selected, coverage


def process(source: Path, workdir: Path, *, ecology_online: bool = True,
            reuse_existing: bool = False, progress=None,
            primary_progress=None) -> dict:
    """Run the production high pipeline locally inside one isolated directory."""
    (analytics_mod, canonical, ecology_review, primary_bridge,
     review_manifest, structured) = _modules()
    form_dir = workdir / "form"
    form_dir.mkdir(parents=True, exist_ok=True)
    _as_pdf(source, form_dir / "input.pdf")
    primary_dir = workdir / "primary"
    if reuse_existing and (primary_dir / "output.xlsx").exists():
        primary_xlsx = primary_dir / "output.xlsx"
    else:
        primary_xlsx = _run_agentic_primary(
            form_dir / "input.pdf", primary_dir, on_page=primary_progress)

    tag = "high_v1"
    canonical_dir = form_dir / "canonical_outputs" / tag
    if reuse_existing and (canonical_dir / "run.json").exists():
        extraction = structured.rebuild(form_dir, tag)
    else:
        extraction = structured.run(
            form_dir, os.environ.get("HIGH_SCHEMA_MODEL", "codex:gpt-5.6-luna"),
            [os.environ.get("HIGH_PRIMARY_MODEL", "codex:gpt-5.6-terra"),
             os.environ.get("HIGH_PEER_MODEL", "codex:gpt-5.6-luna")], tag,
            reuse_existing=reuse_existing,
            progress_callback=progress)
    if extraction.get("validation_errors"):
        raise RuntimeError("canonical validation failed: "
                           + "; ".join(extraction["validation_errors"]))
    peer_document = json.loads((canonical_dir / "canonical.json").read_text())
    canonical.assign_xlsx_coordinates(peer_document)
    primary_document = copy.deepcopy(peer_document)
    bridge = primary_bridge.bind_primary(
        primary_document, canonical_dir / "output.xlsx", primary_xlsx)
    minimum_coverage = float(os.environ.get("HIGH_PRIMARY_BRIDGE_MIN_COVERAGE", "0.80"))
    if bridge["peer_nonblank_coverage"] >= minimum_coverage:
        document = primary_document
        content_route = "agentic_primary"
        selected_reader = None
        reader_coverage = None
    else:
        # A plausible-looking but structurally incomplete agentic workbook is a
        # known fatigue mode. Never retry it and never publish it. Fall back to
        # the independently structured reader with greater literal coverage.
        document, selected_reader, reader_coverage = _select_complete_reader(
            peer_document, canonical)
        canonical.assign_xlsx_coordinates(document)
        content_route = "structured_reader_fallback"

    records = ecology_review.canonical_records(document)
    findings = ecology_review.numeric_findings(records)
    if ecology_online:
        latitude, longitude = ecology_review.location_coordinates(records)
        findings += ecology_review.taxonomy_findings(
            records, ecology_review.GBIFClient(workdir / "gbif-cache"),
            latitude, longitude)
    ecology = {
        "version": "formidable-ecology-review-v1",
        "policy": "flags and suggestions only; literal values are never changed",
        "records": len(records), "findings": findings,
    }
    actionable_findings = [finding for finding in findings
                           if finding.get("severity") in {"medium", "high"}]
    ecology_review.apply_findings(document, actionable_findings)

    content_xlsx = workdir / "content.xlsx"
    if content_route == "agentic_primary":
        # Preserve the proven primary workbook's content and layout exactly.
        shutil.copy2(primary_xlsx, content_xlsx)
    else:
        canonical.write_xlsx(document, content_xlsx)
    output_xlsx = workdir / "output.xlsx"
    shutil.copy2(content_xlsx, output_xlsx)
    ecology_review.add_review_sheet(output_xlsx, findings)
    canonical.dump(document, workdir / "canonical.json")
    (workdir / "ecology_review.json").write_text(
        json.dumps(ecology, indent=2, ensure_ascii=False) + "\n")

    review = review_manifest.from_canonical(document, ecology)
    review["route"] = {
        "status": content_route, "path": "high_v1",
        "reason": (
            "frozen low workflow retained as immutable content; two structured "
            "peers must agree before a red review flag"
            if content_route == "agentic_primary" else
            "agentic workbook failed the sector-agnostic coverage gate; the more "
            "complete structured reader is shown and every peer disagreement is red"
        ),
    }
    errors = review_manifest.validate(review)
    if errors:
        raise RuntimeError("invalid review manifest: " + "; ".join(errors))
    (workdir / "review_manifest.json").write_text(
        json.dumps(review, indent=2, ensure_ascii=False) + "\n")

    analytics = analytics_mod.build(document, ecology)
    (workdir / "analytics.json").write_text(
        json.dumps(analytics, indent=2, ensure_ascii=False) + "\n")

    crops_manifest = _build_crops(document, form_dir, workdir)
    (workdir / "crops_manifest.json").write_text(
        json.dumps(crops_manifest, indent=2) + "\n")

    run = {"version": "formidable-high-v2",
           "route": content_route,
           "primary": {"model": "codex:agentic-low", "workbook": "primary/output.xlsx"},
           "content": {"workbook": "content.xlsx", "route": content_route,
                       "selected_reader": selected_reader,
                       "reader_nonblank_coverage": reader_coverage},
           "bridge": bridge, "extraction": extraction, "review": review["summary"],
           "analytics": analytics["summary"], "ecology_online": ecology_online}
    (workdir / "run.json").write_text(json.dumps(run, indent=2) + "\n")

    evidence = workdir / "evidence"
    evidence.mkdir(exist_ok=True)
    for path in canonical_dir.glob("page_*__*.json"):
        shutil.copy2(path, evidence / path.name)
    for path in canonical_dir.glob("page_*__*.meta.json"):
        shutil.copy2(path, evidence / path.name)
    return run


def _notify(to_addr: str, filename: str, job_id: str, success: bool) -> None:
    if not to_addr:
        return
    subject = f"Formidable high processing {'complete' if success else 'failed'}: {filename}"
    url = f"{os.environ.get('PWA_URL', 'https://fomoscribe.netlify.app')}/review/{job_id}"
    body = f"High-effort processing {'completed' if success else 'failed'}.\n\n{url}"
    boto3.client("ses", region_name=AWS_REGION).send_email(
        Source=os.environ.get("NOTIFICATION_FROM_EMAIL", "prashanth@tech4goodcommunity.com"),
        Destination={"ToAddresses": [to_addr]},
        Message={"Subject": {"Data": subject}, "Body": {"Text": {"Data": body}}})


def main() -> int:
    job_id = os.environ["JOB_ID"]
    input_key = os.environ["INPUT_KEY"]
    filename = os.environ.get("FILENAME", "input.pdf")
    user_id = os.environ["USER_ID"]
    notification = os.environ.get("NOTIFICATION_EMAIL", "")
    s3 = boto3.client("s3", region_name=AWS_REGION)
    dynamo = boto3.client("dynamodb", region_name=AWS_REGION)
    suffix = Path(input_key).suffix or ".pdf"

    with tempfile.TemporaryDirectory(prefix="formidable-high-") as temporary:
        workdir = Path(temporary)
        source = workdir / f"source{suffix}"
        try:
            _update_job(dynamo, user_id, job_id, "SET #st = :s",
                        {":s": {"S": "processing"}}, {"#st": "status"})
            _write_progress(s3, job_id, "Starting high-effort dual-reader pipeline…", 3)
            s3.download_file(JOBS_BUCKET, input_key, str(source))
            _bootstrap_codex_auth()
            _write_progress(s3, job_id, "Running the proven primary transcription…", 8)
            run = process(source, workdir,
                          ecology_online=os.environ.get("HIGH_ECOLOGY_ONLINE", "1") != "0",
                          primary_progress=lambda page: _write_progress(
                              s3, job_id,
                              f"Primary transcribed {page} page{'s' if page != 1 else ''}…",
                              min(28, 8 + 4 * page)),
                          progress=lambda page, total: _write_progress(
                              s3, job_id,
                              f"Consensus peers read page {page} of {total}…",
                              30 + round(54 * page / max(1, total))))
            _write_progress(s3, job_id, "Publishing review and analytics evidence…", 92)

            for name in ("output.xlsx", "crops_manifest.json", "canonical.json",
                         "review_manifest.json", "ecology_review.json", "analytics.json", "run.json"):
                s3.upload_file(str(workdir / name), JOBS_BUCKET, _job_key(job_id, name))
            for path in (workdir / "pages").glob("page_*.png"):
                s3.upload_file(str(path), JOBS_BUCKET, _job_key(job_id, f"pages/{path.name}"))
            for path in (workdir / "crops").glob("crop_*.png"):
                s3.upload_file(str(path), JOBS_BUCKET, _job_key(job_id, f"crops/{path.name}"))
            for path in (workdir / "evidence").glob("*.json"):
                s3.upload_file(str(path), JOBS_BUCKET, _job_key(job_id, f"evidence/{path.name}"))

            manifest = json.loads((workdir / "crops_manifest.json").read_text())
            pages = len(manifest["pages"])
            crops = sum(len(page["crops"]) for page in manifest["pages"])
            _update_job(dynamo, user_id, job_id,
                        "SET #st = :s, pages = :p, crops = :c, high_summary = :h",
                        {":s": {"S": "complete"}, ":p": {"N": str(pages)},
                         ":c": {"N": str(crops)},
                         ":h": {"S": json.dumps(run["review"], separators=(",", ":"))}},
                        {"#st": "status"})
            _write_progress(s3, job_id, "Complete", 100)
            _notify(notification, filename, job_id, True)
            return 0
        except Exception as error:
            log.exception("high worker failed job=%s", job_id)
            try:
                _update_job(dynamo, user_id, job_id, "SET #st = :s, #err = :e",
                            {":s": {"S": "failed"}, ":e": {"S": str(error)[:1000]}},
                            {"#st": "status", "#err": "error"})
                _write_progress(s3, job_id, f"Failed: {error}", 100)
                _notify(notification, filename, job_id, False)
            except Exception:
                log.exception("could not publish high worker failure")
            return 1
        finally:
            if LOG_PATH.exists():
                try:
                    s3.upload_file(str(LOG_PATH), JOBS_BUCKET, _job_key(job_id, "run.log"))
                except Exception:
                    pass


if __name__ == "__main__":
    raise SystemExit(main())
