#!/usr/bin/env bash
# Exercise the real high route and require its focused-review artifacts.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/config.sh"
source "$SCRIPT_DIR/outputs.env"
[ -f "$SCRIPT_DIR/test-credentials.env" ] && source "$SCRIPT_DIR/test-credentials.env"
if [ -z "${TEST_USERNAME:-}" ] && [ -f "$SERVER_DIR/../../server/deploy/test-credentials.env" ]; then
  source "$SERVER_DIR/../../server/deploy/test-credentials.env"
fi
: "${TEST_USERNAME:?set TEST_USERNAME/TEST_PASSWORD (deploy/test-credentials.env)}"

PDF_KEY="${HIGH_VERIFY_PDF_KEY:-${S3_PREFIX}/regression/source.pdf}"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
POLL_TIMEOUT="${HIGH_VERIFY_POLL_TIMEOUT:-1200}"

aws s3 cp "s3://${JOBS_BUCKET}/${PDF_KEY}" "$WORK/source.pdf" --region "$AWS_REGION" >/dev/null
TOKEN=$(aws cognito-idp initiate-auth \
  --client-id "$COGNITO_CLIENT_ID" --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters "USERNAME=${TEST_USERNAME},PASSWORD=${TEST_PASSWORD}" \
  --region "$AWS_REGION" --query 'AuthenticationResult.IdToken' --output text)
AUTH=(-H "Authorization: Bearer ${TOKEN}")

RESP=$(curl -sf -X POST "${APIGW_URL}/vision/extract" "${AUTH[@]}" \
  -H "Content-Type: application/json" \
  -d '{"filename":"TreePlots20mx20m.pdf","name":"high-prod-verify","effort":"high"}')
JOB_ID=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["job_id"])' <<<"$RESP")
UPLOAD_URL=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["upload_url"])' <<<"$RESP")
echo "high verify job_id=${JOB_ID}"
curl -sf -X PUT --upload-file "$WORK/source.pdf" \
  -H "Content-Type: application/octet-stream" "$UPLOAD_URL" >/dev/null
START=$(curl -sf -X POST "${APIGW_URL}/api/jobs/${JOB_ID}/start" "${AUTH[@]}")
python3 -c 'import json,sys; r=json.load(sys.stdin); assert r["effort"]=="high"; assert r["task_family"]=="formidable-high-worker"' <<<"$START"

elapsed=0
while [ "$elapsed" -lt "$POLL_TIMEOUT" ]; do
  STATUS=$(curl -sf "${APIGW_URL}/api/jobs/${JOB_ID}/status" "${AUTH[@]}")
  STATE=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])' <<<"$STATUS")
  case "$STATE" in
    complete) break ;;
    failed) echo "FAIL: high worker: $STATUS"; exit 1 ;;
  esac
  sleep 15; elapsed=$((elapsed + 15))
done
[ "$STATE" = complete ] || { echo "FAIL: high timed out after ${POLL_TIMEOUT}s"; exit 1; }

curl -sf "${APIGW_URL}/api/jobs/${JOB_ID}/review-manifest" "${AUTH[@]}" >"$WORK/review.json"
curl -sf "${APIGW_URL}/api/jobs/${JOB_ID}/analytics" "${AUTH[@]}" >"$WORK/analytics.json"
XLSX_META=$(curl -sf "${APIGW_URL}/api/jobs/${JOB_ID}/xlsx" "${AUTH[@]}")
XLSX_URL=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["url"])' <<<"$XLSX_META")
curl -sf "$XLSX_URL" >"$WORK/output.xlsx"

python3 - "$WORK" <<'PY'
import json, sys
from pathlib import Path
import openpyxl
root = Path(sys.argv[1])
review = json.loads((root / "review.json").read_text())
analytics = json.loads((root / "analytics.json").read_text())
assert review["version"] == "formidable-review-v1"
assert analytics["version"] == "formidable-analytics-v1"
assert review["summary"]["target_cells_including_blanks"] > 0
assert analytics["summary"]["pages"] > 0
assert len(review["cells"]) > 0
assert "transcription_attention" in review["views"]
assert "ecology_anomalies" in review["views"]
wb = openpyxl.load_workbook(root / "output.xlsx", read_only=True)
assert wb.sheetnames[-1] == "ecology_review"
assert len(wb.sheetnames) == analytics["summary"]["pages"] + 1
print(json.dumps({"pages": analytics["summary"]["pages"],
                  "disagreements": analytics["summary"]["disagreements"],
                  "ecology_flags": analytics["summary"]["ecology_findings"]}))
PY
echo "verify_high PASS job_id=${JOB_ID}"
