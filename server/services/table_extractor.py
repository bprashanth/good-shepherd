"""
Extracts structured table data from a Textract response using the textractor library.

Layer 0+1 processing: uses vanilla Textract output parsed by amazon-textract-textractor.
No custom preprocessor logic. See docs/preprocessing.md for the layer model.
"""

from collections import defaultdict
from typing import Any

from textractor.entities.document import Document
from textractor.data.constants import TextTypes


def _cell_bbox(cell) -> dict[str, float] | None:
    """Return normalized bbox for a table cell if available."""
    bbox = getattr(cell, "bbox", None)
    if bbox is None:
        return None
    return {
        "left": float(bbox.x),
        "top": float(bbox.y),
        "width": float(bbox.width),
        "height": float(bbox.height),
    }


def _merge_bboxes(bboxes: list[dict[str, float]]) -> dict[str, float] | None:
    """Union row cell boxes into one normalized rectangle."""
    if not bboxes:
        return None
    left = min(b["left"] for b in bboxes)
    top = min(b["top"] for b in bboxes)
    right = max(b["left"] + b["width"] for b in bboxes)
    bottom = max(b["top"] + b["height"] for b in bboxes)
    return {
        "left": left,
        "top": top,
        "width": right - left,
        "height": bottom - top,
    }


def extract(textract_response: dict) -> dict:
    """
    Parse a raw Textract API response and extract structured table data.

    Returns a dict with:
        - tables: list of table dicts, each with headers, rows, and per-cell confidence
        - key_value_pairs: list of form field dicts (universal fields)
        - diagnostics: block/entity type counts for debugging
    """
    doc = Document.open(textract_response)

    result = {
        "tables": [],
        "key_value_pairs": [],
        "diagnostics": _build_diagnostics(textract_response, doc),
    }

    # Extract tables
    for table in doc.tables:
        result["tables"].append(_extract_table(table))

    # Extract key-value pairs (universal fields)
    for kv in doc.key_values:
        key_text = " ".join(w.text for w in kv.key) if kv.key else ""
        value_text = kv.value.text if kv.value else ""
        key_confidence = min((w.confidence for w in kv.key), default=0) if kv.key else 0
        value_confidence = (
            min((w.confidence for w in kv.value.words), default=0)
            if kv.value and kv.value.words
            else 0
        )
        if key_text.strip():
            result["key_value_pairs"].append({
                "key": key_text.strip().rstrip(":"),
                "value": value_text.strip(),
                "key_confidence": round(key_confidence * 100, 1),
                "value_confidence": round(value_confidence * 100, 1),
            })

    return result


def _get_parent_headers(cells_in_row: list) -> dict:
    """Find contiguous groups of header cells and combine their text.

    For multi-row headers, the parent row often has merged cells spanning
    multiple columns (e.g. "Canopy Openness" spanning cols 5-8). Textractor
    splits these into individual cells with partial text. This function
    detects contiguous groups and combines their text, then maps each
    column in the group to the combined parent header.

    Returns: {col_index: combined_parent_text}
    """
    cells = sorted(cells_in_row, key=lambda c: c.col_index)
    parent_by_col = {}

    if not cells:
        return parent_by_col

    # Find contiguous groups of cells
    groups = []
    current_group = [cells[0]]
    for cell in cells[1:]:
        if cell.col_index == current_group[-1].col_index + 1:
            current_group.append(cell)
        else:
            groups.append(current_group)
            current_group = [cell]
    groups.append(current_group)

    for group in groups:
        texts = [c.text.strip() for c in group if c.text.strip()]
        combined = " ".join(texts)
        for cell in group:
            parent_by_col[cell.col_index] = combined

    return parent_by_col


def _extract_table(table) -> dict:
    """Extract headers, data rows, and metadata from a single Table object."""
    # Collect all header cells directly (bypass table.column_headers which
    # mishandles multi-row hierarchical headers with MERGED_CELL spans)
    header_cells = [c for c in table.table_cells if c.is_column_header]
    header_row_indices = set()
    headers = []

    if header_cells:
        # Group header cells by row
        header_rows_map = defaultdict(list)
        for cell in header_cells:
            header_rows_map[cell.row_index].append(cell)
            header_row_indices.add(cell.row_index)

        sorted_header_rows = sorted(header_rows_map.keys())

        if len(sorted_header_rows) == 1:
            # Single header row: use directly
            for cell in sorted(header_rows_map[sorted_header_rows[0]],
                               key=lambda c: c.col_index):
                text = cell.text.strip()
                if text:
                    headers.append({
                        "text": text,
                        "column_index": cell.col_index,
                        "confidence": round(cell.confidence * 100, 1),
                        "col_span": cell.col_span,
                    })
        else:
            # Multi-row headers: flatten hierarchy.
            # Parent rows (all except last) contain group headers (e.g. "Canopy Openness").
            # Last row contains per-column headers (e.g. "North", "East", "West", "South").
            # Flattened result: "Canopy Openness North", "Canopy Openness East", etc.
            parent_text_by_col = {}
            for row_idx in sorted_header_rows[:-1]:
                parent_text_by_col.update(
                    _get_parent_headers(header_rows_map[row_idx])
                )

            last_row = sorted_header_rows[-1]
            for cell in sorted(header_rows_map[last_row],
                               key=lambda c: c.col_index):
                child_text = cell.text.strip()
                parent_text = parent_text_by_col.get(cell.col_index, "")

                if parent_text and child_text:
                    full_text = f"{parent_text} {child_text}"
                elif child_text:
                    full_text = child_text
                elif parent_text:
                    full_text = parent_text
                else:
                    continue  # skip entirely empty headers

                headers.append({
                    "text": full_text,
                    "column_index": cell.col_index,
                    "confidence": round(cell.confidence * 100, 1),
                    "col_span": cell.col_span,
                })

    # Sort headers by column index
    headers.sort(key=lambda h: h["column_index"])

    # Build column_index → header_text mapping
    col_to_header = {}
    for h in headers:
        col_to_header[h["column_index"]] = h["text"]

    # Fallback: if no COLUMN_HEADER detected, use first row as header
    if not headers:
        rows_by_index = table._get_table_cells(row_wise=True)
        if rows_by_index:
            first_row_idx = min(rows_by_index.keys())
            header_row_indices.add(first_row_idx)
            for cell in rows_by_index[first_row_idx]:
                text = cell.text.strip()
                if text:
                    headers.append({
                        "text": text,
                        "column_index": cell.col_index,
                        "confidence": round(cell.confidence * 100, 1),
                        "col_span": cell.col_span,
                    })
                    col_to_header[cell.col_index] = text
            headers.sort(key=lambda h: h["column_index"])

    # Extract data rows (skip header rows)
    data_rows = []
    rows_by_index = table._get_table_cells(row_wise=True)
    for row_idx in sorted(rows_by_index.keys()):
        if row_idx in header_row_indices:
            continue
        cells = rows_by_index[row_idx]
        row_data = {"_row_index": row_idx, "_cells": []}
        cell_bboxes = []
        for cell in sorted(cells, key=lambda c: c.col_index):
            header_name = col_to_header.get(cell.col_index, f"col_{cell.col_index}")
            cell_info = {
                "header": header_name,
                "text": cell.text.strip(),
                "confidence": round(cell.confidence * 100, 1),
                "column_index": cell.col_index,
            }
            row_data[header_name] = cell.text.strip()
            row_data["_cells"].append(cell_info)
            cell_bbox = _cell_bbox(cell)
            if cell_bbox:
                cell_bboxes.append(cell_bbox)

        merged_row_bbox = _merge_bboxes(cell_bboxes)
        if merged_row_bbox:
            row_data["_bbox"] = merged_row_bbox
        data_rows.append(row_data)

    # Text type distribution
    text_types = defaultdict(int)
    for word in table.words:
        if word.text_type == TextTypes.HANDWRITING:
            text_types["HANDWRITING"] += 1
        elif word.text_type == TextTypes.PRINTED:
            text_types["PRINTED"] += 1
        else:
            text_types["OTHER"] += 1

    return {
        "row_count": table.row_count,
        "column_count": table.column_count,
        "column_headers": headers,
        "data_rows": data_rows,
        "text_types": dict(text_types),
    }


def _build_diagnostics(textract_response: dict, doc: Document) -> dict:
    """Build a diagnostic summary of what Textract returned."""
    blocks = textract_response.get("Blocks", [])

    block_types = defaultdict(int)
    entity_types = defaultdict(int)
    text_types = defaultdict(int)

    for block in blocks:
        block_types[block["BlockType"]] += 1
        for et in block.get("EntityTypes", []):
            entity_types[et] += 1
        if block["BlockType"] == "WORD":
            tt = block.get("TextType", "UNKNOWN")
            text_types[tt] += 1

    return {
        "block_types": dict(block_types),
        "entity_types": dict(entity_types),
        "text_types": dict(text_types),
        "table_count": len(doc.tables),
        "key_value_count": len(doc.key_values),
    }
