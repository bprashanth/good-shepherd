#!/bin/bash
cd "$(dirname "$0")/.." || exit

echo "--- 1. Purging Host Workspace ---"
docker compose -f docker/step0_docker-compose.yml down -v
# Completely remove the bench folder from your Pop!_OS host
sudo rm -rf frappe-bench/

echo "--- 2. Preparing Data directory ---"
mkdir -p mariadb_data
chmod 777 mariadb_data

echo "--- 3. Starting the Forge ---"
# We don't need to mkdir; bench init will create it on the host via the mount
docker compose -f docker/step0_docker-compose.yml up -d
docker logs nursery_frappe --follow
