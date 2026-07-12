#!/usr/bin/env bash
# Copy an ECR image tag: _retag.sh <repo> <src-tag> <dst-tag>
# Points <dst-tag> at whatever image <src-tag> currently references, moving it if
# <dst-tag> already exists (ECR MUTABLE tags). Exits non-zero if <src-tag> is
# absent (e.g. first-ever push, no :latest yet) so callers can `|| true`.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config.sh"

REPO="${1:?repo}"; SRC="${2:?src-tag}"; DST="${3:?dst-tag}"

MANIFEST=$(aws ecr batch-get-image \
  --repository-name "$REPO" --image-ids "imageTag=${SRC}" \
  --query 'images[0].imageManifest' --output text --region "$AWS_REGION" 2>/dev/null || echo "None")

if [ "$MANIFEST" = "None" ] || [ -z "$MANIFEST" ]; then
  echo "  _retag: ${REPO}:${SRC} not found — skipping (${DST} unchanged)"
  exit 1
fi

# put-image with an existing tag + different digest can fail; delete then re-put.
if ! aws ecr put-image --repository-name "$REPO" --image-tag "$DST" \
       --image-manifest "$MANIFEST" --region "$AWS_REGION" >/dev/null 2>&1; then
  aws ecr batch-delete-image --repository-name "$REPO" \
    --image-ids "imageTag=${DST}" --region "$AWS_REGION" >/dev/null 2>&1 || true
  aws ecr put-image --repository-name "$REPO" --image-tag "$DST" \
    --image-manifest "$MANIFEST" --region "$AWS_REGION" >/dev/null
fi
echo "  _retag: ${REPO}:${SRC} → :${DST}"
