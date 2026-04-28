# ANR Metadata Exports

This folder now contains two JSON metadata files that summarize the Osuri restoration study and the nearby photo-monitoring sites.

## Files

### `anr_metadata.json`

This is the fuller metadata export.

It includes:

- `measurements`: what was measured in the Osuri study, which source files hold those measurements, and the basic plot design
- `indicators`: the paper indicators, plus the satellite validation indicators used in this project
- `site_locations`: all Osuri plots tagged as `active`, `passive`, or `benchmark`, plus all `db.json` monitoring sites tagged as `monitoring`
- `plot_boundaries`: per-plot geometry metadata for the 20 x 20 m adult-tree plots and the nested 5 x 5 m sapling subplots
- `clashes`: expected pairings and possible overlaps

Use this file when you want the high-level ingredients needed to rerun or reinterpret the experiment.

### `anr_sites.json`

This is the smaller site-layer export.

It includes:

- `monitoring_sites`: only the unique `db.json` sites, tagged `monitoring`
- `study_area.monitoring_convex_hull`: the convex hull around those monitoring sites
- `study_area.monitoring_convex_hull_buffered`: a 10 km buffer around that hull
- `osuri_sites_within_buffer`: all Osuri plots with coordinates inside that buffered area, tagged `active`, `passive`, or `benchmark`
- `benchmark_sites_missing_coordinates`: benchmark plots present in Osuri but not spatially testable because their coordinates are missing

Use this file when you want a smaller geographic subset around the photo-monitoring network.

## Classifications

The site classifications are:

- `active`: actively restored Osuri plots
- `passive`: naturally regenerating Osuri plots
- `benchmark`: less-disturbed reference forest plots from the Osuri study
- `monitoring`: sites from `db.json`, used here only as photo-monitoring locations

## Indicators In Plain English

These are the main indicators encoded in `anr_metadata.json`.

### Ground indicators from the Osuri study

- `Canopy cover`: how much of the sky is covered by tree canopy above the plot
- `Adult tree density`: how many adult trees were recorded in the 20 x 20 m plot
- `Tree height:diameter ratio`: whether trees are relatively tall and slender versus short and stocky for their trunk size
- `Adult species density`: how many different adult tree species are present in the plot
- `Adult late-successional species density`: how many of those adult species are mature-forest species rather than early or introduced species
- `Community similarity to benchmark rainforest`: how similar a plot’s adult-tree species mix is to the benchmark forest plots
- `Sapling density`: how many seedlings and saplings were counted in the 5 x 5 m subplot
- `Sapling native fraction`: what share of saplings are native rather than introduced
- `Sapling species density`: how many different sapling species were recorded
- `Sapling late-successional species density`: how many sapling species are mature-forest species
- `Aboveground carbon storage`: how much carbon is stored in the standing trees in the plot

### Important non-response site covariate

- `Distance to contiguous forest`: how isolated the site is from large, relatively intact forest; the paper uses this to test whether active restoration matters more in isolated places

### Satellite validation indicators used in this project

- `Meta canopy height`: a satellite-derived structural measure used here as the closest remote-sensing analogue to canopy recovery
- `Alpha Earth embedding similarity to benchmark`: an embedding-space measure of how close a plot looks, from satellite data, to the benchmark forest condition

## Plot Design

The Osuri study uses:

- `20 x 20 m` adult-tree plots (`0.04 ha`)
- nested `5 x 5 m` sapling subplots

No explicit transect geometry is described in the paper or encoded in the CSVs, so the metadata only includes plot and subplot geometry.

## Notes And Caveats

- `db.json` is treated as a source of monitoring-site locations only. It is not used to define the Osuri indicators.
- The Osuri dataset contains benchmark plots with missing coordinates. Those appear in the metadata, but they cannot be used for spatial inclusion tests.
- In the Osuri design, many `site_code` values appear once as `active` and once as `passive`. That is expected and reflects paired treatment/control sampling, not a data error.
- Some monitoring sites fall very close to Osuri plots. Those are reported as overlap candidates, but they are not automatically assumed to be the exact same study point.
