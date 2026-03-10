#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: test/get_db.sh --org <org> [--out <path>]

Fetches the sessions payload for the given org and writes it to disk.

Examples:
  test/get_db.sh --org ncf
  test/get_db.sh --org t4gc --out /tmp/t4gc.json
EOF
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/../deploy" && pwd)"

ORG=""
OUT_FILE=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --org)
      shift
      [ "$#" -gt 0 ] || { echo "--org requires a value" >&2; usage; exit 1; }
      ORG="$1"
      ;;
    --out)
      shift
      [ "$#" -gt 0 ] || { echo "--out requires a value" >&2; usage; exit 1; }
      OUT_FILE="$1"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
  shift
done

[ -n "$ORG" ] || { echo "--org is required" >&2; usage; exit 1; }

if [ -z "$OUT_FILE" ]; then
  OUT_FILE="$SCRIPT_DIR/photomon/db.${ORG}.fresh.json"
fi

echo "Loading config from: $DEPLOY_DIR/config.sh"
source "$DEPLOY_DIR/config.sh"

echo "Loading outputs from: $DEPLOY_DIR/outputs.env"
source "$DEPLOY_DIR/outputs.env"

echo "Loading test credentials from: $DEPLOY_DIR/test-credentials.env"
source "$DEPLOY_DIR/test-credentials.env"

if [ -z "${COGNITO_POOL_ID:-}" ] || [ -z "${COGNITO_CLIENT_ID:-}" ]; then
  echo "Missing Cognito config." >&2
  echo "Set COGNITO_POOL_ID and COGNITO_CLIENT_ID in the environment, or fix deploy/config.sh auth_config loading." >&2
  exit 1
fi

mkdir -p "$(dirname "$OUT_FILE")"

echo "Requesting Cognito token for $TEST_USERNAME"
TOKEN=$(aws cognito-idp initiate-auth \
  --client-id "$COGNITO_CLIENT_ID" \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters "USERNAME=${TEST_USERNAME},PASSWORD=${TEST_PASSWORD}" \
  --region "$AWS_REGION" \
  --query 'AuthenticationResult.IdToken' \
  --output text)

if [ -z "$TOKEN" ] || [ "$TOKEN" = "None" ]; then
  echo "Failed to obtain auth token" >&2
  exit 1
fi

URL="${APIGW_URL}/api/sessions/${ORG}"
echo "Fetching $URL"
curl -sf "$URL" \
  -H "Authorization: Bearer ${TOKEN}" \
  | python3 -m json.tool > "$OUT_FILE"

echo "Wrote $OUT_FILE"
