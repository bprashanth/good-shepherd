#!/usr/bin/env bash
# Shared constants for deploy scripts.
# Reuses the existing form-idable-api API Gateway + cognito-jwt authorizer —
# does NOT create a new gateway. Cognito pool/client are fetched from S3
# auth_config.json (same source used by good-shepherd/server/deploy).

APP_NAME="form-idable-vision"
WORKER_APP_NAME="formidable-worker"
HIGH_WORKER_APP_NAME="formidable-high-worker"

export AWS_REGION="ap-south-1"
export AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text 2>/dev/null)"

# ECR — three repos, one per image
export ECR_REPO="${APP_NAME}"
export ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"
export WORKER_ECR_REPO="${WORKER_APP_NAME}"
export WORKER_ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${WORKER_ECR_REPO}"
export HIGH_WORKER_ECR_REPO="${HIGH_WORKER_APP_NAME}"
export HIGH_WORKER_ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${HIGH_WORKER_ECR_REPO}"

# Lambda
export LAMBDA_FUNCTION="${APP_NAME}"
export WORKER_FUNCTION="${WORKER_APP_NAME}"
export LAMBDA_ROLE_NAME="${APP_NAME}-role"
export IMAGE="${APP_NAME}:latest"
export WORKER_IMAGE="${WORKER_APP_NAME}:latest"
export HIGH_WORKER_IMAGE="${HIGH_WORKER_APP_NAME}:latest"
export HEALTH_CHECK_PATH="/vision/health"
export LAMBDA_MEMORY_MB=2048
export LAMBDA_TIMEOUT_S=600
export RESERVED_CONCURRENCY=10

# S3 — job input/output storage
export JOBS_BUCKET="formidable-storage"
export S3_PREFIX="formidable"

# DynamoDB — job metadata + user lookup
export DYNAMO_TABLE="formidable-jobs"

# Secrets Manager — codex auth.json
export SECRET_NAME="formidable/codex-auth"
export CODEX_SECRET_NAME="${CODEX_SECRET_NAME:-$SECRET_NAME}"
export HIGH_PROVIDER_SECRET_NAME="formidable/openrouter-api-key"

# codex CLI version — PINNED so the image is reproducible and matches the
# validated local Codex. Bump deliberately, run the full local evaluation gate,
# then use ./deploy.sh all so both production routes verify before acceptance.
export CODEX_VERSION="${CODEX_VERSION:-0.144.4}"
export HIGH_CODEX_VERSION="${HIGH_CODEX_VERSION:-0.147.0}"

# Fargate — worker task definition
export FARGATE_TASK_DEF="${WORKER_APP_NAME}"
export FARGATE_TASK_ROLE="${WORKER_APP_NAME}-task-role"
export FARGATE_LOG_GROUP="/ecs/${WORKER_APP_NAME}"
export FARGATE_CPU=2048
export FARGATE_MEMORY=4096
export HIGH_FARGATE_TASK_DEF="${HIGH_WORKER_APP_NAME}"
export HIGH_FARGATE_TASK_ROLE="${HIGH_WORKER_APP_NAME}-task-role"
export HIGH_FARGATE_LOG_GROUP="/ecs/${HIGH_WORKER_APP_NAME}"
export HIGH_FARGATE_CPU=2048
export HIGH_FARGATE_MEMORY=4096

# ── Email notifications (AWS SES) ────────────────────────────────────────────
# Uses the Fargate task's IAM role for auth — no API key needed.
#
# Setup:
#   1. Verify the FROM address (one-time, click link in email AWS sends):
#        aws ses verify-email-identity --email-address prashanth@tech4goodcommunity.com --region ap-south-1
#   2. SES sandbox (default): recipients must also be individually verified:
#        aws ses verify-email-identity --email-address user@gmail.com --region ap-south-1
#      To send to anyone, request production access:
#        AWS Console → SES → Account Dashboard → Request production access (~24h approval)
#   3. Apply updated Fargate task role policy (adds ses:SendEmail):
#        aws iam put-role-policy --role-name formidable-worker-task-role \
#          --policy-name formidable-worker-task-role-policy \
#          --policy-document file://fargate-task-policy.json
#   4. Run push.sh — re-registers task def with NOTIFICATION_FROM_EMAIL + PWA_URL
#
# To change the sender address: update NOTIFICATION_FROM_EMAIL and run push.sh.
export NOTIFICATION_FROM_EMAIL="prashanth@tech4goodcommunity.com"
# Update PWA_URL to your Netlify/production URL so emails link to the right place
export PWA_URL="https://fomoscribe.netlify.app"

# Shared ECS cluster (VPC, subnet, SG) — sourced last so it can reuse vars above
_CONFIG_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${_CONFIG_SCRIPT_DIR}/../../deploy/config.sh"

# API Gateway — reuse the existing shared gateway, do not create
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
