#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

aws ecr describe-repositories --repository-names "$HIGH_WORKER_ECR_REPO" --region "$AWS_REGION" >/dev/null 2>&1 || \
  aws ecr create-repository --repository-name "$HIGH_WORKER_ECR_REPO" --region "$AWS_REGION" >/dev/null

if ! aws iam get-role --role-name "$HIGH_FARGATE_TASK_ROLE" >/dev/null 2>&1; then
  aws iam create-role --role-name "$HIGH_FARGATE_TASK_ROLE" \
    --assume-role-policy-document "file://${SCRIPT_DIR}/fargate-trust-policy.json" >/dev/null
  sleep 5
fi
aws iam put-role-policy --role-name "$HIGH_FARGATE_TASK_ROLE" \
  --policy-name "${HIGH_FARGATE_TASK_ROLE}-policy" \
  --policy-document "file://${SCRIPT_DIR}/fargate-high-task-policy.json"
aws iam put-role-policy --role-name "$LAMBDA_ROLE_NAME" \
  --policy-name "${LAMBDA_ROLE_NAME}-policy" \
  --policy-document "file://${SCRIPT_DIR}/lambda-policy.json"

aws logs describe-log-groups --log-group-name-prefix "$HIGH_FARGATE_LOG_GROUP" \
  --query "logGroups[?logGroupName=='${HIGH_FARGATE_LOG_GROUP}'].logGroupName" \
  --output text --region "$AWS_REGION" | grep -q . || {
    aws logs create-log-group --log-group-name "$HIGH_FARGATE_LOG_GROUP" --region "$AWS_REGION"
    aws logs put-retention-policy --log-group-name "$HIGH_FARGATE_LOG_GROUP" --retention-in-days 14 --region "$AWS_REGION"
  }

APIGW_ID=$(aws apigatewayv2 get-apis --region "$AWS_REGION" \
  --query "Items[?Name=='${APIGW_NAME}'].ApiId | [0]" --output text)
INTEG_ID=$(aws apigatewayv2 get-integrations --api-id "$APIGW_ID" --region "$AWS_REGION" \
  --query "Items[?contains(IntegrationUri, '${LAMBDA_FUNCTION}')].IntegrationId | [0]" --output text)
AUTH_ID=$(aws apigatewayv2 get-authorizers --api-id "$APIGW_ID" --region "$AWS_REGION" \
  --query "Items[?Name=='cognito-jwt'].AuthorizerId | [0]" --output text)
for route in 'GET /api/jobs/{job_id}/review-manifest' 'GET /api/jobs/{job_id}/analytics'; do
  existing=$(aws apigatewayv2 get-routes --api-id "$APIGW_ID" --region "$AWS_REGION" \
    --query "Items[?RouteKey=='${route}'].RouteId | [0]" --output text)
  if [ "$existing" = "None" ] || [ -z "$existing" ]; then
    aws apigatewayv2 create-route --api-id "$APIGW_ID" --route-key "$route" \
      --target "integrations/${INTEG_ID}" --authorization-type JWT --authorizer-id "$AUTH_ID" \
      --region "$AWS_REGION" >/dev/null
  fi
done
echo "High-effort infrastructure ready; low worker was not modified."
