import argparse
from shapely.geometry import Polygon, LineString
import xml.etree.ElementTree as ET
import math

NS = {'kml': 'http://www.opengis.net/kml/2.2'}

def parse_kml_coordinates(coords_str):
    points = []
    for coord in coords_str.strip().split():
        parts = coord.split(',')
        if len(parts) >= 2:
            points.append((float(parts[0]), float(parts[1])))
    return points

def analyze(kml_path):
    tree = ET.parse(kml_path)
    root = tree.getroot()
    
    features = {}
    
    for placemark in root.findall('.//kml:Placemark', NS):
        name = placemark.find('kml:name', NS)
        name = name.text if name is not None else "Unnamed"
        
        # Polygon
        polygon = placemark.find('.//kml:Polygon', NS)
        if polygon is not None:
            coords_node = polygon.find('.//kml:coordinates', NS)
            if coords_node and coords_node.text:
                coords = parse_kml_coordinates(coords_node.text)
                features[name] = {'type': 'Polygon', 'geom': Polygon(coords)}
                
        # LineString
        linestring = placemark.find('.//kml:LineString', NS)
        if linestring is not None:
            coords_node = linestring.find('.//kml:coordinates', NS)
            if coords_node and coords_node.text:
                coords = parse_kml_coordinates(coords_node.text)
                features[name] = {'type': 'LineString', 'geom': LineString(coords)}

    # Analysis 1: A_MD-7 vs A_T4
    print("--- Analysis: A_MD-7 vs A_T4 ---")
    if 'A_MD-7' in features and 'A_T4' in features:
        amd7 = features['A_MD-7']['geom']
        at4 = features['A_T4']['geom']
        
        print(f"A_MD-7 Area: {amd7.area:.2e} (approx deg^2)")
        print(f"A_T4 Length: {at4.length:.2e} (approx deg)")
        print(f"A_MD-7 Contains A_T4? {amd7.contains(at4)}")
        print(f"A_MD-7 Covers A_T4? {amd7.covers(at4)}")
        print(f"A_MD-7 Intersects A_T4? {amd7.intersects(at4)}")
        print(f"Integration: A_T4 within A_MD-7 is {at4.intersection(amd7).length / at4.length * 100:.1f}%")
    else:
        print("Features A_MD-7 or A_T4 not found.")

    # Analysis 2: 60m 1 vs A_T1 (Transect comparison)
    print("\n--- Analysis: Transects vs Markers ---")
    transects = ['A_T1', '60m 1', '60m 4']
    for t_name in transects:
        if t_name in features:
            geom = features[t_name]['geom']
            print(f"{t_name}: Length={geom.length:.2e}")
        else:
            print(f"{t_name}: Not found")

    # Analysis 3: Unnamed Stats
    unnamed_count = sum(1 for k in features if k == 'Unnamed')
    print(f"\nTotal Unnamed features: {unnamed_count}")

analyze('examples/setup_wizard/sites.kml')
