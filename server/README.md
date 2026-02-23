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

### Verify the deployment

Create `deploy/test-credentials.env` if it doesn't exist:

```
TEST_USERNAME=someuser@foo.com
TEST_PASSWORD='Somepassword'
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
5. Tests authenticated JSON→Excel upload
6. Tests authenticated image→Excel upload (Textract)
7. Tests authenticated sessions endpoint
8. Verifies unauthenticated sessions access is blocked

Each test prints the curl command for manual rerun.

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
- [**Client Integration Guide**](docs/manuals/client_integration.md) — how to authenticate and call every endpoint (request/response examples, token handling, migration from static `db.json`)
- [`docs/cross_app_auth.md`](docs/cross_app_auth.md) — shared Cognito pool architecture across apps

## Documentation and file layout 

```
server/
├── main.py                  # FastAPI app, CORS, router registration
├── docs/
│   ├── design/server_design.md     # Architecture + Docker strategy
│   ├── design/session_api.md       # Sessions/sites API design
│   ├── manuals/cross_app_auth.md    # Shared Cognito pool design
│   ├── manuals/client_integration.md    # Integrating a new client
│   └── checkpoint.md        # Implementation checkpoint
├── routers/
│   ├── upload.py            # /api/upload, /api/upload/json
│   ├── analyze.py           # /api/analyze, /api/analyze/json
│   └── sessions.py          # /api/sessions/{org}, /api/sites/{org}
├── services/
│   ├── textract_service.py  # AWS Textract wrapper
│   ├── table_extractor.py   # Textract response → structured data
│   ├── excel_service.py     # Structured data → .xlsx bytes
│   ├── s3_service.py        # S3 utilities (list, fetch, presign)
│   └── sessions_service.py  # Session/sites fetch + transform
├── Dockerfile               # Python 3.12 + Lambda Web Adapter
├── docker-compose.yml       # Integration test (mounts ~/.aws)
├── .gitignore               # Deploy secrets, Python bytecode
├── requirements.txt
├── deploy/
│   ├── config.sh            # Shared constants (region, ECR, Cognito from S3)
│   ├── setup.sh             # One-time infra (ECR, IAM, API Gateway)
│   ├── build.sh             # Docker build + smoke test
│   ├── push.sh              # ECR push + Lambda create/update
│   ├── deploy.sh            # Orchestrator: build → test → push
│   ├── add-user.sh          # Idempotent Cognito user creation
│   ├── trust-policy.json    # Lambda assume-role
│   ├── lambda-policy.json   # Textract + CloudWatch permissions
│   ├── outputs.env          # (generated) API Gateway ID, URL, etc.
│   └── test-credentials.env # (gitignored) TEST_USERNAME, TEST_PASSWORD
└── test/
    ├── test_local.sh        # Dev verification
    ├── test_deployment.sh   # Prod verification
    └── forms/               # Test data (Textract fixtures)
        ├── 000_layout.json
        ├── 001_layout.json
        ├── 002_layout.json
        └── handwritten.jpg
```
