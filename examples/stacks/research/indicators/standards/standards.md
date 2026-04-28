# Indicator Wizard Standards

This directory contains minimal schema stubs for the indicator onboarding workflow.
They are intentionally lightweight for the POC and can be expanded later.

## Schemas
- `variable_catalog.schema.json`: Raw variables extracted from form JSON.
- `computed_variables.schema.json`: User intent + compiled computation rules.
- `indicator_config.schema.json`: Indicator definitions and graph intents.
- `graph_intent.schema.json`: Visualization intent metadata.
- `excel_rules.md`: Heuristics for flattenable vs matrix-style sheets.
- `field_aliases.schema.json`: Canonical field names + aliases across forms and Excel.

## Notes
- Prefer JSONLogic for compiled expressions when possible; allow JS fallback.
- Evidence fields are optional but recommended for traceability.
