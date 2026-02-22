#!/bin/bash
#
# Vulcan Brownout Sprint 2 QA Deployment Script
# Idempotent test deployment with health checks
#
# Usage: ./scripts/deploy.sh
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SOURCE_DIR="${PROJECT_ROOT}/development/src/custom_components/vulcan_brownout"
RELEASES_DIR="${PROJECT_ROOT}/releases"
CURRENT_LINK="${RELEASES_DIR}/current"
VERSION="2.0.0"
DEPLOYMENT_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RELEASE_DIR="${RELEASES_DIR}/${VERSION}_${DEPLOYMENT_TIMESTAMP}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Cleanup on error
cleanup() {
    if [ -d "$RELEASE_DIR" ]; then
        if [ ! -L "$CURRENT_LINK" ] || [ "$(readlink "$CURRENT_LINK" 2>/dev/null)" != "$RELEASE_DIR/vulcan_brownout" ]; then
            log_warn "Cleaning up failed deployment: $RELEASE_DIR"
            rm -rf "$RELEASE_DIR" || true
        fi
    fi
}

trap cleanup EXIT

# 1. Validate environment
log_info "Validating environment..."

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

log_info "✓ All required files present"

# 2. Prepare release directory
log_info "Preparing release directory..."

mkdir -p "$RELEASES_DIR"
mkdir -p "$RELEASE_DIR"

# Copy integration files
cp -r "$SOURCE_DIR" "$RELEASE_DIR/vulcan_brownout" || {
    log_error "Failed to copy integration files"
    exit 1
}

log_info "✓ Integration files copied to $RELEASE_DIR"

# 3. Verify Python syntax
log_info "Verifying Python syntax..."

for py_file in "$RELEASE_DIR"/vulcan_brownout/*.py; do
    if ! python3 -m py_compile "$py_file" 2>/dev/null; then
        log_error "Python syntax error in: $(basename "$py_file")"
        exit 1
    fi
done

log_info "✓ Python syntax verified"

# 4. Verify manifest JSON
log_info "Verifying manifest.json..."

if ! python3 -m json.tool "$RELEASE_DIR/vulcan_brownout/manifest.json" > /dev/null 2>&1; then
    log_error "Invalid JSON in manifest.json"
    exit 1
fi

log_info "✓ manifest.json is valid"

# 5. Update symlink (atomic deployment)
log_info "Updating deployment symlink..."

if [ -L "$CURRENT_LINK" ]; then
    PREVIOUS_RELEASE=$(readlink "$CURRENT_LINK" 2>/dev/null || echo "unknown")
    log_info "Previous deployment: $PREVIOUS_RELEASE"
fi

# Create temp symlink and atomic move
rm -f "${CURRENT_LINK}.tmp" || true
ln -s "$RELEASE_DIR/vulcan_brownout" "${CURRENT_LINK}.tmp"
mv -T "${CURRENT_LINK}.tmp" "$CURRENT_LINK" 2>/dev/null || {
    rm -f "$CURRENT_LINK"
    ln -s "$RELEASE_DIR/vulcan_brownout" "$CURRENT_LINK"
}

log_info "✓ Symlink updated to latest release"

# 6. Health check (optional, if HA running)
log_info "Performing health check..."

HEALTH_CHECK_URL="http://localhost:8123/api/vulcan_brownout/health"
MAX_RETRIES=3
RETRY_INTERVAL=5

health_check_passed=0

for ((i=1; i<=MAX_RETRIES; i++)); do
    log_debug "Health check attempt $i/$MAX_RETRIES..."

    if response=$(curl -s -m 10 "$HEALTH_CHECK_URL" 2>/dev/null); then
        if echo "$response" | python3 -m json.tool > /dev/null 2>&1; then
            if echo "$response" | grep -q '"status".*"healthy"'; then
                log_info "✓ Health check passed"
                health_check_passed=1
                break
            fi
        fi
    fi

    if [ $i -lt $MAX_RETRIES ]; then
        log_debug "Health check failed, retrying in ${RETRY_INTERVAL}s..."
        sleep $RETRY_INTERVAL
    fi
done

if [ $health_check_passed -eq 0 ]; then
    log_warn "Health check failed (HA may not be running). Deployment continues."
else
    log_info "✓ Integration health check passed"
fi

# 7. Cleanup old releases (keep last 2)
log_info "Cleaning up old releases..."

OLD_RELEASES=$(find "$RELEASES_DIR" -maxdepth 1 -type d -name "*_*" ! -name "$RELEASE_DIR" | sort -r | tail -n +3)

if [ -n "$OLD_RELEASES" ]; then
    while IFS= read -r old_release; do
        if [ -d "$old_release" ]; then
            log_debug "Removing old release: $(basename "$old_release")"
            rm -rf "$old_release" || true
        fi
    done <<< "$OLD_RELEASES"
    log_info "✓ Old releases cleaned up"
else
    log_info "✓ No old releases to clean"
fi

# 8. Deployment summary
log_info ""
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Vulcan Brownout Sprint 2 QA Deployment Complete"
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Version: $VERSION"
log_info "Release: $RELEASE_DIR"
log_info "Current: $(readlink "$CURRENT_LINK" 2>/dev/null || echo 'not set')"
log_info "Deployed: $(date)"
log_info ""
log_info "Next steps:"
log_info "1. Verify integration in Home Assistant UI"
log_info "2. Check HA logs for any errors"
log_info "3. Run QA test suite: ./scripts/run-all-tests.sh"
log_info "4. Verify real-time updates working"
log_info ""

exit 0
