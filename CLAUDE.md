# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Vulcan Brownout is a Home Assistant custom integration that provides real-time battery monitoring for battery-powered devices with a dedicated sidebar panel. Backend is Python (async), frontend is a Lit Element web component, E2E tests use Playwright.

**Min HA Version**: 2026.2.0 | **Integration Domain**: `vulcan_brownout`

## Commands

### Component Tests (Python/pytest via Docker)
```bash
# Run all component tests (requires Docker)
docker compose -f .github/docker-compose.yml up --build --abort-on-container-exit component_tests

# Run tests directly (if mock HA is already running)
cd quality/scripts && pytest test_component_integration.py -v --tb=short

# Run a single test
cd quality/scripts && pytest test_component_integration.py::TestClassName::test_name -v
```

### E2E Tests (Playwright)
```bash
cd quality/e2e
npm install && npx playwright install chromium  # first time setup

npx playwright test                          # all tests, headless
npx playwright test panel-load.spec.ts       # single suite
npx playwright test -g "test name pattern"   # single test by name
npx playwright test --headed                 # with browser visible
npx playwright show-report                   # view HTML report
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
- `architecture/` — System design, API contracts, sprint plans, ADRs (14 decisions in `adrs/`)
- `design/` — UX specs, wireframes, interaction flows
- `quality/scripts/` — Python component tests with mock fixtures
- `quality/e2e/` — Playwright E2E tests (Page Object Model in `pages/`, factories in `utils/`)
- `.github/docker/mock_ha/` — Mock Home Assistant WebSocket server for testing
- `vulcan-brownout-team/` — Team role definitions and workflow conventions

### Backend (Python, async)
- **Entry point**: `__init__.py` — `async_setup_entry()` registers WebSocket commands, starts BatteryMonitor
- **`battery_monitor.py`** — Entity discovery, filtering, cursor-based pagination, status calculation
- **`websocket_api.py`** — Command handlers (`vulcan-brownout/query_devices`, `subscribe`, `set_threshold`, etc.)
- **`subscription_manager.py`** — Real-time WebSocket push to subscribers on `state_changed` events
- **`notification_manager.py`** — Threshold alerts with per-device frequency caps
- **`config_flow.py`** — Settings UI; thresholds stored in `ConfigEntry.options`

### Frontend (Lit Element, Shadow DOM)
- **Single file**: `frontend/vulcan-brownout-panel.js` — `VulcanBrownoutPanel` class
- Uses Shadow DOM (E2E selectors must use `>>` piercing: `page.locator('vulcan-brownout-panel >> .battery-list')`)
- Theme detection: `hass.themes.darkMode` → DOM attribute fallback → OS `prefers-color-scheme` → default light
- Cursor-based infinite scroll pagination via WebSocket

### WebSocket Protocol
Custom commands under `vulcan-brownout/*` namespace. See `architecture/api-contracts.md` for full spec.
- Cursor format: `base64("{last_changed}|{entity_id}")`
- Pagination: `limit` (1-100), `cursor`, response has `devices`, `total`, `has_more`, `next_cursor`

## Key Conventions

### Git
- Commit format: imperative mood, under 80 chars, then `# Summary of changes` / `## Summary` with bullet list.
- Branch naming: `sprint-N/story-description`, `fix/short-description`, `chore/short-description`
- Push to GitHub after every commit.

### Testing
- `pytest.ini` sets `asyncio_mode = auto` — all async tests run automatically
- Mock HA server in Docker provides pre-provisioned test entities
- E2E tests authenticate via HA long-lived token in `.env`

### Configuration
- `.env` contains secrets (HA token, SSH keys) — **never commit**. Use `.env.example` as template.
- Python lint: flake8 with `max-line-length=127`, `max-complexity=10`

### Team Workflow
Multi-agent Kanban: Product Owner → Principal Engineer → QA. Max 5 stories/sprint, mandatory deployment story. Architecture decisions documented as ADRs.
