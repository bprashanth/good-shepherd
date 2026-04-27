#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

source .venv/bin/activate

python examples/setup_wizard_2/scripts/build_osuri_wizard_inputs.py \
  --input-dir examples/setup_wizard_2/input \
  --experiment-out examples/setup_wizard_2/experiment.json \
  --features-out examples/setup_wizard_2/features.geojson

python examples/setup_wizard_2/scripts/build_wizard.py \
  examples/setup_wizard_2/experiment.json \
  examples/setup_wizard_2/features.geojson \
  > examples/setup_wizard_2/wizard.html
