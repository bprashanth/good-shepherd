#!/usr/bin/env bash
set -euo pipefail

SITE=${1:-nursery.localhost}
USER=${2:-Administrator}

# Generates and prints API key + secret for a user.
# Requires the Frappe container to be running.

docker exec -i -w /home/frappe/project/frappe-bench nursery_frappe bash -lc "bench --site ${SITE} console" <<PY
import frappe
from frappe.utils.password import set_encrypted_password
user = "${USER}"
api_key = frappe.generate_hash(length=15)
api_secret = frappe.generate_hash(length=15)
frappe.db.set_value("User", user, "api_key", api_key)
set_encrypted_password("User", user, api_secret, "api_secret")
frappe.db.commit()
print("API_KEY=", api_key)
print("API_SECRET=", api_secret)
PY
