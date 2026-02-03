#!/usr/bin/env bash
set -euo pipefail

BENCH_DIR="/home/frappe/frappe-bench"
SITES_DIR="${BENCH_DIR}/sites"
COMMON_CFG="${SITES_DIR}/common_site_config.json"

mkdir -p "${BENCH_DIR}"
chown -R frappe:frappe "${BENCH_DIR}" || true

if [ ! -f "${BENCH_DIR}/Procfile" ]; then
  TMP_BENCH="/tmp/bench-init"
  rm -rf "${TMP_BENCH}"
  FRAPPE_BRANCH="${FRAPPE_BRANCH:-version-15}"
  PYTHON_BIN="${FRAPPE_PYTHON:-python3.11}"
  su frappe -c "bench init --frappe-branch ${FRAPPE_BRANCH} --skip-redis-config-generation --skip-assets --python ${PYTHON_BIN} ${TMP_BENCH}"
  cp -a "${TMP_BENCH}/." "${BENCH_DIR}/"
  chown -R frappe:frappe "${BENCH_DIR}" || true
fi

if [ ! -x "${BENCH_DIR}/env/bin/bench" ]; then
  "${FRAPPE_PYTHON:-python3.11}" -m venv "${BENCH_DIR}/env"
  "${BENCH_DIR}/env/bin/pip" install --upgrade pip setuptools wheel
  "${BENCH_DIR}/env/bin/pip" install --upgrade frappe-bench
  chown -R frappe:frappe "${BENCH_DIR}/env" || true
fi

cd "${BENCH_DIR}"

mkdir -p "${SITES_DIR}"
cat > "${COMMON_CFG}" <<JSON
{
  "db_host": "${DB_HOST}",
  "db_port": ${DB_PORT:-3306},
  "redis_cache": "redis://${REDIS_CACHE}",
  "redis_queue": "redis://${REDIS_QUEUE}",
  "redis_socketio": "redis://${REDIS_SOCKETIO}",
  "socketio_port": ${SOCKETIO_PORT:-9000}
}
JSON

exec su frappe -c "cd ${BENCH_DIR} && ${BENCH_DIR}/env/bin/bench start"
