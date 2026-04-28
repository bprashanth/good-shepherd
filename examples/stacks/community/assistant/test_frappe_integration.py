#!/usr/bin/env python3
"""
Test script for Frappe API integration.
Run this inside the OpenClaw container to verify connectivity.
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, '/opt/openclaw/assistant')

from frappe_client import FrappeClient


def test_connectivity():
    """Test 1: Basic connectivity"""
    print("🔌 Test 1: API Connectivity")
    print("-" * 50)

    try:
        client = FrappeClient.from_env()
        print(f"✓ Client created")
        print(f"  Base URL: {client.base_url}")
        print(f"  Site: {client.site_name}")

        if client.ping():
            print("✓ Ping successful - Frappe is reachable!")
            return client
        else:
            print("✗ Ping failed - Frappe not responding")
            return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def test_read_species(client):
    """Test 2: Read Species DocType"""
    print("\n📖 Test 2: Read Species")
    print("-" * 50)

    try:
        species = client.get("Species", fields=["name", "accepted_name"], limit=5)
        if species:
            print(f"✓ Found {len(species)} species:")
            for s in species:
                print(f"  - {s.get('accepted_name', 'Unknown')} ({s.get('name')})")
        else:
            print("  No species found in database")
        return True
    except Exception as e:
        print(f"✗ Error reading species: {e}")
        return False


def test_read_batches(client):
    """Test 3: Read Batch DocType"""
    print("\n📦 Test 3: Read Batches")
    print("-" * 50)

    try:
        batches = client.get("Batch",
                            fields=["name", "species", "stage", "total_seeds"],
                            limit=5)
        if batches:
            print(f"✓ Found {len(batches)} batches:")
            for b in batches:
                print(f"  - {b.get('name')}: {b.get('species')} "
                      f"({b.get('stage')}, {b.get('total_seeds')} seeds)")
        else:
            print("  No batches found in database")
        return True
    except Exception as e:
        print(f"✗ Error reading batches: {e}")
        return False


def test_filtered_query(client):
    """Test 4: Filtered Query"""
    print("\n🔍 Test 4: Filtered Query (batches in germination)")
    print("-" * 50)

    try:
        batches = client.get("Batch",
                            filters=[["stage", "=", "germination"]],
                            fields=["name", "species", "total_seeds"])
        print(f"✓ Found {len(batches) if batches else 0} batches in germination stage")
        if batches:
            for b in batches:
                print(f"  - {b.get('name')}: {b.get('species')}")
        return True
    except Exception as e:
        print(f"✗ Error with filtered query: {e}")
        return False


def test_environment_vars():
    """Test 0: Check environment variables"""
    print("🌍 Test 0: Environment Variables")
    print("-" * 50)

    required_vars = ['FRAPPE_URL', 'FRAPPE_API_KEY', 'FRAPPE_API_SECRET', 'FRAPPE_SITE']
    all_present = True

    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask secrets
            if 'KEY' in var or 'SECRET' in var:
                display_value = value[:8] + '...' if len(value) > 8 else '***'
            else:
                display_value = value
            print(f"✓ {var}: {display_value}")
        else:
            print(f"✗ {var}: NOT SET")
            all_present = False

    return all_present


def main():
    """Run all tests"""
    print("\n" + "=" * 50)
    print("🧪 Frappe Integration Test Suite")
    print("=" * 50 + "\n")

    # Test 0: Environment
    if not test_environment_vars():
        print("\n❌ Environment variables not configured properly")
        print("Make sure .env file is loaded and contains Frappe credentials")
        return 1

    # Test 1: Connectivity
    client = test_connectivity()
    if not client:
        print("\n❌ Cannot connect to Frappe API")
        print("Check that Frappe container is running and network is configured")
        return 1

    # Test 2-4: Read operations
    test_read_species(client)
    test_read_batches(client)
    test_filtered_query(client)

    print("\n" + "=" * 50)
    print("✅ Stage 2 Integration Complete!")
    print("=" * 50)
    print("\nNext: Stage 3 - Load nursery context (SKILL.md, CONVERSATIONS.md)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
