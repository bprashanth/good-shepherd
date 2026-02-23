#!/usr/bin/env bash
# Test the server running locally.
# Run from anywhere — all paths are relative to this script's location.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="$SCRIPT_DIR/forms"
SERVER_URL="http://localhost:8070"

# Check if server is reachable
if ! curl -s -o /dev/null -w "" "${SERVER_URL}/api/health" 2>/dev/null; then
  echo "Server is not running at ${SERVER_URL}"
  echo ""
  echo "Start it with:"
  echo "  cd server && uvicorn main:app --host 0.0.0.0 --port 8070 --reload"
  exit 1
fi

PASS=0
FAIL=0

check() {
  local label="$1" expected="$2" actual="$3"
  if [ "$actual" = "$expected" ]; then
    echo "  PASS  $label"
    PASS=$((PASS + 1))
  else
    echo "  FAIL  $label (expected $expected, got $actual)"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== Health check ==="
echo "  curl -s -o /dev/null -w '%{http_code}' '${SERVER_URL}/api/health'"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${SERVER_URL}/api/health")
check "GET /api/health → 200" "200" "$STATUS"

echo ""
echo "=== JSON → Excel (no Textract) ==="
for f in 000_layout.json 001_layout.json 002_layout.json; do
  if [ -f "$DATA_DIR/$f" ]; then
    OUT="/tmp/test_local_${f%.json}.xlsx"
    echo "  curl -s -X POST '${SERVER_URL}/api/upload/json' -H 'Content-Type: application/json' -d @${DATA_DIR}/${f} -o $OUT"
    STATUS=$(curl -s -X POST "${SERVER_URL}/api/upload/json" \
      -H "Content-Type: application/json" \
      -d @"${DATA_DIR}/${f}" \
      -o "$OUT" -w "%{http_code}")
    check "POST /api/upload/json ($f) → 200" "200" "$STATUS"
  fi
done

echo ""
echo "=== Image → Excel (Textract) ==="
if [ -f "$DATA_DIR/handwritten.jpg" ]; then
  echo "  curl -s -X POST '${SERVER_URL}/api/upload' -F 'image=@${DATA_DIR}/handwritten.jpg' -o /tmp/test_local_handwritten.xlsx"
  STATUS=$(curl -s -X POST "${SERVER_URL}/api/upload" \
    -F "image=@${DATA_DIR}/handwritten.jpg" \
    -o /tmp/test_local_handwritten.xlsx -w "%{http_code}")
  check "POST /api/upload (handwritten.jpg) → 200" "200" "$STATUS"
fi

echo ""
echo "=== Sessions endpoint (requires AWS creds for S3) ==="
echo "  curl -s '${SERVER_URL}/api/sessions/ncf' | python3 -m json.tool | head -20"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${SERVER_URL}/api/sessions/ncf")
if [ "$STATUS" = "200" ]; then
  COUNT=$(curl -s "${SERVER_URL}/api/sessions/ncf" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d)} sessions')")
  echo "  PASS  GET /api/sessions/ncf → 200 ($COUNT)"
  PASS=$((PASS + 1))
elif [ "$STATUS" = "500" ]; then
  echo "  SKIP  GET /api/sessions/ncf → 500 (no AWS creds?)"
else
  echo "  FAIL  GET /api/sessions/ncf → $STATUS"
  FAIL=$((FAIL + 1))
fi

echo ""
echo "=== Sites endpoint (requires AWS creds for S3) ==="
echo "  curl -s '${SERVER_URL}/api/sites/ncf' | python3 -m json.tool | head -20"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${SERVER_URL}/api/sites/ncf")
if [ "$STATUS" = "200" ]; then
  echo "  PASS  GET /api/sites/ncf → 200"
  PASS=$((PASS + 1))
elif [ "$STATUS" = "500" ]; then
  echo "  SKIP  GET /api/sites/ncf → 500 (no AWS creds?)"
else
  echo "  FAIL  GET /api/sites/ncf → $STATUS"
  FAIL=$((FAIL + 1))
fi

echo ""
echo "=== Results: ${PASS} passed, ${FAIL} failed ==="
[ "$FAIL" -eq 0 ] || exit 1
