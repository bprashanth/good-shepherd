import argparse
import json
from pathlib import Path


def split_dbh_rows(records, dbh_prefix="DBH "):
    output = []
    for record in records:
        if record.get("plot_number") in {"Plot #", "plonum"}:
            continue
        dbh_values = []
        for key, value in record.items():
            if not key.startswith(dbh_prefix):
                continue
            if value is None or value == "":
                continue
            dbh_values.append((key, value))
        if not dbh_values:
            # Drop raw DBH columns if present and keep record as-is.
            record = {k: v for k, v in record.items() if not k.startswith(dbh_prefix)}
            output.append(record)
            continue
        for _, value in dbh_values:
            new_record = dict(record)
            for key, _ in dbh_values:
                new_record.pop(key, None)
            new_record["dbh_in_cms"] = value
            output.append(new_record)
    return output


def main():
    parser = argparse.ArgumentParser(description="Postprocess indicator dataset")
    parser.add_argument("--in", dest="input_path", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    data = json.loads(Path(args.input_path).read_text(encoding="utf-8"))
    records = data.get("records", [])

    records = split_dbh_rows(records)

    Path(args.out).write_text(json.dumps({"records": records}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
