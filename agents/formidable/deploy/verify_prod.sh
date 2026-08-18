#!/usr/bin/env bash
# Post-deploy gate: exercise the REAL prod path end-to-end through the API
# Gateway + Cognito, then tolerant-diff the result against the golden.
#
#   mint JWT → POST /vision/extract → PUT to presigned S3 → POST /api/jobs/{id}/start
#   → poll GET /vision/jobs/{id} → download xlsx → xlsx_diff vs golden
#
# Exit 0 = prod healthy, 1 = failed (deploy.sh triggers rollback on 1).
# Uses the same golden fixture as the nightly regression (in S3).
#
# Usage: ./verify_prod.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/config.sh"
source "$SCRIPT_DIR/outputs.env"
[ -f "$SCRIPT_DIR/test-credentials.env" ] && source "$SCRIPT_DIR/test-credentials.env"
# Fall back to the server repo's test creds if this component has none.
if [ -z "${TEST_USERNAME:-}" ] && [ -f "$SERVER_DIR/../../server/deploy/test-credentials.env" ]; then
  source "$SERVER_DIR/../../server/deploy/test-credentials.env"
fi
: "${TEST_USERNAME:?set TEST_USERNAME/TEST_PASSWORD (deploy/test-credentials.env)}"

PDF_KEY="${REGRESSION_PDF_KEY:-${S3_PREFIX}/regression/source.pdf}"
GOLDEN_KEY="${REGRESSION_GOLDEN_KEY:-${S3_PREFIX}/regression/golden.xlsx}"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
POLL_TIMEOUT="${VERIFY_POLL_TIMEOUT:-600}"

echo "=== verify_prod: real API end-to-end (${APIGW_URL}) ==="

# ── 0. Fixture ─────────────────────────────────────────────────────
aws s3 cp "s3://${JOBS_BUCKET}/${PDF_KEY}"    "$WORK/source.pdf"  --region "$AWS_REGION" >/dev/null
aws s3 cp "s3://${JOBS_BUCKET}/${GOLDEN_KEY}" "$WORK/golden.xlsx" --region "$AWS_REGION" >/dev/null

# ── 1. Mint Cognito JWT ────────────────────────────────────────────
echo "→ minting JWT for ${TEST_USERNAME}"
TOKEN=$(aws cognito-idp initiate-auth \
  --client-id "$COGNITO_CLIENT_ID" --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters "USERNAME=${TEST_USERNAME},PASSWORD=${TEST_PASSWORD}" \
  --region "$AWS_REGION" --query 'AuthenticationResult.IdToken' --output text)
[ -n "$TOKEN" ] && [ "$TOKEN" != "None" ] || { echo "FAIL: could not mint JWT"; exit 1; }

AUTH=(-H "Authorization: Bearer ${TOKEN}")

# ── 2. Create job (returns job_id + presigned upload_url) ──────────
echo "→ POST /vision/extract"
RESP=$(curl -sf -X POST "${APIGW_URL}/vision/extract" "${AUTH[@]}" \
  -H "Content-Type: application/json" \
  -d '{"filename":"TreePlots20mx20m.pdf","name":"prod-verify","effort":"low"}') || { echo "FAIL: /vision/extract"; exit 1; }
JOB_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
UPLOAD_URL=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['upload_url'])")
echo "  job_id=${JOB_ID}"

# ── 3. Upload PDF to S3 via presigned URL (ContentType must match) ─
echo "→ PUT presigned upload"
curl -sf -X PUT --upload-file "$WORK/source.pdf" \
  -H "Content-Type: application/octet-stream" "$UPLOAD_URL" >/dev/null || { echo "FAIL: presigned upload"; exit 1; }

# ── 4. Start the job (launches the worker) ─────────────────────────
echo "→ POST /api/jobs/${JOB_ID}/start"
START=$(curl -sf -X POST "${APIGW_URL}/api/jobs/${JOB_ID}/start" "${AUTH[@]}") || { echo "FAIL: start"; exit 1; }
python3 -c 'import json,sys; r=json.load(sys.stdin); assert r["effort"]=="low"; assert r["task_family"]=="formidable-worker"' <<<"$START"

# ── 5. Poll until the xlsx is ready ───────────────────────────────
echo "→ polling GET /vision/jobs/${JOB_ID} (timeout ${POLL_TIMEOUT}s)"
elapsed=0
while [ "$elapsed" -lt "$POLL_TIMEOUT" ]; do
  CODE=$(curl -s -o "$WORK/out.bin" -w "%{http_code}" "${APIGW_URL}/vision/jobs/${JOB_ID}" "${AUTH[@]}" || echo 000)
  case "$CODE" in
    200) mv "$WORK/out.bin" "$WORK/output.xlsx"; echo "  ready (${elapsed}s)"; break ;;
    202) printf "  [%3ds] %s\n" "$elapsed" "$(python3 -c "import json;print(json.load(open('$WORK/out.bin')).get('status','?'))" 2>/dev/null || echo processing)" ;;
    500) echo "FAIL: worker reported failure: $(cat "$WORK/out.bin")"; exit 1 ;;
    *)   echo "  [${elapsed}s] HTTP ${CODE}" ;;
  esac
  sleep 15; elapsed=$((elapsed + 15))
done
[ -f "$WORK/output.xlsx" ] || { echo "FAIL: timed out after ${POLL_TIMEOUT}s"; exit 1; }

# ── 6. Tolerant diff vs golden ────────────────────────────────────
echo "→ tolerant diff vs golden"
if python3 "$SERVER_DIR/xlsx_diff.py" "$WORK/golden.xlsx" "$WORK/output.xlsx"; then
  echo "=== verify_prod PASS ==="
  exit 0
else
  echo "=== verify_prod FAIL (diff below threshold) ==="
  exit 1
fi
