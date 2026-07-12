#!/usr/bin/env bash
# Run the HTTP handler image locally and exercise the async job flow.
#   POST /vision/extract  →  job_id (202)
#   poll GET /vision/jobs/{job_id}  →  xlsx (200) or error
#
# The worker Lambda is NOT running locally. Set LOCAL_WORKER=1 (default)
# to invoke codex directly in-process after the POST. Set LOCAL_WORKER=0
# to skip worker execution (useful for testing HTTP plumbing only).
#
# Usage: run_local.sh <pdf-or-image> [page] [out.xlsx]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/config.sh"

FILE="${1:?usage: run_local.sh <pdf-or-image> [page] [out.xlsx]}"
PAGE="${2:-1}"
OUT="${3:-/tmp/local_output.xlsx}"
LOCAL_WORKER="${LOCAL_WORKER:-1}"

echo "=== Starting ${IMAGE} on :8081 ==="
# Use dummy env vars for local so the HTTP handler starts without real AWS.
# The container only needs to serve /vision/health + accept POST /vision/extract.
CONTAINER_ID=$(docker run -d --rm -p 8081:8080 \
  -e JOBS_BUCKET=local-test \
  -e WORKER_FUNCTION=local-test \
  -e AWS_LWA_REMOVE_BASE_PATH="" \
  --user "$(id -u):$(id -g)" \
  "$IMAGE")
trap 'docker stop "$CONTAINER_ID" >/dev/null 2>&1 || true' EXIT

echo "waiting for health..."
STATUS="000"
for _ in $(seq 1 30); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    "http://localhost:8081${HEALTH_CHECK_PATH}" || echo "000")
  [ "$STATUS" = "200" ] && break
  sleep 1
done
if [ "$STATUS" != "200" ]; then
  echo "health check FAILED (HTTP ${STATUS})"
  docker logs "$CONTAINER_ID" || true
  exit 1
fi
echo "  healthy ✓"

if [ "$LOCAL_WORKER" = "1" ]; then
  echo "=== Running codex directly (bypassing HTTP handler, LOCAL_WORKER=1) ==="
  # Invoke worker.py directly — no Docker-in-Docker, no AWS needed.
  python3 - <<PYEOF
import sys, os, shutil, subprocess, uuid
from pathlib import Path

sys.path.insert(0, "${SERVER_DIR}")
FILE_PATH = "${FILE}"
OUT       = "${OUT}"

WORKDIR = Path(f"/tmp/local-worker-{uuid.uuid4().hex}")
WORKDIR.mkdir()
try:
    suffix     = Path(FILE_PATH).suffix.lower() or ".pdf"
    input_name = f"input{suffix}"
    shutil.copy(FILE_PATH, str(WORKDIR / input_name))
    shutil.copy("${SERVER_DIR}/tools/render_page.py", str(WORKDIR / "render_page.py"))

    template = open("${SERVER_DIR}/prompts/codex_prompt.md").read()
    prompt   = template.replace("{input_file}", input_name).replace("{render_tool}", "render_page.py")

    print(f"[local] running codex in {WORKDIR}")
    last_msg = WORKDIR / "last_message.txt"
    result = subprocess.run(
        ["codex", "exec",
         "--dangerously-bypass-approvals-and-sandbox",
         "--skip-git-repo-check",
         "-C", str(WORKDIR),
         "-o", str(last_msg),
         "-"],
        input=prompt, text=True,
        capture_output=True, cwd=str(WORKDIR), timeout=540,
        env={**os.environ, "HOME": "/tmp"},
    )
    print(result.stdout[-3000:] if result.stdout else "")
    if result.returncode != 0:
        print(f"codex rc={result.returncode}: {result.stderr[:500]}", file=sys.stderr)
        sys.exit(1)
    xlsx = WORKDIR / "output.xlsx"
    if not xlsx.exists():
        print("ERROR: output.xlsx not produced", file=sys.stderr)
        sys.exit(1)
    shutil.copy(str(xlsx), OUT)
    print(f"[local] saved {xlsx.stat().st_size} bytes → {OUT}")
finally:
    shutil.rmtree(str(WORKDIR), ignore_errors=True)
PYEOF
  echo ""
  echo "=== Result at ${OUT} ==="
else
  echo "=== LOCAL_WORKER=0 — HTTP plumbing test only ==="
  RESP=$(curl -sf -X POST "http://localhost:8081/vision/extract" \
    -F "file=@${FILE}" -F "page=${PAGE}" || echo "{}")
  echo "  POST /vision/extract → ${RESP}"
fi

echo ""
echo "=== Container logs (last 20 lines) ==="
docker logs "$CONTAINER_ID" 2>&1 | tail -20
