import xml.etree.ElementTree as ET
from shapely.geometry import Polygon, LineString, Point
import sys
import os

# Namespace for KML
NS = {'kml': 'http://www.opengis.net/kml/2.2'}

def parse_kml_coordinates(coords_str):
    points = []
    for coord in coords_str.strip().split():
        parts = coord.split(',')
        if len(parts) >= 2:
            points.append((float(parts[0]), float(parts[1])))
    return points

def extract_features(kml_path):
    tree = ET.parse(kml_path)
    root = tree.getroot()
    features = []
    
    for placemark in root.findall('.//kml:Placemark', NS):
        name = placemark.find('kml:name', NS)
        name = name.text if name is not None else "Unnamed"
        
        # Try Polygon
        polygon = placemark.find('.//kml:Polygon', NS)
        if polygon is not None:
            coords_node = polygon.find('.//kml:coordinates', NS)
            if coords_node is not None and coords_node.text:
                coords = parse_kml_coordinates(coords_node.text)
                if len(coords) >= 3:
                     geom = Polygon(coords)
                     features.append({'name': name, 'type': 'Polygon', 'geometry': geom})
                continue
        
        # Try LineString
        linestring = placemark.find('.//kml:LineString', NS)
        if linestring is not None:
            coords_node = linestring.find('.//kml:coordinates', NS)
            if coords_node is not None and coords_node.text:
                coords = parse_kml_coordinates(coords_node.text)
                if len(coords) >= 2:
                    geom = LineString(coords)
                    features.append({'name': name, 'type': 'LineString', 'geometry': geom})
                continue
        
    return features

def analyze(kml_path):
    print(f"Parsing {kml_path}...")
    features = extract_features(kml_path)
    print(f"Found {len(features)} total features.")
    
    # Map by name (handle duplicates by keeping list or just last one for single lookup)
    # Using list to see duplicates
    f_map = {}
    for f in features:
        if f['name'] not in f_map:
            f_map[f['name']] = []
        f_map[f['name']].append(f)
        
    # 1. Unnamed
    unnamed = f_map.get('Unnamed', [])
    print(f"Unnamed features count: {len(unnamed)}")
    
    # 2. A_MD-7 Analysis
    amd7_list = f_map.get('A_MD-7', [])
    if not amd7_list:
        print("A_MD-7 not found!")
    else:
        amd7 = amd7_list[0] # Assume first
        print(f"A_MD-7 Type: {amd7['type']}, Area: {amd7['geometry'].area:.2e}")
        
    # 3. Transects Analysis
    transect_names = ['A_T4', '60m 1', '60m 10']
    
    for t_name in transect_names:
        ts = f_map.get(t_name, [])
        if not ts:
            print(f"{t_name} not found.")
            continue
        
        t = ts[0]
        print(f"{t_name} Type: {t['type']}, Length: {t['geometry'].length:.2e}")
        
        # Check containment in A_MD-7
        if amd7_list:
            poly = amd7_list[0]['geometry']
            line = t['geometry']
            print(f"  Contained in A_MD-7? {poly.contains(line)}")
    
    # 4. Block vs Plot Nesting
    shola_a = f_map.get('Bikkapathimund_Shola_A', [])
    if shola_a and amd7_list:
        block_geom = shola_a[0]['geometry']
        plot_geom = amd7_list[0]['geometry']
        print(f"\nBikkapathimund_Shola_A contains A_MD-7? {block_geom.contains(plot_geom)}")
        print(f"Bikkapathimund_Shola_A Area: {block_geom.area:.2e}")
    else:
        print("\nCould not check Bikkapathimund Nesting (missing features).")

if __name__ == "__main__":
    analyze('examples/setup_wizard/sites.kml')
