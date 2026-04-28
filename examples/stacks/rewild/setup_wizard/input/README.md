# Site information

This folder now contains two JSON metadata files that summarize the site layout. 

### `anr_sites.json`

It includes:

- `monitoring_sites`: only the unique photomonitoring/pwa sites, tagged `monitoring`
- `study_area.monitoring_convex_hull`: the convex hull around those monitoring sites
- `study_area.monitoring_convex_hull_buffered`: a 10 km buffer around that hull
- `osuri_sites_within_buffer`: all Osuri plots with coordinates inside that buffered area, tagged `active`, `passive`, or `benchmark`
- `benchmark_sites_missing_coordinates`: benchmark plots present in Osuri but not spatially testable because their coordinates are missing

Use this file when you want a smaller geographic subset around the photo-monitoring network.

### `anr_metadata.json`

Of note: 

- `plot_boundaries`: per-plot geometry metadata for the 20 x 20 m adult-tree plots and the nested 5 x 5 m sapling subplots



## Classifications

The site classifications are:

- `active`: actively restored Osuri plots
- `passive`: naturally regenerating Osuri plots
- `benchmark`: less-disturbed reference forest plots from the Osuri study
- `monitoring`: sites from `db.json`, used here only as photo-monitoring locations

### Satellite/model validation indicators used in this project

- `Alpha Earth embedding similarity to benchmark`: an embedding-space measure of how close a plot looks, from satellite data, to the benchmark forest condition

- `Alienwise` output tifs for the invasives probability map. 
