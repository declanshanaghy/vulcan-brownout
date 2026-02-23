#!/bin/bash
#
# Vulcan Brownout — Idempotent Test Runner v6.0.0
#
# Runs lint, component tests, and E2E tests. Safe to re-run at any time.
#
# Usage (execute directly — do NOT use `bash` subshell):
#   ./quality/scripts/run-all-tests.sh              # Run all stages
#   ./quality/scripts/run-all-tests.sh --lint       # Lint only
#   ./quality/scripts/run-all-tests.sh --component  # Docker component tests only
#   ./quality/scripts/run-all-tests.sh --e2e        # Playwright E2E mock tests only
#   ./quality/scripts/run-all-tests.sh --docker    # Deploy + Playwright staging tests
#   ./quality/scripts/run-all-tests.sh --verbose    # Verbose output
#
# Exit codes: 0 = all passed, 1 = test failure, 2 = environment error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
E2E_DIR="$PROJECT_ROOT/quality/e2e"

# Python files to lint
PYTHON_FILES=(
    "$PROJECT_ROOT/quality/scripts/test_component_integration.py"
    "$PROJECT_ROOT/quality/scripts/mock_fixtures.py"
    "$PROJECT_ROOT/.github/docker/mock_ha/server.py"
    "$PROJECT_ROOT/.github/docker/mock_ha/fixtures.py"
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# State
VERBOSE=false
RUN_LINT=false
RUN_COMPONENT=false
RUN_E2E=false
RUN_STAGING=false
RUN_ALL=true
FAILURES=0

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_debug() { [ "$VERBOSE" = true ] && echo -e "${BLUE}[DEBUG]${NC} $1" || true; }

log_stage() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --lint)      RUN_LINT=true; RUN_ALL=false; shift ;;
        --component) RUN_COMPONENT=true; RUN_ALL=false; shift ;;
        --e2e)       RUN_E2E=true; RUN_ALL=false; shift ;;
        --docker)   RUN_STAGING=true; RUN_ALL=false; shift ;;
        --verbose|-v) VERBOSE=true; shift ;;
        --help|-h)
            echo "Usage: $0 [--lint] [--component] [--e2e] [--docker] [--verbose]"
            echo "  No flags = run all stages (lint + component + e2e)"
            exit 0
            ;;
        *) log_error "Unknown option: $1"; exit 2 ;;
    esac
done

# If --all (default), enable lint + component + e2e
if [ "$RUN_ALL" = true ]; then
    RUN_LINT=true
    RUN_COMPONENT=true
    RUN_E2E=true
fi

# ─── Stage 1: Lint ───────────────────────────────────────────────────────────

run_lint() {
    log_stage "Stage 1: Lint (flake8 + mypy)"

    # Check flake8 is available
    if ! command -v flake8 &>/dev/null; then
        log_warn "flake8 not found — installing via pip"
        pip install --quiet flake8 mypy 2>/dev/null || {
            log_error "Failed to install flake8/mypy. Install manually: pip install flake8 mypy"
            return 2
        }
    fi

    # Collect existing files only
    local files_to_lint=()
    for f in "${PYTHON_FILES[@]}"; do
        if [ -f "$f" ]; then
            files_to_lint+=("$f")
        else
            log_warn "Skipping missing file: $f"
        fi
    done

    if [ ${#files_to_lint[@]} -eq 0 ]; then
        log_warn "No Python files found to lint"
        return 0
    fi

    # flake8
    log_info "Running flake8..."
    if flake8 --max-line-length=127 --max-complexity=10 "${files_to_lint[@]}"; then
        log_info "flake8 passed"
    else
        log_error "flake8 failed"
        return 1
    fi

    # mypy
    log_info "Running mypy..."
    if mypy --ignore-missing-imports "${files_to_lint[@]}"; then
        log_info "mypy passed"
    else
        log_error "mypy failed"
        return 1
    fi

    log_info "Lint: ALL PASSED"
    return 0
}

# ─── Stage 2: Docker Component Tests ────────────────────────────────────────

run_component() {
    log_stage "Stage 2: Docker Component Tests"

    if ! command -v docker &>/dev/null; then
        log_error "docker not found — cannot run component tests"
        return 2
    fi

    local compose_file="$PROJECT_ROOT/.github/docker-compose.yml"
    if [ ! -f "$compose_file" ]; then
        log_error "docker-compose.yml not found: $compose_file"
        return 2
    fi

    # Clean up any leftover containers from previous runs (idempotent)
    log_info "Cleaning up previous containers..."
    docker compose -f "$compose_file" down --remove-orphans 2>/dev/null || true

    # Build and run
    log_info "Building and running component tests..."
    if docker compose -f "$compose_file" up --build --abort-on-container-exit; then
        log_info "Component tests: ALL PASSED"
        docker compose -f "$compose_file" down --remove-orphans 2>/dev/null || true
        return 0
    else
        log_error "Component tests: FAILED"
        docker compose -f "$compose_file" down --remove-orphans 2>/dev/null || true
        return 1
    fi
}

# ─── Stage 3: Playwright E2E Mock Tests ─────────────────────────────────────

run_e2e() {
    log_stage "Stage 3: Playwright E2E Mock Tests (chromium)"

    if [ ! -d "$E2E_DIR" ]; then
        log_error "E2E directory not found: $E2E_DIR"
        return 2
    fi

    cd "$E2E_DIR"

    # Install deps if needed (idempotent — npm install skips if up to date)
    if [ ! -d "node_modules" ]; then
        log_info "Installing npm dependencies..."
        npm install || { log_error "npm install failed"; return 2; }
    fi

    # Ensure Playwright browsers are installed
    log_info "Ensuring Playwright browsers are installed..."
    npx playwright install chromium 2>/dev/null || true

    # Run tests
    log_info "Running Playwright E2E tests (chromium)..."
    if npx playwright test --project=chromium; then
        log_info "E2E mock tests: ALL PASSED"
        cd "$PROJECT_ROOT"
        return 0
    else
        log_error "E2E mock tests: FAILED"
        log_info "View report: cd $E2E_DIR && npx playwright show-report"
        cd "$PROJECT_ROOT"
        return 1
    fi
}

# ─── Stage 4: Staging Tests (optional) ──────────────────────────────────────

run_staging() {
    log_stage "Stage 4: Deploy + Staging E2E Tests"

    # Deploy first
    local deploy_script="$SCRIPT_DIR/deploy.sh"
    if [ ! -f "$deploy_script" ]; then
        log_error "deploy.sh not found: $deploy_script"
        return 2
    fi

    log_info "Deploying to staging..."
    if "$deploy_script"; then
        log_info "Deploy succeeded"
    else
        log_error "Deploy failed"
        return 1
    fi

    # Run staging E2E tests
    cd "$E2E_DIR"

    log_info "Running staging E2E tests..."
    if STAGING_MODE=true npx playwright test --project=staging; then
        log_info "Staging E2E tests: ALL PASSED"
        cd "$PROJECT_ROOT"
        return 0
    else
        log_error "Staging E2E tests: FAILED"
        log_info "View report: cd $E2E_DIR && npx playwright show-report"
        cd "$PROJECT_ROOT"
        return 1
    fi
}

# ─── Main ────────────────────────────────────────────────────────────────────

echo ""
log_info "Vulcan Brownout Test Runner v6.0.0"
log_info "Project root: $PROJECT_ROOT"
log_info "Timestamp: $(date)"
echo ""

if [ "$RUN_LINT" = true ]; then
    run_lint || FAILURES=$((FAILURES + 1))
fi

if [ "$RUN_COMPONENT" = true ]; then
    run_component || FAILURES=$((FAILURES + 1))
fi

if [ "$RUN_E2E" = true ]; then
    run_e2e || FAILURES=$((FAILURES + 1))
fi

if [ "$RUN_STAGING" = true ]; then
    run_staging || FAILURES=$((FAILURES + 1))
fi

# Summary
echo ""
log_stage "Summary"

if [ "$FAILURES" -eq 0 ]; then
    log_info "ALL STAGES PASSED"
    exit 0
else
    log_error "$FAILURES stage(s) failed"
    exit 1
fi
