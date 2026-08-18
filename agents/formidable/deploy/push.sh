#!/usr/bin/env bash
# Build and push the shared HTTP handler plus Low worker. Credentials are a
# separate release surface; use deploy_credentials.sh to rotate and verify them.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/config.sh"

if ! docker run --rm --platform linux/amd64 --memory 256m --memory-swap 256m \
  public.ecr.aws/docker/library/busybox:1.36 true >/dev/null 2>&1; then
  echo "ERROR: amd64 emulation is unavailable; refusing a mixed-architecture release." >&2
  exit 1
fi

echo "=== ECR login ==="
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin \
  "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# ── Preserve the current images as rollback points BEFORE overwriting :latest ──
# ECR :latest is mutable and the prior image would otherwise become untagged and
# get GC'd. Retag current :latest → :rollback in each repo so rollback.sh can
# restore it. (No-op on first ever push when :latest doesn't exist yet.)
"$SCRIPT_DIR/_retag.sh" "$ECR_REPO"        latest rollback || true
"$SCRIPT_DIR/_retag.sh" "$WORKER_ECR_REPO" latest rollback || true

echo "=== Build + push HTTP handler image (${IMAGE}, codex ${CODEX_VERSION}) ==="
docker build --platform linux/amd64 --memory 8g \
  --build-arg "CODEX_VERSION=${CODEX_VERSION}" -t "$IMAGE" "$SERVER_DIR"
docker tag "$IMAGE" "${ECR_URI}:latest"
docker push "${ECR_URI}:latest"

echo "=== Build + push worker image (${WORKER_IMAGE}, codex ${CODEX_VERSION}) ==="
docker build --platform linux/amd64 --memory 8g \
  --build-arg "CODEX_VERSION=${CODEX_VERSION}" \
  -f "$SERVER_DIR/Dockerfile.worker" -t "$WORKER_IMAGE" "$SERVER_DIR"
docker tag "$WORKER_IMAGE" "${WORKER_ECR_URI}:latest"
docker push "${WORKER_ECR_URI}:latest"

ROLE_ARN=$(aws iam get-role --role-name "$LAMBDA_ROLE_NAME" --query 'Role.Arn' --output text)

# ── HTTP handler Lambda ────────────────────────────────────────────
echo "=== Lambda: ${LAMBDA_FUNCTION} (HTTP handler) ==="
HTTP_ENV="Variables={JOBS_BUCKET=${JOBS_BUCKET},S3_PREFIX=${S3_PREFIX},DYNAMO_TABLE=${DYNAMO_TABLE},ECS_CLUSTER=${ECS_CLUSTER},FARGATE_TASK=${FARGATE_TASK_DEF},FARGATE_TASK_HIGH=${HIGH_FARGATE_TASK_DEF},ECS_SG_NAME=${ECS_SG_NAME},AWS_LWA_REMOVE_BASE_PATH=/prod}"

if aws lambda get-function --function-name "$LAMBDA_FUNCTION" --region "$AWS_REGION" &>/dev/null; then
  echo "  updating function code..."
  aws lambda update-function-code \
    --function-name "$LAMBDA_FUNCTION" \
    --image-uri "${ECR_URI}:latest" \
    --region "$AWS_REGION" --output text >/dev/null
  aws lambda wait function-updated-v2 --function-name "$LAMBDA_FUNCTION" --region "$AWS_REGION"
else
  echo "  creating function..."
  aws lambda create-function \
    --function-name "$LAMBDA_FUNCTION" \
    --package-type Image \
    --code "ImageUri=${ECR_URI}:latest" \
    --role "$ROLE_ARN" \
    --environment "$HTTP_ENV" \
    --memory-size "$LAMBDA_MEMORY_MB" \
    --timeout "$LAMBDA_TIMEOUT_S" \
    --region "$AWS_REGION" --output text >/dev/null
  aws lambda wait function-active-v2 --function-name "$LAMBDA_FUNCTION" --region "$AWS_REGION"
fi

echo "  updating config..."
aws lambda update-function-configuration \
  --function-name "$LAMBDA_FUNCTION" \
  --environment "$HTTP_ENV" \
  --memory-size "$LAMBDA_MEMORY_MB" \
  --timeout "$LAMBDA_TIMEOUT_S" \
  --region "$AWS_REGION" --output text >/dev/null
aws lambda wait function-updated-v2 --function-name "$LAMBDA_FUNCTION" --region "$AWS_REGION"

echo "  setting reserved concurrency..."
aws lambda put-function-concurrency \
  --function-name "$LAMBDA_FUNCTION" \
  --reserved-concurrent-executions "$RESERVED_CONCURRENCY" \
  --region "$AWS_REGION" --output text >/dev/null

# ── Fargate task definition (new revision pointing to just-pushed image) ──
echo "=== Fargate task definition: ${FARGATE_TASK_DEF} ==="
EXEC_ROLE_ARN=$(aws iam get-role --role-name ecsTaskExecutionRole \
  --query 'Role.Arn' --output text 2>/dev/null || echo "")
TASK_ROLE_ARN=$(aws iam get-role --role-name "$FARGATE_TASK_ROLE" \
  --query 'Role.Arn' --output text 2>/dev/null || echo "")

if [ -z "$EXEC_ROLE_ARN" ] || [ -z "$TASK_ROLE_ARN" ]; then
  echo "  ERROR: IAM roles not found — run setup.sh first"
  exit 1
fi

TASK_DEF_ARN=$(aws ecs register-task-definition --region "$AWS_REGION" --cli-input-json "$(cat <<JSON
{
  "family": "${FARGATE_TASK_DEF}",
  "runtimePlatform":{"cpuArchitecture":"X86_64","operatingSystemFamily":"LINUX"},
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
        {"name": "CODEX_SECRET_NAME",       "value": "${SECRET_NAME}"},
        {"name": "JOBS_BUCKET",             "value": "${JOBS_BUCKET}"},
        {"name": "AWS_REGION",              "value": "${AWS_REGION}"},
        {"name": "NOTIFICATION_FROM_EMAIL", "value": "${NOTIFICATION_FROM_EMAIL}"},
        {"name": "PWA_URL",                 "value": "${PWA_URL}"}
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
)" --query 'taskDefinition.taskDefinitionArn' --output text)
echo "  registered: ${TASK_DEF_ARN}"

# ── API Gateway invoke permission ──────────────────────────────────
if [ -f "$SCRIPT_DIR/outputs.env" ]; then
  source "$SCRIPT_DIR/outputs.env"
  echo "  setting API Gateway invoke permission on HTTP handler..."
  aws lambda add-permission \
    --function-name "$LAMBDA_FUNCTION" \
    --statement-id "apigw-invoke" \
    --action "lambda:InvokeFunction" \
    --principal "apigateway.amazonaws.com" \
    --source-arn "arn:aws:execute-api:${AWS_REGION}:${AWS_ACCOUNT_ID}:${APIGW_ID}/*" \
    --region "$AWS_REGION" 2>/dev/null || echo "  permission already exists"
fi

echo ""
echo "=== Push complete ==="
echo "  HTTP handler: ${ECR_URI}:latest  →  Lambda ${LAMBDA_FUNCTION}"
echo "  Worker:       ${WORKER_ECR_URI}:latest  →  Fargate task def ${FARGATE_TASK_DEF}"
echo "  Task def:     ${TASK_DEF_ARN}"
echo "  Jobs bucket:  ${JOBS_BUCKET}"
echo "  Secret:       ${SECRET_NAME} (unchanged; rotate with deploy.sh credentials)"
