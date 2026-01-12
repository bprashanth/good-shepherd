"""KML parsing utilities for extracting features from KML files."""
import xml.etree.ElementTree as ET
from pathlib import Path
import json


def parse_kml(kml_path):
    """
    Parse KML file and extract all features.
    
    Returns:
        List of feature dictionaries with name, geometry type, and coordinates
    """
    kml_path = Path(kml_path)
    if not kml_path.exists():
        raise FileNotFoundError(f"KML file not found: {kml_path}")
    
    with open(kml_path, 'r', encoding='utf-8') as f:
        kml_content = f.read()
    
    root = ET.fromstring(kml_content)
    
    # Detect namespace
    ns = ''
    if root.tag.startswith('{'):
        ns = root.tag.split('}')[0] + '}'
    
    def find_with_ns(elem, path):
        """Find elements with namespace handling."""
        if ns:
            result = elem.findall(f'.//{ns}{path}')
            if result:
                return result
        return elem.findall(f'.//{path}') or elem.findall(f'.//{{{ns}}}{path}')
    
    def find_one_with_ns(elem, path):
        """Find single element with namespace handling."""
        if ns:
            result = elem.find(f'.//{ns}{path}')
            if result is not None:
                return result
        return elem.find(f'.//{path}') or elem.find(f'.//{{{ns}}}{path}')
    
    # Find all Placemark elements
    placemarks = find_with_ns(root, 'Placemark')
    
    features = []
    
    for pm in placemarks:
        feature = {
            "name": None,
            "geometry_type": None,
            "coordinates": None,
            "description": None
        }
        
        # Extract name
        name_elem = find_one_with_ns(pm, 'name')
        if name_elem is not None and name_elem.text:
            feature["name"] = name_elem.text.strip()
        
        # Extract description
        desc_elem = find_one_with_ns(pm, 'description')
        if desc_elem is not None and desc_elem.text:
            feature["description"] = desc_elem.text.strip()
        
        # Extract geometry
        for geom_type in ['Point', 'LineString', 'Polygon']:
            geom_elem = find_one_with_ns(pm, geom_type)
            if geom_elem is not None:
                feature["geometry_type"] = geom_type
                
                if geom_type == 'Point':
                    coord_elem = find_one_with_ns(geom_elem, 'coordinates')
                    if coord_elem is not None and coord_elem.text:
                        coord_str = coord_elem.text.strip()
                        coords_list = coord_str.split()
                        if coords_list:
                            parts = coords_list[0].split(',')
                            if len(parts) >= 2:
                                try:
                                    feature["coordinates"] = [float(parts[0]), float(parts[1])]
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
                            feature["coordinates"] = coords
                
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
                                    feature["coordinates"] = [coords]
                
                break
        
        # Only add features with names and valid geometry
        if feature["name"] and feature["coordinates"]:
            features.append(feature)
    
    return features


def kml_to_geojson(kml_path, output_path=None):
    """
    Convert KML to GeoJSON format.
    
    Returns:
        GeoJSON FeatureCollection dictionary
    """
    features_list = parse_kml(kml_path)
    
    geojson_features = []
    for feat in features_list:
        geojson_feat = {
            "type": "Feature",
            "properties": {
                "name": feat["name"]
            },
            "geometry": None
        }
        
        if feat["description"]:
            geojson_feat["properties"]["description"] = feat["description"]
        
        if feat["geometry_type"] == "Point":
            geojson_feat["geometry"] = {
                "type": "Point",
                "coordinates": feat["coordinates"]
            }
        elif feat["geometry_type"] == "LineString":
            geojson_feat["geometry"] = {
                "type": "LineString",
                "coordinates": feat["coordinates"]
            }
        elif feat["geometry_type"] == "Polygon":
            geojson_feat["geometry"] = {
                "type": "Polygon",
                "coordinates": feat["coordinates"]
            }
        
        if geojson_feat["geometry"]:
            geojson_features.append(geojson_feat)
    
    geojson = {
        "type": "FeatureCollection",
        "features": geojson_features
    }
    
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(geojson, f, indent=2)
    
    return geojson


def get_feature_list_for_agent(kml_path):
    """
    Get a simple list of feature names and types for agent processing.
    
    Returns:
        List of dictionaries with name and geometry_type
    """
    features = parse_kml(kml_path)
    return [
        {
            "name": f["name"],
            "geometry_type": f["geometry_type"]
        }
        for f in features
        if f["name"] and f["geometry_type"]
    ]

