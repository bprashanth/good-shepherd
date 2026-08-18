#!/usr/bin/env bash
# Explicit Formidable release dispatcher. Code and credentials are independent.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODE="${1:-all}"

case "$MODE" in
  credentials|creds)
    exec "$SCRIPT_DIR/deploy_credentials.sh"
    ;;
  low)
    exec "$SCRIPT_DIR/deploy_low.sh"
    ;;
  high)
    exec "$SCRIPT_DIR/deploy_high.sh"
    ;;
  all)
    exec "$SCRIPT_DIR/deploy_all.sh"
    ;;
  *)
    echo "usage: $0 {credentials|low|high|all}" >&2
    exit 2
    ;;
esac
