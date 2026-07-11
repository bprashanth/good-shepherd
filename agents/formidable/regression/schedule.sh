#!/usr/bin/env bash
# Create (or update) the nightly regression schedule on EventBridge Scheduler.
# Idempotent — safe to re-run. Creates the scheduler IAM role on first run.
#
# The schedule uses the *universal* ecs:runTask target so it can pass the
# MODE=regression container override (the templated ECS target cannot).
# It references the task-definition FAMILY (formidable-worker), so it always
# runs the latest revision — no need to re-point it after a push.
#
# Cost: EventBridge Scheduler bills $0 for this (nightly ≈ 30 invocations/mo vs
# a 14M/mo free tier). The only cost is the Fargate task it launches (~$0.02/run).
#
# Usage: ./schedule.sh
#   SCHEDULE_EXPR   cron/rate expression (default: nightly 20:00 UTC ≈ 01:30 IST)
#   REGRESSION_EMAIL  report recipient (default prashanth@tech4goodcommunity.com)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../deploy/config.sh"

SCHEDULE_NAME="formidable-nightly-regression"
SCHEDULER_ROLE="formidable-regression-scheduler-role"
SCHEDULE_EXPR="${SCHEDULE_EXPR:-cron(0 20 * * ? *)}"
REGRESSION_EMAIL="${REGRESSION_EMAIL:-prashanth@tech4goodcommunity.com}"

# ── Resolve security group ─────────────────────────────────────────
SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=${ECS_SG_NAME}" "Name=vpc-id,Values=${ECS_VPC_ID}" \
  --query 'SecurityGroups[0].GroupId' --output text --region "$AWS_REGION" 2>/dev/null || echo "None")
[ "$SG_ID" != "None" ] && [ -n "$SG_ID" ] || { echo "ERROR: SG '${ECS_SG_NAME}' not found"; exit 1; }

CLUSTER_ARN="arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:cluster/${ECS_CLUSTER}"
EXEC_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/ecsTaskExecutionRole"
TASK_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${FARGATE_TASK_ROLE}"

# ── Scheduler IAM role (assumed by scheduler.amazonaws.com) ────────
echo "=== Scheduler IAM role: ${SCHEDULER_ROLE} ==="
if ! aws iam get-role --role-name "$SCHEDULER_ROLE" &>/dev/null; then
  aws iam create-role --role-name "$SCHEDULER_ROLE" \
    --assume-role-policy-document '{
      "Version":"2012-10-17",
      "Statement":[{"Effect":"Allow","Principal":{"Service":"scheduler.amazonaws.com"},"Action":"sts:AssumeRole"}]
    }' --output text >/dev/null
  echo "  created — waiting for IAM propagation..."
  sleep 10
else
  echo "  exists"
fi

aws iam put-role-policy --role-name "$SCHEDULER_ROLE" \
  --policy-name "${SCHEDULER_ROLE}-policy" \
  --policy-document "$(cat <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RunTask",
      "Effect": "Allow",
      "Action": "ecs:RunTask",
      "Resource": "arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:task-definition/${FARGATE_TASK_DEF}:*"
    },
    {
      "Sid": "PassTaskRoles",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": ["${EXEC_ROLE_ARN}", "${TASK_ROLE_ARN}"]
    }
  ]
}
JSON
)"
SCHEDULER_ROLE_ARN=$(aws iam get-role --role-name "$SCHEDULER_ROLE" --query 'Role.Arn' --output text)
echo "  policy applied: ${SCHEDULER_ROLE_ARN}"

# ── Build create/update-schedule request JSON (python handles nested escaping) ──
REQ_FILE="$(mktemp)"
trap 'rm -f "$REQ_FILE"' EXIT
python3 - > "$REQ_FILE" <<PY
import json
run_task = {
    "Cluster": "${ECS_CLUSTER}",
    "TaskDefinition": "${FARGATE_TASK_DEF}",
    "LaunchType": "FARGATE",
    "NetworkConfiguration": {
        "AwsvpcConfiguration": {
            "Subnets": ["${ECS_SUBNET}"],
            "SecurityGroups": ["${SG_ID}"],
            "AssignPublicIp": "ENABLED",
        }
    },
    "Overrides": {
        "ContainerOverrides": [{
            "Name": "worker",
            "Environment": [
                {"Name": "MODE", "Value": "regression"},
                {"Name": "REGRESSION_EMAIL", "Value": "${REGRESSION_EMAIL}"},
            ],
        }]
    },
}
print(json.dumps({
    "Name": "${SCHEDULE_NAME}",
    "ScheduleExpression": "${SCHEDULE_EXPR}",
    "ScheduleExpressionTimezone": "UTC",
    "FlexibleTimeWindow": {"Mode": "OFF"},
    "State": "ENABLED",
    "Description": "Formidable nightly regression — runs codex on the golden form and emails a diff report.",
    "Target": {
        "Arn": "arn:aws:scheduler:::aws-sdk:ecs:runTask",
        "RoleArn": "${SCHEDULER_ROLE_ARN}",
        "Input": json.dumps(run_task),
    },
}))
PY

echo ""
echo "=== EventBridge schedule: ${SCHEDULE_NAME} (${SCHEDULE_EXPR} UTC) ==="
if aws scheduler get-schedule --name "$SCHEDULE_NAME" --region "$AWS_REGION" &>/dev/null; then
  aws scheduler update-schedule --cli-input-json "file://${REQ_FILE}" --region "$AWS_REGION" --output text >/dev/null
  echo "  updated"
else
  aws scheduler create-schedule --cli-input-json "file://${REQ_FILE}" --region "$AWS_REGION" --output text >/dev/null
  echo "  created"
fi

echo ""
echo "Done. Nightly regression is ENABLED (${SCHEDULE_EXPR} UTC → ${REGRESSION_EMAIL})."
echo "  Turn off:  ./toggle.sh off"
echo "  Turn on:   ./toggle.sh on"
echo "  Run now:   ./run_once.sh"
