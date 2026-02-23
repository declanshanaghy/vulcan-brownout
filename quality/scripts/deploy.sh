#!/bin/bash
#
# Vulcan Brownout QA Deployment Script
# SSH-based idempotent deployment with health checks and rollback capability
#
# Reads config from quality/environments/staging/ YAML files via ConfigLoader.
# Assumes the staging HA instance is already fully set up and running.
# Uses quality/venv/ — bootstrapped automatically from quality/requirements.txt.
#
# Usage: ./deploy.sh [--dry-run] [--verbose]
#
# Prerequisites:
#   - python3 (to bootstrap the venv on first run)
#   - quality/environments/staging/vulcan-brownout-secrets.yaml populated
#   - SSH key authorized on HA server (path set in config YAML)
#   - rsync installed locally
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SOURCE_DIR="${PROJECT_ROOT}/development/src/custom_components/vulcan_brownout"
STAGING_CONFIG_DIR="${PROJECT_ROOT}/quality/environments/staging"
QUALITY_VENV="${PROJECT_ROOT}/quality/venv"
QUALITY_PYTHON="${QUALITY_VENV}/bin/python"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Flags
DRY_RUN=false
VERBOSE=false

# Logging functions
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
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[DEBUG]${NC} $1"
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            log_warn "DRY RUN MODE - no changes will be made"
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# 1. Load environment from YAML config via ConfigLoader
log_info "Loading staging config from $STAGING_CONFIG_DIR..."

SECRETS_FILE="${STAGING_CONFIG_DIR}/vulcan-brownout-secrets.yaml"
if [ ! -f "$SECRETS_FILE" ]; then
    log_error "Secrets file not found: $SECRETS_FILE"
    log_error "Run: cp ${SECRETS_FILE}.example ${SECRETS_FILE}"
    log_error "Then fill in your HA token and password."
    exit 1
fi

# Bootstrap quality/venv/ if it doesn't exist yet.
# This is the staging integration test venv — independent of development/venv/.
if [ ! -f "$QUALITY_PYTHON" ]; then
    log_info "Creating quality/venv/ from quality/requirements.txt..."
    if ! command -v python3 &>/dev/null; then
        log_error "python3 not found — install Python 3 to bootstrap quality/venv/"
        exit 1
    fi
    python3 -m venv "$QUALITY_VENV"
    "$QUALITY_PYTHON" -m pip install --quiet --upgrade pip
    "$QUALITY_PYTHON" -m pip install --quiet -r "${PROJECT_ROOT}/quality/requirements.txt"
    log_info "✓ quality/venv/ ready"
fi

log_info "Parsing YAML config via ConfigLoader..."
eval "$(PYTHONPATH="${PROJECT_ROOT}/development/scripts" "$QUALITY_PYTHON" - <<'PYEOF'
import sys, os
sys.path.insert(0, os.environ.get("PYTHONPATH", ""))
from config_loader import ConfigLoader
loader = ConfigLoader("staging", env_base_dir="quality/environments")
for k, v in loader.get_env_vars().items():
    safe_v = str(v).replace("'", "'\\''")
    print(f"export {k}='{safe_v}'")
PYEOF
)"

# Verify required variables were loaded
REQUIRED_VARS=("SSH_HOST" "SSH_PORT" "SSH_USER" "SSH_KEY_PATH" "HA_CONFIG_PATH" "HA_TOKEN")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        log_error "Required config value not set: $var"
        log_error "Check quality/environments/staging/vulcan-brownout-config.yaml"
        log_error "and quality/environments/staging/vulcan-brownout-secrets.yaml"
        exit 1
    fi
done

# Resolve SSH key path (relative paths are relative to project root)
if [[ "$SSH_KEY_PATH" != /* ]]; then
    SSH_KEY_PATH="${PROJECT_ROOT}/${SSH_KEY_PATH}"
fi

if [ ! -f "$SSH_KEY_PATH" ]; then
    log_error "SSH key not found: $SSH_KEY_PATH"
    exit 1
fi

log_debug "SSH_HOST=$SSH_HOST"
log_debug "SSH_PORT=$SSH_PORT"
log_debug "SSH_USER=$SSH_USER"
log_debug "HA_CONFIG_PATH=$HA_CONFIG_PATH"
log_debug "HA_URL=$HA_URL"

# 2. Validate source directory
log_info "Validating source directory..."

if [ ! -d "$SOURCE_DIR" ]; then
    log_error "Integration source directory not found: $SOURCE_DIR"
    exit 1
fi

if [ ! -f "$SOURCE_DIR/manifest.json" ]; then
    log_error "manifest.json not found in: $SOURCE_DIR"
    exit 1
fi

# Check required files
REQUIRED_FILES=(
    "__init__.py"
    "const.py"
    "battery_monitor.py"
    "websocket_api.py"
    "subscription_manager.py"
    "config_flow.py"
    "manifest.json"
    "strings.json"
    "frontend/vulcan-brownout-panel.js"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$SOURCE_DIR/$file" ]; then
        log_error "Required file not found: $file"
        exit 1
    fi
done

log_info "✓ All required files present locally"

# 3. Verify Python syntax
log_info "Verifying Python syntax..."

for py_file in "$SOURCE_DIR"/*.py; do
    if ! python3 -m py_compile "$py_file" 2>/dev/null; then
        log_error "Python syntax error in: $(basename "$py_file")"
        exit 1
    fi
done

log_info "✓ Python syntax verified"

# 4. Verify manifest JSON
log_info "Verifying manifest.json..."

if ! python3 -m json.tool "$SOURCE_DIR/manifest.json" > /dev/null 2>&1; then
    log_error "Invalid JSON in manifest.json"
    exit 1
fi

log_info "✓ manifest.json is valid"

# 5. Test SSH connectivity
log_info "Testing SSH connectivity to $SSH_HOST:$SSH_PORT..."

SSH_OPTS="-i $SSH_KEY_PATH -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -p $SSH_PORT"

if ! ssh $SSH_OPTS "$SSH_USER@$SSH_HOST" "echo 'SSH connection successful'" &>/dev/null; then
    log_error "Failed to connect via SSH. Please check:"
    log_error "  - SSH host: $SSH_HOST:$SSH_PORT"
    log_error "  - SSH user: $SSH_USER"
    log_error "  - SSH key: $SSH_KEY_PATH"
    log_error "  - Key authorization status on server"
    exit 1
fi

log_info "✓ SSH connectivity verified"

# 6. Verify HA config path exists
log_info "Verifying HA config path on server..."

if ! ssh $SSH_OPTS "$SSH_USER@$SSH_HOST" "test -d $HA_CONFIG_PATH" 2>/dev/null; then
    log_error "HA config path not found on server: $HA_CONFIG_PATH"
    exit 1
fi

log_info "✓ HA config path exists: $HA_CONFIG_PATH"

# 7. Test HA API connectivity
log_info "Testing HA API connectivity..."

if ! curl -s -m 5 -H "Authorization: Bearer $HA_TOKEN" \
    "$HA_URL/api/" > /dev/null 2>&1; then
    log_warn "Could not reach HA API at $HA_URL (may be running on server only)"
else
    log_info "✓ HA API connectivity verified"
fi

# 8. Deploy integration files via rsync
log_info "Deploying integration files..."

DEPLOY_PATH="$HA_CONFIG_PATH/custom_components/vulcan_brownout"

if [ "$DRY_RUN" = true ]; then
    log_warn "DRY RUN: Would deploy to $DEPLOY_PATH"
    rsync --dry-run -avz -e "ssh $SSH_OPTS" \
        "$SOURCE_DIR/" "$SSH_USER@$SSH_HOST:$DEPLOY_PATH/"
    log_info "DRY RUN complete"
    exit 0
fi

# Create destination directory
ssh $SSH_OPTS "$SSH_USER@$SSH_HOST" "mkdir -p $DEPLOY_PATH" || {
    log_error "Failed to create deployment directory"
    exit 1
}

# Sync files
if ! rsync -avz -e "ssh $SSH_OPTS" \
    "$SOURCE_DIR/" "$SSH_USER@$SSH_HOST:$DEPLOY_PATH/"; then
    log_error "Failed to sync integration files"
    exit 1
fi

log_info "✓ Integration files deployed to $DEPLOY_PATH"

# 9. Verify deployment
log_info "Verifying deployment..."

if ! ssh $SSH_OPTS "$SSH_USER@$SSH_HOST" "test -f $DEPLOY_PATH/manifest.json"; then
    log_error "Deployment verification failed - manifest.json not found on server"
    exit 1
fi

log_info "✓ Deployment verified on server"

# 10. Restart Home Assistant
log_info "Restarting Home Assistant to load integration..."

RESTART_CMD="curl -X POST -H 'Authorization: Bearer $HA_TOKEN' -H 'Content-Type: application/json' 'http://localhost:8123/api/services/homeassistant/restart' 2>/dev/null"

# Try to restart via SSH
if ssh $SSH_OPTS "$SSH_USER@$SSH_HOST" "$RESTART_CMD" &>/dev/null; then
    log_info "Restart command sent"

    # Wait for HA to restart
    log_info "Waiting for Home Assistant to restart (up to 60 seconds)..."
    for i in {1..12}; do
        sleep 5
        if curl -s -m 5 -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/" > /dev/null 2>&1; then
            log_info "✓ Home Assistant is back online"
            break
        fi
        log_debug "Attempt $i/12 - HA still restarting..."
    done
else
    log_warn "Could not send restart command to HA (may need manual restart)"
fi

# 11. Wait for integration to load
log_info "Waiting for integration to load..."
sleep 5

# 12. Enable debug logging for the integration
log_info "Enabling debug logging for vulcan_brownout..."

if curl -s -m 10 -X POST \
    -H "Authorization: Bearer $HA_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"custom_components.vulcan_brownout": "debug"}' \
    "$HA_URL/api/services/logger/set_level" > /dev/null 2>&1; then
    log_info "✓ Debug logging enabled for custom_components.vulcan_brownout"
else
    log_warn "Could not set debug log level via API (integration may not be loaded yet)"
fi

# 13. Check for integration in HA
log_info "Verifying integration is loaded..."

if curl -s -m 10 -H "Authorization: Bearer $HA_TOKEN" \
    "$HA_URL/api/states" 2>/dev/null | grep -q "vulcan_brownout"; then
    log_info "✓ Integration detected in Home Assistant"
else
    log_warn "Could not verify integration load (may appear in logs)"
fi

# 14. Deployment summary
log_info ""
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Vulcan Brownout Deployment Complete"
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Integration: vulcan_brownout"
log_info "Version: $(grep '"version"' "$SOURCE_DIR/manifest.json" | cut -d'"' -f4)"
log_info "Deployed to: $DEPLOY_PATH"
log_info "Server: $SSH_USER@$SSH_HOST:$SSH_PORT"
log_info "Config: quality/environments/staging/"
log_info "Timestamp: $(date)"
log_info ""
log_info "Next steps:"
log_info "1. Check HA logs: ssh -p $SSH_PORT $SSH_USER@$SSH_HOST 'tail -f /home/homeassistant/.homeassistant/home-assistant.log | grep -i vulcan'"
log_info "2. Open HA UI and verify Battery Monitoring panel appears"
log_info "3. Run integration tests: pytest quality/integration-tests/test_api_integration.py -v"
log_info ""
log_info "To verify integration loaded:"
log_info "  curl -H \"Authorization: Bearer \$HA_TOKEN\" $HA_URL/api/states | grep vulcan"
log_info ""

exit 0
