import argparse
import json
from pathlib import Path

from utils import build_alias_map, normalize_field_name


def extract_values(rows, field_name, limit=5):
    values = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = row.get(field_name)
        if value is None:
            continue
        value = str(value).strip()
        if not value:
            continue
        values.append(value)
        if len(values) >= limit:
            break
    return values


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_catalog(forms_dir, alias_map=None):
    variables = []
    for json_path in sorted(Path(forms_dir).glob("*_classified.json")):
        data = load_json(json_path)
        rows = data.get("rows", [])

        # Universal fields
        for key, entry in (data.get("universal_fields") or {}).items():
            if key == "system":
                continue
            value = entry.get("value") if isinstance(entry, dict) else None
            example_values = []
            if value is not None:
                value = str(value).strip()
                if value:
                    example_values.append(value)
            canonical = alias_map.get(normalize_field_name(key), key) if alias_map else key
            variables.append(
                {
                    "name": canonical,
                    "source_form": json_path.name,
                    "field_name": key,
                    "unit": "",
                    "example_values": example_values,
                    "confidence": None,
                }
            )

        # Header fields from rows
        for key, header in (data.get("header_map") or {}).items():
            if key == "system":
                continue
            field_name = key
            if isinstance(header, dict):
                field_name = header.get("field_name") or key
            example_values = extract_values(rows, key)
            canonical = alias_map.get(normalize_field_name(key), key) if alias_map else key
            variables.append(
                {
                    "name": canonical,
                    "source_form": json_path.name,
                    "field_name": field_name,
                    "unit": "",
                    "example_values": example_values,
                    "confidence": None,
                }
            )

    return {"variables": variables}


def main():
    parser = argparse.ArgumentParser(description="Build variable catalog from form JSON")
    parser.add_argument("--forms-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--variables-codebook", default=None)
    args = parser.parse_args()

    alias_map = {}
    if args.variables_codebook:
        codebook = load_json(args.variables_codebook)
        alias_map = build_alias_map(codebook.get("variables", []))
    catalog = build_catalog(args.forms_dir, alias_map)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)


if __name__ == "__main__":
    main()
