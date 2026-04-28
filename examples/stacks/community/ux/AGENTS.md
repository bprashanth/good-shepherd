# Nursery UX POC Agent Instructions

## Goal
Build UX prototypes (including voice UX) for the Nursery Frappe app, grounded in the Frappe UX spec.

### Required reading order
1. Repo rules: ../../../AGENTS.md
2. Project map: ../../../.agent/rules/project-context.md
3. Nursery Frappe UX spec (primary): ../frappe/UX.md
4. Optional: ../frappe/DESIGN.md and ../frappe/IMPLEMENTATION.md

### Scope
- Default to implementing prototype code only inside this directory (ux/).
- Do NOT modify the Frappe app unless explicitly requested.
- If you need schemas/contracts, prefer reading:
  - ../frappe/frappe-bench/apps/nursery (doctypes/APIs)
  - ../frappe/schemas (if present)

### Output expectations
- Keep prototypes lightweight and runnable locally.
- Maintain scenarios in ./scenarios/ that can be replayed in the harness.

