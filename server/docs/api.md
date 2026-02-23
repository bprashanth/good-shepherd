## API Endpoints

### `GET /api/health`

Health check. No auth required.

**Response** `200`:
```json
{"status": "ok"}
```

---

### `POST /api/upload`

Upload a form image, process via Textract, return Excel.

**Request**: `multipart/form-data`
```
image: <file>    (JPEG/PNG form image)
```

**Response** `200`: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Body: `.xlsx` file bytes
- Header `X-Form-Summary`: `{"rowCount": 12, "flaggedCount": 2}`

**Example**:
```bash
curl -X POST "${BASE_URL}/api/upload" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "image=@form.jpg" \
  -o output.xlsx
```

---

### `POST /api/upload/json`

Same as `/api/upload` but accepts raw Textract JSON instead of an image.
Useful for testing without incurring Textract costs.

**Request**: `application/json` — a Textract `AnalyzeDocument` response body.

**Response** `200`: `.xlsx` file (same as above).

**Example**:
```bash
curl -X POST "${BASE_URL}/api/upload/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d @textract_output.json \
  -o output.xlsx
```

---

### `POST /api/analyze`

Upload a form image, return structured JSON diagnostics (no Excel).

**Request**: `multipart/form-data`
```
image: <file>
```

**Response** `200`: `application/json`
```json
{
  "tables": [
    {
      "headers": ["Species", "Count", "Notes"],
      "data_rows": [
        {
          "Species": "Nilgiri langur",
          "Count": "3",
          "Notes": "near stream",
          "_cells": [
            {"text": "Nilgiri langur", "confidence": 98.2},
            {"text": "3", "confidence": 45.1},
            {"text": "near stream", "confidence": 91.0}
          ]
        }
      ]
    }
  ]
}
```

---

### `POST /api/analyze/json`

Same as `/api/analyze` but accepts raw Textract JSON.

---

### `GET /api/sessions/{org}?bucket=fomomon`

Fetch all monitoring sessions for an organization. Returns GPS coordinates,
timestamps, and presigned image URLs. Survey/response data is excluded —
survey answers come from processing form images via `POST /api/upload`.

**Parameters**:
- `org` (path) — organization ID, e.g. `ncf`
- `bucket` (query, default `fomomon`) — S3 bucket containing session data

**Response** `200`: `application/json`
```json
[
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
]
```

Image URLs are presigned (valid for 7 days). `responses` is always empty —
this is by design.

**Example**:
```bash
curl -s "${BASE_URL}/api/sessions/ncf" \
  -H "Authorization: Bearer ${TOKEN}" | jq '.[0]'
```

---

### `GET /api/sites/{org}?bucket=fomomon`

Fetch the sites configuration for an organization. Returns GPS locations,
site names, survey questions, and presigned reference/ghost image URLs.

**Parameters**:
- `org` (path) — organization ID, e.g. `ncf`
- `bucket` (query, default `fomomon`) — S3 bucket

**Response** `200`: `application/json`
```json
{
  "bucket_root": "s3://fomomon/ncf",
  "sites": [
    {
      "id": "G14R1-2025",
      "name": "Gudalur Plot 14 Row 1",
      "location": {"latitude": 10.313, "longitude": 76.837},
      "referenceImageUrl": "https://fomomon.s3...?X-Amz-Signature=...",
      "ghostImageUrl": "https://fomomon.s3...?X-Amz-Signature=...",
      "survey": [
        {"id": "q1", "question": "What animals did you see?", "type": "text"}
      ]
    }
  ]
}
```

**Example**:
```bash
curl -s "${BASE_URL}/api/sites/ncf" \
  -H "Authorization: Bearer ${TOKEN}" | jq '.sites[0].name'
```

## Migrating from static `db.json`

If your app currently fetches `s3://fomomon/{org}/db.json` directly, replace
that with:

```
GET /api/sessions/{org}
```

Key differences:
- **Auth required** — you need a Cognito login and Bearer token
- **No survey data** — `responses` is always `[]` (use `/api/upload` for that)
- **Presigned image URLs** — image URLs work directly, no S3 credentials needed
- **Live data** — always current, no manual `create_db.py` runs needed

For sites config (previously loaded from a local `sites.json`), use:

```
GET /api/sites/{org}
```

## Error responses

| Status | Meaning |
|---|---|
| `401` | Missing or invalid `Authorization` header (API Gateway rejects) |
| `500` | Server error (check Lambda logs: `aws logs tail /aws/lambda/form-idable-server`) |

The `401` is returned by API Gateway before the request reaches the server.
If you're getting 401s, check:
1. Token is present and prefixed with `Bearer `
2. Token is an ID token (not access token)
3. Token hasn't expired (1 hour lifetime)
4. Token was issued by the correct pool/client (check `auth_config.json`)

Run `server/deploy/setup.sh` to validate pool/client configuration — it checks
auth flows and JWT authorizer settings.
