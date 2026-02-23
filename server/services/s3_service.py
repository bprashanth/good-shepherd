"""Shared S3 utilities: JSON fetching, listing, and presigned URL generation."""

import json
import logging
import re

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

PRESIGN_EXPIRY = 604800  # 7 days (S3 maximum)

# Match S3 HTTPS URLs in two forms:
#   https://{bucket}.s3.{region}.amazonaws.com/{key}
#   https://s3.{region}.amazonaws.com/{bucket}/{key}
S3_URL_RE = re.compile(
    r"https://(?:(.+?)\.s3[.-].*?\.amazonaws\.com/(.+)"
    r"|s3[.-].*?\.amazonaws\.com/([^/]+)/(.+))"
)


class S3Service:
    def __init__(self):
        self.s3 = boto3.client("s3", config=Config(signature_version="s3v4"))

    def list_json_keys(self, bucket: str, prefix: str) -> list[str]:
        """List all *.json keys under prefix, handling pagination."""
        keys: list[str] = []
        continuation_token = None
        while True:
            kwargs = {"Bucket": bucket, "Prefix": prefix}
            if continuation_token:
                kwargs["ContinuationToken"] = continuation_token
            resp = self.s3.list_objects_v2(**kwargs)
            for obj in resp.get("Contents", []):
                k = obj["Key"]
                if k.endswith(".json"):
                    keys.append(k)
            if resp.get("IsTruncated"):
                continuation_token = resp.get("NextContinuationToken")
            else:
                break
        return keys

    def get_json(self, bucket: str, key: str) -> dict | list:
        """Download and parse a single JSON object."""
        resp = self.s3.get_object(Bucket=bucket, Key=key)
        return json.loads(resp["Body"].read())

    def presign_url(self, https_url: str) -> str:
        """Replace an S3 HTTPS URL with a presigned GET URL (7-day expiry).

        Returns original URL unchanged if not a recognized S3 URL.
        """
        m = S3_URL_RE.match(https_url)
        if not m:
            return https_url
        bucket = m.group(1) or m.group(3)
        key = m.group(2) or m.group(4)
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=PRESIGN_EXPIRY,
        )

    def presign_session(self, session: dict) -> dict:
        """Presign portraitImageUrl and landscapeImageUrl fields."""
        for field in ("portraitImageUrl", "landscapeImageUrl"):
            url = session.get(field)
            if url:
                session[field] = self.presign_url(url)
        return session

    def presign_sites(self, sites: dict) -> dict:
        """Presign image URLs in sites.json (reference/ghost images)."""
        for site in sites.get("sites", []):
            for field in ("referenceImageUrl", "ghostImageUrl"):
                url = site.get(field)
                if url:
                    site[field] = self.presign_url(url)
        return sites
