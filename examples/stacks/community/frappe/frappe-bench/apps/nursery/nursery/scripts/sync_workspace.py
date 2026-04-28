import json
from pathlib import Path

import frappe


def sync_workspace():
    workspace_path = (
        Path(frappe.get_app_path("nursery"))
        / "nursery"
        / "workspace"
        / "nursery_home"
        / "nursery_home.json"
    )
    data = json.loads(workspace_path.read_text())
    for key in ("modified", "modified_by", "creation", "owner"):
        data.pop(key, None)

    if frappe.db.exists("Workspace", data["name"]):
        doc = frappe.get_doc("Workspace", data["name"])
    else:
        doc = frappe.new_doc("Workspace")

    doc.update(data)
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return f"Workspace synced: {data['name']}"
