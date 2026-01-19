import argparse
import json
from pathlib import Path

import pandas as pd
from utils import build_alias_map, normalize_field_name


SKIP_SHEET_NAMES = {"read me", "readme", "read me "}


def normalize_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return value


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def apply_aliases(record, alias_map):
    if not alias_map:
        return record
    remapped = {}
    for key, value in record.items():
        norm = normalize_field_name(key)
        canonical = alias_map.get(norm, key)
        if canonical in remapped and remapped[canonical] not in (None, ""):
            if value not in (None, ""):
                remapped[key] = value
            continue
        remapped[canonical] = value
    return remapped


def extract_form_records(forms_dir):
    records = []
    for json_path in sorted(Path(forms_dir).glob("*_classified.json")):
        data = load_json(json_path)
        universal_fields = data.get("universal_fields") or {}
        base = {}
        for key, entry in universal_fields.items():
            if key == "system":
                continue
            if isinstance(entry, dict):
                base[key] = entry.get("value")

        rows = data.get("rows") or []
        for row in rows:
            if not isinstance(row, dict):
                continue
            record = dict(base)
            for key, value in row.items():
                if key == "system" or key.startswith("col_"):
                    continue
                record[key] = value
            sys_meta = row.get("system") or {}
            record["row_index"] = sys_meta.get("row_index")
            record["source_type"] = "form"
            record["source_file"] = json_path.name
            records.append(record)
    return records


def extract_excel_records(xlsx_path):
    records = []
    if not xlsx_path:
        return records
    xlsx = pd.ExcelFile(xlsx_path)
    for sheet_name in xlsx.sheet_names:
        if sheet_name.strip().lower() in SKIP_SHEET_NAMES:
            continue
        df = xlsx.parse(sheet_name)
        df = df.dropna(how="all")
        df = df.dropna(axis=1, how="all")
        if df.empty:
            continue
        for idx, row in df.iterrows():
            record = {col: normalize_value(row[col]) for col in df.columns}
            if not any(v not in (None, "") for v in record.values()):
                continue
            record["row_index"] = int(idx)
            record["source_type"] = "excel"
            record["source_file"] = Path(xlsx_path).name
            record["sheet_name"] = sheet_name
            records.append(record)
    return records


def normalize_records(records, alias_map=None):
    all_keys = set()
    for record in records:
        record = apply_aliases(record, alias_map)
        all_keys.update(record.keys())
    normalized = []
    for i, record in enumerate(records, start=1):
        record = apply_aliases(record, alias_map)
        full_record = {key: record.get(key) for key in all_keys}
        full_record["record_id"] = i
        normalized.append(full_record)
    return normalized


def main():
    parser = argparse.ArgumentParser(description="Build indicator dataset from forms and excel")
    parser.add_argument("--forms-dir", required=True)
    parser.add_argument("--xlsx", default=None)
    parser.add_argument("--variables-codebook", default=None)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    records = []
    # records.extend(extract_form_records(args.forms_dir))
    records.extend(extract_excel_records(args.xlsx))

    alias_map = {}
    if args.variables_codebook:
        codebook = load_json(args.variables_codebook)
        alias_map = build_alias_map(codebook.get("variables", []))

    normalized = normalize_records(records, alias_map)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"records": normalized}, f, indent=2)


if __name__ == "__main__":
    main()
