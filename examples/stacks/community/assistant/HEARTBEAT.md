# Heartbeat (Proactive Scheduler)

Purpose: A background process that runs on a schedule to surface overdue tasks.

## Schedule
- Example: every 24h at 07:00

## Logic (POC)
1. Fetch all `Batch` records with stage = `germination`.
2. For each batch, compute expected germination date using Species protocols
   (from `examples/stacks/community/inputs/data/Auroville protocol data.xlsx`).
3. If overdue, send a proactive message with a concrete request.

## Example Message
"Manager: check Bed B1 (Magnolia, batch 03-01-24-MAG...): tell me how many seeds have germinated so I can update the system."

## Output
- A daily/weekly plan that compares expected protocol milestones with observed events.
- Suggested actions (e.g., check germination, record growth, transplant).

## Frappe API calls
- `GET /api/resource/Batch` (filters by stage)
- `GET /api/resource/Species` (protocol fields)
- `POST /api/resource/Nursery Event` (only after confirmation)

