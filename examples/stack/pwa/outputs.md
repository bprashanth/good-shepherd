# PWA Outputs

This document describes the artifacts emitted by `examples/stack/pwa/`.

This stage mirrors `examples/pwa/`, but the hierarchy is:

- plot
- subplot

instead of:

- transect
- plot

## Stage 0 Contract

The final implementation of this stage is expected to emit:

- upload manifests for the selected plot and its subplots
- submission status artifacts
- advisory metadata when an uploaded filename contains `lantana`, case-insensitively

## Expected Consumers

- this stage is primarily a workflow endpoint
- if needed, later summaries can consume upload manifests from `output/`

## Verification Gate

Before this stage is treated as stable, it must be manually verified in the UI for:

- plot and subplot highlighting
- upload flow
- lantana advisory behavior

This file will be updated after Stage 3 and Stage 5 with exact filenames and semantics.
