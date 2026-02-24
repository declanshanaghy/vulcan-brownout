#!/bin/bash
#
# Vulcan Brownout — Idempotent Test Runner v6.0.0
#
# Runs lint and E2E tests. Safe to re-run at any time.
#
# Usage (execute directly — do NOT use `bash` subshell):
#   ./quality/scripts/run-all-tests.sh              # Run all stages (lint + mock E2E)
#   ./quality/scripts/run-all-tests.sh --lint       # Lint only
#   ./quality/scripts/run-all-tests.sh --e2e        # Playwright mock E2E tests (TARGET_ENV=mock)
#   ./quality/scripts/run-all-tests.sh --docker     # Playwright docker E2E tests (TARGET_ENV=docker)
#   ./quality/scripts/run-all-tests.sh --verbose    # Verbose output
#
# Staging tests: run manually — deploy first, then:
#   cd quality/e2e && npm run test:staging
#
# Exit codes: 0 = all passed, 1 = test failure, 2 = environment error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
E2E_DIR="$PROJECT_ROOT/quality/e2e"
QUALITY_VENV="$PROJECT_ROOT/quality/venv"
QUALITY_PYTHON="$QUALITY_VENV/bin/python"

# Python files to lint
PYTHON_FILES=(
    "$PROJECT_ROOT/quality/integration-tests/test_component_integration.py"
    "$PROJECT_ROOT/quality/integration-tests/mock_fixtures.py"
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
RUN_E2E=false
RUN_DOCKER=false
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
        --lint)       RUN_LINT=true; RUN_ALL=false; shift ;;
        --e2e)        RUN_E2E=true; RUN_ALL=false; shift ;;
        --docker)     RUN_DOCKER=true; RUN_ALL=false; shift ;;
        --staging)    RUN_STAGING=true; RUN_ALL=false; shift ;;
        --verbose|-v) VERBOSE=true; shift ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  (none)      Run all stages: lint + mock E2E tests"
            echo "  --lint      Lint only (flake8 + mypy)"
            echo "  --e2e       Playwright mock E2E tests    (TARGET_ENV=mock,    --project=mock)"
            echo "  --docker    Playwright docker E2E tests  (TARGET_ENV=docker,  --project=docker)"
            echo "  --staging   Playwright staging E2E tests (TARGET_ENV=staging, --project=staging)"
            echo "  --verbose   Enable debug output"
            echo "  --help      Show this help message"
            echo ""
            echo "Exit codes: 0 = all passed, 1 = test failure, 2 = environment error"
            exit 0
            ;;
        *) log_error "Unknown option: $1"; exit 2 ;;
    esac
done

# If --all (default), enable lint + e2e
if [ "$RUN_ALL" = true ]; then
    RUN_LINT=true
    RUN_E2E=true
fi

# ─── Stage 1: Lint ───────────────────────────────────────────────────────────

run_lint() {
    log_stage "Stage 1: Lint (flake8 + mypy)"

    if [ ! -f "$QUALITY_PYTHON" ]; then
        log_error "quality/venv/ not found — run: python3 -m venv quality/venv && quality/venv/bin/pip install -r quality/requirements.txt"
        return 2
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
    if "$QUALITY_PYTHON" -m flake8 --max-line-length=127 --max-complexity=10 "${files_to_lint[@]}"; then
        log_info "flake8 passed"
    else
        log_error "flake8 failed"
        return 1
    fi

    # mypy
    log_info "Running mypy..."
    if "$QUALITY_PYTHON" -m mypy --ignore-missing-imports "${files_to_lint[@]}"; then
        log_info "mypy passed"
    else
        log_error "mypy failed"
        return 1
    fi

    log_info "Lint: ALL PASSED"
    return 0
}

# ─── Stage 2: Playwright E2E Mock Tests ──────────────────────────────────────

_e2e_setup() {
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
}

run_e2e() {
    log_stage "Stage 2: Playwright E2E Tests (TARGET_ENV=mock)"

    _e2e_setup || return $?

    log_info "Running Playwright E2E tests (mock)..."
    if TARGET_ENV=mock npx playwright test --project=mock; then
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

# ─── Stage 3: Docker E2E Tests (optional) ────────────────────────────────────

run_docker() {
    log_stage "Stage 3: Playwright E2E Tests (TARGET_ENV=docker)"

    _e2e_setup || return $?

    log_info "Running Playwright E2E tests (docker)..."
    if TARGET_ENV=docker npx playwright test --project=docker; then
        log_info "Docker E2E tests: ALL PASSED"
        cd "$PROJECT_ROOT"
        return 0
    else
        log_error "Docker E2E tests: FAILED"
        log_info "View report: cd $E2E_DIR && npx playwright show-report"
        cd "$PROJECT_ROOT"
        return 1
    fi
}

# ─── Stage 4: Staging E2E Tests (optional) ───────────────────────────────────

run_staging() {
    log_stage "Stage 4: Playwright E2E Tests (TARGET_ENV=staging)"

    _e2e_setup || return $?

    log_info "Running Playwright E2E tests (staging)..."
    if TARGET_ENV=staging npx playwright test --project=staging; then
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

if [ "$RUN_E2E" = true ]; then
    run_e2e || FAILURES=$((FAILURES + 1))
fi

if [ "$RUN_DOCKER" = true ]; then
    run_docker || FAILURES=$((FAILURES + 1))
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
