# Field Aliasing Design

## Goal
Create a single `variables_codebook.json` that defines canonical field names and aliases across all inputs (forms + Excel). This ensures that:
- the variable catalog shows the same names that appear in the final dataset
- computed variable formulas target the correct dataset columns

## Agent scope
The agent should match equivalent fields across all sources:
- Form JSON headers (from `_classified.json`)
- Excel sheet column headers

Examples:
- `plot #` (excel) ↔ `plotnum` (form) ↔ `plot_no` (form) → canonical `plot_number`

## Canonical name selection (deterministic)
1. Prefer a canonical name that already exists in form JSON.
2. If multiple form names exist, choose the most frequent.
3. If no form name exists, fall back to the Excel name (normalized/slugified).

## Mismatch handling
- **Excel-only fields**: included with `unmatched_source: "excel_only"`.
- **Form-only fields**: included with `unmatched_source: "form_only"`.

## Provenance vs source
- `provenance`: where the canonical name originates (`forms` or `excel`).
- `aliases[].source`: the specific file or sheet where the alias appears.

## Proposed schema (field_aliases.schema.json)
```json
{
  "variables": [
    {
      "canonical_name": "plot_number",
      "provenance": "forms",
      "aliases": [
        {"name": "plot_no", "source": "form:cloud_segmented_000_classified.json"},
        {"name": "Plot #", "source": "excel:Raw 10x10m Data"}
      ],
      "unmatched_source": ""
    }
  ]
}
```

## Pipeline placement
1. Extract form field names + Excel column names.
2. Run agent to generate `variables_codebook.json`.
3. Use the codebook to normalize both:
   - `variable_catalog.json`
   - `indicator_dataset.json`

## Wizard UI
Add a "Field Mapper" step before the current panels to show:
- canonical name → aliases + sources
- allow manual edits and additions

Edits should be saved back into the downloaded codebook.

## Implementation notes

### How aliasing works (summary)

- build_field_sources.py extracts raw field names + sources from forms and Excel.
- Agent produces output/variables_codebook.json following deterministic rules.
- Both build_variable_catalog.py and build_dataset.py map every field via:
canonical = alias_map[normalize(field_name)] or field_name
- This keeps UI names and dataset column names in sync.


Example alias lookup:

variables_codebook.json
```json
{
  "variables": [
    {
      "canonical_name": "plot_number",
      "aliases": [
        {"name": "plot_no", "source": "form:..."},
        {"name": "plotnum", "source": "form:..."},
        {"name": "Plot #", "source": "excel:Raw 10x10m Data"}
      ]
    }
  ]
}
```

Lookup map (after normalization):
- normalize(\"plot_number\") -> plot_number
- normalize(\"plot_no\") -> plot_number
- normalize(\"plotnum\") -> plot_number
- normalize(\"Plot #\") -> plot_number

During dataset building and variable catalog creation:
```
canonical = alias_map[normalize(field_name)] or field_name
```


