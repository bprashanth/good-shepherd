docker exec -it -w /home/frappe/project/frappe-bench nursery_frappe bash -lc "bench --site nursery.localhost console" <<'PY'
import json
from pathlib import Path
import frappe

p = Path("apps/nursery/nursery/workspace/nursery_home/nursery_home.json")
data = json.loads(p.read_text())

if frappe.db.exists("Workspace", data["name"]):
doc = frappe.get_doc("Workspace", data["name"])
else:
doc = frappe.new_doc("Workspace")

doc.update(data)
doc.save(ignore_permissions=True)
frappe.db.commit()
print("Workspace synced:", data["name"])
PY

