# Formidable vision agent (backend)

The backend for **Formidable** — digitises handwritten ecological survey forms.
A Fargate worker runs the `codex` CLI over an uploaded PDF and produces a
structured xlsx + crop images. Self-contained Python (no imports from
`../../server/`).

## >>> DEPLOY <<<  and what it affects

Choose the release surface explicitly:

```
cd deploy
./deploy.sh credentials  # shared Codex auth only; no rebuild
./deploy.sh low          # shared Lambda + Low worker
./deploy.sh high         # shared Lambda + High worker
./deploy.sh all          # shared Lambda + both workers
```

Every mode verifies real Low and High routes and rolls back only the changed
surface. Code releases never rotate credentials; credential rotation never
rebuilds images. The authoritative details are in `docs/deployment.md`.

WHO IS AFFECTED when you run `deploy.sh` here:

- The **Formidable PWA** (Netlify, https://fomoscribe.netlify.app), source at
  `form-idable/pwa/`. It talks to the `/vision/*` and `/api/jobs/*` routes this
  backend serves. A broken deploy breaks uploads, extraction, and review for
  every user of that site. The auto rollback exists to protect them.
- The **nightly regression** (`regression/`, EventBridge schedule
  `formidable-nightly-regression`), which exercises this same worker image.
- Completion and regression **emails** (SES). The link in those emails is set by
  `PWA_URL` in `deploy/config.sh` and baked into the task def on each deploy.

`deploy.sh` here does NOT deploy the PWA. The frontend ships separately via
Netlify on a push to `form-idable`'s `main` branch.

The production High pipeline is owned by `high_pipeline/` in this directory.
Docker builds are self-contained and do not read files from the Formidable
frontend/benchmark repository. Promote experimental benchmark changes here only
after they pass Formidable's frozen evaluation ladder.

## This is a peer backend behind the shared gateway

- Routes `/vision/*` hang off the **`form-idable-api`** API Gateway and the
  **`cognito-jwt`** authorizer — both **created by `../../server/deploy/`**, not
  here. This agent *reuses* them; it never creates a gateway.
- Runs on the shared **`form-idable-agents`** ECS cluster (config in
  `../deploy/config.sh`, sourced by `deploy/config.sh`).

## Where the docs are

Backend deployment documentation lives with the backend; product and evaluation
documentation lives in the sibling Formidable repository:

- `docs/deployment.md` — authoritative credentials/Low/High/all release modes
- `form-idable/docs/architecture.md` — components, data flow, repo/infra ownership
- `form-idable/docs/deployment.md` — frontend and cross-repository release order
- `form-idable/docs/ops.md` — **operations: nightly regression, debugging, rollback, secrets**
- `form-idable/docs/design/evals.md` — model, pipeline and browser gates
- `form-idable/docs/chronology.md` — experiment/release record format
- `form-idable/docs/scaling.md` — concurrency + cost
- `form-idable/CLAUDE.md` — agent index (start here if you have both repos)

## Layout

```
main.py            Lambda HTTP handler (upload → S3 + DynamoDB → ecs.run_task)
worker.py          Fargate worker (codex exec → S3; MODE=regression path)
high_worker.py     High orchestrator (primary + bounded readers + ecology)
high_pipeline/     Canonical production High pipeline copied into Docker
vision_agent.py    job status helpers
xlsx_diff.py       tolerant structure-agnostic xlsx diff (regression scoring)
prompts/           codex + system prompts
tools/render_page.py   crop/zoom CLI the agent calls
deploy/            build / push / setup / teardown / run_* + config.sh (source of truth for IDs)
regression/        nightly suite: schedule.sh, toggle.sh, run_once.sh, upload_golden.sh
```

Deploy: `deploy/deploy.sh {credentials|low|high|all}`. Ops: see
`form-idable/docs/ops.md`.
