# Available Tools

Quick reference for tools available in the nursery assistant environment.

---

## Python Modules for Frappe Integration

### frappe_client.py
Low-level Frappe API wrapper with automatic authentication and header management.

**Usage:**
```python
from frappe_client import FrappeClient

# Create authenticated client from environment
client = FrappeClient.from_env()

# Basic CRUD operations
species = client.get("Species", fields=["name", "accepted_name"])
batch = client.create("Batch", {"species": "...", "total_seeds": 100})
client.update("Batch", "BATCH-001", {"stage": "germination"})

# Test connectivity
if client.ping():
    print("✓ Connected to Frappe")
```

**Key Methods:**
- `get(doctype, name=None, filters=None, fields=None, limit=None)` - Query documents
- `create(doctype, data)` - Create new document
- `update(doctype, name, data)` - Update existing document
- `ping()` - Test API connectivity

---

### nursery_helpers.py
High-level domain-specific helpers that match SKILL.md workflows.

**Usage:**
```python
from nursery_helpers import *

client = get_client()

# Species helpers
find_species_fuzzy(client, "magnolia")
find_species_exact(client, "Magnolia champaca")
get_species_abbreviation("Magnolia champaca")  # Returns: "MAGCHA"

# Batch creation
batch_id = generate_batch_id(client, "Magnolia champaca", "2024-01-22")
batch = create_batch_from_collections(client, "Magnolia champaca", ["C-001"], "B", "B1")

# Stage transitions
log_germination(client, batch_id, quantity=50)
log_transplant(client, batch_id, "B", "B1", "D", "D3", quantity=40)
log_growth_observation(client, batch_id, min_height_cm=10.0, max_height_cm=15.0)
log_exit_event(client, batch_id, quantity=30)

# Operational events
log_move_event(client, batch_id, from_bed="D3", to_bed="D4", quantity=20)
log_failure_event(client, batch_id, quantity=10, notes="Fungal infection")

# Queries
get_batches_by_species(client, "Magnolia champaca")
get_batches_by_stage(client, "germination")
get_batches_by_section(client, "D", bed="D3")

# Stats
germinated, total, rate = calculate_germination_rate(client, batch_id)
latest = get_latest_growth_measurement(client, batch_id)
summary = get_nursery_summary(client)
```

**All Helper Functions:**

**Schema Discovery:**
- `get_doctype_fields(client, doctype)` - Discover all fields for a DocType dynamically
- `get_child_table_data(client, doctype, name, child_field)` - Get child table data from a document

**Client & Species:**
- `get_client()` - Get authenticated Frappe client
- `get_species_abbreviation(name)` - Generate 3+3 species code
- `find_species_fuzzy(client, query)` - Fuzzy search species
- `find_species_exact(client, name)` - Exact species lookup

**Batch Management:**
- `generate_batch_id(client, species, date)` - Generate batch ID
- `find_unbatched_collections(client, species, date)` - Find collections to batch
- `create_batch_from_collections(...)` - Collection → Sowing transition

**Stage Transitions:**
- `log_germination(...)` - Sowing → Germination transition
- `log_transplant(...)` - Germination → Growing transition
- `log_growth_observation(...)` - Growth measurement (no stage change)
- `log_exit_event(...)` - Growing → Exit transition

**Operational Events:**
- `log_move_event(...)` - Operational move (no stage change)
- `log_failure_event(...)` - Record seedling deaths

**Queries & Stats:**
- `get_batches_by_species(...)` - Query batches for species
- `get_batches_by_stage(...)` - Query batches by stage
- `get_batches_by_section(...)` - Query batches by section/bed
- `calculate_germination_rate(...)` - Get germination stats
- `get_latest_growth_measurement(...)` - Get most recent height
- `get_nursery_summary(...)` - Comprehensive stats

---

## Custom Helper Scripts (helpers/)

Directory for agent-created helper modules.

**Current status:** Empty - create as needed

**When to create a helper:**
- When a query pattern repeats frequently
- When you need specialized domain logic
- When the operation combines multiple API calls

**Example:** Create helper for batch age queries:
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
```

**Usage:**
```python
import sys
sys.path.append('/home/node/.openclaw/workspace/helpers')

from batch_age_queries import get_batches_older_than

client = get_client()
old_batches = get_batches_older_than(client, days=30)
```

**Development process:**
1. Draft in SCRATCHPAD.md
2. Test with real data
3. Save to helpers/
4. Document here
5. Update MEMORY.md

**See AGENTS.md** for autonomy guidelines and guardrails.

---

## Quick Reference

**Test connectivity:**
```python
from frappe_client import FrappeClient
client = FrappeClient.from_env()
print(client.ping())  # True if connected
```

**Common operations:**
```python
from nursery_helpers import *

client = get_client()

# Discover DocType fields dynamically
fields = get_doctype_fields(client, "Species")
for field in fields:
    req = "Required" if field.get('reqd') else "Optional"
    print(f"{field['label']}: {field['fieldtype']} ({req})")

# Find species
results = find_species_fuzzy(client, "magnol")

# Create batch
batch = create_batch_from_collections(client, "Magnolia champaca", ["C-001"], "B", "B1")

# Log events
log_germination(client, "15-01-24-MAGCHA-01", 50)
log_transplant(client, "15-01-24-MAGCHA-01", "B", "B1", "D", "D3", 40)

# Get stats
summary = get_nursery_summary(client)
print(f"Total batches: {summary['totals']['batches']}")
```

**For detailed documentation:**
- **CONTEXT.md** - Technical reference and Python examples
- **SKILL.md** - Workflow rules and stage transitions
- **CONVERSATIONS.md** - Language patterns and dialogue examples
- **AGENTS.md** - Autonomy guidelines and guardrails
