"""
Upload endpoint: accepts an image or raw Textract JSON,
runs extraction + Excel generation, returns JSON payload.
"""

import logging

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from services.table_extractor import extract
from services.upload_payload import build_upload_payload
from services.textract_service import TextractService

logger = logging.getLogger(__name__)

router = APIRouter()
textract = TextractService()


@router.post("/upload")
async def upload_image(image: UploadFile = File(...)):
    """Upload an image → Textract → extract → return workbook + bboxes."""
    image_bytes = await image.read()
    try:
        textract_response = textract.analyze_sync(image_bytes)
    except Exception as e:
        logger.exception("Textract call failed")
        raise HTTPException(status_code=502, detail=f"Textract error: {e}")
    result = extract(textract_response)
    return build_upload_payload(result)


@router.post("/upload/json")
async def upload_json(request: Request):
    """Accept raw Textract JSON → extract → return workbook + bboxes.

    Useful for testing with existing files from cloud/output/ without
    spending on Textract API calls.
    """
    textract_response = await request.json()
    result = extract(textract_response)
    return build_upload_payload(result)
