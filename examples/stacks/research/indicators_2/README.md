# Indicator Wizard 2

This stage mirrors `examples/stacks/research/indicators/`, but uses the completed Osuri restoration study as the source instead of upload-time trace mapping.

## Quick Start

### 1) Reuse the compute server from `examples/stacks/research/indicators`

This enables the `Generate formula` button in the wizard UI.

```bash
cd /home/desinotorious/src/github.com/bprashanth/good-shepherd/examples/stacks/research/indicators
source ../../.venv/bin/activate
python3 scripts/compute_server.py
```

The compute server runs on `http://127.0.0.1:8765`.

### 2) Build the Osuri exports

```bash
cd /home/desinotorious/src/github.com/bprashanth/good-shepherd
./examples/stacks/research/indicators_2/process_indicators.sh
```

### 3) Serve the output

```bash
cd /home/desinotorious/src/github.com/bprashanth/good-shepherd/examples/stacks/research/indicators_2/output
python3 -m http.server 8042
```

Then open `http://localhost:8042/indicator_wizard.html`.

## Notes

- The UI is intentionally kept as close as possible to `examples/stacks/research/indicators`.
- This completed-study variant does not depend on OCR trace mapping, even though a minimal mapping artifact is still emitted for structural compatibility.
- The raw variable -> computed variable -> indicator chain is derived from `input/anr_metadata.json` and the Osuri CSVs.
