# Formidable vision agent (backend)

The backend for **Formidable** — digitises handwritten ecological survey forms.
A Fargate worker runs the `codex` CLI over an uploaded PDF and produces a
structured xlsx + crop images. Self-contained Python (no imports from
`../../server/`).

## >>> DEPLOY <<<  and what it affects

Deploy the whole backend with:

```
cd deploy
./deploy.sh
```

This reads your local codex auth, builds and pushes both images, updates the
Lambda + Fargate task def, then runs one real codex job against prod and auto
rolls back if it fails. See `form-idable/docs/ops.md` for the full flow.

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

## This is a peer backend behind the shared gateway

- Routes `/vision/*` hang off the **`form-idable-api`** API Gateway and the
  **`cognito-jwt`** authorizer — both **created by `../../server/deploy/`**, not
  here. This agent *reuses* them; it never creates a gateway.
- Runs on the shared **`form-idable-agents`** ECS cluster (config in
  `../deploy/config.sh`, sourced by `deploy/config.sh`).

## Where the docs are

Full documentation lives in the **`form-idable`** repo (the frontend/data/docs
side), sibling to good-shepherd:

- `form-idable/docs/architecture.md` — components, data flow, repo/infra ownership
- `form-idable/docs/deployment.md` — first-time setup + deploy
- `form-idable/docs/ops.md` — **operations: nightly regression, debugging, rollback, secrets**
- `form-idable/docs/scaling.md` — concurrency + cost
- `form-idable/CLAUDE.md` — agent index (start here if you have both repos)

## Layout

```
main.py            Lambda HTTP handler (upload → S3 + DynamoDB → ecs.run_task)
worker.py          Fargate worker (codex exec → S3; MODE=regression path)
vision_agent.py    job status helpers
xlsx_diff.py       tolerant structure-agnostic xlsx diff (regression scoring)
prompts/           codex + system prompts
tools/render_page.py   crop/zoom CLI the agent calls
deploy/            build / push / setup / teardown / run_* + config.sh (source of truth for IDs)
regression/        nightly suite: schedule.sh, toggle.sh, run_once.sh, upload_golden.sh
```

Deploy: `deploy/deploy.sh` (build+test → push). Ops: see `form-idable/docs/ops.md`.
