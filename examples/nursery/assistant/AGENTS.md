# Nursery Assistant Agent Instructions

## Applies when working in: examples/nursery/assistant/
Follow the repo root AGENTS.md first, then this file.

### Required reading order
1. Repo rules: ../../../AGENTS.md
2. Project map: ../../../.agent/rules/project-context.md
3. Assistant rulebook: ./SKILL.md
4. Assistant context: ./CONTEXT.md
5. Few-shot patterns: ./CONVERSATIONS.md
6. Memory and reminders: ./MEMORY.md
7. Heartbeat schedule + logic: ./HEARTBEAT.md
8. Nursery UX spec: ../frappe/UX.md
9. Nursery design + implementation: ../frappe/DESIGN.md, ../frappe/IMPLEMENTATION.md

### Scope
- This directory defines the conversational layer (clawdbot).
- It should only call Frappe APIs and read UX scenarios.
- Do NOT edit Frappe app code unless explicitly requested.

### Context pointers
- Frappe Doctypes + logic: ../frappe/frappe-bench/apps/nursery
- ETL mappings + scripts: ../inputs/data/ETL.md and ../inputs/data/
- UX harness + scenarios: ../ux/
