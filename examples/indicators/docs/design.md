# Indicator Wizard + Dataset Builder (Design Plan)

## Purpose
Build a general-purpose indicator onboarding workflow that maps forms to raw variables, then to computed variables, then to indicators. The output must be reusable across experiments and support ongoing ingestion of new forms. A Cestrum demo is the reference example.

This design intentionally avoids hardcoding any single experiment into the platform. The onboarding step produces a "codex" (configuration + transformation rules) that can be applied later whenever new form data arrives.

## Scope
- Stage 1: Indicator Wizard (onboarding)
- Stage 2: Dataset Builder (apply codex to new form data)
- Stage 3: Visualization (out of scope here)

## Inputs
- `indicators.pdf` (indicator definitions)
- Form images + `_classified.json` (from Textract + correction UI)
- Optional `field_vars_indicators.xlsx` (readme + lookup tables)

## Outputs
### Stage 1 (Indicator Wizard)
- `indicator_config.json` (indicators + graph intents + evidence)
- `computed_variables.json` (english intent + compiled code + evidence)
- `variable_catalog.json` (raw variables + provenance)
- `indicator_wizard.html` (standalone UI)

### Stage 2 (Dataset Builder)
- `indicator_dataset.json` (flat dataset including raw + computed variables)

## General Pipeline
1. Ingest inputs.
2. Build a raw variable catalog from form JSON.
3. Extract indicator definitions from the PDF.
4. Optionally parse the Excel readme for variable definitions and lookup tables.
5. Use an agent to propose computed variables and indicator mappings.
6. Present the proposal in the wizard UI for edits and approvals.
7. Save the "codex" artifacts for reuse.
8. Dataset builder consumes the codex + new form data to recompute datasets.

## Stage 1: Indicator Wizard

### Core goals
- Capture user intent in plain English.
- Produce compiled expressions that the app can execute later.
- Store evidence links to show why a variable or indicator was inferred.

### Inputs to the agent
- Extracted indicator text (from `indicators.pdf`).
- Raw variable catalog (from form JSON headers + sample values).
- Optional Excel readme content (variable definitions, scales, lookup tables).

### Outputs from the agent
- Proposed computed variables with formulas and evidence.
- Proposed indicator mappings and graph intents.
- Confidence scores to prioritize user review.

### Wizard UI layout (high level)
- **Forms**: preview images + extracted tables.
- **Raw variables**: list of detected variables with confidence and provenance.
- **Computed variables**: proposed transformations with English description + compiled code.
- **Indicators**: mapping of computed variables to indicators + graph intents.

### User edit flow
- Edit variable names and units.
- Edit English description of the computation.
- Accept or revise compiled expression.
- Approve indicators and graph intents.

## Stage 2: Dataset Builder

### Purpose
Recompute raw and computed variables whenever new form data is ingested.

### Inputs
- `variable_catalog.json`
- `computed_variables.json`
- Form data directory (images + `_classified.json` + optional Excel files)

### Steps
1. Normalize incoming form JSON into a single long table of raw observations.
2. Apply `computed_variables.json` to produce computed columns.
3. Emit `indicator_dataset.json` for downstream visualization.

## Standards (JSON schemas)

Three new concepts: 
1. Variable catalog (what are the raw variables, which forms do they come from?)
2. Computed variables (math described in english, that runs on variables) 
3. Indicators (computed variables tracked over time as a trend, i.e. compute variables + time/space + graph) 

There are also the following standard metadatas
1. Graphs: a listing/description of known graphs, whats on the x and y
2. Evidence: a loose standard around where we got this indicator from

### variable_catalog.schema.json
- Flat list of raw variables
- Includes provenance: form source, field name, example values, confidence

### computed_variables.schema.json
- Each entry includes:
  - `name`, `description`
  - `inputs` (raw variables)
  - `english_intent` (user-supplied text)
  - `compiled.language` and `compiled.code`
  - `aggregation` (plot/subplot/time)
  - `evidence[]` (source + snippet)
  - `status` (draft/approved)

### indicator_config.schema.json
- Each indicator includes:
  - `name`, `definition`
  - `required_computed_variables`
  - `graph_intents[]`
  - `evidence[]`

### graph_intent.schema.json
- `chart_type`, `x_axis`, `y_axis`, `group_by`, `aggregation`

## Computation format
Prefer JSONLogic for compiled expressions when possible, with JS fallback for complex cases.
- JSONLogic is declarative and auditable.
- JS fallback remains available for edge cases.

## Evidence model (shared pattern)
Each computed variable or indicator can store an evidence entry:
- `source_type`: `pdf`, `excel`, `form`
- `source_ref`: page number, sheet + row, or filename
- `snippet`: short text excerpt

## Cestrum demo notes (reference)
- Indicators: invasive recovery, resilience, biodiversity gains, ground cover, recruitment.
- Derived rules: canopy openness % (directional readings * 1.04, then average), soil moisture scoring, species mapping via readme table.
- Use `field_vars_indicators.xlsx` readme tab to seed variable definitions and lookup tables.

## Ongoing ingestion story (POC)
- New forms are uploaded via `examples/forms`.
- Dataset builder is re-run on each new batch.
- Visualization stage reads `indicator_dataset.json` and `indicator_config.json` to render graphs.

## Open questions (defer)
- Final visualization library and Vega embedding strategy.
- Whether to persist baseline vs monitoring rounds explicitly.

