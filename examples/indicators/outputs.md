# Indicator Stage Outputs

his document describes the artifacts emitted by the indicator onboarding stage. These outputs are designed to be portable so that downstream components (eg, the Vue3 visualization dashboard) can compute metrics and render graphs without access to the original PDFs, images, or spreadsheets.

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

_TODO: to be documented after the dataset builder is finalized._
