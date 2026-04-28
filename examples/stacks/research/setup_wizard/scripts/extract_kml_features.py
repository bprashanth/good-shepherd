import argparse
import json
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon, LineString, Point, shape
from shapely.ops import unary_union
import os

# Namespace for KML
NS = {'kml': 'http://www.opengis.net/kml/2.2'}

def parse_kml_coordinates(coords_str):
    """
    Parses a KML coordinate string "long,lat,alt long,lat,alt ..."
    returns a list of (long, lat) tuples.
    """
    points = []
    for coord in coords_str.strip().split():
        parts = coord.split(',')
        if len(parts) >= 2:
            points.append((float(parts[0]), float(parts[1])))
    return points

def extract_features(kml_path):
    """
    Parses KML and extracts Geometry objects with their names and IDs.
    Returns a list of dicts: {'name': str, 'type': str, 'geometry': ShapelyGeom}
    """
    tree = ET.parse(kml_path)
    root = tree.getroot()
    
    features = []
    
    import re
    
    # Recursively find Placemarks
    for placemark in root.findall('.//kml:Placemark', NS):
        name = placemark.find('kml:name', NS)
        name_str = name.text.strip() if (name is not None and name.text) else "Unnamed"
        
        # Filter 1: Unnamed
        if name_str == "Unnamed":
            continue
            
        # Filter 2: Distance markers (e.g. "60m 1", "100m")
        # Regex: starts with digits, followed by 'm', optional space and more digits
        if re.match(r'^\d+m.*', name_str, re.IGNORECASE):
            continue

        # Try Polygon
        polygon = placemark.find('.//kml:Polygon', NS)
        if polygon is not None:
            coords_node = polygon.find('.//kml:coordinates', NS)
            if coords_node is not None and coords_node.text:
                coords = parse_kml_coordinates(coords_node.text)
                if len(coords) >= 3:
                     geom = Polygon(coords)
                     features.append({'name': name_str, 'type': 'Polygon', 'geometry': geom})
                continue
        
        # Try LineString
        linestring = placemark.find('.//kml:LineString', NS)
        if linestring is not None:
            coords_node = linestring.find('.//kml:coordinates', NS)
            if coords_node is not None and coords_node.text:
                coords = parse_kml_coordinates(coords_node.text)
                if len(coords) >= 2:
                    geom = LineString(coords)
                    features.append({'name': name_str, 'type': 'LineString', 'geometry': geom})
                continue
        
        # Try Point (optional support, mostly for subplots if needed later)
        point = placemark.find('.//kml:Point', NS)
        if point is not None:
            coords_node = point.find('.//kml:coordinates', NS)
            if coords_node is not None and coords_node.text:
                 coords = parse_kml_coordinates(coords_node.text)
                 if len(coords) >= 1:
                     geom = Point(coords[0])
                     features.append({'name': name_str, 'type': 'Point', 'geometry': geom})

    return features

def classify_hierarchy(features):
    """
    Classifies features into Blocks, Transects, and Plots based on geometric nesting.
    Priority 1: Polygon Nesting (Parent=Block, Child=Plot)
    Priority 2: Transect containment/intersection.
    """
    blocks = []
    transects = []
    plots = []
    orphans = []

    polygons = [f for f in features if f['type'] == 'Polygon']
    linestrings = [f for f in features if f['type'] == 'LineString']
    
    # --- Step 1: Establish Polygon Hierarchy (Block vs Plot) ---
    # We look for Polygons that contain other Polygons.
    # Logic:
    # - If A contains B, A is a "Parent" and B is a "Child".
    # - A Polygon with NO Parent is a BLOCK candidate.
    # - A Polygon WITH a Parent is a PLOT candidate.
    
    # Adjacency list for polygon nesting
    # poly_children[parent_idx] = [child_idx, ...]
    poly_children = {i: [] for i in range(len(polygons))}
    poly_has_parent = {i: False for i in range(len(polygons))}
    
    for i, poly_a in enumerate(polygons):
        geom_a = poly_a['geometry']
        for j, poly_b in enumerate(polygons):
            if i == j: continue
            geom_b = poly_b['geometry']
            
            # Use strict contains or covers
            if geom_a.contains(geom_b) or geom_a.covers(geom_b):
                poly_children[i].append(j)
                poly_has_parent[j] = True

    # Identify Blocks (Roots) and Plots (Leaves/Children)
    # We wrap them in our output dict structure immediately
    
    # Store temporary map to easy access objects
    # block_map[poly_index] = block_dict
    block_map = {} 
    
    for i, poly in enumerate(polygons):
        if not poly_has_parent[i]:
            # This is a Root -> BLOCK
            b_obj = {
                'name': poly['name'],
                'geometry_type': 'Polygon',
                'children': [],
                'geometry_obj': poly['geometry']
            }
            blocks.append(b_obj)
            block_map[i] = b_obj
        else:
            # This is a Child -> PLOT
            # We don't add to 'plots' list yet, we'll assign them to parents first
            pass

    # --- Step 2: Identify Transects ---
    # All LineStrings are Transects
    transect_objs = []
    for ls in linestrings:
        t_obj = {
            'name': ls['name'],
            'geometry_type': 'LineString',
            'children': [],
            'geometry_obj': ls['geometry']
        }
        transects.append(t_obj)
        transect_objs.append(t_obj)

    # --- Step 3: Assign Transects to Blocks ---
    for t_obj in transect_objs:
        assigned = False
        for b_obj in blocks:
            b_geom = b_obj['geometry_obj']
            t_geom = t_obj['geometry_obj']
            # Intersection is enough (sometimes lines start slightly outside)
            if b_geom.intersects(t_geom):
                b_obj['children'].append({'type': 'transect', 'name': t_obj['name']})
                assigned = True
                break # multiple parents unlikely/unsupported for now
        
        # If valid transect but no block? maybe orphan transect, but keep in main list.
        pass

    # --- Step 4: Assign Plots (Polygon Children) ---
    # We iterate through all polygons again. If it was marked as having a parent, 
    # it is a Plot. We need to decide if it's a child of a Transect OR just the Block.
    
    for i, poly in enumerate(polygons):
        if poly_has_parent[i]:
            # It's a PLOT
            p_obj = {
                'name': poly['name'],
                'geometry_type': 'Polygon',
                'children': [],
                'geometry_obj': poly['geometry']
            }
            plots.append(p_obj)
            
            # Find its Block Parent (Geometrically)
            # (We could just check who is 'i's parent in poly_children, but let's re-verify closest container)
            # Actually, simply checking which Block contains it is safer.
            
            parent_block = None
            for b_obj in blocks:
                if b_obj['geometry_obj'].contains(p_obj['geometry_obj']) or b_obj['geometry_obj'].covers(p_obj['geometry_obj']):
                    parent_block = b_obj
                    break
            
            if parent_block:
                # Now check if it belongs to a Transect within this block
                parent_transect = None
                
                # Filter transects that are children of this block (by name)
                block_transect_names = [c['name'] for c in parent_block['children'] if c['type'] == 'transect']
                
                # Find the actual transect objects
                candidate_transects = [t for t in transect_objs if t['name'] in block_transect_names]
                
                for t in candidate_transects:
                    # Check if Plot intersects Transect (or is very close)
                    if t['geometry_obj'].distance(p_obj['geometry_obj']) < 1e-6 or t['geometry_obj'].intersects(p_obj['geometry_obj']):
                        parent_transect = t
                        break
                
                if parent_transect:
                    # Add to Transect
                    parent_transect['children'].append({'type': 'plot', 'name': p_obj['name']})
                else:
                    # Add directly to Block
                    parent_block['children'].append({'type': 'plot', 'name': p_obj['name']})
            else:
                # Has a parent but we couldn't find a Block root? 
                # This happens if there's deep nesting A->B->C and we only checked Roots.
                # For this specific task, defined 3-level hierarchy is standard.
                orphans.append({'name': p_obj['name'], 'type': 'Polygon'})

    # Clean up output (remove geometry objects)
    def clean(node_list):
        cleaned = []
        for n in node_list:
            item = {k: v for k, v in n.items() if k != 'geometry_obj'}
            # Also clean children to not have full objects if we had them (not applicable here, children are refs)
            cleaned.append(item)
        return cleaned

    return {
        'blocks': clean(blocks),
        'transects': clean(transects),
        'plots': clean(plots),
        'orphans': orphans
    }

def save_geojson(features, output_path):
    from shapely.geometry import mapping
    fc = {
        "type": "FeatureCollection",
        "features": []
    }
    for f in features:
        # Re-construct simple flat list of features for GeoJSON
        # We need to traverse the hierarchy or just use the flat list if we had one.
        # But 'features' input to classify_hierarchy was flat.
        # Wait, I don't have the flat list in main() easily if I only get hierarchy.
        # Let's pass the flat list to this function.
        pass

def export_geojson(flat_features, output_path):
    from shapely.geometry import mapping
    fc = {
        "type": "FeatureCollection",
        "features": []
    }
    for f in flat_features:
        feat = {
            "type": "Feature",
            "properties": {"name": f['name'], "type": f['type']},
            "geometry": mapping(f['geometry'])
        }
        fc["features"].append(feat)
    
    with open(output_path, 'w') as f:
        json.dump(fc, f)

def main():
    parser = argparse.ArgumentParser(description='Extract Ecology Features from KML')
    parser.add_argument('kml_file', help='Path to KML file')
    parser.add_argument('--geojson', help='Path to output GeoJSON file', default=None)
    args = parser.parse_args()
    
    if not os.path.exists(args.kml_file):
        print(json.dumps({'error': 'File not found'}))
        return

    try:
        features = extract_features(args.kml_file)
        if args.geojson:
            export_geojson(features, args.geojson)
            
        hierarchy = classify_hierarchy(features)
        print(json.dumps(hierarchy, indent=2))
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(json.dumps({'error': str(e)}))

if __name__ == '__main__':
    main()
