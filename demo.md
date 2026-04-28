# Running the demo 

Landing page (**prefer opening as a file**, so Experiment / Indicators modals navigate with relative URLs and stay on `file:`; do not serve the hub from `localhost` or the browser blocks `file:` targets)
```
file:///ABS/PATH/TO/repo/examples/stacks/research/web/index.html
```
After `./.venv/bin/python examples/stacks/run_stacks.py`, the script prints your machine’s `file://` URL on stdout.
PWA demo
```
cd examples/stacks/research/pwa
python3 -m http.server 8001
Serving HTTP on 0.0.0.0 port 8001 (http://0.0.0.0:8001/) ...
```
Forms server 
```
cd examples/stacks/research/forms
npm run dev
  ➜  Local:   http://localhost:5173/
```
Indicator server 
```
cd examples/stacks/research/indicators
python3 scripts/compute_server.py
Indicator compute server running on http://127.0.0.1:8765
```
Indicator image 
```
cd examples/stacks/research/indicators
imageview output/indicator_dashboard.png
```
Alienwise server 
```
cd examples/stacks/research/alienwise
python3 -m http.server 8080
Serving HTTP on 0.0.0.0 port 8080 (http://0.0.0.0:8080/) ...
```
Notebooks 
```
desinotorious@pop-os:~/src/github.com/bprashanth/plantwise/PlantWise/alienwise$
lantana_satellite_analysis.ipynb - presence on roads

(good-shepherd) desinotorious@pop-os:~/rtmp/data/shola/data$ 
phase2_site_analysis.ipynb - drone vs satellite 
```

