#!/usr/bin/env python3
"""
Process alien species: download observations, format CSVs, run Maxent, convert to TIF.
All processing happens within alienwise/ directory.
"""
import os
import sys
import json
import csv
import subprocess
import argparse
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin

# Import download_observations module
# The script is in the same directory, so we can import it directly
import importlib.util
download_obs_path = Path(__file__).parent / 'download_observations.py'
spec = importlib.util.spec_from_file_location("download_observations", download_obs_path)
download_observations = importlib.util.module_from_spec(spec)
spec.loader.exec_module(download_observations)

# Species to process
SPECIES_LIST = [
    "Cestrum aurantiacum",
    "Lantana camara", 
    "Chromolaena odorata",
    "Senna spectabilis"
]

def sanitize_species_name(species_name):
    """Convert species name to filename-safe format."""
    return species_name.replace(' ', '_')

def download_observations_for_species(species_name, data_dir, start_date="2016-01-01", end_date="2024-12-31"):
    """Download observations for a species."""
    print(f"\n{'='*60}")
    print(f"Downloading observations for: {species_name}")
    print('='*60)
    
    sanitized = sanitize_species_name(species_name)
    output_path = os.path.join(data_dir, f"{sanitized}_observations.json")
    
    # Check if already downloaded
    if os.path.exists(output_path):
        print(f"  Observations file already exists: {output_path}")
        print(f"  Skipping download. Delete file to re-download.")
        return output_path
    
    # Set up arguments for download_observations
    sys.argv = [
        'download_observations.py',
        '--species', species_name,
        '--sources', 'inaturalist,gbif',
        '--output_format', 'json',
        '--output_path', output_path,
        '--start_date', start_date,
        '--end_date', end_date
    ]
    
    try:
        download_observations.main()
        if os.path.exists(output_path):
            print(f"  ✓ Downloaded to: {output_path}")
            return output_path
        else:
            print(f"  ✗ Download failed - file not created")
            return None
    except Exception as e:
        print(f"  ✗ Error during download: {e}")
        return None

def transform_observations_to_csv(json_path, csv_path, species_name):
    """Transform JSON observations to CSV format: Species,Latitude,Longitude"""
    print(f"\nTransforming {json_path} to CSV format...")
    
    if not os.path.exists(json_path):
        print(f"  ✗ JSON file not found: {json_path}")
        return False
    
    try:
        with open(json_path, 'r') as f:
            observations = json.load(f)
        
        if not observations:
            print(f"  ✗ No observations found in {json_path}")
            return False
        
        # Filter valid observations with lat/lon
        valid_obs = []
        for obs in observations:
            lat = obs.get('latitude')
            lon = obs.get('longitude')
            if lat is not None and lon is not None:
                try:
                    lat_f = float(lat)
                    lon_f = float(lon)
                    if -90 <= lat_f <= 90 and -180 <= lon_f <= 180:
                        valid_obs.append({
                            'Species': sanitize_species_name(species_name),
                            'Latitude': lat_f,
                            'Longitude': lon_f
                        })
                except (ValueError, TypeError):
                    continue
        
        if not valid_obs:
            print(f"  ✗ No valid observations with coordinates")
            return False
        
        # Write CSV
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['Species', 'Latitude', 'Longitude'])
            writer.writeheader()
            writer.writerows(valid_obs)
        
        print(f"  ✓ Created CSV with {len(valid_obs)} observations: {csv_path}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error transforming to CSV: {e}")
        return False

def run_maxent(species_csv, output_dir, res_dir, maxent_jar_path, env_layers_path):
    """Run Maxent for a species CSV file."""
    species_name = os.path.splitext(os.path.basename(species_csv))[0]
    print(f"\nRunning Maxent for {species_name}...")
    
    # Check if maxent.jar exists
    if not os.path.exists(maxent_jar_path):
        print(f"  ✗ maxent.jar not found at: {maxent_jar_path}")
        return None
    
    # Check if env layers directory exists
    if not os.path.exists(env_layers_path):
        print(f"  ✗ Environment layers not found at: {env_layers_path}")
        return None
    
    # Ensure output directories exist
    os.makedirs(res_dir, exist_ok=True)
    
    # Build Java command
    java_command = [
        "java", "-Djava.awt.headless=true", "-cp", maxent_jar_path, "density.MaxEnt",
        "nowarnings", "noprefixes", "jackknife",
        f"outputdirectory={res_dir}",
        f"samplesfile={species_csv}",
        f"environmentallayers={env_layers_path}",
        "autoRun", "visible=False"
    ]
    
    print(f"  Command: {' '.join(java_command)}")
    
    try:
        result = subprocess.run(
            java_command,
            check=True,
            text=True,
            capture_output=True,
            cwd=os.path.dirname(species_csv)  # Run from data directory
        )
        
        # Check for output ASC file
        asc_file = os.path.join(res_dir, f"{species_name}.asc")
        if os.path.exists(asc_file):
            print(f"  ✓ Maxent completed. Output: {asc_file}")
            return asc_file
        else:
            print(f"  ✗ Maxent completed but ASC file not found: {asc_file}")
            if result.stdout:
                print(f"  Stdout: {result.stdout[:500]}")
            if result.stderr:
                print(f"  Stderr: {result.stderr[:500]}")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Maxent failed with return code {e.returncode}")
        if e.stdout:
            print(f"  Stdout: {e.stdout[:500]}")
        if e.stderr:
            print(f"  Stderr: {e.stderr[:500]}")
        return None

def convert_asc_to_tiff(asc_file, tif_file):
    """Convert Maxent ASC output to GeoTIFF."""
    print(f"\nConverting {asc_file} to {tif_file}...")
    
    if not os.path.exists(asc_file):
        print(f"  ✗ ASC file not found: {asc_file}")
        return False
    
    try:
        # Read ASC file
        with open(asc_file, 'r') as f:
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
            
            # Read data
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
            tif_file, 'w',
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
        
        print(f"  ✓ Created TIF: {tif_file}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error converting ASC to TIF: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description="Process alien species through complete pipeline")
    parser.add_argument('--skip-download', action='store_true', help='Skip downloading observations (use existing JSON files)')
    parser.add_argument('--skip-maxent', action='store_true', help='Skip Maxent runs (use existing ASC files)')
    parser.add_argument('--skip-convert', action='store_true', help='Skip ASC to TIF conversion')
    parser.add_argument('--maxent-jar', default='../../../maxent.jar', help='Path to maxent.jar (relative to script location)')
    parser.add_argument('--env-layers', default='../../../final_attributes', help='Path to environment layers (relative to script location)')
    
    args = parser.parse_args()
    
    # Get paths
    script_dir = Path(__file__).parent
    alienwise_dir = script_dir.parent
    data_dir = alienwise_dir / 'data'
    output_dir = alienwise_dir / 'output'
    res_dir = output_dir / 'res'
    
    # Resolve relative paths from script directory
    # Go up from scripts/ -> alienwise/ -> PlantWise/ -> maxent.jar
    maxent_jar_path = (script_dir.parent.parent / 'maxent.jar').resolve()
    env_layers_path = (script_dir.parent.parent / 'final_attributes').resolve()
    
    # Override with command line args if provided
    if args.maxent_jar != parser.get_default('maxent_jar'):
        maxent_jar_path = (script_dir / args.maxent_jar).resolve()
    if args.env_layers != parser.get_default('env_layers'):
        env_layers_path = (script_dir / args.env_layers).resolve()
    
    print(f"\n{'='*60}")
    print("Alien Species Processing Pipeline")
    print('='*60)
    print(f"Data directory: {data_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Maxent JAR: {maxent_jar_path}")
    print(f"Environment layers: {env_layers_path}")
    print('='*60)
    
    # Ensure directories exist
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(res_dir, exist_ok=True)
    
    # Process each species
    for species_name in SPECIES_LIST:
        print(f"\n\n{'#'*60}")
        print(f"Processing: {species_name}")
        print('#'*60)
        
        sanitized = sanitize_species_name(species_name)
        json_path = data_dir / f"{sanitized}_observations.json"
        csv_path = data_dir / f"{sanitized}.csv"
        asc_path = res_dir / f"{sanitized}.asc"
        tif_path = output_dir / f"{sanitized}.tif"
        
        # Step 1: Download observations
        if not args.skip_download:
            json_path_result = download_observations_for_species(species_name, str(data_dir))
            if json_path_result:
                json_path = Path(json_path_result)
        else:
            print(f"\nSkipping download (using existing: {json_path})")
        
        # Step 2: Transform to CSV
        if not csv_path.exists() or not args.skip_download:
            success = transform_observations_to_csv(str(json_path), str(csv_path), species_name)
            if not success:
                print(f"  ✗ Failed to create CSV for {species_name}. Skipping.")
                continue
        else:
            print(f"\nCSV already exists: {csv_path}")
        
        # Check if CSV has enough points
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            point_count = sum(1 for _ in reader)
        
        if point_count <= 2:
            print(f"  ⚠ Only {point_count} points found. Maxent requires >2 points. Skipping.")
            continue
        
        # Step 3: Run Maxent
        if not args.skip_maxent:
            asc_result = run_maxent(
                str(csv_path),
                str(output_dir),
                str(res_dir),
                str(maxent_jar_path),
                str(env_layers_path)
            )
            if asc_result:
                asc_path = Path(asc_result)
        else:
            print(f"\nSkipping Maxent (using existing: {asc_path})")
        
        # Step 4: Convert ASC to TIF
        if not args.skip_convert and asc_path.exists():
            convert_asc_to_tiff(str(asc_path), str(tif_path))
        elif args.skip_convert:
            print(f"\nSkipping conversion")
        elif not asc_path.exists():
            print(f"\n  ✗ ASC file not found, cannot convert to TIF")
    
    print(f"\n\n{'='*60}")
    print("Processing complete!")
    print('='*60)
    print(f"\nNext steps:")
    print(f"1. Check TIF files in: {output_dir}")
    print(f"2. Move TIFs to: {alienwise_dir / 'tifs'}")
    print(f"3. Regenerate index: python3 ../../generate_tif_index.py")
    print(f"4. View in: alienwise_viewer.html")

if __name__ == "__main__":
    main()

