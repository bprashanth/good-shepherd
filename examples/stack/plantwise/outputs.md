# Plantwise Outputs

This document describes the artifacts emitted by `examples/stack/plantwise/`.

This stage consumes the fixed saved plot from site selection and renders a static click-to-advise planting view.

## Stage Inputs

- `input/selected_plot.json`
- `input/advisory_data.json`

## Stage Outputs

- `output/plantwise_advisory.json`

## Artifact Roles

### `input/selected_plot.json`

Saved plot handoff from the earlier stage.

- selected plot center
- adult-tree plot geometry

### `input/advisory_data.json`

Static advisory payload used by the Plantwise UI.

- lantana detection flag
- Stage 1 focus AOI center and radius
- replanting advisory led by `Macaranga peltata`
- learn-more text
- pioneer shade species
- two ranked nurseries and their species lists

### `output/plantwise_advisory.json`

Portable copy of the advisory payload for downstream reuse.

## Stage Assumptions

- clicking the plot opens the advisory
- lantana was detected in the plot
- replanting should only happen after lantana removal
- the advisory names a first recommended pioneer shade species directly
- the `Learn more` action reveals the repeated-monitoring note and pioneer shade species
- nursery ranking is static and curated
- the map draws the Stage 1 focus AOI as a circle, not from a copied polygon file
- nursery names are:
  - `oxygen plants`
  - `pollachi greens`

## Stage 3 Run And Verify

Serve this stage over HTTP from the repo root:

```bash
cd /home/desinotorious/src/github.com/bprashanth/good-shepherd
source .venv/bin/activate
python -m http.server 8033 --directory examples/stack/plantwise
```

Open:

- `http://localhost:8033/index.html`

## Verification Gate

Before leaving this stage, manually verify in the UI that:

- the AOI and selected plot render correctly
- clicking the plot reveals the advisory
- the advisory says what to replant, not only what to remove
- the advisory explicitly mentions lantana removal before replanting
- the `Learn more` button reveals the repeated-monitoring and pioneer-shade note
- both nurseries and their species lists display correctly
