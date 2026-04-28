import argparse
import json
import math
from collections import defaultdict
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def meters_to_lat_deg(meters):
    return meters / 110540.0


def meters_to_lon_deg(meters, lat):
    cos_lat = math.cos(math.radians(lat))
    return meters / (111320.0 * cos_lat if abs(cos_lat) > 1e-8 else 111320.0)


def square_polygon(lon, lat, side_m):
    half = side_m / 2.0
    dlat = meters_to_lat_deg(half)
    dlon = meters_to_lon_deg(half, lat)
    return [
        [
            [lon - dlon, lat - dlat],
            [lon + dlon, lat - dlat],
            [lon + dlon, lat + dlat],
            [lon - dlon, lat + dlat],
            [lon - dlon, lat - dlat],
        ]
    ]


def bounds_polygon(points, pad_m=40):
    lons = [point[0] for point in points]
    lats = [point[1] for point in points]
    center_lat = sum(lats) / len(lats)
    pad_lat = meters_to_lat_deg(pad_m)
    pad_lon = meters_to_lon_deg(pad_m, center_lat)
    min_lon = min(lons) - pad_lon
    max_lon = max(lons) + pad_lon
    min_lat = min(lats) - pad_lat
    max_lat = max(lats) + pad_lat
    return [
        [
            [min_lon, min_lat],
            [max_lon, min_lat],
            [max_lon, max_lat],
            [min_lon, max_lat],
            [min_lon, min_lat],
        ]
    ]


def robust_cluster_points(points):
    if len(points) <= 3:
        return points
    lons = sorted(point[0] for point in points)
    lats = sorted(point[1] for point in points)
    median_lon = lons[len(lons) // 2]
    median_lat = lats[len(lats) // 2]
    distances = []
    for lon, lat in points:
        dx = (lon - median_lon) * 111320.0 * math.cos(math.radians(median_lat))
        dy = (lat - median_lat) * 110540.0
        distances.append(math.hypot(dx, dy))
    sorted_distances = sorted(distances)
    median_distance = sorted_distances[len(sorted_distances) // 2]
    if median_distance <= 0:
        return points
    threshold = max(750.0, median_distance * 4.0)
    clustered = [point for point, distance in zip(points, distances) if distance <= threshold]
    return clustered if len(clustered) >= 3 else points


def main():
    parser = argparse.ArgumentParser(description="Generate setup_wizard_2 experiment.json and features.geojson from Osuri metadata.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--experiment-out", required=True)
    parser.add_argument("--features-out", required=True)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    metadata = load_json(input_dir / "anr_metadata.json")

    plot_boundaries = metadata["plot_boundaries"]
    site_locations = metadata["site_locations"]

    plots_with_coords = [p for p in plot_boundaries if p.get("center_lat") is not None and p.get("center_lon") is not None]
    forests = defaultdict(list)
    classifications = defaultdict(set)
    for plot in plots_with_coords:
        forests[plot["forest_name"]].append(plot)
        classifications[plot["forest_name"]].add(plot.get("classification", "unknown"))

    forest_features = []
    plot_features = []
    subplot_features = []
    point_features = []

    for forest_name, plots in sorted(forests.items()):
        points = [[plot["center_lon"], plot["center_lat"]] for plot in plots]
        polygon_points = robust_cluster_points(points)
        forest_features.append({
            "type": "Feature",
            "properties": {
                "name": forest_name,
                "level": "block",
                "classification_mix": ", ".join(sorted(classifications[forest_name]))
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": bounds_polygon(polygon_points),
            },
        })

    for plot in sorted(plots_with_coords, key=lambda p: p["plot_code"]):
        lon = plot["center_lon"]
        lat = plot["center_lat"]
        plot_code = plot["plot_code"]
        site_name = plot["site_name"]
        forest_name = plot["forest_name"]
        adult_side = plot["adult_tree_plot"]["side_m"]
        sapling_side = plot["sapling_subplot"]["side_m"]

        plot_features.append({
            "type": "Feature",
            "properties": {
                "name": plot_code,
                "level": "plot",
                "forest_name": forest_name,
                "site_name": site_name,
                "classification": plot["classification"],
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": square_polygon(lon, lat, adult_side),
            },
        })

        subplot_features.append({
            "type": "Feature",
            "properties": {
                "name": f"{plot_code}_subplot",
                "level": "subplot",
                "plot_code": plot_code,
                "forest_name": forest_name,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": square_polygon(lon, lat, sapling_side),
            },
        })

        point_features.append({
            "type": "Feature",
            "properties": {
                "name": f"{plot_code}_center",
                "level": "point",
                "plot_code": plot_code,
                "forest_name": forest_name,
            },
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat],
            },
        })

    features_geojson = {
        "type": "FeatureCollection",
        "features": forest_features + plot_features + subplot_features + point_features,
    }

    plot_variables = [indicator["name"] for indicator in metadata["indicators"][:11]]
    subplot_variables = [
        "Sapling density",
        "Sapling native fraction",
        "Sapling species density",
        "Sapling late-successional species density",
    ]

    forest_children = {
        forest_name: sorted([plot["plot_code"] for plot in plots], key=str)
        for forest_name, plots in sorted(forests.items())
    }

    experiment = {
        "metadata": {
            "title": "Osuri Restoration Study Setup",
            "aim": "To summarize how the Osuri rainforest restoration experiment is spatially organized, including forest sites, plot locations, adult-tree plots, nested sapling subplots, and the ecological indicators measured at each plot."
        },
        "hierarchy": {
            "block": {
                "exists": True,
                "name_in_protocol": "Forest Site",
                "description": "Named forest locations that contain restored, naturally regenerating, and benchmark plots in the Osuri study.",
                "datasheet_description": "These site polygons are inferred from the observed plot locations in each named forest because no separate KML exists for the paper.",
                "features": sorted(forests.keys()),
                "children": forest_children,
            },
            "transect": {
                "exists": False,
                "name_in_protocol": "",
                "description": "No explicit transect geometry is described in the paper or encoded in the metadata export.",
                "datasheet_description": "",
                "features": [],
                "children": {},
            },
            "plot": {
                "exists": True,
                "name_in_protocol": "Adult-tree plot",
                "dimensions": "20m x 20m",
                "variables": plot_variables,
                "datasheet_description": "Each plot in the paper is a 20 x 20 m adult-tree plot tied to a known center coordinate and classification.",
                "features": sorted([plot["plot_code"] for plot in plots_with_coords]),
            },
            "subplot": {
                "exists": True,
                "name_in_protocol": "Sapling subplot",
                "dimensions": "5m x 5m nested within each plot",
                "variables": subplot_variables,
            },
        },
    }

    Path(args.experiment_out).write_text(json.dumps(experiment, indent=2), encoding="utf-8")
    Path(args.features_out).write_text(json.dumps(features_geojson, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
