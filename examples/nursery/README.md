# Nursery POC (Index)

This folder contains the Frappe nursery app, ETL inputs, and assistant/UX scaffolding.

## Quick Map
- `frappe/` – Frappe app, doctypes, reports, dashboards, and ETL logic.
- `inputs/` – source datasets + ETL docs/scripts.
- `assistant/` – clawdbot rulebook, context, memory, and heartbeat schedule.
- `ux/` – harness + scenarios for human interaction testing.

## Mental Model
- Frappe is the system of record (DocTypes + Events).
- The assistant interprets user intent and writes to Frappe via APIs.
- UX harness exercises voice/text/image flows and scenarios.

See `frappe/UX.md` for user flows and API mappings.
