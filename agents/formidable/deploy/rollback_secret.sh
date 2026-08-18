#!/usr/bin/env bash
# Move AWSCURRENT back to an explicitly captured Secrets Manager version.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

TARGET_VERSION="${1:?usage: rollback_secret.sh VERSION_ID}"
CURRENT_VERSION=$(aws secretsmanager list-secret-version-ids \
  --secret-id "$SECRET_NAME" --region "$AWS_REGION" \
  --query "Versions[?contains(VersionStages,'AWSCURRENT')].VersionId | [0]" --output text)

if [[ "$CURRENT_VERSION" == "$TARGET_VERSION" ]]; then
  echo "Secret already points to ${TARGET_VERSION}."
  exit 0
fi

aws secretsmanager update-secret-version-stage --secret-id "$SECRET_NAME" \
  --version-stage AWSCURRENT --move-to-version-id "$TARGET_VERSION" \
  --remove-from-version-id "$CURRENT_VERSION" --region "$AWS_REGION" >/dev/null
echo "Restored ${SECRET_NAME} to captured version ${TARGET_VERSION}."
