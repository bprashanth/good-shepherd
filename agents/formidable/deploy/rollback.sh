#!/usr/bin/env bash
# Revert the last deploy. Restores the :rollback images that push.sh preserved
# (before it overwrote :latest) and redeploys.
#
#   ./rollback.sh                # image + task-def only (default, safe)
#   ./rollback.sh --with-secret  # ALSO revert codex secret to its prior version
#
# Ordering rationale (see docs/ops.md): image/task-def first. The codex secret
# holds *rotating OAuth tokens* — the previous version is OLDER and may be closer
# to expiry, so only revert it if an image rollback alone doesn't fix prod.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"
source "$SCRIPT_DIR/outputs.env"

WITH_SECRET=0
[ "${1:-}" = "--with-secret" ] && WITH_SECRET=1

echo "=== rollback: restoring :rollback → :latest ==="
"$SCRIPT_DIR/_retag.sh" "$ECR_REPO"        rollback latest \
  || { echo "  no :rollback image for ${ECR_REPO} — nothing to restore"; }
"$SCRIPT_DIR/_retag.sh" "$WORKER_ECR_REPO" rollback latest \
  || { echo "  no :rollback image for ${WORKER_ECR_REPO} — nothing to restore"; }

# ── HTTP Lambda: force it to pick up the restored :latest ──────────
echo "→ redeploying Lambda ${LAMBDA_FUNCTION} from restored :latest"
aws lambda update-function-code \
  --function-name "$LAMBDA_FUNCTION" --image-uri "${ECR_URI}:latest" \
  --region "$AWS_REGION" --output text >/dev/null
aws lambda wait function-updated-v2 --function-name "$LAMBDA_FUNCTION" --region "$AWS_REGION"

# ── Worker: next Fargate run pulls the restored :latest (task def refs the tag).
# Re-register a fresh revision so the family head is unambiguous.
echo "→ re-registering worker task def (points at restored :latest)"
EXEC_ROLE_ARN=$(aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.Arn' --output text)
TASK_ROLE_ARN=$(aws iam get-role --role-name "$FARGATE_TASK_ROLE"  --query 'Role.Arn' --output text)
aws ecs register-task-definition --region "$AWS_REGION" --cli-input-json "$(cat <<JSON
{
  "family": "${FARGATE_TASK_DEF}",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "${FARGATE_CPU}", "memory": "${FARGATE_MEMORY}",
  "executionRoleArn": "${EXEC_ROLE_ARN}", "taskRoleArn": "${TASK_ROLE_ARN}",
  "containerDefinitions": [{
    "name": "worker", "image": "${WORKER_ECR_URI}:latest", "essential": true,
    "environment": [
      {"name": "CODEX_SECRET_NAME", "value": "${SECRET_NAME}"},
      {"name": "JOBS_BUCKET", "value": "${JOBS_BUCKET}"},
      {"name": "AWS_REGION", "value": "${AWS_REGION}"},
      {"name": "NOTIFICATION_FROM_EMAIL", "value": "${NOTIFICATION_FROM_EMAIL}"},
      {"name": "PWA_URL", "value": "${PWA_URL}"}
    ],
    "logConfiguration": {"logDriver": "awslogs", "options": {
      "awslogs-group": "${FARGATE_LOG_GROUP}", "awslogs-region": "${AWS_REGION}",
      "awslogs-stream-prefix": "ecs"}}
  }]
}
JSON
)" --query 'taskDefinition.taskDefinitionArn' --output text

# ── Optional: revert codex secret to its previous version ─────────
if [ "$WITH_SECRET" = "1" ]; then
  echo "→ reverting secret ${SECRET_NAME} to AWSPREVIOUS"
  CUR=$(aws secretsmanager list-secret-version-ids --secret-id "$SECRET_NAME" --region "$AWS_REGION" \
    --query "Versions[?contains(VersionStages,'AWSCURRENT')].VersionId | [0]" --output text)
  PREV=$(aws secretsmanager list-secret-version-ids --secret-id "$SECRET_NAME" --region "$AWS_REGION" \
    --query "Versions[?contains(VersionStages,'AWSPREVIOUS')].VersionId | [0]" --output text)
  if [ -n "$PREV" ] && [ "$PREV" != "None" ]; then
    aws secretsmanager update-secret-version-stage --secret-id "$SECRET_NAME" \
      --version-stage AWSCURRENT --move-to-version-id "$PREV" --remove-from-version-id "$CUR" \
      --region "$AWS_REGION" >/dev/null
    echo "  secret reverted (${CUR} → ${PREV})"
  else
    echo "  no AWSPREVIOUS version — secret left unchanged"
  fi
fi

echo "=== rollback complete ==="
