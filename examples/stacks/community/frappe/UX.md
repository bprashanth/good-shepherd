# Nursery Voice/Image UX (POC)

This document describes voice/image-assisted workflows and how they map to Frappe DocTypes and API calls.
The goal is to help a future team build a conversational layer that guides field and nursery staff without requiring them to track IDs.

## Principles

- All actions are confirmed before write: the system proposes a change and asks for explicit confirmation.
- IDs are internal. Users speak in natural terms (species, bed, section, counts, dates).
- Voice/image input yields structured intents; the system fills missing fields by asking targeted questions.
- Frappe remains the source of truth; the conversational layer only creates records/events.

## Entities and Doctypes (Mapping)

- Species -> `Species`
- Collection -> `Collection`
- Batch -> `Batch`
- Batch allocations -> `Batch Allocation` (child on Batch)
- Events -> `Nursery Event`
- Sections/Beds -> `Section`, `Bed`
- Indicators -> Reports/Dashboard (read-only)

## API Patterns (Frappe)

- Create/update DocType: `POST /api/resource/<DocType>` or `PUT /api/resource/<DocType>/<name>`
- Search: `GET /api/resource/<DocType>?filters=[...]&fields=[...]`
- Reports: `POST /api/method/frappe.desk.query_report.run` with `report_name` and `filters`

## 1) Collection Flow (Voice + Image)

User input (voice + image):
- "Collected seeds from banyan near the stream, local name ‘pichu’, today morning." + photo

System intent:
- create a Collection record
- infer timestamp and GPS from device metadata
- resolve species using local name or fuzzy match

System prompts (clarification examples):
- "I found 2 species matches: Ficus benghalensis and Ficus religiosa. Which is correct?"
- "What was the condition? (fresh / slightly old / old)"
- "What was the seed site? (parent tree / bird scat / ... )"

Create on confirm:
- `Collection` with `date_collected`, `species`, `item_type`, `condition`, `seed_site`, `gps_latitude`, `gps_longitude`, `locality`, `remarks`

Backend actions:
- If species not found, propose: "Create new Species: <name>?" then `POST Species`.

## 2) Processing / Protocol Lookup (Voice)

User input:
- "Show processing instructions for yesterday’s magnolia collections."

System intent:
- find unbatched collections for species
- show Species.protocol fields (processing, germination time/percent)

Read queries:
- `GET Collection` where species = X and not allocated to any batch
- `GET Species` for `processing`, `germination_time`, `germination_percent`

Response example:
- "You have 5 unbatched Magnolia collections. Processing: soak overnight and remove pulp. Proceed?"

## 3) Batching + Sowing (Voice)

User input:
- "Sow the magnolia seeds collected yesterday in bed B1."

System intent:
- create a Batch
- link to Collection(s)
- set bed/section

System prompts:
- "Which collection IDs should I include? I found 3 from yesterday: C-12, C-13, C-15."
- "How many seeds in this batch?"
- "Which section is bed B1 in? (If unknown, propose to create Section/Bed)"

Create on confirm:
- `Batch` with `species`, `total_seeds`, `date_sown`, `bed`, `section`, `stage = sowing`
- `Batch Allocation` rows (collection + quantity)

Backend actions:
- If bed/section doesn’t exist, propose creation:
  - `POST Section` (section_name)
  - `POST Bed` (bed_name, section, bed_type)

## 4) Germination Observation (Voice)

User input:
- "Magnolia, 50 seeds, germinated 12 today in bed B1."

System intent:
- find matching batch(es)
- add a germination event

Disambiguation:
- "I found two Magnolia batches: B1 (sown 2025-05-10) and B2 (sown 2025-05-12). Which one?"

Create on confirm:
- `Nursery Event` with `event_type = germination`, `event_date`, `quantity`

Stage update:
- set Batch.stage = `germination`

## 5) Transplant (Voice)

User input:
- "Move the magnolia seedlings from B1 to D3, 40 seedlings."

System intent:
- create transplant event
- set stage to growing

Create on confirm:
- `Nursery Event` with `event_type = transplant`, `quantity`, `from_section`, `from_bed`, `to_section`, `to_bed`
- update `Batch.stage = growing`

## 6) Growth Observation (Voice)

User input:
- "Magnolia batch in D3: min height 12 cm, max 18 cm."

System intent:
- add a growth event

Create on confirm:
- `Nursery Event` with `event_type = growth`, `min_height_cm`, `max_height_cm`, `event_date`

## 7) Move (Operational)

User input:
- "Shift 20 seedlings from D3 to D4."

System intent:
- create a move event (does not change stage)

Create on confirm:
- `Nursery Event` with `event_type = move`, `from_section`, `from_bed`, `to_section`, `to_bed`, `quantity`

## 8) Exit / Sale (Voice)

User input:
- "Sell 30 magnolia from batch B1 today."

System intent:
- create exit event
- set stage to exit

Create on confirm:
- `Nursery Event` with `event_type = exit`, `quantity`, `event_date`
- update `Batch.stage = exit`

## 9) Indicator Questions (Voice)

Examples:
- "How many batches are in germination right now?"
- "What’s the avg germination rate for Magnolia?"
- "Show height distribution for neem."

Backend actions:
- Use report API: `frappe.desk.query_report.run` with filters
- Return summary text and optionally chart URLs

## Clarification Prompts (Template)

- "I found multiple matches: {option1}, {option2}. Which one?"
- "I need the bed and section for this batch. Which bed should I use?"
- "Should I create a new batch with {count} seeds from collections {list}?"
- "I will record a {event_type} event for {quantity} on {date}. Confirm?"

## Confirmation Response Example

User: "Magnolia, germinated 12 in B1 today."
System: "I will create a germination event for batch B1 (Magnolia), quantity 12, date 2025-05-22. Confirm?"
User: "Yes"
System: creates event and returns "Saved."

