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
ENV_FILE="$REPO_ROOT/.env"

TIMEOUT=90

# Load .env if present (provides HA_URL, HA_TOKEN, HA_USERNAME, HA_PASSWORD)
# shellcheck source=/dev/null
[ -f "$ENV_FILE" ] && source "$ENV_FILE"

HA_URL="${HA_URL:-http://localhost:8123}"

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
info "HA_URL=${HA_URL}:${HA_PORT}"
info "HA_USERNAME=${HA_USERNAME}"

elapsed=0
until curl -sf "${HA_URL}:${HA_PORT}" >/dev/null 2>&1; do
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
echo -e "  ${BOLD}Login:${RESET}    see .env for credentials"
echo ""
echo -e "  ${BOLD}Next steps:${RESET}"
echo -e "  1. Open ${HA_URL} and log in"
echo -e "  2. Verify vulcan-brownout panel is visible in the sidebar"
echo -e "  3. Run E2E tests:"
echo -e "     ${YELLOW}HA_URL=${HA_URL} ./quality/scripts/run-all-tests.sh --docker${RESET}"
echo ""
echo -e "  ${BOLD}After editing Python source:${RESET}"
echo -e "  Restart HA to pick up changes:"
echo -e "  ${YELLOW}curl -X POST -H 'Authorization: Bearer \$HA_TOKEN' ${HA_URL}/api/services/homeassistant/restart${RESET}"
echo ""
echo -e "  ${BOLD}To stop:${RESET}  ./development/environments/docker/down.sh"
echo ""
