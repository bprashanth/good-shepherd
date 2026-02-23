#!/usr/bin/env bash
# Build Docker image + optional smoke test.
# Usage: ./build.sh [--test]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/config.sh"

IMAGE="form-idable-server:latest"

echo "=== Building ${IMAGE} ==="
docker build -t "$IMAGE" "$SERVER_DIR"

if [ "${1:-}" = "--test" ]; then
  echo "=== Smoke test ==="
  CONTAINER_ID=$(docker run -d --rm -p 8071:8070 "$IMAGE")
  sleep 10

  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8071/api/health || echo "000")
  docker stop "$CONTAINER_ID" >/dev/null 2>&1 || true

  if [ "$STATUS" = "200" ]; then
    echo "  health check passed (HTTP ${STATUS})"
  else
    echo "  health check FAILED (HTTP ${STATUS})"
    exit 1
  fi
fi

echo "=== Build complete ==="
