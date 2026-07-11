#!/usr/bin/env bash
# Build, smoke-test, push, then VERIFY against prod — and auto-rollback if the
# verification fails.
#
#   build.sh --test  → push.sh  → verify_prod.sh
#     PASS → done.
#     FAIL → rollback.sh (image + task-def) → verify_prod.sh
#              PASS → prod restored to previous image; exit 1 (this deploy failed)
#              FAIL → rollback.sh --with-secret → verify_prod.sh
#                       PASS → restored; exit 1
#                       FAIL → exit 2 (prod still broken — manual intervention)
#
# Each verify_prod runs one real codex job (~$0.02 Fargate + one form) — a
# rollback path can therefore run codex 2-3 times. Deploys are infrequent, so
# this is an acceptable price for a safe gate.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

"$SCRIPT_DIR/build.sh" --test
"$SCRIPT_DIR/push.sh"

echo ""
echo "########## verifying against prod ##########"
if "$SCRIPT_DIR/verify_prod.sh"; then
  echo ""
  echo "✅ deploy verified — prod healthy."
  exit 0
fi

echo ""
echo "❌ verify FAILED — rolling back image + task-def, then re-verifying."
"$SCRIPT_DIR/rollback.sh"
if "$SCRIPT_DIR/verify_prod.sh"; then
  echo ""
  echo "⚠️  Rolled back to the PREVIOUS image — prod is healthy again."
  echo "    THIS DEPLOY FAILED. Investigate before retrying (codex version? secret? code?)."
  exit 1
fi

echo ""
echo "❌ still failing after image rollback — reverting secret too, then re-verifying."
"$SCRIPT_DIR/rollback.sh" --with-secret
if "$SCRIPT_DIR/verify_prod.sh"; then
  echo ""
  echo "⚠️  Restored after image + secret rollback — prod is healthy again. THIS DEPLOY FAILED."
  exit 1
fi

echo ""
echo "🚨 PROD STILL FAILING after full rollback (image + task-def + secret)."
echo "   Manual intervention required — check docs/ops.md (debugging) and CloudWatch/S3 run.log."
exit 2
