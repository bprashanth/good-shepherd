# Testing

This server has two main verification paths:

- `server/test/test_local.sh` for local FastAPI checks
- `server/test/test_deployment.sh` for deployed API checks

There is also a helper script for fetching a fresh sessions snapshot:

- `server/test/get_db.sh --org <org>`

And a verification wrapper for checking site-id mismatches between live
sessions data and the live sites config:

- `server/test/verify_sites.py --org <org>`

## Required config files

The deployment-oriented test scripts rely on these files:

- `server/deploy/config.sh`
- `server/deploy/outputs.env`
- `server/deploy/test-credentials.env`

`config.sh` resolves shared AWS settings and Cognito config. `outputs.env`
contains the deployed API Gateway URL. `test-credentials.env` provides the
test user credentials used to obtain a Cognito ID token.

If you want to verify the environment manually before running tests:

```bash
source server/deploy/config.sh
source server/deploy/outputs.env
source server/deploy/test-credentials.env
```

If `config.sh` cannot fetch Cognito values from S3, export them explicitly:

```bash
export COGNITO_POOL_ID=ap-south-1_xxxxxxxx
export COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Local testing

Run:

```bash
server/test/test_local.sh
```

This checks the local server endpoints. Start the server first if needed:

```bash
cd server
uvicorn main:app --host 0.0.0.0 --port 8070 --reload
```

## Deployment testing

Run:

```bash
server/test/test_deployment.sh
```

This script:

1. Ensures the test user exists in Cognito
2. Verifies unauthenticated protected endpoints return `401`
3. Verifies `GET /api/health` returns `200`
4. Obtains a Cognito ID token
5. Calls authenticated upload endpoints
6. Calls `GET /api/sessions/ncf`
7. Verifies unauthenticated sessions access is blocked

## Fetching a fresh sessions db

Use `get_db.sh` when you want a fresh local snapshot of the sessions payload
for a specific organization:

```bash
server/test/get_db.sh --org ncf
```

You can change the output path:

```bash
server/test/get_db.sh --org t4gc --out /tmp/t4gc.json
```

By default it writes:

```text
server/test/photomon/db.<org>.fresh.json
```

The script uses the same flow as `test_deployment.sh`:

1. Source `server/deploy/config.sh`
2. Source `server/deploy/outputs.env`
3. Source `server/deploy/test-credentials.env`
4. Obtain a Cognito ID token with `aws cognito-idp initiate-auth`
5. Call `GET /api/sessions/<org>`
6. Pretty-print the JSON to the output file

## Verifying db sites against sites.json

Use `verify_sites.py` when you want to compare the live `/api/sessions/{org}`
site ids with the live `/api/sites/{org}` site ids after applying the same
normalization rule used by `test/photomon/create_db.py`.

Run:

```bash
server/test/verify_sites.py --org ncf
```

By default it writes:

```text
server/test/photomon/db.<org>.fresh.json
server/test/photomon/sites.<org>.fresh.json
server/test/photomon/site_diff.<org>.txt
```

The report starts by documenting the aliasing rule:

- strip a leading year prefix like `2024_` or `2019-`
- remove underscores and dashes
- compare the normalized ids

It then lists:

1. `db.json` raw `siteId` values mapped to canonical ids
2. `sites.json` raw `id` values mapped to canonical ids
3. Canonical ids present in `db.json` but missing from `sites.json`
4. Canonical ids present in `sites.json` but missing from `db.json`

This is the quickest way to identify genuinely new sites versus legacy aliases
such as `2019_LA_R1 -> P1R1`.

## Common failure modes

- Missing `deploy/outputs.env`: run `server/deploy/setup.sh` or redeploy
- Missing `deploy/test-credentials.env`: create the file with `TEST_USERNAME`
  and `TEST_PASSWORD`
- Empty `COGNITO_POOL_ID` or `COGNITO_CLIENT_ID`: `config.sh` could not load
  auth config, so export both values manually
- `401` from the API: the token is missing, invalid, expired, or for the wrong
  pool/client
