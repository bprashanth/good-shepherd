#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
FORMID_REPO="$(cd "$SERVER_DIR/../../../form-idable" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Lambda is currently x86_64, while the DGX Spark deployment host is arm64.
# Build each image for its declared runtime explicitly; never let host
# architecture silently decide what production receives.
if ! docker run --rm --platform linux/amd64 --memory 256m --memory-swap 256m \
  public.ecr.aws/docker/library/busybox:1.36 true >/dev/null 2>&1; then
  echo "ERROR: amd64 emulation is unavailable. Install binfmt before deploying:" >&2
  echo "  docker run --privileged --rm tonistiigi/binfmt --install amd64" >&2
  exit 1
fi

aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin \
  "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
"$SCRIPT_DIR/push_high_secret.sh"
"$SCRIPT_DIR/_retag.sh" "$ECR_REPO" latest rollback || true
"$SCRIPT_DIR/_retag.sh" "$HIGH_WORKER_ECR_REPO" latest rollback || true

docker build --platform linux/amd64 --memory 8g -t "$IMAGE" "$SERVER_DIR"
docker tag "$IMAGE" "${ECR_URI}:latest"
docker push "${ECR_URI}:latest"

docker build --platform linux/arm64 --memory 8g \
  --build-context "pipeline=${FORMID_REPO}" -f "$SERVER_DIR/Dockerfile.high" \
  -t "$HIGH_WORKER_IMAGE" "$SERVER_DIR"
docker tag "$HIGH_WORKER_IMAGE" "${HIGH_WORKER_ECR_URI}:latest"
docker push "${HIGH_WORKER_ECR_URI}:latest"

HTTP_ENV="Variables={JOBS_BUCKET=${JOBS_BUCKET},S3_PREFIX=${S3_PREFIX},DYNAMO_TABLE=${DYNAMO_TABLE},ECS_CLUSTER=${ECS_CLUSTER},FARGATE_TASK=${FARGATE_TASK_DEF},FARGATE_TASK_HIGH=${HIGH_FARGATE_TASK_DEF},ECS_SG_NAME=${ECS_SG_NAME},AWS_LWA_REMOVE_BASE_PATH=/prod}"
aws lambda update-function-code --function-name "$LAMBDA_FUNCTION" --image-uri "${ECR_URI}:latest" \
  --region "$AWS_REGION" >/dev/null
aws lambda wait function-updated-v2 --function-name "$LAMBDA_FUNCTION" --region "$AWS_REGION"
aws lambda update-function-configuration --function-name "$LAMBDA_FUNCTION" --environment "$HTTP_ENV" \
  --memory-size "$LAMBDA_MEMORY_MB" --timeout "$LAMBDA_TIMEOUT_S" --region "$AWS_REGION" >/dev/null
aws lambda wait function-updated-v2 --function-name "$LAMBDA_FUNCTION" --region "$AWS_REGION"

EXEC_ROLE_ARN=$(aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.Arn' --output text)
HIGH_ROLE_ARN=$(aws iam get-role --role-name "$HIGH_FARGATE_TASK_ROLE" --query 'Role.Arn' --output text)
aws ecs register-task-definition --region "$AWS_REGION" --cli-input-json "$(cat <<JSON
{
  "family":"${HIGH_FARGATE_TASK_DEF}","networkMode":"awsvpc","requiresCompatibilities":["FARGATE"],
  "runtimePlatform":{"cpuArchitecture":"ARM64","operatingSystemFamily":"LINUX"},
  "cpu":"${HIGH_FARGATE_CPU}","memory":"${HIGH_FARGATE_MEMORY}",
  "executionRoleArn":"${EXEC_ROLE_ARN}","taskRoleArn":"${HIGH_ROLE_ARN}",
  "containerDefinitions":[{"name":"high-worker","image":"${HIGH_WORKER_ECR_URI}:latest","essential":true,
    "environment":[
      {"name":"PROVIDER_SECRET_NAME","value":"${HIGH_PROVIDER_SECRET_NAME}"},
      {"name":"JOBS_BUCKET","value":"${JOBS_BUCKET}"},{"name":"AWS_REGION","value":"${AWS_REGION}"},
      {"name":"NOTIFICATION_FROM_EMAIL","value":"${NOTIFICATION_FROM_EMAIL}"},{"name":"PWA_URL","value":"${PWA_URL}"}
    ],"logConfiguration":{"logDriver":"awslogs","options":{"awslogs-group":"${HIGH_FARGATE_LOG_GROUP}","awslogs-region":"${AWS_REGION}","awslogs-stream-prefix":"ecs"}}}]
}
JSON
)" >/dev/null
echo "High handler/worker pushed. Low worker image and task definition were not touched."
