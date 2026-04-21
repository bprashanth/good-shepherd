# PWA Outputs

This document describes the artifacts emitted by `examples/stack/pwa/`.

This stage now consumes the fixed Stage 1 handoff from `examples/stack/setup_wizard/output/selected_plot.json`, copied into `input/selected_plot.json`.

## Stage Inputs

- `input/selected_plot.json`

This input contains:

- one fixed plot, shown as `Plot 1`
- one center point for photomonitoring
- four `2 m x 2 m` corner quadrats inside the `20 x 20 m` plot for species-richness surveys
- a survey-target order of:
  - `Center`
  - `Quadrat 1`
  - `Quadrat 2`
  - `Quadrat 3`
  - `Quadrat 4`

## Stage Outputs

This stage is a static frontend, so the primary artifacts are runtime workflow outputs rather than files written directly by the browser into `output/`.

Conceptual runtime outputs:

- upload manifest entries keyed by `plot_id` and survey target
- submission state per target
- advisory events when an uploaded filename contains `lantana`, case-insensitively

## Stage Assumptions

- the left selector is locked to `Plot 1`
- the right selector cycles through the center plus four quadrats
- the center is used for photomonitoring
- the quadrats are corner quadrats used for species-richness surveys
- filenames containing `lantana` trigger the advisory
- all other uploads complete without advisory

## Verification Gate

Before leaving this stage, manually verify in the UI that:

- `Plot 1` stays locked
- the survey target selector cycles through `Center` and `Quadrat 1–4`
- the active target highlights correctly on the map
- uploads mark the active target as complete
- a filename containing `lantana` triggers the advisory
- a non-lantana filename does not trigger the advisory

## Next Handoff

This stage is reused later for site monitoring as the same app with the same spatial setup, but a different workflow framing from `web/`.
