#!/usr/bin/env bash
# Ensure a Cognito user exists with a permanent password.
# Idempotent — safe to run repeatedly.
#
# Usage:
#   ./add-user.sh <email> <password>
#   ./add-user.sh                      # reads from test-credentials.env
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Read from args or fall back to test-credentials.env
if [ $# -ge 2 ]; then
  EMAIL="$1"
  PASS="$2"
elif [ -f "$SCRIPT_DIR/test-credentials.env" ]; then
  source "$SCRIPT_DIR/test-credentials.env"
  EMAIL="${TEST_USERNAME:?TEST_USERNAME not set in test-credentials.env}"
  PASS="${TEST_PASSWORD:?TEST_PASSWORD not set in test-credentials.env}"
else
  echo "Usage: $0 <email> <password>"
  echo "   or: create test-credentials.env with TEST_USERNAME and TEST_PASSWORD"
  exit 1
fi

echo "=== Ensuring user: ${EMAIL} ==="

# Check if user already exists
if aws cognito-idp admin-get-user \
  --user-pool-id "$COGNITO_POOL_ID" \
  --username "$EMAIL" \
  --region "$AWS_REGION" &>/dev/null; then
  echo "  user already exists"
else
  aws cognito-idp admin-create-user \
    --user-pool-id "$COGNITO_POOL_ID" \
    --username "$EMAIL" \
    --temporary-password "$PASS" \
    --message-action SUPPRESS \
    --user-attributes Name=email,Value="$EMAIL" Name=email_verified,Value=true \
    --region "$AWS_REGION" \
    --output text >/dev/null
  echo "  user created"
fi

# Always set permanent password (idempotent)
aws cognito-idp admin-set-user-password \
  --user-pool-id "$COGNITO_POOL_ID" \
  --username "$EMAIL" \
  --password "$PASS" \
  --permanent \
  --region "$AWS_REGION"

echo "  permanent password set"
echo "=== Done — user can log in immediately ==="
