# Nursery Frappe POC — Implementation Guide

This doc outlines how to get a working Frappe instance via Docker, where the app lives, how DocTypes and seed data are managed, and how to iterate safely.

---

## 1) Goal and Scope

**Working** means:
- `docker compose up` starts Frappe + DB successfully.
- A Frappe site exists and is reachable in the browser.
- The Nursery app is installed on the site.
- Core DocTypes (records + events) are present.
- Default metadata (stages, categories) is loaded.

---

## 2) Repo Layout (proposed)

Within `examples/nursery/frappe`:

- `docker/` — Docker Compose and supporting files.
- `apps/` — local Frappe app code (nursery app).
- `sites/` — Frappe sites (mounted volume for persistence).
- `logs/` — Frappe logs (mounted volume).
- `schemas/` — design schemas (already present).
- `DESIGN.md` — design reference.
- `IMPLEMENTATION.md` — this file.
- `run.sh` — start/stop/logs helper for the stack.

**Note**: The Docker setup should mount `apps/` and `sites/` for persistence.

---

## 3) Docker Setup Steps (high-level)

1) Create a Docker Compose file that runs:
   - Frappe stack (backend, frontend, queue, scheduler, websocket)
   - `mariadb` (db)
   - `redis-cache`, `redis-queue`
2) Mount bind volumes for `sites/`, `apps/`, and `logs/` under `examples/nursery/frappe`.
3) Start the stack with the helper script:
   - `examples/nursery/frappe/run.sh start`
4) The default site name is **frontend** (used by the nginx front proxy).
   - First start will create the site automatically.
   - The script also fetches **erpnext** into `apps/` if it is missing.

---

## 4) App Creation & Location

The custom app should live at:
- `examples/nursery/frappe/apps/nursery`

Frappe will generate the app with:
- `nursery/nursery/doctype/` (DocType definitions)
- `nursery/nursery/fixtures/` (seed data)
- `nursery/nursery/patches/` (migrations, optional)

Create the app (one-time):
- `docker compose -f examples/nursery/frappe/docker/docker-compose.yml exec backend bench new-app nursery`
- `docker compose -f examples/nursery/frappe/docker/docker-compose.yml exec backend bench --site frontend install-app nursery`

---

## 5) DocTypes: Where the Code Goes

Each DocType is created under:
- `apps/nursery/nursery/doctype/<doctype_name>/`

This generates:
- `<doctype_name>.json` (fields, metadata)
- `<doctype_name>.py` (logic, hooks)
- `<doctype_name>_test.py` (optional)

For the POC, focus on JSON definitions with minimal Python logic.

DocTypes to implement (POC):
- Species
- Nursery
- Section
- Bed
- Collection
- Batch
- Allocation
- Nursery Event

---

## 6) Seed Data (Defaults)

Recommended approach: **fixtures** for stable defaults.

- `nursery/fixtures/` should include JSON for:
  - Stages (collection, sowing, germination, growing, planting)
  - Category lists (item_type, condition, seed_site, bed_type)

Alternate approach: **patches** if defaults need logic.

---

## 7) Verification Checklist

After setup and install:
- **Docker up**: `examples/nursery/frappe/run.sh start`
  - Expect services to start and site `frontend` to be created (first run).
- **Site reachable**: open `http://localhost:8000` in browser.
  - Expect Frappe login page.
  - Login: user `Administrator`, password `admin`.
- **App installed**: `docker compose -f examples/nursery/frappe/docker/docker-compose.yml exec backend bench --site frontend list-apps`
  - Expect `nursery` in the list.
- **DocTypes present**: check DocType list in Desk.
- **Data entry smoke test**:
  - Create a Species record.
  - Create a Collection record.
  - Create a Batch record and Allocation record.
  - Add a Nursery Event (germination) with absolute count.
- **Indicators (once reports exist)**:
  - Run Script Reports filtered by species/batch/date and confirm expected totals.

---

## 8) Iteration Loop

Typical refinement cycle:
1) Modify DocType JSON or fixtures.
2) Run `bench migrate` to apply changes.
3) Refresh the site (Desk reload).
4) Verify using sample records.

If using Docker:
- Run bench commands via `docker exec` or `docker compose exec`.

Verification after each stage (expected outcomes):
- **Stage A (Docker)**: containers running; Frappe login at `http://localhost:8000`.
- **Stage B (App + Site)**: nursery app listed in `bench --site <site> list-apps`.
- **Stage C (DocTypes + Fixtures)**: DocTypes visible in Desk; defaults loaded; basic CRUD works.
- **Stage D (Indicators + Ingest)**: Script Reports return data; sample data from XLSX appears.

---

## 9) Troubleshooting Tips

- If site is not reachable, check container logs (`docker compose logs`).
- If DocTypes do not appear, ensure the app is installed on the site.
- If fixtures do not load, confirm they are listed in `hooks.py`.
- If DB errors occur, confirm MariaDB is healthy and the site config uses correct credentials.
