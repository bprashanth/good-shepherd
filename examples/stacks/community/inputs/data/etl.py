import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import requests

BASE = Path(__file__).parent
DEFAULT_XLSX = BASE / "nursery_tracker.xlsx"
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
        "User-Agent": "nursery-etl/1.0",
    }


def frappe_url(path: str) -> str:
    base = get_env("FRAPPE_URL")
    return base.rstrip("/") + "/" + path.lstrip("/")


def read_sheet(xlsx_path: Path, name: str) -> pd.DataFrame:
    return pd.read_excel(xlsx_path, sheet_name=name)


def build_source_payload(row: Dict[str, Any], mapped_keys: set) -> Optional[str]:
    payload = {}
    for key, value in row.items():
        if key in mapped_keys:
            continue
        if pd.isna(value):
            continue
        payload[key] = normalize_value(value)
    if not payload:
        return None
    return json.dumps(payload, ensure_ascii=True)


def normalize_value(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    return value


def get_default_nursery(dry_run: bool = False) -> str:
    env_value = os.environ.get("NURSERY_NAME")
    if env_value:
        return env_value
    if dry_run:
        return "Auroville"
    existing = frappe_get(
        "Nursery",
        filters=[["Nursery", "nursery_name", "=", "Auroville"]],
        fields=["name"],
    )
    if existing:
        return existing[0]["name"]
    existing = frappe_get("Nursery", fields=["name"])
    if not existing:
        raise SystemExit("No Nursery found. Create one or set NURSERY_NAME.")
    return existing[0]["name"]


def get_section_id(section_name: str) -> Optional[str]:
    if not section_name:
        return None
    section_list = frappe_get(
        "Section",
        filters=[["Section", "section_name", "=", section_name]],
        fields=["name"],
    )
    if not section_list:
        return None
    return section_list[0]["name"]


def get_bed_id(section_name: str, bed_name: str) -> Optional[str]:
    if not section_name or not bed_name:
        return None
    section_id = get_section_id(section_name)
    if not section_id:
        return None
    bed_list = frappe_get(
        "Bed",
        filters=[
            ["Bed", "section", "=", section_id],
            ["Bed", "bed_name", "=", bed_name],
        ],
        fields=["name"],
    )
    if not bed_list:
        return None
    return bed_list[0]["name"]


def pick_batch_for_move(batches, event_date):
    if not batches:
        return None
    event_date = normalize_value(event_date)
    dated = []
    for batch in batches:
        date_sown = batch.get("date_sown")
        dated.append((date_sown, batch))
    dated.sort(key=lambda item: (item[0] is None, item[0]))
    if event_date:
        before = [b for d, b in dated if d and d <= event_date]
        if before:
            return before[-1]
    return dated[-1][1]


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


def upsert_species(xlsx_path: Path, dry_run: bool = False):
    df = read_sheet(xlsx_path, "speciesList").fillna("")
    created = 0
    updated = 0

    for _, row in df.iterrows():
        scientific_name = str(row.get("acceptedName") or "").strip()
        if not scientific_name:
            continue

        source_payload = build_source_payload(
            row.to_dict(),
            mapped_keys={"acceptedName", "ERAspeciesURL", "nameSource", "IUCNstatus"},
        )

        payload = {
            "doctype": "Species",
            "accepted_name": scientific_name,
            "era_species_url": str(row.get("ERAspeciesURL") or "").strip(),
            "name_source": str(row.get("nameSource") or "").strip(),
            "iucn_status": str(row.get("IUCNstatus") or "").strip(),
        }
        if source_payload:
            payload["source_payload_json"] = source_payload

        if dry_run:
            frappe_insert("Species", payload, dry_run=True)
            created += 1
            continue

        existing = frappe_get(
            "Species",
            filters=[["Species", "accepted_name", "=", scientific_name]],
            fields=["name"],
        )
        if existing:
            frappe_update("Species", existing[0]["name"], payload, dry_run=False)
            updated += 1
        else:
            frappe_insert("Species", payload, dry_run=False)
            created += 1

    print(f"Species: created={created} updated={updated}")


def upsert_collections(xlsx_path: Path, dry_run: bool = False):
    df = read_sheet(xlsx_path, "seedCollection").fillna("")
    created = 0
    updated = 0

    mapped = {
        "collectionID",
        "dateCollected",
        "species",
        "itemType",
        "condition",
        "seedSite",
        "gpsLatitude",
        "gpsLongitude",
        "gpsElevation",
        "locality",
        "collectedBy",
        "remarks",
        "deliveryDate",
    }

    for _, row in df.iterrows():
        collection_id = str(row.get("collectionID") or "").strip()
        if not collection_id:
            continue

        payload = {
            "doctype": "Collection",
            "collection_id": collection_id,
            "date_collected": normalize_value(row.get("dateCollected")),
            "species": str(row.get("species") or "").strip(),
            "item_type": str(row.get("itemType") or "").strip(),
            "condition": str(row.get("condition") or "").strip(),
            "seed_site": str(row.get("seedSite") or "").strip(),
            "gps_latitude": normalize_value(row.get("gpsLatitude")),
            "gps_longitude": normalize_value(row.get("gpsLongitude")),
            "gps_elevation": normalize_value(row.get("gpsElevation")),
            "locality": str(row.get("locality") or "").strip(),
            "collected_by": str(row.get("collectedBy") or "").strip(),
            "remarks": str(row.get("remarks") or "").strip(),
        }

        source_payload = build_source_payload(row.to_dict(), mapped_keys=mapped)
        if source_payload:
            payload["source_payload_json"] = source_payload

        if dry_run:
            frappe_insert("Collection", payload, dry_run=True)
            created += 1
            continue

        existing = frappe_get(
            "Collection",
            filters=[["Collection", "collection_id", "=", collection_id]],
            fields=["name"],
        )
        if existing:
            frappe_update("Collection", existing[0]["name"], payload, dry_run=False)
            updated += 1
        else:
            frappe_insert("Collection", payload, dry_run=False)
            created += 1

    print(f"Collections: created={created} updated={updated}")


def upsert_sections(xlsx_path: Path, nursery_name: str, dry_run: bool = False) -> Dict[str, str]:
    df = read_sheet(xlsx_path, "seedSowing").fillna("")
    sections = {}
    for value in df["section"].dropna().unique():
        section_name = str(value).strip()
        if not section_name:
            continue
        if section_name in sections:
            continue
        payload = {
            "doctype": "Section",
            "nursery": nursery_name,
            "section_name": section_name,
        }
        if dry_run:
            frappe_insert("Section", payload, dry_run=True)
            sections[section_name] = section_name
            continue
        existing = frappe_get(
            "Section",
            filters=[["Section", "section_name", "=", section_name]],
            fields=["name", "section_name"],
        )
        if existing:
            sections[section_name] = existing[0]["name"]
        else:
            created = frappe_insert("Section", payload, dry_run=False)
            if created:
                sections[section_name] = created.get("name")
    return sections


def upsert_beds(xlsx_path: Path, section_name_to_id: Dict[str, str], dry_run: bool = False) -> Dict[str, str]:
    df = read_sheet(xlsx_path, "seedSowing").fillna("")
    beds = {}
    for _, row in df.iterrows():
        section_name = str(row.get("section") or "").strip()
        bed_name = str(row.get("bedNo") or "").strip()
        if not section_name or not bed_name:
            continue
        key = f"{section_name}:{bed_name}"
        if key in beds:
            continue

        payload = {
            "doctype": "Bed",
            "section": section_name_to_id.get(section_name, section_name),
            "bed_name": bed_name,
            "bed_type": str(row.get("bedType") or "").strip(),
        }
        if dry_run:
            frappe_insert("Bed", payload, dry_run=True)
            beds[key] = key
            continue

        existing = frappe_get(
            "Bed",
            filters=[
                ["Bed", "section", "=", payload["section"]],
                ["Bed", "bed_name", "=", bed_name],
            ],
            fields=["name"],
        )
        if existing:
            beds[key] = existing[0]["name"]
        else:
            created = frappe_insert("Bed", payload, dry_run=False)
            if created:
                beds[key] = created.get("name")
    return beds


def upsert_batches(xlsx_path: Path, section_name_to_id: Dict[str, str], bed_key_to_id: Dict[str, str], dry_run: bool = False):
    df = read_sheet(xlsx_path, "seedSowing").fillna("")
    created = 0
    updated = 0

    mapped = {
        "batchID",
        "species",
        "goodSeeds",
        "fruitsByWt",
        "seedlings",
        "dateSown",
        "plantedBy",
        "section",
        "bedNo",
        "bedType",
        "remarks",
    }

    for _, row in df.iterrows():
        legacy_batch_id = str(row.get("batchID") or "").strip()
        if not legacy_batch_id:
            continue

        section_name = str(row.get("section") or "").strip()
        bed_name = str(row.get("bedNo") or "").strip()
        bed_key = f"{section_name}:{bed_name}"

        payload = {
            "doctype": "Batch",
            "species": str(row.get("species") or "").strip(),
            "legacy_batch_id": legacy_batch_id,
            "total_seeds": row.get("goodSeeds"),
            "date_sown": normalize_value(row.get("dateSown")),
            "planted_by": str(row.get("plantedBy") or "").strip(),
            "section": section_name_to_id.get(section_name, section_name),
            "stage": "sowing",
            "bed": bed_key_to_id.get(bed_key),
            "remarks": str(row.get("remarks") or "").strip(),
        }

        source_payload = build_source_payload(row.to_dict(), mapped_keys=mapped)
        if source_payload:
            payload["source_payload_json"] = source_payload

        if dry_run:
            frappe_insert("Batch", payload, dry_run=True)
            created += 1
            continue

        existing = frappe_get(
            "Batch",
            filters=[["Batch", "legacy_batch_id", "=", legacy_batch_id]],
            fields=["name"],
        )
        if existing:
            frappe_update("Batch", existing[0]["name"], payload, dry_run=False)
            updated += 1
        else:
            frappe_insert("Batch", payload, dry_run=False)
            created += 1

    print(f"Batches: created={created} updated={updated}")


def upsert_sowing(xlsx_path: Path, dry_run: bool = False):
    nursery_name = get_default_nursery(dry_run=dry_run)
    sections = upsert_sections(xlsx_path, nursery_name, dry_run=dry_run)
    beds = upsert_beds(xlsx_path, sections, dry_run=dry_run)
    upsert_batches(xlsx_path, sections, beds, dry_run=dry_run)


def upsert_allocations(xlsx_path: Path, dry_run: bool = False):
    collections = read_sheet(xlsx_path, "seedCollection").fillna("")
    collections = collections.sort_values("dateCollected")
    collection_map = {}
    for _, row in collections.iterrows():
        species = str(row.get("species") or "").strip()
        if not species:
            continue
        collection_id = str(row.get("collectionID") or "").strip()
        if not collection_id:
            continue
        if species not in collection_map:
            collection_map[species] = collection_id

    batches = frappe_get(
        "Batch",
        fields=["name", "species", "total_seeds"],
    )

    created = 0
    skipped = 0
    failed = 0
    for batch in batches:
        batch_name = batch.get("name")
        species = batch.get("species")
        if not batch_name or not species:
            skipped += 1
            continue
        collection_id = collection_map.get(species)
        if not collection_id:
            skipped += 1
            continue

        payload = {
            "doctype": "Batch Allocation",
            "parent": batch_name,
            "parenttype": "Batch",
            "parentfield": "allocations",
            "collection": collection_id,
            "quantity": batch.get("total_seeds") or 0,
        }

        if dry_run:
            frappe_insert("Batch Allocation", payload, dry_run=True)
            created += 1
            continue

        try:
            frappe_insert("Batch Allocation", payload, dry_run=False)
            created += 1
        except SystemExit as exc:
            failed += 1
            print(str(exc))

    print(f"Allocations: created={created} skipped={skipped} failed={failed}")


def upsert_germination_events(xlsx_path: Path, dry_run: bool = False):
    shifts = read_sheet(xlsx_path, "germinationShift").fillna("")
    created = 0
    failed = 0

    for _, row in shifts.iterrows():
        legacy_batch_id = str(row.get("batchID") or "").strip()
        if not legacy_batch_id:
            continue
        batch_list = frappe_get(
            "Batch",
            filters=[["Batch", "legacy_batch_id", "=", legacy_batch_id]],
            fields=["name", "total_seeds"],
        )
        if not batch_list:
            print(f"Missing batch for legacy_batch_id={legacy_batch_id}")
            failed += 1
            continue

        batch = batch_list[0]
        batch_name = batch.get("name")
        total_seeds = batch.get("total_seeds") or 0
        quantity = row.get("seedlingsShifted") or 0
        event_date = normalize_value(row.get("date"))

        base_payload = {
            "doctype": "Nursery Event",
            "batch": batch_name,
            "event_date": event_date,
            "quantity": quantity,
            "from_section": str(row.get("fromSection") or "").strip() or None,
            "from_bed": str(row.get("fromBedNo") or "").strip() or None,
            "to_section": str(row.get("toSection") or "").strip() or None,
            "to_bed": str(row.get("toBedNo") or "").strip() or None,
        }

        germ_payload = dict(base_payload)
        germ_payload["event_type"] = "germination"

        transplant_payload = dict(base_payload)
        transplant_payload["event_type"] = "transplant"

        failure_qty = None
        if total_seeds and quantity and total_seeds >= quantity:
            failure_qty = total_seeds - quantity

        if dry_run:
            frappe_insert("Nursery Event", germ_payload, dry_run=True)
            frappe_insert("Nursery Event", transplant_payload, dry_run=True)
            if failure_qty and failure_qty > 0:
                failure_payload = dict(base_payload)
                failure_payload["event_type"] = "failure"
                failure_payload["quantity"] = failure_qty
                frappe_insert("Nursery Event", failure_payload, dry_run=True)
            created += 1
            continue

        try:
            frappe_insert("Nursery Event", germ_payload, dry_run=False)
            frappe_insert("Nursery Event", transplant_payload, dry_run=False)
            if failure_qty and failure_qty > 0:
                failure_payload = dict(base_payload)
                failure_payload["event_type"] = "failure"
                failure_payload["quantity"] = failure_qty
                frappe_insert("Nursery Event", failure_payload, dry_run=False)
            frappe_update(
                "Batch",
                batch_name,
                {"stage": "growing"},
                dry_run=False,
            )
            created += 1
        except SystemExit as exc:
            failed += 1
            print(str(exc))

    print(f"Germination events: rows={len(shifts)} created={created} failed={failed}")


def upsert_move_events(xlsx_path: Path, dry_run: bool = False):
    moves = read_sheet(xlsx_path, "moving").fillna("")
    created = 0
    failed = 0

    mapped = {
        "date",
        "fromSection",
        "fromBedNo",
        "species",
        "moveType",
        "seedlingsShifted",
        "toSection",
        "toBedNo",
        "bedType",
    }

    for _, row in moves.iterrows():
        species = str(row.get("species") or "").strip()
        if not species:
            continue

        event_date = normalize_value(row.get("date"))
        quantity = row.get("seedlingsShifted") or 0
        from_section_name = str(row.get("fromSection") or "").strip()
        to_section_name = str(row.get("toSection") or "").strip()
        from_bed_name = str(row.get("fromBedNo") or "").strip()
        to_bed_name = str(row.get("toBedNo") or "").strip()

        from_section_id = get_section_id(from_section_name)
        to_section_id = get_section_id(to_section_name)
        from_bed_id = get_bed_id(from_section_name, from_bed_name)
        to_bed_id = get_bed_id(to_section_name, to_bed_name)

        batch_filters = [["Batch", "species", "=", species]]
        if from_bed_id:
            batch_filters.append(["Batch", "bed", "=", from_bed_id])
        elif from_section_id:
            batch_filters.append(["Batch", "section", "=", from_section_id])

        candidate_batches = frappe_get(
            "Batch",
            filters=batch_filters,
            fields=["name", "date_sown"],
        )
        batch = pick_batch_for_move(candidate_batches, event_date)
        if not batch:
            print(f"Missing batch for species={species} from={from_section_name}:{from_bed_name}")
            failed += 1
            continue

        payload = {
            "doctype": "Nursery Event",
            "batch": batch.get("name"),
            "event_type": "move",
            "event_date": event_date,
            "quantity": quantity,
            "from_section": from_section_id,
            "to_section": to_section_id,
            "from_bed": from_bed_id,
            "to_bed": to_bed_id,
        }

        source_payload = build_source_payload(row.to_dict(), mapped_keys=mapped)
        if source_payload:
            payload["source_payload_json"] = source_payload

        if dry_run:
            frappe_insert("Nursery Event", payload, dry_run=True)
            created += 1
            continue

        try:
            frappe_insert("Nursery Event", payload, dry_run=False)
            created += 1
        except SystemExit as exc:
            failed += 1
            print(str(exc))

    print(f"Move events: rows={len(moves)} created={created} failed={failed}")


def main():
    parser = argparse.ArgumentParser(description="Nursery ETL to Frappe")
    parser.add_argument("--input", default=str(DEFAULT_XLSX), help="Path to input XLSX")
    parser.add_argument("--env", default=str(DEFAULT_ENV), help="Path to .env file")
    parser.add_argument("--only", default=os.environ.get("ETL_ONLY", "species"))
    parser.add_argument("--dry-run", action="store_true", help="Print payloads without writing")
    args = parser.parse_args()

    load_env_file(Path(args.env))
    xlsx_path = Path(args.input)

    if args.only == "species":
        upsert_species(xlsx_path, dry_run=args.dry_run)
    elif args.only == "collections":
        upsert_collections(xlsx_path, dry_run=args.dry_run)
    elif args.only == "sowing":
        upsert_sowing(xlsx_path, dry_run=args.dry_run)
    elif args.only == "allocations":
        upsert_allocations(xlsx_path, dry_run=args.dry_run)
    elif args.only == "germination":
        upsert_germination_events(xlsx_path, dry_run=args.dry_run)
    elif args.only == "moving":
        upsert_move_events(xlsx_path, dry_run=args.dry_run)
    else:
        raise SystemExit(f"Unsupported --only value: {args.only}")


if __name__ == "__main__":
    main()
