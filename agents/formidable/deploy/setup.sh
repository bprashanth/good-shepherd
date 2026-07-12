#!/usr/bin/env bash
# One-time idempotent infra setup: ECR, IAM, integration + routes on the
# EXISTING form-idable-api API Gateway. Does not create a new gateway or
# a new authorizer — both are shared with form-idable-server.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

echo "=== Setting up infra in ${AWS_REGION} (account ${AWS_ACCOUNT_ID}) ==="

# ── 1. ECR repositories (HTTP handler + worker) ────────────────
for repo in "$ECR_REPO" "$WORKER_ECR_REPO"; do
  echo "→ ECR repository: ${repo}"
  if aws ecr describe-repositories --repository-names "$repo" --region "$AWS_REGION" &>/dev/null; then
    echo "  already exists"
  else
    aws ecr create-repository --repository-name "$repo" --region "$AWS_REGION" --output text
    echo "  created"
  fi
done

# ── 2. IAM role ─────────────────────────────────────────────────
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

echo "→ Inline policy: ${LAMBDA_ROLE_NAME}-policy"
aws iam put-role-policy \
  --role-name "$LAMBDA_ROLE_NAME" \
  --policy-name "${LAMBDA_ROLE_NAME}-policy" \
  --policy-document "file://${SCRIPT_DIR}/lambda-policy.json"
echo "  applied"

ROLE_ARN=$(aws iam get-role --role-name "$LAMBDA_ROLE_NAME" --query 'Role.Arn' --output text)

# ── 3. Existing API Gateway HTTP API ────────────────────────────
echo "→ API Gateway: ${APIGW_NAME} (reuse, not creating)"
APIGW_ID=$(aws apigatewayv2 get-apis --region "$AWS_REGION" \
  --query "Items[?Name=='${APIGW_NAME}'].ApiId | [0]" --output text 2>/dev/null || echo "None")

if [ "$APIGW_ID" = "None" ] || [ -z "$APIGW_ID" ]; then
  echo "  ERROR: API Gateway '${APIGW_NAME}' not found. This script reuses the"
  echo "  existing form-idable-api gateway and does not create one."
  exit 1
fi
echo "  found: ${APIGW_ID}"

# ── 4. Existing cognito-jwt authorizer ──────────────────────────
echo "→ JWT authorizer: cognito-jwt (reuse, not creating)"
AUTH_ID=$(aws apigatewayv2 get-authorizers --api-id "$APIGW_ID" --region "$AWS_REGION" \
  --query "Items[?Name=='cognito-jwt'].AuthorizerId | [0]" --output text 2>/dev/null || echo "None")

if [ "$AUTH_ID" = "None" ] || [ -z "$AUTH_ID" ]; then
  echo "  ERROR: authorizer 'cognito-jwt' not found on ${APIGW_NAME}."
  exit 1
fi
echo "  found: ${AUTH_ID}"

# ── 4b. S3 jobs bucket ──────────────────────────────────────────
echo "→ S3 bucket: ${JOBS_BUCKET}"
if aws s3api head-bucket --bucket "$JOBS_BUCKET" --region "$AWS_REGION" &>/dev/null; then
  echo "  already exists"
else
  echo "  ERROR: bucket ${JOBS_BUCKET} does not exist — create it first with:"
  echo "    aws s3 mb s3://${JOBS_BUCKET} --region ${AWS_REGION}"
  exit 1
fi

# ── 4c. DynamoDB table ──────────────────────────────────────────
echo "→ DynamoDB table: ${DYNAMO_TABLE}"
if aws dynamodb describe-table --table-name "$DYNAMO_TABLE" --region "$AWS_REGION" &>/dev/null; then
  echo "  already exists"
else
  aws dynamodb create-table \
    --table-name "$DYNAMO_TABLE" \
    --attribute-definitions \
      AttributeName=user_id,AttributeType=S \
      AttributeName=job_id,AttributeType=S \
    --key-schema \
      AttributeName=user_id,KeyType=HASH \
      AttributeName=job_id,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region "$AWS_REGION" \
    --output text >/dev/null
  echo "  created (PAY_PER_REQUEST)"
  echo "  waiting for table to become ACTIVE..."
  aws dynamodb wait table-exists --table-name "$DYNAMO_TABLE" --region "$AWS_REGION"
  echo "  active"
fi

# ── 5. Lambda integration (HTTP handler) ────────────────────────
echo "→ Lambda integration"
LAMBDA_ARN="arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:${LAMBDA_FUNCTION}"
INTEG_ID=$(aws apigatewayv2 get-integrations --api-id "$APIGW_ID" --region "$AWS_REGION" \
  --query "Items[?IntegrationUri=='${LAMBDA_ARN}'].IntegrationId | [0]" --output text 2>/dev/null || echo "None")

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
# Vision routes (legacy + new extract)
create_route "GET /vision/health"         "false"
create_route "POST /vision/extract"       "true"
create_route "GET /vision/jobs/{job_id}"  "true"
# API routes (dashboard + review)
create_route "GET /api/jobs"                          "true"
create_route "GET /api/jobs/{job_id}/status"          "true"
create_route "GET /api/jobs/{job_id}/manifest"        "true"
create_route "GET /api/jobs/{job_id}/pages/{filename}" "true"
create_route "GET /api/jobs/{job_id}/crops/{filename}" "true"
create_route "GET /api/jobs/{job_id}/xlsx"             "true"
create_route "GET /api/jobs/{job_id}/progress"        "true"
create_route "POST /api/jobs/{job_id}/start"          "true"
create_route "POST /api/jobs/{job_id}/submit"         "true"
create_route "POST /api/jobs/{job_id}/rerun"          "true"
create_route "DELETE /api/jobs/{job_id}"              "true"

# ── 7. Stage (prod, shared, should already exist) ────────────────
echo "→ Stage: prod"
STAGE_EXISTS=$(aws apigatewayv2 get-stages --api-id "$APIGW_ID" --region "$AWS_REGION" \
  --query "Items[?StageName=='prod'].StageName | [0]" --output text 2>/dev/null || echo "None")

if [ "$STAGE_EXISTS" = "None" ] || [ -z "$STAGE_EXISTS" ]; then
  echo "  ERROR: stage 'prod' not found on ${APIGW_NAME}. Expected it to already exist."
  exit 1
fi
echo "  exists"

# ── 8. Fargate infrastructure ────────────────────────────────────

# 8a. ECS task execution role (standard — allows ECS to pull ECR + push CW logs)
echo "→ ECS task execution role: ecsTaskExecutionRole"
if aws iam get-role --role-name ecsTaskExecutionRole &>/dev/null; then
  echo "  already exists"
else
  aws iam create-role --role-name ecsTaskExecutionRole \
    --assume-role-policy-document "file://${SCRIPT_DIR}/fargate-trust-policy.json" \
    --output text >/dev/null
  aws iam attach-role-policy --role-name ecsTaskExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
  echo "  created"
  sleep 5
fi
EXEC_ROLE_ARN=$(aws iam get-role --role-name ecsTaskExecutionRole \
  --query 'Role.Arn' --output text)

# 8b. Fargate task role (S3 + Secrets Manager + CloudWatch for the running container)
echo "→ Fargate task role: ${FARGATE_TASK_ROLE}"
if aws iam get-role --role-name "$FARGATE_TASK_ROLE" &>/dev/null; then
  echo "  already exists"
else
  aws iam create-role --role-name "$FARGATE_TASK_ROLE" \
    --assume-role-policy-document "file://${SCRIPT_DIR}/fargate-trust-policy.json" \
    --output text >/dev/null
  echo "  created"
  sleep 5
fi
aws iam put-role-policy \
  --role-name "$FARGATE_TASK_ROLE" \
  --policy-name "${FARGATE_TASK_ROLE}-policy" \
  --policy-document "file://${SCRIPT_DIR}/fargate-task-policy.json"
TASK_ROLE_ARN=$(aws iam get-role --role-name "$FARGATE_TASK_ROLE" \
  --query 'Role.Arn' --output text)
echo "  policy applied"

# 8c. CloudWatch log group
echo "→ CloudWatch log group: ${FARGATE_LOG_GROUP}"
if aws logs describe-log-groups --log-group-name-prefix "$FARGATE_LOG_GROUP" \
    --query "logGroups[?logGroupName=='${FARGATE_LOG_GROUP}'].logGroupName" \
    --output text --region "$AWS_REGION" | grep -q .; then
  echo "  already exists"
else
  aws logs create-log-group --log-group-name "$FARGATE_LOG_GROUP" --region "$AWS_REGION"
  aws logs put-retention-policy --log-group-name "$FARGATE_LOG_GROUP" \
    --retention-in-days 7 --region "$AWS_REGION"
  echo "  created (7-day retention)"
fi

# 8d. Register initial Fargate task definition
echo "→ Fargate task definition: ${FARGATE_TASK_DEF}"
aws ecs register-task-definition --region "$AWS_REGION" --cli-input-json "$(cat <<JSON
{
  "family": "${FARGATE_TASK_DEF}",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "${FARGATE_CPU}",
  "memory": "${FARGATE_MEMORY}",
  "executionRoleArn": "${EXEC_ROLE_ARN}",
  "taskRoleArn": "${TASK_ROLE_ARN}",
  "containerDefinitions": [
    {
      "name": "worker",
      "image": "${WORKER_ECR_URI}:latest",
      "essential": true,
      "environment": [
        {"name": "CODEX_SECRET_NAME", "value": "${SECRET_NAME}"},
        {"name": "JOBS_BUCKET",       "value": "${JOBS_BUCKET}"},
        {"name": "AWS_REGION",        "value": "${AWS_REGION}"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group":         "${FARGATE_LOG_GROUP}",
          "awslogs-region":        "${AWS_REGION}",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
JSON
)" --query 'taskDefinition.taskDefinitionArn' --output text
echo "  registered"

# ── 9. Write outputs ─────────────────────────────────────────────
APIGW_URL="https://${APIGW_ID}.execute-api.${AWS_REGION}.amazonaws.com/prod"
cat > "$SCRIPT_DIR/outputs.env" <<EOF
APIGW_ID=${APIGW_ID}
APIGW_URL=${APIGW_URL}
LAMBDA_ARN=${LAMBDA_ARN}
ROLE_ARN=${ROLE_ARN}
AUTH_ID=${AUTH_ID}
INTEG_ID=${INTEG_ID}
EXEC_ROLE_ARN=${EXEC_ROLE_ARN}
TASK_ROLE_ARN=${TASK_ROLE_ARN}
EOF

echo ""
echo "=== Setup complete ==="
echo "API Gateway URL: ${APIGW_URL}"
echo "Fargate task def: ${FARGATE_TASK_DEF}"
echo "Outputs written to: ${SCRIPT_DIR}/outputs.env"
