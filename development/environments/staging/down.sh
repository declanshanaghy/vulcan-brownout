#!/usr/bin/env bash
# down.sh — Stop and remove the local Docker staging environment
#
# Usage:
#   ./development/environments/staging/down.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GREEN='\033[0;32m'
BOLD='\033[1m'
YELLOW='\033[1;33m'
RESET='\033[0m'

echo -e "${BOLD}Stopping local staging environment...${RESET}"

cd "$SCRIPT_DIR"
docker compose down --remove-orphans

echo ""
echo -e "${GREEN}Container removed.${RESET}"
echo ""
echo -e "  All HA state has been discarded (no persistent volume)."
echo -e "  Re-run ${YELLOW}./development/environments/staging/up.sh${RESET} to start fresh."
echo ""
