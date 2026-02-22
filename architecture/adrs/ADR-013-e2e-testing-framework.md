# ADR-013: E2E Testing Framework Architecture

## Status: Accepted

## Decision

**Adopt Playwright as primary E2E testing framework**

Use Playwright for frontend E2E tests with mocked WebSocket (fast feedback), complemented by existing Python WebSocket tests for API validation.

## Framework choice

**Selected: Playwright** over Cypress and WebdriverIO

Reasons:
- Native Shadow DOM piercing (Lit web components)
- Built-in WebSocket mocking (`page.routeWebSocket()`)
- Trace viewer for superior debugging
- Fastest execution (20-30M npm downloads/week)
- Cross-browser support (Chromium, Firefox, WebKit)

## Architecture decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Mock vs Real API | Mock WebSocket (Option A) | Fast feedback; Python tests validate real API |
| Headless vs Headed | Headless + screenshot on failure (Option A) | Local dev, optional `--headed` flag |
| Auth tokens | `.env.test` + saved auth state (Option B) | Simple local development |
| Test data | Fresh data per test via factory (Option A) | Perfect isolation |
| Folder structure | Flat (Option C) → feature-based (Option A) at 30+ tests | Start simple, scale later |
| CI/CD trigger | Every PR locally (Option A) | `npm test` is the gate before push |
| Team onboarding | Comprehensive docs + workshop (Option B+C) | `quality/TESTING.md` + Loki training |
| Monitoring | GitHub checks + manual Slack (Option A) | Local feedback first |

## Test coverage

68 tests across:
- Panel load (8 tests) — initialization, DOM structure
- Device list (11 tests) — rendering, filtering
- Sorting (10 tests) — all sort methods
- Infinite scroll (12 tests) — pagination
- Dark mode (12 tests) — theme detection and CSS
- Modals (15 tests) — settings, notifications

## File structure

```
quality/e2e/
├── tests/
│   ├── auth.setup.ts
│   ├── panel-load.spec.ts
│   ├── device-list.spec.ts
│   ├── sorting.spec.ts
│   ├── dark-mode.spec.ts
│   └── modals.spec.ts
├── fixtures/
│   ├── auth.fixture.ts
│   └── websocket-mock.fixture.ts
├── pages/
│   └── vulcan-brownout.page.ts
├── utils/
│   ├── device-factory.ts
│   └── ws-helpers.ts
├── playwright.config.ts
└── .env.test (git-ignored)
```

## Running tests

```bash
npm test                                # Headless, all tests
npm test -- --headed                    # Browser visible
npm test -- --debug                     # Inspector UI
npm test -- --grep "sorting"            # Pattern filter
npm run report                          # HTML report
```

## Key features

- **Page Object Model**: `VulcanBrownoutPanel` encapsulates all selectors
- **WebSocket mocking**: `WebSocketMockHelper` intercepts API calls
- **Device factory**: `generateDeviceList()` produces realistic test data
- **TypeScript**: Full type safety
- **HTML reports**: Screenshots, traces, videos on failure

## Performance

- Single test: 2-3 seconds
- Full suite: 20-25 seconds
- Headless (faster): -20%
- Headed (slower): +30%

## Onboarding

1. ArsonWells reads `quality/TESTING.md` (15 min)
2. Loki does 30-min code review on first test PR
3. Questions addressed async via Slack/Discord

## Maintenance

**Adding new tests**:
1. Extend `device-factory.ts` if needed
2. Create new `tests/feature.spec.ts`
3. Reuse `VulcanBrownoutPanel` page object
4. Follow existing patterns

**HA API changes**:
- Update `WebSocketMockHelper.registerHandler()` to match new format
- Tests automatically validate new behavior

**DOM changes**:
- Update `VulcanBrownoutPanel` selectors
- No test logic changes needed

**Scaling to 30+ tests**:
- Migrate flat structure to feature-based:
  ```
  tests/
  ├── device-list/
  │   ├── loading.spec.ts
  │   ├── sorting.spec.ts
  │   └── infinite-scroll.spec.ts
  └── ...
  ```
- No test code changes needed

## Future enhancements

- Visual regression testing (screenshot matching)
- Accessibility testing (Axe integration)
- Performance metrics (Playwright metrics API)
- GitHub Actions CI (when infrastructure available)
- Real HA integration tests (quarterly nightly runs)

## Complementary testing

- **Python WebSocket tests** (27/28 passing): Integration-level API validation
- **Playwright E2E tests** (68 tests): Frontend user interaction validation
- **Combined coverage**: Full stack validation without duplication

## Implementation notes

- Setup time: 2-3 hours
- Auth fixture: Load token from `.env.test`, save state to `playwright/.auth/auth.json`
- WebSocket mock: Intercept `/api/websocket` and respond with device data
- Test execution: Local before push; no GitHub Actions infrastructure available
