#!/bin/bash
set -e

# Configuration
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"


SCRIPTS_DIR="$BASE_DIR/scripts"
STANDARDS_DIR="$BASE_DIR/standards"

# Check args
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <kml_file> <protocol_pdf> [protocol_pdf_2 ...]"
    exit 1
fi

KML_FILE="$1"
# Shift to get protocols
shift
PROTOCOLS=("$@")

echo "--- Step 1: KML Feature Extraction ---"
python3 "$SCRIPTS_DIR/extract_kml_features.py" "$KML_FILE" --geojson "$BASE_DIR/features.geojson" > "$BASE_DIR/kml_summary.json"
echo "KML summary saved to $BASE_DIR/kml_summary.json"

echo "--- Step 2: Construct Prompt ---"
PROMPT_OUT="$BASE_DIR/constructed_prompt.md"

# Start with System Role (optional, or part of prompt)
echo "# Role" > "$PROMPT_OUT"
cat "$BASE_DIR/json_spatial_system.md" >> "$PROMPT_OUT"
echo "" >> "$PROMPT_OUT"

echo "# Instructions" >> "$PROMPT_OUT"
echo "Analyze the Protocol files and the provided KML Ground Truth." >> "$PROMPT_OUT"
echo "Produce a JSON output matching the following Schema and nothing else." >> "$PROMPT_OUT"
echo "" >> "$PROMPT_OUT"

echo "## Output Schema" >> "$PROMPT_OUT"
cat "$STANDARDS_DIR/experiment_schema.json" >> "$PROMPT_OUT"
echo "" >> "$PROMPT_OUT"

echo "## KML Extraction Rules (Context)" >> "$PROMPT_OUT"
cat "$STANDARDS_DIR/kml_rules.md" >> "$PROMPT_OUT"
echo "" >> "$PROMPT_OUT"

echo "# Ground Truth Data (Features found in KML)" >> "$PROMPT_OUT"
echo "The following spatial hierarchy was extracted from the KML file. USE THESE NAMES EXACTLY." >> "$PROMPT_OUT"
cat "$BASE_DIR/kml_summary.json" >> "$PROMPT_OUT"
echo "" >> "$PROMPT_OUT"

echo "--- Step 3: Run Agent ---"
# Set System Prompt Env Var if needed by gemini cli (as per original run_extraction.sh)
export GEMINI_SYSTEM_MD="$BASE_DIR/json_spatial_system.md"

# Call run_agent.sh
# Note: run_agent expects: prompt_file input_file_1 ...
"$SCRIPTS_DIR/run_agent.sh" "$PROMPT_OUT" "${PROTOCOLS[@]}" > "$BASE_DIR/experiment.json"

echo "Experiment JSON saved to $BASE_DIR/experiment.json"

echo "--- Step 4: Build Wizard HTML ---"
python3 "$SCRIPTS_DIR/build_wizard.py" "$BASE_DIR/experiment.json" "$BASE_DIR/features.geojson" > "$BASE_DIR/wizard.html"

echo "Wizard generated at $BASE_DIR/wizard.html"
