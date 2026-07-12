#!/usr/bin/env bash
# Enable or disable the nightly regression schedule — the simple on/off switch.
# Disabling leaves the schedule in place (no re-create needed to resume).
#
# Usage: ./toggle.sh on|off   (or: ./toggle.sh status)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../deploy/config.sh"

SCHEDULE_NAME="formidable-nightly-regression"
ACTION="${1:-status}"

if ! aws scheduler get-schedule --name "$SCHEDULE_NAME" --region "$AWS_REGION" &>/dev/null; then
  echo "Schedule '${SCHEDULE_NAME}' does not exist — run ./schedule.sh first."
  exit 1
fi

case "$ACTION" in
  on|off)
    STATE=$([ "$ACTION" = "on" ] && echo ENABLED || echo DISABLED)
    # update-schedule replaces the whole schedule, so round-trip the current
    # definition through jq, changing only State.
    CUR="$(aws scheduler get-schedule --name "$SCHEDULE_NAME" --region "$AWS_REGION")"
    REQ="$(mktemp)"; trap 'rm -f "$REQ"' EXIT
    echo "$CUR" | python3 -c "
import sys, json
s = json.load(sys.stdin)
out = {k: s[k] for k in ('Name','ScheduleExpression','ScheduleExpressionTimezone',
                         'FlexibleTimeWindow','Description','Target') if k in s}
out['State'] = '${STATE}'
json.dump(out, sys.stdout)
" > "$REQ"
    aws scheduler update-schedule --cli-input-json "file://${REQ}" --region "$AWS_REGION" --output text >/dev/null
    echo "Nightly regression is now ${STATE}."
    ;;
  status)
    STATE=$(aws scheduler get-schedule --name "$SCHEDULE_NAME" --region "$AWS_REGION" \
      --query 'State' --output text)
    EXPR=$(aws scheduler get-schedule --name "$SCHEDULE_NAME" --region "$AWS_REGION" \
      --query 'ScheduleExpression' --output text)
    echo "Nightly regression: ${STATE}  (${EXPR} UTC)"
    ;;
  *)
    echo "usage: ./toggle.sh on|off|status"; exit 2;;
esac
