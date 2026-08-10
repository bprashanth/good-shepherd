#!/usr/bin/env bash
# Roll back only the additive API handler and high worker. The low worker image
# and formidable-worker task family are deliberately outside this script.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

"$SCRIPT_DIR/_retag.sh" "$ECR_REPO" rollback latest

# A first high release has no previous high image. In that case roll back the
# handler (which makes high unreachable) and leave the unused high task alone.
HIGH_ROLLBACK=false
if aws ecr describe-images --repository-name "$HIGH_WORKER_ECR_REPO" \
    --image-ids imageTag=rollback --region "$AWS_REGION" >/dev/null 2>&1; then
  "$SCRIPT_DIR/_retag.sh" "$HIGH_WORKER_ECR_REPO" rollback latest
  HIGH_ROLLBACK=true
fi

aws lambda update-function-code --function-name "$LAMBDA_FUNCTION" \
  --image-uri "${ECR_URI}:latest" --region "$AWS_REGION" >/dev/null
aws lambda wait function-updated-v2 --function-name "$LAMBDA_FUNCTION" --region "$AWS_REGION"

if [[ "$HIGH_ROLLBACK" == true ]]; then
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
fi
echo "High API/worker rollback complete. Low worker was not modified."
