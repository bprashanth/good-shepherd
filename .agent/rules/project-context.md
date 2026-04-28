# Good Shepherd POC Guidelines

## 1. Project Map

The Good Shepherd POC example apps live under `examples/`. Three **stacks** (personas) are grouped under `examples/stacks/`:

### Persona stacks
* **Research** — `examples/stacks/research/`: new-study flow (`web/`, `pwa/`, `setup_wizard/`, `forms/`, `indicators/`, `alienwise/`, `inputs/`) and ingested-study flow (`web_2/`, `setup_wizard_2/`, `indicators_2/`). Entry hubs: open **`examples/stacks/research/web/index.html`**, **`web_2/index.html`** (ingest), **`examples/stacks/rewild/web/index.html`** (rewild) as **`file://`** URIs—the script prints them. Modals must stay on `file:` (do not serve the hub over `http://localhost` or sibling `file:` links misbehave). Other pieces (PWA, forms dev server, compute server, Alienwise static server) still use localhost URLs from `run_stacks.py`.  
* **Rewild** (practitioner) — `examples/stacks/rewild/`: `web/`, `setup_wizard/`, `pwa/`, `plantwise/`, `indicators/` (mirrors the research pattern with practitioner-focused content). Port map in `examples/stacks/rewild/DEPLOYMENT.md`.  
* **Community** — `examples/stacks/community/`: Frappe app under `frappe/`, OpenClaw/assistant under `assistant/`, shared `inputs/`. Run via Docker per component READMEs (not started by the default `run_stacks.py` script).

To bring up the default research + rewild static servers, compute server, and npm apps: from repo root, `./.venv/bin/python examples/stacks/run_stacks.py` (Ctrl+C stops; next run clears ports in use). Optional: `--stack research`, `--stack rewild`, `--stack community` (community is validated only; Docker is documented separately).

### Other `examples/` roots (out of stack layout)
* `examples/pipeline/`, `examples/site_comparison/` — ignore unless explicitly in scope.  
* `examples/zenodo/` — separate Zenodo/NC pilot assets.

### Key directories and patterns
* **Standards:** any `standards/` subdirectory under a component (e.g. `setup_wizard/standards/`) defines the expected schema/format.  
* **Documentation:** check component `README.md` or `docs/` before proposing changes.  
* **Outputs:** see `outputs.md` in each component for data flow.

### Reference and reference data
* **Reference data:** experiment setup and field reference files live under the research `inputs/` tree (protocols, KML, sample datasheets, xlsx as applicable).

### Output assets (`output/`)
* Stages emit assets for the next layer; see each component’s `outputs.md` and the bootstrap script log for which URLs to open.

## 2. Execution and environment
* **Python path:** use `./.venv/bin/python` (or project `venv`).  
* **Shell:** prefer `source .venv/bin/activate` before ad hoc Python.  
* **Tooling:** simple automation: Bash; heavier orchestration: use `examples/stacks/run_stacks.py`.  
* **Dependencies:** minimize new packages; use `requirements.txt`. Do not add dependencies without explicit approval.

## 3. Tech stack preferences
* **Backend:** Python.  
* **Frontend:** simple HTML/JS or Vue 3. Keep the POC light.  
* **Standards:** prefer readability over unnecessary abstraction.

## 4. Operational guardrails
* **Read and propose:** read the codebase; propose nontrivial changes before applying.  
* **Execution:** you may run shell/Python for discovery and tests.  
* **Write:** for substantive edits, explain intent first when the repo asks for it.  
* **Linting:** do not block on style-only issues.  
* **Geospatial:** default to EPSG:4326 unless file metadata says otherwise.

## 5. Backend
* The `server/` backend consolidates auth and shared APIs across Good Shepherd. New APIs: see `server/README.md`. Treat server changes with care: if the server is broken, the product is broken. Ask when unclear.
