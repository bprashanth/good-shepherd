#!/usr/bin/env bash
# ECR login, tag, push, create/update Lambda function.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

IMAGE="form-idable-server:latest"

echo "=== ECR login ==="
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "=== Tag + push ==="
docker tag "$IMAGE" "${ECR_URI}:latest"
docker push "${ECR_URI}:latest"

echo "=== Lambda function: ${LAMBDA_FUNCTION} ==="
ROLE_ARN=$(aws iam get-role --role-name "$LAMBDA_ROLE_NAME" --query 'Role.Arn' --output text)

LAMBDA_ENV='Variables={AWS_LWA_REMOVE_BASE_PATH=/prod}'

if aws lambda get-function --function-name "$LAMBDA_FUNCTION" --region "$AWS_REGION" &>/dev/null; then
  echo "  updating function code..."
  aws lambda update-function-code \
    --function-name "$LAMBDA_FUNCTION" \
    --image-uri "${ECR_URI}:latest" \
    --region "$AWS_REGION" \
    --output text >/dev/null
else
  echo "  creating function..."
  aws lambda create-function \
    --function-name "$LAMBDA_FUNCTION" \
    --package-type Image \
    --code "ImageUri=${ECR_URI}:latest" \
    --role "$ROLE_ARN" \
    --environment "$LAMBDA_ENV" \
    --memory-size 512 \
    --timeout 60 \
    --region "$AWS_REGION" \
    --output text >/dev/null
fi

echo "  waiting for function to be active..."
aws lambda wait function-active-v2 \
  --function-name "$LAMBDA_FUNCTION" \
  --region "$AWS_REGION"

# Ensure env var is set (idempotent — covers existing functions)
echo "  setting environment..."
aws lambda wait function-updated-v2 \
  --function-name "$LAMBDA_FUNCTION" \
  --region "$AWS_REGION" 2>/dev/null || true
aws lambda update-function-configuration \
  --function-name "$LAMBDA_FUNCTION" \
  --environment "$LAMBDA_ENV" \
  --region "$AWS_REGION" \
  --output text >/dev/null
aws lambda wait function-updated-v2 \
  --function-name "$LAMBDA_FUNCTION" \
  --region "$AWS_REGION"

# Grant API Gateway invoke permission (idempotent — fails silently if exists)
if [ -f "$SCRIPT_DIR/outputs.env" ]; then
  source "$SCRIPT_DIR/outputs.env"
  echo "  setting API Gateway invoke permission..."
  aws lambda add-permission \
    --function-name "$LAMBDA_FUNCTION" \
    --statement-id "apigw-invoke" \
    --action "lambda:InvokeFunction" \
    --principal "apigateway.amazonaws.com" \
    --source-arn "arn:aws:execute-api:${AWS_REGION}:${AWS_ACCOUNT_ID}:${APIGW_ID}/*" \
    --region "$AWS_REGION" 2>/dev/null || echo "  permission already exists"
fi

echo "=== Push complete ==="
