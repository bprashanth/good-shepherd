#!/bin/bash
set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$BASE_DIR/scripts"
STANDARDS_DIR="$BASE_DIR/standards"
OUT_DIR="$BASE_DIR/output"

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <indicators_pdf> <forms_dir> [optional_xlsx]"
    exit 1
fi

INDICATORS_PDF="$1"
FORMS_DIR="$2"
OPTIONAL_XLSX="$3"

VENV_DIR="$BASE_DIR/../../.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Error: .venv not found at $VENV_DIR" >&2
    exit 1
fi

mkdir -p "$OUT_DIR"

echo "--- Step 0: Extract Field Sources ---"
source "$VENV_DIR/bin/activate"
python3 "$SCRIPTS_DIR/build_field_sources.py" \
  --forms-dir "$FORMS_DIR" \
  --xlsx "$OPTIONAL_XLSX" \
  --out "$OUT_DIR/field_sources.json"

echo "Field sources saved to $OUT_DIR/field_sources.json"

echo "--- Step 0b: Build Variables Codebook ---"
PROMPT_FIELDS="$OUT_DIR/field_mapping_prompt.md"
cat > "$PROMPT_FIELDS" <<'PROMPT'
# Role
You are a field-mapping assistant. You match equivalent field names across forms and Excel and choose a canonical name for each group.

# Instructions
- Use the field_sources.json content below as the source of truth.
- Group equivalent fields across sources into a single canonical name.
- Follow the canonical selection rules:
  1. Prefer a name that already exists in forms.
  2. If multiple form names exist, choose the most frequent.
  3. If no form name exists, fall back to the Excel name (normalized/slugified).
- For Excel-only fields, set unmatched_source to "excel_only".
- For form-only fields, set unmatched_source to "form_only".
- Use provenance to indicate whether the canonical name came from forms or excel.
- Output must be valid JSON and conform to the field_aliases schema.

# Strict Output Rules
1. Return ONLY valid, raw JSON.
2. NO markdown code blocks.
3. NO conversational filler.
4. Output must start with '{' and end with '}'.

# Output Schema
PROMPT
cat "$STANDARDS_DIR/field_aliases.schema.json" >> "$PROMPT_FIELDS"
cat >> "$PROMPT_FIELDS" <<'PROMPT'

# Field Sources
PROMPT
cat "$OUT_DIR/field_sources.json" >> "$PROMPT_FIELDS"

"$SCRIPTS_DIR/run_agent.sh" "$PROMPT_FIELDS" "$OUT_DIR/field_sources.json" > "$OUT_DIR/variables_codebook_raw.json"
echo "Variables codebook raw saved to $OUT_DIR/variables_codebook_raw.json"

echo "--- Step 0c: Sanitize Variables Codebook ---"
RAW_CODEBOOK="$OUT_DIR/variables_codebook_raw.json"
FINAL_CODEBOOK="$OUT_DIR/variables_codebook.json"
RAW_CODEBOOK="$RAW_CODEBOOK" FINAL_CODEBOOK="$FINAL_CODEBOOK" python3 - <<'PY'
import json
import os
from pathlib import Path

raw_path = Path(os.environ["RAW_CODEBOOK"])
out_path = Path(os.environ["FINAL_CODEBOOK"])

text = raw_path.read_text(encoding="utf-8").strip()
if text.startswith("```"):
    lines = text.splitlines()
    if lines:
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    text = "\n".join(lines).strip()

data = json.loads(text)
out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
print(f"Sanitized variables codebook saved to {out_path}")
PY

echo "--- Step 1: Build Variable Catalog ---"
source "$VENV_DIR/bin/activate"
python3 "$SCRIPTS_DIR/build_variable_catalog.py" \
  --forms-dir "$FORMS_DIR" \
  --variables-codebook "$OUT_DIR/variables_codebook.json" \
  --out "$OUT_DIR/variable_catalog.json"

echo "Variable catalog saved to $OUT_DIR/variable_catalog.json"

echo "--- Step 2: Construct Prompt ---"
PROMPT_OUT="$OUT_DIR/constructed_prompt.md"

cat > "$PROMPT_OUT" <<'PROMPT'
# Role
You are an ecological data assistant. You extract computed variables and indicator mappings from indicator documents and raw variable catalogs.

# Instructions
- Use the provided indicator PDF and the raw variable catalog to propose computed variables and indicators.
- Prefer JSONLogic expressions for compiled rules. Use JS only when JSONLogic is insufficient.
- Include evidence references (PDF page/snippet, Excel row/cell, or form field name).
- Output a single JSON object that matches the schema sections below.
- The JSON must be valid and must not include any extra text.
- Identify and include all indicators mentioned in the PDF, even if required variables are missing. For unknown mappings, set required_computed_variables to [] and add status \"draft\" with a short notes field explaining what is missing.
- The optional Excel file may contain variable definitions and lookup tables. Use it if provided.

# Strict Output Rules
1. Return ONLY valid, raw JSON.
2. NO markdown code blocks.
3. NO conversational filler.
4. Output must start with '{' and end with '}'.

# Error Handling
If the files are incompatible or missing, output: {"error": "detailed reason"}

## Output Shape (Root)
The output must be a JSON object with exactly two top-level keys:
- "computed_variables": object matching computed_variables.schema.json
- "indicator_config": object matching indicator_config.schema.json

## computed_variables.schema.json
PROMPT
cat "$STANDARDS_DIR/computed_variables.schema.json" >> "$PROMPT_OUT"
cat >> "$PROMPT_OUT" <<'PROMPT'

## indicator_config.schema.json
PROMPT
cat "$STANDARDS_DIR/indicator_config.schema.json" >> "$PROMPT_OUT"
cat >> "$PROMPT_OUT" <<'PROMPT'

## graph_intent.schema.json
PROMPT
cat "$STANDARDS_DIR/graph_intent.schema.json" >> "$PROMPT_OUT"
cat >> "$PROMPT_OUT" <<'PROMPT'

## evidence.schema.json
PROMPT
cat "$STANDARDS_DIR/evidence.schema.json" >> "$PROMPT_OUT"
cat >> "$PROMPT_OUT" <<'PROMPT'

# Raw Variable Catalog
Below is the extracted raw variable catalog. Use these names as inputs to computed variables.
PROMPT
cat "$OUT_DIR/variable_catalog.json" >> "$PROMPT_OUT"

echo "Prompt saved to $PROMPT_OUT"

echo "--- Step 3: Run Agent ---"
AGENT_ARGS=("$PROMPT_OUT" "$INDICATORS_PDF")
if [ -n "$OPTIONAL_XLSX" ]; then
    AGENT_ARGS+=("$OPTIONAL_XLSX")
fi

"$SCRIPTS_DIR/run_agent.sh" "${AGENT_ARGS[@]}" > "$OUT_DIR/indicator_codebook_raw.json"

echo "Raw codebook saved to $OUT_DIR/indicator_codebook_raw.json"

echo "--- Step 3b: Sanitize Agent Output ---"
source "$VENV_DIR/bin/activate"
RAW_CODEBOOK="$OUT_DIR/indicator_codebook_raw.json"
FINAL_CODEBOOK="$OUT_DIR/indicator_codebook.json"
RAW_CODEBOOK="$RAW_CODEBOOK" FINAL_CODEBOOK="$FINAL_CODEBOOK" python3 - <<'PY'
import json
import os
from pathlib import Path

raw_path = Path(os.environ["RAW_CODEBOOK"])
out_path = Path(os.environ["FINAL_CODEBOOK"])

text = raw_path.read_text(encoding="utf-8").strip()
if text.startswith("```"):
    lines = text.splitlines()
    if lines:
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    text = "\n".join(lines).strip()

data = json.loads(text)
out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
print(f"Sanitized codebook saved to {out_path}")
PY

echo "--- Step 4: Build Wizard HTML ---"
source "$VENV_DIR/bin/activate"
python3 "$SCRIPTS_DIR/build_indicator_wizard.py" \
  --variable-catalog "$OUT_DIR/variable_catalog.json" \
  --codex "$OUT_DIR/indicator_codebook.json" \
  --variables-codebook "$OUT_DIR/variables_codebook.json" \
  --out-html "$OUT_DIR/indicator_wizard.html" \
  --out-mapping "$OUT_DIR/indicator_field_mapping.html" \
  --out-computed "$OUT_DIR/computed_variables.json" \
  --out-indicators "$OUT_DIR/indicator_config.json"

echo "Wizard generated at $OUT_DIR/indicator_wizard.html"

echo "--- Step 4b: Normalize Indicator Config ---"
source "$VENV_DIR/bin/activate"
python3 "$SCRIPTS_DIR/normalize_indicator_config.py" \
  --indicator-config "$OUT_DIR/indicator_config.json" \
  --variables-codebook "$OUT_DIR/variables_codebook.json" \
  --out "$OUT_DIR/indicator_config.json"

echo "--- Step 5: Build Dataset ---"
DATASET_RAW="$OUT_DIR/indicator_dataset_raw.json"
DATASET_OUT="$OUT_DIR/indicator_dataset.json"
DATASET_ARGS=(--forms-dir "$FORMS_DIR" --out "$DATASET_RAW" --variables-codebook "$OUT_DIR/variables_codebook.json")
if [ -n "$OPTIONAL_XLSX" ]; then
    DATASET_ARGS+=(--xlsx "$OPTIONAL_XLSX")
fi
source "$VENV_DIR/bin/activate"
python3 "$SCRIPTS_DIR/build_dataset.py" "${DATASET_ARGS[@]}"
echo "Raw dataset saved to $DATASET_RAW"

echo "--- Step 6: Postprocess Dataset ---"
source "$VENV_DIR/bin/activate"
python3 "$SCRIPTS_DIR/postprocess_dataset.py" --in "$DATASET_RAW" --out "$DATASET_OUT"
echo "Dataset saved to $DATASET_OUT"

if command -v curl >/dev/null 2>&1; then
    if ! curl -sf "http://localhost:8765/health" >/dev/null; then
        echo "Warning: compute server not running. Start it to use Generate formula in the wizard via: source ../../.venv/bin/activate && python3 scripts/compute_server.py"
    fi
else
    echo "Warning: curl not found. Unable to check compute server status."
fi
