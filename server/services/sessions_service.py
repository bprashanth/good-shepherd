"""Business logic for fetching sessions and sites config from S3."""

import logging

from services.s3_service import S3Service

logger = logging.getLogger(__name__)

# Fields to drop from raw session data (local device paths, upload flags).
_DROP_FIELDS = {"portraitImagePath", "landscapeImagePath", "isUploaded"}


class SessionsService:
    def __init__(self, s3_service: S3Service | None = None):
        self.s3 = s3_service or S3Service()

    def get_sessions(self, org: str, bucket: str = "fomomon") -> list[dict]:
        """Fetch all sessions from S3, strip survey data, presign image URLs.

        1. List s3://{bucket}/{org}/sessions/*.json
        2. Download each to memory
        3. Strip responses (survey data comes from form images)
        4. Drop device-local fields
        5. Presign portraitImageUrl + landscapeImageUrl
        6. Return combined list
        """
        prefix = f"{org}/sessions/"
        keys = self.s3.list_json_keys(bucket, prefix)
        logger.info("Found %d session files under s3://%s/%s", len(keys), bucket, prefix)

        sessions: list[dict] = []
        for key in keys:
            try:
                session = self.s3.get_json(bucket, key)
            except Exception:
                logger.exception("Failed to download s3://%s/%s", bucket, key)
                continue

            # Strip survey responses — answers come from form image processing.
            session["responses"] = []

            # Drop device-local fields.
            for field in _DROP_FIELDS:
                session.pop(field, None)

            session = self.s3.presign_session(session)
            sessions.append(session)

        return sessions

    def get_sites(self, org: str, bucket: str = "fomomon") -> dict:
        """Fetch sites.json from S3 and presign reference/ghost image URLs.

        1. Download s3://{bucket}/{org}/sites.json
        2. Presign reference/ghost image URLs in each site
        3. Return sites config dict
        """
        key = f"{org}/sites.json"
        sites = self.s3.get_json(bucket, key)
        return self.s3.presign_sites(sites)
