"""Helpers for building upload API payloads."""

from __future__ import annotations

import base64

from services.excel_service import to_xlsx


def build_summary(result: dict) -> dict:
    """Build row and flagged counts for UI summary."""
    row_count = 0
    flagged_count = 0
    for table in result.get("tables", []):
        for row in table.get("data_rows", []):
            row_count += 1
            cells = row.get("_cells", [])
            if any(c.get("confidence", 100) < 85 for c in cells):
                flagged_count += 1
    return {"rowCount": row_count, "flaggedCount": flagged_count}


def _attach_system_rows(result: dict) -> list[dict]:
    """Assign deterministic system serials in sheet write order."""
    rows = []
    system_serial = 1
    for table in result.get("tables", []):
        for row_data in table.get("data_rows", []):
            row_data["_system_serial"] = system_serial
            rows.append({
                "system_serial": system_serial,
                "bbox": row_data.get("_bbox"),
            })
            system_serial += 1
    return rows


def build_upload_payload(result: dict) -> dict:
    """Construct JSON response with workbook bytes and row bboxes."""
    rows = _attach_system_rows(result)
    xlsx_bytes = to_xlsx(result)
    return {
        "xlsx": base64.b64encode(xlsx_bytes).decode("ascii"),
        "rows": rows,
        "summary": build_summary(result),
    }
