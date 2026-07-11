You are transcribing a scanned handwritten ecological field datasheet
(Western Ghats forest plot surveys) into a spreadsheet.

You have been given `{input_file}` in the current directory. Your goal is
to produce `output.xlsx` containing one sheet named `v2`.

You have a sandbox with PyMuPDF (fitz), Pillow, numpy, openpyxl, and a shell.
There is NO pre-processed Textract output — work directly from the PDF.

## The quality bar

Every table, heading, metadata field, and grid visible on the page must
show up in `v2` — that's the non-negotiable part. Beyond that, use your
turn budget to verify and correct cell values, read handwritten
marks/ticks, and fill in any gaps you find. A human reviewer will do a
final pass, but the more you get right here, the less they have to fix.

## Using render_page.py to render and crop

```
python3 render_page.py {input_file} --out crop.png --bbox x0,y0,x1,y1 --zoom Z --page N
```

- `--bbox x0,y0,x1,y1` is **fractions (0.0-1.0)** of the page width/height.
- `--zoom` is capped at source native resolution and ~1568px on longest edge.
- Start with a full-page overview (`--zoom 2`, no `--bbox`) to understand
  the layout, then crop/zoom into specific regions to read cell values.
- This PDF may have multiple pages — check all of them.

## Building v2

1. Render each page at a low zoom first to understand the structure.
2. Crop into tables, header blocks, and any marginal annotations.
3. The form may contain repeated form-sheets stacked on one page or across
   pages — keep each form's data clearly separated in `v2`.

## Notation conventions

- A **dot/period** in a cell means the recorded value is literally `0`
- A **continuous line drawn through a cell** means "no entry" — leave blank
- **Tally marks** (`I`, `l`, `1`, `|` repeated) are a count — sum to an integer
- **Checkbox marks** (`✓`, `X`, `x`, ticks) mean "present/yes" — transcribe
  as `X`; an empty/unchecked box means absent — leave blank

## Flag uncertainty

For any cell where you're not confident even after cropping, apply yellow fill
(`PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")`).

## Saving renders and crops

Every time you render a full page overview, save it as `page_N.png`
(e.g. `page_1.png`, `page_2.png`). Crops you take for closer inspection
can use any name but must start with `crop_` (e.g. `crop_001.png`).

## crops_manifest.json

After writing `output.xlsx`, write a `crops_manifest.json` to the current
directory. For every crop you took during the run, add one entry. Format:

```json
{
  "pages": [
    {
      "page": 1,
      "render": "page_1.png",
      "crops": [
        {
          "file": "crop_001.png",
          "bbox": [0.0, 0.3, 1.0, 0.65],
          "rows": "6:20",
          "note": "main vegetation table, rows 1-15"
        }
      ]
    }
  ]
}
```

- `bbox` is `[x0, y0, x1, y1]` as fractions (0.0-1.0) — the same values
  you passed to `--bbox` when you took the crop. If you rendered the full
  page without a bbox, use `[0.0, 0.0, 1.0, 1.0]`.
- `rows` is the approximate xlsx row range the crop covers, e.g. `"6:20"`.
- `note` is a one-line human description.

Only include crops you actually took. Do not invent entries.

## metadata.json

Also write a `metadata.json` to the current directory with header metadata
extracted from the form. All fields are optional — include only what you
can reliably read:

```json
{
  "gps": [10.3149, 76.8312],
  "grid_no": "M15",
  "date": "28.4.2016"
}
```

- `gps`: latitude and longitude as decimal numbers (look for GPS/coordinates in headers)
- `grid_no`: grid reference or plot code visible on the form (e.g. "M15", "B3")
- `date`: survey date in any format you find (e.g. "28.4.2016", "April 2016")

If none of these are visible on the form, write `{}`.

## Output

Write `output.xlsx` (sheet `v2`), `crops_manifest.json`, and `metadata.json`
to the current directory. When done, briefly summarize what you transcribed
and which cells you flagged.

---

Transcribe `{input_file}` into `output.xlsx` as described above. Begin by
rendering an overview of page 1 (saving it as `page_1.png`), then proceed
page by page.
