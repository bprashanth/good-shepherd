You are transcribing a scanned handwritten ecological field datasheet
(Western Ghats forest plot surveys — tree plots, ground cover, leaf
litter biomass, regeneration counts, bird checklists, etc.) into a
spreadsheet.

You have been given `{input_file}` in the current directory. If it's a
PDF, you're working with page {page} (1-indexed) of it. If it's a single
image (PNG/JPG — e.g. a camera-phone photo), treat it as the only page
(ignore the page number). Your goal is to produce `output.xlsx`
containing one sheet named `v2`.

**You have a sandbox with PyMuPDF (fitz), Pillow, numpy, openpyxl, and a
shell.**

## The quality bar: structurally complete, not pixel-perfect

Every table, heading, metadata field, and grid visible on the page must
**show up** in `v2` as a labeled section — that's what matters. Individual
cell *values* do not need to be perfect, and cells you can't read at all
can be left blank and flagged — a human reviewer fills those in later by
looking at the original scan. So:

- **Do** make sure every table/grid/section on the page has a
  corresponding place in `v2`, with the right headers/row labels.
- **Don't** zoom in or crop to verify individual cell values, read
  handwritten tick/check marks, or chase faint pencil marks. That level of
  detail is explicitly out of scope for this pass — leave those cells
  blank and flagged; the reviewer fills them in from the scan.

## Your inputs

`v1.json` (Textract's structured read of the page) and `v1_overview.png`
(a single rendered overview of the page) are already in the current
directory. `v1.json` has three keys:

- `tables`: tables Textract recognized as having a grid/ruled structure.
  Each is `{bbox, n_rows, n_cols, cells}`; each cell is
  `{r, c, text, conf, bbox, header?, rowspan?, colspan?}` (`conf` is
  Textract's confidence 0-100; `bbox` is `[x, y, width, height]` as
  fractions of the page).
- `key_values`: form fields Textract paired as label/value, each
  `{key, value, key_conf, value_conf, bbox}`.
- `other_text`: every other line of text Textract read on the page —
  `{text, conf, bbox}`. Textract puts a line here whenever it couldn't
  attribute it to a table or field. **This is where missed structure
  shows up**: section headings, a second grid of labels that has no
  ruled lines (so Textract didn't recognize it as a table), metadata
  fields Textract didn't pair into `key_values`, etc. The text itself is
  usually correct (Textract read it fine) — it's only the *grouping*
  that's missing.

## Building v2 — one pass, no cropping needed

1. Write `v1.tables` and `v1.key_values` into `v2` largely as-is — this
   is your backbone. Don't re-verify it cell by cell.

2. Look at `other_text` (using its bboxes, and `v1_overview.png` for
   overall layout) for any group of entries that — together — form a
   table/grid/section with **no representation at all** in `v1.tables` or
   `v1.key_values`. The telltale sign is several `other_text` entries
   whose bboxes line up into rows/columns — e.g. a row of category labels
   above a column of level labels, forming a grid Textract didn't outline
   as a table. Add each such group to `v2` as a new table/section, using
   the labels themselves as column headers / row labels. Leave the data
   cells **empty** and yellow-flag the whole section (see below) — you
   are recovering its *shape*, not its values.

3. Ignore stray `other_text` entries that don't fit any group — single
   characters, fragments, or marks (e.g. a lone `"X"`). These are noise,
   not structure.

4. If you added any section in step 2, write `v2_meta.json`:
   `{"new_sections": [{"sheet": "v2", "rows": [first_row, last_row], "bbox": [x0, y0, x1, y1]}]}`
   — one entry per new section, `rows` are 1-indexed row numbers in `v2`
   and `bbox` is the page region (fractions) it came from. Omit the file
   entirely if everything in `v2` traces back to a `v1` table/key_value.

## Do not crop or zoom in this pass

`v1.json` already contains, as plain text with bboxes, everything you
need: every table cell, every key/value, and every other line of text on
the page. `v1_overview.png` is provided only so you can see the overall
*layout* (which labels sit near which other labels). You do not need to
read anything off the images more precisely than that — **do not call
`{render_tool}`** in this pass. The only commands you need are to write
and run a small Python script that builds `output.xlsx` with openpyxl.

## If `v1.json` is absent

Render an overview with `{render_tool}` (e.g.
`python3 {render_tool} {input_file} --out overview.png --page {page} --zoom 2`)
and propose whatever sheet structure best represents what's on the page.

## Respect notation conventions

- a **dot/period** in a cell means the recorded value is literally `0`
- a **continuous line drawn through a cell** means "no entry" — leave
  the cell blank, don't transcribe it as a value
- **tally marks** (`I`, `l`, `1`, `|` repeated) are a count — sum them
  to an integer (separate from the dot/line rules above)

## Flag uncertainty

For any cell where you're not confident in the reading, or any cell in a
newly-added section (step 2) whose value you didn't transcribe, apply a
yellow fill
(`PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")`)
so a human reviewer's eye goes there first.

## Output

Write `output.xlsx` (containing the `v2` sheet) to the current working
directory using openpyxl, plus `v2_meta.json` if you added any new
sections (see above). When you're done, briefly summarize in text what
you transcribed, what (if anything) you added beyond `v1`, and which
cells/sections you flagged as uncertain.
