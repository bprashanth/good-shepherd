# Alien Species Pipeline 

## Current Status

### Step 1: Downloading Observations 

Downloading observations from GBIF and iNaturalist for:
- Cestrum aurantiacum
- Lantana camara (currently downloading - 1122+ records found)
- Chromolaena odorata
- Senna spectabilis

**Expected time:** 10-30 minutes depending on API response times

### Step 2: Transform to CSV Format 

Once downloads complete, observations will be transformed to CSV format:
- Format: `Species,Latitude,Longitude`
- Files saved to: `alienwise/data/*.csv`

### Step 3: Run Maxent Models 

For each species CSV with >2 observations:
- Run Maxent Java command
- Output to: `alienwise/output/res/*.asc`
- **Expected time:** 5-15 minutes per species

### Step 4: Convert to TIF 

Convert Maxent ASC files to GeoTIFF:
- Output to: `alienwise/output/*.tif`
- Ready for viewing in the viewer

## Monitor Progress

### Check Log File
```bash
tail -f /tmp/alien_processing_full.log
```

### Check Downloaded Files
```bash
# See what's been downloaded
ls -lh alienwise/data/*.json

# Check file sizes (growing = still downloading)
watch -n 5 'ls -lh alienwise/data/*.json'
```

### Check CSV Files Created
```bash
# Count observations per species
wc -l alienwise/data/*.csv
```

### Check Maxent Progress
```bash
# See ASC files being created
ls -lh alienwise/output/res/*.asc

# Check HTML reports
ls -lh alienwise/output/res/*.html
```

### Check Final TIFs
```bash
ls -lh alienwise/output/*.tif
```

## What to Expect

1. **Download Phase** (10-30 min)
   - JSON files appearing in `alienwise/data/`
   - Files growing in size as data downloads
   - Some species may have many observations (1000+), others may have few

2. **CSV Transformation** (1-2 min)
   - CSV files created in `alienwise/data/`
   - Each CSV should have >2 rows (header + observations)

3. **Maxent Processing** (20-60 min total)
   - One species at a time
   - ASC files appearing in `alienwise/output/res/`
   - HTML reports also created

4. **TIF Conversion** (1-2 min)
   - TIF files appearing in `alienwise/output/`

## After Processing Completes

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

## If Processing Fails

### Re-run from where it stopped:
```bash
cd /path/to/PlantWise
source venv/bin/activate
cd alienwise/scripts

# Skip steps that already completed
python3 process_alien_species.py --skip-download  # If downloads done
python3 process_alien_species.py --skip-maxent    # If Maxent done
```

### Check for errors:
```bash
# Review full log
cat /tmp/alien_processing_full.log | grep -i error

# Check individual species
grep "Processing:" /tmp/alien_processing_full.log
```

## Estimated Total Time

- **Download:** 10-30 minutes
- **CSV Transform:** 1-2 minutes  
- **Maxent (4 species):** 20-60 minutes
- **TIF Conversion:** 1-2 minutes
- **Total:** ~30-90 minutes

The process is designed to be resumable - if it stops, you can re-run with `--skip-*` flags to continue from where it left off.

