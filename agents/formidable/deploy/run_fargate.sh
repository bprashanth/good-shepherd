#!/usr/bin/env bash
# Trigger a codex worker job on Fargate and tail its output.
#
# Usage: run_fargate.sh <pdf-path> [output.xlsx]
#
# Flow:
#   1. Upload local PDF to S3 as a new job
#   2. aws ecs run-task with env overrides (JOB_ID, INPUT_KEY, FILENAME)
#   3. Tail CloudWatch logs in background while polling S3 for completion
#   4. Download output.xlsx when done
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

PDF_PATH="${1:?usage: run_fargate.sh <pdf-path> [output.xlsx]}"
OUT_PATH="${2:-/tmp/fargate_output.xlsx}"

if [ ! -f "$PDF_PATH" ]; then
  echo "ERROR: file not found: ${PDF_PATH}"
  exit 1
fi

# ── Look up security group ID ──────────────────────────────────────
SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=${ECS_SG_NAME}" "Name=vpc-id,Values=${ECS_VPC_ID}" \
  --query 'SecurityGroups[0].GroupId' --output text --region "$AWS_REGION" 2>/dev/null || echo "None")

if [ "$SG_ID" = "None" ] || [ -z "$SG_ID" ]; then
  echo "ERROR: security group '${ECS_SG_NAME}' not found — run setup_cluster.sh first"
  exit 1
fi

# ── Upload input to S3 ─────────────────────────────────────────────
JOB_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
FILENAME=$(basename "$PDF_PATH")
S3_PREFIX="${S3_PREFIX:-formidable}"
INPUT_KEY="${S3_PREFIX}/jobs/${JOB_ID}/input.pdf"
DEV_USER="${DEV_USER_ID:-dev-user}"

echo "=== Fargate codex job ==="
echo "  job_id:   ${JOB_ID}"
echo "  user_id:  ${DEV_USER}"
echo "  file:     ${PDF_PATH}"
echo "  s3 key:   s3://${JOBS_BUCKET}/${INPUT_KEY}"
echo ""

echo "→ Uploading input to S3..."
aws s3 cp "$PDF_PATH" "s3://${JOBS_BUCKET}/${INPUT_KEY}" --region "$AWS_REGION"

echo "→ Creating DynamoDB record..."
NOW=$(python3 -c "from datetime import datetime, timezone; print(datetime.now(timezone.utc).isoformat())")
aws dynamodb put-item \
  --table-name formidable-jobs \
  --item "{
    \"user_id\":      {\"S\": \"${DEV_USER}\"},
    \"job_id\":       {\"S\": \"${JOB_ID}\"},
    \"name\":         {\"S\": \"${FILENAME}\"},
    \"status\":       {\"S\": \"queued\"},
    \"review_state\": {\"S\": \"unreviewed\"},
    \"created_at\":   {\"S\": \"${NOW}\"},
    \"pages\":        {\"N\": \"0\"},
    \"crops\":        {\"N\": \"0\"}
  }" \
  --region "$AWS_REGION"
echo "  record created"

# ── Launch Fargate task ────────────────────────────────────────────
echo "→ Launching Fargate task (cluster: ${ECS_CLUSTER}, task def: ${FARGATE_TASK_DEF})..."
RUN_OUTPUT=$(aws ecs run-task \
  --cluster "$ECS_CLUSTER" \
  --task-definition "$FARGATE_TASK_DEF" \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[${ECS_SUBNET}],securityGroups=[${SG_ID}],assignPublicIp=ENABLED}" \
  --overrides "{\"containerOverrides\":[{\"name\":\"worker\",\"environment\":[{\"name\":\"JOB_ID\",\"value\":\"${JOB_ID}\"},{\"name\":\"INPUT_KEY\",\"value\":\"${INPUT_KEY}\"},{\"name\":\"FILENAME\",\"value\":\"${FILENAME}\"},{\"name\":\"USER_ID\",\"value\":\"${DEV_USER}\"}]}]}" \
  --region "$AWS_REGION")

TASK_ARN=$(echo "$RUN_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['tasks'][0]['taskArn'])" 2>/dev/null || echo "")
if [ -z "$TASK_ARN" ]; then
  echo "ERROR: failed to launch task"
  echo "$RUN_OUTPUT"
  exit 1
fi

TASK_ID="${TASK_ARN##*/}"
echo "  task ARN: ${TASK_ARN}"
echo "  task ID:  ${TASK_ID}"

# ── Wait for task to reach RUNNING ────────────────────────────────
echo ""
echo "→ Waiting for task to start..."
for i in $(seq 1 30); do
  TASK_STATUS=$(aws ecs describe-tasks --cluster "$ECS_CLUSTER" --tasks "$TASK_ARN" \
    --query 'tasks[0].lastStatus' --output text --region "$AWS_REGION" 2>/dev/null || echo "UNKNOWN")
  printf "  [%2d] %s\n" "$i" "$TASK_STATUS"
  if [ "$TASK_STATUS" = "RUNNING" ]; then
    break
  elif [ "$TASK_STATUS" = "STOPPED" ]; then
    STOPPED_REASON=$(aws ecs describe-tasks --cluster "$ECS_CLUSTER" --tasks "$TASK_ARN" \
      --query 'tasks[0].stoppedReason' --output text --region "$AWS_REGION" 2>/dev/null || echo "unknown")
    echo "ERROR: task stopped before RUNNING: ${STOPPED_REASON}"
    exit 1
  fi
  sleep 10
done

# ── Tail CloudWatch logs in background ────────────────────────────
LOG_STREAM="ecs/worker/${TASK_ID}"
echo ""
echo "→ Tailing logs (${FARGATE_LOG_GROUP} / ${LOG_STREAM})..."
aws logs tail "$FARGATE_LOG_GROUP" \
  --log-stream-names "$LOG_STREAM" \
  --follow --region "$AWS_REGION" 2>/dev/null &
LOG_PID=$!
cleanup() { kill "$LOG_PID" 2>/dev/null || true; }
trap cleanup EXIT

# ── Poll S3 for job completion ─────────────────────────────────────
echo ""
echo "→ Polling S3 for completion (timeout: 600s)..."
MAX_WAIT=600
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
  # Worker signals completion via DynamoDB, not status.json — poll DynamoDB
  STATUS_JSON=$(aws dynamodb get-item \
    --table-name formidable-jobs \
    --key "{\"user_id\":{\"S\":\"${DEV_USER}\"},\"job_id\":{\"S\":\"${JOB_ID}\"}}" \
    --region "$AWS_REGION" \
    --query "Item.status.S" --output text 2>/dev/null || echo "unknown")
  STATUS="$STATUS_JSON"

  if [ "$STATUS" = "complete" ]; then
    cleanup; trap - EXIT
    echo ""
    echo "=== Job complete! ==="
    aws s3 cp "s3://${JOBS_BUCKET}/${S3_PREFIX}/jobs/${JOB_ID}/output.xlsx" "$OUT_PATH" --region "$AWS_REGION"
    echo "  xlsx: ${OUT_PATH} ($(stat -c%s "$OUT_PATH") bytes)"

    # Display manifest summary
    MANIFEST_LOCAL="/tmp/crops_manifest_${JOB_ID}.json"
    if aws s3 cp "s3://${JOBS_BUCKET}/${S3_PREFIX}/jobs/${JOB_ID}/crops_manifest.json" \
        "$MANIFEST_LOCAL" --region "$AWS_REGION" 2>/dev/null; then
      echo "  manifest: ${MANIFEST_LOCAL}"
      python3 - "$MANIFEST_LOCAL" <<'PYEOF'
import sys, json
m = json.load(open(sys.argv[1]))
total_crops = sum(len(p.get("crops", [])) for p in m.get("pages", []))
print(f"  pages: {len(m.get('pages', []))}, crops: {total_crops}")
for p in m.get("pages", []):
    print(f"    page {p['page']} ({p.get('render','?')}): {len(p.get('crops',[]))} crops")
    for c in p.get("crops", []):
        bb = c.get("bbox", [])
        bb_str = "[{:.2f},{:.2f},{:.2f},{:.2f}]".format(*bb) if len(bb)==4 else str(bb)
        print(f"      {c['file']} bbox={bb_str} rows={c.get('rows','?')}  {c.get('note','')}")
PYEOF
    else
      echo "  (no manifest — codex did not produce crops_manifest.json)"
    fi

    # Display metadata
    META_LOCAL="/tmp/metadata_${JOB_ID}.json"
    if aws s3 cp "s3://${JOBS_BUCKET}/${S3_PREFIX}/jobs/${JOB_ID}/metadata.json" \
        "$META_LOCAL" --region "$AWS_REGION" 2>/dev/null; then
      echo "  metadata: $(cat "$META_LOCAL")"
    fi

    # S3 artifact listing
    echo ""
    echo "  S3 artifacts:"
    aws s3 ls "s3://${JOBS_BUCKET}/${S3_PREFIX}/jobs/${JOB_ID}/" --recursive --region "$AWS_REGION" \
      | awk '{print "    " $3 " bytes  " $4}'
    exit 0
  elif [ "$STATUS" = "failed" ]; then
    cleanup; trap - EXIT
    echo ""
    echo "=== Job FAILED ==="
    aws dynamodb get-item \
      --table-name formidable-jobs \
      --key "{\"user_id\":{\"S\":\"${DEV_USER}\"},\"job_id\":{\"S\":\"${JOB_ID}\"}}" \
      --region "$AWS_REGION" \
      --query "Item.error.S" --output text 2>/dev/null || echo "(no error in DynamoDB)"
    aws s3 cp "s3://${JOBS_BUCKET}/${S3_PREFIX}/jobs/${JOB_ID}/run.log" - \
      --region "$AWS_REGION" 2>/dev/null | tail -30 || true
    exit 1
  fi

  sleep 10
  ELAPSED=$((ELAPSED + 10))
done

echo "ERROR: timed out after ${MAX_WAIT}s — check CloudWatch logs for ${FARGATE_LOG_GROUP}"
exit 1
