# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Vulcan Brownout is a Home Assistant custom integration that provides real-time battery monitoring for battery-powered devices with a dedicated sidebar panel. Backend is Python (async), frontend is a Lit Element web component, E2E tests use Playwright.

**Version**: 6.0.0 | **Min HA Version**: 2026.2.0 | **Integration Domain**: `vulcan_brownout`

**Simplified architecture**: Fixed 15% battery threshold. Shows only `device_class=battery` entities below 15%. No filtering, sorting, pagination, configurable thresholds, or notifications. Two WebSocket commands: `query_entities` (no params) and `subscribe`.

## Commands

### Team members

| {{NAME}} | {{ROLE}} |
|---|---|
| Freya | `product-owner` |
| Luna | `ux-designer` |
| FiremanDecko | `principal-engineer` |
| Loki | `qa-tester` |

When the user says load up a {{ROLE}}. 
Read in the vulcan-brownout-team/{{ROLE}}/SKILL.md for the member's SKILL file.

When the user says load up a team member using their name. 
Use the {{NAME}} to determine the {{ROLE}}.
Read in the vulcan-brownout-team/{{ROLE}}/SKILL.md for the member's SKILL file.

### Common commands and their corresponding script files
#### deploy to docker
Load vulcan-brownout-team/principal-engineer/SKILL.md and execute `development/scripts/deploy.sh`

#### deploy to staging
Load vulcan-brownout-team/qa-tester/SKILL.md and run `ansible-playbook quality/ansible/deploy.yml`


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
flake8 quality/integration-tests/test_component_integration.py quality/integration-tests/mock_fixtures.py \
  .github/docker/mock_ha/server.py .github/docker/mock_ha/fixtures.py

# mypy
mypy quality/integration-tests/test_component_integration.py quality/integration-tests/mock_fixtures.py \
  .github/docker/mock_ha/server.py .github/docker/mock_ha/fixtures.py --ignore-missing-imports
```

### CI
GitHub Actions runs lint then Docker component tests on every push/PR. See `.github/workflows/component-tests.yml`.

## Architecture

### Directory Layout
- `development/src/custom_components/vulcan_brownout/` — Main integration code (Python backend + JS frontend)
- `architecture/` — System design, API contracts, sprint plans, ADRs
- `design/` — UX specs, wireframes, interaction flows
- `quality/scripts/` — Bash scripts only: `run-all-tests.sh`
- `quality/ansible/` — Ansible playbooks: `setup.yml` (one-time env setup), `deploy.yml` (staging deployment)
- `quality/integration-tests/` — Python test suites (component, API, live, environment) and mock fixtures
- `quality/environments/staging/` — Staging environment YAML config (mirrors `development/environments/docker/`)
- `quality/ansible/` — Ansible playbook for one-time quality environment setup (`setup.yml`)
- `quality/venv/` — Python venv for staging/QA work (gitignored, bootstrapped by `quality/ansible/setup.yml`)
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
- E2E staging tests authenticate via HA long-lived token in `quality/environments/staging/vulcan-brownout-secrets.yaml`

### Configuration & Environment Setup (macOS)

**Supported: macOS only** (Sonoma or later)

#### Prerequisites
- **Docker Desktop** — https://www.docker.com/products/docker-desktop
- **Homebrew** — https://brew.sh
- **Ansible** — `brew install ansible`

#### Initial Setup

**Docker dev environment** (run once):
```bash
ansible-playbook development/ansible/host-setup.yml
```
Creates `development/venv/`, installs pyyaml, initialises Docker environment config.

**Quality / staging environment** (run once):
```bash
ansible-playbook quality/ansible/setup.yml
```
This automatically:
- Installs Python 3.12 via Homebrew
- Creates isolated venv at `quality/venv/`
- Installs all test dependencies from `quality/requirements.txt`
- Installs Playwright npm dependencies and Chromium browser
- Creates `quality/environments/staging/vulcan-brownout-secrets.yaml` from template

#### Configuration Files (YAML)
Each environment has config files in its own directory:
- `development/environments/docker/` — Local Docker dev environment
- `quality/environments/staging/` — Staging deployment environment

Each directory contains:
- `vulcan-brownout-config.yaml` — Main config (committed)
- `vulcan-brownout-secrets.yaml.example` — Template (committed)
- `vulcan-brownout-secrets.yaml` — Secrets (gitignored, must be created locally)

#### Setting Up Secrets

**Docker (local dev):**
1. After running the Ansible playbook, start Docker: `./development/environments/docker/up.sh`
2. Log in at http://localhost:8123 (admin / sprocket)
3. Get long-lived token: Profile → Security → Long-Lived Access Tokens
4. Update `development/environments/docker/vulcan-brownout-secrets.yaml` with your token

**Staging:**
1. Run `ansible-playbook quality/ansible/setup.yml` — creates secrets file from template automatically
2. Edit `quality/environments/staging/vulcan-brownout-secrets.yaml` with your staging HA token, password, and SSH details
3. `ansible-playbook quality/ansible/deploy.yml` and all test tooling load config automatically from this file

#### Using Configuration in Code
Set PYTHONPATH before running Python:

```bash
export PYTHONPATH=development/scripts
python your_script.py
```

Then import and use:

```python
from config_loader import ConfigLoader

# Docker (local dev) — uses development/environments/docker/
loader = ConfigLoader('docker')
config = loader.load()
token = config['ha']['token']

# Staging — uses quality/environments/staging/
loader = ConfigLoader('staging', env_base_dir='quality/environments')
config = loader.load()
token = config['ha']['token']
```

#### Linting
- Python lint: flake8 with `max-line-length=127`, `max-complexity=10`

### Team Workflow
Multi-agent Kanban: Product Owner (Freya) → Principal Engineer (FiremanDecko) → QA (Loki). Max 5 stories/sprint, mandatory deployment story. Architecture decisions documented as ADRs.
