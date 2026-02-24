#!/usr/bin/env bash
# up.sh — Start the local Docker environment for Vulcan Brownout
#
# What this does:
#   * Starts HA in Docker (bind-mounts integration source live)
#   * Waits for HA to be ready
#   * Prints a summary with next steps
#
# Usage:
#   ./development/environments/docker/up.sh
#
# After running:
#   Open http://localhost:8123 — HA UI with vulcan-brownout panel in sidebar

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
VENV_PATH="${REPO_ROOT}/development/venv"

TIMEOUT=90

# Load YAML configuration from development/environments/docker/
# Note: Environment must be set up first with: ansible-playbook development/ansible/host-setup.yml
if [[ ! -d "$VENV_PATH" ]]; then
    echo "ERROR: Development environment not initialized."
    echo "Run: ansible-playbook development/ansible/host-setup.yml"
    exit 1
fi

# Activate venv and load configuration
export PYTHONPATH="$REPO_ROOT/development/scripts:${PYTHONPATH:-}"
eval "$("$VENV_PATH/bin/python" << 'PYTHON_EOF'
import sys
from config_loader import ConfigLoader

try:
    loader = ConfigLoader('docker')
    env_vars = loader.get_env_vars()
    for key, value in env_vars.items():
        escaped_value = value.replace("'", "'\\''")
        print(f"export {key}='{escaped_value}'")
except Exception as e:
    print(f"ERROR: Failed to load configuration: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_EOF
)"

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${GREEN}[up]${RESET} $*"; }
error()   { echo -e "${RED}[up] ERROR:${RESET} $*" >&2; }
section() { echo -e "\n${BOLD}$*${RESET}"; }

# ── Start Docker Compose ──────────────────────────────────────────────────────
section "Starting Home Assistant container"
cd "$SCRIPT_DIR"
docker compose up -d --force-recreate
info "Container started."

# ── Wait for HA to be ready ───────────────────────────────────────────────────
# Use /api/onboarding — always returns 200 without authentication
section "Waiting for Home Assistant to be ready (up to ${TIMEOUT}s)"
info "HA_URL=${HA_URL}"
info "HA_USERNAME=${HA_USERNAME}"

elapsed=0
until curl -sf "${HA_URL}" >/dev/null 2>&1; do
  if [ "$elapsed" -ge "$TIMEOUT" ]; then
    error "HA did not become ready within ${TIMEOUT}s."
    error "Check logs with: docker logs vulcan-brownout-ha"
    exit 1
  fi
  printf "."
  sleep 5
  elapsed=$((elapsed + 5))
done
echo ""
info "Home Assistant is ready."

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}============================================================${RESET}"
echo -e "${GREEN}  Local Docker environment is ready!${RESET}"
echo -e "${BOLD}============================================================${RESET}"
echo ""
echo -e "  ${BOLD}HA UI:${RESET}    ${HA_URL}"
echo -e "  ${BOLD}Config:${RESET}    development/environments/docker/vulcan-brownout-secrets.yaml"
echo ""
echo -e "  ${BOLD}Next steps:${RESET}"
echo -e "  1. Open ${HA_URL} and log in (admin / sprocket)"
echo -e "  2. Get long-lived token from Profile → Security"
echo -e "  3. Update vulcan-brownout-secrets.yaml with your token"
echo -e "  4. Verify vulcan-brownout panel is visible in the sidebar"
echo -e "  5. Run E2E tests:"
echo -e "     ${YELLOW}HA_URL=${HA_URL} ./quality/scripts/run-all-tests.sh --docker${RESET}"
echo ""
echo -e "  ${BOLD}After editing Python source:${RESET}"
echo -e "  Restart HA to pick up changes:"
echo -e "  ${YELLOW}curl -X POST -H 'Authorization: Bearer \$HA_TOKEN' ${HA_URL}/api/services/homeassistant/restart${RESET}"
echo ""
echo -e "  ${BOLD}To stop:${RESET}  ./development/environments/docker/down.sh"
echo ""
