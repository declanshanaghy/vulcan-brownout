# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Vulcan Brownout is a Home Assistant custom integration that provides real-time battery monitoring for battery-powered devices with a dedicated sidebar panel. Backend is Python (async), frontend is a Lit Element web component, E2E tests use Playwright.

**Version**: 6.0.0 | **Min HA Version**: 2026.2.0 | **Integration Domain**: `vulcan_brownout`

**Simplified architecture**: Fixed 15% battery threshold. Shows only `device_class=battery` entities below 15%. No filtering, sorting, pagination, configurable thresholds, or notifications. Two WebSocket commands: `query_entities` (no params) and `subscribe`.

## Commands

### Run All Tests (PREFERRED — use this instead of custom bash commands)
```bash
# Run all stages: lint + component tests + E2E mock tests
./quality/scripts/run-all-tests.sh

# Run individual stages
./quality/scripts/run-all-tests.sh --lint       # flake8 + mypy only
./quality/scripts/run-all-tests.sh --component  # Docker component tests only
./quality/scripts/run-all-tests.sh --e2e        # Playwright E2E mock tests only
./quality/scripts/run-all-tests.sh --docker    # Deploy + staging E2E tests
./quality/scripts/run-all-tests.sh --verbose    # Verbose output
```

### Component Tests (Python/pytest via Docker)
```bash
# Run all component tests (requires Docker)
docker compose -f .github/docker-compose.yml up --build --abort-on-container-exit component_tests

# Run a single test
cd quality/scripts && pytest test_component_integration.py::TestClassName::test_name -v
```

### E2E Tests (Playwright)
```bash
cd quality/e2e
npm install && npx playwright install chromium  # first time setup

npx playwright test --project=chromium           # mock tests, headless
npx playwright test panel-load.spec.ts           # single suite
npx playwright test -g "test name pattern"       # single test by name
npx playwright test --headed                     # with browser visible
npx playwright show-report                       # view HTML report
```

### Linting
```bash
# flake8 (max-line-length=127, max-complexity=10)
flake8 quality/scripts/test_component_integration.py quality/scripts/mock_fixtures.py \
  .github/docker/mock_ha/server.py .github/docker/mock_ha/fixtures.py

# mypy
mypy quality/scripts/test_component_integration.py quality/scripts/mock_fixtures.py \
  .github/docker/mock_ha/server.py .github/docker/mock_ha/fixtures.py --ignore-missing-imports
```

### CI
GitHub Actions runs lint then Docker component tests on every push/PR. See `.github/workflows/component-tests.yml`.

## Architecture

### Directory Layout
- `development/src/custom_components/vulcan_brownout/` — Main integration code (Python backend + JS frontend)
- `architecture/` — System design, API contracts, sprint plans, ADRs
- `design/` — UX specs, wireframes, interaction flows
- `quality/scripts/` — Test runner script, Python component tests, mock fixtures, deploy script
- `quality/e2e/` — Playwright E2E tests (Page Object Model in `pages/`, factories in `utils/`)
- `.github/docker/mock_ha/` — Mock Home Assistant WebSocket server for testing
- `vulcan-brownout-team/` — Team role definitions and workflow conventions

### Backend (Python, async)
- **Entry point**: `__init__.py` — `async_setup_entry()` registers WebSocket commands, starts BatteryMonitor
- **`battery_monitor.py`** — Entity discovery, returns entities below fixed 15% threshold sorted by level
- **`websocket_api.py`** — Two command handlers: `query_entities` (no params) and `subscribe`
- **`subscription_manager.py`** — Real-time WebSocket push to subscribers on `state_changed` events
- **`config_flow.py`** — Minimal config flow for integration setup (no options)

### Frontend (Lit Element, Shadow DOM)
- **Single file**: `frontend/vulcan-brownout-panel.js` — `VulcanBrownoutPanel` class (~300 lines)
- Uses Shadow DOM (E2E selectors must use `>>` piercing: `page.locator('vulcan-brownout-panel >> .battery-list')`)
- Theme: inherits HA CSS custom properties (auto/light/dark)
- Shows flat device list with real-time updates; empty state: "All batteries above 15%"

### WebSocket Protocol (v6.0.0)
Two commands under `vulcan-brownout/*` namespace. See `architecture/api-contracts.md`.
- `query_entities`: no params, returns `{ entities: [...], total: N }` — all battery entities below 15%
- `subscribe`: returns `{ subscription_id, status }` — pushes `entity_changed` events

## Key Conventions

### Git
- Commit format: imperative mood, under 80 chars, then `# Summary of changes` / `## Summary` with bullet list.
- Branch naming: `sprint-N/story-description`, `fix/short-description`, `chore/short-description`
- Push to GitHub after every commit.

### Testing
- **Always use `./quality/scripts/run-all-tests.sh`** — never ad-hoc bash commands for running tests
- `pytest.ini` sets `asyncio_mode = auto` — all async tests run automatically
- Mock HA server in Docker provides pre-provisioned test entities
- E2E tests authenticate via HA long-lived token in `.env`

### Configuration
- `.env` contains secrets (HA token, SSH keys) — **never commit**. Use `.env.example` as template.
- Python lint: flake8 with `max-line-length=127`, `max-complexity=10`

### Team Workflow
Multi-agent Kanban: Product Owner (Freya) → Principal Engineer (FiremanDecko) → QA (Loki). Max 5 stories/sprint, mandatory deployment story. Architecture decisions documented as ADRs.
