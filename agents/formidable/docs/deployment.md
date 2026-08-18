# Formidable backend releases

This is the authoritative runbook for releasing the Formidable Lambda and
Fargate workers. Run every command from `agents/formidable/deploy/` in a clean
Good Shepherd checkout. The backend build is self-contained and does not need
the Formidable PWA repository.

## Before every release

```bash
aws sts get-caller-identity
docker info
git status --short
git fetch origin
git rev-parse HEAD
git rev-parse origin/main
```

Deploy only a reviewed commit that is on `origin/main`. Do not deploy from a
dirty worktree. `deploy/test-credentials.env` must provide a Cognito test user;
it is gitignored. Docker builds are pinned by `deploy/config.sh`.

The scripts build the shared Lambda and Low worker explicitly for x86_64 and
High explicitly for ARM64, regardless of deployment-host architecture. Their
preflight stops before ECR changes if the required emulation is unavailable.

## Choose one release mode

| Change | Command | Rebuilt | Automated production gate |
| --- | --- | --- | --- |
| Codex login/auth only | `./deploy.sh credentials` | nothing | real Low + real High; restore captured secret on failure |
| Low worker or shared API only | `./deploy.sh low` | Lambda + Low | real Low + real High; High image/task must not move |
| High pipeline or shared API only | `./deploy.sh high` | Lambda + High | real Low + real High; Low image/task must not move |
| Shared contract, CLI versions, or both workers | `./deploy.sh all` | Lambda + Low + High | real Low + real High; restore all code images on failure |

`./deploy.sh` without an argument is an alias for `./deploy.sh all`. Credentials
are deliberately not rotated by code releases. Run the credential mode
separately when needed so an auth failure cannot be confused with an image or
model regression.

### Credentials only

Run `codex login` on the deployment machine first, then:

```bash
./deploy.sh credentials
```

Both workers fetch `formidable/codex-auth` from Secrets Manager when a task
starts; credentials are not baked into an image. The script captures the
current secret version, uploads `~/.codex/auth.json`, runs both real routes and
moves `AWSCURRENT` back to the captured version if either route fails. It never
rebuilds Lambda or a worker.

`push_high_secret.sh` manages a historical OpenRouter secret and is not the
Codex authentication path for the current High worker.

### High only

```bash
./deploy.sh high
```

This is the normal release for changes under `high_pipeline/`, `high_worker.py`
or High review/Analytics behavior. It snapshots Low's ECR digest and task ARN,
builds the ARM64 High image, updates the shared x86_64 Lambda, verifies both
routes, and rejects the release if Low moved.

### Low only

```bash
./deploy.sh low
```

This releases the shared Lambda plus the historical Low worker. Because the
Lambda routes both tiers, the script also runs the High smoke test. High's image
digest and task ARN must remain unchanged.

### All code surfaces

```bash
./deploy.sh all
```

Use this for a shared API contract change, a coordinated worker change, or a
Codex CLI version change affecting both images. It builds both images locally,
deploys the handler and both workers, then verifies real Low and High jobs.
Credentials remain unchanged.

## What the automated gates prove

`verify_prod.sh` explicitly creates an `effort=low` job, asserts that the API
selected `formidable-worker`, downloads the workbook and compares it with the
golden fixture. `verify_high.sh` explicitly selects `formidable-high-worker`
and requires a valid workbook, canonical review coordinates, red attention,
orange ecology and Analytics contracts.

These scripts prove the API, Cognito, S3, DynamoDB, task launch and artifact
paths. They do not replace the all-form benchmark or visual browser gate for a
model, layout, review or frontend change.

## Frontend releases

The PWA is independent. It deploys from Formidable's `main` branch through
Netlify. Backend additions must be backward compatible with the previous PWA;
deploy the backend first, verify it, then merge the PWA. A PWA-only change does
not require an AWS release.

For a change spanning both repositories:

1. pass backend unit/container and Formidable benchmark gates locally;
2. merge and deploy the backward-compatible Good Shepherd backend;
3. verify both API routes in production;
4. merge the Formidable PWA;
5. run the production browser gate and save screenshots;
6. record both commits and live image/task identifiers in chronology.

## Manual rollback and diagnosis

The mode wrappers roll back automatically. Component scripts remain available
for diagnosis:

- `rollback_secret.sh VERSION_ID` restores only a captured auth version;
- `rollback.sh` restores the shared Lambda and Low image/task;
- `rollback_high.sh` restores the shared Lambda and High image/task;
- `verify_prod.sh` and `verify_high.sh` can be rerun independently.

CloudWatch logs are `/ecs/formidable-worker` and
`/ecs/formidable-high-worker`. Detailed job artifacts and `run.log` are under
`s3://formidable-storage/formidable/jobs/<job_id>/`.
