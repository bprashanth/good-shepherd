#!/usr/bin/env python3
"""
Generate a JSON index of all TIF files in the tifs/ directory.
This helps the HTML viewer quickly discover available TIF files.
Run this script from the alienwise/ directory.
"""
import json
import os
from pathlib import Path

def generate_index():
    """Generate index.json with list of TIF files."""
    # Use current working directory
    cwd = Path.cwd()
    tifs_dir = cwd / "tifs"
    
    if not tifs_dir.exists():
        print(f"Error: tifs/ directory does not exist in {cwd}")
        print(f"Please run this script from the alienwise/ directory")
        return
    
    tif_files = []
    for tif_file in sorted(tifs_dir.glob("*.tif")):
        # Store relative path from alienwise directory
        tif_files.append({
            "name": tif_file.stem,
            "path": f"tifs/{tif_file.name}"
        })
    
    index_path = cwd / "tif_index.json"
    with open(index_path, 'w') as f:
        json.dump({"files": tif_files}, f, indent=2)
    
    print(f"Generated index with {len(tif_files)} TIF files")
    print(f"Saved to: {index_path}")

if __name__ == "__main__":
    generate_index()

