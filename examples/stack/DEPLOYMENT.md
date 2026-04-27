# Stage 1

```bash
cd /home/desinotorious/src/github.com/bprashanth/good-shepherd
source .venv/bin/activate
python -m http.server 8031 --directory examples/stack/setup_wizard
```

# navigate to `http://localhost:8031/wizard.html`

# Stage 2

```bash
cd /home/desinotorious/src/github.com/bprashanth/good-shepherd
source .venv/bin/activate
python -m http.server 8032 --directory examples/stack/pwa
```

# navigate to `http://localhost:8032/index.html`

# Stage 3

```bash
cd /home/desinotorious/src/github.com/bprashanth/good-shepherd
source .venv/bin/activate
python -m http.server 8033 --directory examples/stack/plantwise
```

# navigate to `http://localhost:8033/index.html`

# Stage 4

```bash
cd /home/desinotorious/src/github.com/bprashanth/good-shepherd
source .venv/bin/activate
python -m http.server 8034 --directory examples/stack/indicators
```

# navigate to `http://localhost:8034/index.html`

# Stage 5

```bash
cd /home/desinotorious/src/github.com/bprashanth/good-shepherd/examples/forms
npm run dev
```

# navigate to `http://localhost:5173`

# Stage 6

```bash
cd /home/desinotorious/src/github.com/bprashanth/good-shepherd
source .venv/bin/activate
python -m http.server 8035 --directory examples/stack/web
```

# navigate to `http://localhost:8035/index.html`

# Appendix: `examples/indicators_2`

Reuse the shared compute server from `examples/indicators`:

```bash
cd /home/desinotorious/src/github.com/bprashanth/good-shepherd/examples/indicators
source ../../.venv/bin/activate
python3 scripts/compute_server.py
```

# compute server runs on `http://127.0.0.1:8765`

Rebuild the Osuri artifacts if needed:

```bash
cd /home/desinotorious/src/github.com/bprashanth/good-shepherd
./examples/indicators_2/process_indicators.sh
```

Open the generated static page directly:

# navigate to `file:///home/desinotorious/src/github.com/bprashanth/good-shepherd/examples/indicators_2/output/indicator_wizard.html`
