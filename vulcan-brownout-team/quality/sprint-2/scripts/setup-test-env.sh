#!/bin/bash
#
# Vulcan Brownout QA Test Environment Setup
# Creates mock battery entities on test HA instance
# Idempotent: Safe to run multiple times
#
# Usage: ./scripts/setup-test-env.sh
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HA_URL="${HA_URL:-http://localhost:8123}"
HA_TOKEN="${HA_TOKEN:-}"

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

# Validate environment
log_info "Validating test environment..."

if [ -z "$HA_TOKEN" ]; then
    log_error "HA_TOKEN environment variable not set"
    log_error "Usage: HA_URL=http://localhost:8123 HA_TOKEN=<token> ./setup-test-env.sh"
    exit 2
fi

# Test connection
log_debug "Testing connection to $HA_URL..."
if ! curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/config" > /dev/null 2>&1; then
    log_error "Cannot connect to Home Assistant at $HA_URL"
    log_error "Verify HA_URL and HA_TOKEN are correct"
    exit 2
fi

log_info "✓ Connected to Home Assistant"

# Function to create or update battery entity
create_battery_entity() {
    local entity_id=$1
    local friendly_name=$2
    local battery_level=$3

    log_debug "Creating/updating entity: $entity_id ($friendly_name at $battery_level%)"

    # Try to set state via REST API
    local response=$(curl -s -w "\n%{http_code}" -X POST \
        -H "Authorization: Bearer $HA_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"state\": \"$battery_level\", \"attributes\": {\"friendly_name\": \"$friendly_name\", \"unit_of_measurement\": \"%\", \"device_class\": \"battery\"}}" \
        "$HA_URL/api/states/$entity_id")

    http_code=$(echo "$response" | tail -n1)

    if [ "$http_code" = "201" ] || [ "$http_code" = "200" ]; then
        log_info "✓ Created: $entity_id"
        return 0
    else
        log_warn "⚠ Failed to create $entity_id (HTTP $http_code)"
        return 1
    fi
}

# Create test battery entities
log_info "Creating test battery entities..."

# Critical (5%)
create_battery_entity "sensor.test_battery_critical" "Test Battery Critical" "5" || true

# Warning (18%)
create_battery_entity "sensor.test_battery_warning" "Test Battery Warning" "18" || true

# Healthy (87%)
create_battery_entity "sensor.test_battery_healthy" "Test Battery Healthy" "87" || true

# Edge case: 0%
create_battery_entity "sensor.test_battery_zero" "Test Battery Zero" "0" || true

# Edge case: 100%
create_battery_entity "sensor.test_battery_max" "Test Battery Max" "100" || true

# Unavailable
log_debug "Creating unavailable entity..."
curl -s -X POST \
    -H "Authorization: Bearer $HA_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"state\": \"unavailable\", \"attributes\": {\"friendly_name\": \"Test Battery Unavailable\", \"unit_of_measurement\": \"%\", \"device_class\": \"battery\"}}" \
    "$HA_URL/api/states/sensor.test_battery_unavailable" > /dev/null 2>&1 || true

log_info "✓ Test entities created"

# Summary
log_info ""
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Test Environment Setup Complete"
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Home Assistant URL: $HA_URL"
log_info ""
log_info "Created test entities:"
log_info "  • sensor.test_battery_critical (5%)"
log_info "  • sensor.test_battery_warning (18%)"
log_info "  • sensor.test_battery_healthy (87%)"
log_info "  • sensor.test_battery_zero (0%)"
log_info "  • sensor.test_battery_max (100%)"
log_info "  • sensor.test_battery_unavailable"
log_info ""
log_info "To change battery levels during testing:"
log_info "  curl -X POST -H 'Authorization: Bearer $HA_TOKEN' \\"
log_info "    -H 'Content-Type: application/json' \\"
log_info "    -d '{\"state\": \"45\"}' \\"
log_info "    http://localhost:8123/api/states/sensor.test_battery_critical"
log_info ""

exit 0
