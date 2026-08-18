#!/usr/bin/env python3
"""Build a provenance-preserving review contract from extraction artifacts.

The presented value always comes from the primary literal reader. Peer readers
and ecology stages can add alternatives or findings but never overwrite it.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any


VERSION = "formidable-review-v1"
REVIEW_STATUSES = {
    "peer_consensus_disagreement", "disagreement", "majority_after_reread",
    "unresolved_after_reread", "structural_anomaly",
}


def norm(value: Any) -> str:
    text = "" if value is None else " ".join(str(value).strip().split()).casefold()
    if not text:
        return ""
    try:
        number = float(text)
        return str(int(number)) if math.isfinite(number) and number.is_integer() else str(number)
    except ValueError:
        return text


def decisions(directory: Path) -> dict[str, dict[str, Any]]:
    result = {}
    for path in sorted(directory.glob("batch_*.json")):
        if path.name.endswith((".meta.json", ".targets.json")):
            continue
        for cell in json.loads(path.read_text()).get("cells") or []:
            if cell.get("cell_id") is not None:
                result[str(cell["cell_id"])] = cell
    return result


def targets(directory: Path, decision_map: dict[str, dict[str, Any]]):
    result = {}
    for path in sorted(directory.glob("batch_*.targets.json")):
        for item in json.loads(path.read_text()):
            result[str(item["cell_id"])] = {**item, "targets_file": path.name}
    if not result:
        result = {cell_id: {"cell_id": cell_id} for cell_id in decision_map}
    return result


def _coordinate(cell_id):
    match = re.fullmatch(r"r(\d+)_c(\d+)", cell_id)
    if not match:
        return {"source_cell_id": cell_id}
    return {"source_cell_id": cell_id,
            "xlsx_row": int(match.group(1)) + 1,
            "xlsx_column": int(match.group(2)) + 1}


def _bbox(target):
    raw = target.get("bbox_1000")
    if not isinstance(raw, list) or len(raw) != 4:
        return None
    return [round(float(value) / 1000, 4) for value in raw]


def _run_metadata(directory):
    path = directory / "run.json"
    if not path.exists():
        return {"tag": directory.name, "model": directory.name,
                "cost_usd": None, "latency_s": None}
    run = json.loads(path.read_text())
    return {key: run.get(key) for key in
            ("tag", "provider", "model", "mode", "cost_usd", "latency_s")}


def from_template(primary_dir: Path, peer_dir: Path | None = None,
                  *, route: dict[str, Any] | None = None):
    primary = decisions(primary_dir)
    peer = decisions(peer_dir) if peer_dir else {}
    target_map = targets(primary_dir, primary)
    primary_meta = _run_metadata(primary_dir)
    peer_meta = _run_metadata(peer_dir) if peer_dir else None
    cells, attention = [], []
    for cell_id in sorted(target_map, key=lambda item: tuple(
            int(x) for x in re.findall(r"\d+", item)) or (10**9,)):
        target = target_map[cell_id]
        first = primary.get(cell_id) or {}
        second = peer.get(cell_id) or {}
        first_value, second_value = first.get("value"), second.get("value")
        has_peer = peer_dir is not None
        agrees = has_peer and norm(first_value) == norm(second_value)
        confidence = float(first.get("confidence") or 0.0)
        if has_peer and not agrees:
            status, priority, reason = "reader_disagreement", "high", "literal readers disagree"
        elif confidence <= 0.80:
            status, priority, reason = "low_confidence", "medium", "primary confidence at or below 0.80"
        else:
            status = "reader_agreement" if has_peer else "single_reader"
            priority = reason = None
        item = {
            "id": cell_id, "page": 1, **_coordinate(cell_id),
            "bbox": _bbox(target), "context": target.get("context"),
            "presented_value": first_value,
            "primary": {
                "value": first_value, "confidence": confidence,
                "evidence": first.get("evidence"), "model": primary_meta.get("model"),
            },
            "peer": ({"value": second_value,
                       "confidence": float(second.get("confidence") or 0.0),
                       "evidence": second.get("evidence"),
                       "model": peer_meta.get("model")}
                      if has_peer else None),
            "status": status, "review_priority": priority,
            "alternatives": ([second_value] if has_peer and not agrees else []),
            "policy": "primary literal value retained; alternatives are never auto-applied",
        }
        cells.append(item)
        if priority:
            attention.append({"cell_id": cell_id, "page": 1, "bbox": item["bbox"],
                              "priority": priority, "reason": reason,
                              "presented_value": first_value,
                              "alternatives": item["alternatives"]})
    disagreements = sum(item["status"] == "reader_disagreement" for item in cells)
    low_confidence = sum(item["status"] == "low_confidence" for item in cells)
    return {
        "version": VERSION,
        "route": route or {"status": "known_template", "evidence": "caller supplied"},
        "policy": {
            "literal_transcription_is_immutable": True,
            "peer_readers_select_review_regions_not_replacements": True,
            "ecology_suggestions_are_separate": True,
        },
        "readers": {"primary": primary_meta, "peer": peer_meta},
        "summary": {"target_cells_including_blanks": len(cells),
                    "reader_disagreements": disagreements,
                    "low_confidence_primary": low_confidence,
                    "transcription_review_cells": len(attention),
                    "ecology_findings": 0},
        "cells": cells,
        "views": {"transcription_attention": attention, "ecology_anomalies": []},
    }


def from_canonical(document: dict[str, Any], ecology: dict[str, Any] | None = None):
    attention, cells = [], []
    for page in document.get("pages") or []:
        standalone = [
            ("field", item) for item in page.get("metadata_fields") or []
        ] + [
            ("text", item) for item in page.get("free_text_regions") or []
        ]
        for kind, cell in standalone:
            cell_id = f"p{page['page_number']}:{kind}:{cell['id']}"
            alternatives = [value for value in cell.get("alternatives") or []
                            if norm(value) != norm(cell.get("value"))]
            item = {"id": cell_id, "page": page["page_number"],
                    "bbox": cell.get("bbox"), "context": cell.get("label"),
                    "xlsx_sheet": cell.get("xlsx_sheet"),
                    "xlsx_row": cell.get("xlsx_row"),
                    "xlsx_column": cell.get("xlsx_column"),
                    "presented_value": cell.get("value"), "status": cell.get("status"),
                    "confidence": cell.get("confidence"),
                    "alternatives": alternatives,
                    "ecology_flags": cell.get("ecology_flags") or []}
            cells.append(item)
            if item["status"] in REVIEW_STATUSES:
                attention.append({"cell_id": cell_id, "page": item["page"],
                                  "bbox": item["bbox"], "priority": "high",
                                  "reason": cell.get("structural_reason") or item["status"],
                                  "presented_value": item["presented_value"],
                                  "alternatives": item["alternatives"]})
        for table in page.get("tables") or []:
            columns = {column["id"]: column for column in table.get("columns") or []}
            for row in table.get("rows") or []:
                for cell in row.get("cells") or []:
                    column = columns.get(cell.get("column_id"), {})
                    cell_id = f"p{page['page_number']}:{table['id']}:{row['id']}:{cell.get('column_id')}"
                    alternatives = [value for value in cell.get("alternatives") or []
                                    if norm(value) != norm(cell.get("value"))]
                    item = {"id": cell_id, "page": page["page_number"],
                            "bbox": cell.get("bbox"), "context": column.get("label"),
                            "xlsx_sheet": cell.get("xlsx_sheet"),
                            "xlsx_row": cell.get("xlsx_row"),
                            "xlsx_column": cell.get("xlsx_column"),
                            "presented_value": cell.get("value"), "status": cell.get("status"),
                            "confidence": cell.get("confidence"),
                            "alternatives": alternatives,
                            "ecology_flags": cell.get("ecology_flags") or []}
                    cells.append(item)
                    if item["status"] in REVIEW_STATUSES:
                        attention.append({"cell_id": cell_id, "page": item["page"],
                                          "bbox": item["bbox"], "priority": "high",
                                          "reason": cell.get("structural_reason") or item["status"],
                                          "presented_value": item["presented_value"],
                                          "alternatives": item["alternatives"]})
    # Informational taxonomy context belongs in analytics, not in the orange
    # human queue. Only findings that ask for a decision receive an overlay.
    findings = [finding for finding in (ecology or {}).get("findings") or []
                if finding.get("severity") in {"medium", "high"}]
    anomalies = []
    for index, finding in enumerate(findings):
        location = finding.get("location") or {}
        anomaly = {"finding_id": index + 1, **finding,
                   "page": location.get("page"), "bbox": location.get("bbox"),
                   "xlsx_sheet": location.get("xlsx_sheet"),
                   "xlsx_row": location.get("xlsx_row"),
                   "xlsx_column": location.get("xlsx_column")}
        anomalies.append(anomaly)
    return {
        "version": VERSION, "route": {"status": "unknown_template", "path": "canonical"},
        "policy": {
            "literal_transcription_is_immutable": True,
            "peer_readers_select_review_regions_not_replacements": True,
            "ecology_suggestions_are_separate": True,
        },
        "summary": {"target_cells_including_blanks": len(cells),
                    "transcription_review_cells": len(attention),
                    "ecology_findings": len(anomalies)},
        "cells": cells,
        "views": {"transcription_attention": attention,
                  "ecology_anomalies": anomalies},
    }


def validate(manifest):
    errors = []
    if manifest.get("version") != VERSION:
        errors.append("unsupported version")
    cell_ids = [cell.get("id") for cell in manifest.get("cells") or []]
    if len(cell_ids) != len(set(cell_ids)):
        errors.append("duplicate cell IDs")
    for cell in manifest.get("cells") or []:
        primary = cell.get("primary")
        if primary is not None and cell.get("presented_value") != primary.get("value"):
            errors.append(f"{cell.get('id')}: peer/ecology overwrote primary value")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="kind", required=True)
    template = sub.add_parser("template")
    template.add_argument("primary", type=Path)
    template.add_argument("--peer", type=Path)
    template.add_argument("--route", type=Path)
    template.add_argument("--output", type=Path, required=True)
    generic = sub.add_parser("canonical")
    generic.add_argument("canonical", type=Path)
    generic.add_argument("--ecology", type=Path)
    generic.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.kind == "template":
        route = json.loads(args.route.read_text()) if args.route else None
        manifest = from_template(args.primary, args.peer, route=route)
    else:
        document = json.loads(args.canonical.read_text())
        ecology = json.loads(args.ecology.read_text()) if args.ecology else None
        manifest = from_canonical(document, ecology)
    errors = validate(manifest)
    if errors:
        raise SystemExit("invalid review manifest: " + "; ".join(errors))
    args.output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(args.output), **manifest["summary"]}, indent=2))


if __name__ == "__main__":
    main()
