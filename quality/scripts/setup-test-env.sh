#!/bin/bash
#
# Vulcan Brownout QA Test Environment Setup
# Creates mock battery entities on test HA instance via REST API
# Idempotent: Safe to run multiple times
#
# Usage: ./setup-test-env.sh [--create|--cleanup] [--count N]
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"

# Defaults
ACTION="create"
ENTITY_COUNT=10

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --create)
            ACTION="create"
            shift
            ;;
        --cleanup)
            ACTION="cleanup"
            shift
            ;;
        --count)
            ENTITY_COUNT="$2"
            shift 2
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Load environment
if [ ! -f "$ENV_FILE" ]; then
    log_error ".env file not found: $ENV_FILE"
    exit 1
fi

source "$ENV_FILE"

# Verify required variables
if [ -z "${HA_URL:-}" ] || [ -z "${HA_TOKEN:-}" ]; then
    log_error "Missing required environment variables: HA_URL or HA_TOKEN"
    exit 1
fi

HA_BASE_URL="${HA_URL}:${HA_PORT:-8123}"
API_ENDPOINT="${HA_BASE_URL}/api/states"

# Test connection
log_info "Testing connection to $HA_BASE_URL..."
if ! curl -s -m 5 -H "Authorization: Bearer $HA_TOKEN" "$HA_BASE_URL/api/" > /dev/null 2>&1; then
    log_error "Cannot connect to Home Assistant at $HA_BASE_URL"
    log_error "Verify HA_URL, HA_PORT, and HA_TOKEN are correct"
    exit 1
fi

log_info "✓ Connected to Home Assistant"

# Function to create or update battery entity
create_entity() {
    local entity_id=$1
    local friendly_name=$2
    local battery_level=$3

    log_debug "Creating entity: $entity_id ($friendly_name at $battery_level%)"

    RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer $HA_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"state\": \"$battery_level\",
            \"attributes\": {
                \"friendly_name\": \"$friendly_name\",
                \"unit_of_measurement\": \"%\",
                \"device_class\": \"battery\",
                \"icon\": \"mdi:battery-high\"
            }
        }" \
        "$API_ENDPOINT/$entity_id")

    if echo "$RESPONSE" | grep -q '"state"'; then
        log_info "✓ Created: $entity_id ($battery_level%)"
        return 0
    else
        log_warn "Failed to create $entity_id"
        return 1
    fi
}

# Function to create entities
create_entities() {
    log_info "Creating $ENTITY_COUNT test battery entities..."

    for i in $(seq 1 $ENTITY_COUNT); do
        ENTITY_ID="sensor.test_battery_$i"
        BATTERY_LEVEL=$((10 + (i * 7) % 90))  # Vary from 10% to ~95%

        create_entity "$ENTITY_ID" "Test Battery $i" "$BATTERY_LEVEL"
        sleep 0.1
    done

    log_info "✓ Test entities created"
}

# Function to cleanup entities
cleanup_entities() {
    log_info "Cleaning up test battery entities..."

    ENTITIES=$(curl -s "$API_ENDPOINT" \
        -H "Authorization: Bearer $HA_TOKEN" | \
        grep -o '"entity_id":"sensor\.test_battery_[0-9]*"' | \
        cut -d'"' -f4 | sort -u)

    DELETED=0
    for ENTITY_ID in $ENTITIES; do
        log_debug "Deleting $ENTITY_ID..."

        RESPONSE=$(curl -s -X DELETE "$API_ENDPOINT/$ENTITY_ID" \
            -H "Authorization: Bearer $HA_TOKEN")

        if [ -z "$RESPONSE" ] || echo "$RESPONSE" | grep -q '{}'; then
            log_info "✓ Deleted: $ENTITY_ID"
            ((DELETED++)) || true
        else
            log_warn "Failed to delete: $ENTITY_ID"
        fi

        sleep 0.1
    done

    log_info "✓ Cleanup complete ($DELETED entities removed)"
}

# Main execution
case "$ACTION" in
    create)
        create_entities
        log_info ""
        log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        log_info "Test Environment Setup Complete"
        log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        log_info "Home Assistant: $HA_BASE_URL"
        log_info "Created: $ENTITY_COUNT test battery entities"
        log_info ""
        log_info "You can now:"
        log_info "  1. Run integration tests"
        log_info "  2. Test state change detection"
        log_info "  3. Verify battery monitoring UI"
        log_info ""
        ;;
    cleanup)
        cleanup_entities
        log_info ""
        log_info "Test environment cleaned up"
        ;;
    *)
        log_error "Unknown action: $ACTION"
        exit 1
        ;;
esac

exit 0
