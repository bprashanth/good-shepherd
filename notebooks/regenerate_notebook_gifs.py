#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

FFMPEG_CMD = (
    'for i in *.gif; do ffmpeg -i "$i" -movflags faststart -pix_fmt yuv420p '
    '-vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" "${i%.*}.mp4"; done'
)

# aoi_sieve.ipynb constants
GIF_FPS = 1
AE_CHANGE_THRESHOLD = 0.03
AE_CHANGE_MAX = 0.10
GPW_CHANGE_THRESHOLD_M = 0.5
GPW_DELTA_RANGE_M = 10.0
DW_TREE_THRESHOLD = 0.10
DW_DELTA_RANGE = 0.50
DISPLAY_PERCENTILE_LOW = 2
DISPLAY_PERCENTILE_HIGH = 98
DISPLAY_AE_VMAX_FLOOR = 1e-6
DISPLAY_SYMMETRIC_HALF_FLOOR = 1e-6

# explain_unexplained_optical.ipynb constants
TEXTURE_THRESHOLD = 0.03
SHADOW_THRESHOLD = 0.05
DISTURBANCE_THRESHOLD = 0.10
MOISTURE_STRESS_THRESHOLD = 0.08
VIGOR_CHANGE_THRESHOLD = 0.08
TEXTURE_DELTA_RANGE = 0.15
SHADOW_DELTA_RANGE = 0.30
DISTURBANCE_DELTA_RANGE = 0.30
MOISTURE_DELTA_RANGE = 0.30
VIGOR_DELTA_RANGE = 0.30
DISPLAY_FLOOR = 1e-6
SITE_MARKER_COLOR = "#39ff14"
SITE_MARKER_SIZE = 70


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regenerate GIFs from cached arrays produced by notebook workflows."
    )
    parser.add_argument("--start", type=int, required=True, help="Start year (inclusive).")
    parser.add_argument("--end", type=int, required=True, help="End year (inclusive).")
    parser.add_argument("--out-dir", type=Path, required=True, help="Output directory for GIFs.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("gif_regen_config.json"),
        help="Config file with data source cache and dataset paths.",
    )
    return parser.parse_args()


def resolve_path(value: str, base_dir: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base_dir / path).resolve()


def resolve_runtime_paths(config: Dict[str, object], config_dir: Path) -> Dict[str, Path]:
    cfg_paths = config["paths"]
    preferred_data_root = resolve_path(cfg_paths["preferred_data_root"], config_dir)
    fallback_working_dir = resolve_path(cfg_paths["fallback_working_dir"], config_dir)

    if preferred_data_root.exists():
        data_root = preferred_data_root
        cache_root = resolve_path(cfg_paths["cache_root_when_preferred"], config_dir)
    else:
        data_root = fallback_working_dir
        cache_root = resolve_path(cfg_paths["cache_root_when_fallback"], config_dir)

    phase1_dir = cache_root / cfg_paths["phase1_state_subdir"]
    optical_dir = cache_root / cfg_paths["optical_cache_subdir"]
    db_path = resolve_path(cfg_paths["db_json"], config_dir)

    return {
        "data_root": data_root,
        "cache_root": cache_root,
        "phase1_dir": phase1_dir,
        "optical_dir": optical_dir,
        "db_path": db_path,
    }


def load_json(path: Path):
    return json.loads(path.read_text())


def squeeze_band(arr: np.ndarray) -> np.ndarray:
    return np.squeeze(np.asarray(arr))


def resize_to_shape(arr: np.ndarray, target_shape: Sequence[int]) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    if tuple(arr.shape) == tuple(target_shape):
        return arr
    img = Image.fromarray(arr, mode="F")
    resized = img.resize((target_shape[1], target_shape[0]), resample=Image.BILINEAR)
    return np.asarray(resized, dtype=np.float32)


def mask_below_threshold(arr: np.ndarray, threshold: float) -> np.ndarray:
    arr = np.asarray(arr, dtype=float)
    return np.where(arr > threshold, arr, np.nan)


def mask_abs_below_threshold(arr: np.ndarray, threshold: float) -> np.ndarray:
    arr = np.asarray(arr, dtype=float)
    return np.where(np.abs(arr) > threshold, arr, np.nan)


def display_ae_limits_for_stack(
    arrays: Sequence[np.ndarray],
    vmax_fixed: float,
    pct_high: float,
    vmax_cap: float,
    vmax_floor: float,
) -> Tuple[float, float]:
    valid_parts = []
    for arr in arrays:
        arr = np.asarray(arr, dtype=float)
        valid = arr[np.isfinite(arr)]
        if valid.size:
            valid_parts.append(valid)
    if not valid_parts:
        return 0.0, float(vmax_fixed)
    merged = np.concatenate(valid_parts)
    vmax = min(max(float(np.percentile(merged, pct_high)), vmax_floor), float(vmax_cap))
    return 0.0, vmax


def display_symmetric_limits_for_stack(
    arrays: Sequence[np.ndarray],
    half_range_fixed: float,
    pct_low: float,
    pct_high: float,
    half_cap: float,
    half_floor: float,
) -> Tuple[float, float]:
    valid_parts = []
    for arr in arrays:
        arr = np.asarray(arr, dtype=float)
        valid = arr[np.isfinite(arr)]
        if valid.size:
            valid_parts.append(valid)
    if not valid_parts:
        h = float(half_range_fixed)
        return -h, h
    merged = np.concatenate(valid_parts)
    lo = float(np.percentile(merged, pct_low))
    hi = float(np.percentile(merged, pct_high))
    half = max(abs(lo), abs(hi))
    half = min(max(half, half_floor), float(half_cap))
    return -half, half


def make_threshold_cmap(base_cmap: str, background: str = "#101014"):
    cmap = plt.colormaps[base_cmap].copy()
    cmap.set_bad(background)
    return cmap


def save_gif(frames: Sequence[Image.Image], path: Path, fps: int = GIF_FPS) -> bool:
    if not frames:
        print(f"warning: no frames for {path.name}; skipping")
        return False
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=int(1000 / fps), loop=0)
    print("saved", path)
    return True


def render_cache_dir(template: str, cache_root: Path) -> Path:
    return Path(template.replace("{cache_root}", str(cache_root)))


def load_year_arrays(
    source_key: str,
    years: Iterable[int],
    config: Dict[str, object],
    cache_root: Path,
) -> Tuple[List[int], List[np.ndarray]]:
    source_cfg = config["data_sources"][source_key]
    cache_cfg = source_cfg["cache"]
    dataset_path = source_cfg["dataset_or_asset_path"]
    base_dir = render_cache_dir(cache_cfg["base_dir"], cache_root)
    pattern = cache_cfg["pattern"]

    kept_years: List[int] = []
    arrays: List[np.ndarray] = []
    for year in years:
        cache_path = base_dir / pattern.format(year=year)
        if not cache_path.exists():
            print(
                f"warning: missing cache for '{source_key}' year {year}: {cache_path} "
                f"(dataset/asset: {dataset_path})"
            )
            continue
        arr = squeeze_band(np.load(cache_path))
        kept_years.append(year)
        arrays.append(arr)
    return kept_years, arrays


def load_site_points(db_path: Path) -> List[Tuple[float, float]]:
    records = load_json(db_path)
    unique = {}
    for row in records:
        lat = row.get("latitude")
        lon = row.get("longitude")
        if lat is None or lon is None:
            continue
        key = (float(lon), float(lat))
        unique[key] = key
    return list(unique.values())


def add_optical_overlays(ax, extent: Sequence[float], site_points: Sequence[Tuple[float, float]]) -> None:
    minx, maxx, miny, maxy = extent
    xs = [minx, maxx, maxx, minx, minx]
    ys = [miny, miny, maxy, maxy, miny]
    ax.plot(xs, ys, color="#f5f5f5", linewidth=1.5)
    if site_points:
        xs = [pt[0] for pt in site_points]
        ys = [pt[1] for pt in site_points]
        ax.scatter(xs, ys, marker="x", s=SITE_MARKER_SIZE, c=SITE_MARKER_COLOR, linewidths=1.8)


def build_aoi_frame(
    arr: np.ndarray,
    extent: Sequence[float],
    site_points: Sequence[Tuple[float, float]],
    title: str,
    cmap,
    vmin: float,
    vmax: float,
    legend_lines: Sequence[str],
) -> Image.Image:
    fig = plt.figure(figsize=(11, 8))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 0.34], wspace=0.15)
    ax = fig.add_subplot(gs[0, 0])
    ax_leg = fig.add_subplot(gs[0, 1])
    im = ax.imshow(arr, origin="upper", extent=extent, cmap=cmap, vmin=vmin, vmax=vmax)

    minx, maxx, miny, maxy = extent
    ax.plot([minx, maxx, maxx, minx, minx], [miny, miny, maxy, maxy, miny], color="white", linewidth=0.8)
    if site_points:
        xs = [pt[0] for pt in site_points]
        ys = [pt[1] for pt in site_points]
        ax.scatter(xs, ys, color="yellow", s=20, marker="x")

    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Value")
    ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax_leg.axis("off")
    ax_leg.text(
        0.0,
        1.0,
        "\n".join(["Monitoring sites: yellow x"] + list(legend_lines)),
        va="top",
        ha="left",
        fontsize=10,
        wrap=True,
    )
    fig.tight_layout()
    fig.canvas.draw()
    frame = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3])
    plt.close(fig)
    return frame


def build_optical_frame(
    arr: np.ndarray,
    extent: Sequence[float],
    site_points: Sequence[Tuple[float, float]],
    title: str,
    cmap,
    vmin: float,
    vmax: float,
    cbar_label: str,
    legend_lines: Sequence[str],
) -> Image.Image:
    fig = plt.figure(figsize=(11, 8))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 0.34], wspace=0.15)
    ax = fig.add_subplot(gs[0, 0])
    ax_leg = fig.add_subplot(gs[0, 1])
    im = ax.imshow(arr, origin="upper", extent=extent, cmap=cmap, vmin=vmin, vmax=vmax)
    add_optical_overlays(ax, extent, site_points)
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label(cbar_label)
    ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax_leg.axis("off")
    ax_leg.text(
        0.0,
        1.0,
        "\n\n".join(list(legend_lines) + [f"Colorbar: {vmin:g} to {vmax:g}", "GIF scale fixed across all years"]),
        va="top",
        ha="left",
        fontsize=10,
        wrap=True,
    )
    fig.tight_layout()
    fig.canvas.draw()
    frame = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3])
    plt.close(fig)
    return frame


def regenerate_aoi_gifs(
    years: List[int],
    config: Dict[str, object],
    cache_root: Path,
    out_dir: Path,
    extent: Sequence[float],
    site_points: Sequence[Tuple[float, float]],
) -> List[Path]:
    written: List[Path] = []

    ae_years, ae_arrays = load_year_arrays("alphaearth_change_strength", years, config, cache_root)
    gpw_years, gpw_arrays = load_year_arrays("gpw_height_delta", years, config, cache_root)
    dw_years, dw_arrays = load_year_arrays("dynamic_world_tree_prob_delta", years, config, cache_root)

    ae_masked = [mask_below_threshold(arr, AE_CHANGE_THRESHOLD) for arr in ae_arrays]
    gpw_masked = [mask_abs_below_threshold(arr, GPW_CHANGE_THRESHOLD_M) for arr in gpw_arrays]
    dw_masked = [mask_abs_below_threshold(arr, DW_TREE_THRESHOLD) for arr in dw_arrays]

    _, ae_gif_vmax = display_ae_limits_for_stack(
        ae_masked,
        AE_CHANGE_MAX,
        DISPLAY_PERCENTILE_HIGH,
        AE_CHANGE_MAX,
        DISPLAY_AE_VMAX_FLOOR,
    )
    ae_gif_vmin = AE_CHANGE_THRESHOLD
    gpw_gif_vmin, gpw_gif_vmax = display_symmetric_limits_for_stack(
        gpw_masked,
        GPW_DELTA_RANGE_M,
        DISPLAY_PERCENTILE_LOW,
        DISPLAY_PERCENTILE_HIGH,
        GPW_DELTA_RANGE_M,
        DISPLAY_SYMMETRIC_HALF_FLOOR,
    )
    dw_gif_vmin, dw_gif_vmax = display_symmetric_limits_for_stack(
        dw_masked,
        DW_DELTA_RANGE,
        DISPLAY_PERCENTILE_LOW,
        DISPLAY_PERCENTILE_HIGH,
        DW_DELTA_RANGE,
        DISPLAY_SYMMETRIC_HALF_FLOOR,
    )

    ae_cmap = make_threshold_cmap("inferno", background="#101014")
    gpw_cmap = make_threshold_cmap("RdYlGn", background="#101014")
    dw_cmap = make_threshold_cmap("RdYlGn", background="#101014")

    ae_frames = [
        build_aoi_frame(
            arr,
            extent,
            site_points,
            f"AE change from baseline to {year}",
            ae_cmap,
            ae_gif_vmin,
            ae_gif_vmax,
            [
                f"Colorbar: {ae_gif_vmin:g} to {ae_gif_vmax:g}",
                f"Only AE > {AE_CHANGE_THRESHOLD:g} are colored",
                "Values below threshold are dark background",
                "GIF scale fixed across all years",
            ],
        )
        for year, arr in zip(ae_years, ae_masked)
    ]
    gpw_frames = [
        build_aoi_frame(
            arr,
            extent,
            site_points,
            f"GPW delta from baseline to {year}",
            gpw_cmap,
            gpw_gif_vmin,
            gpw_gif_vmax,
            [
                f"Colorbar: {gpw_gif_vmin:g} to {gpw_gif_vmax:g} m",
                f"Only |GPW| > {GPW_CHANGE_THRESHOLD_M:g} m are colored",
                "Values inside threshold band are dark background",
                "GIF scale fixed across all years",
            ],
        )
        for year, arr in zip(gpw_years, gpw_masked)
    ]
    dw_frames = [
        build_aoi_frame(
            arr,
            extent,
            site_points,
            f"DW delta from baseline to {year}",
            dw_cmap,
            dw_gif_vmin,
            dw_gif_vmax,
            [
                f"Colorbar: {dw_gif_vmin:g} to {dw_gif_vmax:g}",
                f"Only |DW| > {DW_TREE_THRESHOLD:g} are colored",
                "Values inside threshold band are dark background",
                "GIF scale fixed across all years",
            ],
        )
        for year, arr in zip(dw_years, dw_masked)
    ]

    outputs = {
        "ae_change_cumulative.gif": ae_frames,
        "gpw_change_cumulative.gif": gpw_frames,
        "dw_change_cumulative.gif": dw_frames,
    }
    for name, frames in outputs.items():
        path = out_dir / name
        if save_gif(frames, path):
            written.append(path)
    return written


def regenerate_optical_gifs(
    years: List[int],
    config: Dict[str, object],
    cache_root: Path,
    out_dir: Path,
    extent: Sequence[float],
    site_points: Sequence[Tuple[float, float]],
    phase1_shape: Sequence[int],
) -> List[Path]:
    written: List[Path] = []

    texture_years, texture_arrays = load_year_arrays("optical_patchiness_evi_texture", years, config, cache_root)
    shadow_years, shadow_arrays = load_year_arrays("optical_shadow_index", years, config, cache_root)
    nbr_years, nbr_arrays = load_year_arrays("optical_disturbance_nbr", years, config, cache_root)
    ndmi_years, ndmi_arrays = load_year_arrays("optical_moisture_ndmi", years, config, cache_root)
    evi_years, evi_arrays = load_year_arrays("optical_vigor_evi", years, config, cache_root)

    texture_arrays = [resize_to_shape(arr, phase1_shape) for arr in texture_arrays]
    shadow_arrays = [resize_to_shape(arr, phase1_shape) for arr in shadow_arrays]
    nbr_arrays = [resize_to_shape(arr, phase1_shape) for arr in nbr_arrays]
    ndmi_arrays = [resize_to_shape(arr, phase1_shape) for arr in ndmi_arrays]
    evi_arrays = [resize_to_shape(arr, phase1_shape) for arr in evi_arrays]

    texture_masked = [mask_abs_below_threshold(arr, TEXTURE_THRESHOLD) for arr in texture_arrays]
    shadow_masked = [mask_abs_below_threshold(arr, SHADOW_THRESHOLD) for arr in shadow_arrays]
    nbr_masked = [mask_abs_below_threshold(arr, DISTURBANCE_THRESHOLD) for arr in nbr_arrays]
    ndmi_masked = [mask_abs_below_threshold(arr, MOISTURE_STRESS_THRESHOLD) for arr in ndmi_arrays]
    evi_masked = [mask_abs_below_threshold(arr, VIGOR_CHANGE_THRESHOLD) for arr in evi_arrays]

    texture_gif_vmin, texture_gif_vmax = display_symmetric_limits_for_stack(
        texture_masked,
        TEXTURE_DELTA_RANGE,
        DISPLAY_PERCENTILE_LOW,
        DISPLAY_PERCENTILE_HIGH,
        TEXTURE_DELTA_RANGE,
        DISPLAY_FLOOR,
    )
    shadow_gif_vmin, shadow_gif_vmax = display_symmetric_limits_for_stack(
        shadow_masked,
        SHADOW_DELTA_RANGE,
        DISPLAY_PERCENTILE_LOW,
        DISPLAY_PERCENTILE_HIGH,
        SHADOW_DELTA_RANGE,
        DISPLAY_FLOOR,
    )
    nbr_gif_vmin, nbr_gif_vmax = display_symmetric_limits_for_stack(
        nbr_masked,
        DISTURBANCE_DELTA_RANGE,
        DISPLAY_PERCENTILE_LOW,
        DISPLAY_PERCENTILE_HIGH,
        DISTURBANCE_DELTA_RANGE,
        DISPLAY_FLOOR,
    )
    ndmi_gif_vmin, ndmi_gif_vmax = display_symmetric_limits_for_stack(
        ndmi_masked,
        MOISTURE_DELTA_RANGE,
        DISPLAY_PERCENTILE_LOW,
        DISPLAY_PERCENTILE_HIGH,
        MOISTURE_DELTA_RANGE,
        DISPLAY_FLOOR,
    )
    evi_gif_vmin, evi_gif_vmax = display_symmetric_limits_for_stack(
        evi_masked,
        VIGOR_DELTA_RANGE,
        DISPLAY_PERCENTILE_LOW,
        DISPLAY_PERCENTILE_HIGH,
        VIGOR_DELTA_RANGE,
        DISPLAY_FLOOR,
    )

    texture_cmap = make_threshold_cmap("viridis")
    shadow_cmap = make_threshold_cmap("cividis")
    nbr_cmap = make_threshold_cmap("PuOr")
    ndmi_cmap = make_threshold_cmap("BrBG")
    evi_cmap = make_threshold_cmap("RdYlGn")

    texture_frames = [
        build_optical_frame(
            arr,
            extent,
            site_points,
            f"Structural patchiness change from baseline to {year}",
            texture_cmap,
            texture_gif_vmin,
            texture_gif_vmax,
            "Patchiness change (EVI texture delta)",
            [
                "Root variable: local EVI texture",
                f"Only |delta| > {TEXTURE_THRESHOLD:g} are colored",
                "Values inside threshold band are dark background",
            ],
        )
        for year, arr in zip(texture_years, texture_masked)
    ]
    shadow_frames = [
        build_optical_frame(
            arr,
            extent,
            site_points,
            f"Shadow / canopy-closure change from baseline to {year}",
            shadow_cmap,
            shadow_gif_vmin,
            shadow_gif_vmax,
            "Shadow change (shadow index delta)",
            [
                "Root variable: visible-band shadow index",
                f"Only |delta| > {SHADOW_THRESHOLD:g} are colored",
                "Values inside threshold band are dark background",
            ],
        )
        for year, arr in zip(shadow_years, shadow_masked)
    ]
    nbr_frames = [
        build_optical_frame(
            arr,
            extent,
            site_points,
            f"Disturbance signal from baseline to {year}",
            nbr_cmap,
            nbr_gif_vmin,
            nbr_gif_vmax,
            "Disturbance change (NBR delta)",
            [
                "Root variable: NBR",
                f"Only |delta| > {DISTURBANCE_THRESHOLD:g} are colored",
                "Values inside threshold band are dark background",
            ],
        )
        for year, arr in zip(nbr_years, nbr_masked)
    ]
    ndmi_frames = [
        build_optical_frame(
            arr,
            extent,
            site_points,
            f"Canopy moisture change from baseline to {year}",
            ndmi_cmap,
            ndmi_gif_vmin,
            ndmi_gif_vmax,
            "Moisture change (NDMI delta)",
            [
                "Root variable: NDMI",
                f"Only |delta| > {MOISTURE_STRESS_THRESHOLD:g} are colored",
                "Values inside threshold band are dark background",
            ],
        )
        for year, arr in zip(ndmi_years, ndmi_masked)
    ]
    evi_frames = [
        build_optical_frame(
            arr,
            extent,
            site_points,
            f"Photosynthetic vigor change from baseline to {year}",
            evi_cmap,
            evi_gif_vmin,
            evi_gif_vmax,
            "Vigor change (EVI delta)",
            [
                "Root variable: EVI",
                f"Only |delta| > {VIGOR_CHANGE_THRESHOLD:g} are colored",
                "Values inside threshold band are dark background",
            ],
        )
        for year, arr in zip(evi_years, evi_masked)
    ]

    outputs = {
        "patchiness_change_cumulative.gif": texture_frames,
        "shadow_change_cumulative.gif": shadow_frames,
        "disturbance_change_cumulative.gif": nbr_frames,
        "moisture_change_cumulative.gif": ndmi_frames,
        "vigor_change_cumulative.gif": evi_frames,
    }
    for name, frames in outputs.items():
        path = out_dir / name
        if save_gif(frames, path):
            written.append(path)
    return written


def validate_phase1_cache(config: Dict[str, object], cache_root: Path, phase1_dir: Path) -> bool:
    source_cfg = config["data_sources"]["phase1_state"]
    dataset_path = source_cfg["dataset_or_asset_path"]
    required_files = source_cfg["cache"]["required_files"]
    ok = True
    for name in required_files:
        p = phase1_dir / name
        if not p.exists():
            print(
                f"warning: missing cache for 'phase1_state': {p} "
                f"(dataset/asset: {dataset_path})"
            )
            ok = False
    return ok


def main() -> int:
    args = parse_args()
    if args.end < args.start:
        raise SystemExit("--end must be >= --start")

    config_path = args.config.resolve()
    if not config_path.exists():
        raise SystemExit(f"Config file not found: {config_path}")
    config = load_json(config_path)

    runtime_paths = resolve_runtime_paths(config, config_path.parent)
    cache_root = runtime_paths["cache_root"]
    phase1_dir = runtime_paths["phase1_dir"]
    db_path = runtime_paths["db_path"]

    years = list(range(args.start, args.end + 1))
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"using config: {config_path}")
    print(f"cache root: {cache_root}")
    print(f"years: {years[0]}..{years[-1]}")
    print(f"output dir: {out_dir}")

    validate_phase1_cache(config, cache_root, phase1_dir)
    if not db_path.exists():
        print(f"warning: missing asset for 'site_observations_db': {db_path}")

    extent_meta_path = phase1_dir / "phase1_extent.json"
    mask_path = phase1_dir / "phase1_unexplained_mask.npy"
    if not extent_meta_path.exists() or not mask_path.exists():
        raise SystemExit("phase1 extent/mask cache is required to render notebook-equivalent GIFs")

    extent_meta = load_json(extent_meta_path)
    extent = extent_meta["extent"]
    phase1_shape = np.load(mask_path).shape
    site_points = load_site_points(db_path) if db_path.exists() else []

    written: List[Path] = []
    written.extend(regenerate_aoi_gifs(years, config, cache_root, out_dir, extent, site_points))
    written.extend(
        regenerate_optical_gifs(years, config, cache_root, out_dir, extent, site_points, phase1_shape)
    )

    print(f"generated {len(written)} gif(s)")
    for path in written:
        print(f" - {path}")

    print("\nTo convert generated GIFs to MP4:")
    print(FFMPEG_CMD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
