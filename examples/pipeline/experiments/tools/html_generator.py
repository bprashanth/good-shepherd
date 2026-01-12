"""HTML template generator for experiment verification interface."""
import json
from pathlib import Path
import folium
from .config import get_experiment_dir
from .kml_parser import kml_to_geojson


def get_bounds_from_geojson(geojson_data):
    """Calculate map center from GeoJSON data."""
    coords = []
    for feature in geojson_data.get('features', []):
        geom = feature.get('geometry', {})
        if geom.get('type') == 'Point':
            coords.append(geom['coordinates'][:2])
        elif geom.get('type') == 'LineString':
            coords.extend([c[:2] for c in geom['coordinates']])
        elif geom.get('type') == 'Polygon':
            for ring in geom['coordinates']:
                coords.extend([c[:2] for c in ring])

    if coords:
        lats = [c[1] for c in coords]
        lons = [c[0] for c in coords]
        center_lat = (min(lats) + max(lats)) / 2
        center_lon = (min(lons) + max(lons)) / 2
        return center_lat, center_lon
    return 11.48, 76.79  # Default center (Bikkapathy Mund area)


def generate_verification_html(experiment_id):
    """
    Generate verification HTML interface for experiment.

    Args:
        experiment_id: Experiment ID

    Returns:
        Path to generated HTML file
    """
    experiment_dir = get_experiment_dir(experiment_id)

    # Load all JSON files
    features_file = experiment_dir / "features" / "features.json"
    variables_file = experiment_dir / "variables" / "variables.json"
    indicators_file = experiment_dir / "indicators" / "indicators.json"
    mismatches_file = experiment_dir / "analysis" / "mismatches.json"
    experiment_file = experiment_dir / "experiment.json"

    # Load data
    with open(experiment_file, 'r') as f:
        experiment_data = json.load(f)

    features_data = {}
    if features_file.exists():
        with open(features_file, 'r') as f:
            features_data = json.load(f)

    variables_data = {}
    if variables_file.exists():
        with open(variables_file, 'r') as f:
            variables_data = json.load(f)

    indicators_data = {}
    if indicators_file.exists():
        with open(indicators_file, 'r') as f:
            indicators_data = json.load(f)

    mismatches_data = {}
    if mismatches_file.exists():
        with open(mismatches_file, 'r') as f:
            mismatches_data = json.load(f)

    # Get map files for bounds
    map_files = experiment_data.get("map_files", [])
    kml_path = None
    if map_files:
        kml_path = experiment_dir / map_files[0]

    # Generate GeoJSON if needed
    geojson_path = experiment_dir / "maps" / "sites.geojson"
    if kml_path and kml_path.exists() and not geojson_path.exists():
        kml_to_geojson(kml_path, geojson_path)

    # Get bounds
    if geojson_path.exists():
        with open(geojson_path, 'r') as f:
            geojson_data = json.load(f)
        center_lat, center_lon = get_bounds_from_geojson(geojson_data)
    else:
        center_lat, center_lon = 11.48, 76.79

    # Group features by type
    features_by_type = {}
    if features_data.get("features"):
        for feature in features_data["features"]:
            feat_type = feature.get("type", "unknown")
            if feat_type not in features_by_type:
                features_by_type[feat_type] = []
            features_by_type[feat_type].append(feature)
    elif features_data.get("feature_mappings"):
        # Handle case where features are in feature_mappings format
        for mapping in features_data["feature_mappings"]:
            feat_type = mapping.get("feature_type", "unknown")
            if feat_type not in features_by_type:
                features_by_type[feat_type] = []
            features_by_type[feat_type].append({
                "name": mapping.get("kml_feature_name", "Unknown"),
                "type": feat_type,
                "geometry_type": "unknown",
                "coordinates": []
            })

    # Group variables by feature type
    variables_by_type = {}
    if variables_data.get("variables"):
        for var in variables_data["variables"]:
            var_type = var.get("feature_type", "unknown")
            if var_type not in variables_by_type:
                variables_by_type[var_type] = []
            variables_by_type[var_type].append(var)

    # Group indicators by feature type
    indicators_by_type = {}
    if indicators_data.get("indicators"):
        for ind in indicators_data["indicators"]:
            ind_type = ind.get("feature_type", "unknown")
            if ind_type not in indicators_by_type:
                indicators_by_type[ind_type] = []
            indicators_by_type[ind_type].append(ind)

    # Generate HTML sections
    sections_html = ""

    # Mismatches section (at top)
    if mismatches_data.get("mismatches"):
        mismatches_html = generate_mismatches_section(
            mismatches_data["mismatches"])
        sections_html += mismatches_html

    # Feature type sections
    for feat_type in sorted(features_by_type.keys()):
        section_html = generate_feature_type_section(
            feat_type,
            features_by_type[feat_type],
            variables_by_type.get(feat_type, []),
            indicators_by_type.get(feat_type, []),
            center_lat,
            center_lon
        )
        sections_html += section_html

    # Generate full HTML
    full_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Experiment Verification - {experiment_data.get('name', experiment_id)}</title>
    <meta charset="utf-8">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .mismatches-section {{
            margin-bottom: 40px;
            padding: 20px;
            border: 2px solid #e74c3c;
            border-radius: 8px;
            background: #fee;
        }}
        .mismatches-section h2 {{
            color: #c0392b;
            margin-top: 0;
        }}
        .mismatch-item {{
            padding: 10px;
            margin: 10px 0;
            border-left: 4px solid #e74c3c;
            background: white;
        }}
        .mismatch-item.error {{ border-left-color: #e74c3c; }}
        .mismatch-item.warning {{ border-left-color: #f39c12; }}
        .mismatch-item.info {{ border-left-color: #3498db; }}
        .feature-section {{
            margin-bottom: 40px;
            padding: 20px;
            border: 2px solid #ddd;
            border-radius: 8px;
            background: #fafafa;
        }}
        .feature-section h2 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        .section-content {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }}
        .map-wrapper {{
            min-height: 500px;
        }}
        .variables-panel, .indicators-panel {{
            background: white;
            padding: 20px;
            border-radius: 4px;
            border: 1px solid #ddd;
        }}
        .variables-panel h3, .indicators-panel h3 {{
            color: #27ae60;
            margin-top: 0;
        }}
        .variable-item, .indicator-item {{
            padding: 10px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: #f9f9f9;
        }}
        .add-button {{
            background: #3498db;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            margin: 10px 0;
        }}
        .add-button:hover {{
            background: #2980b9;
        }}
        .file-input-container {{
            margin: 10px 0;
        }}
        .indicator-input {{
            width: 100%;
            min-height: 60px;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin: 10px 0;
        }}
        @media (max-width: 1400px) {{
            .section-content {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Experiment Verification: {experiment_data.get('name', experiment_id)}</h1>
        <p>{experiment_data.get('description', '')}</p>
        {sections_html}
    </div>
    <script>
        let datasheetCounters = {{}};
        let indicatorCounters = {{}};
        
        function addDatasheet(featureType) {{
            const container = document.getElementById(`datasheets-${{featureType}}`);
            const counter = datasheetCounters[featureType] || 0;
            datasheetCounters[featureType] = counter + 1;
            
            const div = document.createElement('div');
            div.className = 'file-input-container';
            div.innerHTML = `
                <input type="file" accept="image/*" id="datasheet-${{featureType}}-${{counter}}" />
                <button onclick="this.parentElement.remove()">Remove</button>
            `;
            container.appendChild(div);
        }}
        
        function addIndicator(featureType) {{
            const container = document.getElementById(`indicators-${{featureType}}`);
            const counter = indicatorCounters[featureType] || 0;
            indicatorCounters[featureType] = counter + 1;
            
            const div = document.createElement('div');
            div.className = 'indicator-input-container';
            div.innerHTML = `
                <textarea class="indicator-input" placeholder="Enter indicator description in English..." id="indicator-${{featureType}}-${{counter}}"></textarea>
                <button onclick="this.parentElement.remove()">Remove</button>
            `;
            container.appendChild(div);
        }}
    </script>
</body>
</html>
"""

    # Save HTML
    output_path = experiment_dir / "verification.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_html)

    return output_path


def generate_mismatches_section(mismatches):
    """Generate HTML for mismatches section."""
    items_html = ""
    for mismatch in mismatches:
        severity = mismatch.get("severity", "info")
        items_html += f"""
        <div class="mismatch-item {severity}">
            <strong>{mismatch.get('type', 'Unknown')}</strong> ({severity})
            <p>{mismatch.get('message', '')}</p>
            <p><em>Recommendation:</em> {mismatch.get('recommendation', '')}</p>
        </div>
        """

    return f"""
    <section class="mismatches-section">
        <h2>⚠️ Mismatches and Issues</h2>
        {items_html}
    </section>
    """


def generate_feature_type_section(feat_type, features, variables, indicators, center_lat, center_lon):
    """Generate HTML section for a feature type."""
    # Create map
    feat_map = folium.Map(
        location=[center_lat, center_lon], zoom_start=15, tiles='OpenStreetMap')

    # Add features to map
    for feature in features:
        # Features can have geometry directly or coordinates
        coords = feature.get("coordinates")
        if not coords:
            geom = feature.get("geometry")
            if geom:
                coords = geom.get("coordinates")

        if not coords:
            continue

        name = feature.get("name", "Unnamed")
        geom_type = feature.get("geometry_type")
        if not geom_type:
            geom = feature.get("geometry")
            if geom:
                geom_type = geom.get("type")

        if not geom_type:
            # Infer from coordinates structure
            if isinstance(coords[0], (int, float)):
                geom_type = "Point"
            elif isinstance(coords[0], list) and isinstance(coords[0][0], (int, float)):
                geom_type = "LineString"
            elif isinstance(coords[0], list) and isinstance(coords[0][0], list):
                geom_type = "Polygon"

        if geom_type == "Point":
            folium.Marker(
                [coords[1], coords[0]],
                popup=name,
                tooltip=name
            ).add_to(feat_map)
        elif geom_type == "LineString":
            folium.PolyLine(
                [[c[1], c[0]] for c in coords],
                popup=name,
                tooltip=name,
                color='blue',
                weight=3
            ).add_to(feat_map)
        elif geom_type == "Polygon":
            if len(coords) > 0:
                # Handle both [coords] and coords formats
                polygon_coords = coords[0] if isinstance(
                    coords[0], list) and isinstance(coords[0][0], list) else coords
                folium.Polygon(
                    [[c[1], c[0]] for c in polygon_coords],
                    popup=name,
                    tooltip=name,
                    color='green',
                    fillColor='green',
                    fillOpacity=0.4
                ).add_to(feat_map)

    map_html = feat_map._repr_html_()

    # Variables HTML
    variables_html = ""
    for var in variables:
        variables_html += f"""
        <div class="variable-item">
            <strong>{var.get('name', 'Unknown')}</strong>
            <p>{var.get('description', '')}</p>
            <small>Type: {var.get('data_type', 'unknown')}, Unit: {var.get('unit', 'N/A')}</small>
        </div>
        """

    # Indicators HTML
    indicators_html = ""
    for ind in indicators:
        indicators_html += f"""
        <div class="indicator-item">
            <strong>{ind.get('name', 'Unknown')}</strong>
            <p>{ind.get('description_english', ind.get('description', ''))}</p>
            <small>{'Suggested' if ind.get('suggested') else 'From Protocol'}</small>
        </div>
        """

    return f"""
    <section class="feature-section" id="feature-{feat_type}">
        <h2>Feature Type: {feat_type.title()}</h2>
        <p>Found {len(features)} feature(s) of this type</p>
        <div class="section-content">
            <div class="map-wrapper">
                {map_html}
            </div>
            <div class="variables-panel">
                <h3>Variables ({len(variables)})</h3>
                {variables_html}
                <button class="add-button" onclick="addDatasheet('{feat_type}')">Add Datasheet</button>
                <div id="datasheets-{feat_type}"></div>
            </div>
            <div class="indicators-panel">
                <h3>Indicators ({len(indicators)})</h3>
                {indicators_html}
                <button class="add-button" onclick="addIndicator('{feat_type}')">Add Indicator</button>
                <div id="indicators-{feat_type}"></div>
            </div>
        </div>
    </section>
    """
