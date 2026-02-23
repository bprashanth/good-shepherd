"""Session and site endpoints: fetch from S3 with presigned image URLs."""

import logging

from fastapi import APIRouter, HTTPException

from services.sessions_service import SessionsService

logger = logging.getLogger(__name__)
router = APIRouter()
_service = SessionsService()


@router.get("/sessions/{org}")
async def get_sessions(org: str, bucket: str = "fomomon"):
    """Return combined session data with presigned image URLs.

    Sessions contain GPS coordinates, timestamps, and image URLs.
    Survey/response data is excluded — survey answers come from
    processing form images via POST /api/upload (Textract).
    """
    try:
        return _service.get_sessions(org, bucket)
    except Exception:
        logger.exception("Failed to fetch sessions for org=%s bucket=%s", org, bucket)
        raise HTTPException(status_code=500, detail="Failed to fetch sessions")


@router.get("/sites/{org}")
async def get_sites(org: str, bucket: str = "fomomon"):
    """Return sites config with presigned reference/ghost image URLs.

    Sites contain GPS locations, site names, and reference images.
    """
    try:
        return _service.get_sites(org, bucket)
    except Exception:
        logger.exception("Failed to fetch sites for org=%s bucket=%s", org, bucket)
        raise HTTPException(status_code=500, detail="Failed to fetch sites config")
