# Session & Sites API Design

## Why these endpoints exist

The `server/test/photomon/create_db.py` CLI script downloads session JSONs from
S3 and combines them into a local `db.json`. This requires manual runs and local
AWS credentials. The new `/api/sessions/{org}` and `/api/sites/{org}` endpoints
do this live — the server fetches data from S3, replaces raw image URLs with
presigned GET URLs, and returns JSON.

Survey/question data is intentionally excluded from the sessions response.
Survey answers come from processing form images via the existing `/api/upload`
(Textract) endpoint, not from session metadata.

## S3 bucket structure

Sessions and sites config live under an org prefix in the bucket:

```
s3://{bucket}/{org}/
  sessions/
    {userId}_{timestamp}.json   # one per session
  sites.json                     # site definitions with GPS + survey config
```

Image URLs in these files point to one of several buckets (`fomomon`,
`fomomonguest`, `forestfomo-images`) depending on the upload path.

## Presigned URL strategy

Raw session/site data contains plain S3 HTTPS URLs like:
```
https://fomomonguest.s3.ap-south-1.amazonaws.com/ncf/sessions/photo.jpg
```

These are not publicly accessible. The server generates presigned GET URLs
with a 7-day expiry (the S3 maximum). The presigning happens server-side
using the Lambda's IAM role, so clients never need direct S3 credentials.

The regex `S3_URL_RE` in `s3_service.py` handles both S3 URL formats:
- `https://{bucket}.s3.{region}.amazonaws.com/{key}` (virtual-hosted)
- `https://s3.{region}.amazonaws.com/{bucket}/{key}` (path-style)

## Session data shape

Input (raw from S3):
```json
{
  "sessionId": "srini_2025-09-04T13:12:28.859762",
  "siteId": "G14R1-2025",
  "latitude": 10.313653,
  "longitude": 76.8372776,
  "portraitImageUrl": "https://fomomonguest.s3.ap-south-1.amazonaws.com/...",
  "landscapeImageUrl": "https://fomomonguest.s3.ap-south-1.amazonaws.com/...",
  "portraitImagePath": "/data/user/0/.../portrait.jpg",
  "landscapeImagePath": "/data/user/0/.../landscape.jpg",
  "isUploaded": true,
  "responses": [{"questionId": "q1", "answer": "Nilgiri langur"}],
  "timestamp": "2025-09-04T13:12:28.859762",
  "userId": "srini"
}
```

Output (from endpoint):
```json
{
  "sessionId": "srini_2025-09-04T13:12:28.859762",
  "siteId": "G14R1-2025",
  "latitude": 10.313653,
  "longitude": 76.8372776,
  "portraitImageUrl": "https://fomomonguest.s3...?X-Amz-Signature=...",
  "landscapeImageUrl": "https://fomomonguest.s3...?X-Amz-Signature=...",
  "responses": [],
  "timestamp": "2025-09-04T13:12:28.859762",
  "userId": "srini"
}
```

Dropped fields: `portraitImagePath`, `landscapeImagePath` (local device paths),
`isUploaded`. Modified: image URLs are presigned, `responses` is emptied.

## Deployment changes

### Lambda IAM policy (`deploy/lambda-policy.json`)

Added `s3:GetObject` and `s3:ListBucket` for the three image buckets:

```json
{
  "Effect": "Allow",
  "Action": ["s3:GetObject", "s3:ListBucket"],
  "Resource": [
    "arn:aws:s3:::fomomon",
    "arn:aws:s3:::fomomon/*",
    "arn:aws:s3:::fomomonguest",
    "arn:aws:s3:::fomomonguest/*",
    "arn:aws:s3:::forestfomo-images",
    "arn:aws:s3:::forestfomo-images/*"
  ]
}
```

`s3:GetObject` is needed both for downloading JSON files and for generating
presigned URLs. `s3:ListBucket` is needed to list session files under a prefix.

### API Gateway routes (`deploy/setup.sh`)

Added two GET routes with JWT auth:

```bash
create_route "GET /api/sessions/{org}" "true"
create_route "GET /api/sites/{org}" "true"
```

The existing `POST /api/{proxy+}` wildcard only matches POST requests, so GET
endpoints need explicit routes.

### Deploying the changes

After editing `lambda-policy.json` and `setup.sh`:

```bash
cd server/deploy
./setup.sh    # updates IAM policy + adds new routes (idempotent)
./deploy.sh   # builds, tests, pushes new Lambda code
```

`setup.sh` is fully idempotent — `put-role-policy` overwrites the IAM policy,
and `create_route` checks for existing routes before creating new ones.

## Future

The Flutter app can use `/api/sites/{org}` to fetch presigned reference/ghost
image URLs instead of accessing S3 directly. This allows the S3 buckets to be
fully locked down (no public access, no client-side credentials).
