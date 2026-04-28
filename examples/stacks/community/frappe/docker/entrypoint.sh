#!/bin/bash
# Exit on error
set -e

# If the bench doesn't exist yet, init it
if [ ! -d "frappe-bench/sites" ]; then
    bench init --skip-redis-config-generation --frappe-branch version-15 frappe-bench --skip-assets
    cd frappe-bench
    bench config set-common-config -c redis_cache '"redis://redis:6379"'
    bench config set-common-config -c redis_queue '"redis://redis:6379"'
    bench config set-common-config -c redis_socketio '"redis://redis:6379"'
    bench new-site nursery.localhost --db-host mariadb --db-root-password admin --admin-password admin --force
else
    cd frappe-bench
fi

# Keep the bench updated with the apps in the 'apps' folder
bench build
bench start
