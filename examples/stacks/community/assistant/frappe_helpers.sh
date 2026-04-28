#!/bin/bash
# Frappe API Helper Functions for OpenClaw Nursery Assistant
#
# Usage: source this file in bash scripts or agent commands
#   source /home/node/.openclaw/workspace/frappe_helpers.sh
#   frappe_get Species

# Base configuration
FRAPPE_BASE_URL="${FRAPPE_URL:-http://frappe:8000}"
FRAPPE_SITE="${FRAPPE_SITE:-nursery.localhost}"

# Get documents from Frappe
# Usage: frappe_get DocType [filters] [fields] [limit]
# Example: frappe_get Species '[]' '["name","accepted_name"]' 5
frappe_get() {
    local doctype=$1
    local filters=${2:-"[]"}
    local fields=${3:-"[]"}
    local limit=${4:-""}

    local url="${FRAPPE_BASE_URL}/api/resource/${doctype}"
    local params="filters=${filters}"

    if [ -n "$fields" ] && [ "$fields" != "[]" ]; then
        params="${params}&fields=${fields}"
    fi

    if [ -n "$limit" ]; then
        params="${params}&limit=${limit}"
    fi

    curl -s \
        -H "Host: ${FRAPPE_SITE}" \
        -H "Authorization: token ${FRAPPE_API_KEY}:${FRAPPE_API_SECRET}" \
        -H "Accept: application/json" \
        "${url}?${params}"
}

# Get single document by name
# Usage: frappe_get_doc DocType name
# Example: frappe_get_doc Batch "BATCH-001"
frappe_get_doc() {
    local doctype=$1
    local name=$2

    curl -s \
        -H "Host: ${FRAPPE_SITE}" \
        -H "Authorization: token ${FRAPPE_API_KEY}:${FRAPPE_API_SECRET}" \
        -H "Accept: application/json" \
        "${FRAPPE_BASE_URL}/api/resource/${doctype}/${name}"
}

# Create document in Frappe
# Usage: frappe_create DocType '{"field":"value",...}'
# Example: frappe_create Batch '{"species":"Magnolia","total_seeds":100}'
frappe_create() {
    local doctype=$1
    local data=$2

    curl -s -X POST \
        -H "Host: ${FRAPPE_SITE}" \
        -H "Authorization: token ${FRAPPE_API_KEY}:${FRAPPE_API_SECRET}" \
        -H "Content-Type: application/json" \
        -d "${data}" \
        "${FRAPPE_BASE_URL}/api/resource/${doctype}"
}

# Update document in Frappe
# Usage: frappe_update DocType name '{"field":"new_value"}'
# Example: frappe_update Batch "BATCH-001" '{"stage":"germination"}'
frappe_update() {
    local doctype=$1
    local name=$2
    local data=$3

    curl -s -X PUT \
        -H "Host: ${FRAPPE_SITE}" \
        -H "Authorization: token ${FRAPPE_API_KEY}:${FRAPPE_API_SECRET}" \
        -H "Content-Type: application/json" \
        -d "${data}" \
        "${FRAPPE_BASE_URL}/api/resource/${doctype}/${name}"
}

# Ping Frappe API
# Usage: frappe_ping
frappe_ping() {
    curl -s \
        -H "Host: ${FRAPPE_SITE}" \
        -H "Authorization: token ${FRAPPE_API_KEY}:${FRAPPE_API_SECRET}" \
        "${FRAPPE_BASE_URL}/api/method/ping"
}

# Pretty print JSON responses (requires jq)
# Usage: frappe_get Species | frappe_json
frappe_json() {
    if command -v jq &> /dev/null; then
        jq -r '.data'
    else
        cat
    fi
}

# --- Convenience functions for common nursery operations ---

# Get all species
# Usage: get_all_species [limit]
get_all_species() {
    local limit=${1:-20}
    frappe_get Species '[]' '["name","accepted_name","iucn_status"]' "$limit"
}

# Find species by name
# Usage: find_species "Magnolia champaca"
find_species() {
    local name=$1
    local filters="[[\"accepted_name\",\"=\",\"${name}\"]]"
    frappe_get Species "$filters" '["name","accepted_name","iucn_status"]' 1
}

# Get batches by stage
# Usage: get_batches_by_stage germination [limit]
get_batches_by_stage() {
    local stage=$1
    local limit=${2:-20}
    local filters="[[\"stage\",\"=\",\"${stage}\"]]"
    frappe_get Batch "$filters" '["name","species","total_seeds","section","bed","date_sown"]' "$limit"
}

# Get batches by section
# Usage: get_batches_by_section D [limit]
get_batches_by_section() {
    local section=$1
    local limit=${2:-20}
    local filters="[[\"section\",\"=\",\"${section}\"]]"
    frappe_get Batch "$filters" '["name","species","total_seeds","bed","stage"]' "$limit"
}

# Create germination event
# Usage: create_germination_event "BATCH-001" 50 "2024-01-22"
create_germination_event() {
    local batch=$1
    local quantity=$2
    local date=${3:-$(date +%Y-%m-%d)}

    local data="{
        \"batch\": \"${batch}\",
        \"event_type\": \"germination\",
        \"event_date\": \"${date}\",
        \"quantity\": ${quantity}
    }"

    frappe_create "Nursery Event" "$data"
}

# Update batch stage
# Usage: update_batch_stage "BATCH-001" germination
update_batch_stage() {
    local batch=$1
    local stage=$2

    frappe_update Batch "$batch" "{\"stage\":\"${stage}\"}"
}

# Test connectivity
# Usage: test_frappe_connection
test_frappe_connection() {
    echo "Testing Frappe API connectivity..."
    echo "Base URL: ${FRAPPE_BASE_URL}"
    echo "Site: ${FRAPPE_SITE}"
    echo ""

    local result=$(frappe_ping)
    if echo "$result" | grep -q "pong"; then
        echo "✓ Connection successful!"
        return 0
    else
        echo "✗ Connection failed"
        echo "Response: $result"
        return 1
    fi
}

# Print usage examples
frappe_help() {
    cat << 'EOF'
Frappe API Helper Functions
============================

Basic Operations:
  frappe_get DocType [filters] [fields] [limit]
  frappe_get_doc DocType name
  frappe_create DocType '{"json":"data"}'
  frappe_update DocType name '{"json":"data"}'
  frappe_ping

Nursery Shortcuts:
  get_all_species [limit]
  find_species "Species Name"
  get_batches_by_stage stage [limit]
  get_batches_by_section section [limit]
  create_germination_event batch quantity [date]
  update_batch_stage batch stage
  test_frappe_connection

Examples:
  # Get all species
  get_all_species | frappe_json

  # Find a specific species
  find_species "Magnolia champaca" | jq

  # Get batches in germination stage
  get_batches_by_stage germination | frappe_json

  # Create germination event
  create_germination_event "BATCH-001" 50 | jq

  # Update batch stage
  update_batch_stage "BATCH-001" "germination" | jq

Test:
  source frappe_helpers.sh && test_frappe_connection

EOF
}

# Auto-run help if sourced with --help
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    frappe_help
fi
