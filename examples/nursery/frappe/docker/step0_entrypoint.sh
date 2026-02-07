#!/bin/bash
set -e

# THIS is the path relative to the container's mount point
BENCH_DIR="/home/frappe/project/frappe-bench"

# TODO(prashanth@): nc -z $DB_HOST $DB_PORT is preferred but the baseimage doesn't have nc 
# But why do we even need to scout in the first place? 
# Because "depends" in the docker compose dosn't save us. Depends only guards against the 
# container starting, not the maria within the container accepting connections. 
echo "Scouting MariaDB at $DB_HOST:$DB_PORT..."
# Attempt to open a socket to the DB host/port
until (echo > /dev/tcp/$DB_HOST/$DB_PORT) >/dev/null 2>&1; do
  echo "MariaDB is still deep in meditation... waiting 2 seconds."
  sleep 2
done
echo "MariaDB has awakened. Proceeding with the Forge."

# 1. Forge only if the Bench hasn't been initialized
if [ ! -d "$BENCH_DIR/env" ]; then
    echo "--- Phase 1: Forging Bench onto Host Mount ---"
    
    # Move to the project root where the volume is mounted
    cd /home/frappe/project
    
    # Initialize the bench. This creates the 'frappe-bench' folder ON YOUR HOST.
    bench init --skip-redis-config-generation --frappe-branch version-15 frappe-bench
fi

# 2. Enter the bench (using the full path to be safe)
cd "$BENCH_DIR"

echo "--- Phase 2: Configuring Redis ---"
bench config set-common-config -c redis_cache '"redis://redis:6379"'
bench config set-common-config -c redis_queue '"redis://redis:6379"'
bench config set-common-config -c redis_socketio '"redis://redis:6379"'

echo "--- Phase 3: Creating Site & App ---"
if [ ! -d "sites/nursery.localhost" ]; then
    bench new-site nursery.localhost --db-host mariadb --db-root-password admin --admin-password admin --force
else
    echo "Nursery site found in repository, skipping creation."
fi 

if [ ! -d "apps/nursery" ]; then
    # We add two 'n's at the end to say NO to GitHub Actions and any other fluff
    echo -e "Nursery\nEcology\nDesiNotorious\nadmin@nursery.localhost\nmit\nn\nn" | bench new-app nursery --no-git
else
    echo "Nursery app found in repository, skipping creation."
fi

bench --site nursery.localhost install-app nursery
bench --site nursery.localhost set-config developer_mode 1

echo "--- Ignition ---"
bench start
