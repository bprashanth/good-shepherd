# Alienwise TIF Viewer

A self-contained web application for visualizing species distribution GeoTIFF files. The viewer provides an interactive map interface with autocomplete search, multi-layer visualization, and probability threshold filtering.

## Directory Structure

```
alienwise/
├── README.md                 # This file
├── alienwise_viewer.html     # Main application (single HTML file)
├── tif_index.json            # Index of all available TIF files
└── tifs/                     # Directory containing all GeoTIFF files
    ├── Species1_name.tif
    ├── Species2_name.tif
    └── ...
```

## Quick Start

1. **Start the HTTP server** (from the `alienwise/` directory):
   ```bash
   python3 -m http.server 8000
   ```

2. **Open in browser**:
   ```
   http://localhost:8000/alienwise_viewer.html
   ```

3. **Use the viewer**:
   - Type in the search box to find species (e.g., "m" for Magnolia)
   - Click on species from the autocomplete dropdown to select them
   - Click "Load Selected TIFs" to render them on the map
   - Adjust the probability threshold slider to filter low-probability areas
   - Each species appears in a different color for easy distinction

## Adding a New Species

For a complete guide on adding new species from scratch (downloading observations, training models, generating TIFs), see **[docs/adding_species.md](docs/adding_species.md)**.

### Quick: Adding an Existing TIF File

If you already have a TIF file:

1. **Place the TIF file** in the `tifs/` directory:
   ```bash
   cp /path/to/new_species.tif tifs/
   ```

2. **Regenerate the index**:
   ```bash
   python3 generate_tif_index.py
   ```

3. **Refresh the viewer** - your species should appear in the search

**File Naming Convention:**
- Use scientific names: `Genus_species.tif` (e.g., `Magnolia_nilagirica.tif`)
- Use underscores instead of spaces
- File extension must be `.tif` or `.tiff`

**TIF File Requirements:**
- Must be a valid GeoTIFF with geographic coordinate system (preferably WGS84/EPSG:4326)
- Should contain species distribution probability/suitability values (typically 0.0 to 1.0)
- NoData values should be set to -9999 or similar sentinel value
- Single-band raster data

## Design Overview

### Architecture

The viewer is a **single-file HTML application** with embedded CSS and JavaScript. It uses:

- **Leaflet.js** (CDN) - Interactive map rendering
- **GeoTIFF.js** (CDN) - Client-side GeoTIFF parsing
- **Plain JavaScript** - No build step or dependencies required

### Key Components

#### 1. TIF File Discovery

- Loads `tif_index.json` on page load
- JSON structure:
  ```json
  {
    "files": [
      {
        "name": "Species_name",
        "path": "tifs/Species_name.tif"
      }
    ]
  }
  ```

#### 2. Autocomplete Search

- Real-time filtering as user types
- Fuzzy matching (e.g., "m" matches "Magnolia")
- Keyboard navigation (arrow keys, Enter, Escape)
- Shows up to 10 matching results
- Highlights matching text in results

#### 3. Multi-Layer Visualization

- Each selected species gets a unique color from a predefined palette
- Colors are assigned sequentially (first = red, second = blue, etc.)
- Up to 20 distinct colors, then cycles
- Layers are rendered as semi-transparent overlays
- Overlapping areas blend colors (heatmap effect)

#### 4. Probability Threshold Filter

- Slider control (0.00 to 1.00)
- Filters out pixels below the threshold value
- Helps focus on high-suitability areas
- Updates visualization in real-time when adjusted

#### 5. Rendering Pipeline

```
TIF File → Fetch → Parse (GeoTIFF.js) → Extract Raster Data
    ↓
Filter NoData values (-9999)
    ↓
Normalize values (0-1 range)
    ↓
Apply probability threshold filter
    ↓
Convert to colored canvas (RGB + alpha)
    ↓
Create Leaflet ImageOverlay
    ↓
Add to map with auto-zoom to bounds
```

### Data Processing

**NoData Handling:**
- Values ≤ -1000 are treated as NoData
- NoData pixels are rendered as fully transparent
- Only valid data is included in min/max calculation for normalization

**Normalization:**
- Each TIF is normalized independently using its own min/max range
- Formula: `normalized = (value - min) / (max - min)`
- Normalized values (0-1) control opacity/alpha channel

**Color Mapping:**
- Base colors are darkened by 15% for better contrast
- Opacity ranges from 30% (low values) to 90% (high values)
- Formula: `alpha = 0.3 + (0.6 * normalized)`

### Color Palette

The viewer uses a predefined 20-color palette:

```javascript
['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6',
 '#1abc9c', '#e67e22', '#34495e', '#d35400', '#16a085',
 '#c0392b', '#2980b9', '#27ae60', '#d68910', '#8e44ad',
 '#138d75', '#ba4a00', '#2c3e50', '#a93226', '#2874a6']
```

Colors cycle if more than 20 species are selected.

## Technical Details

### File Format Requirements

**GeoTIFF Specifications:**
- Coordinate Reference System: WGS84 (EPSG:4326) recommended
- Data type: Float32 or similar
- NoData value: -9999 (or values ≤ -1000)
- Value range: Typically 0.0 to 1.0 (probability/suitability)
- Single band raster

### Browser Compatibility

- Modern browsers with ES6+ support
- Requires Canvas API support
- Requires Fetch API support
- Tested on: Chrome, Firefox, Safari, Edge

### Performance Considerations

- TIF files are loaded and parsed client-side
- Large files (>10MB) may take several seconds to load
- Multiple layers are loaded in parallel
- Canvas rendering happens in memory before display
- Consider file size when adding new TIFs (compress if needed)

### Limitations

1. **CORS**: Requires HTTP server (cannot use `file://` protocol)
2. **File Size**: Very large TIFs (>50MB) may cause browser slowdowns
3. **Memory**: Multiple large TIFs loaded simultaneously can consume significant memory
4. **Spatial Extent**: All TIFs should cover similar geographic regions for meaningful comparison

## Troubleshooting

### TIF file not appearing in search

1. Check file is in `tifs/` directory
2. Verify filename ends with `.tif` or `.tiff`
3. Regenerate index: `python3 generate_tif_index.py`
4. Check browser console for errors
5. Verify `tif_index.json` contains the file

### Map not showing TIFs

1. Check browser console for errors
2. Verify TIF file is valid GeoTIFF (try opening in QGIS/GDAL)
3. Check network tab - is file loading?
4. Verify NoData values are set correctly (-9999)
5. Try adjusting probability threshold slider

### Colors look the same

1. Use probability threshold slider to filter low values
2. Check browser console for value ranges (should differ between species)
3. Verify TIF files have different data values (not just same footprint)

### Performance issues

1. Reduce number of simultaneously loaded TIFs
2. Increase probability threshold to show fewer pixels
3. Check TIF file sizes (consider compression)
4. Use browser DevTools to identify bottlenecks

## Maintenance

### Regenerating the Index

If TIF files are added/removed/renamed:

```bash
cd alienwise
python3 generate_tif_index.py
```

The script automatically:
- Scans the `tifs/` directory in the current working directory
- Finds all `.tif` files
- Generates `tif_index.json` in the current directory
- Preserves file order (sorted alphabetically)

**Note:** Run this script from the `alienwise/` directory.

### Updating the Viewer

The viewer is self-contained in `alienwise_viewer.html`. To update:

1. Edit the HTML file directly
2. No build step required
3. Refresh browser to see changes
4. All CSS and JavaScript is embedded in the file

## Future Enhancements

Potential improvements:

- [ ] Export selected layers as combined image
- [ ] Layer visibility toggle (show/hide individual species)
- [ ] Legend showing color → species mapping
- [ ] Statistics panel (coverage area, mean probability, etc.)
- [ ] Comparison mode (side-by-side species view)
- [ ] Download individual TIF layers
- [ ] Custom color assignment per species
- [ ] Save/load selection presets

## License

Part of the PlantWise project.

