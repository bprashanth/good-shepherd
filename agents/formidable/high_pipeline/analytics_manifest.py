#!/usr/bin/env python3
"""Create deterministic, read-only distribution summaries from canonical data."""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from collections import Counter
from pathlib import Path

VERSION = "formidable-analytics-v1"
REVIEW_STATUSES = {
    "peer_consensus_disagreement", "disagreement", "majority_after_reread",
    "unresolved_after_reread", "structural_anomaly",
}


def _identifier_like(label):
    """Catch row keys even when a reader omitted the value-kind hint."""
    leaf = str(label or "").rsplit("/", 1)[-1].strip().casefold()
    leaf = re.sub(r"[._-]+", " ", leaf)
    leaf = " ".join(leaf.split())
    return bool(re.fullmatch(
        r"(?:s(?:l)?\s*(?:no|number)|serial(?:\s*(?:no|number))?|"
        r"row(?:\s*(?:no|number|id))?|identifier|timestamp|date|time)",
        leaf,
    ))


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().replace(",", "")
    if not re.fullmatch(r"[-+]?\d+(?:\.\d+)?", text):
        return None
    result = float(text)
    return result if math.isfinite(result) else None


def _quantile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return None
    position = (len(ordered) - 1) * fraction
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _histogram(values, bins=8):
    low, high = min(values), max(values)
    if low == high:
        return [{"x0": low, "x1": high, "count": len(values)}]
    width = (high - low) / bins
    counts = [0] * bins
    for value in values:
        index = min(bins - 1, int((value - low) / width))
        counts[index] += 1
    return [{"x0": round(low + index * width, 6),
             "x1": round(low + (index + 1) * width, 6), "count": count}
            for index, count in enumerate(counts)]


def build(document, ecology=None):
    groups, page_stats = {}, {}
    total, filled = 0, 0
    for page in document.get("pages") or []:
        number = int(page.get("page_number") or 0)
        stats = page_stats.setdefault(number, {"page": number, "cells": 0, "filled": 0,
                                                "disagreements": 0, "ecology_flags": 0})
        for cell in [*(page.get("metadata_fields") or []),
                     *(page.get("free_text_regions") or [])]:
            total += 1
            stats["cells"] += 1
            if str(cell.get("value") or "").strip():
                filled += 1
                stats["filled"] += 1
            if cell.get("status") in REVIEW_STATUSES:
                stats["disagreements"] += 1
            stats["ecology_flags"] += len(cell.get("ecology_flags") or [])
        for table in page.get("tables") or []:
            columns = table.get("columns") or []
            for row in table.get("rows") or []:
                for column, cell in zip(columns, row.get("cells") or []):
                    label = " / ".join(value for value in
                                       (table.get("title"), column.get("parent"), column.get("label"))
                                       if value)
                    key = (table.get("id"), column.get("id"), label,
                           str(column.get("value_kind") or "unknown").casefold())
                    groups.setdefault(key, []).append(cell.get("value"))
                    total += 1
                    stats["cells"] += 1
                    if str(cell.get("value") or "").strip():
                        filled += 1
                        stats["filled"] += 1
                    if cell.get("status") in REVIEW_STATUSES:
                        stats["disagreements"] += 1
                    stats["ecology_flags"] += len(cell.get("ecology_flags") or [])

    charts = []
    for (_table, _column, label, value_kind), raw_values in groups.items():
        # Row keys, dates and timestamps have high cardinality by design; their
        # histograms consume attention without describing the measured system.
        if (value_kind in {"identifier", "serial", "date", "time"}
                or _identifier_like(label)):
            continue
        present = [value for value in raw_values if str(value or "").strip()]
        numeric = [value for value in (_number(item) for item in present) if value is not None]
        if len(numeric) >= 4 and len(numeric) >= 0.75 * len(present):
            charts.append({
                "type": "numeric", "label": label, "n": len(numeric),
                "min": min(numeric), "q1": _quantile(numeric, .25),
                "median": statistics.median(numeric), "q3": _quantile(numeric, .75),
                "max": max(numeric), "histogram": _histogram(numeric),
            })
        elif len(present) >= 4:
            counts = Counter(" ".join(str(value).split()) for value in present)
            charts.append({
                "type": "categorical", "label": label, "n": len(present),
                "values": [{"label": value, "count": count}
                           for value, count in counts.most_common(8)],
                "other": max(0, len(present) - sum(counts[value] for value, _ in counts.most_common(8))),
            })
    charts.sort(key=lambda chart: (-chart["n"], chart["label"].casefold()))
    findings = (ecology or {}).get("findings") or []
    actionable = [finding for finding in findings
                  if finding.get("severity") in {"medium", "high"}]
    return {
        "version": VERSION,
        "policy": "read-only summaries; anomalies are observations, never corrections",
        "summary": {"pages": len(page_stats), "cells": total, "filled": filled,
                    "blank": total - filled, "completeness": round(filled / total, 4) if total else 0,
                    "disagreements": sum(item["disagreements"] for item in page_stats.values()),
                    "ecology_findings": len(actionable),
                    "ecology_information": len(findings) - len(actionable)},
        "pages": list(page_stats.values()), "charts": charts,
        "ecology_findings": findings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("canonical", type=Path)
    parser.add_argument("--ecology", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    document = json.loads(args.canonical.read_text())
    ecology = json.loads(args.ecology.read_text()) if args.ecology else None
    result = build(document, ecology)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(args.output), "summary": result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
