#!/usr/bin/env python3
"""Validate species_occurrences rows against source CSV files."""

from __future__ import annotations

import csv
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parent
SPECIES_OCCURRENCES_PATH = BASE_DIR / "species_occurrences.json"
REPORT_PATH = BASE_DIR / "species_occurrences_verification.json"


def normalize_header(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def parse_float(value: object) -> Optional[float]:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def float_equal(a: float, b: float, tol: float = 1e-7) -> bool:
    return math.isclose(a, b, rel_tol=0.0, abs_tol=tol)


def matching_column(row: dict, candidates: List[str], expected: object) -> Optional[str]:
    if expected is None:
        return None
    normalized = {normalize_header(k): k for k in row.keys()}
    for candidate in candidates:
        key = normalized.get(candidate)
        if key is None:
            continue
        value = row.get(key)
        if isinstance(expected, float):
            parsed = parse_float(value)
            if parsed is not None and float_equal(parsed, expected):
                return key
        else:
            if str(value).strip() == str(expected):
                return key
    return None


def value_exists_anywhere(row: dict, expected: object) -> bool:
    if expected is None:
        return True
    needle = str(expected).strip()
    for value in row.values():
        if str(value).strip() == needle:
            return True
    return False


def row_at(csv_path: Path, row_num: int) -> Optional[dict]:
    # species_occurrences row is 1-indexed data row (excluding header).
    if row_num < 1:
        return None
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(reader, start=1):
            if idx == row_num:
                return row
    return None


@dataclass
class Failure:
    index: int
    reason: str
    source: str
    csv_file: str
    row: int
    species: str
    lat: float
    lon: float

    def as_dict(self) -> dict:
        return {
            "index": self.index,
            "reason": self.reason,
            "source": self.source,
            "csv_file": self.csv_file,
            "row": self.row,
            "species": self.species,
            "lat": self.lat,
            "lon": self.lon,
        }


def main() -> None:
    payload = json.loads(SPECIES_OCCURRENCES_PATH.read_text(encoding="utf-8"))
    entries = payload.get("entries") or []

    species_candidates = [
        "species",
        "speciesname",
        "scientificname",
        "commonname",
        "vernacularname",
        "taxon",
        "taxonname",
        "speciesmatched",
    ]
    lat_candidates = ["latitude", "lat", "decimallatitude", "latgps", "y"]
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

    failures: List[Failure] = []
    per_source_counts: Dict[str, int] = defaultdict(int)

    for idx, entry in enumerate(entries, start=1):
        csv_rel = entry.get("csv_file")
        csv_path = BASE_DIR / str(csv_rel)
        if not csv_path.exists():
            failures.append(
                Failure(
                    index=idx,
                    reason="csv_file_missing",
                    source=str(entry.get("source")),
                    csv_file=str(csv_rel),
                    row=int(entry.get("row", -1)),
                    species=str(entry.get("species")),
                    lat=float(entry.get("lat")),
                    lon=float(entry.get("lon")),
                )
            )
            continue

        row_num = int(entry.get("row", -1))
        row = row_at(csv_path, row_num)
        if row is None:
            failures.append(
                Failure(
                    index=idx,
                    reason="row_not_found",
                    source=str(entry.get("source")),
                    csv_file=str(csv_rel),
                    row=row_num,
                    species=str(entry.get("species")),
                    lat=float(entry.get("lat")),
                    lon=float(entry.get("lon")),
                )
            )
            continue

        species_value = str(entry.get("species"))
        lat_value = float(entry.get("lat"))
        lon_value = float(entry.get("lon"))
        timestamp_value = entry.get("timestamp")

        species_col = matching_column(row, species_candidates, species_value)
        lat_col = matching_column(row, lat_candidates, lat_value)
        lon_col = matching_column(row, lon_candidates, lon_value)
        ts_col = matching_column(row, timestamp_candidates, timestamp_value)

        if species_col is None:
            failures.append(
                Failure(
                    index=idx,
                    reason="species_value_not_found_in_row",
                    source=str(entry.get("source")),
                    csv_file=str(csv_rel),
                    row=row_num,
                    species=species_value,
                    lat=lat_value,
                    lon=lon_value,
                )
            )
            continue
        if lat_col is None:
            failures.append(
                Failure(
                    index=idx,
                    reason="lat_value_not_found_in_row",
                    source=str(entry.get("source")),
                    csv_file=str(csv_rel),
                    row=row_num,
                    species=species_value,
                    lat=lat_value,
                    lon=lon_value,
                )
            )
            continue
        if lon_col is None:
            failures.append(
                Failure(
                    index=idx,
                    reason="lon_value_not_found_in_row",
                    source=str(entry.get("source")),
                    csv_file=str(csv_rel),
                    row=row_num,
                    species=species_value,
                    lat=lat_value,
                    lon=lon_value,
                )
            )
            continue
        if timestamp_value is not None and ts_col is None:
            if value_exists_anywhere(row, timestamp_value):
                ts_col = "__any__"
        if timestamp_value is not None and ts_col is None:
            failures.append(
                Failure(
                    index=idx,
                    reason="timestamp_value_not_found_in_row",
                    source=str(entry.get("source")),
                    csv_file=str(csv_rel),
                    row=row_num,
                    species=species_value,
                    lat=lat_value,
                    lon=lon_value,
                )
            )
            continue

        per_source_counts[str(entry.get("source"))] += 1

    report = {
        "total_entries_checked": len(entries),
        "passed": len(entries) - len(failures),
        "failed": len(failures),
        "per_source_passed": dict(sorted(per_source_counts.items())),
        "failures": [f.as_dict() for f in failures[:1000]],
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"Total checked: {report['total_entries_checked']}")
    print(f"Passed: {report['passed']}")
    print(f"Failed: {report['failed']}")
    print(f"Report: {REPORT_PATH.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
