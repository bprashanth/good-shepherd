# KML and GeoJSON Visualization Script

This script visualizes KML and GeoJSON files side by side for comparison.

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the visualization script:

```bash
python3 visualize_sites.py
```

This will:

1. Load the KML file from `./assets/sites.kml`
2. Load the GeoJSON file from `./assets/sites.geojson`
3. Create side-by-side visualizations
4. Generate `sites_comparison.html` in the project root

## Output Files

- `sites_comparison.html` - Main comparison page with both maps side by side
- `sites_comparison_kml.html` - Individual KML map (also created)
- `sites_comparison_geojson.html` - Individual GeoJSON map (also created)

Open `sites_comparison.html` in your web browser to view the comparison.

See standards/maps.md for a description of the translation rules. 
