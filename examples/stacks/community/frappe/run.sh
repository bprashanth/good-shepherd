#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker/docker-compose.yml"

usage() {
  echo "Usage: $0 {start|stop|logs}"
  exit 1
}

start_stack() {
  docker compose -f "$COMPOSE_FILE" up -d db redis-cache redis-queue
  docker compose -f "$COMPOSE_FILE" run --rm configurator
  if [ ! -d "$ROOT_DIR/apps/erpnext" ]; then
    docker compose -f "$COMPOSE_FILE" run --rm backend bench get-app erpnext --branch version-15
  fi
  if [ ! -f "$ROOT_DIR/sites/frontend/site_config.json" ]; then
    docker compose -f "$COMPOSE_FILE" run --rm create-site
  else
    echo "Site 'frontend' already exists; skipping create-site."
  fi
  docker compose -f "$COMPOSE_FILE" up -d backend frontend websocket queue-long queue-short scheduler
}

stop_stack() {
  docker compose -f "$COMPOSE_FILE" down
}

logs_stack() {
  docker compose -f "$COMPOSE_FILE" logs --tail=200 backend
}

case "${1:-}" in
  start)
    start_stack
    ;;
  stop)
    stop_stack
    ;;
  logs)
    logs_stack
    ;;
  *)
    usage
    ;;
esac
