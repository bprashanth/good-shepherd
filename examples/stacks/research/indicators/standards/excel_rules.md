# Excel Parsing Rules (POC)

These rules help determine whether an Excel sheet can be flattened directly into a long table or requires human review.
The dataset builder should apply these heuristics conservatively and emit warnings when a sheet appears to be a matrix/pivot layout.

## Allowed (Directly Flattenable)
- **Simple tabular sheets** with:
  - A single header row.
  - Consistent column count across rows.
  - Mostly scalar values per cell.
- **Record-style sheets** where each row is an observation and each column is a field.

## Flag for Review (Matrix / Pivot-like)
If any of the following is detected, flag the sheet as requiring manual serialization:

1. **Multiple header rows**
   - Two or more top rows with a high ratio of text values and repeating patterns.

2. **Merged cells**
   - Any merged cells in the header region (common in matrices).

3. **Wide numeric blocks with row/column labels**
   - A contiguous block where the first row is mostly text labels and the subsequent rows are mostly numeric values.
   - Often indicates a matrix (e.g., years across columns and sites down rows).

4. **Irregular row lengths**
   - Significant variation in number of non-empty cells per row.

5. **Cross-tab structure**
   - First column contains labels, first row contains labels, and the interior is mostly numeric.

## Minimal Heuristics (POC)
A sheet should be flagged if **two or more** of the following are true:
- Header row contains fewer than 50% unique values (repeated labels).
- More than 20% of cells are merged in the header region.
- Non-empty cell counts vary by more than 30% across rows.
- The first row is text-heavy and the next 3+ rows are numeric-heavy.

## Output Behavior
- **If flattenable**: convert rows directly into records.
- **If flagged**: emit a warning and skip or require user confirmation.

## Notes
- These rules are intentionally conservative for the POC.
- The goal is to avoid incorrect flattening and instead surface ambiguous layouts to the user.
