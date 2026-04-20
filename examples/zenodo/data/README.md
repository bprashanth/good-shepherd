# NCF India CSV Extraction Outputs

This directory contains a reproducible CSV download + extraction workflow for NCF India Zenodo records.
The workflow is implemented in `download_ncfindia_csvs.py` and validated with `verify_species_occurrences.py`.

## How `species_occurrences.json` Is Produced

1. Read all records from `ncfindia_all_records.json`.
2. For each record, download **all `.csv` files** into:
   - `ncfindia/<paper_slug>/inputs/<csv_file>`
3. For every CSV, try to detect:
   - species column
   - latitude column
   - longitude column
   - timestamp/date column (optional)
4. If a CSV does **not** have usable lat/lon/species for row-level occurrence extraction:
   - it is **skipped for occurrence rows**
   - it is still documented in `csv_paper_lookup.json` with diagnostics (`lat_column`, `lon_column`, etc.)
5. If a CSV has usable species + lat + lon:
   - each valid row is emitted into `species_occurrences.json`
   - mapped as `{species, lat, lon, timestamp, source, csv_file, row}`
6. For each source/paper, all valid geospatial points are aggregated to compute paper-level `net_bounds`
   (bbox + convex hull + hull perimeter), stored in `csv_paper_lookup.json`.

## Output JSONs: Purpose and Schema

### `source_lookup.json`

Purpose:
- Short source-id registry for papers (e.g. `raman2026`).
- Use this to resolve source IDs in occurrence rows into title/DOI/record metadata.

Top-level schema:
- `generated_at`: string (ISO datetime)
- `count`: number of sources
- `sources`: object keyed by `source_id`
  - `title`: paper title
  - `paper_slug`: local folder slug
  - `zenodo_id`: Zenodo record id
  - `record_id`: record id (numeric)
  - `doi`: DOI string
  - `doi_url`: DOI URL
  - `publication_date`: record timestamp
  - `first_author`: normalized first-author surname

### `csv_paper_lookup.json`

Purpose:
- Per-CSV extraction diagnostics and metadata bridge from source/paper to each downloaded CSV.
- Includes paper-level spatial bounds (`net_bounds`) derived from all valid geospatial rows for that source.

Top-level schema:
- `generated_at`: string (ISO datetime)
- `count`: number of CSV entries
- `source_bounds`: object keyed by `source_id`
  - `point_count`: number of valid geospatial points
  - `bbox`: `{min_lat, max_lat, min_lon, max_lon}`
  - `hull_perimeter_km`: convex-hull perimeter
  - `hull`: array of `{lat, lon}` hull vertices
- `entries`: array of per-CSV objects
  - `source`, `title`, `paper_slug`, `zenodo_id`, `doi`
  - `csv_key`, `csv_path`, `csv_url`, `downloaded_now`
  - `species_column`, `lat_column`, `lon_column`, `timestamp_column`
  - `geospatial_rows`, `species_rows_extracted`, `rows_scanned`
  - `net_bounds` (same structure as `source_bounds[source]`, or `null`)

Important note:
- `lat_column`/`lon_column` can be `null` for non-spatial CSVs (for example name-mapping tables).
- That does **not** prevent other CSVs under the same source from producing valid occurrences.

### `species_occurrences.json`

Purpose:
- Biodiversity lookup-ready row-level output.
- Canonical flattened occurrence list built only from rows with valid species + lat + lon.

Top-level schema:
- `generated_at`: string (ISO datetime)
- `count`: number of occurrence rows
- `entries`: array of occurrence objects
  - `species`: string
  - `lat`: number
  - `lon`: number
  - `timestamp`: string or `null`
  - `source`: short source id (lookup in `source_lookup.json`)
  - `csv_file`: relative CSV file path
  - `row`: source CSV row number (1-indexed data row)

## Verification

Run reverse validation to verify every occurrence row maps back to the source CSV row:

```bash
source .venv/bin/activate && python examples/zenodo/data/verify_species_occurrences.py
```

This writes:
- `species_occurrences_verification.json` with pass/fail summary and failure samples.
