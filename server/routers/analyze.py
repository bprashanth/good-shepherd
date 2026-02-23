"""
Diagnostic endpoint: accepts an image or raw Textract JSON and returns
a structured analysis of what Textract detected (block types, entity types,
tables with headers, key-value pairs, text type distribution).

Use this to understand what Textract gives us for different form types
before building any preprocessing logic.
"""

import json

from fastapi import APIRouter, File, Request, UploadFile

from services.table_extractor import extract
from services.textract_service import TextractService

router = APIRouter()
textract = TextractService()


@router.post("/analyze")
async def analyze_image(image: UploadFile = File(...)):
    """Analyze an image: send to Textract, parse with textractor, return diagnostics."""
    image_bytes = await image.read()
    textract_response = textract.analyze_sync(image_bytes)
    result = extract(textract_response)
    return result


@router.post("/analyze/json")
async def analyze_json(request: Request):
    """Analyze an existing Textract JSON response (skip the Textract API call).

    Useful for testing with files from cloud/output/ without spending on Textract.
    """
    textract_response = await request.json()
    result = extract(textract_response)
    return result
