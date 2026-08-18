#!/usr/bin/env bash
# Build the self-contained High worker. Pass --test for an import/runtime smoke.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/config.sh"

if ! docker run --rm --platform linux/arm64 --memory 256m --memory-swap 256m \
  public.ecr.aws/docker/library/busybox:1.36 true >/dev/null 2>&1; then
  echo "ERROR: arm64 execution is unavailable on this deployment host." >&2
  echo "Install binfmt, then retry: docker run --privileged --rm tonistiigi/binfmt --install arm64" >&2
  exit 1
fi

docker build --platform linux/arm64 --memory 8g \
  --build-arg "LOW_CODEX_VERSION=${CODEX_VERSION}" \
  --build-arg "HIGH_CODEX_VERSION=${HIGH_CODEX_VERSION}" \
  -f "$SERVER_DIR/Dockerfile.high" -t "$HIGH_WORKER_IMAGE" "$SERVER_DIR"

if [[ "${1:-}" == "--test" ]]; then
  docker run --rm --platform linux/arm64 --memory 8g --memory-swap 8g \
    "$HIGH_WORKER_IMAGE" python3 -c \
    'import high_worker, sys; sys.path.insert(0, "/app/high_pipeline"); import structured_pipeline, review_manifest, analytics_manifest, ecology_review'
fi

echo "High worker build passed."
