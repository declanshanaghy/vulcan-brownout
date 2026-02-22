# Vulcan Brownout E2E Testing Framework

Playwright-based end-to-end tests for the Vulcan Brownout Home Assistant panel.

## Quick Start

```bash
cd quality/e2e

# Install (one-time)
npm install
npx playwright install chromium

# Run all tests
npm test

# Run with browser UI
npm test -- --headed

# View report
npm run report
```

## File Structure

```
.
├── .env.test                       # HA token (git-ignored)
├── playwright.config.ts            # Configuration
├── pages/
│   └── vulcan-panel.page.ts       # Page Object Model
├── tests/
│   ├── panel-load.spec.ts         # Panel initialization (8 tests)
│   ├── device-list.spec.ts        # Device list rendering (11 tests)
│   ├── sorting.spec.ts            # Sorting (10 tests)
│   ├── infinite-scroll.spec.ts    # Pagination (12 tests)
│   ├── dark-mode.spec.ts          # Theme support (12 tests)
│   └── modals.spec.ts             # Modals (15 tests)
└── utils/
    ├── device-factory.ts          # Test data generation
    └── ws-mock.ts                 # WebSocket mock
```

## Test Coverage

**68 tests** covering major panel functionality:

| Suite | Tests | Coverage |
|-------|-------|----------|
| Panel Load | 8 | Initialization, DOM structure |
| Device List | 11 | Rendering, filtering |
| Sorting | 10 | All sort methods |
| Infinite Scroll | 12 | Pagination, loading |
| Dark Mode | 12 | Theme detection, CSS |
| Modals | 15 | Settings, notifications |

## Common Commands

```bash
npm test                          # All tests, headless
npm test -- --headed              # Browser visible
npm test -- device-list.spec.ts   # Specific file
npm test -- --grep "sorting"      # Pattern match
npm test -- --debug               # Inspector
npm run report                    # HTML report
```

## Key Architecture

**Page Object Model**: Encapsulates all panel interactions
```typescript
const panel = new VulcanBrownoutPanel(page);
await panel.goto();
await panel.clickSort();
expect(await panel.getDeviceCount()).toBe(20);
```

**WebSocket Mocking**: Fast, controlled API responses
```typescript
const wsMock = new WebSocketMock(page);
await wsMock.setup();
wsMock.mockQueryDevices(generateDeviceList(0, 20));
```

**Device Factory**: Realistic test data
```typescript
const devices = generateDeviceList(0, 9);        // Random
const critical = generateCriticalDevice();        // Low battery
```

## Performance

- Single test: 2-3 seconds
- Full suite: 20-25 seconds
- Headless: -20% faster
- Headed: +30% slower

## Documentation

See [../TESTING.md](../TESTING.md) for:
- Setup instructions
- Authentication details
- Architecture overview
- Common patterns
- Debugging guide
- Adding new tests
- Troubleshooting

## Status

**Ready for deployment** — Framework established, tests passing, documentation complete.

Framework: Playwright 1.48+
Last Updated: February 2026
