#!/usr/bin/env bash
# Push ~/.codex/auth.json to AWS Secrets Manager as 'form-idable/codex-auth'.
# Run this once before deploying (or whenever local credentials change).
# Safe to re-run — updates the existing secret if it already exists.
#
# Usage: ./push_secrets.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

AUTH_FILE="${HOME}/.codex/auth.json"

if [ ! -f "$AUTH_FILE" ]; then
  echo "ERROR: $AUTH_FILE not found — log in to codex first (codex login)"
  exit 1
fi

SECRET_VALUE=$(cat "$AUTH_FILE")

if aws secretsmanager describe-secret \
    --secret-id "$SECRET_NAME" \
    --region "$AWS_REGION" &>/dev/null; then
  echo "Updating secret: ${SECRET_NAME}"
  aws secretsmanager update-secret \
    --secret-id "$SECRET_NAME" \
    --secret-string "$SECRET_VALUE" \
    --region "$AWS_REGION" > /dev/null
  echo "  updated"
else
  echo "Creating secret: ${SECRET_NAME}"
  aws secretsmanager create-secret \
    --name "$SECRET_NAME" \
    --description "codex CLI auth.json for form-idable-vision-worker Lambda" \
    --secret-string "$SECRET_VALUE" \
    --region "$AWS_REGION" > /dev/null
  echo "  created"
fi

echo "Done — ${SECRET_NAME} is live in ${AWS_REGION}"
