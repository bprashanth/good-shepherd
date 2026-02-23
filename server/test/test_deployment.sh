#!/usr/bin/env bash
# End-to-end test of the deployed Lambda API.
# Ensures test user exists, verifies auth is enforced, then tests endpoints.
#
# Run from anywhere — all paths are relative to this script's location.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/../deploy" && pwd)"
DATA_DIR="$SCRIPT_DIR/forms"

echo "Loading config from: $DEPLOY_DIR/config.sh"
source "$DEPLOY_DIR/config.sh"

echo "Loading outputs from: $DEPLOY_DIR/outputs.env"
source "$DEPLOY_DIR/outputs.env"

echo "  APIGW_URL=$APIGW_URL"
echo "  COGNITO_POOL_ID=$COGNITO_POOL_ID"
echo "  COGNITO_CLIENT_ID=$COGNITO_CLIENT_ID"
echo "  AUTH_CONFIG_URL=$AUTH_CONFIG_URL"
echo ""

PASS_COUNT=0
FAIL_COUNT=0

check() {
  local label="$1" expected="$2" actual="$3"
  if [ "$actual" = "$expected" ]; then
    echo "  PASS  $label"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  FAIL  $label (expected $expected, got $actual)"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

# ── 1. Ensure test user ─────────────────────────────────────────
echo "=== 1. Ensure test user exists ==="
"$DEPLOY_DIR/add-user.sh"

# ── 2. Unauthenticated access blocked ───────────────────────────
echo ""
echo "=== 2. Verify unauthenticated access is blocked ==="

echo "  curl -s -o /dev/null -w '%{http_code}' -X POST '${APIGW_URL}/api/upload'"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${APIGW_URL}/api/upload")
check "POST /api/upload without token → 401" "401" "$STATUS"

echo "  curl -s -o /dev/null -w '%{http_code}' -X POST '${APIGW_URL}/api/upload/json' -H 'Content-Type: application/json' -d '{}'"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${APIGW_URL}/api/upload/json" \
  -H "Content-Type: application/json" -d '{}')
check "POST /api/upload/json without token → 401" "401" "$STATUS"

# ── 3. Health endpoint ──────────────────────────────────────────
echo ""
echo "=== 3. Verify health endpoint (no auth) ==="

echo "  curl -s -o /dev/null -w '%{http_code}' '${APIGW_URL}/api/health'"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${APIGW_URL}/api/health")
check "GET /api/health → 200" "200" "$STATUS"

# ── 4. Get Cognito token ────────────────────────────────────────
echo ""
echo "=== 4. Get Cognito token ==="

source "$DEPLOY_DIR/test-credentials.env"

echo "  aws cognito-idp initiate-auth \\"
echo "    --client-id $COGNITO_CLIENT_ID \\"
echo "    --auth-flow USER_PASSWORD_AUTH \\"
echo "    --auth-parameters USERNAME=${TEST_USERNAME},PASSWORD=*** \\"
echo "    --region $AWS_REGION \\"
echo "    --query 'AuthenticationResult.IdToken' --output text"

TOKEN=$(aws cognito-idp initiate-auth \
  --client-id "$COGNITO_CLIENT_ID" \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters "USERNAME=${TEST_USERNAME},PASSWORD=${TEST_PASSWORD}" \
  --region "$AWS_REGION" \
  --query 'AuthenticationResult.IdToken' --output text 2>&1) || true

if [ -z "$TOKEN" ] || [ "$TOKEN" = "None" ] || echo "$TOKEN" | grep -q "error\|Error"; then
  echo "  FAIL  Could not get token: $TOKEN"
  FAIL_COUNT=$((FAIL_COUNT + 1))
  echo ""
  echo "=== Results: ${PASS_COUNT} passed, ${FAIL_COUNT} failed ==="
  exit 1
else
  echo "  PASS  Token obtained (${#TOKEN} chars)"
  PASS_COUNT=$((PASS_COUNT + 1))
fi

# ── 5. Authenticated JSON upload ────────────────────────────────
echo ""
echo "=== 5. Authenticated JSON upload ==="

echo "  curl -s -X POST '${APIGW_URL}/api/upload/json' -H 'Authorization: Bearer <token>' -H 'Content-Type: application/json' -d @${DATA_DIR}/000_layout.json -o /tmp/lambda_test.xlsx"
STATUS=$(curl -s -X POST "${APIGW_URL}/api/upload/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d @"${DATA_DIR}/000_layout.json" \
  -o /tmp/lambda_test.xlsx -w "%{http_code}")
check "POST /api/upload/json with token → 200" "200" "$STATUS"

# ── 6. Authenticated image upload ───────────────────────────────
echo ""
echo "=== 6. Authenticated image upload (Textract) ==="

echo "  curl -s -X POST '${APIGW_URL}/api/upload' -H 'Authorization: Bearer <token>' -F 'image=@${DATA_DIR}/handwritten.jpg' -o /tmp/lambda_live.xlsx"
STATUS=$(curl -s -X POST "${APIGW_URL}/api/upload" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "image=@${DATA_DIR}/handwritten.jpg" \
  -o /tmp/lambda_live.xlsx -w "%{http_code}")
check "POST /api/upload with token → 200" "200" "$STATUS"

# ── 7. Authenticated sessions endpoint ────────────────────────
echo ""
echo "=== 7. Authenticated sessions endpoint ==="

echo "  curl -s '${APIGW_URL}/api/sessions/ncf' -H 'Authorization: Bearer <token>' | python3 -m json.tool | head -20"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${APIGW_URL}/api/sessions/ncf" \
  -H "Authorization: Bearer ${TOKEN}")
check "GET /api/sessions/ncf with token → 200" "200" "$STATUS"

# ── 8. Unauthenticated sessions blocked ───────────────────────
echo ""
echo "=== 8. Verify unauthenticated sessions access is blocked ==="

echo "  curl -s -o /dev/null -w '%{http_code}' '${APIGW_URL}/api/sessions/ncf'"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${APIGW_URL}/api/sessions/ncf")
check "GET /api/sessions/ncf without token → 401" "401" "$STATUS"

echo ""
echo "=== Results: ${PASS_COUNT} passed, ${FAIL_COUNT} failed ==="
[ "$FAIL_COUNT" -eq 0 ] || exit 1
