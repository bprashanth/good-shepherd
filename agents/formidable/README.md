# Formidable vision agent (backend)

The backend for **Formidable** — digitises handwritten ecological survey forms.
A Fargate worker runs the `codex` CLI over an uploaded PDF and produces a
structured xlsx + crop images. Self-contained Python (no imports from
`../../server/`).

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
