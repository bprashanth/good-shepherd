#!/usr/bin/env python3
"""Download NCF India CSV assets and build source/species lookup files."""

from __future__ import annotations

import csv
import json
import math
import re
import string
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


BASE_DIR = Path(__file__).resolve().parent
RECORDS_PATH = BASE_DIR / "ncfindia_all_records.json"
OUTPUT_DATA_DIR = BASE_DIR / "ncfindia"
SOURCE_LOOKUP_PATH = BASE_DIR / "source_lookup.json"
CSV_PAPER_LOOKUP_PATH = BASE_DIR / "csv_paper_lookup.json"
SPECIES_OCCURRENCES_PATH = BASE_DIR / "species_occurrences.json"


def slugify(text: str, max_len: int = 80) -> str:
    value = re.sub(r"\bdata from\b[: ]*", "", text, flags=re.IGNORECASE)
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    if not value:
        value = "untitled_paper"
    if len(value) > max_len:
        value = value[:max_len].rstrip("_")
    return value


def normalize_header(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def tokenize_header(name: str) -> List[str]:
    return [token for token in re.split(r"[^a-z0-9]+", name.lower()) if token]


def parse_year(pub_date: str) -> str:
    match = re.search(r"(19|20)\d{2}", pub_date or "")
    if match:
        return match.group(0)
    return "0000"


def first_author_last_name(record: dict) -> str:
    creators = (record.get("metadata") or {}).get("creators") or []
    if creators and isinstance(creators, list):
        name = str((creators[0] or {}).get("name", "paper"))
    else:
        name = "paper"
    # Usually "Last, First", fallback to trailing token.
    if "," in name:
        last = name.split(",", 1)[0]
    else:
        parts = name.split()
        last = parts[-1] if parts else "paper"
    last = re.sub(r"[^a-zA-Z]", "", last).lower()
    return last or "paper"


def build_source_id(record: dict, used: Dict[str, int]) -> str:
    last = first_author_last_name(record)[:6]
    year = parse_year(str(record.get("created") or record.get("modified") or ""))
    base = f"{last}{year}"
    # Reserve at most 2 suffix chars so id stays <= 12.
    base = base[:10]
    count = used[base]
    if count == 0:
        candidate = base
    else:
        alpha = string.ascii_lowercase
        suffix = ""
        n = count
        while True:
            suffix = alpha[n % 26] + suffix
            n = n // 26 - 1
            if n < 0:
                break
        suffix = suffix[:2]
        candidate = f"{base[:12-len(suffix)]}{suffix}"
    used[base] += 1
    return candidate[:12]


def csv_files_from_record(record: dict) -> List[dict]:
    files = record.get("files") or []
    out = []
    for file_obj in files:
        key = str(file_obj.get("key", ""))
        if key.lower().endswith(".csv"):
            out.append(file_obj)
    return out


def download_file(url: str, destination: Path) -> Tuple[bool, Optional[str]]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 0:
        return False, None

    if not url:
        return False, "Missing file URL"

    if url.startswith("/"):
        url = urllib.parse.urljoin("https://zenodo.org", url)
    parsed = urllib.parse.urlsplit(url)
    safe_path = urllib.parse.quote(parsed.path, safe="/%")
    url = urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, safe_path, parsed.query, parsed.fragment)
    )

    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read()
        destination.write_bytes(data)
        return True, None
    except urllib.error.URLError as exc:
        return False, str(exc)


def detect_column(
    headers: List[str], candidates: List[str], allow_contains: bool = False
) -> Optional[str]:
    normalized_map = {normalize_header(h): h for h in headers}
    for candidate in candidates:
        if candidate in normalized_map:
            return normalized_map[candidate]

    token_map = {h: set(tokenize_header(h)) for h in headers}
    for candidate in candidates:
        for header, tokens in token_map.items():
            if candidate in tokens:
                return header

    # Loose fallback is only safe for semantic columns (species/timestamp),
    # not coordinates where short fragments (e.g. "lon") can create false matches.
    if allow_contains:
        for normalized, original in normalized_map.items():
            for candidate in candidates:
                if len(candidate) >= 4 and candidate in normalized:
                    return original
    return None


def parse_float(value: str) -> Optional[float]:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * radius_km * math.asin(math.sqrt(a))


def convex_hull(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    # Points are (lon, lat). Monotonic chain, returns hull without duplicate endpoint.
    unique = sorted(set(points))
    if len(unique) <= 1:
        return unique

    def cross(
        o: Tuple[float, float], a: Tuple[float, float], b: Tuple[float, float]
    ) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: List[Tuple[float, float]] = []
    for p in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper: List[Tuple[float, float]] = []
    for p in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    return lower[:-1] + upper[:-1]


def compute_net_bounds(points_latlon: List[Tuple[float, float]]) -> Optional[dict]:
    if not points_latlon:
        return None

    lats = [p[0] for p in points_latlon]
    lons = [p[1] for p in points_latlon]
    hull_lonlat = convex_hull([(lon, lat) for lat, lon in points_latlon])

    if len(hull_lonlat) == 1:
        perimeter_km = 0.0
    elif len(hull_lonlat) == 2:
        lat1, lon1 = hull_lonlat[0][1], hull_lonlat[0][0]
        lat2, lon2 = hull_lonlat[1][1], hull_lonlat[1][0]
        perimeter_km = 2 * haversine_km(lat1, lon1, lat2, lon2)
    else:
        perimeter_km = 0.0
        for i in range(len(hull_lonlat)):
            curr = hull_lonlat[i]
            nxt = hull_lonlat[(i + 1) % len(hull_lonlat)]
            perimeter_km += haversine_km(curr[1], curr[0], nxt[1], nxt[0])

    return {
        "point_count": len(points_latlon),
        "bbox": {
            "min_lat": min(lats),
            "max_lat": max(lats),
            "min_lon": min(lons),
            "max_lon": max(lons),
        },
        # "Circumference" requested: perimeter of convex hull (km).
        "hull_perimeter_km": perimeter_km,
        "hull": [{"lat": lat, "lon": lon} for lon, lat in hull_lonlat],
    }


@dataclass
class SpeciesExtractionResult:
    total_rows: int
    matched_rows: int
    geospatial_rows: int
    species_column: Optional[str]
    lat_column: Optional[str]
    lon_column: Optional[str]
    timestamp_column: Optional[str]


def extract_species_rows(
    csv_path: Path,
    source_id: str,
    occurrences: List[dict],
    source_points: List[Tuple[float, float]],
) -> SpeciesExtractionResult:
    headers: List[str] = []
    total_rows = 0
    matched_rows = 0
    species_col = None
    lat_col = None
    lon_col = None
    timestamp_col = None

    species_candidates = [
        "species",
        "speciesname",
        "scientificname",
        "scientificnameauthorship",
        "commonname",
        "vernacularname",
        "taxon",
        "taxonname",
        "speciesmatched",
    ]
    lat_candidates = ["latitude", "lat", "decimallatitude", "y"]
    lon_candidates = [
        "longitude",
        "lon",
        "lng",
        "long",
        "decimallongitude",
        "longgps",
        "x",
    ]
    timestamp_candidates = [
        "eventdate",
        "timestamp",
        "datetime",
        "date",
        "observationdate",
        "observedon",
        "time",
    ]

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                return SpeciesExtractionResult(0, 0, 0, None, None, None, None)
            headers = [h for h in reader.fieldnames if h is not None]
            species_col = detect_column(headers, species_candidates, allow_contains=True)
            lat_col = detect_column(headers, lat_candidates, allow_contains=False)
            lon_col = detect_column(headers, lon_candidates, allow_contains=False)
            timestamp_col = detect_column(
                headers, timestamp_candidates, allow_contains=True
            )
            if not lat_col or not lon_col:
                return SpeciesExtractionResult(
                    0, 0, 0, species_col, lat_col, lon_col, timestamp_col
                )

            geospatial_rows = 0
            for row_idx, row in enumerate(reader, start=1):
                total_rows += 1
                lat = parse_float(row.get(lat_col, ""))
                lon = parse_float(row.get(lon_col, ""))
                if lat is None or lon is None:
                    continue
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    continue
                geospatial_rows += 1
                source_points.append((lat, lon))

                if not species_col:
                    continue
                species = str(row.get(species_col, "")).strip()
                if not species:
                    continue
                # Avoid numeric or coded values from wide-form matrices.
                if not re.search(r"[A-Za-z]", species):
                    continue

                timestamp_value = None
                if timestamp_col:
                    raw_ts = row.get(timestamp_col, "")
                    if raw_ts is not None:
                        raw_ts = str(raw_ts).strip()
                        timestamp_value = raw_ts or None
                occurrences.append(
                    {
                        "species": species,
                        "lat": lat,
                        "lon": lon,
                        "timestamp": timestamp_value,
                        "source": source_id,
                        "csv_file": str(csv_path.relative_to(BASE_DIR)),
                        "row": row_idx,
                    }
                )
                matched_rows += 1
    except UnicodeDecodeError:
        # Skip unusual encodings for now.
        return SpeciesExtractionResult(
            total_rows, matched_rows, 0, species_col, lat_col, lon_col, timestamp_col
        )
    except csv.Error:
        return SpeciesExtractionResult(
            total_rows, matched_rows, 0, species_col, lat_col, lon_col, timestamp_col
        )

    return SpeciesExtractionResult(
        total_rows,
        matched_rows,
        geospatial_rows,
        species_col,
        lat_col,
        lon_col,
        timestamp_col,
    )


def main() -> None:
    records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
    used_source_bases: Dict[str, int] = defaultdict(int)

    source_lookup: Dict[str, dict] = {}
    csv_entries: List[dict] = []
    species_occurrences: List[dict] = []
    source_points_map: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
    failed_downloads: List[dict] = []
    downloaded_count = 0
    skipped_existing_count = 0

    for record in records:
        csv_files = csv_files_from_record(record)
        if not csv_files:
            continue

        metadata = record.get("metadata") or {}
        title = str(record.get("title") or metadata.get("title") or "Untitled paper")
        paper_slug = slugify(title)
        source_id = build_source_id(record, used_source_bases)
        record_id = record.get("id")
        recid = record.get("recid")
        doi = record.get("doi")

        source_lookup[source_id] = {
            "title": title,
            "paper_slug": paper_slug,
            "zenodo_id": recid,
            "record_id": record_id,
            "doi": doi,
            "doi_url": record.get("doi_url"),
            "publication_date": record.get("created"),
            "first_author": first_author_last_name(record),
        }

        paper_dir = OUTPUT_DATA_DIR / paper_slug / "inputs"
        for file_obj in csv_files:
            key = str(file_obj.get("key"))
            file_url = ((file_obj.get("links") or {}).get("self")) or ""
            destination = paper_dir / key

            downloaded, err = download_file(file_url, destination)
            if err:
                failed_downloads.append(
                    {
                        "source": source_id,
                        "title": title,
                        "csv_key": key,
                        "url": file_url,
                        "error": err,
                    }
                )
                continue

            if downloaded:
                downloaded_count += 1
            else:
                skipped_existing_count += 1

            extraction = extract_species_rows(
                destination,
                source_id,
                species_occurrences,
                source_points_map[source_id],
            )
            csv_entries.append(
                {
                    "source": source_id,
                    "title": title,
                    "paper_slug": paper_slug,
                    "zenodo_id": recid,
                    "doi": doi,
                    "csv_key": key,
                    "csv_path": str(destination.relative_to(BASE_DIR)),
                    "csv_url": file_url,
                    "downloaded_now": downloaded,
                    "species_column": extraction.species_column,
                    "lat_column": extraction.lat_column,
                    "lon_column": extraction.lon_column,
                    "timestamp_column": extraction.timestamp_column,
                    "geospatial_rows": extraction.geospatial_rows,
                    "species_rows_extracted": extraction.matched_rows,
                    "rows_scanned": extraction.total_rows,
                }
            )

    source_bounds = {
        source_id: compute_net_bounds(points)
        for source_id, points in source_points_map.items()
        if points
    }
    for entry in csv_entries:
        entry["net_bounds"] = source_bounds.get(entry["source"])

    SOURCE_LOOKUP_PATH.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "count": len(source_lookup),
                "sources": source_lookup,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    CSV_PAPER_LOOKUP_PATH.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "count": len(csv_entries),
                "source_bounds": source_bounds,
                "entries": csv_entries,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    SPECIES_OCCURRENCES_PATH.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "count": len(species_occurrences),
                "entries": species_occurrences,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Records scanned: {len(records)}")
    print(f"Sources with CSVs: {len(source_lookup)}")
    print(f"CSV entries indexed: {len(csv_entries)}")
    print(f"Downloaded now: {downloaded_count}")
    print(f"Already present (skipped): {skipped_existing_count}")
    print(f"Species occurrences extracted: {len(species_occurrences)}")
    print(f"Failed downloads: {len(failed_downloads)}")
    errors_path = BASE_DIR / "failed_csv_downloads.json"
    if failed_downloads:
        errors_path.write_text(
            json.dumps(
                {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "count": len(failed_downloads),
                    "entries": failed_downloads,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"Failure details written to: {errors_path.relative_to(BASE_DIR)}")
    elif errors_path.exists():
        errors_path.unlink()


if __name__ == "__main__":
    main()
