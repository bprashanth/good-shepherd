#!/usr/bin/env bash
# Orchestrator: build with smoke test, then push to ECR + update Lambda.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

echo "╔══════════════════════════════════════╗"
echo "║   form-idable deploy                 ║"
echo "╚══════════════════════════════════════╝"
echo ""

"$SCRIPT_DIR/build.sh" --test
echo ""
"$SCRIPT_DIR/push.sh"

# Print API Gateway URL if outputs.env exists
if [ -f "$SCRIPT_DIR/outputs.env" ]; then
  source "$SCRIPT_DIR/outputs.env"
  echo ""
  echo "=== Deployed ==="
  echo "API Gateway: ${APIGW_URL}"
  echo "Health:      curl ${APIGW_URL}/api/health"
fi
