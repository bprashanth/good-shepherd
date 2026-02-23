#!/usr/bin/env bash
# Shared constants for deploy scripts.
# Cognito pool/client are fetched from S3 auth_config.json (same source as all apps).

export AWS_REGION="ap-south-1"
export AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text 2>/dev/null)"

# ECR
export ECR_REPO="form-idable-server"
export ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"

# Lambda
export LAMBDA_FUNCTION="form-idable-server"
export LAMBDA_ROLE_NAME="form-idable-lambda-role"

# API Gateway
export APIGW_NAME="form-idable-api"

# Cognito — fetch from S3 auth config (override URL via AUTH_CONFIG_URL env var)
export AUTH_CONFIG_URL="${AUTH_CONFIG_URL:-https://fomomon.s3.ap-south-1.amazonaws.com/auth_config.json}"

_auth_json=$(curl -sf "$AUTH_CONFIG_URL" 2>/dev/null || echo '{}')
_parse() { echo "$_auth_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('$1',''))" 2>/dev/null; }

export COGNITO_POOL_ID="${COGNITO_POOL_ID:-$(_parse userPoolId)}"
export COGNITO_CLIENT_ID="${COGNITO_CLIENT_ID:-$(_parse clientId)}"

if [ -z "$COGNITO_POOL_ID" ] || [ -z "$COGNITO_CLIENT_ID" ]; then
  echo "WARNING: Could not fetch Cognito config from ${AUTH_CONFIG_URL}" >&2
  echo "  Set COGNITO_POOL_ID and COGNITO_CLIENT_ID manually, or fix AUTH_CONFIG_URL" >&2
fi

export COGNITO_ISSUER="https://cognito-idp.${AWS_REGION}.amazonaws.com/${COGNITO_POOL_ID}"
