# Alien Species Processing Scripts

## Overview

Scripts to process alien species through the complete pipeline: download observations, format CSVs, run Maxent models, and generate TIF files.

## Setup

### Prerequisites

1. **Python virtual environment** with required packages:
   ```bash
   cd /path/to/PlantWise
   source venv/bin/activate
   pip install pygbif pyinaturalist pandas numpy rasterio
   ```

2. **Maxent JAR file** at `../../maxent.jar` (relative to alienwise/)

3. **Environment layers** at `../../final_attributes/` (relative to alienwise/)

## Usage

### Run Complete Pipeline

```bash
cd /path/to/PlantWise
source venv/bin/activate
cd alienwise/scripts
python3 process_alien_species.py
```

This will:
1. Download observations from GBIF and iNaturalist for all 4 species
2. Transform JSON observations to CSV format (Species,Latitude,Longitude)
3. Run Maxent models for each species
4. Convert Maxent ASC output to GeoTIFF files

### Skip Steps

If you've already completed some steps:

```bash
# Skip download (use existing JSON files)
python3 process_alien_species.py --skip-download

# Skip Maxent (use existing ASC files)
python3 process_alien_species.py --skip-maxent

# Skip conversion (use existing TIFs)
python3 process_alien_species.py --skip-convert

# Combine flags
python3 process_alien_species.py --skip-download --skip-maxent
```

### Custom Paths

```bash
# Custom maxent.jar location
python3 process_alien_species.py --maxent-jar /path/to/maxent.jar

# Custom environment layers location
python3 process_alien_species.py --env-layers /path/to/final_attributes
```

## Species Processed

1. Cestrum aurantiacum
2. Lantana camara
3. Chromolaena odorata
4. Senna spectabilis

## Output Structure

```
alienwise/
├── data/
│   ├── Cestrum_aurantiacum_observations.json  # Raw downloads
│   ├── Lantana_camara_observations.json
│   ├── Chromolaena_odorata_observations.json
│   ├── Senna_spectabilis_observations.json
│   ├── Cestrum_aurantiacum.csv                # Formatted CSVs
│   ├── Lantana_camara.csv
│   ├── Chromolaena_odorata.csv
│   └── Senna_spectabilis.csv
└── output/
    ├── res/                                    # Temporary Maxent files
    │   ├── *.asc
    │   └── *.html
    ├── Cestrum_aurantiacum.tif                 # Final TIFs
    ├── Lantana_camara.tif
    ├── Chromolaena_odorata.tif
    └── Senna_spectabilis.tif
```

## After Processing

1. **Move TIFs to viewer directory**:
   ```bash
   cd alienwise
   cp output/*.tif tifs/
   ```

2. **Regenerate index**:
   ```bash
   cd /path/to/PlantWise
   python3 generate_tif_index.py
   ```

3. **View in browser**:
   ```bash
   cd alienwise
   python3 -m http.server 8000
   # Open http://localhost:8000/alienwise_viewer.html
   ```

## Monitoring Progress

Check the log file:
```bash
tail -f /tmp/alien_processing_full.log
```

Or check output files:
```bash
# Check downloaded observations
ls -lh alienwise/data/*.json

# Check CSV files
ls -lh alienwise/data/*.csv
wc -l alienwise/data/*.csv  # Count observations

# Check Maxent output
ls -lh alienwise/output/res/*.asc

# Check final TIFs
ls -lh alienwise/output/*.tif
```

## Troubleshooting

### No observations downloaded

- Check internet connection
- Verify API keys/rate limits for GBIF/iNaturalist
- Check species names are correct
- Verify AOI bounds are correct

### Maxent fails

- Ensure maxent.jar exists and is accessible
- Check Java is installed: `java -version`
- Verify environment layers directory exists
- Check CSV has >2 observations
- Review Maxent output in `output/res/*.html`

### ASC to TIF conversion fails

- Ensure rasterio is installed
- Check ASC file exists and is valid
- Verify disk space available

## Notes

- Downloads may take 10-30 minutes depending on API response times
- Maxent runs may take 5-15 minutes per species
- All processing happens within `alienwise/` directory for portability
- Script automatically skips steps if output files already exist

