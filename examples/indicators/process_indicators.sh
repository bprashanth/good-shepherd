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

echo "--- Step 1: Build Variable Catalog ---"
source "$VENV_DIR/bin/activate"
python3 "$SCRIPTS_DIR/build_variable_catalog.py" \
  --forms-dir "$FORMS_DIR" \
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
  --out-html "$OUT_DIR/indicator_wizard.html" \
  --out-computed "$OUT_DIR/computed_variables.json" \
  --out-indicators "$OUT_DIR/indicator_config.json"

echo "Wizard generated at $OUT_DIR/indicator_wizard.html"
