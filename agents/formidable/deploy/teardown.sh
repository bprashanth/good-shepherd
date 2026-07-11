#!/usr/bin/env bash
# Tear down all AWS resources created by setup.sh + deploy.sh for this component.
#
# Deletes:
#   - The /vision/health and /vision/extract routes + this component's
#     integration on the shared form-idable-api gateway
#   - Lambda function (also removes reserved concurrency)
#   - ECR repository named ${APP_NAME} and all images within it
#   - IAM role ${APP_NAME}-role and its inline policy
#   - CloudWatch log group /aws/lambda/${APP_NAME}
#
# Does NOT delete:
#   - The shared form-idable-api API Gateway, cognito-jwt authorizer, or
#     prod stage (used by form-idable-server)
#   - Any other component's resources
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

DRY_RUN=false
for arg in "$@"; do
  [ "$arg" = "--dry-run" ] && DRY_RUN=true
done

if [ "$DRY_RUN" = true ]; then
  echo "=== DRY RUN — nothing will be deleted ==="
else
  echo "=== Teardown: ${APP_NAME} (${AWS_REGION}) ==="
fi
echo ""

handle() {
  local label="$1" exists="$2"
  shift 2
  if [ "$exists" = "true" ]; then
    if [ "$DRY_RUN" = true ]; then
      echo "  [would delete] ${label}"
    else
      echo "→ ${label}"
      "$@"
      echo "  deleted"
    fi
  else
    if [ "$DRY_RUN" = true ]; then
      echo "  [not found]    ${label}"
    else
      echo "→ ${label} — not found, skipping"
    fi
  fi
}

# ── 1. API Gateway routes + integration (this component only) ──────────────
APIGW_ID=$(aws apigatewayv2 get-apis --region "$AWS_REGION" \
  --query "Items[?Name=='${APIGW_NAME}'].ApiId | [0]" --output text 2>/dev/null || echo "None")

if [ "$APIGW_ID" != "None" ] && [ -n "$APIGW_ID" ]; then
  for ROUTE_KEY in "GET /vision/health" "POST /vision/extract"; do
    ROUTE_ID=$(aws apigatewayv2 get-routes --api-id "$APIGW_ID" --region "$AWS_REGION" \
      --query "Items[?RouteKey=='${ROUTE_KEY}'].RouteId | [0]" --output text 2>/dev/null || echo "None")
    if [ "$ROUTE_ID" != "None" ] && [ -n "$ROUTE_ID" ]; then
      handle "Route: ${ROUTE_KEY}" "true" \
        aws apigatewayv2 delete-route --api-id "$APIGW_ID" --route-id "$ROUTE_ID" --region "$AWS_REGION"
    else
      handle "Route: ${ROUTE_KEY}" "false"
    fi
  done

  LAMBDA_ARN="arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:${LAMBDA_FUNCTION}"
  INTEG_ID=$(aws apigatewayv2 get-integrations --api-id "$APIGW_ID" --region "$AWS_REGION" \
    --query "Items[?IntegrationUri=='${LAMBDA_ARN}'].IntegrationId | [0]" --output text 2>/dev/null || echo "None")
  if [ "$INTEG_ID" != "None" ] && [ -n "$INTEG_ID" ]; then
    handle "Integration: ${INTEG_ID} (this component)" "true" \
      aws apigatewayv2 delete-integration --api-id "$APIGW_ID" --integration-id "$INTEG_ID" --region "$AWS_REGION"
  else
    handle "Integration (this component)" "false"
  fi
else
  echo "→ API Gateway ${APIGW_NAME} not found, skipping route/integration cleanup"
fi

# ── 2. Lambda function ─────────────────────────────────────────────────────
LAMBDA_EXISTS=false
aws lambda get-function --function-name "$LAMBDA_FUNCTION" \
  --region "$AWS_REGION" &>/dev/null && LAMBDA_EXISTS=true || true

delete_lambda() {
  aws lambda delete-function \
    --function-name "$LAMBDA_FUNCTION" \
    --region "$AWS_REGION"
}
handle "Lambda function: ${LAMBDA_FUNCTION} (+ reserved concurrency)" \
  "$LAMBDA_EXISTS" delete_lambda

# ── 3. ECR repository ──────────────────────────────────────────────────────
ECR_EXISTS=false
aws ecr describe-repositories --repository-names "$ECR_REPO" \
  --region "$AWS_REGION" &>/dev/null && ECR_EXISTS=true || true

delete_ecr() {
  aws ecr delete-repository \
    --repository-name "$ECR_REPO" \
    --force \
    --region "$AWS_REGION" \
    --output text >/dev/null
}
handle "ECR repository: ${ECR_REPO}" \
  "$ECR_EXISTS" delete_ecr

# ── 4. IAM role + inline policy ───────────────────────────────────────────
IAM_EXISTS=false
aws iam get-role --role-name "$LAMBDA_ROLE_NAME" &>/dev/null && IAM_EXISTS=true || true

delete_iam() {
  aws iam delete-role-policy \
    --role-name "$LAMBDA_ROLE_NAME" \
    --policy-name "${LAMBDA_ROLE_NAME}-policy" 2>/dev/null || true
  aws iam delete-role --role-name "$LAMBDA_ROLE_NAME"
}
handle "IAM role: ${LAMBDA_ROLE_NAME} (+ inline policy)" \
  "$IAM_EXISTS" delete_iam

# ── 5. CloudWatch log group ───────────────────────────────────────────────
LOG_GROUP="/aws/lambda/${LAMBDA_FUNCTION}"
CW_EXISTS=false
FOUND=$(aws logs describe-log-groups \
  --log-group-name-prefix "$LOG_GROUP" \
  --region "$AWS_REGION" \
  --query "logGroups[?logGroupName=='${LOG_GROUP}'] | length(@)" \
  --output text 2>/dev/null || echo "0")
[ "$FOUND" = "1" ] && CW_EXISTS=true

delete_cw() {
  aws logs delete-log-group \
    --log-group-name "$LOG_GROUP" \
    --region "$AWS_REGION"
}
handle "CloudWatch log group: ${LOG_GROUP}" \
  "$CW_EXISTS" delete_cw

echo ""
echo "  Will NOT touch: shared API Gateway, cognito-jwt authorizer, prod stage"

if [ "$DRY_RUN" = true ]; then
  echo ""
  echo "=== Dry run complete ==="
  exit 0
fi

rm -f "$SCRIPT_DIR/outputs.env"

echo ""
echo "=== Teardown complete ==="
