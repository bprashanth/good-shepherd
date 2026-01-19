# Dataset Builder Design

## Purpose
The dataset builder produces a flat, analysis-ready table that can be consumed immediately by the visualization app alongside `indicator_codebook.json`. This supports two scenarios:
- **Mid-experiment onboarding:** existing forms/spreadsheets are already available and should be converted into a dataset right away.
- **New experiments:** no data yet; the dataset starts empty and is appended as new forms arrive.

## Long-term intent (beyond POC)
A complete pipeline would include:
1. **Transform:** map source field names to standardized names (e.g., `dirt` -> `dirt_presence`).
2. **Edit/Enrich:** add units, normalize scales, standardize categorical values.
3. **Validate:** confirm required fields and ranges.

These steps are out of scope for the initial POC but are represented here as future layers.

## POC scope
For the basic POC, the dataset builder will:
- Read relevant spreadsheet inputs (Excel only for now).
- Normalize them into a single **long table**.
- Leave non-applicable fields blank for records that do not contain them.
- Output a raw dataset, then run a postprocessing step for experiment-specific logic.

## Inputs
- Optional Excel sheets (e.g., `field_vars_indicators.xlsx`) for additional rows

## Outputs
- `indicator_dataset_raw.json`: raw flattened records (Excel only)
- `indicator_dataset.json`: postprocessed dataset for visualization

## Excel notes
- See `examples/indicators/standards/excel_rules.md` for heuristics on flattenable vs matrix-style sheets.\n- The \"Read me\" tab in `field_vars_indicators.xlsx` should be treated as a guide (definitions and mappings), not as a data table to flatten.

## Record model (POC)
Each record in the long table shares the same schema, even if some fields are empty:
- Identifiers: `date`, `area_name`, `block_code`, `transect_number`, `plot_number`, `subplot_number`
- Raw variables: any field extracted from forms/spreadsheets
- Provenance: `source_file`

## Postprocessing (experiment-specific)
These rules are specific to the current POC and should be isolated in a separate script:

1. **DBH columns (Raw 10x10m Data)**
   - Columns `DBH 1` ... `DBH 15` all map to `dbh_in_cms`.
   - For each populated DBH value, emit a duplicate row with a single `dbh_in_cms` value.

2. **Density sheet header**
   - In the `Density` tab, use the second row as column headers (the row with `blo cod`, `tranum`, `plonum`).
   - Ignore the first row with the title string.

## Append behavior
- New incoming rows are appended as new records.
- Existing records remain unchanged unless explicitly reprocessed.

## Downstream usage
The visualization stage receives:
1. `indicator_codebook.json` (rules + graph intents)
2. `indicator_dataset.json` (raw + computed values)

The Vue3 app can then:
- Recompute derived variables if needed
- Apply groupings and aggregation defined by indicators
- Render graphs using `graph_intents`
