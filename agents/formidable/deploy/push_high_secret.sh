#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

CONFIG_PATH="${FORMIDABLE_OPENROUTER_CONFIG:-$HOME/.config/formidable/openrouter.json}"
[ -f "$CONFIG_PATH" ] || { echo "ERROR: missing OpenRouter config: $CONFIG_PATH" >&2; exit 1; }
python3 - "$CONFIG_PATH" <<'PY'
import json, sys
value = json.load(open(sys.argv[1]))
assert value.get("api_key"), "gemini.json has no api_key"
PY

if aws secretsmanager describe-secret --secret-id "$HIGH_PROVIDER_SECRET_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
  aws secretsmanager put-secret-value --secret-id "$HIGH_PROVIDER_SECRET_NAME" \
    --secret-string "file://${CONFIG_PATH}" --region "$AWS_REGION" >/dev/null
else
  aws secretsmanager create-secret --name "$HIGH_PROVIDER_SECRET_NAME" \
    --secret-string "file://${CONFIG_PATH}" --region "$AWS_REGION" >/dev/null
fi
echo "High provider secret updated: ${HIGH_PROVIDER_SECRET_NAME}"
