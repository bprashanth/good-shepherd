#!/usr/bin/env bash
# Rotate the shared Codex auth without rebuilding images; verify both tiers.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

PREVIOUS_VERSION=$(aws secretsmanager list-secret-version-ids \
  --secret-id "$SECRET_NAME" --region "$AWS_REGION" \
  --query "Versions[?contains(VersionStages,'AWSCURRENT')].VersionId | [0]" --output text)
[[ -n "$PREVIOUS_VERSION" && "$PREVIOUS_VERSION" != "None" ]] || {
  echo "ERROR: cannot capture current ${SECRET_NAME} version" >&2
  exit 1
}

"$SCRIPT_DIR/push_secrets.sh"
if "$SCRIPT_DIR/verify_prod.sh" && "$SCRIPT_DIR/verify_high.sh"; then
  echo "Credential rotation verified on Low and High; no image was rebuilt."
  exit 0
fi

echo "Credential verification failed; restoring the captured secret version." >&2
"$SCRIPT_DIR/rollback_secret.sh" "$PREVIOUS_VERSION"
if "$SCRIPT_DIR/verify_prod.sh" && "$SCRIPT_DIR/verify_high.sh"; then
  echo "Previous credentials restored and verified; rotation rejected." >&2
  exit 1
fi

echo "FATAL: Low or High remains unhealthy after credential rollback." >&2
exit 2
