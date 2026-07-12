#!/usr/bin/env bash
# Build the Docker image. Pass --test to run a local health-check smoke test
# (no Claude API calls — free, repeatable).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/config.sh"

echo "=== Building ${IMAGE} (codex ${CODEX_VERSION}) ==="
docker build --build-arg "CODEX_VERSION=${CODEX_VERSION}" -t "$IMAGE" "$SERVER_DIR"

if [ "${1:-}" = "--test" ]; then
  echo "=== Smoke test ==="
  CONTAINER_ID=$(docker run -d --rm -p 8081:8080 --env-file "$SERVER_DIR/.env" "$IMAGE")
  sleep 5

  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    "http://localhost:8081${HEALTH_CHECK_PATH}" || echo "000")
  docker stop "$CONTAINER_ID" >/dev/null 2>&1 || true

  if [ "$STATUS" = "200" ]; then
    echo "  health check passed (HTTP ${STATUS})"
  else
    echo "  health check FAILED (HTTP ${STATUS}) — check HEALTH_CHECK_PATH in config.sh"
    exit 1
  fi
fi

echo "=== Build complete ==="
