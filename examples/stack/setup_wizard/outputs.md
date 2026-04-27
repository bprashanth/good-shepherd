# Site Selection Outputs

This document describes the artifacts emitted by `examples/stack/setup_wizard/`.

Stage 1 is now a focused site-selection package built around a curated circular AOI that contains benchmark sites plus nearby mixed restoration sites.

## Stage 1 Outputs

The following files are emitted into `output/`:

- `aoi.geojson`
- `benchmark_sites.geojson`
- `plot_similarity.geojson`
- `suggestions.geojson`
- `selected_plot.geojson`
- `selected_plot.json`
- `ae_similarity.tif`
- `invasive_probability.tif`
- `layers.json`

There is also a verification viewer at:

- `wizard.html`

## Artifact Roles

### `aoi.geojson`

The circular AOI used by the Stage 1 viewer.

- geometry: curated focus circle
- center: `76.99557, 10.35952`
- radius: `2000 m`
- purpose: keep the overlap between benchmark sites and mixed restoration sites visually legible

### `benchmark_sites.geojson`

Known benchmark sites within the focus AOI.

- geometry: point features
- purpose: ground the similarity layer against real benchmark locations

### `plot_similarity.geojson`

Real per-plot benchmark similarity values for Osuri plots inside the focus AOI.

- geometry: point features at real plot centers
- purpose: preserve plot-level ranking even though the similarity raster is a coarse context layer

### `suggestions.geojson`

Suggested plots inside the focus AOI.

- geometry: point features at real plot centers
- source ranking: weighted combination of low benchmark similarity and high invasive probability
- important properties:
  - `plot_code`
  - `classification`
  - `ae_cosine_to_benchmark`
  - `invasive_probability`
  - `suggestion_score`

### `selected_plot.geojson`

Saved plot geometry for the next stage.

- contents:
  - adult-tree plot polygon (`20 m x 20 m`)
  - sapling subplot polygon (`5 m x 5 m`)
  - center point
- purpose: downstream spatial handoff

### `selected_plot.json`

Machine-readable handoff artifact for the next stage.

- center coordinate
- plot geometry
- subplot geometry
- selection reason
- stage source

### `ae_similarity.tif`

Single-band benchmark-similarity context raster clipped to the focus AOI.

- export scale: `150 m`
- purpose: landscape context only
- display intent: values near benchmark saturate green

### `invasive_probability.tif`

Single-band combined invasive probability raster clipped to the focus AOI.

- source rasters:
  - `Cestrum_aurantiacum`
  - `Chromolaena_odorata`
  - `Lantana_camara`
  - `Senna_spectabilis`
- combination rule: pixelwise max
- display treatment: values below the upper-tail threshold are transparent to increase contrast

### `layers.json`

Manifest for the Stage 1 viewer.

- AOI path
- raster paths
- point layer paths
- style parameters
- assumptions used for generation

## Stage 1 Assumptions

- the AOI is intentionally narrowed to a benchmark-rich circle so the overlap story is visible
- benchmark similarity is a context layer, not the sole basis for picking plots
- suggestions should be interpreted from `suggestions.geojson`, not raster pixels alone
- the downstream selected plot is fixed in Stage 1 via `selected_plot.json`
- invasive probability is shown only in its high-probability tail to avoid a blurred map

## Stage 1 Verification Gate

Before Stage 2 begins, manually verify in the UI that:

- the circular AOI contains benchmark sites plus mixed nearby plots
- benchmark similarity and benchmark-site overlap is visually obvious
- invasive probability has enough contrast to be meaningful
- benchmark-site toggle affects only benchmark points
- suggestion toggle affects only suggested points
- the suggestion points are plausible anti-benchmark candidates
- the red selected plot appears in the southwest hotspot and is the one to use downstream

## Stage 1 Run And Verify

Serve this stage over HTTP from the repo root:

```bash
cd /home/desinotorious/src/github.com/bprashanth/good-shepherd
source .venv/bin/activate
python -m http.server 8031 --directory examples/stack/setup_wizard
```

Then navigate to:

- `http://localhost:8031/wizard.html`

## Stage 2 Preview

Stage 2 can now start from the saved `selected_plot.json` handoff rather than requiring another round of plot picking.
