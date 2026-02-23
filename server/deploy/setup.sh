#!/usr/bin/env bash
# One-time idempotent infra setup: ECR, IAM, API Gateway + JWT authorizer.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

echo "=== Setting up infra in ${AWS_REGION} (account ${AWS_ACCOUNT_ID}) ==="

# ── 0. Validate Cognito config ──────────────────────────────────
# Catch auth misconfigurations here rather than mysterious 401s at test time.
echo "→ Validating Cognito config"
COGNITO_WARNINGS=0

# 0a. auth_config.json reachable and parsed?
if [ -z "$COGNITO_POOL_ID" ] || [ -z "$COGNITO_CLIENT_ID" ]; then
  echo "  ERROR: COGNITO_POOL_ID or COGNITO_CLIENT_ID is empty."
  echo "    Could not fetch or parse: ${AUTH_CONFIG_URL}"
  echo "    Fix: upload a valid auth_config.json to S3, or set env vars manually:"
  echo "      export COGNITO_POOL_ID=ap-south-1_XXXXXXXXX"
  echo "      export COGNITO_CLIENT_ID=abcdef123456"
  exit 1
fi
echo "  auth_config.json: pool=${COGNITO_POOL_ID} client=${COGNITO_CLIENT_ID}"

# 0b. Pool exists in this account?
if ! aws cognito-idp describe-user-pool \
    --user-pool-id "$COGNITO_POOL_ID" --region "$AWS_REGION" &>/dev/null; then
  echo "  ERROR: User pool ${COGNITO_POOL_ID} not found in account ${AWS_ACCOUNT_ID} (${AWS_REGION})."
  echo "    The pool ID in auth_config.json does not exist in this AWS account."
  echo "    Fix: update auth_config.json at ${AUTH_CONFIG_URL}"
  echo "         or override: export COGNITO_POOL_ID=<correct-pool-id>"
  exit 1
fi
echo "  pool ${COGNITO_POOL_ID} exists"

# 0c. Client exists and has required auth flows?
CLIENT_JSON=$(aws cognito-idp describe-user-pool-client \
  --user-pool-id "$COGNITO_POOL_ID" \
  --client-id "$COGNITO_CLIENT_ID" \
  --region "$AWS_REGION" \
  --output json 2>&1) || {
  echo "  ERROR: Client ${COGNITO_CLIENT_ID} not found in pool ${COGNITO_POOL_ID}."
  echo "    Fix: update auth_config.json or override: export COGNITO_CLIENT_ID=<correct-id>"
  exit 1
}
echo "  client ${COGNITO_CLIENT_ID} exists"

# Check ExplicitAuthFlows — we need USER_PASSWORD_AUTH for CLI test scripts
# and USER_SRP_AUTH for the PWA.
FLOWS=$(echo "$CLIENT_JSON" | python3 -c "
import sys, json
flows = json.load(sys.stdin)['UserPoolClient'].get('ExplicitAuthFlows', [])
print(' '.join(flows))
" 2>/dev/null || echo "")

check_flow() {
  local flow="$1" purpose="$2"
  if echo "$FLOWS" | grep -qw "$flow"; then
    echo "  $flow enabled ($purpose)"
  else
    echo "  WARNING: $flow not enabled on client ${COGNITO_CLIENT_ID}."
    echo "    Needed for: $purpose"
    echo "    Fix: aws cognito-idp update-user-pool-client \\"
    echo "           --user-pool-id ${COGNITO_POOL_ID} \\"
    echo "           --client-id ${COGNITO_CLIENT_ID} \\"
    echo "           --explicit-auth-flows ALLOW_USER_SRP_AUTH ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \\"
    echo "           --region ${AWS_REGION}"
    COGNITO_WARNINGS=$((COGNITO_WARNINGS + 1))
  fi
}

check_flow "ALLOW_USER_PASSWORD_AUTH" "CLI test scripts (test_deployment.sh, add-user.sh)"
check_flow "ALLOW_USER_SRP_AUTH" "PWA / Flutter app login"

# 0d. If JWT authorizer already exists, verify issuer/audience match.
EXISTING_AUTH_ID=$(aws apigatewayv2 get-apis --region "$AWS_REGION" \
  --query "Items[?Name=='${APIGW_NAME}'].ApiId | [0]" --output text 2>/dev/null || echo "None")

if [ "$EXISTING_AUTH_ID" != "None" ] && [ -n "$EXISTING_AUTH_ID" ]; then
  AUTH_CFG=$(aws apigatewayv2 get-authorizers --api-id "$EXISTING_AUTH_ID" --region "$AWS_REGION" \
    --query "Items[?Name=='cognito-jwt'] | [0]" --output json 2>/dev/null || echo "{}")

  if [ "$AUTH_CFG" != "{}" ] && [ "$AUTH_CFG" != "null" ] && [ -n "$AUTH_CFG" ]; then
    EXISTING_ISSUER=$(echo "$AUTH_CFG" | python3 -c "import sys,json; print(json.load(sys.stdin).get('JwtConfiguration',{}).get('Issuer',''))" 2>/dev/null)
    EXISTING_AUDIENCE=$(echo "$AUTH_CFG" | python3 -c "import sys,json; a=json.load(sys.stdin).get('JwtConfiguration',{}).get('Audience',[]); print(a[0] if a else '')" 2>/dev/null)

    if [ "$EXISTING_ISSUER" != "$COGNITO_ISSUER" ]; then
      echo "  WARNING: JWT authorizer issuer mismatch!"
      echo "    authorizer has: $EXISTING_ISSUER"
      echo "    config.sh has:  $COGNITO_ISSUER"
      echo "    Tokens will be rejected. Delete the authorizer and re-run setup.sh,"
      echo "    or update auth_config.json to match."
      COGNITO_WARNINGS=$((COGNITO_WARNINGS + 1))
    fi

    if [ "$EXISTING_AUDIENCE" != "$COGNITO_CLIENT_ID" ]; then
      echo "  WARNING: JWT authorizer audience mismatch!"
      echo "    authorizer has: $EXISTING_AUDIENCE"
      echo "    config.sh has:  $COGNITO_CLIENT_ID"
      echo "    Tokens will be rejected. Delete the authorizer and re-run setup.sh,"
      echo "    or update auth_config.json to match."
      COGNITO_WARNINGS=$((COGNITO_WARNINGS + 1))
    fi

    if [ "$EXISTING_ISSUER" = "$COGNITO_ISSUER" ] && [ "$EXISTING_AUDIENCE" = "$COGNITO_CLIENT_ID" ]; then
      echo "  JWT authorizer issuer/audience match config ✓"
    fi
  fi
fi

if [ "$COGNITO_WARNINGS" -gt 0 ]; then
  echo ""
  echo "  ⚠ ${COGNITO_WARNINGS} warning(s) above. Auth may fail at test time."
  echo "  Continuing with setup — fix warnings before running tests."
  echo ""
fi

# ── 1. ECR repository ──────────────────────────────────────────
echo "→ ECR repository: ${ECR_REPO}"
if aws ecr describe-repositories --repository-names "$ECR_REPO" --region "$AWS_REGION" &>/dev/null; then
  echo "  already exists"
else
  aws ecr create-repository --repository-name "$ECR_REPO" --region "$AWS_REGION" --output text
  echo "  created"
fi

# ── 2. IAM role ─────────────────────────────────────────────────
ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${LAMBDA_ROLE_NAME}"
echo "→ IAM role: ${LAMBDA_ROLE_NAME}"
if aws iam get-role --role-name "$LAMBDA_ROLE_NAME" &>/dev/null; then
  echo "  already exists"
else
  aws iam create-role \
    --role-name "$LAMBDA_ROLE_NAME" \
    --assume-role-policy-document "file://${SCRIPT_DIR}/trust-policy.json" \
    --output text
  echo "  created"
  echo "  waiting 10s for IAM propagation..."
  sleep 10
fi

echo "→ Inline policy: form-idable-lambda-policy"
aws iam put-role-policy \
  --role-name "$LAMBDA_ROLE_NAME" \
  --policy-name "form-idable-lambda-policy" \
  --policy-document "file://${SCRIPT_DIR}/lambda-policy.json"
echo "  applied"

ROLE_ARN=$(aws iam get-role --role-name "$LAMBDA_ROLE_NAME" --query 'Role.Arn' --output text)

# ── 3. API Gateway HTTP API ─────────────────────────────────────
echo "→ API Gateway: ${APIGW_NAME}"
APIGW_ID=$(aws apigatewayv2 get-apis --region "$AWS_REGION" \
  --query "Items[?Name=='${APIGW_NAME}'].ApiId | [0]" --output text 2>/dev/null || echo "None")

if [ "$APIGW_ID" = "None" ] || [ -z "$APIGW_ID" ]; then
  APIGW_ID=$(aws apigatewayv2 create-api \
    --name "$APIGW_NAME" \
    --protocol-type HTTP \
    --cors-configuration "AllowOrigins=*,AllowMethods=GET,POST,OPTIONS,AllowHeaders=content-type,authorization,ExposeHeaders=X-Form-Summary,MaxAge=3600" \
    --region "$AWS_REGION" \
    --query 'ApiId' --output text)
  echo "  created: ${APIGW_ID}"
else
  echo "  already exists: ${APIGW_ID}"
fi

# ── 4. JWT authorizer ───────────────────────────────────────────
echo "→ JWT authorizer"
AUTH_ID=$(aws apigatewayv2 get-authorizers --api-id "$APIGW_ID" --region "$AWS_REGION" \
  --query "Items[?Name=='cognito-jwt'].AuthorizerId | [0]" --output text 2>/dev/null || echo "None")

if [ "$AUTH_ID" = "None" ] || [ -z "$AUTH_ID" ]; then
  AUTH_ID=$(aws apigatewayv2 create-authorizer \
    --api-id "$APIGW_ID" \
    --name "cognito-jwt" \
    --authorizer-type JWT \
    --identity-source '$request.header.Authorization' \
    --jwt-configuration "Issuer=${COGNITO_ISSUER},Audience=${COGNITO_CLIENT_ID}" \
    --region "$AWS_REGION" \
    --query 'AuthorizerId' --output text)
  echo "  created: ${AUTH_ID}"
else
  echo "  already exists: ${AUTH_ID}"
fi

# ── 5. Lambda integration ───────────────────────────────────────
echo "→ Lambda integration"
LAMBDA_ARN="arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:${LAMBDA_FUNCTION}"
INTEG_ID=$(aws apigatewayv2 get-integrations --api-id "$APIGW_ID" --region "$AWS_REGION" \
  --query "Items[?IntegrationType=='AWS_PROXY'].IntegrationId | [0]" --output text 2>/dev/null || echo "None")

if [ "$INTEG_ID" = "None" ] || [ -z "$INTEG_ID" ]; then
  INTEG_ID=$(aws apigatewayv2 create-integration \
    --api-id "$APIGW_ID" \
    --integration-type AWS_PROXY \
    --integration-uri "$LAMBDA_ARN" \
    --payload-format-version "2.0" \
    --region "$AWS_REGION" \
    --query 'IntegrationId' --output text)
  echo "  created: ${INTEG_ID}"
else
  echo "  already exists: ${INTEG_ID}"
fi

# ── 6. Routes ────────────────────────────────────────────────────
create_route() {
  local ROUTE_KEY="$1"
  local USE_AUTH="$2"

  local EXISTING
  EXISTING=$(aws apigatewayv2 get-routes --api-id "$APIGW_ID" --region "$AWS_REGION" \
    --query "Items[?RouteKey=='${ROUTE_KEY}'].RouteId | [0]" --output text 2>/dev/null || echo "None")

  if [ "$EXISTING" != "None" ] && [ -n "$EXISTING" ]; then
    echo "  route '${ROUTE_KEY}' already exists"
    return
  fi

  local AUTH_ARGS=""
  if [ "$USE_AUTH" = "true" ]; then
    AUTH_ARGS="--authorization-type JWT --authorizer-id ${AUTH_ID}"
  fi

  aws apigatewayv2 create-route \
    --api-id "$APIGW_ID" \
    --route-key "$ROUTE_KEY" \
    --target "integrations/${INTEG_ID}" \
    $AUTH_ARGS \
    --region "$AWS_REGION" \
    --output text >/dev/null
  echo "  route '${ROUTE_KEY}' created"
}

echo "→ Routes"
create_route "GET /api/health" "false"
create_route "POST /api/{proxy+}" "true"
create_route "GET /api/sessions/{org}" "true"
create_route "GET /api/sites/{org}" "true"

# ── 7. Stage (prod, auto-deploy) ────────────────────────────────
echo "→ Stage: prod"
STAGE_EXISTS=$(aws apigatewayv2 get-stages --api-id "$APIGW_ID" --region "$AWS_REGION" \
  --query "Items[?StageName=='prod'].StageName | [0]" --output text 2>/dev/null || echo "None")

if [ "$STAGE_EXISTS" = "None" ] || [ -z "$STAGE_EXISTS" ]; then
  aws apigatewayv2 create-stage \
    --api-id "$APIGW_ID" \
    --stage-name "prod" \
    --auto-deploy \
    --region "$AWS_REGION" \
    --output text >/dev/null
  echo "  created"
else
  echo "  already exists"
fi

# ── 8. Write outputs ─────────────────────────────────────────────
# Note: Lambda invoke permission is set by push.sh after the function exists.
APIGW_URL="https://${APIGW_ID}.execute-api.${AWS_REGION}.amazonaws.com/prod"
cat > "$SCRIPT_DIR/outputs.env" <<EOF
APIGW_ID=${APIGW_ID}
APIGW_URL=${APIGW_URL}
LAMBDA_ARN=${LAMBDA_ARN}
ROLE_ARN=${ROLE_ARN}
AUTH_ID=${AUTH_ID}
EOF

echo ""
echo "=== Setup complete ==="
echo "API Gateway URL: ${APIGW_URL}"
echo "Outputs written to: ${SCRIPT_DIR}/outputs.env"
