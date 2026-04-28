import argparse
import json
import re
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_species_list(english_intent):
    if not english_intent:
        return []
    # Try to extract a comma-separated list after keywords like "values" or "species".
    match = re.search(r"values?\s+([^\n]+)", english_intent, re.IGNORECASE)
    if not match:
        match = re.search(r"species\s+([^\n]+)", english_intent, re.IGNORECASE)
    if not match:
        return []
    chunk = match.group(1)
    chunk = chunk.split("and return")[0]
    chunk = chunk.replace(" and ", ",")
    items = [s.strip().strip("'\"") for s in chunk.split(",") if s.strip()]
    return items


def normalize_species(series):
    return series.fillna("").astype(str).str.strip()


def to_numeric(series):
    return pd.to_numeric(series.astype(str).str.replace(r"[^0-9.]", "", regex=True), errors="coerce")


def parse_jsonlogic_code(compiled):
    if not compiled:
        return None
    code = compiled.get("code")
    if isinstance(code, dict):
        return code
    if isinstance(code, str):
        try:
            return json.loads(code)
        except json.JSONDecodeError:
            return None
    return None


def extract_in_list(rule):
    # Expect {"in": [{"var":"spp_name_local_name"}, [..]]}
    if not isinstance(rule, dict):
        return []
    if "in" in rule and isinstance(rule["in"], list) and len(rule["in"]) == 2:
        _, values = rule["in"]
        if isinstance(values, list):
            return values
    return []


def build_computed(df, codebook):
    computed_map = {c.get("name"): c for c in codebook.get("computed_variables", {}).get("computed_variables", [])}

    def species_matcher(name):
        comp = computed_map.get(name)
        if not comp:
            return None, []
        intent = comp.get("english_intent", "")
        species_list = parse_species_list(intent)
        if "cestrum" in intent.lower():
            return "cestrum", species_list
        return None, species_list

    spp = normalize_species(df.get("spp_name_local_name"))
    dbh = to_numeric(df.get("dbh_in_cms"))
    seedlings = to_numeric(df.get("number_seedlings"))
    saplings = to_numeric(df.get("number_saplings"))
    habit = normalize_species(df.get("habit"))

    # Resilience growth
    growth_comp = computed_map.get("native_species_growth", {})
    growth_rule = parse_jsonlogic_code(growth_comp.get("compiled", {}))
    native_mask = pd.Series(False, index=df.index)
    if growth_rule and "if" in growth_rule:
        condition = growth_rule["if"][0]
        if "!=" in condition:
            left, right = condition["!="]
            if isinstance(left, dict) and left.get("var") == "spp_name_local_name":
                native_mask = spp != str(right)
        else:
            values = extract_in_list(condition)
            if values:
                native_mask = spp.isin(values)
    else:
        _, native_list = species_matcher("native_species_growth")
        if native_list:
            native_mask = spp.isin(native_list)
    df["native_species_growth"] = dbh.where(native_mask)

    # Resilience survival
    survival_comp = computed_map.get("native_species_survival", {})
    survival_rule = parse_jsonlogic_code(survival_comp.get("compiled", {}))
    survival_mask = native_mask
    if survival_rule and "if" in survival_rule:
        condition = survival_rule["if"][0]
        if "in" in condition:
            values = extract_in_list(condition)
            if values:
                survival_mask = spp.isin(values)
        if "!=" in condition:
            left, right = condition["!="]
            if isinstance(left, dict) and left.get("var") == "spp_name_local_name":
                survival_mask = spp != str(right)
    df["native_species_survival"] = survival_mask.astype(int)

    # Invasive recovery components
    cestrum_token = None
    for name in ["c_aurantiacum_mature_count", "c_aurantiacum_recruit_count"]:
        comp = computed_map.get(name, {})
        compiled = comp.get("compiled", {})
        if compiled.get("language") == "js":
            code = compiled.get("code", "")
            match = re.search(r"includes\\(['\\\"]([^'\\\"]+)['\\\"]\\)", code)
            if match:
                cestrum_token = match.group(1)
                break
    if not cestrum_token:
        _, cestrum_list = species_matcher("c_aurantiacum_mature_count")
        if cestrum_list:
            cestrum_mask = spp.isin(cestrum_list)
        else:
            cestrum_mask = spp.str.contains("cesaur", case=False, na=False)
    else:
        cestrum_mask = spp.str.contains(cestrum_token, case=False, na=False)
    df["c_aurantiacum_mature_count"] = ((cestrum_mask) & (dbh > 0)).astype(int)
    df["c_aurantiacum_recruit_count"] = ((seedlings.fillna(0) + saplings.fillna(0)) * cestrum_mask.astype(int))

    # Biodiversity gains uses spp_name_local_name directly in aggregation

    return df


def plot_indicators(df, codebook, out_path, top_n):
    indicators = {
        i.get("name"): i
        for i in codebook.get("indicator_config", {}).get("indicators", [])
    }

    def ensure_plot_number(data):
        if "plot_number" not in data.columns and "plot_no" in data.columns:
            data = data.copy()
            data["plot_number"] = data["plot_no"]
        return data

    def aggregate_series(data, y_axis, group_by, aggregation):
        data = ensure_plot_number(data)
        if y_axis == "species_richness":
            grouped = data[data["spp_name_local_name"].notna()].groupby(group_by)["spp_name_local_name"].nunique()
            return grouped
        series = data[y_axis]
        grouped = series.groupby(data[group_by])
        return grouped.agg(aggregation)

    output_base = Path(out_path)
    indicator_names = [
        "Resilience.growth",
        "Resilience.survival",
        "Invasive Recovery",
        "Biodiversity Gains",
    ]

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    axes = axes.ravel()

    for ax, name in zip(axes, indicator_names):
        indicator = indicators.get(name, {})
        intent = (indicator.get("graph_intents") or [{}])[0]
        chart_type = intent.get("chart_type", "bar")
        x_axis = intent.get("x_axis", "plot_number")
        y_axis = intent.get("y_axis")
        group_by = intent.get("group_by", x_axis)
        aggregation = intent.get("aggregation", "mean")

        data = ensure_plot_number(df)
        data = data[data["plot_number"].notna()] if "plot_number" in data.columns else data
        data = data[~data["plot_number"].isin(["Plot #", "plonum"])] if "plot_number" in data.columns else data

        if y_axis not in data.columns and y_axis != "species_richness":
            ax.set_title(f"{name} (missing {y_axis})")
            ax.axis("off")
            continue

        if chart_type == "boxplot":
            grouped = data.groupby(group_by)[y_axis].apply(lambda s: s.dropna().tolist())
            values = [vals for vals in grouped.values if vals]
            labels = [str(idx) for idx, vals in zip(grouped.index, grouped.values) if vals]
            if not values:
                ax.set_title(f"{name} (no data)")
                ax.axis("off")
                continue
            ax.boxplot(values, tick_labels=labels)
        elif chart_type == "stacked_bar":
            grouped = data.groupby([x_axis, group_by])[y_axis].agg(aggregation).unstack(fill_value=0)
            total_species = len(grouped)
            if top_n and total_species > top_n:
                top = grouped.sum(axis=1).sort_values(ascending=False).head(top_n).index
                grouped = grouped.loc[top]
            grouped.plot(kind="bar", stacked=True, ax=ax)
            ax.text(0.99, 0.98, f"species: {total_species}", transform=ax.transAxes, ha="right", va="top", fontsize=8, color="#6b7280")
        else:
            aggregated = aggregate_series(data, y_axis, group_by, aggregation)
            ax.bar(aggregated.index.astype(str), aggregated.values, color="#3b82f6")

        ax.set_title(name)
        ax.set_xlabel(x_axis)
        ax.set_ylabel(y_axis)
        ax.tick_params(axis="x", rotation=45)

    fig.tight_layout()
    fig.savefig(output_base)
    print(f"saved {output_base}")


def main():
    parser = argparse.ArgumentParser(description="Visualize key indicators")
    parser.add_argument("--codebook", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--top-n", type=int, default=10)
    args = parser.parse_args()

    codebook = load_json(args.codebook)
    dataset = load_json(args.dataset)

    df = pd.DataFrame(dataset.get("records", []))
    if df.empty:
        raise SystemExit("Dataset is empty")

    df = build_computed(df, codebook)
    plot_indicators(df, codebook, args.out, args.top_n)


if __name__ == "__main__":
    main()
