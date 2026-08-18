#!/usr/bin/env bash
# Release the shared handler plus Low worker, proving High did not move.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

HIGH_DIGEST=$(aws ecr describe-images --repository-name "$HIGH_WORKER_ECR_REPO" \
  --image-ids imageTag=latest --region "$AWS_REGION" \
  --query 'imageDetails[0].imageDigest' --output text)
HIGH_TASK=$(aws ecs describe-task-definition --task-definition "$HIGH_FARGATE_TASK_DEF" \
  --region "$AWS_REGION" --query 'taskDefinition.taskDefinitionArn' --output text)

assert_high_unchanged() {
  local digest task
  digest=$(aws ecr describe-images --repository-name "$HIGH_WORKER_ECR_REPO" \
    --image-ids imageTag=latest --region "$AWS_REGION" \
    --query 'imageDetails[0].imageDigest' --output text)
  task=$(aws ecs describe-task-definition --task-definition "$HIGH_FARGATE_TASK_DEF" \
    --region "$AWS_REGION" --query 'taskDefinition.taskDefinitionArn' --output text)
  [[ "$digest" == "$HIGH_DIGEST" ]] || { echo "FATAL: High image changed" >&2; return 1; }
  [[ "$task" == "$HIGH_TASK" ]] || { echo "FATAL: High task changed" >&2; return 1; }
}

"$SCRIPT_DIR/build.sh" --test
if ! "$SCRIPT_DIR/push.sh"; then
  echo "Low push failed; restoring the prior handler/Low image." >&2
  "$SCRIPT_DIR/rollback.sh" || true
  assert_high_unchanged
  exit 1
fi
assert_high_unchanged

if "$SCRIPT_DIR/verify_prod.sh" && "$SCRIPT_DIR/verify_high.sh"; then
  assert_high_unchanged
  echo "Low release verified across both routes; High image/task stayed unchanged."
  exit 0
fi

echo "Low release verification failed; rolling back handler/Low." >&2
"$SCRIPT_DIR/rollback.sh"
assert_high_unchanged
if "$SCRIPT_DIR/verify_prod.sh" && "$SCRIPT_DIR/verify_high.sh"; then
  echo "Previous release restored; Low release rejected." >&2
  exit 1
fi
echo "FATAL: a route remains unhealthy after Low rollback." >&2
exit 2
