#!/usr/bin/env bash
# Additive high deployment with a hard assertion that the low image/task stay put.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

LOW_DIGEST=$(aws ecr describe-images --repository-name "$WORKER_ECR_REPO" \
  --image-ids imageTag=latest --region "$AWS_REGION" --query 'imageDetails[0].imageDigest' --output text)
LOW_TASK=$(aws ecs describe-task-definition --task-definition "$FARGATE_TASK_DEF" \
  --region "$AWS_REGION" --query 'taskDefinition.taskDefinitionArn' --output text)

assert_low_unchanged() {
  local digest task
  digest=$(aws ecr describe-images --repository-name "$WORKER_ECR_REPO" \
    --image-ids imageTag=latest --region "$AWS_REGION" --query 'imageDetails[0].imageDigest' --output text)
  task=$(aws ecs describe-task-definition --task-definition "$FARGATE_TASK_DEF" \
    --region "$AWS_REGION" --query 'taskDefinition.taskDefinitionArn' --output text)
  [[ "$digest" == "$LOW_DIGEST" ]] || { echo "FATAL: low image digest changed" >&2; return 1; }
  [[ "$task" == "$LOW_TASK" ]] || { echo "FATAL: low task revision changed" >&2; return 1; }
}

"$SCRIPT_DIR/setup_high.sh"
if ! "$SCRIPT_DIR/push_high.sh"; then
  echo "High push failed; restoring the prior handler/high image." >&2
  "$SCRIPT_DIR/rollback_high.sh" || true
  assert_low_unchanged
  exit 1
fi
assert_low_unchanged

if "$SCRIPT_DIR/verify_high.sh"; then
  assert_low_unchanged
  echo "High deploy verified. Low image/task are byte-for-byte/revision unchanged."
  exit 0
fi

echo "High verification failed; rolling back additive handler/high image." >&2
"$SCRIPT_DIR/rollback_high.sh"
assert_low_unchanged
exit 1
