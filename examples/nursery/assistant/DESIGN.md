# OpenClaw Nursery Assistant Implementation Plan

## Context

The nursery POC requires a conversational AI assistant that helps field staff manage seed collections, batches, and nursery events through natural language interactions. The assistant will:

- Run in a Docker container alongside the Frappe backend
- Use voice/text input to create and update nursery records via Frappe REST API
- Implement confirmation-before-write pattern for all database operations
- Provide proactive "plan for the day" summaries based on nursery protocols
- Maintain context through SKILL.md, CONVERSATIONS.md, MEMORY.md, and HEARTBEAT.md files

Current state:
- Frappe containers are running (nursery_frappe, nursery_mariadb, nursery_redis)
- Frappe API is functional with API keys available in `examples/nursery/inputs/data/.env`
- Assistant scaffold exists with context files but no openclaw installation yet
- ETL scripts provide working examples of Frappe API integration patterns
- Docker patterns are well-established for adding new services

**Problem**: OpenClaw is not installed or configured. We need a secure, containerized setup that protects API keys while allowing the assistant to interact with Frappe.

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│  Host: examples/nursery/                             │
│                                                       │
│  ┌─────────────────┐  ┌──────────────────┐         │
│  │ frappe/         │  │ assistant/        │         │
│  │ (unchanged)     │  │  - Context files  │         │
│  │                 │  │  - .env (keys)    │         │
│  │                 │  │  - Dockerfile     │         │
│  │                 │  │  - compose.yml    │◄─ NEW  │
│  └─────────────────┘  └────────┬─────────┘         │
└───────────────────────────────┼──────────────────────┘
                                │ Volume mount
                                │ (assistant/ only)
                                ▼
┌──────────────────────────────────────────────────────┐
│  Docker Network: nursery_network (existing)          │
│                                                       │
│  ┌─────────────┐         ┌─────────────┐           │
│  │ nursery_    │         │ nursery_    │           │
│  │ frappe      │◄────────┤ openclaw    │ (NEW)     │
│  │ :8000       │  HTTP   │             │           │
│  └─────────────┘  API    └─────────────┘           │
│                    calls                             │
│                                                       │
│  Frappe: http://frappe:8000/api/resource/{DocType}  │
└──────────────────────────────────────────────────────┘

Key Points:
- frappe/ directory: UNCHANGED (no modifications to working setup)
- assistant/ directory: Contains standalone docker-compose.yml
- openclaw connects to existing nursery_network
- Reaches Frappe via network (no frappe/ volume mount needed)
- Only assistant/ directory is mounted into openclaw container
```

## Critical Files

**To be created:**
- `examples/nursery/assistant/DESIGN.md` - This plan document (for reference)
- `examples/nursery/assistant/.clawdignore` - Security file to hide sensitive data
- `examples/nursery/assistant/Dockerfile` - OpenClaw container definition
- `examples/nursery/assistant/docker-compose.yml` - Standalone container orchestration (does NOT modify frappe/docker/)
- `examples/nursery/assistant/entrypoint.sh` - Container initialization script
- `examples/nursery/assistant/frappe_api.py` - Frappe API wrapper functions

**To be updated:**
- `examples/nursery/assistant/CONTEXT.md` - Add Frappe DocType schemas and API patterns
- `examples/nursery/assistant/SKILL.md` - Expand stage transition rules with API mappings
- `examples/nursery/assistant/CONVERSATIONS.md` - Add more realistic conversation flows
- `examples/nursery/assistant/HEARTBEAT.md` - Add concrete implementation details

**Existing files to reference:**
- `examples/nursery/inputs/data/etl.py` - Frappe API patterns (read-only reference)
- `examples/nursery/inputs/data/.env` - Frappe API credentials
- `examples/nursery/frappe/docker/docker-compose.yml` - Base docker setup
- `examples/nursery/frappe/docker/entrypoint.sh` - Container init pattern

## Implementation Stages

### Stage 1: Setup & Security (Getting OpenClaw Running)

**Objective**: Install OpenClaw in a Docker container with proper security isolation.

#### 1.1 Create Security Configuration

**File**: `examples/nursery/assistant/.clawdignore`
```
# API keys and secrets
.env
*.key
*.secret
config.json
openclaw.json

# System directories
~/.ssh
~/.aws
~/.config

# Frappe credentials
../inputs/data/.env

# Git history
.git/
```

#### 1.2 Create Dockerfile for OpenClaw

**File**: `examples/nursery/assistant/Dockerfile`
```dockerfile
FROM python:3.11-slim

# Install system dependencies (curl for health checks, git if needed for openclaw)
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install openclaw via pip (auto-installed in container)
# Note: Adjust package name if needed (openclaw, openclaude, etc.)
RUN pip install --no-cache-dir openclaw

# Create working directory
WORKDIR /opt/openclaw

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set environment
ENV OPENCLAW_HOME=/opt/openclaw
ENV ASSISTANT_DIR=/opt/openclaw/assistant

# No docker socket needed - openclaw runs directly in container
# No additional volumes - assistant/ is mounted at runtime

ENTRYPOINT ["/entrypoint.sh"]
CMD ["chat"]
```

**Notes:**
- OpenClaw is auto-installed via `pip install openclaw` (no manual installation needed)
- No docker-in-docker required - runs natively in container
- No docker socket access needed (simplified security)
- Assistant context files are mounted at runtime (not copied in build)

#### 1.3 Create Container Entrypoint

**File**: `examples/nursery/assistant/entrypoint.sh`
```bash
#!/bin/bash
set -e

echo "🌱 Initializing Nursery Assistant..."

# Wait for Frappe to be ready
echo "Waiting for Frappe API..."
until curl -f http://frappe:8000/api/method/ping 2>/dev/null; do
    echo "  Frappe not ready yet, waiting 2 seconds..."
    sleep 2
done
echo "✓ Frappe is ready"

# Load environment variables
if [ -f /opt/openclaw/assistant/.env ]; then
    export $(cat /opt/openclaw/assistant/.env | grep -v '^#' | xargs)
    echo "✓ Environment loaded"
fi

# Initialize openclaw if not already configured
if [ ! -f ~/.openclaw/openclaw.json ]; then
    echo "Configuring openclaw..."

    # Create openclaw config directory
    mkdir -p ~/.openclaw

    # Create openclaw configuration
    cat > ~/.openclaw/openclaw.json <<EOF
{
  "provider": "anthropic",
  "api_key_source": "environment",
  "confirmation_required": {
    "terminal": true,
    "frappe_api": true,
    "file_operations": true
  },
  "docker_sandbox": {
    "enabled": true,
    "mount_path": "/opt/openclaw/assistant",
    "restrict_access": true
  },
  "heartbeat": {
    "enabled": true,
    "interval_minutes": 5,
    "schedule": "*/5 * * * *"
  },
  "context_files": [
    "/opt/openclaw/assistant/CONTEXT.md",
    "/opt/openclaw/assistant/SKILL.md",
    "/opt/openclaw/assistant/CONVERSATIONS.md",
    "/opt/openclaw/assistant/MEMORY.md",
    "/opt/openclaw/assistant/HEARTBEAT.md"
  ],
  "ignore_file": "/opt/openclaw/assistant/.clawdignore"
}
EOF
    echo "✓ OpenClaw configured"
fi

# Set working directory to assistant
cd /opt/openclaw/assistant

# Run openclaw command (default: chat)
echo "🚀 Starting OpenClaw Assistant..."
exec openclaw "$@"
```

#### 1.4 Create Standalone Docker Compose Configuration

**File**: `examples/nursery/assistant/docker-compose.yml` (standalone - does NOT modify frappe setup)
```yaml
version: '3.8'

services:
  openclaw:
    build:
      context: ../../assistant
      dockerfile: Dockerfile
    container_name: nursery_openclaw
    depends_on:
      - frappe
    environment:
      # Service discovery
      FRAPPE_HOST: frappe
      FRAPPE_PORT: "8000"
      FRAPPE_SITE: nursery.localhost

      # Load Frappe API credentials from .env
      FRAPPE_URL: ${FRAPPE_URL:-http://frappe:8000}
      FRAPPE_API_KEY: ${FRAPPE_API_KEY}
      FRAPPE_API_SECRET: ${FRAPPE_API_SECRET}

      # Load Claude API key
      CLAUDE_API_KEY: ${CLAUDE_API_KEY}

    volumes:
      # Mount assistant directory (read-write for logs/state)
      - ../../assistant:/opt/openclaw/assistant

      # Mount .env files as read-only (security)
      - ../../assistant/.env:/opt/openclaw/assistant/.env:ro
      - ../../inputs/data/.env:/opt/openclaw/frappe.env:ro

      # Docker socket for sandboxing (if needed)
      - /var/run/docker.sock:/var/run/docker.sock:ro

    networks:
      - nursery_network

    # Interactive terminal
    stdin_open: true
    tty: true

    # Override for testing
    command: ["chat"]

networks:
  nursery_network:
    external: true
```

#### 1.5 Update Main Docker Compose

**File**: `examples/nursery/frappe/docker/docker-compose.yml`

Add network configuration to existing services:
```yaml
# Add to end of file
networks:
  nursery_network:
    name: nursery_network
    driver: bridge
```

Add `networks: [nursery_network]` to each existing service (frappe, mariadb, redis).

### Stage 2: Frappe Integration Layer

**Objective**: Create reusable API wrapper functions that OpenClaw can use.

#### 2.1 Create Frappe API Wrapper

**File**: `examples/nursery/assistant/frappe_api.py`
```python
"""
Frappe API wrapper for OpenClaw nursery assistant.
Uses patterns from examples/nursery/inputs/data/etl.py
"""
import os
import json
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime


def frappe_url(path: str) -> str:
    """Construct full Frappe API URL."""
    base = os.getenv("FRAPPE_URL", "http://frappe:8000")
    return base.rstrip("/") + "/" + path.lstrip("/")


def frappe_headers() -> Dict[str, str]:
    """Build authenticated headers for Frappe API."""
    api_key = os.getenv("FRAPPE_API_KEY")
    api_secret = os.getenv("FRAPPE_API_SECRET")

    if not api_key or not api_secret:
        raise ValueError("FRAPPE_API_KEY and FRAPPE_API_SECRET must be set")

    return {
        "Authorization": f"token {api_key}:{api_secret}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def frappe_get(doctype: str,
               filters: Optional[List] = None,
               fields: Optional[List[str]] = None) -> List[Dict]:
    """
    Get documents from Frappe.

    Example:
        frappe_get("Species",
                   filters=[["Species", "accepted_name", "=", "Tectona grandis"]],
                   fields=["name", "accepted_name"])
    """
    params = {}
    if filters:
        params["filters"] = json.dumps(filters)
    if fields:
        params["fields"] = json.dumps(fields)

    resp = requests.get(
        frappe_url(f"api/resource/{doctype}"),
        headers=frappe_headers(),
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def frappe_insert(doctype: str, payload: Dict[str, Any]) -> Optional[Dict]:
    """
    Create a new document in Frappe.
    Returns None if document already exists (409 conflict).

    Example:
        frappe_insert("Batch", {
            "species": "Tectona grandis",
            "total_seeds": 100,
            "date_sown": "2024-01-15",
            "section": "A",
            "bed": "A:Bed-1",
        })
    """
    resp = requests.post(
        frappe_url(f"api/resource/{doctype}"),
        headers=frappe_headers(),
        json=payload,
        timeout=30,
    )

    if resp.status_code == 409:
        return None  # Already exists

    resp.raise_for_status()
    return resp.json().get("data")


def frappe_update(doctype: str, name: str, payload: Dict[str, Any]) -> Dict:
    """
    Update an existing document in Frappe.

    Example:
        frappe_update("Batch", "BATCH-001", {"stage": "germination"})
    """
    resp = requests.put(
        frappe_url(f"api/resource/{doctype}/{name}"),
        headers=frappe_headers(),
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("data")


# Convenience functions for common operations

def get_species_by_name(name: str) -> Optional[Dict]:
    """Find species by scientific or local name."""
    results = frappe_get(
        "Species",
        filters=[["Species", "accepted_name", "=", name]],
        fields=["name", "accepted_name", "iucn_status"]
    )
    return results[0] if results else None


def get_batches_by_stage(stage: str) -> List[Dict]:
    """Get all batches in a specific stage."""
    return frappe_get(
        "Batch",
        filters=[["Batch", "stage", "=", stage]],
        fields=["name", "species", "date_sown", "total_seeds", "section", "bed"]
    )


def create_germination_event(batch_name: str, quantity: int,
                             event_date: Optional[str] = None) -> Dict:
    """Create a germination event for a batch."""
    if not event_date:
        event_date = datetime.now().strftime("%Y-%m-%d")

    return frappe_insert("Nursery Event", {
        "batch": batch_name,
        "event_type": "germination",
        "event_date": event_date,
        "quantity": quantity,
    })


def create_batch(species: str, total_seeds: int, section: str, bed: str,
                date_sown: Optional[str] = None, **kwargs) -> Dict:
    """Create a new batch (implies sowing)."""
    if not date_sown:
        date_sown = datetime.now().strftime("%Y-%m-%d")

    payload = {
        "species": species,
        "total_seeds": total_seeds,
        "section": section,
        "bed": bed,
        "date_sown": date_sown,
        "stage": "sowing",
        **kwargs
    }

    return frappe_insert("Batch", payload)
```

#### 2.2 Update CONTEXT.md with DocType Schemas

**File**: `examples/nursery/assistant/CONTEXT.md` (append to existing content)

```markdown
## Frappe DocType Schemas

### Species
Fields:
- `name` (ID, auto): Species document ID
- `accepted_name` (str, required): Scientific name
- `era_species_url` (str): External reference URL
- `iucn_status` (str): Conservation status (LC, EN, CR, etc.)
- `habit` (str): Plant growth form
- `processing` (text): Seed processing instructions
- `germination_time` (int): Expected days to germinate
- `germination_percent` (float): Expected germination rate

### Collection
Fields:
- `name` (ID, auto): Collection document ID
- `date_collected` (date, required): Collection date
- `species` (link, required): Link to Species
- `item_type` (str): seed/cutting/etc
- `condition` (str): fresh/old/etc
- `seed_site` (str): parent_tree/bird_scat/etc
- `gps_latitude` (float, **optional**): EPSG:4326 (can be mocked for testing)
- `gps_longitude` (float, **optional**): EPSG:4326 (can be mocked for testing)
- `locality` (str): Text description of location
- `collected_by` (str): Person name
- `remarks` (text): Notes

**GPS Mocking for Testing:**
- GPS fields are optional (nullable in Frappe)
- For testing without device GPS:
  - Use env vars: `TEST_GPS_LAT=12.9716, TEST_GPS_LON=77.5946` (Bangalore coords)
  - Or use fake locality: "Test location near pond"
  - Assistant should ask: "I don't have GPS coordinates. Use test location (12.97°N, 77.59°E)?"

### Batch
Fields:
- `name` (ID, auto): Batch document ID
- `species` (link, required): Link to Species
- `total_seeds` (int, required): Total seed count
- `date_sown` (date): Sowing date
- `section` (link): Link to Section
- `bed` (link): Link to Bed
- `stage` (str): collection/sowing/germination/growing/exit
- `planted_by` (str): Person name
- `remarks` (text): Notes

### Nursery Event
Fields:
- `name` (ID, auto): Event document ID
- `batch` (link, required): Link to Batch
- `event_type` (str, required): germination/move/transplant/growth/failure/exit
- `event_date` (date, required): When event occurred
- `quantity` (int): Count (for germination/move/transplant/exit)
- `from_section` (link): Origin section (for move/transplant)
- `to_section` (link): Destination section (for move/transplant)
- `from_bed` (link): Origin bed (for move/transplant)
- `to_bed` (link): Destination bed (for move/transplant)
- `min_height_cm` (float): Minimum height (for growth events)
- `max_height_cm` (float): Maximum height (for growth events)
- `notes` (text): Event notes

## API Endpoints

Base URL: `http://frappe:8000` (inside container) or `http://nursery.localhost:8000` (from host)

### Authentication
```
Authorization: token {FRAPPE_API_KEY}:{FRAPPE_API_SECRET}
```

### Common Operations

**List documents with filters:**
```
GET /api/resource/{DocType}?filters=[...]&fields=[...]
```

**Get single document:**
```
GET /api/resource/{DocType}/{name}
```

**Create document:**
```
POST /api/resource/{DocType}
Body: {"field1": "value1", ...}
```

**Update document:**
```
PUT /api/resource/{DocType}/{name}
Body: {"field1": "new_value", ...}
```

## Filter Syntax Examples

Simple equality:
```python
filters=[["Species", "accepted_name", "=", "Tectona grandis"]]
```

Multiple conditions (AND):
```python
filters=[
    ["Batch", "section", "=", "A"],
    ["Batch", "stage", "=", "germination"]
]
```

See `frappe_api.py` for helper functions.
```

### Stage 3: Enhance Assistant Context Files

**Objective**: Expand the context files with concrete examples and API mappings.

#### 3.1 Expand SKILL.md

**File**: `examples/nursery/assistant/SKILL.md` (replace existing content)

```markdown
# Assistant Rulebook (Stages + Rules + API Mappings)

Purpose: Define nursery stages, transition rules, and Frappe API operations.

## Stages

1. **Collection** - Seeds/cuttings collected from field
2. **Sowing** - Seeds planted in nursery beds
3. **Germination** - Seedlings emerge
4. **Growing** - Seedlings develop height
5. **Exit** - Seedlings leave nursery (sale/planting)

## Stage Transition Rules

### Rule 1: Collection → Sowing (Create Batch)
**Trigger**: User wants to sow collected seeds

**User Intent Examples:**
- "Sow the magnolia seeds in bed B1"
- "Create a batch from yesterday's collections"
- "Plant the seeds from collection C-12"

**Required Information:**
- Species (resolved from collection or user input)
- Section and Bed (where sowing will happen)
- Total seeds count
- Which collection(s) to allocate from

**API Operations:**
1. `GET /api/resource/Collection` - Find unbatched collections
2. `POST /api/resource/Batch` - Create batch (stage=sowing)
3. `POST /api/resource/Batch Allocation` - Link collections to batch

**Confirmation Template:**
"I will create a batch for {species}, {total_seeds} seeds, in bed {bed_name}, section {section_name}, using collections {collection_ids}. Confirm?"

---

### Rule 2: Sowing → Germination (Log Germination Event)
**Trigger**: User reports germinated seedlings

**User Intent Examples:**
- "12 magnolia seeds germinated in B1"
- "Batch B-001 has 50 germinated"
- "Germination observation: 85 seedlings"

**Required Information:**
- Batch ID (or inferred from species + bed)
- Absolute germinated count
- Observation date (defaults to today)

**API Operations:**
1. `GET /api/resource/Batch` - Find matching batch
2. `POST /api/resource/Nursery Event` - Create germination event
3. `PUT /api/resource/Batch/{name}` - Update stage to "germination"

**Confirmation Template:**
"I will record a germination event for batch {batch_id} ({species}), quantity {count}, date {date}. This will update the stage to Germination. Confirm?"

---

### Rule 3: Germination → Growing (Transplant Event)
**Trigger**: User moves seedlings to growing area

**User Intent Examples:**
- "Move 40 magnolia seedlings from B1 to D3"
- "Transplant batch B-001 to growing section"
- "Shift seedlings to bed D4"

**Required Information:**
- Batch ID
- From section/bed
- To section/bed
- Quantity moving

**API Operations:**
1. `GET /api/resource/Batch` - Verify batch exists
2. `POST /api/resource/Nursery Event` - Create transplant event
3. `PUT /api/resource/Batch/{name}` - Update stage to "growing", update bed

**Confirmation Template:**
"I will record a transplant event for batch {batch_id}, moving {count} seedlings from {from_bed} to {to_bed}. This will update the stage to Growing. Confirm?"

---

### Rule 4: Growing → Growing (Growth Observation)
**Trigger**: User records height measurements

**User Intent Examples:**
- "Magnolia in D3: min 12cm, max 18cm"
- "Height check: batch B-001, 10-15cm range"

**Required Information:**
- Batch ID (or inferred from species + bed)
- Min height (cm)
- Max height (cm)
- Observation date

**API Operations:**
1. `GET /api/resource/Batch` - Find matching batch
2. `POST /api/resource/Nursery Event` - Create growth event (stage unchanged)

**Confirmation Template:**
"I will record a growth observation for batch {batch_id}: min {min_height}cm, max {max_height}cm, date {date}. Confirm?"

---

### Rule 5: Growing → Exit (Sale/Planting Event)
**Trigger**: Seedlings leave the nursery

**User Intent Examples:**
- "Sell 30 magnolia from batch B-001"
- "Exit 50 seedlings from D3"
- "Transfer 20 to plantation"

**Required Information:**
- Batch ID
- Quantity exiting
- Exit date

**API Operations:**
1. `GET /api/resource/Batch` - Verify batch exists
2. `POST /api/resource/Nursery Event` - Create exit event
3. `PUT /api/resource/Batch/{name}` - Update stage to "exit"

**Confirmation Template:**
"I will record an exit event for batch {batch_id}, quantity {count}, date {date}. This will update the stage to Exit. Confirm?"

---

## Operational Events (No Stage Change)

### Move Event
**Trigger**: Operational relocation within same stage

**User Intent**: "Move 20 seedlings from D3 to D4"

**API Operation**: `POST /api/resource/Nursery Event` (event_type=move)

---

### Failure Event
**Trigger**: Deaths observed

**User Intent**: "10 seedlings died in B1"

**API Operation**: `POST /api/resource/Nursery Event` (event_type=failure)

---

## Stats and Reports (Read-Only Queries)

The assistant can answer questions about nursery stock, stages, and metrics without confirmation (read-only operations).

### Query Pattern 1: Stock by Species
**User Intent Examples:**
- "How many magnolia seeds do we have?"
- "Show me stock for teak"
- "What's the count for species X?"

**Clarification Flow:**
- Bot asks: "Which stage? (all/sowing/germination/growing)"
- User: "germination"
- Bot queries and responds: "Magnolia in germination stage: 3 batches, 250 seeds total, in beds B1, B2, B3"

**API Operations:**
```python
batches = frappe_get("Batch",
                     filters=[
                         ["Batch", "species", "=", "Magnolia champaca"],
                         ["Batch", "stage", "=", "germination"]
                     ],
                     fields=["name", "total_seeds", "bed", "section"])
```

---

### Query Pattern 2: Stock by Stage
**User Intent Examples:**
- "Show me all germinating batches"
- "What's in the growing section?"
- "List everything in stage X"

**Clarification Flow:**
- Bot may ask: "Which section? (all/A/B/C/D/E)"
- User: "Section B"
- Bot responds: "Section B (germination area): 5 batches, 4 species, 450 total seeds"

**API Operations:**
```python
batches = frappe_get("Batch",
                     filters=[
                         ["Batch", "stage", "=", "germination"],
                         ["Batch", "section", "=", "B"]
                     ],
                     fields=["name", "species", "total_seeds", "bed"])

# Aggregate and format
```

---

### Query Pattern 3: Stock by Section/Bed
**User Intent Examples:**
- "Show me stock"
- "What's in bed B1?"
- "Tell me about section D"

**Clarification Flow:**
- Bot asks: "Which section or bed? (e.g., Section A, Bed B1, or 'all')"
- User: "Section D"
- Bot responds:
  ```
  Section D (growing area):
  - Magnolia: 40 seedlings (D3), 25 seedlings (D4)
  - Teak: 30 seedlings (D5)
  - Neem: 50 seedlings (D6)
  Total: 145 seedlings across 4 beds
  ```

**API Operations:**
```python
batches = frappe_get("Batch",
                     filters=[["Batch", "section", "=", "D"]],
                     fields=["name", "species", "total_seeds", "bed", "stage"])

# Group by species and bed
```

---

### Query Pattern 4: Germination Rates
**User Intent Examples:**
- "What's the germination rate for magnolia?"
- "Show germination stats for batch B-001"
- "How well is species X germinating?"

**API Operations:**
```python
# Get batch
batch = frappe_get("Batch", filters=[...], fields=["name", "total_seeds"])

# Get germination events
events = frappe_get("Nursery Event",
                    filters=[
                        ["Nursery Event", "batch", "=", batch_name],
                        ["Nursery Event", "event_type", "=", "germination"]
                    ],
                    fields=["quantity"])

# Calculate rate
germinated = sum(e["quantity"] for e in events)
rate = (germinated / batch["total_seeds"]) * 100
```

**Response Format:**
"Magnolia batch B-001: 50/70 seeds germinated (71%)"

---

### Query Pattern 5: Height Distribution
**User Intent Examples:**
- "Show me height stats for teak"
- "What's the height range in section D?"
- "How tall are the seedlings?"

**API Operations:**
```python
# Get growth events
events = frappe_get("Nursery Event",
                    filters=[
                        ["Nursery Event", "event_type", "=", "growth"],
                        ["Nursery Event", "batch", "in", batch_names]
                    ],
                    fields=["min_height_cm", "max_height_cm", "event_date"])

# Find latest measurements
```

**Response Format:**
"Teak seedlings in Section D: 10-18 cm range (measured 2024-01-20)"

---

### Query Pattern 6: Summary Stats
**User Intent**: "Give me a summary" or "What's the status?"

**Response Format:**
```
Nursery Summary (2024-01-22):

By Stage:
- Sowing: 5 batches, 350 seeds
- Germination: 8 batches, 600 seeds (avg 68% germination)
- Growing: 12 batches, 890 seedlings
- Exit: 3 batches, 150 seedlings (sold/planted)

By Species (top 3):
1. Magnolia: 250 seeds/seedlings across 6 batches
2. Teak: 180 seeds/seedlings across 4 batches
3. Neem: 150 seeds/seedlings across 3 batches

Total: 28 active batches, 1990 seeds/seedlings
```

---

## Confirmation Requirement

⚠️ **CRITICAL RULE**: The assistant MUST propose the change and ask for explicit confirmation before ANY write operation (POST/PUT to Frappe API).

**Format:**
1. Summarize the operation in plain language
2. State what will be created/updated
3. End with "Confirm?" or "Proceed?"
4. Wait for explicit "yes", "ok", "confirm", or similar affirmative response

**Never execute writes without confirmation.**
```

#### 3.2 Expand CONVERSATIONS.md

**File**: `examples/nursery/assistant/CONVERSATIONS.md` (replace existing)

```markdown
# Few-Shot Conversation Examples

Purpose: Teach the assistant the field team's language and expected confirmation flow.

---

## Example 1: Collection Flow

**Worker**: "Collected banyan seeds near the stream this morning. About 50 seeds, fresh condition."

**Bot**: "I'll create a Collection record. Which species? I found:
1. Ficus benghalensis (Banyan)
2. Ficus religiosa (Peepal)

Please choose 1 or 2."

**Worker**: "1"

**Bot**: "Collection details:
- Species: Ficus benghalensis
- Item type: seed
- Condition: fresh
- Quantity: ~50
- Date: today
- Location: near the stream
- GPS: [will use device location]

Create this collection? (yes/no)"

**Worker**: "yes"

**Bot**: "✓ Collection C-045 created. Record ID: C-045"

---

## Example 2: Batch Creation (Sowing)

**Worker**: "Sow yesterday's magnolia seeds in bed B1."

**Bot**: "I found 3 magnolia collections from yesterday:
- C-042: 30 seeds, fresh
- C-043: 25 seeds, fresh
- C-044: 15 seeds, slightly old

Total: 70 seeds. Use all three? (yes/no/specify)"

**Worker**: "yes, all"

**Bot**: "Batch details:
- Species: Magnolia champaca
- Total seeds: 70
- Collections: C-042 (30), C-043 (25), C-044 (15)
- Section: B (germination area)
- Bed: B1
- Date sown: today
- Stage: Sowing

Create this batch? (yes/no)"

**Worker**: "yes"

**Bot**: "✓ Batch BATCH-2024-01-15-MAG created.
✓ Allocations linked.
Next: watch for germination in ~7-14 days (per protocol)."

---

## Example 3: Germination Event

**Worker**: "Magnolia B1, 50 germinated today."

**Bot**: "I found batch BATCH-2024-01-15-MAG in bed B1 (70 seeds sown on Jan 15).

Germination event:
- Batch: BATCH-2024-01-15-MAG
- Quantity: 50 germinated
- Date: today (Jan 22)
- Stage change: Sowing → Germination

Record this? (yes/no)"

**Worker**: "yes"

**Bot**: "✓ Germination event recorded.
✓ Batch stage updated to Germination.

Germination rate: 71% (50/70)
Time to germination: 7 days (within expected range)"

---

## Example 4: Disambiguation

**Worker**: "Check batch 12 germination."

**Bot**: "I found multiple batches:
1. BATCH-2024-01-12-MAG (Magnolia, bed B1, 70 seeds)
2. BATCH-2024-01-12-NEE (Neem, bed B2, 100 seeds)

Which one? (1 or 2)"

**Worker**: "1"

**Bot**: "Batch BATCH-2024-01-12-MAG:
- Species: Magnolia champaca
- Total seeds: 70
- Germinated: 50 (71%)
- Date sown: Jan 12
- Current stage: Germination
- Location: Section B, Bed B1"

---

## Example 5: Transplant Flow

**Worker**: "Move 40 magnolia seedlings from B1 to D3."

**Bot**: "Transplant operation:
- Batch: BATCH-2024-01-12-MAG
- From: Section B, Bed B1 (germination area)
- To: Section D, Bed D3 (growing area)
- Quantity: 40 seedlings
- Stage change: Germination → Growing

Proceed? (yes/no)"

**Worker**: "yes"

**Bot**: "✓ Transplant event recorded.
✓ Batch location updated to D3.
✓ Stage updated to Growing.

Remaining in B1: 10 seedlings (will need separate transplant later)"

---

## Example 6: Growth Observation

**Worker**: "Height check D3: min 10cm, max 15cm."

**Bot**: "I found 2 batches in D3:
1. BATCH-2024-01-12-MAG (Magnolia, 40 seedlings)
2. BATCH-2024-01-10-TEA (Teak, 25 seedlings)

Which batch? (1, 2, or both)"

**Worker**: "1"

**Bot**: "Growth observation:
- Batch: BATCH-2024-01-12-MAG (Magnolia)
- Min height: 10 cm
- Max height: 15 cm
- Date: today

Record this? (yes/no)"

**Worker**: "yes"

**Bot**: "✓ Growth observation recorded.

Growth status: Healthy range for 15 days post-germination."

---

## Example 7: Exit Event

**Worker**: "Sell 30 magnolia from D3."

**Bot**: "Exit event:
- Batch: BATCH-2024-01-12-MAG
- Quantity: 30 seedlings
- From: Section D, Bed D3
- Date: today
- Stage change: Growing → Exit

Proceed? (yes/no)"

**Worker**: "yes"

**Bot**: "✓ Exit event recorded.
✓ Batch stage updated to Exit.

Remaining stock: 10 seedlings still in Growing stage."

---

## Example 8: Stats Query (Stock by Species)

**Worker**: "How many magnolia do we have?"

**Bot**: "Magnolia stock:
- Sowing: 2 batches, 140 seeds (beds B1, B2)
- Germination: 3 batches, 210 seeds (beds B3, B4, B5)
- Growing: 2 batches, 75 seedlings (beds D3, D4)
- Total: 7 batches, 425 seeds/seedlings

Want details on a specific stage?"

**Worker**: "germination"

**Bot**: "Magnolia in Germination:
1. Batch BATCH-2024-01-12-MAG (Bed B3): 70 seeds, 50 germinated (71%), 7 days old
2. Batch BATCH-2024-01-15-MAG (Bed B4): 80 seeds, 62 germinated (78%), 4 days old
3. Batch BATCH-2024-01-18-MAG (Bed B5): 60 seeds, 45 germinated (75%), 1 day old

Total: 210 seeds, 157 germinated (75% avg)"

---

## Example 9: Stats Query (Stock by Section)

**Worker**: "Show me stock"

**Bot**: "Which section or bed? (e.g., 'Section B', 'Bed D3', or 'all')"

**Worker**: "Section D"

**Bot**: "Section D (growing area):

By species:
- Magnolia: 65 seedlings across 2 beds (D3: 40, D4: 25)
- Teak: 55 seedlings across 2 beds (D5: 30, D6: 25)
- Neem: 50 seedlings (D7)

Total: 170 seedlings, 4 species, 5 beds

Latest measurements:
- Magnolia: 10-18 cm (measured Jan 20)
- Teak: 8-15 cm (measured Jan 19)
- Neem: 12-20 cm (measured Jan 21)"

---

## Example 10: Summary Stats

**Worker**: "Give me a summary"

**Bot**: "Nursery Summary (Jan 22, 2024):

📊 By Stage:
- Sowing: 5 batches, 350 seeds
- Germination: 8 batches, 600 seeds (avg 72% germination)
- Growing: 12 batches, 890 seedlings
- Exit: 150 seedlings sold/planted this month

🌱 By Species (top 3):
1. Magnolia: 425 across 7 batches
2. Teak: 280 across 5 batches
3. Neem: 210 across 4 batches

📈 Recent Activity:
- 3 batches ready for transplant (germination → growing)
- 2 germination checks overdue (see daily plan)

Total: 28 active batches, 1840 seeds/seedlings"

---

## Conversation Patterns

### Clarification Questions
- "Which species? I found: ..."
- "Which batch? I found multiple: ..."
- "Use all collections or specify?"
- "What's the bed location?"

### Confirmation Format
- Summarize operation
- List all changes
- End with "(yes/no)" or "Proceed?"

### Success Messages
- Use "✓" for completed actions
- Provide record IDs
- Show relevant metrics
- Suggest next steps

### Error Handling
- "I couldn't find a batch matching that description."
- "That bed doesn't exist in the system. Should I create it?"
- "The API returned an error: [message]. Please check and try again."
```

#### 3.3 Expand HEARTBEAT.md

**File**: `examples/nursery/assistant/HEARTBEAT.md` (replace existing)

```markdown
# Heartbeat (Proactive Scheduler)

Purpose: Background process that surfaces overdue tasks without explicit user requests.

## Configuration

**Schedule**: Every 5 minutes (configurable in `openclaw.json`)
```json
{
  "heartbeat": {
    "enabled": true,
    "interval_minutes": 5,
    "schedule": "*/5 * * * *"
  }
}
```

## Logic Flow

### 1. Fetch Current State
```python
# Get all active batches (not in Exit stage)
batches = frappe_get("Batch",
                     filters=[["Batch", "stage", "!=", "exit"]],
                     fields=["name", "species", "date_sown", "stage", "section", "bed"])

# Get species protocols
species_data = frappe_get("Species",
                         fields=["name", "accepted_name", "germination_time", "germination_percent"])
```

### 2. Compare Against Protocols

For each batch:

**If stage = "sowing":**
- Calculate days since `date_sown`
- Compare to `species.germination_time`
- If overdue (e.g., > germination_time + 3 days): flag for check

**If stage = "germination":**
- Check for recent germination events
- If no events in last 7 days: flag for observation

**If stage = "growing":**
- Check for recent growth events
- If no height recorded in last 14 days: flag for measurement

### 3. Generate Proactive Message

**Format**: Concrete, actionable requests

**Example Messages:**

**Germination Check:**
```
🌱 Daily Plan (Jan 22, 07:00)

URGENT - Germination Checks:
- Bed B1 (Magnolia, batch BATCH-2024-01-12-MAG): 10 days since sowing
  Expected germination: 7-14 days
  → Tell me: how many seeds have germinated?

- Bed B3 (Neem, batch BATCH-2024-01-10-NEE): 12 days since sowing
  Expected germination: 10-20 days
  → Tell me: any germination yet?
```

**Growth Observation:**
```
📏 Measurement Reminder:

- Bed D3 (Magnolia, 40 seedlings): no height recorded in 15 days
  → Measure: tell me min and max height in cm

- Bed D4 (Teak, 25 seedlings): last measurement Jan 5
  → Update: current height range?
```

**Transplant Reminder:**
```
🌿 Transplant Due:

- Batch BATCH-2024-01-05-MAG: germinated 30 days ago, still in germination area
  → Should we move to growing section?
```

### 4. Output Channels

**Terminal mode**: Print to console when user starts `openclaw chat`

**WhatsApp mode**: Send as proactive message to configured number

**Silent mode**: Store in `MEMORY.md` for next user interaction

## Implementation

**Heartbeat Script** (pseudo-code):
```python
def heartbeat_check():
    """Run proactive checks and generate daily plan."""

    # 1. Get overdue germination checks
    overdue_germination = []
    batches_sowing = frappe_get("Batch", filters=[["stage", "=", "sowing"]])

    for batch in batches_sowing:
        species = get_species_by_name(batch["species"])
        days_since_sowing = (today - batch["date_sown"]).days
        expected_time = species.get("germination_time", 14)

        if days_since_sowing >= expected_time:
            overdue_germination.append({
                "batch": batch["name"],
                "species": batch["species"],
                "bed": batch["bed"],
                "days": days_since_sowing,
                "expected": expected_time
            })

    # 2. Get growth measurement reminders
    overdue_growth = []
    batches_growing = frappe_get("Batch", filters=[["stage", "=", "growing"]])

    for batch in batches_growing:
        last_event = get_last_growth_event(batch["name"])
        if not last_event or days_since(last_event["date"]) > 14:
            overdue_growth.append({
                "batch": batch["name"],
                "species": batch["species"],
                "bed": batch["bed"],
                "last_check": last_event["date"] if last_event else "never"
            })

    # 3. Generate message
    message = build_daily_plan(overdue_germination, overdue_growth)

    # 4. Send/display
    return message


def build_daily_plan(germination_checks, growth_checks):
    """Format proactive message."""
    lines = ["🌱 Daily Plan\n"]

    if germination_checks:
        lines.append("GERMINATION CHECKS:")
        for item in germination_checks:
            lines.append(f"- Bed {item['bed']} ({item['species']}): "
                        f"{item['days']} days since sowing")
            lines.append(f"  → Tell me: how many germinated?")
        lines.append("")

    if growth_checks:
        lines.append("GROWTH MEASUREMENTS:")
        for item in growth_checks:
            lines.append(f"- Bed {item['bed']} ({item['species']}): "
                        f"last check {item['last_check']}")
            lines.append(f"  → Measure: min and max height?")
        lines.append("")

    if not germination_checks and not growth_checks:
        lines.append("✓ All batches are up to date. No urgent tasks.")

    return "\n".join(lines)
```

## Testing

**Manual trigger**:
```bash
# Inside container
openclaw heartbeat --run-once
```

**Test scenario**:
1. Create a batch with `date_sown` 15 days ago
2. Don't add any germination events
3. Run heartbeat
4. Expect: message flagging this batch for check

**Automated test**:
```bash
# Set interval to 1 minute for testing
# Update openclaw.json: "interval_minutes": 1
# Restart container
docker restart nursery_openclaw
```
```

### Stage 4: Testing & Validation

**Objective**: Verify each component works incrementally.

#### 4.1 Test Plan

**Test 1: Container Startup**
```bash
cd examples/nursery/assistant
docker compose build
docker compose up
```
Expected: Container starts, waits for Frappe, loads config, starts openclaw chat

**Test 2: API Connectivity**
```bash
# Inside openclaw container
docker exec -it nursery_openclaw python3
>>> from assistant.frappe_api import *
>>> species = frappe_get("Species", fields=["name", "accepted_name"])
>>> print(species)
```
Expected: Returns list of species from Frappe

**Test 3: Security - Verify .clawdignore Works**
```bash
# Try to make openclaw read .env file
docker exec -it nursery_openclaw openclaw chat
> "Read the .env file and tell me what's in it"
```
Expected: Bot refuses or says file is not accessible

**Test 4: Confirmation Requirement**
```bash
docker exec -it nursery_openclaw openclaw chat
> "Create a new species called Test Species"
```
Expected: Bot asks for confirmation before making POST request

**Test 5: Collection → Batch Flow**
```bash
docker exec -it nursery_openclaw openclaw chat
> "I collected 50 banyan seeds today near the pond"
# Bot should create Collection (after confirmation)
> "Sow those seeds in bed B1"
# Bot should create Batch + Allocation (after confirmation)
```

**Test 6: Germination Event**
```bash
> "30 banyan seeds germinated in B1"
# Bot should create Nursery Event and update Batch stage
```

**Test 7: Heartbeat Proactive Message**
```bash
# Wait 5 minutes or trigger manually
docker exec -it nursery_openclaw openclaw heartbeat --run-once
```
Expected: Prints daily plan with overdue checks

**Test 8: Stats Queries (Read-Only)**
```bash
docker exec -it nursery_openclaw openclaw chat
> "How many magnolia do we have?"
> "Show me stock in Section B"
> "What's the germination rate for batch B-001?"
> "Give me a summary"
```
Expected: Bot responds with stats without requiring confirmation (read-only)

**Test 9: GPS Mocking**
```bash
# Set test mode
export TEST_MODE=true
docker exec -it nursery_openclaw openclaw chat
> "I collected 50 banyan seeds near the pond"
# Bot should use TEST_GPS_LAT/LON or ask to confirm test location
```
Expected: Collection created with mock GPS coordinates

#### 4.2 Verification Checklist

- [ ] Container builds successfully
- [ ] Frappe API connectivity works (can read Species)
- [ ] .clawdignore prevents reading sensitive files
- [ ] Confirmation prompt appears before writes
- [ ] Can create Collection records
- [ ] GPS coordinates are optional (can use test mode)
- [ ] Can create Batch records with allocations
- [ ] Can create Nursery Event records
- [ ] Stage transitions update correctly
- [ ] Can query stock by species/section/bed (no confirmation needed)
- [ ] Can get germination rates and height stats
- [ ] Can get summary stats
- [ ] Heartbeat generates proactive messages
- [ ] Context files are loaded (SKILL.md, CONVERSATIONS.md, etc.)
- [ ] Frappe setup remains unchanged (no modifications to frappe/docker/)

### Stage 5: Documentation & Handoff

**Objective**: Document what was built and how to use it.

#### 5.1 Create DESIGN.md

**File**: `examples/nursery/assistant/DESIGN.md`

This file should contain:
1. Architecture overview
2. Component descriptions (Dockerfile, docker-compose, API wrapper)
3. Security model (.clawdignore, confirmation requirements)
4. API integration patterns
5. Conversation flows
6. Testing instructions
7. Troubleshooting guide

(Content: summarize this plan document in a reference format)

#### 5.2 Update README.md

**File**: `examples/nursery/assistant/README.md` (keep existing, add sections)

Add sections:
- "Getting Started" with docker commands
- "Testing the Assistant" with example conversations
- "Architecture" diagram
- "Troubleshooting" common issues

## Key Design Decisions

### 1. Standalone Docker Setup (No Frappe Modifications)
**Decision**: Create `assistant/docker-compose.yml` instead of modifying `frappe/docker/`
**Rationale**:
- Keeps working Frappe setup stable
- OpenClaw can be added/removed without touching Frappe
- Both setups work independently
- Uses external network to connect to existing Frappe containers

### 2. OpenClaw Auto-Installation
**Decision**: Install openclaw via `pip install openclaw` in Dockerfile
**Rationale**:
- Automatic installation in container build process
- No manual installation steps
- No docker-in-docker complexity needed
- Simplified security model (no docker socket access required)

### 3. Volume Mount Strategy
**Decision**: Mount only `assistant/` directory (read-write)
**Rationale**:
- No need to mount frappe/ (OpenClaw reaches Frappe via network API)
- Assistant can write logs/memory but is isolated from frappe code
- Simpler container configuration

### 4. API Wrapper Layer
**Decision**: Create `frappe_api.py` with reusable functions
**Rationale**:
- Provides abstraction over Frappe REST API
- Reusable functions align with ETL patterns
- Better error handling and type safety
- Easier testing and maintenance

### 5. Confirmation-Before-Write vs Read-Only
**Decision**:
- Write operations (POST/PUT) require confirmation
- Read operations (GET) do NOT require confirmation
**Rationale**:
- Safety for database changes
- Fluid conversation for stats queries
- Field staff can explore data freely

### 6. GPS Mocking for Testing
**Decision**: Make GPS coordinates optional with test mode support
**Rationale**:
- Enables testing without physical GPS device
- Environment variables provide default test coordinates
- Production can use real GPS from mobile devices
- Doesn't break development workflow

### 7. Stats and Reports Integration
**Decision**: Add read-only query patterns for stock, rates, and summaries
**Rationale**:
- Aligned with Frappe's reporting capabilities
- Field staff need quick insights without confirmation overhead
- Supports interactive clarification ("which section?")
- Enables data-driven decision making

### 8. Heartbeat Configuration
**Decision**: Make interval configurable (default 5 minutes for testing)
**Rationale**:
- Allows rapid iteration during development
- Can be adjusted for production (e.g., once daily)
- Testable without waiting long periods

### 9. Context File Strategy
**Decision**: Keep SKILL.md, CONVERSATIONS.md, CONTEXT.md separate
**Rationale**:
- Easier to maintain and update
- OpenClaw can load selectively based on context
- Clear separation of concerns (rules vs examples vs schemas)

## Open Questions (To Clarify During Implementation)

1. **OpenClaw Package Name**: Confirm exact pip package name (openclaw, openclaude, etc.)
   - Action: Check during Stage 1 - adjust Dockerfile if needed
   - Fallback: If not pip-installable, clone from GitHub

2. **Frappe Network Name**: Verify exact network name used by frappe containers
   - Action: Run `docker network ls` to find network
   - Common names: `nursery_default`, `frappe_default`, or custom `nursery_network`
   - Update docker-compose.yml accordingly

3. **Voice Input Integration**: Voice capabilities for mobile/WhatsApp
   - Decision: Start with text-only terminal testing
   - Add voice transcription layer later (separate service or openclaw built-in)

4. **WhatsApp Channel**: Channel authentication and message handling
   - Decision: Phase 2 feature after terminal testing is stable
   - Requires openclaw channels setup and WhatsApp Business API

## Next Steps After Plan Approval

1. Create `.clawdignore` file
2. Create Dockerfile for openclaw
3. Create entrypoint.sh script
4. Create docker-compose-openclaw.yml
5. Create frappe_api.py wrapper
6. Update CONTEXT.md with schemas
7. Update SKILL.md with API mappings
8. Update CONVERSATIONS.md with examples
9. Update HEARTBEAT.md with implementation
10. Build and test container
11. Run through test plan
12. Create DESIGN.md documentation
13. Update README.md

## Success Metrics

**Core Functionality:**
- [ ] Can start openclaw container successfully
- [ ] Can authenticate with Frappe API
- [ ] Can read DocTypes (GET requests work)
- [ ] Can execute a full Collection → Batch → Germination flow
- [ ] Stage transitions work correctly

**Security:**
- [ ] API keys remain secure (not readable by bot via .clawdignore)
- [ ] Confirmation prompts appear before ALL write operations
- [ ] Read-only queries work without confirmation

**Features:**
- [ ] Stats queries work (stock by species/section/bed)
- [ ] Germination rates and height stats accessible
- [ ] Summary stats display correctly
- [ ] GPS mocking works for testing
- [ ] Heartbeat generates proactive messages
- [ ] Context files are loaded and influence bot behavior

**Stability:**
- [ ] Frappe setup remains unchanged (no modifications to frappe/docker/)
- [ ] Both systems work independently
- [ ] Can tear down openclaw without affecting Frappe

## Estimated Timeline

- Stage 1 (Setup & Security): 1 hour
- Stage 2 (Frappe Integration): 1 hour
- Stage 3 (Context Enhancement): 1 hour
- Stage 4 (Testing): 2 hours
- Stage 5 (Documentation): 30 mins

Total: ~5.5 hours for complete implementation
