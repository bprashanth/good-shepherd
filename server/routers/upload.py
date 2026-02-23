"""
Upload endpoint: accepts an image or raw Textract JSON,
runs extraction + Excel generation, returns .xlsx file.
"""

import json
import logging

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import Response

from services.table_extractor import extract
from services.excel_service import to_xlsx
from services.textract_service import TextractService


def _build_summary(result: dict) -> str:
    """Build a JSON summary string with row and flagged counts."""
    row_count = 0
    flagged_count = 0
    for table in result.get("tables", []):
        for row in table.get("data_rows", []):
            row_count += 1
            cells = row.get("_cells", [])
            if any(c.get("confidence", 100) < 85 for c in cells):
                flagged_count += 1
    return json.dumps({"rowCount": row_count, "flaggedCount": flagged_count})

logger = logging.getLogger(__name__)

router = APIRouter()
textract = TextractService()


@router.post("/upload")
async def upload_image(image: UploadFile = File(...)):
    """Upload an image → Textract → extract → return .xlsx."""
    image_bytes = await image.read()
    try:
        textract_response = textract.analyze_sync(image_bytes)
    except Exception as e:
        logger.exception("Textract call failed")
        raise HTTPException(status_code=502, detail=f"Textract error: {e}")
    result = extract(textract_response)
    xlsx_bytes = to_xlsx(result)

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=form_output.xlsx",
            "X-Form-Summary": _build_summary(result),
        },
    )


@router.post("/upload/json")
async def upload_json(request: Request):
    """Accept raw Textract JSON → extract → return .xlsx.

    Useful for testing with existing files from cloud/output/ without
    spending on Textract API calls.
    """
    textract_response = await request.json()
    result = extract(textract_response)
    xlsx_bytes = to_xlsx(result)

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=form_output.xlsx",
            "X-Form-Summary": _build_summary(result),
        },
    )
