#!/usr/bin/env python3
"""
Script to visualize KML and GeoJSON files side by side for comparison.
This script requires the venv of the root folder to run. 
"""

import folium
from folium import plugins
import json
import os
import re
import math
from pathlib import Path
import time

# #region agent log
LOG_PATH = "/home/desinotorious/src/github.com/bprashanth/good-shepherd/.cursor/debug.log"


def log_debug(session_id, run_id, hypothesis_id, location, message, data=None):
    try:
        with open(LOG_PATH, 'a') as f:
            f.write(json.dumps({
                "sessionId": session_id,
                "runId": run_id,
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data or {},
                "timestamp": int(time.time() * 1000)
            }) + "\n")
    except:
        pass
# #endregion


def load_geojson(file_path):
    """Load and return GeoJSON data."""
    with open(file_path, 'r') as f:
        return json.load(f)


def get_bounds_from_geojson(geojson_path):
    """Calculate map bounds from GeoJSON file."""
    geojson_data = load_geojson(geojson_path)
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
    return 11.48, 76.79


def create_map_with_kml(kml_path, geojson_path_for_bounds, title="KML Visualization"):
    """Create a folium map with KML overlay."""
    # #region agent log
    log_debug("debug-session", "run1", "A,B", "visualize_sites.py:43", "create_map_with_kml entry",
              {"kml_path": str(kml_path), "kml_path_exists": os.path.exists(kml_path), "kml_path_abs": os.path.abspath(kml_path)})
    # #endregion
    center_lat, center_lon = get_bounds_from_geojson(geojson_path_for_bounds)

    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=15,
        tiles='OpenStreetMap'
    )

    # Convert KML to GeoJSON and add to map
    # #region agent log
    log_debug("debug-session", "run1", "A,C", "visualize_sites.py:79",
              "Converting KML to GeoJSON", {"kml_path": str(kml_path)})
    # #endregion

    try:
        # Read and parse KML file
        import xml.etree.ElementTree as ET

        with open(kml_path, 'r', encoding='utf-8') as f:
            kml_content = f.read()

        # Parse KML XML
        root = ET.fromstring(kml_content)

        # Convert KML to GeoJSON format
        # This is a simplified converter - handles basic geometries
        features = []

        # Define KML namespaces (KML files can have different namespace declarations)
        # Try to detect namespace from root element
        ns = ''
        if root.tag.startswith('{'):
            ns = root.tag.split('}')[0] + '}'

        # Helper function to find elements with or without namespace
        def find_with_ns(elem, path):
            # Try with namespace first
            if ns:
                result = elem.findall(f'.//{ns}{path}')
                if result:
                    return result
            # Try without namespace
            return elem.findall(f'.//{path}') or elem.findall(f'.//{{{ns}}}{path}')

        def find_one_with_ns(elem, path):
            if ns:
                result = elem.find(f'.//{ns}{path}')
                if result is not None:
                    return result
            return elem.find(f'.//{path}') or elem.find(f'.//{{{ns}}}{path}')

        # Find all Placemark elements (KML features)
        placemarks = find_with_ns(root, 'Placemark')

        # #region agent log
        log_debug("debug-session", "run1", "A", "visualize_sites.py:98",
                  "KML parsed", {"placemarks_count": len(placemarks)})
        # #endregion

        for pm in placemarks:
            feature = {"type": "Feature", "properties": {}, "geometry": None}

            # Extract name and description
            name_elem = find_one_with_ns(pm, 'name')
            if name_elem is not None and name_elem.text:
                feature["properties"]["name"] = name_elem.text.strip()

            # Extract geometry
            for geom_type in ['Point', 'LineString', 'Polygon', 'MultiGeometry']:
                geom_elem = find_one_with_ns(pm, geom_type)
                if geom_elem is not None:
                    if geom_type == 'Point':
                        coord_elem = find_one_with_ns(geom_elem, 'coordinates')
                        if coord_elem is not None and coord_elem.text:
                            coord_str = coord_elem.text.strip()
                            # KML coordinates are space-separated, format: lon,lat,alt
                            coords_list = coord_str.split()
                            if coords_list:
                                # Take first coordinate
                                parts = coords_list[0].split(',')
                                if len(parts) >= 2:
                                    try:
                                        feature["geometry"] = {
                                            "type": "Point",
                                            "coordinates": [float(parts[0]), float(parts[1])]
                                        }
                                    except ValueError:
                                        pass
                    elif geom_type == 'LineString':
                        coord_elem = find_one_with_ns(geom_elem, 'coordinates')
                        if coord_elem is not None and coord_elem.text:
                            coord_str = coord_elem.text.strip()
                            coord_strs = coord_str.split()
                            coords = []
                            for cs in coord_strs:
                                parts = cs.split(',')
                                if len(parts) >= 2:
                                    try:
                                        coords.append(
                                            [float(parts[0]), float(parts[1])])
                                    except ValueError:
                                        continue
                            if coords:
                                feature["geometry"] = {
                                    "type": "LineString",
                                    "coordinates": coords
                                }
                    elif geom_type == 'Polygon':
                        outer_elem = find_one_with_ns(
                            geom_elem, 'outerBoundaryIs')
                        if outer_elem is not None:
                            linear_ring = find_one_with_ns(
                                outer_elem, 'LinearRing')
                            if linear_ring is not None:
                                coord_elem = find_one_with_ns(
                                    linear_ring, 'coordinates')
                                if coord_elem is not None and coord_elem.text:
                                    coord_str = coord_elem.text.strip()
                                    coord_strs = coord_str.split()
                                    coords = []
                                    for cs in coord_strs:
                                        parts = cs.split(',')
                                        if len(parts) >= 2:
                                            try:
                                                coords.append(
                                                    [float(parts[0]), float(parts[1])])
                                            except ValueError:
                                                continue
                                    if coords:
                                        feature["geometry"] = {
                                            "type": "Polygon",
                                            "coordinates": [coords]
                                        }
                    break

            if feature["geometry"] is not None:
                features.append(feature)

        # Create GeoJSON from features
        geojson_data = {"type": "FeatureCollection", "features": features}

        # #region agent log
        log_debug("debug-session", "run1", "A", "visualize_sites.py:150",
                  "KML converted to GeoJSON", {"features_count": len(features)})
        # #endregion

        # Add GeoJSON to map with styling and labels
        if features:
            folium.GeoJson(
                geojson_data,
                name=title,
                style_function=lambda feature: {
                    'color': 'blue' if feature['geometry']['type'] == 'LineString' else
                    'red' if feature['geometry']['type'] == 'Point' else
                    'green',
                    'weight': 2 if feature['geometry']['type'] == 'LineString' else 1,
                    'fillOpacity': 0.3 if feature['geometry']['type'] == 'Polygon' else 0,
                    'fillColor': 'green' if feature['geometry']['type'] == 'Polygon' else 'transparent'
                }
            ).add_to(m)

            # Group labels by location to avoid overlaps
            # Dictionary: (lat, lon) -> list of names
            # Filter: Only show labels for LineString features by default
            # (This reduces clutter from Point markers that overlap with transect lines)
            label_groups = {}

            for feature in features:
                name = feature.get('properties', {}).get('name', '')
                if not name:
                    continue

                geom = feature.get('geometry', {})
                geom_type = geom.get('type', '')

                # Filter: Only show labels for LineString features
                # This works for both KML (after conversion) and GeoJSON
                # KML Point markers (like T2) will be hidden
                # KML LineString transects (like A_T1, A_T2) will be shown
                if geom_type != 'LineString':
                    continue

                coords = geom.get('coordinates', [])
                label_location = None

                if geom_type == 'LineString' and len(coords) > 0:
                    mid_idx = len(coords) // 2
                    mid_coord = coords[mid_idx]
                    label_location = (
                        round(mid_coord[1], 6), round(mid_coord[0], 6))

                if label_location:
                    if label_location not in label_groups:
                        label_groups[label_location] = []
                    label_groups[label_location].append((name, feature))

            # Add labels with smart spacing to avoid overlaps
            # For multiple labels at same location, distribute them in a pattern

            for (lat, lon), name_features in label_groups.items():
                names = [nf[0] for nf in name_features]

                if len(names) == 1:
                    # Single label - place at exact location
                    label_text = names[0]
                    offset_lat = lat
                    offset_lon = lon

                    folium.Marker(
                        location=[offset_lat, offset_lon],
                        popup=folium.Popup(label_text, max_width=200),
                        tooltip=label_text,
                        icon=folium.DivIcon(
                            html=f'<div style="font-size: 11px; font-weight: bold; color: black; text-shadow: -1px -1px 0 white, 1px -1px 0 white, -1px 1px 0 white, 1px 1px 0 white; background: rgba(255,255,255,0.85); padding: 2px 4px; border-radius: 3px; border: 1px solid rgba(0,0,0,0.3);">{label_text}</div>',
                            icon_size=(len(label_text) * 7, 18),
                            icon_anchor=(len(label_text) * 3.5, 9)
                        )
                    ).add_to(m)
                else:
                    # Multiple labels - distribute in a circular pattern
                    # Calculate spacing based on number of labels
                    num_labels = len(names)
                    # Spacing radius in degrees (approximately 10-20 meters at this latitude)
                    spacing_radius = 0.0002  # ~20 meters

                    # Distribute labels in a circle or grid pattern
                    if num_labels <= 4:
                        # For 2-4 labels, use cardinal/intercardinal directions
                        positions = [
                            (0, spacing_radius),      # North
                            (spacing_radius, 0),      # East
                            (0, -spacing_radius),     # South
                            (-spacing_radius, 0),     # West
                        ]
                    else:
                        # For more labels, distribute in a circle
                        angle_step = 2 * math.pi / num_labels
                        positions = []
                        for i in range(num_labels):
                            angle = i * angle_step
                            offset_lat_delta = spacing_radius * math.cos(angle)
                            offset_lon_delta = spacing_radius * \
                                math.sin(angle) / math.cos(math.radians(lat))
                            positions.append(
                                (offset_lon_delta, offset_lat_delta))

                    # Place each label at its offset position
                    for i, name in enumerate(names):
                        offset_lon_delta, offset_lat_delta = positions[i % len(
                            positions)]
                        offset_lat = lat + offset_lat_delta
                        offset_lon = lon + offset_lon_delta

                        folium.Marker(
                            location=[offset_lat, offset_lon],
                            popup=folium.Popup(name, max_width=200),
                            tooltip=name,
                            icon=folium.DivIcon(
                                html=f'<div style="font-size: 11px; font-weight: bold; color: black; text-shadow: -1px -1px 0 white, 1px -1px 0 white, -1px 1px 0 white, 1px 1px 0 white; background: rgba(255,255,255,0.85); padding: 2px 4px; border-radius: 3px; border: 1px solid rgba(0,0,0,0.3);">{name}</div>',
                                icon_size=(len(name) * 7, 18),
                                icon_anchor=(len(name) * 3.5, 9)
                            )
                        ).add_to(m)

            # #region agent log
            log_debug("debug-session", "run1", "A", "visualize_sites.py:280",
                      "GeoJSON layer with labels added to map", {
                          "map_children": list(m._children.keys()),
                          "features_with_names": sum(1 for f in features if f.get('properties', {}).get('name'))
                      })
            # #endregion
        else:
            # #region agent log
            log_debug("debug-session", "run1", "A",
                      "visualize_sites.py:166", "No features found in KML", {})
            # #endregion
            print("Warning: No features found in KML file")

    except Exception as e:
        # #region agent log
        log_debug("debug-session", "run1", "A", "visualize_sites.py:170", "KML conversion exception",
                  {"error_type": str(type(e).__name__), "error_message": str(e)})
        # #endregion
        print(f"Error converting KML to GeoJSON: {e}")
        import traceback
        traceback.print_exc()

    # #region agent log
    log_debug("debug-session", "run1", "A", "visualize_sites.py:177",
              "After KML conversion attempt", {"map_children": list(m._children.keys())})
    # #endregion

    # Add layer control
    folium.LayerControl().add_to(m)

    # #region agent log
    log_debug("debug-session", "run1", "A", "visualize_sites.py:83",
              "create_map_with_kml exit", {"final_map_children": list(m._children.keys())})
    # #endregion
    return m


def match_features_by_geometry(kml_features_geojson, geojson_features, tolerance=0.0001):
    """Match KML features to GeoJSON features by comparing geometry coordinates.
    Returns a dictionary mapping GeoJSON feature index to KML feature name.
    Both inputs should be GeoJSON-like feature dictionaries."""
    matches = {}

    def get_first_coord(feature):
        """Extract first coordinate from a feature for matching."""
        geom = feature.get('geometry', {})
        geom_type = geom.get('type', '')
        coords = geom.get('coordinates', [])

        if geom_type == 'Point' and len(coords) >= 2:
            return (round(coords[1], 6), round(coords[0], 6))
        elif geom_type == 'LineString' and len(coords) > 0:
            # Return first point
            return (round(coords[0][1], 6), round(coords[0][0], 6))
        elif geom_type == 'Polygon' and len(coords) > 0 and len(coords[0]) > 0:
            # Return first point
            return (round(coords[0][0][1], 6), round(coords[0][0][0], 6))
        return None

    # Match features by first coordinate
    for i, geojson_feat in enumerate(geojson_features):
        geojson_coord = get_first_coord(geojson_feat)
        if geojson_coord is None:
            continue

        for kml_feat in kml_features_geojson:
            kml_name = kml_feat.get('properties', {}).get('name', '')
            if not kml_name:
                continue

            kml_coord = get_first_coord(kml_feat)
            if kml_coord:
                # Check if coordinates match within tolerance
                if abs(kml_coord[0] - geojson_coord[0]) <= tolerance and \
                   abs(kml_coord[1] - geojson_coord[1]) <= tolerance:
                    matches[i] = kml_name
                    break

    return matches


def create_map_with_geojson(geojson_path, kml_path=None, title="GeoJSON Visualization"):
    """Create a folium map with GeoJSON overlay.
    If kml_path is provided, will transfer labels from KML to GeoJSON features."""
    center_lat, center_lon = get_bounds_from_geojson(geojson_path)

    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=15,
        tiles='OpenStreetMap'
    )

    # Load GeoJSON
    geojson_data = load_geojson(geojson_path)
    geojson_features = geojson_data.get('features', [])

    # Transfer labels from KML if provided
    if kml_path and os.path.exists(kml_path):
        try:
            # Parse KML to get features with names
            import xml.etree.ElementTree as ET

            with open(kml_path, 'r', encoding='utf-8') as f:
                kml_content = f.read()

            root = ET.fromstring(kml_content)
            ns = ''
            if root.tag.startswith('{'):
                ns = root.tag.split('}')[0] + '}'

            def find_with_ns(elem, path):
                if ns:
                    result = elem.findall(f'.//{ns}{path}')
                    if result:
                        return result
                return elem.findall(f'.//{path}') or elem.findall(f'.//{{{ns}}}{path}')

            def find_one_with_ns(elem, path):
                if ns:
                    result = elem.find(f'.//{ns}{path}')
                    if result is not None:
                        return result
                return elem.find(f'.//{path}') or elem.find(f'.//{{{ns}}}{path}')

            # Extract KML features and convert to GeoJSON format for matching
            kml_features_geojson = []
            placemarks = find_with_ns(root, 'Placemark')

            for pm in placemarks:
                name_elem = find_one_with_ns(pm, 'name')
                name = name_elem.text.strip() if name_elem is not None and name_elem.text else ''
                if not name:
                    continue

                # Convert KML geometry to GeoJSON format
                feature = {"type": "Feature", "properties": {
                    "name": name}, "geometry": None}

                for geom_type in ['Point', 'LineString', 'Polygon']:
                    geom_elem = find_one_with_ns(pm, geom_type)
                    if geom_elem is not None:
                        coord_elem = find_one_with_ns(geom_elem, 'coordinates')
                        if coord_elem is not None and coord_elem.text:
                            coord_str = coord_elem.text.strip()
                            coord_strs = coord_str.split()

                            if geom_type == 'Point' and coord_strs:
                                parts = coord_strs[0].split(',')
                                if len(parts) >= 2:
                                    try:
                                        feature["geometry"] = {
                                            "type": "Point",
                                            "coordinates": [float(parts[0]), float(parts[1])]
                                        }
                                    except ValueError:
                                        pass
                            elif geom_type == 'LineString' and coord_strs:
                                coords = []
                                for cs in coord_strs:
                                    parts = cs.split(',')
                                    if len(parts) >= 2:
                                        try:
                                            coords.append(
                                                [float(parts[0]), float(parts[1])])
                                        except ValueError:
                                            continue
                                if coords:
                                    feature["geometry"] = {
                                        "type": "LineString",
                                        "coordinates": coords
                                    }
                            elif geom_type == 'Polygon':
                                outer_elem = find_one_with_ns(
                                    geom_elem, 'outerBoundaryIs')
                                if outer_elem is not None:
                                    linear_ring = find_one_with_ns(
                                        outer_elem, 'LinearRing')
                                    if linear_ring is not None:
                                        coord_elem = find_one_with_ns(
                                            linear_ring, 'coordinates')
                                        if coord_elem is not None and coord_elem.text:
                                            coord_str = coord_elem.text.strip()
                                            coord_strs = coord_str.split()
                                            coords = []
                                            for cs in coord_strs:
                                                parts = cs.split(',')
                                                if len(parts) >= 2:
                                                    try:
                                                        coords.append(
                                                            [float(parts[0]), float(parts[1])])
                                                    except ValueError:
                                                        continue
                                            if coords:
                                                feature["geometry"] = {
                                                    "type": "Polygon",
                                                    "coordinates": [coords]
                                                }
                        break

                if feature["geometry"] is not None:
                    kml_features_geojson.append(feature)

            # Match and transfer names
            if kml_features_geojson:
                matches = match_features_by_geometry(
                    kml_features_geojson, geojson_features)

                # Transfer names to GeoJSON features
                for idx, name in matches.items():
                    if 'properties' not in geojson_features[idx]:
                        geojson_features[idx]['properties'] = {}
                    geojson_features[idx]['properties']['name'] = name
        except Exception as e:
            print(f"Warning: Could not transfer labels from KML: {e}")

    # Add GeoJSON features with different colors for different geometry types
    folium.GeoJson(
        geojson_data,
        name=title,
        style_function=lambda feature: {
            'color': 'blue' if feature['geometry']['type'] == 'LineString' else
            'red' if feature['geometry']['type'] == 'Point' else
            'green',
            'weight': 2 if feature['geometry']['type'] == 'LineString' else 1,
            'fillOpacity': 0.3 if feature['geometry']['type'] == 'Polygon' else 0,
            'fillColor': 'green' if feature['geometry']['type'] == 'Polygon' else 'transparent'
        }
    ).add_to(m)

    # Add labels for GeoJSON features (same logic as KML)
    # Filter: Only show labels for LineString features (same as KML)
    label_groups = {}
    for feature in geojson_features:
        name = feature.get('properties', {}).get('name', '')
        if not name:
            continue

        geom = feature.get('geometry', {})
        geom_type = geom.get('type', '')

        # Filter: Only show labels for LineString features
        # This matches the KML filtering logic for consistency
        if geom_type != 'LineString':
            continue

        coords = geom.get('coordinates', [])
        label_location = None

        if geom_type == 'LineString' and len(coords) > 0:
            mid_idx = len(coords) // 2
            mid_coord = coords[mid_idx]
            label_location = (
                round(mid_coord[1], 6), round(mid_coord[0], 6))

        if label_location:
            if label_location not in label_groups:
                label_groups[label_location] = []
            label_groups[label_location].append((name, feature))

    # Add labels with smart spacing to avoid overlaps (same logic as KML)

    for (lat, lon), name_features in label_groups.items():
        names = [nf[0] for nf in name_features]

        if len(names) == 1:
            # Single label - place at exact location
            label_text = names[0]
            offset_lat = lat
            offset_lon = lon

            folium.Marker(
                location=[offset_lat, offset_lon],
                popup=folium.Popup(label_text, max_width=200),
                tooltip=label_text,
                icon=folium.DivIcon(
                    html=f'<div style="font-size: 11px; font-weight: bold; color: black; text-shadow: -1px -1px 0 white, 1px -1px 0 white, -1px 1px 0 white, 1px 1px 0 white; background: rgba(255,255,255,0.85); padding: 2px 4px; border-radius: 3px; border: 1px solid rgba(0,0,0,0.3);">{label_text}</div>',
                    icon_size=(len(label_text) * 7, 18),
                    icon_anchor=(len(label_text) * 3.5, 9)
                )
            ).add_to(m)
        else:
            # Multiple labels - distribute in a circular pattern
            num_labels = len(names)
            spacing_radius = 0.0002  # ~20 meters

            if num_labels <= 4:
                # For 2-4 labels, use cardinal/intercardinal directions
                positions = [
                    (0, spacing_radius),      # North
                    (spacing_radius, 0),      # East
                    (0, -spacing_radius),     # South
                    (-spacing_radius, 0),     # West
                ]
            else:
                # For more labels, distribute in a circle
                angle_step = 2 * math.pi / num_labels
                positions = []
                for i in range(num_labels):
                    angle = i * angle_step
                    offset_lat_delta = spacing_radius * math.cos(angle)
                    offset_lon_delta = spacing_radius * \
                        math.sin(angle) / math.cos(math.radians(lat))
                    positions.append((offset_lon_delta, offset_lat_delta))

            # Place each label at its offset position
            for i, name in enumerate(names):
                offset_lon_delta, offset_lat_delta = positions[i % len(
                    positions)]
                offset_lat = lat + offset_lat_delta
                offset_lon = lon + offset_lon_delta

                folium.Marker(
                    location=[offset_lat, offset_lon],
                    popup=folium.Popup(name, max_width=200),
                    tooltip=name,
                    icon=folium.DivIcon(
                        html=f'<div style="font-size: 11px; font-weight: bold; color: black; text-shadow: -1px -1px 0 white, 1px -1px 0 white, -1px 1px 0 white, 1px 1px 0 white; background: rgba(255,255,255,0.85); padding: 2px 4px; border-radius: 3px; border: 1px solid rgba(0,0,0,0.3);">{name}</div>',
                        icon_size=(len(name) * 7, 18),
                        icon_anchor=(len(name) * 3.5, 9)
                    )
                ).add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    return m


def combine_maps_html(kml_html_path, geojson_html_path, output_path):
    """Combine two folium map HTML files into a single side-by-side HTML."""
    # #region agent log
    log_debug("debug-session", "run1", "D", "visualize_sites.py:112", "combine_maps_html entry",
              {"kml_html_path": kml_html_path, "geojson_html_path": geojson_html_path})
    # #endregion

    # Read both HTML files
    with open(kml_html_path, 'r', encoding='utf-8') as f:
        kml_html = f.read()
    # #region agent log
    log_debug("debug-session", "run1", "D", "visualize_sites.py:117", "KML HTML read", {"kml_html_length": len(
        kml_html), "has_body": "<body>" in kml_html, "has_scripts": "<script" in kml_html, "script_count": kml_html.count("<script")})
    # #endregion

    with open(geojson_html_path, 'r', encoding='utf-8') as f:
        geojson_html = f.read()

    # Extract head content (CSS, leaflet includes, etc.) from both files
    head_pattern = r'<head>(.*?)</head>'
    kml_head_match = re.search(head_pattern, kml_html, re.DOTALL)
    geojson_head_match = re.search(head_pattern, geojson_html, re.DOTALL)

    kml_head_content = kml_head_match.group(1) if kml_head_match else ''
    geojson_head_content = geojson_head_match.group(
        1) if geojson_head_match else ''

    # Extract just the CSS styles from GeoJSON head (we'll merge them)
    # Find the style block that contains a map ID selector
    geojson_style_pattern = r'(<style[^>]*>.*?#map_[a-f0-9]+.*?</style>)'
    geojson_style_match = re.search(
        geojson_style_pattern, geojson_head_content, re.DOTALL)
    geojson_map_style = geojson_style_match.group(
        1) if geojson_style_match else ''

    # #region agent log
    log_debug("debug-session", "run1", "D", "visualize_sites.py:330", "Extracted GeoJSON style", {
        "geojson_map_style_found": bool(geojson_map_style),
        "geojson_map_style_length": len(geojson_map_style) if geojson_map_style else 0
    })
    # #endregion

    # Use KML head as base (has all the script/link tags)
    head_content = kml_head_content

    # Extract body content
    body_pattern = r'<body>(.*?)</body>'
    kml_body_match = re.search(body_pattern, kml_html, re.DOTALL)
    geojson_body_match = re.search(body_pattern, geojson_html, re.DOTALL)

    kml_body = kml_body_match.group(1) if kml_body_match else ''
    geojson_body = geojson_body_match.group(1) if geojson_body_match else ''

    # Extract scripts
    script_pattern = r'<script[^>]*>(.*?)</script>'
    kml_scripts = re.findall(script_pattern, kml_html, re.DOTALL)
    geojson_scripts = re.findall(script_pattern, geojson_html, re.DOTALL)

    # Extract the actual map variable names and IDs from scripts first
    def extract_map_info(scripts_text):
        """Extract map variable name and map ID from scripts."""
        # Find var map_xxx = L.map("map_xxx", ...)
        match = re.search(
            r'var\s+(map_[a-f0-9]+)\s*=\s*L\.map\s*\(\s*["\'](map_[a-f0-9]+)["\']', scripts_text)
        if match:
            return match.group(1), match.group(2)  # variable name, ID
        return None, None

    kml_scripts_text = ' '.join(kml_scripts)
    geojson_scripts_text = ' '.join(geojson_scripts)

    kml_map_var, kml_map_id = extract_map_info(kml_scripts_text)
    geojson_map_var, geojson_map_id = extract_map_info(geojson_scripts_text)

    # #region agent log
    log_debug("debug-session", "run1", "D", "visualize_sites.py:343", "Extracted map info", {
        "kml_map_var": kml_map_var, "kml_map_id": kml_map_id,
        "geojson_map_var": geojson_map_var, "geojson_map_id": geojson_map_id
    })
    # #endregion

    # Replace map IDs in body HTML
    if kml_map_id:
        kml_body = re.sub(rf'id="{re.escape(kml_map_id)}"',
                          f'id="kml_{kml_map_id}"', kml_body)
    if geojson_map_id:
        geojson_body = re.sub(
            rf'id="{re.escape(geojson_map_id)}"', f'id="geojson_{geojson_map_id}"', geojson_body)

    # Update CSS styles in head_content that reference the map IDs
    if kml_map_id:
        # Update CSS selectors like #map_xxx { ... }
        head_content = re.sub(
            rf'#({re.escape(kml_map_id)})', r'#kml_\1', head_content)
        # Update any style attributes or other references in quotes
        head_content = re.sub(
            rf'"{re.escape(kml_map_id)}"', f'"kml_{kml_map_id}"', head_content)

    # Add GeoJSON map CSS style if it exists
    if geojson_map_style and geojson_map_id:
        # Update the GeoJSON map ID in its style block
        geojson_map_style_updated = re.sub(
            rf'#({re.escape(geojson_map_id)})', r'#geojson_\1', geojson_map_style)
        # Insert it after the KML map style (or at the end of existing styles)
        # Find where to insert (after the last </style> tag in head_content)
        style_insert_pos = head_content.rfind('</style>')
        if style_insert_pos != -1:
            # Insert after the closing </style> tag
            head_content = (head_content[:style_insert_pos + 8] +
                            '\n            ' + geojson_map_style_updated +
                            head_content[style_insert_pos + 8:])
        else:
            # No style found, append it before closing head (if we can find it) or at end
            head_end = head_content.rfind('</head>')
            if head_end != -1:
                head_content = head_content[:head_end] + '\n            ' + \
                    geojson_map_style_updated + '\n' + head_content[head_end:]
            else:
                head_content += '\n            ' + geojson_map_style_updated

        # #region agent log
        log_debug("debug-session", "run1", "D", "visualize_sites.py:390", "Added GeoJSON CSS style", {
            "geojson_style_added": f"geojson_{geojson_map_id}" in head_content
        })
        # #endregion

    # #region agent log
    log_debug("debug-session", "run1", "D", "visualize_sites.py:385", "Updated CSS styles in head", {
        "head_has_kml_id": f"kml_{kml_map_id}" in head_content if kml_map_id else False,
        "head_has_geojson_id": f"geojson_{geojson_map_id}" in head_content if geojson_map_id else False
    })
    # #endregion

    # Replace variable names in scripts
    def fix_kml_script(script):
        if kml_map_var:
            # Replace the variable declaration
            script = re.sub(
                rf'var\s+{re.escape(kml_map_var)}\s*=', f'var kml_{kml_map_var} =', script)
            # Replace ALL references to the map variable (word boundary to avoid partial matches)
            script = re.sub(rf'\b{re.escape(kml_map_var)}\b',
                            f'kml_{kml_map_var}', script)
        if kml_map_id:
            # Replace the ID in L.map() calls (handle both single and double quotes)
            script = re.sub(
                rf'L\.map\s*\(\s*["\']{re.escape(kml_map_id)}["\']', f"L.map('kml_{kml_map_id}')", script)
        return script

    def fix_geojson_script(script):
        if geojson_map_var:
            # Replace the variable declaration
            script = re.sub(rf'var\s+{re.escape(geojson_map_var)}\s*=',
                            f'var geojson_{geojson_map_var} =', script)
            # Replace ALL references to the map variable
            script = re.sub(rf'\b{re.escape(geojson_map_var)}\b',
                            f'geojson_{geojson_map_var}', script)
        if geojson_map_id:
            # Replace the ID in L.map() calls
            script = re.sub(
                rf'L\.map\s*\(\s*["\']{re.escape(geojson_map_id)}["\']', f"L.map('geojson_{geojson_map_id}')", script)
        return script

    kml_scripts_fixed = [fix_kml_script(s) for s in kml_scripts]
    geojson_scripts_fixed = [fix_geojson_script(s) for s in geojson_scripts]
    # #region agent log
    log_debug("debug-session", "run1", "D", "visualize_sites.py:165", "Scripts fixed", {"kml_scripts_count": len(
        kml_scripts_fixed), "geojson_scripts_count": len(geojson_scripts_fixed), "kml_body_has_map_id": 'id="' in kml_body, "kml_body_length": len(kml_body)})
    # #endregion

    # Create combined HTML
    combined_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KML vs GeoJSON Comparison</title>
    {head_content}
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 20px;
        }}
        .container {{
            display: flex;
            gap: 20px;
            justify-content: center;
            flex-wrap: wrap;
        }}
        .map-container {{
            flex: 1;
            min-width: 400px;
            max-width: 50%;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
            background: white;
        }}
        .map-header {{
            padding: 15px;
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
            text-align: center;
        }}
        .map-header.geojson {{
            background-color: #2196F3;
        }}
        .map-content {{
            height: 600px;
        }}
        @media (max-width: 900px) {{
            .map-container {{
                max-width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <h1>KML vs GeoJSON Comparison</h1>
    <div class="container">
        <div class="map-container">
            <div class="map-header">KML File</div>
            <div class="map-content">
                {kml_body}
            </div>
        </div>
        <div class="map-container">
            <div class="map-header geojson">GeoJSON File</div>
            <div class="map-content">
                {geojson_body}
            </div>
        </div>
    </div>
    <script>
        {' '.join(kml_scripts_fixed)}
        {' '.join(geojson_scripts_fixed)}
    </script>
</body>
</html>
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(combined_html)
    # #region agent log
    log_debug("debug-session", "run1", "D", "visualize_sites.py:247", "Combined HTML written", {"output_path": output_path, "combined_html_length": len(
        combined_html), "has_kml_body": kml_body[:100] in combined_html, "has_both_scripts": len(kml_scripts_fixed) > 0 and len(geojson_scripts_fixed) > 0})
    # #endregion


def create_side_by_side_html(kml_path, geojson_path, output_path='sites_comparison.html'):
    """Create an HTML file with two maps side by side."""

    print("Creating KML map...")
    kml_map = create_map_with_kml(kml_path, geojson_path, "KML Layers")

    print("Creating GeoJSON map...")
    geojson_map = create_map_with_geojson(
        geojson_path, kml_path=kml_path, title="GeoJSON Features")

    # Save maps to temporary files
    base_path = output_path.replace('.html', '')
    kml_map_file = f"{base_path}_kml.html"
    geojson_map_file = f"{base_path}_geojson.html"

    print(f"Saving individual maps...")
    kml_map.save(kml_map_file)
    # #region agent log
    with open(kml_map_file, 'r', encoding='utf-8') as f:
        kml_html_content_check = f.read()
    log_debug("debug-session", "run1", "D", "visualize_sites.py:265", "KML map saved", {"kml_file_size": len(
        kml_html_content_check), "has_map_div": "id=\"map_" in kml_html_content_check, "has_scripts": "<script" in kml_html_content_check, "has_kml_reference": "kml" in kml_html_content_check.lower()[:1000]})
    # #endregion
    geojson_map.save(geojson_map_file)

    print("Combining maps into side-by-side view...")
    combine_maps_html(kml_map_file, geojson_map_file, output_path)

    # Clean up temporary files (optional - comment out if you want to keep them)
    # os.remove(kml_map_file)
    # os.remove(geojson_map_file)

    print(f"\n✓ Comparison map saved to: {output_path}")
    print(f"✓ Individual maps saved to: {kml_map_file} and {geojson_map_file}")
    print(f"\nOpen {output_path} in your browser to view the visualization.")


def kml_placemark_to_geojson(pm, find_one_with_ns):
    """Convert a KML Placemark to GeoJSON feature."""
    feature = {"type": "Feature", "properties": {}, "geometry": None}
    
    # Extract name
    name_elem = find_one_with_ns(pm, 'name')
    if name_elem is not None and name_elem.text:
        feature["properties"]["name"] = name_elem.text.strip()
    
    # Extract geometry
    for geom_type in ['Point', 'LineString', 'Polygon']:
        geom_elem = find_one_with_ns(pm, geom_type)
        if geom_elem is not None:
            if geom_type == 'Point':
                coord_elem = find_one_with_ns(geom_elem, 'coordinates')
                if coord_elem is not None and coord_elem.text:
                    coord_str = coord_elem.text.strip()
                    coords_list = coord_str.split()
                    if coords_list:
                        parts = coords_list[0].split(',')
                        if len(parts) >= 2:
                            try:
                                feature["geometry"] = {
                                    "type": "Point",
                                    "coordinates": [float(parts[0]), float(parts[1])]
                                }
                            except ValueError:
                                pass
            elif geom_type == 'LineString':
                coord_elem = find_one_with_ns(geom_elem, 'coordinates')
                if coord_elem is not None and coord_elem.text:
                    coord_str = coord_elem.text.strip()
                    coord_strs = coord_str.split()
                    coords = []
                    for cs in coord_strs:
                        parts = cs.split(',')
                        if len(parts) >= 2:
                            try:
                                coords.append([float(parts[0]), float(parts[1])])
                            except ValueError:
                                continue
                    if coords:
                        feature["geometry"] = {
                            "type": "LineString",
                            "coordinates": coords
                        }
            elif geom_type == 'Polygon':
                outer_elem = find_one_with_ns(geom_elem, 'outerBoundaryIs')
                if outer_elem is not None:
                    linear_ring = find_one_with_ns(outer_elem, 'LinearRing')
                    if linear_ring is not None:
                        coord_elem = find_one_with_ns(linear_ring, 'coordinates')
                        if coord_elem is not None and coord_elem.text:
                            coord_str = coord_elem.text.strip()
                            coord_strs = coord_str.split()
                            coords = []
                            for cs in coord_strs:
                                parts = cs.split(',')
                                if len(parts) >= 2:
                                    try:
                                        coords.append([float(parts[0]), float(parts[1])])
                                    except ValueError:
                                        continue
                            if coords:
                                feature["geometry"] = {
                                    "type": "Polygon",
                                    "coordinates": [coords]
                                }
            break
    
    return feature if feature["geometry"] is not None else None


def create_setup_wizard(kml_path, geojson_path_for_bounds, output_path='setup_wizard.html'):
    """Create a setup wizard HTML page with progressive data entry forms based on field protocol."""
    import xml.etree.ElementTree as ET
    
    # Parse KML to extract features by type
    with open(kml_path, 'r', encoding='utf-8') as f:
        kml_content = f.read()
    
    root = ET.fromstring(kml_content)
    ns = ''
    if root.tag.startswith('{'):
        ns = root.tag.split('}')[0] + '}'
    
    def find_with_ns(elem, path):
        if ns:
            result = elem.findall(f'.//{ns}{path}')
            if result:
                return result
        return elem.findall(f'.//{path}') or elem.findall(f'.//{{{ns}}}{path}')
    
    def find_one_with_ns(elem, path):
        if ns:
            result = elem.find(f'.//{ns}{path}')
            if result is not None:
                return result
        return elem.find(f'.//{path}') or elem.find(f'.//{{{ns}}}{path}')
    
    # Extract features by type
    placemarks = find_with_ns(root, 'Placemark')
    
    sites = []  # Shola patches (Polygons with names like "Bikkapathimund_Shola_*")
    transects = []  # Transect lines (LineString with names like "A_T*", "B_T*")
    transect_points = []  # Transect start points (Point with names like "T*", "B_T*")
    plots = []  # 10x10m plots (Polygons with density names like "A_HD-*", "A_MD-*", etc.)
    
    for pm in placemarks:
        name_elem = find_one_with_ns(pm, 'name')
        name = name_elem.text.strip() if name_elem is not None and name_elem.text else ''
        
        if not name:
            continue
        
        # Convert to GeoJSON
        feature = kml_placemark_to_geojson(pm, find_one_with_ns)
        if feature is None:
            continue
        
        geom_type = feature["geometry"]["type"]
        
        # Categorize features
        if 'Shola' in name or 'shola' in name.lower():
            sites.append({'name': name, 'type': geom_type, 'feature': feature})
        elif name.startswith('A_T') or name.startswith('B_T'):
            if geom_type == 'LineString':
                transects.append({'name': name, 'type': geom_type, 'feature': feature})
            elif geom_type == 'Point':
                transect_points.append({'name': name, 'type': geom_type, 'feature': feature})
        elif any(prefix in name for prefix in ['A_HD', 'A_MD', 'A_LD', 'A_VHD', 'A_VHd', 'B_HD', 'B_MD', 'B_LD', 'B_VHD']):
            plots.append({'name': name, 'type': geom_type, 'feature': feature})
        elif name.startswith('T') and len(name) <= 3:  # T1, T2, etc.
            transect_points.append({'name': name, 'type': geom_type, 'feature': feature})
    
    # Get map center
    center_lat, center_lon = get_bounds_from_geojson(geojson_path_for_bounds)
    
    # Create HTML sections for each feature type
    html_sections = []
    
    # 1. Sites Section
    sites_map = folium.Map(location=[center_lat, center_lon], zoom_start=14, tiles='OpenStreetMap')
    sites_geojson = {"type": "FeatureCollection", "features": [s['feature'] for s in sites]}
    
    if sites_geojson["features"]:
        folium.GeoJson(sites_geojson, style_function=lambda x: {
            'fillColor': 'green', 'color': 'darkgreen', 'weight': 2, 'fillOpacity': 0.4
        }).add_to(sites_map)
        # Add labels
        for site in sites:
            geom = site['feature']['geometry']
            if geom['type'] == 'Polygon' and len(geom['coordinates']) > 0:
                coords = geom['coordinates'][0]
                if len(coords) > 0:
                    center = [sum(c[1] for c in coords) / len(coords), sum(c[0] for c in coords) / len(coords)]
                    folium.Marker(center, popup=site['name'], tooltip=site['name']).add_to(sites_map)
    
    sites_map_html = sites_map._repr_html_()
    
    sites_form = """
    <div class="data-form">
        <h3>Site Information</h3>
        <p><strong>Protocol Requirement:</strong> Four shola patches (two close to settlement: 150-350m, two far: >450m)</p>
        <p><strong>Found in KML:</strong> {site_count} site(s)</p>
        <div id="sites-container">
            <!-- Site forms will be generated here -->
        </div>
        <button onclick="addSite()">Add Missing Site</button>
    </div>
    """.format(site_count=len(sites))
    
    html_sections.append({
        'title': 'Step 1: Sites (Shola Patches)',
        'map_html': sites_map_html,
        'form_html': sites_form,
        'features': sites
    })
    
    # 2. Transects Section
    transects_map = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles='OpenStreetMap')
    transects_geojson = {"type": "FeatureCollection", "features": [t['feature'] for t in transects]}
    
    if transects_geojson["features"]:
        folium.GeoJson(transects_geojson, style_function=lambda x: {
            'color': 'blue', 'weight': 3
        }).add_to(transects_map)
        # Add labels at midpoint of each transect
        for transect in transects:
            geom = transect['feature']['geometry']
            if geom['type'] == 'LineString' and len(geom['coordinates']) > 0:
                mid_idx = len(geom['coordinates']) // 2
                mid_coord = geom['coordinates'][mid_idx]
                folium.Marker(
                    [mid_coord[1], mid_coord[0]],
                    popup=transect['name'],
                    tooltip=transect['name'],
                    icon=folium.DivIcon(
                        html=f'<div style="font-size: 11px; font-weight: bold; color: blue; text-shadow: -1px -1px 0 white, 1px -1px 0 white, -1px 1px 0 white, 1px 1px 0 white; background: rgba(255,255,255,0.85); padding: 2px 4px; border-radius: 3px;">{transect["name"]}</div>',
                        icon_size=(len(transect['name']) * 7, 18),
                        icon_anchor=(len(transect['name']) * 3.5, 9)
                    )
                ).add_to(transects_map)
    
    transects_map_html = transects_map._repr_html_()
    
    transects_form = """
    <div class="data-form">
        <h3>Transect Information</h3>
        <p><strong>Protocol Requirement:</strong> Transects radiating from shola edge into interior, perpendicular to edge, minimum 50m separation</p>
        <p><strong>Found in KML:</strong> {transect_count} transect(s)</p>
        <div id="transects-container">
            <!-- Transect forms will be generated here -->
        </div>
    </div>
    """.format(transect_count=len(transects))
    
    html_sections.append({
        'title': 'Step 2: Transects',
        'map_html': transects_map_html,
        'form_html': transects_form,
        'features': transects
    })
    
    # 3. Plots Section
    plots_map = folium.Map(location=[center_lat, center_lon], zoom_start=16, tiles='OpenStreetMap')
    plots_geojson = {"type": "FeatureCollection", "features": [p['feature'] for p in plots]}
    
    if plots_geojson["features"]:
        folium.GeoJson(plots_geojson, style_function=lambda x: {
            'fillColor': 'orange', 'color': 'darkorange', 'weight': 2, 'fillOpacity': 0.5
        }).add_to(plots_map)
        # Add labels at center of each plot
        for plot in plots:
            geom = plot['feature']['geometry']
            if geom['type'] == 'Polygon' and len(geom['coordinates']) > 0:
                coords = geom['coordinates'][0]
                if len(coords) > 0:
                    center = [sum(c[1] for c in coords) / len(coords), sum(c[0] for c in coords) / len(coords)]
                    folium.Marker(
                        center,
                        popup=plot['name'],
                        tooltip=plot['name'],
                        icon=folium.DivIcon(
                            html=f'<div style="font-size: 10px; font-weight: bold; color: darkorange; text-shadow: -1px -1px 0 white, 1px -1px 0 white, -1px 1px 0 white, 1px 1px 0 white; background: rgba(255,255,255,0.85); padding: 2px 4px; border-radius: 3px;">{plot["name"]}</div>',
                            icon_size=(len(plot['name']) * 6, 16),
                            icon_anchor=(len(plot['name']) * 3, 8)
                        )
                    ).add_to(plots_map)
    
    plots_map_html = plots_map._repr_html_()
    
    plots_form = """
    <div class="data-form">
        <h3>Plot Information (10x10m)</h3>
        <p><strong>Protocol Requirement:</strong> Five plots per transect at 0m, 10m, 20m, 40m, 60m from edge</p>
        <p><strong>Data Required per Plot:</strong></p>
        <ul>
            <li>DBH of all woody individuals ≥1cm (including Cestrum)</li>
            <li>Soil moisture at center (Dry+, Dry-, Normal, Wet-, Wet+)</li>
            <li>Canopy openness at center (4 readings in cardinal directions)</li>
            <li>Other observations (dung, lopping, trails, etc.)</li>
        </ul>
        <p><strong>Found in KML:</strong> {plot_count} plot(s)</p>
        <div id="plots-container">
            <!-- Plot forms will be generated here -->
        </div>
    </div>
    """.format(plot_count=len(plots))
    
    html_sections.append({
        'title': 'Step 3: Plots (10x10m)',
        'map_html': plots_map_html,
        'form_html': plots_form,
        'features': plots
    })
    
    # 4. Subplots Section
    subplots_map = folium.Map(location=[center_lat, center_lon], zoom_start=17, tiles='OpenStreetMap')
    
    subplots_form = """
    <div class="data-form">
        <h3>Subplot Information (2x2m)</h3>
        <p><strong>Protocol Requirement:</strong> Four subplots per 10x10m plot, at corners, numbered 1-4 clockwise from left corner closest to edge</p>
        <p><strong>Data Required per Subplot:</strong></p>
        <ul>
            <li>Number of seedlings (non-woody individuals)</li>
            <li>Number of saplings (woody individuals <1.3m OR ≥1.3m but DBH <1cm)</li>
            <li>Ocular estimate of grass cover (%)</li>
            <li>Ocular estimate of bare ground cover (%)</li>
            <li>Soil moisture (Dry+, Dry-, Normal, Wet-, Wet+)</li>
        </ul>
        <p><strong>Status:</strong> ⚠️ Subplots not found in KML - need to be generated from plot corners or provided by user</p>
        <div id="subplots-container">
            <!-- Subplot forms will be generated here after plots are defined -->
        </div>
    </div>
    """
    
    html_sections.append({
        'title': 'Step 4: Subplots (2x2m)',
        'map_html': subplots_map._repr_html_(),
        'form_html': subplots_form,
        'features': []
    })
    
    # Generate full HTML
    sections_html = ""
    for i, section in enumerate(html_sections, 1):
        sections_html += f"""
        <section id="step-{i}" class="wizard-step">
            <h2>{section['title']}</h2>
            <div class="step-content">
                <div class="map-wrapper">
                    {section['map_html']}
                </div>
                {section['form_html']}
            </div>
        </section>
        """
    
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Ecological Survey Setup Wizard</title>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .wizard-container {{
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .wizard-step {{
                margin-bottom: 40px;
                padding: 20px;
                border: 2px solid #ddd;
                border-radius: 8px;
                background: #fafafa;
            }}
            .wizard-step h2 {{
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
            }}
            .step-content {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-top: 20px;
            }}
            .map-wrapper {{
                min-height: 500px;
            }}
            .data-form {{
                background: white;
                padding: 20px;
                border-radius: 4px;
                border: 1px solid #ddd;
            }}
            .data-form h3 {{
                color: #27ae60;
                margin-top: 0;
            }}
            .data-form ul {{
                margin: 10px 0;
                padding-left: 20px;
            }}
            .data-form button {{
                background: #3498db;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                cursor: pointer;
                margin-top: 10px;
            }}
            .data-form button:hover {{
                background: #2980b9;
            }}
            @media (max-width: 1200px) {{
                .step-content {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="wizard-container">
            <h1>Ecological Survey Setup Wizard</h1>
            <p>This wizard guides you through data entry for the Cestrum invasion study at Bikkapathy Mund, based on the field protocol.</p>
            {sections_html}
        </div>
        <script>
            function addSite() {{
                alert('Functionality to add missing sites will be implemented');
            }}
        </script>
    </body>
    </html>
    """
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"✓ Setup wizard created: {output_path}")


def main():
    """Main function."""
    script_dir = Path(__file__).parent
    kml_path = script_dir / 'assets' / 'sites.kml'
    geojson_path = script_dir / 'assets' / 'sites.geojson'
    output_path = script_dir / 'sites_comparison.html'

    if not kml_path.exists():
        print(f"Error: KML file not found at {kml_path}")
        return

    if not geojson_path.exists():
        print(f"Error: GeoJSON file not found at {geojson_path}")
        return

    create_side_by_side_html(str(kml_path), str(
        geojson_path), str(output_path))
    
    # Also create setup wizard
    wizard_path = script_dir / 'setup_wizard.html'
    create_setup_wizard(str(kml_path), str(geojson_path), str(wizard_path))


if __name__ == '__main__':
    main()
