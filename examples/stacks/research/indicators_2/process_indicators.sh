#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT_DIR"

source .venv/bin/activate

python examples/stacks/research/indicators_2/scripts/build_osuri_exports.py \
  --input-dir examples/stacks/research/indicators_2/input \
  --out-dir examples/stacks/research/indicators_2/output

python examples/stacks/research/indicators_2/scripts/build_indicator_wizard.py \
  --variable-catalog examples/stacks/research/indicators_2/output/variable_catalog.json \
  --codex examples/stacks/research/indicators_2/output/codex.json \
  --variables-codebook examples/stacks/research/indicators_2/output/variables_codebook.json \
  --out-html examples/stacks/research/indicators_2/output/indicator_wizard.html \
  --out-computed examples/stacks/research/indicators_2/output/computed_variables.json \
  --out-indicators examples/stacks/research/indicators_2/output/indicator_config.json \
  --out-mapping examples/stacks/research/indicators_2/output/indicator_field_mapping.html
