import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import requests

BASE = Path(__file__).parent
DEFAULT_XLSX = BASE / "Auroville protocol data.xlsx"
DEFAULT_ENV = BASE / ".env"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def get_env(name: str, default: Optional[str] = None) -> str:
    value = os.environ.get(name, default)
    if not value:
        raise SystemExit(f"Missing required env var: {name}")
    return value


def frappe_headers() -> Dict[str, str]:
    api_key = get_env("FRAPPE_API_KEY")
    api_secret = get_env("FRAPPE_API_SECRET")
    return {
        "Authorization": f"token {api_key}:{api_secret}",
        "Accept": "application/json",
        "Expect": "",
        "User-Agent": "nursery-protocols/1.0",
    }


def frappe_url(path: str) -> str:
    base = get_env("FRAPPE_URL")
    return base.rstrip("/") + "/" + path.lstrip("/")


def normalize_value(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, float) and pd.isna(value):
        return None
    return value


def frappe_get(doctype: str, filters: Optional[list] = None, fields: Optional[list] = None):
    params = {}
    if filters:
        params["filters"] = json.dumps(filters)
    if fields:
        params["fields"] = json.dumps(fields)
    resp = requests.get(
        frappe_url(f"api/resource/{doctype}"),
        headers=frappe_headers(),
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def frappe_insert(doctype: str, payload: Dict[str, Any], dry_run: bool = False):
    if dry_run:
        print(f"[DRY-RUN] insert {doctype}: {payload}")
        return None
    resp = requests.post(
        frappe_url(f"api/resource/{doctype}"),
        headers=frappe_headers(),
        json=payload,
        timeout=30,
    )
    if resp.status_code == 409:
        return None
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        raise SystemExit(f"Insert {doctype} failed: {resp.status_code} {resp.text}") from exc
    return resp.json().get("data")


def frappe_update(doctype: str, name: str, payload: Dict[str, Any], dry_run: bool = False):
    if dry_run:
        print(f"[DRY-RUN] update {doctype} {name}: {payload}")
        return None
    resp = requests.put(
        frappe_url(f"api/resource/{doctype}/{name}"),
        headers=frappe_headers(),
        json=payload,
        timeout=30,
    )
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        raise SystemExit(f"Update {doctype} {name} failed: {resp.status_code} {resp.text}") from exc
    return resp.json().get("data")


def upsert_species_protocols(xlsx_path: Path, dry_run: bool = False):
    df = pd.read_excel(xlsx_path, sheet_name="Sheet1").fillna("")
    created = 0
    updated = 0

    for _, row in df.iterrows():
        scientific_name = str(row.get("Species") or "").strip()
        if not scientific_name:
            continue

        payload = {
            "doctype": "Species",
            "accepted_name": scientific_name,
            "processing": str(row.get("Cleaning and Sowing") or "").strip(),
            "germination_time": str(row.get("Germination time") or "").strip(),
            "germination_percent": normalize_value(row.get("Germination %")),
        }

        existing = frappe_get(
            "Species",
            filters=[["Species", "accepted_name", "=", scientific_name]],
            fields=["name"],
        )
        if existing:
            frappe_update("Species", existing[0]["name"], payload, dry_run=dry_run)
            updated += 1
        else:
            frappe_insert("Species", payload, dry_run=dry_run)
            created += 1

    print(f"Protocols: created={created} updated={updated}")


def main():
    parser = argparse.ArgumentParser(description="Update species protocols from Auroville sheet")
    parser.add_argument("--input", default=str(DEFAULT_XLSX), help="Path to input XLSX")
    parser.add_argument("--env", default=str(DEFAULT_ENV), help="Path to .env file")
    parser.add_argument("--dry-run", action="store_true", help="Print payloads without writing")
    args = parser.parse_args()

    load_env_file(Path(args.env))
    upsert_species_protocols(Path(args.input), dry_run=args.dry_run)


if __name__ == "__main__":
    main()
