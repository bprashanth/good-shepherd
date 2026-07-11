#!/usr/bin/env bash
# Trigger the nightly regression ON DEMAND (same Fargate task the schedule runs)
# and tail its logs until it finishes. Use this for the Milestone-A checkpoint
# and any time you want to force a regression run without waiting for the cron.
#
# Usage: ./run_once.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../deploy/config.sh"

REGRESSION_EMAIL="${REGRESSION_EMAIL:-prashanth@tech4goodcommunity.com}"

SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=${ECS_SG_NAME}" "Name=vpc-id,Values=${ECS_VPC_ID}" \
  --query 'SecurityGroups[0].GroupId' --output text --region "$AWS_REGION" 2>/dev/null || echo "None")
[ "$SG_ID" != "None" ] && [ -n "$SG_ID" ] || { echo "ERROR: SG '${ECS_SG_NAME}' not found"; exit 1; }

echo "=== On-demand regression run ==="
echo "  cluster:  ${ECS_CLUSTER}"
echo "  task def: ${FARGATE_TASK_DEF}"
echo "  email →   ${REGRESSION_EMAIL}"
echo ""

RUN_OUTPUT=$(aws ecs run-task \
  --cluster "$ECS_CLUSTER" \
  --task-definition "$FARGATE_TASK_DEF" \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[${ECS_SUBNET}],securityGroups=[${SG_ID}],assignPublicIp=ENABLED}" \
  --overrides "{\"containerOverrides\":[{\"name\":\"worker\",\"environment\":[{\"name\":\"MODE\",\"value\":\"regression\"},{\"name\":\"REGRESSION_EMAIL\",\"value\":\"${REGRESSION_EMAIL}\"}]}]}" \
  --region "$AWS_REGION")

TASK_ARN=$(echo "$RUN_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['tasks'][0]['taskArn'])" 2>/dev/null || echo "")
[ -n "$TASK_ARN" ] || { echo "ERROR: failed to launch task"; echo "$RUN_OUTPUT"; exit 1; }
TASK_ID="${TASK_ARN##*/}"
echo "  task ID: ${TASK_ID}"

echo ""
echo "→ Waiting for task to start..."
for i in $(seq 1 30); do
  STATUS=$(aws ecs describe-tasks --cluster "$ECS_CLUSTER" --tasks "$TASK_ARN" \
    --query 'tasks[0].lastStatus' --output text --region "$AWS_REGION" 2>/dev/null || echo "UNKNOWN")
  printf "  [%2d] %s\n" "$i" "$STATUS"
  [ "$STATUS" = "RUNNING" ] && break
  if [ "$STATUS" = "STOPPED" ]; then break; fi
  sleep 10
done

echo ""
echo "→ Tailing logs (${FARGATE_LOG_GROUP} / ecs/worker/${TASK_ID})..."
aws logs tail "$FARGATE_LOG_GROUP" --log-stream-names "ecs/worker/${TASK_ID}" \
  --follow --region "$AWS_REGION" 2>/dev/null &
LOG_PID=$!
trap 'kill "$LOG_PID" 2>/dev/null || true' EXIT

echo "→ Waiting for task to stop..."
aws ecs wait tasks-stopped --cluster "$ECS_CLUSTER" --tasks "$TASK_ARN" --region "$AWS_REGION"
kill "$LOG_PID" 2>/dev/null || true; trap - EXIT

EXIT_CODE=$(aws ecs describe-tasks --cluster "$ECS_CLUSTER" --tasks "$TASK_ARN" \
  --query 'tasks[0].containers[0].exitCode' --output text --region "$AWS_REGION" 2>/dev/null || echo "?")
echo ""
echo "=== Task stopped (container exit code: ${EXIT_CODE}) ==="
echo "  0 = regression PASS, 1 = regression FAIL — check the email to ${REGRESSION_EMAIL}."
echo "  Artifacts: s3://${JOBS_BUCKET}/${S3_PREFIX}/regression/runs/"
