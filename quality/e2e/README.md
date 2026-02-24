# Vulcan Brownout E2E Testing Framework

Playwright-based end-to-end tests for the Vulcan Brownout Home Assistant panel.

## Quick Start

```bash
cd quality/e2e

# Install (one-time — or run: ansible-playbook quality/ansible/setup.yml)
npm install
npx playwright install chromium

# Run mock tests (no real HA needed)
npm test

# Run staging tests (requires real HA + YAML config)
npm run test:staging

# View report
npm run report
```

## File Structure

```
.
├── playwright.config.ts            # Configuration (mock + docker + staging projects)
├── global-setup.ts                # Real HA auth for docker and staging projects
├── tests/
│   ├── panel-load.spec.ts         # Panel initialization and DOM structure (7 tests)
│   ├── device-list.spec.ts        # Battery device list rendering (5 tests)
│   ├── dark-mode.spec.ts          # Theme detection — real HA only (1 test)
│   └── debug-panel.spec.ts        # Debug panel — real HA only (1 test)
└── utils/
    ├── device-factory.ts          # Test data generation
    └── ws-mock.ts                 # WebSocket mock (active only when TARGET_ENV=mock)
```

## Test Coverage

**14 tests** covering the panel's core functionality:

| Suite | Tests | Project | Coverage |
|-------|-------|---------|----------|
| Panel Load | 7 | mock | Initialization, DOM structure, empty state, connection badge |
| Device List | 5 | mock | Battery rendering, threshold filtering, ordering |
| Dark Mode | 1 | docker/staging | Theme detection via HA profile |
| Debug Panel | 1 | docker/staging | Debug panel rendering |

Tests tagged `@mock-only` are skipped by docker and staging projects.

## Environment Control

Set `TARGET_ENV` to select the target environment:

| `TARGET_ENV` | Project | HA URL | WebSocket | Auth |
|---|---|---|---|---|
| `mock` (default) | `mock` | localhost:8123 | intercepted | none |
| `docker` | `docker` | localhost:8123 | real | storageState |
| `staging` | `staging` | homeassistant.lan:8123 | real | storageState |

## Common Commands

```bash
# Mock tests (Docker HA frontend + mocked vulcan-brownout WS)
TARGET_ENV=mock npx playwright test --project=mock
npm run test:mock

# Docker tests (real vulcan-brownout integration at localhost:8123)
TARGET_ENV=docker npx playwright test --project=docker
npm run test:docker

# Staging tests (real HA at homeassistant.lan:8123)
TARGET_ENV=staging npx playwright test --project=staging
npm run test:staging

# Single file (set TARGET_ENV as needed)
TARGET_ENV=mock npx playwright test panel-load.spec.ts

# Pattern match
npx playwright test -g "empty state"

# Debug inspector
npx playwright test --debug

# HTML report
npx playwright show-report
```

## Key Architecture

**WebSocket Mocking**: Fast, controlled API responses against the mock server
```typescript
const wsMock = new WebSocketMock(page);
await wsMock.setup();
wsMock.mockQueryDevices(generateDeviceList(5));  // 5 low-battery entities
```

**Device Factory**: Realistic test data
```typescript
const devices = generateDeviceList(5);    // 5 devices below 15%
const critical = generateCriticalDevice(); // Single low-battery device
```

**Shadow DOM selectors**: The panel uses Shadow DOM — use `>>` piercing
```typescript
page.locator('vulcan-brownout-panel >> .battery-list')
```

## Staging Setup

Staging tests authenticate against a real HA instance. Config is loaded from
`quality/environments/staging/vulcan-brownout-config.yaml` + secrets via ConfigLoader.

See `quality/ansible/setup.yml` for one-command environment bootstrap.

## Performance

- Single mock test: 2-3 seconds
- Full mock suite: ~10 seconds
- Headless: -20% faster

## Status

Framework: Playwright 1.48+ | Last Updated: February 2026
