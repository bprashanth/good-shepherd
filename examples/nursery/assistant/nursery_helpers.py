"""
Nursery Domain Helpers for OpenClaw Assistant

High-level helper functions that match the user journeys and stage transitions
defined in SKILL.md. These functions encapsulate common nursery operations.

Usage:
    from nursery_helpers import *

    client = get_client()
    find_species_fuzzy(client, "magnolia")
    create_batch_from_collections(client, "Magnolia champaca", ["C-001", "C-002"], "B", "B1")
"""
import os
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from difflib import SequenceMatcher
from frappe_client import FrappeClient


def get_client() -> FrappeClient:
    """
    Get authenticated Frappe client from environment variables.

    Returns:
        FrappeClient instance
    """
    return FrappeClient.from_env()


def get_doctype_fields(client: FrappeClient, doctype: str, include_child_tables: bool = True) -> List[Dict[str, Any]]:
    """
    Get all fields for a DocType by querying Frappe metadata API.

    This discovers the schema dynamically, so you don't need to hardcode
    field lists in documentation.

    Args:
        client: Frappe client
        doctype: DocType name (e.g., "Species", "Batch")
        include_child_tables: If True, includes info about child tables

    Returns:
        List of field dictionaries with keys:
        - fieldname: API field name
        - label: Human-readable label
        - fieldtype: Type (Data, Link, Int, Float, Table, etc.)
        - reqd: 1 if required, 0 if optional
        - options: For Link/Select fields, the linked DocType or choices
        - is_child_table: True if this is a child table field
        - child_table_doctype: For child tables, the linked DocType name

    Example:
        fields = get_doctype_fields(client, "Species")
        for field in fields:
            req = "Required" if field.get('reqd') else "Optional"
            print(f"{field['label']}: {field['fieldtype']} ({req})")

            # Check for child tables
            if field.get('is_child_table'):
                print(f"  → Child table: {field['child_table_doctype']}")
                # To query child table data:
                # species = client.get("Species", name="SPE-001")
                # child_data = species.get(field['fieldname'], [])
    """
    meta = client.get_doctype_meta(doctype)

    # Filter out internal/system fields
    fields = []
    child_tables = []

    for field in meta.get('fields', []):
        # Skip internal fields
        if field.get('fieldname', '').startswith('_'):
            continue
        if field.get('fieldtype') in ['Section Break', 'Column Break', 'HTML']:
            continue

        is_child_table = field.get('fieldtype') == 'Table'

        field_info = {
            'fieldname': field.get('fieldname'),
            'label': field.get('label'),
            'fieldtype': field.get('fieldtype'),
            'reqd': field.get('reqd', 0),
            'options': field.get('options'),
            'description': field.get('description', ''),
            'is_child_table': is_child_table
        }

        if is_child_table:
            field_info['child_table_doctype'] = field.get('options')
            child_tables.append(field_info)

        fields.append(field_info)

    # Add summary of child tables at the end if any exist
    if include_child_tables and child_tables:
        print(f"\n⚠️  {doctype} has {len(child_tables)} child table(s):")
        for ct in child_tables:
            print(f"   - {ct['fieldname']} ({ct['label']}) → {ct['child_table_doctype']}")
        print(f"\nTo access child table data:")
        print(f"   doc = client.get('{doctype}', name='DOC-ID')")
        print(f"   child_rows = doc.get('{child_tables[0]['fieldname']}', [])")
        print(f"   for row in child_rows:")
        print(f"       print(row)")

    return fields


def get_child_table_data(client: FrappeClient, doctype: str, name: str, child_field: str) -> List[Dict]:
    """
    Get child table data for a specific document.

    Child tables in Frappe are nested data (like local names, batch allocations, etc.)
    that are stored within a parent document.

    Args:
        client: Frappe client
        doctype: Parent DocType name (e.g., "Species")
        name: Document name/ID
        child_field: Child table field name (e.g., "local_names")

    Returns:
        List of child table rows

    Example:
        # Get local names for a species
        local_names = get_child_table_data(client, "Species", "SPE-001", "local_names")
        for row in local_names:
            print(f"{row.get('local_name')}: {row.get('language')}")

        # Get batch allocations for a batch
        allocations = get_child_table_data(client, "Batch", "15-01-24-MAGCHA-01", "batch_allocations")
    """
    doc = client.get(doctype, name=name)
    return doc.get(child_field, [])


# ============================================================================
# Species Helpers
# ============================================================================

def get_species_abbreviation(scientific_name: str) -> str:
    """
    Generate species abbreviation using 3+3 algorithm.

    Algorithm: First 3 letters of genus + First 3 letters of species (uppercase)

    Args:
        scientific_name: Full scientific name (e.g., "Magnolia champaca")

    Returns:
        Abbreviation (e.g., "MAGCHA")

    Example:
        get_species_abbreviation("Magnolia champaca") -> "MAGCHA"
        get_species_abbreviation("Tectona grandis") -> "TECGRA"
    """
    parts = scientific_name.strip().split()
    if len(parts) < 2:
        # Fallback for malformed names
        return scientific_name[:6].upper()

    genus = parts[0][:3].upper()
    species = parts[1][:3].upper()
    return f"{genus}{species}"


def find_species_fuzzy(client: FrappeClient, query: str, limit: int = 5) -> List[Dict]:
    """
    Search for species with fuzzy matching on accepted_name.

    Handles typos, abbreviations, and partial matches.

    Args:
        client: Frappe client
        query: User's search term (e.g., "magnolia", "cullena", "teak")
        limit: Max results to return

    Returns:
        List of matching species with similarity scores

    Example:
        results = find_species_fuzzy(client, "magnol")
        # Returns: [{"name": "...", "accepted_name": "Magnolia champaca", "score": 0.85}, ...]
    """
    # Get all species
    all_species = client.get("Species", fields=["name", "accepted_name", "iucn_status"])

    # Calculate similarity scores
    query_lower = query.lower()
    scored_species = []

    for sp in all_species:
        name_lower = sp["accepted_name"].lower()

        # Exact substring match gets high score
        if query_lower in name_lower:
            score = 0.9
        else:
            # Use sequence matcher for fuzzy matching
            score = SequenceMatcher(None, query_lower, name_lower).ratio()

        if score > 0.3:  # Threshold for relevance
            scored_species.append({
                **sp,
                "score": score
            })

    # Sort by score descending
    scored_species.sort(key=lambda x: x["score"], reverse=True)

    return scored_species[:limit]


def find_species_exact(client: FrappeClient, scientific_name: str) -> Optional[Dict]:
    """
    Find species by exact scientific name match.

    Args:
        client: Frappe client
        scientific_name: Full scientific name

    Returns:
        Species document or None if not found
    """
    results = client.get("Species",
                        filters=[["accepted_name", "=", scientific_name]],
                        fields=["name", "accepted_name", "iucn_status",
                               "germination_time", "germination_percent"])
    return results[0] if results else None


# ============================================================================
# Batch ID Generation
# ============================================================================

def generate_batch_id(client: FrappeClient,
                      species_name: str,
                      date_sown: Optional[str] = None) -> str:
    """
    Generate batch ID using algorithm: DD-MM-YY-SSSFAM-INDEX

    Format:
        DD-MM-YY: Day, month, year (2 digits each)
        SSSFAM: Species abbreviation (3+3 algorithm)
        INDEX: Sequential number for this species on this date (01, 02, etc.)

    Args:
        client: Frappe client
        species_name: Full scientific name
        date_sown: Sowing date (YYYY-MM-DD), defaults to today

    Returns:
        Batch ID string

    Example:
        generate_batch_id(client, "Magnolia champaca", "2024-01-15")
        -> "15-01-24-MAGCHA-01"
    """
    if not date_sown:
        date_sown = datetime.now().strftime("%Y-%m-%d")

    # Parse date
    dt = datetime.strptime(date_sown, "%Y-%m-%d")
    date_prefix = dt.strftime("%d-%m-%y")

    # Get species abbreviation
    species_abbr = get_species_abbreviation(species_name)

    # Find existing batches with same date and species
    # Pattern: {date_prefix}-{species_abbr}-*
    all_batches = client.get("Batch",
                            filters=[
                                ["species", "=", species_name],
                                ["date_sown", "=", date_sown]
                            ],
                            fields=["name"])

    # Calculate next index
    index = len(all_batches) + 1

    return f"{date_prefix}-{species_abbr}-{index:02d}"


# ============================================================================
# Collection Helpers
# ============================================================================

def find_unbatched_collections(client: FrappeClient,
                                species: Optional[str] = None,
                                date_collected: Optional[str] = None) -> List[Dict]:
    """
    Find collections that haven't been allocated to a batch yet.

    This queries all batches and their batch_allocations child tables to find
    which collections are already used.

    Args:
        client: Frappe client
        species: Filter by species (optional)
        date_collected: Filter by collection date (optional)

    Returns:
        List of unbatched collections

    Example:
        # Get all unbatched collections
        unbatched = find_unbatched_collections(client)

        # Get unbatched collections for a specific species
        unbatched = find_unbatched_collections(client, species="Magnolia champaca")
    """
    # Get all collections matching the filters
    filters = []
    if species:
        filters.append(["species", "=", species])
    if date_collected:
        filters.append(["date_collected", "=", date_collected])

    collections = client.get("Collection",
                            filters=filters,
                            fields=["name", "date_collected", "species",
                                   "quantity", "condition", "collected_by"])

    # Get all batches to check which collections are allocated
    # Note: We need to get full batch documents to access child tables
    all_batches = client.get("Batch", fields=["name"])

    # Collect all allocated collection IDs
    allocated_collection_ids = set()

    for batch in all_batches:
        try:
            # Get full batch document with child tables
            batch_doc = client.get("Batch", name=batch['name'])

            # Check if batch has allocations (child table might be named differently)
            # Common names: batch_allocations, allocations, collection_allocations
            for field_name in ['batch_allocations', 'allocations', 'collection_allocations']:
                allocations = batch_doc.get(field_name, [])
                for alloc in allocations:
                    # Child table rows might reference collection via different field names
                    coll_id = alloc.get('collection') or alloc.get('collection_id') or alloc.get('collection_name')
                    if coll_id:
                        allocated_collection_ids.add(coll_id)
        except Exception:
            # Skip batches that can't be read or don't have allocations
            continue

    # Filter out allocated collections
    unbatched = [c for c in collections if c['name'] not in allocated_collection_ids]

    return unbatched


# ============================================================================
# Stage Transition: Collection -> Sowing (Create Batch)
# ============================================================================

def create_batch_from_collections(client: FrappeClient,
                                   species: str,
                                   collection_ids: List[str],
                                   section: str,
                                   bed: str,
                                   date_sown: Optional[str] = None,
                                   planted_by: str = "Field Staff") -> Dict:
    """
    Create a batch from collected seeds (Collection -> Sowing transition).

    Args:
        client: Frappe client
        species: Full scientific name
        collection_ids: List of Collection IDs to allocate
        section: Section code (e.g., "B")
        bed: Bed code (e.g., "B1")
        date_sown: Sowing date (defaults to today)
        planted_by: Person name

    Returns:
        Created batch document

    Example:
        batch = create_batch_from_collections(
            client,
            "Magnolia champaca",
            ["C-001", "C-002"],
            "B", "B1"
        )
    """
    if not date_sown:
        date_sown = datetime.now().strftime("%Y-%m-%d")

    # Calculate total seeds from collections
    total_seeds = 0
    for coll_id in collection_ids:
        coll = client.get("Collection", name=coll_id)
        total_seeds += coll.get("quantity", 0)

    # Generate batch ID
    batch_id = generate_batch_id(client, species, date_sown)

    # Create batch
    batch = client.create("Batch", {
        "name": batch_id,
        "species": species,
        "total_seeds": total_seeds,
        "date_sown": date_sown,
        "section": section,
        "bed": bed,
        "stage": "sowing",
        "planted_by": planted_by
    })

    # TODO: Create Batch Allocation records to link collections
    # This requires understanding Frappe child table API

    return batch


# ============================================================================
# Stage Transition: Sowing -> Germination (Log Germination Event)
# ============================================================================

def log_germination(client: FrappeClient,
                    batch_id: str,
                    quantity: int,
                    event_date: Optional[str] = None,
                    notes: str = "") -> Dict:
    """
    Record germination event and update batch stage to Germination.

    Args:
        client: Frappe client
        batch_id: Batch ID
        quantity: Number of germinated seeds
        event_date: Event date (defaults to today)
        notes: Optional notes

    Returns:
        Created Nursery Event document

    Example:
        event = log_germination(client, "15-01-24-MAGCHA-01", 50)
    """
    if not event_date:
        event_date = datetime.now().strftime("%Y-%m-%d")

    # Create germination event
    event = client.create("Nursery Event", {
        "batch": batch_id,
        "event_type": "germination",
        "event_date": event_date,
        "quantity": quantity,
        "notes": notes
    })

    # Update batch stage
    client.update("Batch", batch_id, {"stage": "germination"})

    return event


# ============================================================================
# Stage Transition: Germination -> Growing (Transplant Event)
# ============================================================================

def log_transplant(client: FrappeClient,
                   batch_id: str,
                   from_section: str,
                   from_bed: str,
                   to_section: str,
                   to_bed: str,
                   quantity: int,
                   event_date: Optional[str] = None,
                   notes: str = "") -> Dict:
    """
    Record transplant event and update batch stage to Growing.

    Args:
        client: Frappe client
        batch_id: Batch ID
        from_section: Origin section
        from_bed: Origin bed
        to_section: Destination section
        to_bed: Destination bed
        quantity: Number of seedlings moved
        event_date: Event date (defaults to today)
        notes: Optional notes

    Returns:
        Created Nursery Event document

    Example:
        event = log_transplant(client, "15-01-24-MAGCHA-01",
                              "B", "B1", "D", "D3", 40)
    """
    if not event_date:
        event_date = datetime.now().strftime("%Y-%m-%d")

    # Create transplant event
    event = client.create("Nursery Event", {
        "batch": batch_id,
        "event_type": "transplant",
        "event_date": event_date,
        "quantity": quantity,
        "from_section": from_section,
        "from_bed": from_bed,
        "to_section": to_section,
        "to_bed": to_bed,
        "notes": notes
    })

    # Update batch location and stage
    client.update("Batch", batch_id, {
        "stage": "growing",
        "section": to_section,
        "bed": to_bed
    })

    return event


# ============================================================================
# Stage Transition: Growing -> Growing (Growth Observation)
# ============================================================================

def log_growth_observation(client: FrappeClient,
                           batch_id: str,
                           min_height_cm: float,
                           max_height_cm: float,
                           event_date: Optional[str] = None,
                           notes: str = "") -> Dict:
    """
    Record growth observation (height measurement).

    Note: This does NOT change the batch stage (remains in Growing).

    Args:
        client: Frappe client
        batch_id: Batch ID
        min_height_cm: Minimum height in cm
        max_height_cm: Maximum height in cm
        event_date: Event date (defaults to today)
        notes: Optional notes

    Returns:
        Created Nursery Event document

    Example:
        event = log_growth_observation(client, "15-01-24-MAGCHA-01", 12.0, 18.0)
    """
    if not event_date:
        event_date = datetime.now().strftime("%Y-%m-%d")

    # Create growth event
    event = client.create("Nursery Event", {
        "batch": batch_id,
        "event_type": "growth",
        "event_date": event_date,
        "min_height_cm": min_height_cm,
        "max_height_cm": max_height_cm,
        "notes": notes
    })

    return event


# ============================================================================
# Stage Transition: Growing -> Exit (Sale/Planting Event)
# ============================================================================

def log_exit_event(client: FrappeClient,
                   batch_id: str,
                   quantity: int,
                   event_date: Optional[str] = None,
                   notes: str = "") -> Dict:
    """
    Record exit event (sale/planting) and update batch stage to Exit.

    Args:
        client: Frappe client
        batch_id: Batch ID
        quantity: Number of seedlings exiting
        event_date: Event date (defaults to today)
        notes: Optional notes (e.g., "Sale to customer")

    Returns:
        Created Nursery Event document

    Example:
        event = log_exit_event(client, "15-01-24-MAGCHA-01", 30,
                              notes="Sale to customer")
    """
    if not event_date:
        event_date = datetime.now().strftime("%Y-%m-%d")

    # Create exit event
    event = client.create("Nursery Event", {
        "batch": batch_id,
        "event_type": "exit",
        "event_date": event_date,
        "quantity": quantity,
        "notes": notes
    })

    # Update batch stage
    client.update("Batch", batch_id, {"stage": "exit"})

    return event


# ============================================================================
# Operational Events (No Stage Change)
# ============================================================================

def log_move_event(client: FrappeClient,
                   batch_id: str,
                   from_bed: str,
                   to_bed: str,
                   quantity: int,
                   event_date: Optional[str] = None,
                   notes: str = "") -> Dict:
    """
    Record move event (operational relocation within same stage).

    Args:
        client: Frappe client
        batch_id: Batch ID
        from_bed: Origin bed
        to_bed: Destination bed
        quantity: Number of seedlings moved
        event_date: Event date (defaults to today)
        notes: Optional notes

    Returns:
        Created Nursery Event document
    """
    if not event_date:
        event_date = datetime.now().strftime("%Y-%m-%d")

    # Create move event
    event = client.create("Nursery Event", {
        "batch": batch_id,
        "event_type": "move",
        "event_date": event_date,
        "from_bed": from_bed,
        "to_bed": to_bed,
        "quantity": quantity,
        "notes": notes
    })

    # Update batch location (no stage change)
    client.update("Batch", batch_id, {"bed": to_bed})

    return event


def log_failure_event(client: FrappeClient,
                      batch_id: str,
                      quantity: int,
                      event_date: Optional[str] = None,
                      notes: str = "") -> Dict:
    """
    Record failure event (seedling deaths).

    Args:
        client: Frappe client
        batch_id: Batch ID
        quantity: Number of deaths
        event_date: Event date (defaults to today)
        notes: Optional notes (cause of death, etc.)

    Returns:
        Created Nursery Event document
    """
    if not event_date:
        event_date = datetime.now().strftime("%Y-%m-%d")

    # Create failure event
    event = client.create("Nursery Event", {
        "batch": batch_id,
        "event_type": "failure",
        "event_date": event_date,
        "quantity": quantity,
        "notes": notes
    })

    return event


# ============================================================================
# Query Helpers (Read-Only Stats)
# ============================================================================

def get_batches_by_species(client: FrappeClient,
                           species: str,
                           stage: Optional[str] = None) -> List[Dict]:
    """
    Get all batches for a species, optionally filtered by stage.

    Args:
        client: Frappe client
        species: Full scientific name
        stage: Optional stage filter

    Returns:
        List of batch documents
    """
    filters = [["species", "=", species]]
    if stage:
        filters.append(["stage", "=", stage])

    return client.get("Batch",
                     filters=filters,
                     fields=["name", "stage", "total_seeds", "section", "bed",
                            "date_sown"])


def get_batches_by_stage(client: FrappeClient, stage: str) -> List[Dict]:
    """
    Get all batches in a specific stage.

    Args:
        client: Frappe client
        stage: Stage name (sowing, germination, growing, exit)

    Returns:
        List of batch documents
    """
    return client.get("Batch",
                     filters=[["stage", "=", stage]],
                     fields=["name", "species", "total_seeds", "section", "bed",
                            "date_sown"])


def get_batches_by_section(client: FrappeClient,
                           section: str,
                           bed: Optional[str] = None) -> List[Dict]:
    """
    Get all batches in a section or specific bed.

    Args:
        client: Frappe client
        section: Section code (e.g., "B", "D")
        bed: Optional bed code (e.g., "B1")

    Returns:
        List of batch documents
    """
    filters = [["section", "=", section]]
    if bed:
        filters.append(["bed", "=", bed])

    return client.get("Batch",
                     filters=filters,
                     fields=["name", "species", "stage", "total_seeds", "bed",
                            "date_sown"])


def calculate_germination_rate(client: FrappeClient, batch_id: str) -> Tuple[int, int, float]:
    """
    Calculate germination rate for a batch.

    Args:
        client: Frappe client
        batch_id: Batch ID

    Returns:
        Tuple of (germinated_count, total_seeds, rate_percentage)

    Example:
        germinated, total, rate = calculate_germination_rate(client, "15-01-24-MAGCHA-01")
        # (50, 70, 71.4)
    """
    # Get batch
    batch = client.get("Batch", name=batch_id)
    total_seeds = batch.get("total_seeds", 0)

    # Get germination events
    events = client.get("Nursery Event",
                       filters=[
                           ["batch", "=", batch_id],
                           ["event_type", "=", "germination"]
                       ],
                       fields=["quantity"])

    # Sum germinated
    germinated = sum(e.get("quantity", 0) for e in events)

    # Calculate rate
    rate = (germinated / total_seeds * 100) if total_seeds > 0 else 0.0

    return (germinated, total_seeds, rate)


def get_latest_growth_measurement(client: FrappeClient, batch_id: str) -> Optional[Dict]:
    """
    Get the most recent growth observation for a batch.

    Args:
        client: Frappe client
        batch_id: Batch ID

    Returns:
        Latest growth event or None if no measurements recorded
    """
    events = client.get("Nursery Event",
                       filters=[
                           ["batch", "=", batch_id],
                           ["event_type", "=", "growth"]
                       ],
                       fields=["event_date", "min_height_cm", "max_height_cm", "notes"])

    if not events:
        return None

    # Sort by date descending
    events.sort(key=lambda e: e["event_date"], reverse=True)

    return events[0]


def get_nursery_summary(client: FrappeClient) -> Dict[str, Any]:
    """
    Get comprehensive nursery summary stats.

    Returns:
        Dictionary with stage counts, species breakdown, and totals

    Example:
        summary = get_nursery_summary(client)
        # {
        #   "by_stage": {
        #     "sowing": {"batches": 5, "total_seeds": 350},
        #     ...
        #   },
        #   "by_species": {
        #     "Magnolia champaca": {"batches": 6, "total": 425},
        #     ...
        #   },
        #   "totals": {"batches": 28, "seeds_seedlings": 1990}
        # }
    """
    # Get all non-exit batches
    all_batches = client.get("Batch",
                            filters=[["stage", "!=", "exit"]],
                            fields=["name", "species", "stage", "total_seeds"])

    # Aggregate by stage
    by_stage = {}
    for batch in all_batches:
        stage = batch.get("stage", "unknown")
        if stage not in by_stage:
            by_stage[stage] = {"batches": 0, "total_seeds": 0}

        by_stage[stage]["batches"] += 1
        by_stage[stage]["total_seeds"] += batch.get("total_seeds", 0)

    # Aggregate by species
    by_species = {}
    for batch in all_batches:
        species = batch.get("species", "unknown")
        if species not in by_species:
            by_species[species] = {"batches": 0, "total": 0}

        by_species[species]["batches"] += 1
        by_species[species]["total"] += batch.get("total_seeds", 0)

    # Calculate totals
    total_batches = len(all_batches)
    total_seeds = sum(b.get("total_seeds", 0) for b in all_batches)

    return {
        "by_stage": by_stage,
        "by_species": by_species,
        "totals": {
            "batches": total_batches,
            "seeds_seedlings": total_seeds
        }
    }
