# Server Architecture

## Overview

The FastAPI server (`server/`) processes form images via AWS Textract and returns
structured Excel files. The same Docker image runs locally with `uvicorn` and on
AWS Lambda via the Lambda Web Adapter — zero code changes between environments.

## Dockerfile

```
server/Dockerfile
```

Uses `python:3.12-slim` with the
[AWS Lambda Web Adapter](https://github.com/awslabs/aws-lambda-web-adapter)
(`public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1`). The adapter binary is
copied to `/opt/extensions/lambda-adapter` and is inert without the Lambda
Runtime API, so the same image works with plain `docker run`.

Key env vars:
- `PORT=8070` / `AWS_LWA_PORT=8070` — port uvicorn listens on
- `AWS_LWA_READINESS_CHECK_PATH=/api/health` — adapter polls this before
  forwarding traffic

## Local Development

### Bare uvicorn (fastest iteration)

```bash
cd server
uvicorn main:app --host 0.0.0.0 --port 8070 --reload
```

Uses `~/.aws` credentials for Textract.

### Docker Compose (integration testing)

```bash
docker compose up --build
curl http://localhost:8070/api/health
```

`docker-compose.yml` mounts `~/.aws` read-only and sets
`AWS_REGION=ap-south-1`.

## Deploy Scripts

All scripts live in `deploy/`:

| Script | Purpose |
|---|---|
| `config.sh` | Shared constants (region, account, ECR repo, Lambda name, Cognito IDs) |
| `setup.sh` | One-time idempotent infra: ECR repo, IAM role, API Gateway + JWT authorizer, routes |
| `build.sh` | `docker build` + optional `--test` smoke test |
| `push.sh` | ECR login, tag, push, create/update Lambda function |
| `deploy.sh` | Orchestrator: build → test → push, prints API Gateway URL |
| `add-user.sh` | Create Cognito user with permanent password (no temp password flow) |

### IAM Role

`deploy/trust-policy.json` — Lambda assume-role trust.
`deploy/lambda-policy.json` — inline policy grants:
- `textract:AnalyzeDocument`
- CloudWatch Logs (`logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`)

### API Gateway

HTTP API with:
- `GET /api/health` — no auth (for uptime monitors)
- `POST /api/{proxy+}` — JWT authorizer (Cognito)
- CORS: `Access-Control-Expose-Headers: X-Form-Summary`

JWT authorizer validates tokens from the shared Cognito pool
(`ap-south-1_28HVATwK2`, client `1j0f2k3top2af4m8da7nbmeu63`).

## Environment Variables

| Var | Local | Lambda |
|---|---|---|
| `AWS_REGION` | Set via docker-compose or shell | Set by Lambda runtime |
| `AWS_DEFAULT_REGION` | Set via docker-compose | Set by Lambda runtime |
| `PORT` | Dockerfile default 8070 | Dockerfile default 8070 |

No secrets in env vars — Lambda uses its execution role for AWS API calls,
local dev uses `~/.aws` credentials.

## Deployment Flow

```
docker build → local smoke test → ECR push → Lambda create/update
                                                    ↓
                                          API Gateway routes
                                          (JWT auth on POST)
```

1. `./deploy/setup.sh` — creates ECR, IAM, API Gateway (idempotent)
2. `./deploy/deploy.sh` — builds, tests, pushes, prints URL
3. Verify: `curl <url>/api/health` returns 200, unauthenticated POST returns 401
