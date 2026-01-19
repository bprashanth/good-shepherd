# Indicator Stage Outputs

This document describes the artifacts emitted by the indicator onboarding stage. These outputs are designed to be portable so that downstream components (e.g., the Vue3 visualization dashboard) can compute metrics and render graphs without access to the original PDFs, images, or spreadsheets.

## indicator_codebook.json

**Purpose**
A self-contained "rules" artifact describing:
- Which raw variables exist (and their provenance)
- How to compute derived variables from raw records
- Which indicators to display and how to visualize them

**Produced by**
- `process_indicators.sh` (via `indicator_wizard.html` or agent output)
- The wizard UI can export an updated codebook after user edits

**Expected consumers**
- Visualization app (Vue3)
- Dataset builder (optional validation)

**Top-level shape (v1)**
- `version`: schema version
- `generated_at`: ISO timestamp
- `variables_codebook`: canonical field names + aliases across inputs
- `variable_catalog`: raw variables and provenance
- `computed_variables`: list of computed variable definitions
- `indicator_config`: list of indicators and graph intents

**How to use in visualization**
1. Load `indicator_codebook.json` alongside the indicator dataset.
2. Use `computed_variables` to interpret or recompute derived fields when needed.
3. Use `indicator_config.graph_intents` to select graph types and axis mappings.
4. Use `indicator_config.required_computed_variables` to determine which computed fields are needed per indicator (this links computed variables and indicators).

**Notes**
- Computed variables are defined per record (no aggregation). Aggregation and grouping are handled at the indicator level.
- If an indicator has `status: "draft"`, it is incomplete and should be surfaced for user review.

## indicator_dataset.json

**Purpose**
Flat record list containing raw fields (canonicalized names) and any postprocessed fields (e.g., `dbh_in_cms`). This is the data table the UI should aggregate and visualize.

**How to use with indicator_codebook.json**
1. Load `indicator_dataset.json` and `indicator_codebook.json`.
2. For each indicator, identify required computed variables.
3. For each computed variable:
   - Evaluate its compiled expression per record to produce a new field.
4. For each indicator:
   - Apply `group_by` and `aggregation` from its `graph_intents`.
   - Render charts using the grouped/aggregated results.

## Examples

**Example A: DBH-based indicator**
- Computed variable: `native_species_dbh` (per record)
  - Intent: filter to specific species and return `dbh_in_cms`.
- Indicator: “Resilience.growth”
  - Graph intent: group by `plot_number`, aggregate `mean` of `native_species_dbh`.

Pseudo-flow:
1. Compute `native_species_dbh` for each record.
2. Filter out null values.
3. Group records by `plot_number`.
4. Compute mean DBH per group.
5. Plot as a line or bar chart over time.

**Example B: Presence/count indicator**
- Computed variable: `cestrum_present` (per record)
  - Intent: return 1 if species is Cestrum, else 0.
- Indicator: “Invasive Recovery”
  - Graph intent: group by `plot_number`, aggregate `sum` of `cestrum_present`.

Pseudo-flow:
1. Compute `cestrum_present` for each record.
2. Group by `plot_number`.
3. Sum per group to get counts.
4. Plot counts as a line over time or a bar per plot.
