#!/usr/bin/env bash
# Build the Docker image. Pass --test to run a local health-check smoke test
# (no Claude API calls — free, repeatable).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/config.sh"

if ! docker run --rm --platform linux/amd64 --memory 256m --memory-swap 256m \
  public.ecr.aws/docker/library/busybox:1.36 true >/dev/null 2>&1; then
  echo "ERROR: amd64 emulation is unavailable on this deployment host." >&2
  echo "Install binfmt, then retry: docker run --privileged --rm tonistiigi/binfmt --install amd64" >&2
  exit 1
fi

echo "=== Building ${IMAGE} (codex ${CODEX_VERSION}) ==="
docker build --platform linux/amd64 --memory 8g \
  --build-arg "CODEX_VERSION=${CODEX_VERSION}" -t "$IMAGE" "$SERVER_DIR"

if [ "${1:-}" = "--test" ]; then
  echo "=== Smoke test ==="
  RUN_ARGS=(-d --rm --memory 2g --memory-swap 2g -p 8081:8080)
  if [[ -f "$SERVER_DIR/.env" ]]; then
    RUN_ARGS+=(--env-file "$SERVER_DIR/.env")
  fi
  CONTAINER_ID=$(docker run --platform linux/amd64 "${RUN_ARGS[@]}" "$IMAGE")
  STATUS="000"
  for _attempt in $(seq 1 30); do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
      "http://localhost:8081${HEALTH_CHECK_PATH}" || true)
    [[ "$STATUS" == "200" ]] && break
    sleep 2
  done
  docker stop "$CONTAINER_ID" >/dev/null 2>&1 || true

  if [ "$STATUS" = "200" ]; then
    echo "  health check passed (HTTP ${STATUS})"
  else
    echo "  health check FAILED (HTTP ${STATUS}) — check HEALTH_CHECK_PATH in config.sh"
    exit 1
  fi
fi

echo "=== Build complete ==="
