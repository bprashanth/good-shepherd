# Scribe Server

FastAPI server that processes form images via AWS Textract and returns
structured Excel files. Deployed to AWS Lambda via Docker + Lambda Web Adapter.

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/health` | No | Health check |
| `POST` | `/api/upload` | Yes | Image → Textract → .xlsx |
| `POST` | `/api/upload/json` | Yes | Raw Textract JSON → .xlsx (no Textract call) |
| `POST` | `/api/analyze` | Yes | Image → Textract → structured JSON diagnostics |
| `POST` | `/api/analyze/json` | Yes | Raw Textract JSON → structured JSON diagnostics |
| `GET` | `/api/sessions/{org}?bucket=fomomon` | Yes | Combined sessions with presigned image URLs |
| `GET` | `/api/sites/{org}?bucket=fomomon` | Yes | Sites config with presigned reference/ghost image URLs |

## Adding a new endpoint

1. Create or edit a router file in `routers/` (e.g., `routers/my_router.py`):
   ```python
   from fastapi import APIRouter
   router = APIRouter()

   @router.post("/my-endpoint")
   async def my_endpoint():
       return {"result": "ok"}
   ```

2. Register it in `main.py`:
   ```python
   from routers import my_router
   app.include_router(my_router.router, prefix="/api")
   ```

3. If the route needs auth in prod, no code changes are needed — API Gateway's
   JWT authorizer already covers `POST /api/{proxy+}`. If you add a new HTTP
   method (e.g., `GET /api/something`), add a route in `deploy/setup.sh`:
   ```bash
   create_route "GET /api/something" "true"   # "true" = JWT required
   ```

4. If the Lambda needs new AWS permissions (e.g., S3 access), add them to
   `deploy/lambda-policy.json`. Re-running `setup.sh` applies the updated
   policy (idempotent). See [`docs/session_api.md`](docs/session_api.md) for a worked example
   of adding API Gateway routes and Lambda IAM permissions.

## Development

### Start the server

```bash
cd server
uvicorn main:app --host 0.0.0.0 --port 8070 --reload
```

### Run local tests

```bash
server/test/test_local.sh
```

This tests health, JSON→Excel (no Textract cost), image→Excel (Textract),
and session/sites endpoints (if AWS creds are available). Each test prints
the curl command so you can rerun it by hand for finer verification (e.g.,
piping to `jq`). If the server isn't running it prints the command to start it.

You can also test out the bbox logic independently
```bash
cd server/test/forms
python3 render_row_bbox_previews.py --input-image images/segmented_000.jpg --match-word kage
```

### Docker Compose (integration test)

```bash
cd server
docker compose up --build -d
sleep 3
curl http://localhost:8070/api/health    # → {"status":"ok"}
docker compose down
```

## Deployment

### Prerequisites

- AWS CLI configured (`aws sts get-caller-identity` works)
- Docker installed
- `deploy/test-credentials.env` with test user creds (see below)

### First-time setup

```bash
cd server/deploy
./setup.sh
```

Creates ECR repo, IAM role, API Gateway HTTP API with JWT authorizer, routes,
and `prod` stage. Idempotent — safe to re-run. Writes `deploy/outputs.env`.

### Deploy

```bash
cd server/deploy
./deploy.sh
```

Builds the Docker image, runs a local smoke test, pushes to ECR, creates or
updates the Lambda function, sets env vars, and grants API Gateway invoke
permission.

### Testing

Create `deploy/test-credentials.env` if it doesn't exist:

```
TEST_USERNAME=someuser@foo.com
TEST_PASSWORD='Somepassword'
```

The deployment test scripts expect three config sources:

- `server/deploy/config.sh` for shared AWS region and Cognito settings
- `server/deploy/outputs.env` for the deployed API Gateway URL
- `server/deploy/test-credentials.env` for the test Cognito username/password

If you want to inspect the resolved values in your current shell first:

```bash
source server/deploy/config.sh
source server/deploy/outputs.env
source server/deploy/test-credentials.env
```

Then run the end-to-end test:

```bash
server/test/test_deployment.sh
```

This script:
1. Ensures the test user exists in Cognito (idempotent)
2. Verifies unauthenticated POST requests return 401
3. Verifies health endpoint returns 200 (no auth)
4. Gets a Cognito JWT token
5. Tests authenticated JSON`->`Excel upload
6. Tests authenticated image`->`Excel upload (Textract)
7. Tests authenticated sessions endpoint
8. Verifies unauthenticated sessions access is blocked

Each test prints the curl command for manual rerun.

To fetch a fresh sessions snapshot for a specific org and save it locally:

```bash
server/test/get_db.sh --org ncf
```

By default this writes `server/test/photomon/db.<org>.fresh.json`. You can
override the path with `--out /path/to/file.json`.

If `server/deploy/config.sh` cannot load Cognito config from S3, set
`COGNITO_POOL_ID` and `COGNITO_CLIENT_ID` in your shell before running
`test_deployment.sh` or `get_db.sh`.

### Add a Cognito user

```bash
cd server/deploy

# From test-credentials.env:
./add-user.sh

# Or with explicit args:
./add-user.sh user@example.com 'somepassword'
```

Idempotent — skips creation if user already exists, always sets the password.

## Authentication

All endpoints except `/api/health` require a Cognito JWT token in the
`Authorization: Bearer <token>` header. Auth is enforced at API Gateway —
the FastAPI code has no auth middleware (locally, endpoints work without tokens).

Quick check of current config:
```bash
source server/deploy/config.sh && echo "POOL=$COGNITO_POOL_ID CLIENT=$COGNITO_CLIENT_ID"
```

`setup.sh` validates the full auth chain on every run — pool existence, client
auth flows, and JWT authorizer issuer/audience. If something is wrong you'll
see it there, not as a mystery 401 at test time.

For full details see:
- [`docs/testing.md`](docs/testing.md) - test script prerequisites and workflows
- [**Client Integration Guide**](docs/manuals/client_integration.md) — how to authenticate and call every endpoint (request/response examples, token handling, migration from static `db.json`)
- [`docs/cross_app_auth.md`](docs/cross_app_auth.md) — shared Cognito pool architecture across apps
