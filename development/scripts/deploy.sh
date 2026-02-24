#!/bin/bash
#
# Vulcan Brownout Deployment Script
#
# Integration source is bind-mounted into the Docker container.
# Deployment = restart HA so it picks up the latest source.
#
# Usage: ./development/scripts/deploy.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INTEGRATION_DIR="$SCRIPT_DIR/../src/custom_components/vulcan_brownout"
ENV_DIR="$PROJECT_ROOT/development/environments/docker"
CONFIG_FILE="$ENV_DIR/vulcan-brownout-config.yaml"
SECRETS_FILE="$ENV_DIR/vulcan-brownout-secrets.yaml"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ---------------------------------------------------------------------------
# 1. Load config from YAML using yq
# ---------------------------------------------------------------------------
log_info "Loading configuration from YAML..."

if ! command -v yq &>/dev/null; then
    log_error "yq is not installed. Run: brew install yq"
    exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
    log_error "Config file not found: $CONFIG_FILE"
    exit 1
fi

if [ ! -f "$SECRETS_FILE" ]; then
    log_error "Secrets file not found: $SECRETS_FILE"
    log_error "Copy from template: cp ${SECRETS_FILE}.example $SECRETS_FILE"
    exit 1
fi

HA_HOST=$(yq '.ha.url' "$CONFIG_FILE")
HA_PORT=$(yq '.ha.port' "$CONFIG_FILE")
HA_URL="${HA_HOST}:${HA_PORT}"
HA_TOKEN=$(yq '.ha.token' "$SECRETS_FILE")

if [ -z "$HA_URL" ]; then
    log_error "HA_URL is not set in configuration"
    exit 1
fi

if [ -z "$HA_TOKEN" ] || [ "$HA_TOKEN" = "not-set" ]; then
    log_error "HA_TOKEN is not set. Edit development/environments/docker/vulcan-brownout-secrets.yaml"
    exit 1
fi

log_info "HA URL: $HA_URL"

# ---------------------------------------------------------------------------
# 2. Validate integration source files
# ---------------------------------------------------------------------------
log_info "Validating integration source..."

REQUIRED_FILES=(
    "__init__.py"
    "const.py"
    "config_flow.py"
    "manifest.json"
    "frontend/vulcan-brownout-panel.js"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$INTEGRATION_DIR/$file" ]; then
        log_error "Required file missing: $INTEGRATION_DIR/$file"
        exit 1
    fi
done

log_info "All required files present"

# ---------------------------------------------------------------------------
# 3. Restart HA via REST API
# ---------------------------------------------------------------------------
log_info "Restarting Home Assistant..."

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST \
    -H "Authorization: Bearer $HA_TOKEN" \
    -H "Content-Type: application/json" \
    "$HA_URL/api/services/homeassistant/restart")

if [ "$HTTP_STATUS" != "200" ]; then
    log_error "Restart request failed (HTTP $HTTP_STATUS). Is HA running at $HA_URL?"
    exit 1
fi

log_info "Restart request accepted (HTTP $HTTP_STATUS)"

# ---------------------------------------------------------------------------
# 4. Wait for HA to come back up
# ---------------------------------------------------------------------------
log_info "Waiting for Home Assistant to come back online..."

MAX_RETRIES=24   # 24 × 5s = 2 minutes
RETRY_INTERVAL=5
ready=0

for ((i=1; i<=MAX_RETRIES; i++)); do
    sleep "$RETRY_INTERVAL"
    log_info "Checking HA health (attempt $i/$MAX_RETRIES)..."

    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $HA_TOKEN" \
        "$HA_URL/api/")

    if [ "$HTTP_STATUS" = "200" ]; then
        ready=1
        break
    fi
done

if [ "$ready" -eq 0 ]; then
    log_error "Home Assistant did not come back online within $(( MAX_RETRIES * RETRY_INTERVAL ))s"
    exit 1
fi

# ---------------------------------------------------------------------------
# 5. Done
# ---------------------------------------------------------------------------
log_info ""
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Deployment complete"
log_info "HA is online at $HA_URL"
log_info "Deployed: $(date)"
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exit 0
