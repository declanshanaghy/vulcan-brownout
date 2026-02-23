#!/usr/bin/env bash
# up.sh — Start the local Docker staging environment for Vulcan Brownout
#
# What this does:
#   1. Starts HA in Docker (bind-mounts integration source live)
#   2. Waits for HA to pass its healthcheck
#   3. Runs automated onboarding (creates admin user, exchanges tokens)
#   4. Configures the vulcan_brownout integration via config flow API
#   5. Enables debug logging for the integration
#   6. Writes HA_URL, HA_TOKEN, HA_USERNAME, HA_PASSWORD to .env (project root)
#   7. Prints a summary with next steps
#
# Usage:
#   ./development/environments/staging/up.sh
#
# After running:
#   Open http://localhost:8123 — HA UI with vulcan-brownout panel in sidebar

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"

HA_URL="http://localhost:8123"
HA_USERNAME="admin"
HA_PASSWORD="vulcan-staging-2026"
TIMEOUT=90

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${GREEN}[up]${RESET} $*"; }
warn()    { echo -e "${YELLOW}[up]${RESET} $*"; }
error()   { echo -e "${RED}[up] ERROR:${RESET} $*" >&2; }
section() { echo -e "\n${BOLD}$*${RESET}"; }

# ── Step 1: Start Docker Compose ──────────────────────────────────────────────
section "Step 1/7 — Starting Home Assistant container"
cd "$SCRIPT_DIR"
docker compose up -d
info "Container started."

# ── Step 2: Wait for HA healthcheck ──────────────────────────────────────────
section "Step 2/7 — Waiting for Home Assistant to be ready (up to ${TIMEOUT}s)"
elapsed=0
until curl -sf "${HA_URL}/api/" >/dev/null 2>&1; do
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

# ── Helper: POST with JSON body ───────────────────────────────────────────────
post_json() {
  local url="$1"
  local body="$2"
  curl -sf -X POST \
    -H "Content-Type: application/json" \
    -d "$body" \
    "$url"
}

post_auth() {
  local url="$1"
  local token="$2"
  local body="$3"
  curl -sf -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $token" \
    -d "$body" \
    "$url"
}

# ── Step 3: Onboarding — create admin user ────────────────────────────────────
section "Step 3/7 — Running HA onboarding (creating admin user)"

# Check if already onboarded
onboarding_status=$(curl -sf "${HA_URL}/api/onboarding" || echo '{"done":[]}')
if echo "$onboarding_status" | grep -q '"user"'; then
  warn "HA appears to already be onboarded. Skipping user creation."
  warn "If this is a fresh container, try: docker compose down && docker compose up -d"
  warn "Then re-run this script."
  exit 1
fi

onboard_response=$(post_json "${HA_URL}/api/onboarding/users" \
  "{\"client_id\":\"http://localhost:8123/\",\"name\":\"Admin\",\"username\":\"${HA_USERNAME}\",\"password\":\"${HA_PASSWORD}\",\"language\":\"en\"}")

auth_code=$(echo "$onboard_response" | python3 -c "import sys,json; print(json.load(sys.stdin)['auth_code'])")
info "Admin user created. Auth code received."

# ── Step 4: Exchange auth code for access token ───────────────────────────────
section "Step 4/7 — Exchanging auth code for access token"

token_response=$(curl -sf -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=${auth_code}&client_id=http://localhost:8123/" \
  "${HA_URL}/auth/token")

access_token=$(echo "$token_response" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
info "Access token obtained."

# ── Step 5: Generate long-lived access token ──────────────────────────────────
section "Step 5/7 — Generating long-lived access token"

llat_response=$(post_auth "${HA_URL}/api/auth/long_lived_access_token" "$access_token" \
  '{"lifespan":3650,"client_name":"vulcan-brownout-staging"}')

ha_token=$(echo "$llat_response" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
info "Long-lived token generated (valid 10 years)."

# ── Step 6: Configure vulcan_brownout integration ─────────────────────────────
section "Step 6/7 — Configuring vulcan_brownout integration"

# Start config flow
flow_response=$(post_auth "${HA_URL}/api/config/config_entries/flow" "$ha_token" \
  '{"handler":"vulcan_brownout"}')

flow_id=$(echo "$flow_response" | python3 -c "import sys,json; print(json.load(sys.stdin)['flow_id'])")
info "Config flow started (flow_id: ${flow_id})."

# Complete config flow (no user input required — minimal config flow)
post_auth "${HA_URL}/api/config/config_entries/flow/${flow_id}" "$ha_token" '{}' >/dev/null
info "Integration configured."

# ── Step 7: Enable debug logging ──────────────────────────────────────────────
section "Step 7/7 — Enabling debug logging for vulcan_brownout"

post_auth "${HA_URL}/api/services/logger/set_level" "$ha_token" \
  '{"custom_components.vulcan_brownout":"debug"}' >/dev/null
info "Debug logging enabled."

# ── Write .env ────────────────────────────────────────────────────────────────
section "Writing credentials to .env"

# Remove any existing staging block and append fresh values
if [ -f "$ENV_FILE" ]; then
  # Strip lines between staging markers (if present from a previous run)
  python3 - "$ENV_FILE" <<'PYEOF'
import sys, re
path = sys.argv[1]
with open(path) as f:
    content = f.read()
# Remove existing staging block
content = re.sub(
    r'\n?# --- LOCAL DOCKER STAGING.*?# --- END LOCAL DOCKER STAGING ---\n?',
    '',
    content,
    flags=re.DOTALL
)
with open(path, 'w') as f:
    f.write(content)
PYEOF
fi

cat >> "$ENV_FILE" <<EOF

# --- LOCAL DOCKER STAGING (written by up.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)) ---
HA_URL=${HA_URL}
HA_TOKEN=${ha_token}
HA_USERNAME=${HA_USERNAME}
HA_PASSWORD=${HA_PASSWORD}
# --- END LOCAL DOCKER STAGING ---
EOF

info ".env updated at $ENV_FILE"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}============================================================${RESET}"
echo -e "${GREEN}  Local staging environment is ready!${RESET}"
echo -e "${BOLD}============================================================${RESET}"
echo ""
echo -e "  ${BOLD}HA UI:${RESET}      ${HA_URL}"
echo -e "  ${BOLD}Username:${RESET}   ${HA_USERNAME}"
echo -e "  ${BOLD}Password:${RESET}   ${HA_PASSWORD}"
echo -e "  ${BOLD}Token:${RESET}      ${ha_token:0:20}... (full token written to .env)"
echo ""
echo -e "  ${BOLD}Next steps:${RESET}"
echo -e "  1. Open ${HA_URL} and log in"
echo -e "  2. Verify vulcan-brownout panel is visible in the sidebar"
echo -e "  3. Run staging E2E tests:"
echo -e "     ${YELLOW}HA_URL=${HA_URL} ./quality/scripts/run-all-tests.sh --staging${RESET}"
echo ""
echo -e "  ${BOLD}After editing Python source:${RESET}"
echo -e "  Restart HA to pick up changes:"
echo -e "  ${YELLOW}curl -X POST -H 'Authorization: Bearer \$HA_TOKEN' ${HA_URL}/api/services/homeassistant/restart${RESET}"
echo ""
echo -e "  ${BOLD}To stop:${RESET}  ./development/environments/staging/down.sh"
echo ""
