#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: test/get_sites.sh --org <org> [--out <path>] [--bucket <bucket>]

Fetches the sites payload for the given org and writes it to disk.

Examples:
  test/get_sites.sh --org ncf
  test/get_sites.sh --org t4gc --out /tmp/t4gc.sites.json
  test/get_sites.sh --org ncf --bucket fomomon
EOF
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/../deploy" && pwd)"

ORG=""
OUT_FILE=""
BUCKET="fomomon"

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
    --bucket)
      shift
      [ "$#" -gt 0 ] || { echo "--bucket requires a value" >&2; usage; exit 1; }
      BUCKET="$1"
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
  OUT_FILE="$SCRIPT_DIR/photomon/sites.${ORG}.fresh.json"
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

URL="${APIGW_URL}/api/sites/${ORG}?bucket=${BUCKET}"
echo "Fetching $URL"

RAW_FILE="${OUT_FILE}.raw"
if ! curl -sS -f "$URL" \
  -H "Authorization: Bearer ${TOKEN}" \
  > "$RAW_FILE"; then
  STATUS=$?
  echo "Request failed for $URL (curl exit $STATUS)" >&2
  if [ -s "$RAW_FILE" ]; then
    echo "Raw response preview:" >&2
    head -c 1000 "$RAW_FILE" >&2
    echo >&2
  fi
  rm -f "$RAW_FILE"
  exit "$STATUS"
fi

python3 - <<'PY' "$RAW_FILE" "$OUT_FILE"
import json
import pathlib
import sys

raw_path = pathlib.Path(sys.argv[1])
out_path = pathlib.Path(sys.argv[2])
raw_text = raw_path.read_text()

try:
    parsed = json.loads(raw_text)
except json.JSONDecodeError as exc:
    preview = raw_text[:1000]
    print(f"Sites endpoint did not return valid JSON: {exc}", file=sys.stderr)
    if preview:
        print("Raw response preview:", file=sys.stderr)
        print(preview, file=sys.stderr)
    else:
        print("Raw response was empty.", file=sys.stderr)
    sys.exit(1)

out_path.write_text(json.dumps(parsed, indent=2) + "\n")
raw_path.unlink(missing_ok=True)
PY

echo "Wrote $OUT_FILE"
