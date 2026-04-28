# Adding New Species - Complete Guide

This guide walks you through the complete end-to-end process of adding a new species to the Alienwise TIF viewer, from downloading observations to generating the final TIF files.

## Overview

The complete pipeline consists of:
1. **Download observations** from GBIF and iNaturalist
2. **Format observations** as CSV files
3. **Train Maxent model** to generate species distribution predictions
4. **Convert to TIF** format for visualization
5. **Regenerate index** to include the new species in the viewer

## Prerequisites

- Python virtual environment with required packages (see `scripts/README.md`)
- Maxent JAR file at `../../maxent.jar` (relative to `alienwise/`)
- Environment layers at `../../final_attributes/` (relative to `alienwise/`)
- Java installed and accessible

## Step-by-Step Process

### Step 1: Download Observations

Use the `download_observations.py` script to download species observations:

```bash
cd alienwise/scripts
source ../../venv/bin/activate  # Activate virtual environment

python3 download_observations.py \
  --species "Your Species Name" \
  --sources "inaturalist,gbif" \
  --output_format json \
  --output_path ../data/Your_species_name_observations.json \
  --start_date 2016-01-01 \
  --end_date 2024-12-31
```

**Parameters:**
- `--species`: Scientific name of the species (e.g., "Lantana camara")
- `--sources`: Data sources to use (comma-separated: "inaturalist,gbif")
- `--output_format`: "json" or "csv" (use json for processing pipeline)
- `--output_path`: Where to save the observations file
- `--start_date`: Start date for observations (YYYY-MM-DD)
- `--end_date`: End date for observations (YYYY-MM-DD)

**Output:** JSON file in `alienwise/data/` directory

### Step 2: Transform Observations to CSV Format

The observations need to be transformed to the format expected by Maxent: `Species,Latitude,Longitude`

You can use the `process_alien_species.py` script which handles this automatically, or manually transform:

**Manual transformation example:**
```python
import json
import csv

# Read JSON observations
with open('data/Your_species_name_observations.json', 'r') as f:
    observations = json.load(f)

# Filter and format
csv_data = []
for obs in observations:
    lat = obs.get('latitude')
    lon = obs.get('longitude')
    if lat is not None and lon is not None:
        csv_data.append({
            'Species': 'Your_species_name',  # Use underscores, no spaces
            'Latitude': float(lat),
            'Longitude': float(lon)
        })

# Write CSV
with open('data/Your_species_name.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['Species', 'Latitude', 'Longitude'])
    writer.writeheader()
    writer.writerows(csv_data)
```

**Output:** CSV file in `alienwise/data/` directory

**Requirements:**
- CSV must have exactly 3 columns: `Species`, `Latitude`, `Longitude`
- Species name should use underscores (e.g., `Lantana_camara`)
- Must have at least 3 observations (Maxent requires >2 points)

### Step 3: Run Maxent Model

Train the species distribution model using Maxent:

```bash
cd alienwise/scripts
source ../../venv/bin/activate

java -Djava.awt.headless=true -cp ../../maxent.jar density.MaxEnt \
  nowarnings noprefixes jackknife \
  outputdirectory=../output/res \
  samplesfile=../data/Your_species_name.csv \
  environmentallayers=../../final_attributes \
  autoRun visible=False
```

**Parameters:**
- `-cp ../../maxent.jar`: Path to Maxent JAR file
- `outputdirectory`: Where to save Maxent output (creates `alienwise/output/res/`)
- `samplesfile`: Path to your CSV file
- `environmentallayers`: Path to environment layers directory

**Output:**
- `alienwise/output/res/Your_species_name.asc` - Raw prediction raster
- `alienwise/output/res/Your_species_name.html` - Model report

**Expected time:** 5-15 minutes per species

### Step 4: Convert ASC to TIF

Convert the Maxent ASC output to GeoTIFF format:

You can use the `process_alien_species.py` script which handles this automatically, or use Python:

```python
import numpy as np
import rasterio
from rasterio.transform import from_origin

# Read ASC file
with open('output/res/Your_species_name.asc', 'r') as f:
    header = {}
    for line in f:
        if line.startswith('ncols'):
            header['ncols'] = int(line.split()[1])
        elif line.startswith('nrows'):
            header['nrows'] = int(line.split()[1])
        elif line.startswith('xllcorner'):
            header['xllcorner'] = float(line.split()[1])
        elif line.startswith('yllcorner'):
            header['yllcorner'] = float(line.split()[1])
        elif line.startswith('cellsize'):
            header['cellsize'] = float(line.split()[1])
        elif line.startswith('NODATA_value'):
            header['nodata'] = float(line.split()[1])
        if len(header) >= 6:
            break
    
    data = np.loadtxt(f, dtype=np.float32)

# Create transform
transform = from_origin(
    header['xllcorner'],
    header['yllcorner'] + header['cellsize'] * header['nrows'],
    header['cellsize'],
    header['cellsize']
)

# Write GeoTIFF
with rasterio.open(
    'output/Your_species_name.tif', 'w',
    driver='GTiff',
    height=header['nrows'],
    width=header['ncols'],
    count=1,
    dtype=data.dtype,
    crs='EPSG:4326',
    transform=transform,
    nodata=header.get('nodata', -9999)
) as dst:
    dst.write(data, 1)
```

**Output:** TIF file in `alienwise/output/` directory

### Step 5: Move TIF to Viewer Directory

Copy the TIF file to the `tifs/` directory where the viewer looks for files:

```bash
cd alienwise
cp output/Your_species_name.tif tifs/
```

### Step 6: Regenerate TIF Index

Update the `tif_index.json` file to include your new species:

```bash
cd alienwise
python3 generate_tif_index.py
```

This script:
- Scans the `tifs/` directory
- Finds all `.tif` files
- Generates/updates `tif_index.json`
- Saves the index in the current directory

**Output:** Updated `tif_index.json` file

### Step 7: View in Browser

Start the HTTP server and open the viewer:

```bash
cd alienwise
python3 -m http.server 8000
```

Then open `http://localhost:8000/alienwise_viewer.html` in your browser.

Your new species should now appear in the autocomplete search!

## Using the Automated Script

For convenience, you can use the `process_alien_species.py` script which automates steps 1-4:

```bash
cd alienwise/scripts
source ../../venv/bin/activate

# Edit the SPECIES_LIST in process_alien_species.py to add your species
# Then run:
python3 process_alien_species.py
```

The script will:
1. Download observations (or skip if JSON already exists)
2. Transform to CSV format
3. Run Maxent models
4. Convert ASC to TIF

Then you still need to:
- Move TIFs: `cp output/*.tif tifs/`
- Regenerate index: `python3 generate_tif_index.py`

## File Naming Conventions

- **Species names**: Use scientific names with underscores (e.g., `Lantana_camara`)
- **CSV files**: `Genus_species.csv` (e.g., `Lantana_camara.csv`)
- **TIF files**: `Genus_species.tif` (e.g., `Lantana_camara.tif`)
- **Observation files**: `Genus_species_observations.json`

## Troubleshooting

### No observations downloaded

- Check internet connection
- Verify species name spelling
- Check API rate limits (GBIF/iNaturalist)
- Try downloading from a single source first

### Maxent fails

- Ensure CSV has >2 observations
- Check Java is installed: `java -version`
- Verify maxent.jar exists and is accessible
- Check environment layers directory exists
- Review Maxent HTML report for errors

### TIF conversion fails

- Ensure rasterio is installed
- Check ASC file exists and is valid
- Verify disk space available
- Check file permissions

### Species not appearing in viewer

- Verify TIF file is in `tifs/` directory
- Regenerate index: `python3 generate_tif_index.py`
- Check browser console for errors
- Verify `tif_index.json` contains the species

## Example: Complete Workflow

Here's a complete example for adding "Lantana camara":

```bash
# 1. Download observations
cd alienwise/scripts
source ../../venv/bin/activate
python3 download_observations.py \
  --species "Lantana camara" \
  --output_path ../data/Lantana_camara_observations.json

# 2-4. Process (transform, Maxent, convert)
# Edit process_alien_species.py to add "Lantana camara" to SPECIES_LIST
python3 process_alien_species.py --skip-download  # Skip download, use existing JSON

# 5. Move TIF
cd ..
cp output/Lantana_camara.tif tifs/

# 6. Regenerate index
python3 generate_tif_index.py

# 7. View
python3 -m http.server 8000
# Open http://localhost:8000/alienwise_viewer.html
```

## Directory Structure After Adding Species

```
alienwise/
├── data/
│   ├── Your_species_name_observations.json  # Raw observations
│   └── Your_species_name.csv                # Formatted CSV
├── output/
│   ├── res/
│   │   ├── Your_species_name.asc            # Maxent output
│   │   └── Your_species_name.html           # Maxent report
│   └── Your_species_name.tif                # Final TIF
├── tifs/
│   └── Your_species_name.tif                # Copy for viewer
└── tif_index.json                           # Updated index
```

## Next Steps

After adding your species:
- Verify it appears in the viewer
- Test with probability threshold slider
- Compare with other species distributions
- Check model quality in Maxent HTML report

For more details on the viewer, see the main [README.md](../README.md).

