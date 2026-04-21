#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

source .venv/bin/activate

python examples/indicators_2/scripts/build_osuri_exports.py \
  --input-dir examples/indicators_2/input \
  --out-dir examples/indicators_2/output

python examples/indicators_2/scripts/build_indicator_wizard.py \
  --variable-catalog examples/indicators_2/output/variable_catalog.json \
  --codex examples/indicators_2/output/codex.json \
  --variables-codebook examples/indicators_2/output/variables_codebook.json \
  --out-html examples/indicators_2/output/indicator_wizard.html \
  --out-computed examples/indicators_2/output/computed_variables.json \
  --out-indicators examples/indicators_2/output/indicator_config.json \
  --out-mapping examples/indicators_2/output/indicator_field_mapping.html
