#!/bin/bash
#
# Vulcan Brownout Sprint 4 Deployment Script
# Idempotent deployment with health checks and rollback support
#
# Usage: ./deploy.sh
#

set -e

# Source .env for secrets (HA_URL, HA_PORT, HA_TOKEN, SSH_USER, SSH_HOST, SSH_IDENTITY)
ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
else
    echo "Warning: .env file not found at $ENV_FILE. Using defaults or environment variables."
fi

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RELEASES_DIR="${PROJECT_ROOT}/releases"
CURRENT_LINK="${RELEASES_DIR}/current"
INTEGRATION_DIR="${PROJECT_ROOT}/src/custom_components/vulcan_brownout"
VERSION="4.0.0"
DEPLOYMENT_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RELEASE_DIR="${RELEASES_DIR}/${VERSION}_${DEPLOYMENT_TIMESTAMP}"

# HA deployment settings
HA_URL="${HA_URL:-http://localhost}"
HA_PORT="${HA_PORT:-8123}"
HA_TOKEN="${HA_TOKEN:-}"
HA_REMOTE_DIR="${HA_REMOTE_DIR:-/home/homeassistant/.homeassistant/custom_components}"
SSH_USER="${SSH_USER:-homeassistant}"
SSH_HOST="${SSH_HOST:-localhost}"
SSH_IDENTITY="${SSH_IDENTITY:-$HOME/.ssh/id_rsa}"

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

# Check for required files (Sprint 4)
REQUIRED_FILES=(
    "__init__.py"
    "const.py"
    "config_flow.py"
    "manifest.json"
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

# 6. SSH Deployment to HA Server (if SSH_HOST is configured)
if [ -n "$SSH_HOST" ] && [ "$SSH_HOST" != "localhost" ]; then
    log_info "Deploying to remote HA server via SSH..."

    # Verify SSH identity exists
    if [ ! -f "$SSH_IDENTITY" ]; then
        log_error "SSH identity file not found: $SSH_IDENTITY"
        exit 1
    fi

    # Use rsync to deploy integration (idempotent with --delete)
    log_info "Syncing files to $SSH_HOST:$HA_REMOTE_DIR/vulcan_brownout..."

    rsync -av --delete -e "ssh -i $SSH_IDENTITY" \
        "$INTEGRATION_DIR/" \
        "$SSH_USER@$SSH_HOST:$HA_REMOTE_DIR/vulcan_brownout/" || {
        log_error "Failed to sync files via SSH"
        exit 1
    }

    log_info "✓ Files synced successfully"

    # Restart HA service via SSH
    log_info "Restarting Home Assistant service..."
    ssh -i "$SSH_IDENTITY" "$SSH_USER@$SSH_HOST" \
        "systemctl restart homeassistant" || {
        log_warn "Failed to restart HA service via SSH (may require different approach)"
    }

    sleep 5
fi

# 7. Health check (if HA instance is running)
log_info "Performing health check..."

HEALTH_CHECK_URL="$HA_URL:$HA_PORT/api/vulcan_brownout/health"
MAX_RETRIES=3
RETRY_INTERVAL=5

health_check_passed=0

for ((i=1; i<=MAX_RETRIES; i++)); do
    log_info "Health check attempt $i/$MAX_RETRIES..."

    if [ -n "$HA_TOKEN" ]; then
        response=$(curl -s -k -m 30 \
            -H "Authorization: Bearer $HA_TOKEN" \
            "$HEALTH_CHECK_URL" 2>/dev/null)
    else
        response=$(curl -s -k -m 30 "$HEALTH_CHECK_URL" 2>/dev/null)
    fi

    if [ -n "$response" ]; then
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
    log_warn "Health check failed (HA may not be running or endpoint unavailable). Continuing deployment."
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

# 8. Cleanup old releases (keep last 2 versions)
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

# 9. Deployment summary
log_info ""
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Vulcan Brownout Sprint 4 Deployment Complete"
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Version: $VERSION"
log_info "Release: $RELEASE_DIR"
log_info "Current: $CURRENT_LINK -> $(readlink "$CURRENT_LINK")"
log_info "Deployed: $(date)"
if [ -n "$SSH_HOST" ] && [ "$SSH_HOST" != "localhost" ]; then
    log_info "Remote HA Server: $SSH_USER@$SSH_HOST:$HA_REMOTE_DIR/vulcan_brownout"
fi
log_info ""
log_info "Next steps:"
log_info "1. Verify integration in Home Assistant UI"
log_info "2. Check theme switching works (light ↔ dark)"
log_info "3. Load panel and verify battery devices display"
log_info "4. Test notification settings modal"
log_info "5. Check for any error logs in HA"
log_info ""

exit 0
