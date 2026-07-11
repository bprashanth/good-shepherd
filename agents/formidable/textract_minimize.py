"""Call Textract and reduce its response to a small, generic JSON for the
vision agent.

Raw `AnalyzeDocument` responses are dominated by per-point `Polygon`
coordinates, UUID `Id`/`Relationships` chains, and per-`WORD` blocks that are
redundant once `LINE`/`CELL` text is resolved (~30x size reduction in
practice: ~450KB -> ~15-25KB for a typical datasheet page). This module does
that reduction without any form-specific layout assumptions (no header
detection/flattening) — it's a direct, generic re-shaping of Textract's own
block graph:

  - tables: row/col grid of cells (text, confidence, bbox, header flag,
    row/col span)
  - key_values: Textract's KEY_VALUE_SET pairs
  - other_text: LINE blocks not consumed by any table cell or key/value
    (titles, loose labels, secondary blocks Textract didn't place in a
    table — this is where "structure Textract missed" shows up)

The agent is expected to use this as a starting point, not ground truth —
it has the page image too and can crop/zoom to verify or fill gaps.
"""

import re

import boto3


def analyze(image_bytes: bytes, region: str = "ap-south-1") -> dict:
    """Call Textract AnalyzeDocument with TABLES+FORMS+LAYOUT."""
    client = boto3.client("textract", region_name=region)
    return client.analyze_document(
        Document={"Bytes": image_bytes},
        FeatureTypes=["TABLES", "FORMS", "LAYOUT"],
    )


def _bbox(block, ndigits: int = 3) -> list[float]:
    g = block["Geometry"]["BoundingBox"]
    return [round(g["Left"], ndigits), round(g["Top"], ndigits),
            round(g["Width"], ndigits), round(g["Height"], ndigits)]


def _child_ids(block: dict, rel_type: str = "CHILD") -> list[str]:
    for r in block.get("Relationships", []):
        if r["Type"] == rel_type:
            return r["Ids"]
    return []


def _text_of(block_id: str, by_id: dict) -> str:
    """Join WORD/SELECTION_ELEMENT children of a block in reading order."""
    block = by_id[block_id]
    words = []
    for cid in _child_ids(block):
        c = by_id.get(cid)
        if c is None:
            continue
        if c["BlockType"] == "WORD":
            words.append((c["Geometry"]["BoundingBox"]["Left"], c["Text"]))
        elif c["BlockType"] == "SELECTION_ELEMENT":
            mark = "[X]" if c.get("SelectionStatus") == "SELECTED" else "[ ]"
            words.append((c["Geometry"]["BoundingBox"]["Left"], mark))
    words.sort()
    return " ".join(w for _, w in words)


def simplify(textract_response: dict) -> dict:
    """Reduce a raw Textract response to {tables, key_values, other_text}."""
    by_id = {b["Id"]: b for b in textract_response["Blocks"]}
    consumed_word_ids: set[str] = set()

    tables = []
    for block in textract_response["Blocks"]:
        if block["BlockType"] != "TABLE":
            continue
        cells = []
        n_rows, n_cols = 0, 0
        for cid in _child_ids(block):
            cell = by_id[cid]
            if cell["BlockType"] != "CELL":
                continue
            consumed_word_ids.update(_child_ids(cell))
            r, c = cell["RowIndex"], cell["ColumnIndex"]
            n_rows, n_cols = max(n_rows, r), max(n_cols, c)
            entry = {
                "r": r, "c": c,
                "text": _text_of(cid, by_id),
                "conf": round(cell["Confidence"], 1),
                "bbox": _bbox(cell),
            }
            if cell.get("RowSpan", 1) > 1:
                entry["rowspan"] = cell["RowSpan"]
            if cell.get("ColumnSpan", 1) > 1:
                entry["colspan"] = cell["ColumnSpan"]
            if "COLUMN_HEADER" in cell.get("EntityTypes", []):
                entry["header"] = True
            cells.append(entry)
        tables.append({
            "bbox": _bbox(block),
            "n_rows": n_rows, "n_cols": n_cols,
            "cells": cells,
        })

    key_values = []
    for block in textract_response["Blocks"]:
        if block["BlockType"] != "KEY_VALUE_SET" or "KEY" not in block.get("EntityTypes", []):
            continue
        consumed_word_ids.update(_child_ids(block))
        value_text, value_conf = "", 0.0
        for vid in _child_ids(block, "VALUE"):
            vblock = by_id[vid]
            consumed_word_ids.update(_child_ids(vblock))
            value_text = _text_of(vid, by_id)
            value_conf = vblock["Confidence"]
        key_values.append({
            "key": _text_of(block["Id"], by_id),
            "value": value_text,
            "key_conf": round(block["Confidence"], 1),
            "value_conf": round(value_conf, 1),
            "bbox": _bbox(block),
        })

    other_text = []
    for block in textract_response["Blocks"]:
        if block["BlockType"] != "LINE":
            continue
        wids = _child_ids(block)
        if wids and all(w in consumed_word_ids for w in wids):
            continue
        text = block["Text"]
        if not re.search(r"\w", text):
            # Pure punctuation/marks (stray commas, dashes, ticks) — not
            # words, drop as noise.
            continue
        other_text.append({
            "text": text,
            "conf": round(block["Confidence"], 1),
            "bbox": _bbox(block),
        })

    return {"tables": tables, "key_values": key_values, "other_text": other_text}
