import argparse
import json
from utils import build_alias_map, normalize_field_name


def normalize_field(value, alias_map):
    if not value:
        return value
    norm = normalize_field_name(value)
    return alias_map.get(norm, value)


def main():
    parser = argparse.ArgumentParser(description="Normalize indicator config field names")
    parser.add_argument("--indicator-config", required=True)
    parser.add_argument("--variables-codebook", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    with open(args.variables_codebook, "r", encoding="utf-8") as f:
        codebook = json.load(f)
    alias_map = build_alias_map(codebook.get("variables", []))

    with open(args.indicator_config, "r", encoding="utf-8") as f:
        config = json.load(f)

    indicators = config.get("indicators", [])
    for indicator in indicators:
        for intent in indicator.get("graph_intents", []) or []:
            intent["x_axis"] = normalize_field(intent.get("x_axis"), alias_map)
            intent["y_axis"] = normalize_field(intent.get("y_axis"), alias_map)
            intent["group_by"] = normalize_field(intent.get("group_by"), alias_map)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


if __name__ == "__main__":
    main()
