# Indicators Outputs

This document describes the artifacts emitted by `examples/stacks/rewild/indicators/`.

This stage mirrors the role of `examples/stacks/research/indicators/`, but for the practitioner stack the deliverable is a static four-panel recovery dashboard rather than a full indicator onboarding pipeline.

## Stage Inputs

- `input/images/*.jpg`
- `input/images/*.JPG`

This stage uses the EXIF chronology of the curated image set in `input/images/` as the recovery sequence.

## Stage Outputs

- `output/progression_manifest.json`
- `output/indicator_progression.json`

## Artifact Roles

### `output/progression_manifest.json`

Static frontend contract for the four-panel Indicators dashboard.

- Stage 1 focus AOI circle center and radius
- selected `20 x 20 m` plot geometry
- site summary values:
  - lat/lon
  - invasive status
  - removal status
  - nursery
  - replantation species
- chronological image manifest derived from the current EXIF-ordered image set

### `output/indicator_progression.json`

Curated recovery indicator payload keyed to the same timeline.

- `Similarity Score` is the primary indicator
- additional indicators increase or appear over time
- all steps are intentionally aligned with the Plantwise replantation story
- each indicator entry also carries the metadata name used to resolve computation details from `input/anr_metadata.json`

## Stage Assumptions

- the UI is a four-panel dashboard inspired by the FOMO quarter-panel layout
- top-left shows the same AOI circle and selected plot used earlier in the stack
- top-right shows a readable recovery summary, not raw JSON
- bottom-left cycles chronological site images
- bottom-right cycles a growing set of indicators in sync with the images
- the summary uses `pollachi greens` as the displayed nursery
- the summary species list matches the Plantwise recommendation for `pollachi greens`
- the recovery indicators are curated static values for narrative clarity, not recomputed from raw source data at runtime
- only the first timeline card is labeled `Baseline`; later cards use literal timestamps
- image caption summary text below the photo has been intentionally removed
- clicking an indicator reveals its explanation and `js_snippet` from `input/anr_metadata.json` when available

## Stage Run And Verify

Serve this stage over HTTP from the repo root:

```bash
cd /home/desinotorious/src/github.com/bprashanth/good-shepherd
source .venv/bin/activate
python -m http.server 8034 --directory examples/stacks/rewild/indicators
```

Open:

- `http://localhost:8034/index.html`

## Verification Gate

Before leaving this stage, manually verify in the UI that:

- the map panel shows the AOI circle and selected plot correctly
- the summary panel shows the expected site, invasive, removal, nursery, and species values
- the nursery link opens correctly
- `Next` advances images and indicators together
- `Similarity Score` trends upward across the sequence
- additional indicators appear and rise over time
- clicking an indicator reveals how it was computed
- the overall four-panel layout feels coherent on desktop
