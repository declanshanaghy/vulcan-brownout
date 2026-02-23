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
├── playwright.config.ts            # Configuration (chromium mock + staging projects)
├── global-setup-staging.ts        # Real HA auth for staging project
├── tests/
│   ├── panel-load.spec.ts         # Panel initialization and DOM structure (7 tests)
│   ├── device-list.spec.ts        # Battery device list rendering (5 tests)
│   ├── dark-mode.spec.ts          # Theme detection — staging only (1 test)
│   └── debug-panel.spec.ts        # Debug panel — staging only (1 test)
└── utils/
    ├── device-factory.ts          # Test data generation
    └── ws-mock.ts                 # WebSocket mock
```

## Test Coverage

**14 tests** covering the panel's core functionality:

| Suite | Tests | Project | Coverage |
|-------|-------|---------|----------|
| Panel Load | 7 | chromium | Initialization, DOM structure, empty state, connection badge |
| Device List | 5 | chromium | Battery rendering, threshold filtering, ordering |
| Dark Mode | 1 | staging | Theme detection via HA profile |
| Debug Panel | 1 | staging | Debug panel rendering |

Tests tagged `@mock-only` are skipped by the staging project.

## Common Commands

```bash
# Mock tests (fast, no real HA)
npx playwright test --project=chromium

# Staging tests (requires real HA)
STAGING_MODE=true npx playwright test --project=staging

# Single file
npx playwright test panel-load.spec.ts

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
