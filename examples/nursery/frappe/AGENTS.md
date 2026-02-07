# Nursery / Frappe Subproject Agent Instructions

## Applies when working in: examples/nursery/frappe/
Follow the repo root AGENTS.md first, then this file.

### Required context
1. Repo rules: ../../../AGENTS.md
2. Project map: ../../../.agent/rules/project-context.md
3. App code: frappe-bench/apps/nursery, other frappe boilerplate apps are ignored via .gitignore

### Subproject docs (read before proposing changes)
- UX: ./UX.md
- Design: ./DESIGN.md
- Implementation plan: ./IMPLEMENTATION.md
- Additional notes: ./docs/ and ./schemas/

### Scope & guardrails
- This directory contains the Frappe-based nursery app + supporting docker/bench scripts.
- Prefer making changes inside this directory only when the task is explicitly about the Frappe app.
- Avoid touching other `examples/` POCs unless asked.

### Runtime / commands
- If testing, the site will be available on `nursery.localhost:8000`. If not, ask user to start docker. 
- Treat mariadb_data/ and logs/ as runtime artifacts; avoid committing accidental changes there.

### Related POC
- Voice UX prototype lives at: ../ux/voice/
- Voice POC may reference this directory’s UX.md, schemas/, and any API/UI contracts.

