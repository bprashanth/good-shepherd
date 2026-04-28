import argparse
import json
from pathlib import Path

import pandas as pd


SKIP_SHEET_NAMES = {"read me", "readme", "read me "}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_form_fields(forms_dir):
    fields = []
    for json_path in sorted(Path(forms_dir).glob("*_classified.json")):
        data = load_json(json_path)
        for key in (data.get("universal_fields") or {}).keys():
            if key == "system":
                continue
            fields.append({"name": key, "source": f"form:{json_path.name}"})
        for key in (data.get("header_map") or {}).keys():
            if key == "system":
                continue
            fields.append({"name": key, "source": f"form:{json_path.name}"})
    return fields


def extract_excel_fields(xlsx_path):
    fields = []
    if not xlsx_path:
        return fields
    xlsx = pd.ExcelFile(xlsx_path)
    for sheet_name in xlsx.sheet_names:
        if sheet_name.strip().lower() in SKIP_SHEET_NAMES:
            continue
        df = xlsx.parse(sheet_name)
        df = df.dropna(how="all")
        df = df.dropna(axis=1, how="all")
        if df.empty:
            continue
        for col in df.columns:
            fields.append({"name": str(col), "source": f"excel:{sheet_name}"})
    return fields


def main():
    parser = argparse.ArgumentParser(description="Extract field sources from forms and excel")
    parser.add_argument("--forms-dir", required=True)
    parser.add_argument("--xlsx", default=None)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    payload = {
        "form_fields": extract_form_fields(args.forms_dir),
        "excel_fields": extract_excel_fields(args.xlsx),
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


if __name__ == "__main__":
    main()
