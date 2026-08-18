#!/usr/bin/env bash
# Release shared handler plus both workers as one verified code release.
# Credentials are intentionally separate: use deploy_credentials.sh.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

"$SCRIPT_DIR/build.sh" --test
"$SCRIPT_DIR/build_high.sh" --test
"$SCRIPT_DIR/setup_high.sh"

if ! "$SCRIPT_DIR/push.sh"; then
  echo "Shared handler/Low push failed; restoring previous images." >&2
  "$SCRIPT_DIR/rollback.sh" || true
  exit 1
fi

if ! HIGH_SKIP_HANDLER=1 "$SCRIPT_DIR/push_high.sh"; then
  echo "High push failed; restoring all code surfaces." >&2
  "$SCRIPT_DIR/rollback_high.sh" || true
  "$SCRIPT_DIR/rollback.sh" || true
  exit 1
fi

if "$SCRIPT_DIR/verify_prod.sh" && "$SCRIPT_DIR/verify_high.sh"; then
  echo "All-tier code release verified on Low and High. Credentials were unchanged."
  exit 0
fi

echo "All-tier verification failed; restoring handler, Low and High." >&2
"$SCRIPT_DIR/rollback_high.sh" || true
"$SCRIPT_DIR/rollback.sh" || true
if "$SCRIPT_DIR/verify_prod.sh" && "$SCRIPT_DIR/verify_high.sh"; then
  echo "Previous all-tier release restored; candidate rejected." >&2
  exit 1
fi
echo "FATAL: a route remains unhealthy after all-tier rollback." >&2
exit 2
