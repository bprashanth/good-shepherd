# Design: Return Bounding Boxes from POST /api/upload

## Goal

Enable the PWA form viewer to highlight the table row on the cropped form image that
corresponds to the species (or other) row a biologist is correcting. Today
`POST /api/upload` returns only an `.xlsx` file. This design extends the API to return
bounding box data together with the spreadsheet, and adds a **reserved system row ID**
column in Excel so the **agent server** and **PWA** can agree on a stable row key even
when the form’s own serial column is missing, messy, or renumbered later.

## Background

Textract returns normalized geometry for table cells. In this repo, `amazon-textract-textractor`
represents each `TableCell` with a **`bbox`** (`x`, `y`, `width`, `height` in normalized
0–1 coordinates, equivalent to Textract’s `Left` / `Top` / `Width` / `Height`). The server
already walks TABLE → CELL in `table_extractor.py`; reading those boxes adds no AWS cost.

The PWA keeps the cropped image in the client (`formStore.croppedImage`). The gap is a
**stable join key** between (a) rows the agent reasons about from Excel and (b) row
highlights on the image.

### Why a reserved “system row ID” column

The agent pipeline (see copies under `server/docs/`) infers column types, optionally
renumbers user-facing serial columns (`check-serial`), then uses serial-like values to
order species proposals (`extract_species_with_serial`). That logic **assumes** a usable
serial column when present; without it, ordering falls back to scan order only.

Adding a column written only by Good Shepherd—**not** part of the original form—gives a
canonical integer per **data row** that:

- Aligns 1:1 with bbox entries returned from upload
- Is not meant for biologists to edit (distinct styling in Excel)
- Should be **ignored by type inference** and **never rewritten** by `check-serial`

## Proposed API change

**Extend `POST /api/upload` and `POST /api/upload/json` in place** (same URLs; response
shape changes—see client modifications for migration).

Response `application/json`:

```json
{
  "xlsx": "<base64-encoded xlsx>",
  "rows": [
    {
      "system_serial": 1,
      "bbox": { "left": 0.05, "top": 0.12, "width": 0.90, "height": 0.03 }
    }
  ]
}
```

- **`system_serial`**: Monotonic integer **in sheet row order**, one entry per **table
  data row** written by `excel_service` (legend and universal-field rows are omitted;
  each table’s header row is omitted). If multiple Textract tables are written on the
  same sheet, IDs continue across tables in the same order as rows appear in the
  workbook (so bbox order matches Excel walk order).
- **`bbox`**: Axis-aligned union of that row’s table cell boxes; `left` / `top` /
  `width` / `height` are normalized fractions (same convention as `BoxOverlay`).

Universal fields (KEY_VALUE_SET) are not table rows: they do not receive
`system_serial` entries in `rows[]`.

## Excel workbook changes (Good Shepherd)

In `server/services/excel_service.py`, for each table block:

1. Append one header cell at the **end** of the table header row with a **fixed,
   documented label** (e.g. `(Good Shepherd) Row ID`—exact string is part of the public
   contract so the agent can detect it).
2. For each data row, write the matching integer in that column (same value as
   `system_serial` in the JSON `rows` array for that row).
3. Style that column distinctly: e.g. grey font, optional dotted border, so it is
   obviously not original field data.

The upload JSON `rows` array is built in the same pass order as these cells are written.

## Good Shepherd implementation sketch

1. **`server/services/table_extractor.py`**  
   - Helper to compute per–data-row union bbox from `TableCell.bbox` (normalized
     `x,y,width,height` → response `left,top,width,height`).

2. **`server/services/excel_service.py`**  
   - Write the reserved column and styles.  
   - Optionally return metadata (e.g. parallel list of `system_serial`) if the router
     prefers not to duplicate row-walk logic—keep a **single source of truth** for
     serial assignment.

3. **`server/routers/upload.py`**  
   - After `extract` + `to_xlsx`, attach bbox list keyed by `system_serial`, return JSON
     with `xlsx` and `rows`.

## API Gateway

Existing `POST /api/{proxy+}` covers `/api/upload` and `/api/upload/json`; JWT unchanged.

---

## Client modifications

Reference copies in this repo vs the **form-idable** originals:

| Original (form-idable) | Copy in good-shepherd (reference) |
|------------------------|-----------------------------------|
| `form-idable/agent/server/routers/checks.py` | [server/docs/agent_router_checks.py](../agent_router_checks.py) |
| `form-idable/agent/server/services/excel.py` | [server/docs/agent_excel.py](../agent_excel.py) |
| `form-idable/pwa/src/views/ResultView.vue` | [server/docs/ResultView.vue](../ResultView.vue) |

### Current agent behaviour (reference copies)

- **`agent_router_checks.py` — `infer-types`**: Reads workbook headers via
  `excel.get_headers`, runs fuzzy type inference, returns `type_map` and `all_headers`.
- **`agent_router_checks.py` — `check-serial`**: Requires at least one column typed
  `serial`; renumbers those columns row-by-row with `excel.apply_serial_numbering`.
- **`agent_router_checks.py` — `check-species`**: Requires `species` columns; calls
  `excel.extract_species_with_serial(xlsx, species_cols, serial_cols)`. That function
  uses the **first** resolved serial column to attach `first_serial` to each distinct
  species string for sorting proposals; if no serial column, it falls back to **row
  scan order** (see `agent_excel.py`, `row_num` fallback).

- **`agent_excel.py`**: Finds the table by scanning for the first row with **two or more
  bold** cells (`_find_header_row`). All later logic is keyed off that header row.

### Agent server changes (to implement in form-idable; mirror here when ported)

1. **Reserved column contract**  
   - Treat the Good Shepherd header (exact string TBD and documented next to
     `excel_service`) as the **canonical row id** for bbox and species review.  
   - **Type inference**: Exclude this header from fuzzy species/serial matching (treat as
     `system` / ignore) so it never becomes the “species” column.  
   - **`check-serial`**: When renumbering user serial columns, **skip** any column whose
     header is the reserved system column—those integers must stay aligned with bbox
     `system_serial`.  
   - **`extract_species_with_serial`**: Prefer the reserved column for `first_serial` /
     per-row identity when present; keep existing behaviour as fallback for legacy
     workbooks without the column.

2. **Species proposals payload**  
   - Extend proposal objects (or parallel field) with `system_serial` (from the row’s
     reserved cell) so the PWA can call `bboxBySystemSerial[system_serial]` without
     inferring from user `S.No.` after renumbering.

3. **`apply_species_corrections`**  
   - No change needed if it continues to touch only species-typed columns; verify the
     reserved column is never in `species_cols`.

### PWA changes (to implement in form-idable; mirror `ResultView.vue` here when ported)

1. **Upload handling**  
   - Parse JSON from `POST /api/upload` (`xlsx` + `rows`). Decode `xlsx` into
     `xlsxBytes` as today. Store `rows` (or a `Map(system_serial → bbox)`) alongside the
     workbook in the form store.

2. **Species review UI**  
   - When rendering a proposal, use **`system_serial` from the agent** (once exposed) to
     select the highlight bbox.  
   - If the agent response is not yet extended, interim option: read the reserved column
     from the sheet for the row that contains each species value (heavier); prefer
     agent-returned `system_serial`.

3. **Overlay**  
   - Reuse `BoxOverlay` with fractional `left/top/width/height` from the matching `rows`
     entry.

---

## What this design explicitly excludes

- No cell-level bboxes in the first version (row-level union is enough for row highlight).
- No coordinate transforms beyond normalized fractions → CSS `%` as today.
- No bbox rows for universal KEY_VALUE blocks (not part of the main table grid).
