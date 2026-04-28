# Indicator Stage Outputs

This document describes the artifacts emitted by `examples/stacks/research/indicators_2/`.

The stage mirrors `examples/stacks/research/indicators/`, but the inputs come from the completed Osuri restoration study rather than upload-time forms and trace mapping.

## Key Outputs

- `output/variable_catalog.json`
- `output/variables_codebook.json`
- `output/computed_variables.json`
- `output/indicator_config.json`
- `output/indicator_dataset.json`
- `output/indicator_wizard.html`
- `output/indicator_field_mapping.html`
- `output/indicator_codebook.json`

## Artifact Roles

### `output/variable_catalog.json`

Raw variables with:

- source dataset
- example values
- measurement explanation

### `output/computed_variables.json`

Computed-variable layer derived from the Osuri metadata.

- raw inputs
- English intent
- compiled snippet or formula text when available

### `output/indicator_config.json`

Final indicator layer for the wizard UI.

- indicator definition
- required computed variables
- graph intents

### `output/indicator_dataset.json`

Finished per-plot dataset assembled from the Osuri CSVs.

- one record per eligible plot
- completed-study indicator values
- treatment and site context

### `output/indicator_wizard.html`

Wizard UI matching `examples/stacks/research/indicators` as closely as possible, without depending on trace-mapping workflow.

### `output/indicator_field_mapping.html`

Compatibility artifact retained so the sibling output shape stays close to `examples/stacks/research/indicators`, even though this stage does not rely on active trace mapping.

## Assumptions

- the compute server is reused from `examples/stacks/research/indicators/scripts/compute_server.py`
- `anr_metadata.json` is the authoritative source for raw/computed/indicator semantics
- the CSVs in `input/Osuri+et+al_data_scripts/` provide the finished-study data table
- trace mapping is not part of the core workflow for this sibling stage

## Build Entry

Use:

- `./examples/stacks/research/indicators_2/process_indicators.sh`
