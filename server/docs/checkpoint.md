# Phase 5 Checkpoint — Docker, Lambda, Cognito Auth

**Branch:** `assistant`
**Status:** Steps 1–7 complete. Server deployed, auth verified end-to-end via CLI. Frontend auth not yet tested in browser.

## What was done

- **Docker**: `server/Dockerfile` (Python 3.12-slim + Lambda Web Adapter),
  `server/.dockerignore`, `server/docker-compose.yml`
- **Deploy scripts**: `server/deploy/{config,setup,build,push,deploy,add-user}.sh`,
  `server/deploy/{trust-policy,lambda-policy}.json`
- **Test scripts**: `server/test/test_local.sh` (dev),
  `server/test/test_deployment.sh` (prod e2e)
- **Frontend auth**: `useCognitoAuth.js` composable (fetches config from S3),
  `useApi.js` (Bearer token + 401 retry), `LoginView.vue`, router auth guard,
  logout button in AppHeader
- **Docs**: `docs/server_design.md`, `docs/cross_app_auth.md`,
  `server/README.md` (full workflow: add API → dev test → deploy → prod test → auth)

## What remains

Steps 1–7 are done. Pick up from Step 8 (PWA production env) onward.

## Gotchas discovered during deploy

1. **Lambda invoke permission**: `setup.sh` creates the API Gateway before the
   Lambda exists, so it can't grant the invoke permission. Fix: `push.sh` now
   grants the permission after creating/updating the Lambda.

2. **Stage path prefix**: API Gateway `prod` stage prepends `/prod` to the path,
   so Lambda receives `/prod/api/health` instead of `/api/health`. Fix: `push.sh`
   sets `AWS_LWA_REMOVE_BASE_PATH=/prod` env var on the Lambda so the Web
   Adapter strips the prefix before forwarding to uvicorn.

3. **Auth flow mismatch**: The Cognito client doesn't have
   `ALLOW_ADMIN_USER_PASSWORD_AUTH` enabled. Fix: test scripts use
   `initiate-auth` with `USER_PASSWORD_AUTH` instead of `admin-initiate-auth`.
   The PWA uses `USER_SRP_AUTH` (SDK default) which is always enabled.

4. **S3 config field names**: `auth_config.json` uses `userPoolId`/`clientId`
   (camelCase), not `user_pool_id`/`client_id`. Fixed in `useCognitoAuth.js`.

5. **Hardcoded Cognito IDs**: `config.sh` was hardcoding pool/client IDs.
   Fix: now fetches from S3 `auth_config.json` at source time. URL is
   configurable via `AUTH_CONFIG_URL` env var.

6. **Deploy scripts location**: moved `deploy/` → `server/deploy/` so the
   server + deploy is hermetic and can be lifted into its own repo.

---

## Step 1 — Local server (bare uvicorn)

```bash
cd server
uvicorn main:app --host 0.0.0.0 --port 8070 --reload
```

In another terminal:

```bash
server/test/test_local.sh
```

If the server isn't running, it prints the command to start it.

## Step 2 — Docker Compose (local container)

```bash
cd server
docker compose up --build -d
sleep 3
curl -s http://localhost:8070/api/health   # → {"status":"ok"}
docker compose down
```

## Step 3 — Deploy infra (one-time)

```bash
cd server/deploy
aws sts get-caller-identity   # verify AWS access
./setup.sh                    # ECR, IAM, API Gateway, JWT authorizer
cat outputs.env               # APIGW_ID, APIGW_URL, etc.
```

## Step 4 — Build, push, deploy Lambda

```bash
cd server/deploy
./deploy.sh
```

Builds image, smoke tests, pushes to ECR, creates/updates Lambda, sets
`AWS_LWA_REMOVE_BASE_PATH=/prod`, grants API Gateway invoke permission.

## Step 5 — Quick health check

```bash
source server/deploy/outputs.env
curl -s "${APIGW_URL}/api/health"   # → {"status":"ok"}
```

## Step 6 — Create test credentials

Create `server/deploy/test-credentials.env` (gitignored):

```
TEST_USERNAME=testuser@example.com
TEST_PASSWORD='SomePassword123!'
```

## Step 7 — Run end-to-end deployment test

```bash
server/test/test_deployment.sh
```

This script:
1. Ensures the test user exists in Cognito (idempotent via `add-user.sh`)
2. Verifies unauthenticated POST → 401
3. Verifies health → 200 (no auth)
4. Gets a JWT token via `initiate-auth` (`USER_PASSWORD_AUTH`)
5. Tests authenticated JSON → Excel upload
6. Tests authenticated image → Excel upload (Textract)

Prints every command for easy copy-paste debugging.

## Step 8 — Update PWA production env

```bash
source server/deploy/outputs.env
echo "$APIGW_URL"
```

Edit `pwa/.env.production` and replace `REPLACE_ME` with the actual API ID:

```
VITE_API_BASE_URL=https://<actual-api-id>.execute-api.ap-south-1.amazonaws.com/prod
```

## Step 9 — Test PWA locally

```bash
cd server && uvicorn main:app --host 0.0.0.0 --port 8070 --reload &
cd pwa && npm run dev
```

Open browser (usually `http://localhost:5173`):

1. **Login** — enter email + password → redirects to capture
2. **Capture** → **Crop** → **Processing** (calls `/api/upload` with Bearer token)
3. **Result** — download xlsx

Verify logout: click "Logout" in header → redirects to `/login`.

## Step 10 — Build and deploy PWA to production

```bash
cd pwa && npm run build
# dist/ ready for Netlify/Vercel/S3
```

## Phase 6 — Extract server into its own repo

**Status:** Ready. All prep work done — server is fully self-contained.

### What was done (prep)

- **`.gitignore`**: created `server/.gitignore` with `deploy/outputs.env`,
  `deploy/test-credentials.env`, Python bytecode
- **`docker-compose.yml`**: moved into `server/` with `context: .`
  (was at project root with `context: ./server`)
- **Doc references**: removed `pwa/` file paths from `cross_app_auth.md`,
  `client_integration.md` — replaced with generic patterns and pointers
  to `docs/manuals/client_integration.md`
- **README**: updated docker compose instructions to run from `server/`

### What's clean (no changes needed)

- All Python imports (stdlib, pip, or relative within `server/`)
- All deploy scripts (relative paths within `server/`)
- Dockerfile (`COPY . .` from its own context)
- requirements.txt (complete and standalone)
- Test scripts + fixtures (self-contained under `server/test/`)

### Extraction commands

```bash
# From the form-idable repo root:
cd /path/to/form-idable

# Option A: git subtree (preserves history)
git subtree split -P server -b server-extract
# Then push server-extract to a new remote repo

# Option B: simple copy (fresh history)
mkdir /path/to/new-repo && cd /path/to/new-repo
git init
cp -r /path/to/form-idable/server/* .
cp -r /path/to/form-idable/server/.* .  # .gitignore, .dockerignore
git add -A && git commit -m "Extract server from form-idable"
```

---

## Key config values

| Item | Value |
|---|---|
| Auth config URL | `https://fomomon.s3.ap-south-1.amazonaws.com/auth_config.json` |
| Cognito Pool ID | `ap-south-1_28HVATwK2` (from S3 config) |
| Cognito Client ID | `1j0f2k3top2af4m8da7nbmeu63` (from S3 config) |
| AWS Region | `ap-south-1` |
| ECR repo | `form-idable-server` |
| Lambda function | `form-idable-server` |
| IAM role | `form-idable-lambda-role` |
| API Gateway name | `form-idable-api` |
| API Gateway ID | `hachry61xe` |
| API Gateway URL | `https://hachry61xe.execute-api.ap-south-1.amazonaws.com/prod` |
| Server port | `8070` |

## Key file paths

| File | Purpose |
|---|---|
| `README.md` | Full workflow: add API, dev test, deploy, prod test, auth |
| `deploy/config.sh` | Shared constants (fetches Cognito from S3) |
| `deploy/setup.sh` | One-time infra setup (idempotent) |
| `deploy/deploy.sh` | Build → test → push orchestrator |
| `deploy/add-user.sh` | Idempotent Cognito user creation |
| `deploy/test-credentials.env` | Test user creds (gitignored) |
| `deploy/outputs.env` | Generated API Gateway IDs/URLs (gitignored) |
| `test/test_local.sh` | Dev verification (checks server is running) |
| `test/test_deployment.sh` | Prod e2e verification |
| `docs/manuals/client_integration.md` | Auth patterns + API reference for clients |
