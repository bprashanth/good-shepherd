# Assistant Knowledge (Protocols + Agronomy + API Reference)

Purpose: Species-specific protocols, operational notes, and Frappe API integration patterns.

Source of truth for germination protocols:
- `examples/nursery/inputs/data/Auroville protocol data.xlsx`

---

## Frappe API Integration

### Python Helper Modules
All Frappe API operations use Python modules:

**Base API client:**
```python
from frappe_client import FrappeClient

# Create authenticated client from environment variables
client = FrappeClient.from_env()
```

**High-level nursery helpers:**
```python
from nursery_helpers import *

# Get authenticated client
client = get_client()

# Use domain-specific helper functions
find_species_fuzzy(client, "magnolia")
log_germination(client, "15-01-24-MAGCHA-01", 50)
```

### Authentication
Automatically handled by `FrappeClient.from_env()` using environment variables:
- `FRAPPE_URL`: http://frappe:8000
- `FRAPPE_API_KEY`: Loaded from environment
- `FRAPPE_API_SECRET`: Loaded from environment
- `FRAPPE_SITE`: nursery.localhost (for Host header)

---

## Frappe DocType Schemas

**IMPORTANT: Use Dynamic Schema Discovery**

Instead of relying on hardcoded field lists (which can drift from reality), query the Frappe metadata API:

```python
from nursery_helpers import get_doctype_fields

# Get complete, current field list for any DocType
fields = get_doctype_fields(client, "Species")

for field in fields:
    req = "Required" if field.get('reqd') else "Optional"
    print(f"{field['label']}: {field['fieldtype']} ({req})")
    if field.get('description'):
        print(f"  {field['description']}")
    if field.get('options'):
        print(f"  Options/Link: {field['options']}")
```

This discovers:
- All current fields (including those added after docs were written)
- Child tables (local names, allocations, etc.)
- Field types, requirements, and linked DocTypes
- Field descriptions and options

---

### Child Tables

Child tables are nested data within documents. Fields with `fieldtype='Table'` contain child table data.

**Identify child tables:**
```python
fields = get_doctype_fields(client, "Species")
child_tables = [f for f in fields if f.get('is_child_table')]
```

**Get child table data:**
```python
from nursery_helpers import get_child_table_data

# Direct helper
data = get_child_table_data(client, "Species", "SPE-001", "local_names")

# Or from document
doc = client.get("Species", name="SPE-001")
data = doc.get('local_names', [])
```

**Important:** Child tables cannot be queried directly via `/api/resource/ChildTableName`.
You must get the parent document first, then access the child table field.

**Example - Finding items referenced in child tables:**
```python
# WRONG: Can't query child table directly
# allocations = client.get("Batch Allocation", ...)  # 403 FORBIDDEN

# CORRECT: Get parent documents, then access child table
batches = client.get("Batch", fields=["name"])
for batch in batches:
    batch_doc = client.get("Batch", name=batch['name'])
    allocations = batch_doc.get('batch_allocations', [])
```

---

### Species
**Purpose:** Stores information about plant species.

**Key fields:** accepted_name (scientific name), iucn_status, germination_time, germination_percent, and more

**To see all fields:**
```python
fields = get_doctype_fields(client, "Species")
```

**Python Examples:**
```python
from nursery_helpers import *

client = get_client()

# Get all species
species = client.get("Species", fields=["name", "accepted_name"], limit=20)

# Find species with fuzzy matching
results = find_species_fuzzy(client, "magnolia", limit=5)

# Find exact species
species = find_species_exact(client, "Magnolia champaca")

# Get species with filters
endangered = client.get("Species",
                       filters=[["iucn_status", "=", "EN"]],
                       fields=["name", "accepted_name", "iucn_status"],
                       limit=10)
```

---

### Collection
**Purpose:** Records seed/cutting collections from the field.

**Key fields:** date_collected, species (link), item_type, condition, gps_latitude/longitude (optional), locality, collected_by

**GPS Handling:**
- GPS coordinates are optional - can be null
- For testing without GPS device: use approximate coordinates (e.g., `12.9716, 77.5946`)

**To see all fields:**
```python
fields = get_doctype_fields(client, "Collection")
```

**Python Examples:**
```python
from nursery_helpers import *
from datetime import datetime

client = get_client()

# Create collection
collection = client.create("Collection", {
    "date_collected": datetime.now().strftime("%Y-%m-%d"),
    "species": "Magnolia champaca",
    "item_type": "seed",
    "condition": "fresh",
    "locality": "Near stream, Section A",
    "collected_by": "Field Staff",
    "remarks": "Good quality seeds"
})

# Get recent collections
recent = client.get("Collection",
                   filters=[["date_collected", ">", "2024-01-01"]],
                   fields=["name", "species", "date_collected", "locality"],
                   limit=10)

# Find unbatched collections
unbatched = find_unbatched_collections(client, species="Magnolia champaca")
```

---

### Batch
**Purpose:** Represents a group of seeds/seedlings being tracked through nursery stages.

**Key fields:** species (link), total_seeds, date_sown, section, bed, stage (sowing/germination/growing/exit), planted_by

**To see all fields:**
```python
fields = get_doctype_fields(client, "Batch")
```

**Python Examples:**
```python
from nursery_helpers import *

client = get_client()

# Create batch from collections
batch = create_batch_from_collections(
    client,
    species="Magnolia champaca",
    collection_ids=["C-001", "C-002"],
    section="B",
    bed="B1"
)

# Generate batch ID
batch_id = generate_batch_id(client, "Magnolia champaca", "2024-01-22")
# Returns: "22-01-24-MAGCHA-01"

# Get batches by stage
germinating = get_batches_by_stage(client, "germination")

# Get batches by section
section_d = get_batches_by_section(client, "D")

# Get specific batch
batch = client.get("Batch", name="15-01-24-MAGCHA-01")

# Update batch stage
client.update("Batch", "15-01-24-MAGCHA-01", {"stage": "germination"})

# Get batches for a species
magnolia_batches = get_batches_by_species(client, "Magnolia champaca")
```

---

### Nursery Event
**Purpose:** Records events that happen to batches (germination, transplant, growth, etc.).

**Key fields:** batch (link), event_type (germination/move/transplant/growth/failure/exit), event_date, quantity, from/to section/bed, min/max_height_cm, notes

**To see all fields:**
```python
fields = get_doctype_fields(client, "Nursery Event")
```

**Python Examples:**
```python
from nursery_helpers import *

client = get_client()

# Create germination event (Sowing -> Germination)
event = log_germination(client, "15-01-24-MAGCHA-01", quantity=50)

# Create transplant event (Germination -> Growing)
event = log_transplant(client, "15-01-24-MAGCHA-01",
                      from_section="B", from_bed="B1",
                      to_section="D", to_bed="D3",
                      quantity=40)

# Create growth observation (Growing -> Growing)
event = log_growth_observation(client, "15-01-24-MAGCHA-01",
                               min_height_cm=10.0,
                               max_height_cm=15.0,
                               notes="Healthy growth")

# Create exit event (Growing -> Exit)
event = log_exit_event(client, "15-01-24-MAGCHA-01",
                       quantity=30,
                       notes="Sale to customer")

# Create move event (operational, no stage change)
event = log_move_event(client, "15-01-24-MAGCHA-01",
                      from_bed="D3", to_bed="D4",
                      quantity=20)

# Create failure event (deaths)
event = log_failure_event(client, "15-01-24-MAGCHA-01",
                          quantity=10,
                          notes="Fungal infection")

# Get events for a batch
events = client.get("Nursery Event",
                   filters=[["batch", "=", "15-01-24-MAGCHA-01"]],
                   fields=["name", "event_type", "event_date", "quantity"])
```

---

## API Query Patterns

### Filter Syntax
Frappe uses Python list syntax for filters:

**Single condition:**
```python
filters=[["field", "=", "value"]]
```

**Multiple conditions (AND):**
```python
filters=[
    ["field1", "=", "value1"],
    ["field2", "=", "value2"]
]
```

**Operators:** `=`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `not in`, `like`

### Common Query Examples

**Get batches in specific stage:**
```python
batches = client.get("Batch",
                    filters=[["stage", "=", "germination"]],
                    fields=["name", "species", "total_seeds"])
```

**Get batches in section with stage filter:**
```python
batches = client.get("Batch",
                    filters=[
                        ["section", "=", "B"],
                        ["stage", "=", "germination"]
                    ],
                    fields=["name", "species"])
```

**Get recent events:**
```python
events = client.get("Nursery Event",
                   filters=[["event_date", ">", "2024-01-01"]],
                   fields=["batch", "event_type", "event_date"])
```

### Stats Query Examples

**Calculate germination rate:**
```python
germinated, total, rate = calculate_germination_rate(client, "15-01-24-MAGCHA-01")
print(f"Germination rate: {germinated}/{total} ({rate:.1f}%)")
```

**Get latest growth measurement:**
```python
latest = get_latest_growth_measurement(client, "15-01-24-MAGCHA-01")
if latest:
    print(f"Height: {latest['min_height_cm']}-{latest['max_height_cm']} cm")
```

**Get nursery summary:**
```python
summary = get_nursery_summary(client)
print(f"Total batches: {summary['totals']['batches']}")
print(f"By stage: {summary['by_stage']}")
print(f"By species: {summary['by_species']}")
```

---

## Workflow Integration

### Typical Workflow Sequence

1. **Collection** → Create Collection document
2. **Sowing** → Create Batch, link to Collections via Batch Allocation
3. **Germination** → Create Nursery Event (type=germination), update Batch stage
4. **Transplant** → Create Nursery Event (type=transplant), update Batch location/stage
5. **Growth tracking** → Create Nursery Event (type=growth) periodically
6. **Exit** → Create Nursery Event (type=exit), update Batch stage

### Agent Guidelines

**For read operations (queries):**
- No confirmation needed
- Use helper functions directly
- Format results clearly for user

**For Frappe write operations (create/update):**
- Always show what will be created/updated in Frappe
- Ask for explicit confirmation ("Confirm?", "Proceed?")
- Wait for "yes", "ok", "confirm" before executing
- After execution, show success message with record ID

**For helper script creation (internal tooling):**
- Create autonomously in helpers/ when patterns emerge
- No user confirmation needed (they are non-technical)
- Document in TOOLS.md and MEMORY.md
- These are your internal optimizations, not business operations

---

## Batch ID Format & Heuristics

### Standard Batch ID Format
`DD-MM-YY-SSSFAM-INDEX`

**Components:**
- DD-MM-YY: Date sown (04-01-24 = Jan 4, 2024)
- SSS: First 3 letters of Genus
- FAM: First 3 letters of Species
- INDEX: 4-digit padded sequential (0001, 0002, 0003)

**Examples:**
- 04-01-24-CULEXA-0003 = Cullenia exarillata, 3rd batch, Jan 4
- 15-02-24-MAGCHA-0001 = Magnolia champaca, 1st batch, Feb 15
- 22-01-24-TECTEC-0005 = Tectona grandis, 5th batch, Jan 22

### Species Abbreviation Algorithm

**Rule**: First 3 letters of genus + First 3 letters of species (uppercase)

**Algorithm:**
```python
def get_species_abbreviation(scientific_name: str) -> str:
    """
    Generate species abbreviation using 3+3 algorithm.

    Example:
        "Cullenia exarillata" -> "CULEXA"
        "Magnolia champaca" -> "MAGCHA"
    """
    parts = scientific_name.strip().split()
    genus = parts[0][:3].upper()
    species = parts[1][:3].upper()
    return f"{genus}{species}"
```

Do not maintain a hardcoded list - calculate on demand from the full scientific name.

### Handling Typos & Fuzzy Input

Field staff may provide unclear species names (typos, abbreviations, common names):

**Disambiguation Strategy:**
1. Search Frappe with fuzzy matching:
   ```python
   from nursery_helpers import find_species_fuzzy

   # User says "culnia" or "cullena"
   results = find_species_fuzzy(client, "culnia", limit=5)
   ```

2. Show top matches with similarity scores:
   ```python
   for i, sp in enumerate(results, 1):
       print(f"{i}. {sp['accepted_name']} (score: {sp['score']:.0%})")

   # I found multiple species:
   # 1. Cullenia exarillata (score: 85%)
   # 2. Culcasia scandens (score: 62%)
   # 3. Culex pipiens (score: 54%)
   # Which one? (1, 2, 3)
   ```

3. User picks → use full scientific name → generate abbreviation with algorithm:
   ```python
   chosen = results[user_choice - 1]
   abbr = get_species_abbreviation(chosen['accepted_name'])
   ```

Never assume - always disambiguate when input is unclear.

### Batch ID Generation

Use the helper function to generate batch IDs automatically:
```python
from nursery_helpers import generate_batch_id

# Generates: "22-01-24-CULEXA-01"
batch_id = generate_batch_id(client, "Cullenia exarillata", "2024-01-22")

# Auto-increments if multiple batches on same date
# First batch: "22-01-24-CULEXA-01"
# Second batch: "22-01-24-CULEXA-02"
```

The function automatically:
- Formats date as DD-MM-YY
- Generates species abbreviation
- Queries existing batches to find next index
- Returns formatted batch ID

---

## Agent Autonomy

If the current helper modules are missing a specific query type (e.g., "Get all batches older than 30 days"), you are **encouraged** to:

1. Write one-off Python code for immediate need
2. Propose and test in SCRATCHPAD.md
3. Create helper function in `helpers/` if pattern repeats (no confirmation needed)
4. Document in TOOLS.md and note in MEMORY.md

**Example workflow:**
```python
# User asks: "Show me batches older than 30 days"

# Step 1: One-off solution
from datetime import datetime, timedelta
from nursery_helpers import get_client

client = get_client()
cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
old_batches = client.get("Batch",
                        filters=[["date_sown", "<", cutoff]],
                        fields=["name", "species", "date_sown", "stage"])

for batch in old_batches:
    print(f"{batch['name']}: {batch['species']}, {batch['date_sown']}")

# Step 2: If pattern repeats, create helper (autonomously)
# Create: helpers/batch_age_queries.py
```

**Create helper file:**
```python
# helpers/batch_age_queries.py
from datetime import datetime, timedelta
from typing import List, Dict

def get_batches_older_than(client, days: int = 30) -> List[Dict]:
    """Get batches older than N days."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return client.get("Batch",
                     filters=[["date_sown", "<", cutoff]],
                     fields=["name", "species", "date_sown", "stage"])

def get_batches_without_events(client, event_type: str, days: int = 14) -> List[Dict]:
    """Get batches that haven't had specific event type in N days."""
    # Implementation here
    pass
```

**Step 3: Document**
- Update TOOLS.md: "batch_age_queries.py - Query batches by age and event history"
- Update MEMORY.md: "Created batch age helpers - users frequently ask about aging batches"

**Two types of "writes":**
- **Frappe API writes** (create/update nursery data) → Always confirm with user
- **Helper code writes** (your internal Python tools) → Create autonomously, no confirmation

**Innovate in the right direction:**
- Create helper functions for common patterns
- Handle edge cases gracefully
- Never bypass Frappe API mandatory fields
- Always confirm Frappe writes with user
- Helper creation is autonomous (internal tooling)


