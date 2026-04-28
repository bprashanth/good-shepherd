import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_csv_rows(path):
    for encoding in ("utf-8", "latin-1"):
        try:
            with open(path, "r", encoding=encoding, newline="") as handle:
                return list(csv.DictReader(handle))
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("csv", b"", 0, 1, f"Could not decode {path}")


def normalize_str(value):
    if value is None:
        return ""
    return str(value).strip()


def to_float(value, default=None):
    try:
        if value in ("", None, "NA"):
            return default
        return float(value)
    except Exception:
        return default


def to_int(value, default=None):
    try:
        if value in ("", None, "NA"):
            return default
        return int(float(value))
    except Exception:
        return default


def mean(values):
    values = [v for v in values if v is not None and not math.isnan(v)]
    if not values:
        return None
    return sum(values) / len(values)


def sum_values(values):
    vals = [v for v in values if v is not None and not math.isnan(v)]
    if not vals:
        return None
    return sum(vals)


def bray_curtis(counter_a, counter_b):
    species = set(counter_a) | set(counter_b)
    if not species:
        return None
    shared = sum(min(counter_a.get(sp, 0), counter_b.get(sp, 0)) for sp in species)
    total = sum(counter_a.get(sp, 0) + counter_b.get(sp, 0) for sp in species)
    if total == 0:
        return None
    return 1 - (2 * shared / total)


def build_variable_catalog(metadata, sample_rows_by_dataset):
    variables = []
    seen = set()
    for measured in metadata["measurements"]["measured_variables"]:
        dataset = measured["dataset"]
        examples = sample_rows_by_dataset.get(dataset, [])
        for variable in measured["variables"]:
            key = (dataset, variable)
            if key in seen:
                continue
            seen.add(key)
            sample_values = []
            for row in examples:
                value = row.get(variable)
                if value not in (None, "", "NA") and value not in sample_values:
                    sample_values.append(value)
                if len(sample_values) >= 5:
                    break
            variables.append({
                "name": variable,
                "source_form": dataset,
                "field_name": variable,
                "unit": "",
                "example_values": sample_values,
                "confidence": None,
                "explanation": measured.get("explanation", "")
            })
    return {"variables": variables}


def build_variables_codebook(variable_catalog):
    grouped = defaultdict(list)
    for variable in variable_catalog["variables"]:
        grouped[variable["name"]].append({
            "name": variable["field_name"],
            "source": variable["source_form"]
        })
    entries = []
    for name in sorted(grouped):
        entries.append({
            "canonical_name": name,
            "aliases": grouped[name]
        })
    return {"variables": entries}


def slugify(name):
    return (
        name.lower()
        .replace(":", "")
        .replace("%", "percent")
        .replace("-", " ")
        .replace("/", " ")
        .replace("(", " ")
        .replace(")", " ")
        .replace(",", " ")
    ).strip().replace(" ", "_")


def build_computed_variables(metadata):
    computed = []
    for indicator in metadata["indicators"]:
        variable_name = slugify(indicator["name"])
        compiled = {}
        if indicator.get("js_snippet"):
            compiled = {
                "language": "js",
                "code": indicator["js_snippet"]
            }
        elif indicator.get("formula"):
            compiled = {
                "language": "text",
                "code": indicator["formula"]
            }
        computed.append({
            "name": variable_name,
            "description": indicator.get("explanation", ""),
            "inputs": indicator.get("csv_variables", []),
            "english_intent": indicator.get("explanation", ""),
            "compiled": compiled,
            "aggregation": {
                "level": "plot",
                "time": "completed_study_snapshot"
            },
            "evidence": [
                {
                    "source_type": "metadata",
                    "source_ref": ",".join(indicator.get("source_files", [])),
                    "snippet": indicator.get("formula") or indicator.get("explanation", "")
                }
            ],
            "status": "approved"
        })
    return {"computed_variables": computed}


def build_indicator_config(metadata):
    indicators = []
    for indicator in metadata["indicators"]:
        computed_name = slugify(indicator["name"])
        indicators.append({
            "name": indicator["name"],
            "definition": indicator.get("explanation", ""),
            "required_computed_variables": [computed_name],
            "graph_intents": [
                {
                    "chart_type": "bar",
                    "x_axis": "treatment",
                    "y_axis": computed_name,
                    "group_by": "treatment",
                    "aggregation": "mean"
                }
            ],
            "evidence": [
                {
                    "source_type": "metadata",
                    "source_ref": ",".join(indicator.get("source_files", [])),
                    "snippet": indicator.get("formula") or indicator.get("explanation", "")
                }
            ]
        })
    return {"indicators": indicators}


def build_dataset(input_dir, metadata):
    csv_dir = Path(input_dir) / "Osuri+et+al_data_scripts"
    sites_rows = read_csv_rows(csv_dir / "Resto_site_info.csv")
    tree_rows = read_csv_rows(csv_dir / "tree_data.csv")
    regen_rows = read_csv_rows(csv_dir / "regen_data.csv")
    traits_rows = read_csv_rows(csv_dir / "species_traits.csv")

    traits_by_acc = {normalize_str(row.get("acc_name")): row for row in traits_rows}
    sites_by_plot = {normalize_str(row["Plot_code"]): row for row in sites_rows}

    age_by_plot = {}
    for plot_code, row in sites_by_plot.items():
        year_restored = to_int(row.get("Year_restored"))
        site_type = normalize_str(row.get("Type"))
        age = 9999 if site_type == "Benchmark" else (2017 - year_restored if year_restored is not None else None)
        age_by_plot[plot_code] = age

    filtered_trees = []
    for row in tree_rows:
        plot_code = normalize_str(row.get("Plot_code"))
        remarks = normalize_str(row.get("Remarks")).lower()
        age = age_by_plot.get(plot_code)
        if remarks in {"cut", "dead"}:
            continue
        if age is None or age < 7:
            continue
        if plot_code == "drop":
            continue
        trait = traits_by_acc.get(normalize_str(row.get("accpt.nam")), {})
        row = dict(row)
        row["Habt_New"] = trait.get("Habt_New")
        row["Can_vis"] = sites_by_plot.get(plot_code, {}).get("Can_vis")
        row["Chave_E"] = sites_by_plot.get(plot_code, {}).get("Chave_E")
        wd_sp = to_float(trait.get("Wden_sp"))
        wd_gen = to_float(trait.get("Wden_gen"))
        wden_use = wd_sp if wd_sp is not None else (wd_gen if wd_gen is not None else 0.54)
        dbh = to_float(row.get("DBH"))
        height = to_float(row.get("Height"))
        chave_e = to_float(row.get("Chave_E"), 0.0)
        if dbh and dbh > 0:
            mod_ht = math.exp(0.893 - chave_e + 0.760 * math.log(dbh) - 0.0340 * (math.log(dbh) ** 2))
        else:
            mod_ht = None
        effective_height = mod_ht if normalize_str(row.get("Remarks")).lower() == "no height noted" else height
        if dbh and effective_height and effective_height > 0:
            carbon = 0.471 * 0.0673 * ((wden_use * (dbh ** 2) * effective_height) ** 0.976)
        else:
            carbon = None
        hd_include = to_int(row.get("HD_include"))
        if hd_include == 1 and dbh and dbh > 0 and height and height > 0:
            log_hd = math.log(height) / math.log(dbh)
        else:
            log_hd = None
        row["carbon_value"] = carbon
        row["log_hd"] = log_hd
        filtered_trees.append(row)

    for row in regen_rows:
        trait = traits_by_acc.get(normalize_str(row.get("acc_name")), {})
        row["Habt_New"] = trait.get("Habt_New")

    tree_by_plot = defaultdict(list)
    for row in filtered_trees:
        tree_by_plot[normalize_str(row.get("Plot_code"))].append(row)

    regen_by_plot = defaultdict(list)
    for row in regen_rows:
        regen_by_plot[normalize_str(row.get("Plot_code"))].append(row)

    species_counts_by_plot = {}
    for plot_code, rows in tree_by_plot.items():
        counter = Counter()
        for row in rows:
            species = normalize_str(row.get("species"))
            if species:
                counter[species] += 1
        species_counts_by_plot[plot_code] = counter

    benchmark_plots = [
        plot_code for plot_code, row in sites_by_plot.items()
        if normalize_str(row.get("Type")) == "Benchmark" and plot_code in species_counts_by_plot
    ]

    similarity_by_plot = {}
    for plot_code, counter in species_counts_by_plot.items():
        distances = []
        for benchmark_plot in benchmark_plots:
            dist = bray_curtis(counter, species_counts_by_plot[benchmark_plot])
            if dist is not None:
                distances.append(dist)
        similarity_by_plot[plot_code] = 100 * (1 - mean(distances)) if distances else None

    records = []
    for plot_code, site in sites_by_plot.items():
        age = age_by_plot.get(plot_code)
        if age is None or age < 7:
            continue
        tree_rows_for_plot = tree_by_plot.get(plot_code, [])
        if not tree_rows_for_plot:
            continue

        regen_rows_for_plot = regen_by_plot.get(plot_code, [])
        tree_species = {normalize_str(row.get("species")) for row in tree_rows_for_plot if normalize_str(row.get("species"))}
        mature_tree_species = {
            normalize_str(row.get("species")) for row in tree_rows_for_plot
            if normalize_str(row.get("Habt_New")) == "Mature" and normalize_str(row.get("species"))
        }
        sapling_species = {
            normalize_str(row.get("acc_name") or row.get("Species.name")) for row in regen_rows_for_plot
            if normalize_str(row.get("acc_name") or row.get("Species.name"))
        }
        mature_sapling_species = {
            normalize_str(row.get("acc_name") or row.get("Species.name")) for row in regen_rows_for_plot
            if normalize_str(row.get("Habt_New")) == "Mature" and normalize_str(row.get("acc_name") or row.get("Species.name"))
        }
        native_regen = [
            to_float(row.get("regen"), 0.0) for row in regen_rows_for_plot
            if normalize_str(row.get("Habt_New")) != "Int"
        ]
        all_regen = [to_float(row.get("regen"), 0.0) for row in regen_rows_for_plot]

        record = {
            "record_id": len(records) + 1,
            "plot_code": plot_code,
            "site_code": normalize_str(site.get("Site_code")),
            "site_name": normalize_str(site.get("Site_name")),
            "forest_name": normalize_str(site.get("Forest_name")),
            "treatment": normalize_str(site.get("Type")),
            "year_restored": to_int(site.get("Year_restored")),
            "distance_to_contiguous_forest": to_float(site.get("dist_PA")),
            "can_vis": to_float(site.get("Can_vis")),
            "can_den": to_float(site.get("Can_den")),
            "canopy_cover": to_float(site.get("Can_vis")),
            "adult_tree_density": len(tree_rows_for_plot),
            "tree_height_diameter_ratio_log_log": mean([to_float(row.get("log_hd")) for row in tree_rows_for_plot]),
            "adult_species_density": len(tree_species),
            "adult_late_successional_species_density": len(mature_tree_species),
            "community_similarity_to_benchmark_rainforest": similarity_by_plot.get(plot_code),
            "sapling_density": sum_values(all_regen),
            "sapling_native_fraction": (sum(native_regen) / sum(all_regen)) if all_regen and sum(all_regen) else None,
            "sapling_species_density": len(sapling_species),
            "sapling_late_successional_species_density": len(mature_sapling_species),
            "aboveground_carbon_storage": (
                sum_values([to_float(row.get("carbon_value")) for row in tree_rows_for_plot]) * 100 * 100 / (1000 * 20 * 20)
                if sum_values([to_float(row.get("carbon_value")) for row in tree_rows_for_plot]) is not None
                else None
            ),
        }
        records.append(record)

    return {"records": records}


def build_field_sources(variable_catalog):
    entries = []
    for variable in variable_catalog["variables"]:
        entries.append({
            "variable_name": variable["name"],
            "source_name": variable["source_form"],
            "field_name": variable["field_name"],
            "explanation": variable.get("explanation", "")
        })
    return {"entries": entries}


def main():
    parser = argparse.ArgumentParser(description="Build indicators_2 outputs from the Osuri study metadata and CSVs.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata = load_json(input_dir / "anr_metadata.json")
    sample_rows_by_dataset = {
        "Resto_site_info.csv": read_csv_rows(input_dir / "Osuri+et+al_data_scripts" / "Resto_site_info.csv")[:5],
        "tree_data.csv": read_csv_rows(input_dir / "Osuri+et+al_data_scripts" / "tree_data.csv")[:5],
        "regen_data.csv": read_csv_rows(input_dir / "Osuri+et+al_data_scripts" / "regen_data.csv")[:5],
        "species_traits.csv": read_csv_rows(input_dir / "Osuri+et+al_data_scripts" / "species_traits.csv")[:5],
    }

    variable_catalog = build_variable_catalog(metadata, sample_rows_by_dataset)
    variables_codebook = build_variables_codebook(variable_catalog)
    computed_variables = build_computed_variables(metadata)
    indicator_config = build_indicator_config(metadata)
    indicator_dataset = build_dataset(input_dir, metadata)
    field_sources = build_field_sources(variable_catalog)

    codex = {
        "computed_variables": computed_variables,
        "indicator_config": indicator_config
    }
    indicator_codebook = {
        "version": "v1",
        "generated_at": "completed-study-export",
        "variables_codebook": variables_codebook,
        "variable_catalog": variable_catalog,
        "computed_variables": computed_variables,
        "indicator_config": indicator_config
    }

    (out_dir / "variable_catalog.json").write_text(json.dumps(variable_catalog, indent=2), encoding="utf-8")
    (out_dir / "variables_codebook.json").write_text(json.dumps(variables_codebook, indent=2), encoding="utf-8")
    (out_dir / "computed_variables.json").write_text(json.dumps(computed_variables, indent=2), encoding="utf-8")
    (out_dir / "indicator_config.json").write_text(json.dumps(indicator_config, indent=2), encoding="utf-8")
    (out_dir / "indicator_dataset_raw.json").write_text(json.dumps(indicator_dataset, indent=2), encoding="utf-8")
    (out_dir / "indicator_dataset.json").write_text(json.dumps(indicator_dataset, indent=2), encoding="utf-8")
    (out_dir / "indicator_codebook.json").write_text(json.dumps(indicator_codebook, indent=2), encoding="utf-8")
    (out_dir / "field_sources.json").write_text(json.dumps(field_sources, indent=2), encoding="utf-8")
    (out_dir / "codex.json").write_text(json.dumps(codex, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
