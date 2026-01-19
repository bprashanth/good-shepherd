# Indicator Wizard

This stage captures how raw form variables are transformed into computed variables and indicators.
It produces a reusable "codex" that can be applied whenever new form data arrives.

## Quick Start (POC)

### 1) Run the onboarding pipeline
```bash
./process_indicators.sh <path_to_indicators_pdf> <path_to_forms_dir> [optional_xlsx]
```

**Example:**
```bash
./process_indicators.sh ../inputs/indicators.pdf ../inputs/forms ../inputs/field_vars_indicators.xlsx
```

**Outputs (written to `output/`):**
- `indicator_config.json`
- `computed_variables.json`
- `variable_catalog.json`
- `variables_codebook.json`
- `indicator_wizard.html`

### 1b) Start the compute server (optional)
This enables the \"Generate formula\" button in the wizard UI.
```bash
source .venv/bin/activate && python3 examples/indicators/scripts/compute_server.py
```

### 2) Recompute the dataset
```bash
python3 scripts/build_dataset.py \
  --forms-dir ../inputs/forms \
  --variables-codebook ../output/variables_codebook.json \
  --xlsx ../inputs/field_vars_indicators.xlsx \
  --out indicator_dataset_raw.json
python3 scripts/postprocess_dataset.py \
  --in indicator_dataset_raw.json \
  --out indicator_dataset.json
```

Note: `process_indicators.sh` also produces `output/indicator_dataset.json` by default.

### 3) Normalize indicator config (when edited)
If `indicator_config.json` was edited manually, normalize its field names to canonical aliases:
```bash
python3 scripts/normalize_indicator_config.py \
  --indicator-config output/indicator_config.json \
  --variables-codebook output/variables_codebook.json \
  --out output/indicator_config.json
```

## Directory Structure
- `docs/`: design notes and planning
- `scripts/`: pipeline scripts (agent + builders)
- `standards/`: minimal schema stubs

## Inputs
- `indicators.pdf`: indicator definitions
- `forms/`: images + `_classified.json` (Textract outputs)
- `field_vars_indicators.xlsx` (optional): variable definitions + lookups

## Outputs
- `indicator_config.json`: indicator definitions + graph intents
- `computed_variables.json`: English intent + compiled code (JSONLogic/JS)
- `variable_catalog.json`: raw variable catalog from forms
- `variables_codebook.json`: canonical field names + aliases across inputs
- `indicator_wizard.html`: standalone UI for user edits
- `indicator_field_mapping.html`: alias trace view for canonical fields
- `indicator_dataset_raw.json`: raw flattened records (Excel only)
- `indicator_dataset.json`: postprocessed dataset for visualization

## Summary Data Flow
```mermaid
graph TD
    A[indicators.pdf] --> B[process_indicators.sh]
    C[forms/ + _classified.json] --> B
    D[field_vars_indicators.xlsx] --> B
    B --> E[output/variable_catalog.json]
    B --> K[output/variables_codebook.json]
    B --> F[output/computed_variables.json]
    B --> G[output/indicator_config.json]
    B --> H[output/indicator_wizard.html]
    B --> L[output/indicator_field_mapping.html]
    K --> E
    E --> H
    F --> H
    G --> H
    K --> I[build_dataset.py]
    D --> I
    I --> J[indicator_dataset_raw.json]
    J --> L[postprocess_dataset.py]
    L --> M[indicator_dataset.json]
    H --> N[indicator_codebook.json]
```

## Notes
- JSONLogic is preferred for compiled expressions; JS fallback is allowed.
- Evidence snippets are optional but recommended for traceability.
- Computed variables are evaluated per record in a single long table; missing inputs should yield null/empty.
- Records from different form types will have different subsets of fields populated; others remain empty.
