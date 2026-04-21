#!/usr/bin/env python
from __future__ import annotations

import json
import math
import tempfile
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path

import ee
import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.features import geometry_mask
from rasterio.io import MemoryFile
from rasterio.mask import mask
from shapely.geometry import Point, Polygon, mapping
from shapely.ops import transform


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"
GEE_CACHE_PATH = Path("/home/desinotorious/Documents/good_shepherd/anr/osuri_2019/cache/gee_data.json")
ALIENWISE_DIR = Path(__file__).resolve().parents[3] / "alienwise" / "output"
AE_ASSET = "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL"
AE_YEAR_START = "2017-01-01"
AE_YEAR_END = "2017-12-31"
AE_BANDS = [f"A{i:02d}" for i in range(64)]
AE_EXPORT_SCALE_METERS = 150
NODATA = -9999.0

FOCUS_CENTER_LON = 76.99557
FOCUS_CENTER_LAT = 10.35952
FOCUS_RADIUS_M = 2000
UTM_CRS = "EPSG:32643"
SELECTED_PLOT_CENTER_LON = 76.97916666650352
SELECTED_PLOT_CENTER_LAT = 10.3541666665775


def load_json(path: Path):
    return json.loads(path.read_text())


def write_geojson(path: Path, features: list[dict]) -> None:
    payload = {"type": "FeatureCollection", "features": features}
    path.write_text(json.dumps(payload, indent=2))


def quantile(values: np.ndarray, q: float) -> float:
    return float(np.nanquantile(values, q))


def build_focus_aoi() -> shape:
    to_utm = Transformer.from_crs("EPSG:4326", UTM_CRS, always_xy=True).transform
    to_wgs84 = Transformer.from_crs(UTM_CRS, "EPSG:4326", always_xy=True).transform
    center_utm = transform(to_utm, Point(FOCUS_CENTER_LON, FOCUS_CENTER_LAT))
    return transform(to_wgs84, center_utm.buffer(FOCUS_RADIUS_M, resolution=96))


def build_square(center_lon: float, center_lat: float, side_m: float) -> Polygon:
    to_utm = Transformer.from_crs("EPSG:4326", UTM_CRS, always_xy=True).transform
    to_wgs84 = Transformer.from_crs(UTM_CRS, "EPSG:4326", always_xy=True).transform
    center_utm = transform(to_utm, Point(center_lon, center_lat))
    half = side_m / 2.0
    square = Polygon(
        [
            (center_utm.x - half, center_utm.y - half),
            (center_utm.x + half, center_utm.y - half),
            (center_utm.x + half, center_utm.y + half),
            (center_utm.x - half, center_utm.y + half),
            (center_utm.x - half, center_utm.y - half),
        ]
    )
    return transform(to_wgs84, square)


def cosine_similarity(vector: np.ndarray, centroid: np.ndarray) -> float:
    denom = np.linalg.norm(vector) * np.linalg.norm(centroid)
    if denom <= 0:
        return float("nan")
    return float(np.dot(vector, centroid) / denom)


def download_ae_stack(aoi_geom: dict) -> Path:
    ee.Initialize()
    image = (
        ee.ImageCollection(AE_ASSET)
        .filter(ee.Filter.date(AE_YEAR_START, AE_YEAR_END))
        .mosaic()
        .select(AE_BANDS)
        .clip(ee.Geometry(aoi_geom))
    )
    url = image.getDownloadURL(
        {
            "scale": AE_EXPORT_SCALE_METERS,
            "crs": "EPSG:4326",
            "region": aoi_geom,
            "format": "GEO_TIFF",
        }
    )
    blob = urllib.request.urlopen(url).read()
    tmpdir = Path(tempfile.mkdtemp(prefix="ae_stack_"))
    if blob[:2] == b"PK":
        with zipfile.ZipFile(BytesIO(blob)) as zf:
            tif_names = [name for name in zf.namelist() if name.lower().endswith(".tif")]
            if not tif_names:
                raise RuntimeError("Earth Engine download did not contain a GeoTIFF.")
            out_path = tmpdir / Path(tif_names[0]).name
            out_path.write_bytes(zf.read(tif_names[0]))
            return out_path
    out_path = tmpdir / "ae_stack.tif"
    out_path.write_bytes(blob)
    return out_path


def build_similarity_raster(aoi_geom: dict, benchmark_centroid: np.ndarray, benchmark_sites: list[dict]) -> dict:
    stack_path = download_ae_stack(aoi_geom)
    with rasterio.open(stack_path) as src:
        bands = src.read().astype("float32")
        valid_mask = geometry_mask([aoi_geom], transform=src.transform, invert=True, out_shape=(src.height, src.width))
        finite_mask = np.all(np.isfinite(bands), axis=0)
        norms = np.linalg.norm(bands, axis=0)
        denom = norms * np.linalg.norm(benchmark_centroid)
        valid = valid_mask & finite_mask & (denom > 0)

        similarity = np.full((src.height, src.width), NODATA, dtype="float32")
        dot = np.tensordot(benchmark_centroid.astype("float32"), bands, axes=(0, 0))
        similarity[valid] = (dot[valid] / denom[valid]).astype("float32")

        profile = src.profile.copy()
        profile.update({"count": 1, "dtype": "float32", "nodata": NODATA, "compress": "lzw"})
        out_path = OUTPUT_DIR / "ae_similarity.tif"
        with rasterio.open(out_path, "w", **profile) as dst:
            dst.write(similarity, 1)

    valid_values = similarity[similarity > NODATA + 1]
    with rasterio.open(out_path) as src:
        benchmark_scores = []
        for feature in benchmark_sites:
            lon, lat = feature["geometry"]["coordinates"]
            sample = float(next(src.sample([(lon, lat)]))[0])
            if sample > NODATA + 1:
                benchmark_scores.append(sample)

    benchmark_arr = np.array(benchmark_scores, dtype="float32")
    style_max = min(quantile(valid_values, 0.995), quantile(benchmark_arr, 0.10))
    style_min = quantile(valid_values, 0.02)
    style_mid = quantile(valid_values, 0.28)
    if style_mid <= style_min:
        style_mid = (style_min + style_max) / 2.0
    if style_max <= style_mid:
        style_max = max(style_mid + 1e-4, quantile(valid_values, 0.999))

    return {
        "path": out_path.name,
        "stats": {
            "valid_min": float(valid_values.min()),
            "valid_max": float(valid_values.max()),
            "benchmark_p10": quantile(benchmark_arr, 0.10),
        },
        "style": {
            "palette": ["#7f0000", "#d7301f", "#fdae61", "#fee08b", "#66bd63", "#1a9850"],
            "display_min": style_min,
            "display_mid": style_mid,
            "display_max": style_max,
            "gamma": 0.78,
            "nodata": NODATA,
            "description": "Values near benchmark saturate green.",
        },
    }


def build_invasive_probability(aoi_geom: dict) -> dict:
    tif_paths = sorted(ALIENWISE_DIR.glob("*.tif"))
    if not tif_paths:
        raise FileNotFoundError(f"No invasive probability TIFFs found in {ALIENWISE_DIR}")

    arrays = []
    profile = None
    for tif_path in tif_paths:
        with rasterio.open(tif_path) as src:
            arr = src.read(1).astype("float32")
            arr = np.where(arr > -1000, arr, np.nan)
            arrays.append(arr)
            if profile is None:
                profile = src.profile.copy()

    combined = np.nanmax(np.stack(arrays, axis=0), axis=0).astype("float32")
    combined = np.where(np.isfinite(combined), combined, NODATA)

    with MemoryFile() as memfile:
        profile.update({"count": 1, "dtype": "float32", "nodata": NODATA, "compress": "lzw"})
        with memfile.open(**profile) as dataset:
            dataset.write(combined, 1)
            clipped, transform_affine = mask(dataset, [aoi_geom], crop=True, nodata=NODATA)
            clipped_profile = dataset.profile.copy()
            clipped_profile.update(
                {
                    "height": clipped.shape[1],
                    "width": clipped.shape[2],
                    "transform": transform_affine,
                    "compress": "lzw",
                }
            )
        out_path = OUTPUT_DIR / "invasive_probability.tif"
        with rasterio.open(out_path, "w", **clipped_profile) as dst:
            dst.write(clipped)

    valid_values = clipped[0][clipped[0] > NODATA + 1]
    return {
        "path": out_path.name,
        "species_sources": [path.stem for path in tif_paths],
        "stats": {
            "valid_min": float(valid_values.min()),
            "valid_max": float(valid_values.max()),
            "p90": quantile(valid_values, 0.90),
            "p995": quantile(valid_values, 0.995),
        },
        "style": {
            "palette": ["#fff5eb", "#fd8d3c", "#f03b20", "#bd0026", "#67000d"],
            "display_min": quantile(valid_values, 0.90),
            "display_max": quantile(valid_values, 0.995),
            "gamma": 0.85,
            "nodata": NODATA,
            "transparent_below_min": True,
            "description": "Combined invasive probability.",
        },
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sites = load_json(INPUT_DIR / "anr_sites.json")
    gee_cache = load_json(GEE_CACHE_PATH)
    focus_aoi = build_focus_aoi()

    aoi_feature = {
        "type": "Feature",
        "properties": {
            "name": "Focus AOI",
            "source": "curated site-selection subset",
            "radius_m": FOCUS_RADIUS_M,
        },
        "geometry": mapping(focus_aoi),
    }
    write_geojson(OUTPUT_DIR / "aoi.geojson", [aoi_feature])

    focus_rows = [
        row for row in sites["osuri_sites_within_buffer"] if focus_aoi.contains(Point(row["lon"], row["lat"]))
    ]
    benchmark_rows = [row for row in focus_rows if row["classification"] == "benchmark"]

    benchmark_features = [
        {
            "type": "Feature",
            "properties": {
                "name": row["name"],
                "plot_code": row["plot_code"],
                "forest_name": row["forest_name"],
                "classification": row["classification"],
            },
            "geometry": {"type": "Point", "coordinates": [row["lon"], row["lat"]]},
        }
        for row in benchmark_rows
    ]
    write_geojson(OUTPUT_DIR / "benchmark_sites.geojson", benchmark_features)

    records_by_plot = {row["Plot_code"]: row for row in gee_cache if row.get("has_valid_coords")}
    benchmark_vectors = []
    for feature in benchmark_features:
        record = records_by_plot.get(feature["properties"]["plot_code"])
        if not record:
            continue
        ae_vector = record.get("ae_vector") or {}
        vector = np.array([ae_vector.get(band, np.nan) for band in AE_BANDS], dtype="float32")
        if np.isfinite(vector).all():
            benchmark_vectors.append(vector)

    if not benchmark_vectors:
        raise RuntimeError("No valid benchmark vectors found inside the focus AOI.")

    benchmark_centroid = np.mean(np.stack(benchmark_vectors, axis=0), axis=0)
    similarity_layer = build_similarity_raster(mapping(focus_aoi), benchmark_centroid, benchmark_features)
    invasive_layer = build_invasive_probability(mapping(focus_aoi))

    plot_similarity_features = []
    for row in focus_rows:
        record = records_by_plot.get(row["plot_code"])
        if not record:
            continue
        ae_vector = record.get("ae_vector") or {}
        vector = np.array([ae_vector.get(band, np.nan) for band in AE_BANDS], dtype="float32")
        if not np.isfinite(vector).all():
            continue
        score = cosine_similarity(vector, benchmark_centroid)
        if not math.isfinite(score):
            continue
        plot_similarity_features.append(
            {
                "type": "Feature",
                "properties": {
                    "plot_code": row["plot_code"],
                    "forest_name": row["forest_name"],
                    "classification": row["classification"],
                    "ae_cosine_to_benchmark": score,
                },
                "geometry": {"type": "Point", "coordinates": [row["lon"], row["lat"]]},
            }
        )
    write_geojson(OUTPUT_DIR / "plot_similarity.geojson", plot_similarity_features)

    with rasterio.open(OUTPUT_DIR / invasive_layer["path"]) as src:
        candidate_features = []
        for feature in plot_similarity_features:
            if feature["properties"]["classification"] == "benchmark":
                continue
            lon, lat = feature["geometry"]["coordinates"]
            invasive_prob = float(next(src.sample([(lon, lat)]))[0])
            if invasive_prob <= NODATA + 1:
                invasive_prob = float("nan")
            props = feature["properties"].copy()
            props["invasive_probability"] = invasive_prob
            candidate_features.append({"type": "Feature", "properties": props, "geometry": feature["geometry"]})

    sim_values = np.array([f["properties"]["ae_cosine_to_benchmark"] for f in candidate_features], dtype="float32")
    inv_values = np.array(
        [f["properties"]["invasive_probability"] for f in candidate_features if math.isfinite(f["properties"]["invasive_probability"])],
        dtype="float32",
    )
    sim_min = float(sim_values.min())
    sim_max = float(sim_values.max())
    inv_min = float(inv_values.min()) if inv_values.size else 0.0
    inv_max = float(inv_values.max()) if inv_values.size and inv_values.max() > inv_min else inv_min + 1.0

    for feature in candidate_features:
        sim = feature["properties"]["ae_cosine_to_benchmark"]
        inv = feature["properties"]["invasive_probability"]
        anti_benchmark = 1.0 - ((sim - sim_min) / (sim_max - sim_min if sim_max > sim_min else 1.0))
        anti_benchmark = max(0.0, min(1.0, anti_benchmark))
        invasive_score = 0.0 if not math.isfinite(inv) else (inv - inv_min) / (inv_max - inv_min)
        invasive_score = max(0.0, min(1.0, invasive_score))
        feature["properties"]["suggestion_score"] = 0.65 * anti_benchmark + 0.35 * invasive_score

    candidate_features.sort(key=lambda feature: feature["properties"]["suggestion_score"], reverse=True)
    suggestions = candidate_features[:8]
    write_geojson(OUTPUT_DIR / "suggestions.geojson", suggestions)

    selected_adult = build_square(SELECTED_PLOT_CENTER_LON, SELECTED_PLOT_CENTER_LAT, 20.0)
    selected_subplot = build_square(SELECTED_PLOT_CENTER_LON, SELECTED_PLOT_CENTER_LAT, 5.0)
    with rasterio.open(OUTPUT_DIR / similarity_layer["path"]) as sim_src, rasterio.open(OUTPUT_DIR / invasive_layer["path"]) as inv_src:
        selected_plot_score = float(next(sim_src.sample([(SELECTED_PLOT_CENTER_LON, SELECTED_PLOT_CENTER_LAT)]))[0])
        selected_invasive_probability = float(next(inv_src.sample([(SELECTED_PLOT_CENTER_LON, SELECTED_PLOT_CENTER_LAT)]))[0])
    selected_anti_benchmark = 1.0 - (
        (selected_plot_score - sim_min) / (sim_max - sim_min if sim_max > sim_min else 1.0)
    )
    selected_anti_benchmark = max(0.0, min(1.0, selected_anti_benchmark))
    selected_invasive_score = 0.0 if not math.isfinite(selected_invasive_probability) else (
        (selected_invasive_probability - inv_min) / (inv_max - inv_min)
    )
    selected_invasive_score = max(0.0, min(1.0, selected_invasive_score))
    selected_suggestion_score = 0.65 * selected_anti_benchmark + 0.35 * selected_invasive_score
    selected_plot = {
        "plot_id": "stack_focus_selected_plot",
        "name": "Focus suggestion plot",
        "center": {"lon": SELECTED_PLOT_CENTER_LON, "lat": SELECTED_PLOT_CENTER_LAT},
        "adult_tree_plot": {"shape": "square_plot", "side_m": 20.0, "geometry": mapping(selected_adult)},
        "sapling_subplot": {"shape": "square_plot", "side_m": 5.0, "geometry": mapping(selected_subplot)},
        "ae_cosine_to_benchmark": selected_plot_score,
        "invasive_probability": selected_invasive_probability,
        "suggestion_score": selected_suggestion_score,
        "reason": "Handpicked southwest hotspot inside the focus AOI where invasive probability is high.",
        "stage_source": "site_selection",
    }
    (OUTPUT_DIR / "selected_plot.json").write_text(json.dumps(selected_plot, indent=2))
    write_geojson(
        OUTPUT_DIR / "selected_plot.geojson",
        [
            {
                "type": "Feature",
                "properties": {
                    "name": selected_plot["name"],
                    "plot_id": selected_plot["plot_id"],
                    "role": "adult_tree_plot",
                    "side_m": 20.0,
                },
                "geometry": mapping(selected_adult),
            },
            {
                "type": "Feature",
                "properties": {
                    "name": selected_plot["name"],
                    "plot_id": selected_plot["plot_id"],
                    "role": "sapling_subplot",
                    "side_m": 5.0,
                },
                "geometry": mapping(selected_subplot),
            },
            {
                "type": "Feature",
                "properties": {
                    "name": selected_plot["name"],
                    "plot_id": selected_plot["plot_id"],
                    "role": "center",
                    "ae_cosine_to_benchmark": selected_plot_score,
                    "invasive_probability": selected_invasive_probability,
                    "suggestion_score": selected_suggestion_score,
                },
                "geometry": {"type": "Point", "coordinates": [SELECTED_PLOT_CENTER_LON, SELECTED_PLOT_CENTER_LAT]},
            },
        ],
    )

    with rasterio.open(OUTPUT_DIR / similarity_layer["path"]) as src:
        bounds = src.bounds

    layers = {
        "aoi": {
            "path": "aoi.geojson",
            "bounds": [bounds.left, bounds.bottom, bounds.right, bounds.top],
        },
        "benchmark_sites": {"path": "benchmark_sites.geojson", "count": len(benchmark_features)},
        "suggestions": {"path": "suggestions.geojson", "count": len(suggestions)},
        "selected_plot": {
            "path": "selected_plot.geojson",
            "json_path": "selected_plot.json",
            "center": [SELECTED_PLOT_CENTER_LON, SELECTED_PLOT_CENTER_LAT],
        },
        "layers": {
            "benchmark_similarity": similarity_layer,
            "invasive_probability": invasive_layer,
        },
        "assumptions": {
            "focus_aoi_center": [FOCUS_CENTER_LON, FOCUS_CENTER_LAT],
            "focus_aoi_radius_m": FOCUS_RADIUS_M,
            "selected_plot_center": [SELECTED_PLOT_CENTER_LON, SELECTED_PLOT_CENTER_LAT],
            "similarity_metric": "cosine similarity to benchmark centroid",
            "invasive_combination_rule": "pixelwise max across bundled invasive TIFFs",
        },
    }
    (OUTPUT_DIR / "layers.json").write_text(json.dumps(layers, indent=2))


if __name__ == "__main__":
    main()
