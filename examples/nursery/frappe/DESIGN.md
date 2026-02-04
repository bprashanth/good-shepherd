# Nursery Management (Frappe) — POC Design

This document covers Stage 1 outputs:
1) A working Frappe setup (Docker-based).
2) A design plan for Stage 2 implementation.

It is organized into three sections:
- **Up and Running**: Docker/Compose setup.
- **POC (Option A)**: Frappe Desk only, minimal UI.
- **Custom UI (Option B)**: Humanized workflows layered on top of DocTypes.

---

## 1) Up and Running (Docker)

**Goal**: bring up a local Frappe instance quickly without installing dependencies on the host.

**Why Docker**:
- Minimal host changes (no local MariaDB/Redis/Node setup).
- Easy teardown and reproducible runs.

**Approach**:
- Run a standard Frappe container stack with MariaDB + Redis.
- Keep the POC app inside `examples/nursery/frappe`.

**Notes**:
- The POC targets a single nursery site.
- Offline use is out of scope for the POC.
- No custom workflows required for Stage 1.

(Implementation details to be added in the setup steps; e.g., compose file, volumes, and a basic bench site.)
See [IMPLEMENTATION.md](IMPLEMENTATION.md) for details. 
---

## 2) POC (Option A): Frappe Desk Only

### 2.1 Core Concepts: Records vs Events

**Records (durable entities)**
- *Species*, *Nursery*, *Section*, *Bed*, *Collection*, *Batch*.
- A record is created once and persists over time.

**Events (transactions)**
- *Germination*, *Move*, *Transplant*, *Treatment*, *Growth Observation* (height), and *Failure*.
- Events describe changes to a batch over time.
- **State is derived from events** (you never edit inventory directly).

### 2.2 Stages (default, editable)

- collection
- sowing
- germination
- growing
- planting

Stages map to **Sections** by default. Each Section can contain one or more Beds.
For the POC, initialize as **1:1 Section:Bed**, but allow more beds later.

### 2.3 Entity Model Summary

**Species**
- Master list of species used across all records.

**Nursery**
- Single nursery for the POC; design supports multiple in future.

**Section**
- Conceptual stage or area (e.g., germination, growing).

**Bed**
- Physical location within a Section (beds, trays, covers, etc.).

**Collection**
- Field collection from a specific source/time/location.

**Batch**
- Nursery unit of work. **Batch creation = sowing** in the POC.

**Allocation (Collection ↔ Batch)**
- Explicit user-facing link from Collection(s) into Batch(es).
- Needed because **collection and batch are many-to-many**:
  - One collection can be split into multiple batches.
  - Multiple collections can be combined into one batch.

### 2.4 POC Assumptions

- **Batch is atomic** for the POC: one person handles one batch end-to-end.
- **Batch creation implies sowing** (no separate sow event).
- **Germination entries are absolute counts** (not deltas).
  - Example: “Batch 7 now has 10 germinated.”
  - The system stores this observation and derives the change.
- **Failure is auto-derived at cutoff**:
  - When a germination observation is recorded, failure can be inferred as
    `total seeds - germinated count` for that batch at the cutoff date.
  - An explicit failure event can also be recorded when deaths are observed in germination or growing.

### 2.5 Typical Journey (Collection -> Planting)

1) **Collection**
   - Field team creates a Collection record with GPS/species/etc.

2) **Allocation + Batch Creation (Sowing)**
   - Nursery team creates a Batch (this is the sowing event for the POC).
   - They link Collection(s) to this Batch via Allocation with quantities.

3) **Germination Monitoring**
   - Nursery team logs germination events as **absolute counts** over time.
   - The system derives change and tracks earliest/last germination dates.

4) **Movement / Transplant**
   - Movement event captures from-bed and to-bed.
   - Transplant event is used when moving to a new container or growth stage.

5) **Planting**
   - Final status is recorded as a transplant/movement into planting section.
   - No deletion — records are retained for audit.

### 2.6 User Actions (POC)

**Add a new Bed or Bed Type**
- Create a Bed under a Section (bed type from categories).

**Add a new Species**
- Add to Species master list with metadata (habit, seed size, etc.).

**Add a new Collection**
- Create Collection with source location, species, and collection metadata.

**Create a new Batch**
- Create Batch (this implies sowing).
- Allocate Collection(s) into the Batch with quantities.
- Assign Bed and Section at creation.

**Add an Event**
- Germination: record absolute count.
- Movement: record from-bed → to-bed and quantity.
- Transplant: similar to movement but marks stage change.
- Treatment: record treatment type (e.g., soaking) and notes.
- Growth Observation: record height for the batch (e.g., in cm).
- Failure: record explicit deaths (germination or growing).

### 2.7 Indicators (examples)

Proposed indicators (also captured in metadata schema defaults):
- **Germination Rate**: germinated_count / total_seeds.
- **Earliest Germination Date**: min(germination_event_date).
- **Latest Germination Date**: max(germination_event_date).
- **Germination Spread**: latest_germination_date - earliest_germination_date.
- **Failure Rate**: failed_count / total_seeds (auto-derived at cutoff).
- **Stock by Stage**: summed counts grouped by section stage.
- **Height Distribution**: min/avg/max height by species or batch.

All indicators should be sliceable by species, batch_id, date range, and nursery.

---

## 3) Custom UI (Option B): Humanized Workflows

Option B keeps DocTypes as the data layer but adds custom flows for field staff.
It is a tiered UI: **Frappe Desk = base**, **Custom Pages = easy flow**.

### 3.1 Principles

- **Bed-first** workflow: select the bed, then the batch.
- **Absolute counts only**: user enters the current value, system derives change.
- **Minimal fields**: small dialogs, prefilled defaults, no ID typing.

### 3.2 Frappe Tools for Custom UI

- **Quick Entry**: reduces fields for core DocTypes.
- **Web Forms**: minimal entry flows for field staff.
- **Custom Page + Dialog**: add “Record Germination” / “Move Batch” actions.
- **Barcode/QR scan** (optional): select bed/batch by scan.

### 3.3 API Notes (if building custom screens)

- Create event:
  - `POST /api/resource/Nursery Event`
- Read batch:
  - `GET /api/resource/Nursery Batch/<name>`
- List beds:
  - `GET /api/resource/Nursery Bed?fields=...`
- Custom logic:
  - Use `frappe.client.*` or custom ` /api/method/...`

### 3.4 Why Option B Helps

- Fewer taps and no manual ID lookup.
- Works better for field users with low bandwidth.
- Keeps data integrity through shared DocTypes and rules.

## 3.5 GIS Note (Simple Heatmap)

Collection records include GPS coordinates (EPSG:4326). A simple heatmap can be generated by:
- Aggregating collection points by species or date range.
- Rendering on a map view (basic map widget or export to GeoJSON for a simple web map).

---

## Appendix: Schema References

See:
- `examples/nursery/frappe/schemas/nursery_entities.schema.json`
- `examples/nursery/frappe/schemas/nursery_events.schema.json`
- `examples/nursery/frappe/schemas/nursery_metadata.schema.json`

## Appendix: Frappe DocType Mapping (POC)

This mapping shows how the schemas translate into Frappe DocTypes.

**Core DocTypes (records)**
- **Species**
  - Fields: accepted_name, era_species_url, name_source, iucn_status, habit, fruit_size, seed_size, seed_no.
- **Nursery**
  - Fields: nursery_id, name, region, notes.
- **Section**
  - Fields: section_id, nursery_id (Link: Nursery), name, stage.
- **Bed**
  - Fields: bed_id, section_id (Link: Section), name, bed_type, notes.
- **Collection**
  - Fields: collection_id, date_collected, species (Link: Species), item_type, condition, seed_site,
    gps_latitude, gps_longitude, gps_elevation, locality, collected_by, remarks, delivery_date.
- **Batch**
  - Fields: batch_id, species (Link: Species), total_seeds, date_sown, bed_id (Link: Bed), section_id (Link: Section),
    planted_by, remarks.
  - Rule: batch creation implies sowing in the POC.
- **Allocation**
  - Fields: allocation_id, collection_id (Link: Collection), batch_id (Link: Batch), quantity, allocation_date.
  - Purpose: explicit user-facing traceability between collection sources and batches.

**Event DocType (transactions)**
- **Nursery Event**
  - Fields: event_id, batch_id (Link: Batch), event_type, event_date, absolute_count, quantity_moved,
    from_bed_id (Link: Bed), to_bed_id (Link: Bed), treatment_type, height_cm, notes.
  - Event types: germination, move, transplant, treatment, growth_observation, failure (auto-derived at cutoff or explicit).
  - Rule: events store absolute observations; state is derived from the event log.
