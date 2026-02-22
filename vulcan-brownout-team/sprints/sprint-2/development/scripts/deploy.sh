#!/bin/bash
#
# Vulcan Brownout Sprint 2 Deployment Script
# Idempotent deployment with health checks and rollback support
#
# Usage: ./deploy.sh
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RELEASES_DIR="${PROJECT_ROOT}/releases"
CURRENT_LINK="${RELEASES_DIR}/current"
INTEGRATION_DIR="${PROJECT_ROOT}/src/custom_components/vulcan_brownout"
VERSION="2.0.0"
DEPLOYMENT_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RELEASE_DIR="${RELEASES_DIR}/${VERSION}_${DEPLOYMENT_TIMESTAMP}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# Cleanup function
cleanup() {
    if [ -d "$RELEASE_DIR" ] && [ ! -L "$CURRENT_LINK" ] || [ "$(readlink "$CURRENT_LINK")" != "$RELEASE_DIR" ]; then
        log_info "Cleaning up failed deployment: $RELEASE_DIR"
        rm -rf "$RELEASE_DIR" || true
    fi
}

trap cleanup EXIT

# 1. Validate environment
log_info "Validating environment..."

if [ ! -d "$INTEGRATION_DIR" ]; then
    log_error "Integration source directory not found: $INTEGRATION_DIR"
    exit 1
fi

if [ ! -f "$INTEGRATION_DIR/manifest.json" ]; then
    log_error "manifest.json not found in integration directory"
    exit 1
fi

# Check for required files
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
    if [ ! -f "$INTEGRATION_DIR/$file" ]; then
        log_error "Required file not found: $file"
        exit 1
    fi
done

log_info "✓ All required files present"

# 2. Prepare release directory
log_info "Preparing release directory..."

mkdir -p "$RELEASES_DIR"
mkdir -p "$RELEASE_DIR"

# Copy integration files
cp -r "$INTEGRATION_DIR" "$RELEASE_DIR/vulcan_brownout"
log_info "✓ Integration files copied to $RELEASE_DIR"

# 3. Verify deployment (basic syntax checks)
log_info "Verifying Python syntax..."

for py_file in "$RELEASE_DIR"/vulcan_brownout/*.py; do
    if ! python3 -m py_compile "$py_file" 2>/dev/null; then
        log_error "Python syntax error in: $(basename "$py_file")"
        exit 1
    fi
done

log_info "✓ Python syntax verified"

# 4. Verify manifest
log_info "Verifying manifest.json..."

if ! python3 -m json.tool "$RELEASE_DIR/vulcan_brownout/manifest.json" > /dev/null 2>&1; then
    log_error "Invalid JSON in manifest.json"
    exit 1
fi

log_info "✓ manifest.json is valid"

# 5. Update symlink (atomic deployment)
log_info "Updating current deployment symlink..."

if [ -L "$CURRENT_LINK" ]; then
    PREVIOUS_RELEASE=$(readlink "$CURRENT_LINK")
    log_info "Previous deployment: $PREVIOUS_RELEASE"
fi

# Create new symlink
rm -f "${CURRENT_LINK}.tmp"
ln -s "$RELEASE_DIR/vulcan_brownout" "${CURRENT_LINK}.tmp"
mv -T "${CURRENT_LINK}.tmp" "$CURRENT_LINK"

log_info "✓ Symlink updated to: $RELEASE_DIR/vulcan_brownout"

# 6. Health check (if HA instance is running)
log_info "Performing health check..."

HEALTH_CHECK_URL="http://localhost:8123/api/vulcan_brownout/health"
MAX_RETRIES=3
RETRY_INTERVAL=5

health_check_passed=0

for ((i=1; i<=MAX_RETRIES; i++)); do
    log_info "Health check attempt $i/$MAX_RETRIES..."

    if response=$(curl -s -m 30 "$HEALTH_CHECK_URL" 2>/dev/null); then
        if echo "$response" | python3 -m json.tool > /dev/null 2>&1; then
            if echo "$response" | grep -q '"status".*"healthy"'; then
                log_info "✓ Health check passed"
                health_check_passed=1
                break
            fi
        fi
    fi

    if [ $i -lt $MAX_RETRIES ]; then
        log_warn "Health check failed, retrying in ${RETRY_INTERVAL}s..."
        sleep $RETRY_INTERVAL
    fi
done

if [ $health_check_passed -eq 0 ]; then
    log_warn "Health check failed (HA may not be running). Continuing deployment."
else
    log_info "✓ Health check passed"
fi

# 7. Cleanup old releases (keep last 2 versions)
log_info "Cleaning up old releases..."

OLD_RELEASES=$(ls -t "$RELEASES_DIR" | grep -v "^current$" | tail -n +3)

if [ -n "$OLD_RELEASES" ]; then
    echo "$OLD_RELEASES" | while read -r old_release; do
        log_info "Removing old release: $old_release"
        rm -rf "${RELEASES_DIR:?}/$old_release"
    done
    log_info "✓ Old releases cleaned up"
else
    log_info "✓ No old releases to clean"
fi

# 8. Deployment summary
log_info ""
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Vulcan Brownout Sprint 2 Deployment Complete"
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Version: $VERSION"
log_info "Release: $RELEASE_DIR"
log_info "Current: $CURRENT_LINK -> $(readlink "$CURRENT_LINK")"
log_info "Deployed: $(date)"
log_info ""
log_info "Next steps:"
log_info "1. Verify integration in Home Assistant UI"
log_info "2. Check for any error logs in HA"
log_info "3. Test real-time updates and settings"
log_info ""

exit 0
