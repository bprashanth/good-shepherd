# Site Assesment 

This folder now contains two JSON metadata files that summarize the site assesment step.

### `anr_metadata.json`

Of relevance:

- `plot_boundaries`: per-plot geometry metadata for the 20 x 20 m adult-tree plots and the nested 5 x 5 m sapling subplots

### `anr_sites.json`

- `monitoring_sites`: only the unique `db.json` sites, tagged `monitoring`
- `study_area.monitoring_convex_hull`: the convex hull around those monitoring sites
- `study_area.monitoring_convex_hull_buffered`: a 10 km buffer around that hull
- `osuri_sites_within_buffer`: all Osuri plots with coordinates inside that buffered area, tagged `active`, `passive`, or `benchmark`
- `benchmark_sites_missing_coordinates`: benchmark plots present in Osuri but not spatially testable because their coordinates are missing

## Plot Design

- `20 x 20 m` adult-tree plots (`0.04 ha`)
- nested `5 x 5 m` sapling subplots
