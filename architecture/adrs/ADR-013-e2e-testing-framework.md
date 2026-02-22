# ADR-013: E2E Testing Framework Architecture

## Status: Accepted

## Context

Vulcan Brownout's frontend panel is a Lit Element web component served within Home Assistant's frontend shell at `http://homeassistant.lan:8123/vulcan-brownout`. The panel communicates with HA via WebSocket API and requires comprehensive E2E testing to validate user interactions across browsers.

Current testing covers backend integration (Python WebSocket tests, 27/28 passing). Frontend E2E testing is needed to validate:
- Shadow DOM component rendering (Lit Element encapsulation)
- WebSocket communication patterns (HA API calls)
- Dark mode CSS custom properties
- Infinite scroll with IntersectionObserver
- Authentication token handling
- Device list sorting/filtering
- Modal interactions

The team must select an E2E framework and establish patterns for:
1. WebSocket mocking vs real HA staging server
2. Headless vs headed browser execution
3. Authentication token management
4. Test data generation
5. Test folder organization
6. CI/CD trigger strategy
7. Team onboarding approach
8. Monitoring and alerting

**Project Constraints:**
- Small team (5 agents)
- No GitHub Actions/CI server (tests run locally from Cowork sandbox)
- SSH access to live HA staging server
- Cannot push to GitHub from sandbox
- Tests should complete in under 60 seconds
- Zero external service budget

## Options Considered

### Framework Selection (Q1 Context)

Loki's research evaluated six frameworks across Shadow DOM, WebSocket, authentication, and performance:

**Top Contenders:**
1. **Playwright** — Native Shadow DOM piercing, built-in WebSocket mocking (v1.48+), excellent DX, fastest performance
2. **WebdriverIO** — W3C WebDriver standard, Lit-specific tooling, strong Shadow DOM support (`shadow$()`)
3. **Cypress** — Best developer debugging (time-travel debug), less ideal WebSocket support (plugin-based)

**Decision: Playwright** (unanimous recommendation in research)

Rationale:
- Native `page.routeWebSocket()` API perfectly matches HA's WebSocket architecture
- CSS locator piercing works seamlessly with Lit's open Shadow DOM
- Fastest test execution (20-30M npm downloads/week)
- Cross-browser support (Chromium, Firefox, WebKit) in single API
- Trace viewer and inspector provide superior debugging vs alternatives
- Minimal setup complexity; no paid tiers required

### Q1: Mock WebSocket Responses vs Real HA Staging Server

**Options:**
- **A (Mock):** Intercept WebSocket with `page.routeWebSocket()` — Fast, controlled, no network latency
- **B (Real Server):** Tests run against `homeassistant.lan:8123` — Validates real API behavior, detects regressions
- **C (Hybrid):** Mock for dev cycle, real server for nightly runs — Best of both worlds, more complex

**Decision: Option A (Mock WebSocket) with integration testing strategy**

Rationale:
- Sprint cycles require fast feedback (mock tests run in <5 seconds per test)
- Staging server is available for manual integration verification, not CI
- No CI infrastructure to run nightly jobs (cannot push from sandbox)
- Our existing Python WebSocket tests (27/28 passing) already validate real HA API contracts
- Complement, don't duplicate: Playwright E2E + Python WS tests = full coverage
- Mock data factory (device-factory.ts) provides reproducible, edge-case-friendly scenarios

Implementation: Use `WebSocketMockHelper` fixture to register response handlers for device list queries, sort operations, and filtering. Tests can simulate pagination, errors, and timeouts deterministically.

### Q2: Headless vs Headed Browser in CI

**Options:**
- **A (Headless):** No UI rendering, faster CI, screenshots on failure
- **B (Headed):** Full video recording every run — debuggable but slow, high storage cost
- **C (Smart):** Headless by default, re-run failures in headed mode — Complex CI setup

**Decision: Option A (Headless) with screenshot on failure + trace viewer**

Rationale:
- No CI infrastructure (tests run locally in sandbox, not GitHub Actions)
- Headless is default for local development (`npm test` = headless)
- Optional `--headed` flag for debugging (`npm test -- --headed`)
- Playwright's trace viewer (`.zip` file) provides superior debugging to video (re-playable UI interactions, full network log, console)
- Screenshots automatically captured on failure; stored in `test-results/`

Configuration:
```typescript
use: {
  screenshot: 'only-on-failure',
  video: 'retain-on-failure',
  trace: 'on-first-retry',
}
```

### Q3: Authentication Token Management

**Options:**
- **A (GitHub Secrets):** Store token in GitHub Actions secrets, inject via env var
- **B (.env file):** Shared `.env.test` (git-ignored), loaded locally
- **C (Token Generation):** Tests generate token via HA API programmatically

**Decision: Option B (.env file) + Option A (GitHub Secrets fallback)**

Rationale:
- **Primary (local development):** Store token in `.env.test` (git-ignored), loaded via `process.env.HA_TOKEN`
  - No GitHub Actions available, so GitHub Secrets infrastructure is not applicable
  - Simpler for local/sandbox testing
  - Token rotated manually (quarterly review)

- **Secondary (future CI):** If GitHub Actions becomes available, use GitHub Secrets with same env var pattern

Process:
1. Create `HA_STAGING_TOKEN` long-lived token in HA frontend (copy from Settings > Developers > Long-Lived Tokens)
2. Store in `.env.test` (or `.env.local`) in project root
3. Load via `process.env.HA_TOKEN` in auth fixture
4. Save authenticated state to `playwright/.auth/auth.json` (git-ignored)
5. Reuse state across test runs (30% performance boost, no re-auth needed)

File structure:
```
.gitignore:
playwright/.auth/auth.json
.env.test
.env.local
```

### Q4: Test Data — Fresh Data Each Run vs Reusable State

**Options:**
- **A (Fresh):** Generate new mock devices per test in `beforeEach`
- **B (Persistent):** Database/file persists state across tests
- **C (Snapshots):** Committed fixture files, reused across runs

**Decision: Option A (Fresh Data) with factory pattern**

Rationale:
- Perfect test isolation (no flakiness from shared state)
- Easy to debug (each test has predictable data)
- Fast to generate (synthetic factory methods, no I/O)
- Edge cases easy to model (`generateMockDevices(10, 200)` = 10th page, 200 devices)

Implementation: `utils/device-factory.ts` provides:
- `generateMockDevices(pageNum, perPage)` — Random device types/statuses
- `generateDevicesByName(names)` — Specific test scenarios
- Deterministic if needed (optional seed parameter for flaky test debugging)

### Q5: Test Folder Structure & Organization

**Options:**
- **A (Feature-based):** `tests/device-list/`, `tests/modals/`, etc. — Scales well
- **B (Layer-based):** `tests/unit/`, `tests/integration/`, `tests/e2e/` — HA-style structure
- **C (Flat):** All tests in `tests/` root — Simple for MVP

**Decision: Option C (Flat) with migration path to Option A**

Rationale:
- MVP phase (~10-15 tests) doesn't need organization overhead
- Simple to find tests (`tests/*.spec.ts`)
- Easy shared fixtures and setup
- **Migration plan:** When suite reaches 30+ tests, migrate to feature-based structure without code changes (just directory moves)

Structure:
```
quality/e2e/
├── tests/
│   ├── auth.setup.ts              # Authentication setup (runs first)
│   ├── panel-load.spec.ts          # Panel initialization
│   ├── device-list.spec.ts         # Device list + infinite scroll
│   ├── sorting.spec.ts             # Sort/filter operations
│   ├── dark-mode.spec.ts           # Dark mode CSS custom properties
│   ├── modals.spec.ts              # Settings & notification modals
│   └── integration.spec.ts         # Multi-step user flows
├── fixtures/
│   ├── auth.fixture.ts
│   └── websocket-mock.fixture.ts
├── pages/
│   └── vulcan-brownout.page.ts     # Page Object Model
├── utils/
│   ├── device-factory.ts
│   └── ws-helpers.ts
└── playwright.config.ts
```

### Q6: CI/CD Trigger Strategy

**Options:**
- **A (Every PR):** Tests run on all PRs, block merge if failing
- **B (Manual):** Developer triggers tests manually
- **C (Smart):** PR tests (frontend changes), nightly tests (regression)
- **D (Nightly):** Scheduled tests only

**Decision: Option A (Every PR) with local execution model**

Rationale:
- No CI infrastructure means "every PR" runs locally before push
- Developer runs `npm test` locally before pushing to GitHub
- Immediate feedback cycle during development
- **Implementation:** `npm test` is the gate; no GitHub Actions (not available)

Future consideration: When/if GitHub Actions becomes available, add workflow for automated PR checks. No code changes needed; just add `.github/workflows/playwright.yml`.

### Q7: Team Skill Level & Onboarding

**Options:**
- **A (Minimal):** Copy-paste examples, quick start
- **B (Comprehensive):** TESTING.md guide + code examples
- **C (Workshop):** Hands-on training + pair programming

**Decision: Option B (Comprehensive Docs) + Option C (Workshop) for high-value scenarios**

Rationale:
- Small team, new to Playwright → invest in learning
- Loki (QA) will lead testing implementation; ArsonWells (builder) will maintain tests
- Create `quality/TESTING.md` with:
  - Quick start (local setup)
  - Common patterns (WebSocket mock, Page Object Model)
  - Debugging guide (trace viewer, headed mode)
  - Adding new tests (template test file)
  - Running specific tests (`npm test -- device-list`)

Onboarding:
1. ArsonWells reads `quality/TESTING.md` (15 min)
2. Loki does 30-min code review on first test PR
3. Questions addressed asynchronously (Slack/Discord)

### Q8: Monitoring & Alerts

**Options:**
- **A (GitHub):** PR checks + email notifications
- **B (Dashboard):** Central health dashboard, trend metrics
- **C (Slack):** Slack pings for failures

**Decision: Option A (GitHub) with manual Slack notification pattern**

Rationale:
- Local test execution: Developer sees pass/fail immediately
- No external services/cost
- Team small enough for async notification (Slack message in dev channel when tests fail)
- **For future CI:** Add GitHub Actions workflow with Slack integration via Action

Process (Local):
- `npm test` fails → Developer sees error in terminal
- Developer fixes, re-runs `npm test`
- On push: Reviewer can re-run tests locally if needed

Process (Future CI):
- GitHub Actions workflow posts results to Slack #dev channel
- Team monitors for failures

## Decision

**Adopt Playwright as the primary E2E testing framework for Vulcan Brownout** with the following architecture:

### Rulings on the 8 Questions

| Q | Ruling | Notes |
|---|--------|-------|
| Q1 | Mock WebSocket (Option A) | Fast feedback, complemented by existing Python WS tests |
| Q2 | Headless + screenshot on failure (Option A) | Local development optional `--headed` flag |
| Q3 | `.env.test` + saved auth state (Option B) | GitHub Secrets pattern ready for future CI |
| Q4 | Fresh data each run (Option A) | Factory pattern in `device-factory.ts` |
| Q5 | Flat structure (Option C) → Option A migration | Start simple, scale later |
| Q6 | Every PR locally (Option A) | `npm test` is the gate before push |
| Q7 | Comprehensive docs + workshop (Option B+C) | TESTING.md + Loki training |
| Q8 | GitHub checks + manual Slack (Option A) | Local feedback first, async communication |

## Consequences

### Positive

1. **Fast feedback loop:** Mock WebSocket tests run in 3-5 sec each; full suite in <30 seconds
2. **Simple setup:** Playwright installs in 30 seconds; no external service dependencies
3. **Shadow DOM ready:** Native CSS locator piercing works out-of-the-box with Lit
4. **Scalable:** Page Object Model + factory pattern support suite growth without refactoring
5. **Team friendly:** Local development; debugging tools built-in; no CI complexity
6. **Complementary coverage:** E2E Playwright tests + existing Python WS tests = full stack validation
7. **Future-proof:** When CI becomes available, no test code changes needed (just add GitHub Actions workflow)

### Negative

1. **Not testing real HA API contract directly:** (Mitigated by existing Python WS tests + manual staging verification)
2. **Mock data must be kept in sync:** If HA API changes, mock handlers need updates (managed via integration test matrix)
3. **Headless only in CI:** Local developers must use `--headed` flag for visual debugging (acceptable; optional)
4. **Manual refresh for new devices:** Panel doesn't auto-detect newly added HA entities (matches Product Design)

### Trade-offs Accepted

- **Speed vs Coverage:** We accept mock testing for speed, keeping real HA integration testing separate (Python)
- **Simple Structure vs Organization:** Start flat; migrate to feature-based at 30+ tests
- **Local Testing vs CI:** Team runs tests locally; GitHub Actions integration deferred (infrastructure not available)

## Implementation Notes

### Setup (2-3 hours)

1. **Install Playwright**
   ```bash
   npm install --save-dev @playwright/test
   npx playwright install
   ```

2. **Create directory structure** (from Loki's recommendation document)
   ```
   quality/e2e/
   ├── playwright.config.ts
   ├── fixtures/
   │   ├── auth.fixture.ts
   │   └── websocket-mock.fixture.ts
   ├── pages/
   │   └── vulcan-brownout.page.ts
   ├── tests/
   │   ├── auth.setup.ts
   │   ├── panel-load.spec.ts
   │   └── ...
   ├── utils/
   │   ├── device-factory.ts
   │   └── ws-helpers.ts
   └── CI/
       └── playwright.yml (template; use when GitHub Actions available)
   ```

3. **Configure `playwright.config.ts`**
   - Base URL: `http://homeassistant.lan:8123`
   - Projects: Chromium (required), Firefox, WebKit (optional, add later)
   - Reporter: HTML + JSON (for CI integration)
   - Storage state: `playwright/.auth/auth.json`

4. **Create auth fixture** (`fixtures/auth.fixture.ts`)
   - Load token from `process.env.HA_TOKEN`
   - Set localStorage keys: `hassAccessToken`, `hassRefreshToken`
   - Save state to `playwright/.auth/auth.json`
   - Reuse state in all tests

5. **Implement WebSocket mock helper** (`utils/ws-helpers.ts`)
   - `routeWebSocket('/api/websocket', ...)` pattern
   - `registerDeviceListResponse()` for device queries
   - `registerHandler()` for custom message types

6. **Create Page Object Model** (`pages/vulcan-brownout.page.ts`)
   - Encapsulates all selectors (`.device-list`, `.device-item`, etc.)
   - Methods for user interactions (`clickSort()`, `setFilter()`, `scrollToBottom()`)
   - Isolates test logic from DOM structure changes

7. **Write initial test suite** (3-4 days, Loki)
   - `auth.setup.ts` — Authentication setup (runs once)
   - `panel-load.spec.ts` — Panel initialization
   - `device-list.spec.ts` — Device list + sorting + filtering + infinite scroll
   - `dark-mode.spec.ts` — Dark mode emulation + CSS validation
   - `modals.spec.ts` — Settings/notification modal interactions

8. **Document in `quality/TESTING.md`**
   - Quick start guide
   - Running tests locally (`npm test`, `npm test -- --headed`, `npm test -- --debug`)
   - Adding new tests (template, patterns)
   - Debugging (trace viewer, headed mode)
   - WebSocket mock patterns
   - Page Object Model examples

### Running Tests (Loki & ArsonWells)

**Local Development:**
```bash
# Setup
export HA_TOKEN="your-long-lived-token"
npm install --save-dev @playwright/test
npx playwright install

# Run all tests (headless)
npm test

# Run specific test file
npm test device-list.spec.ts

# Debug mode (UI inspector)
npm test -- --debug

# Headed browser (watch what happens)
npm test -- --headed

# View HTML report
npx playwright show-report
```

**Test Execution Speed:**
- Single test: 2-3 seconds
- Full suite (10 tests, single browser): 20-30 seconds
- Full suite (3 browsers): 60-90 seconds

### Maintenance Plan

**Adding New Tests:**
1. Extend `device-factory.ts` with new device scenarios if needed
2. Create new `tests/feature.spec.ts` file
3. Reuse `VulcanBrownoutPanel` page object
4. Register WebSocket mocks in `beforeEach`
5. Follow existing test patterns

**Handling HA API Changes:**
1. If HA WebSocket API changes (new endpoint, response format):
   - Update `WebSocketMockHelper.registerHandler()` to match new format
   - Update component to call new endpoint
   - Tests automatically validate new behavior
2. If component DOM changes (class names, data-test attributes):
   - Update `VulcanBrownoutPanel` selectors
   - No test logic changes needed

**Scaling to 30+ Tests:**
When test suite reaches 30+ tests, migrate flat structure to feature-based:
```
tests/
├── device-list/          # All device list tests
│   ├── loading.spec.ts
│   ├── sorting.spec.ts
│   ├── filtering.spec.ts
│   └── infinite-scroll.spec.ts
├── modals/
│   ├── settings.spec.ts
│   └── notifications.spec.ts
└── ...
```
No test code changes needed; just reorganize files.

## Future Enhancements (Post-MVP)

1. **Visual Regression Testing** (after Q2 design stabilization)
   ```typescript
   await expect(page).toMatchScreenshot('device-list-dark.png');
   ```

2. **Accessibility Testing** (Axe integration)
   ```typescript
   await checkA11y(page, 'vulcan-brownout-panel');
   ```

3. **Performance Metrics** (Playwright metrics API)
   ```typescript
   const metrics = await page.metrics();
   expect(metrics.JSHeapUsedSize).toBeLessThan(50 * 1024 * 1024);
   ```

4. **GitHub Actions CI** (when infrastructure available)
   - PR checks on every push
   - Nightly cross-browser runs
   - Artifact storage (reports, videos, traces)
   - Slack notification integration

5. **Real HA Integration Tests** (quarterly)
   - Dedicated nightly suite against live staging HA
   - Validates WebSocket API contract
   - Catches HA version incompatibilities

## Related Decisions

- **ADR-005: Test Environment Setup** — Uses staging HA at `homeassistant.lan:8123`
- **ADR-004: Secrets Management** — HA tokens stored securely (`.env.test`, git-ignored)
- **Python WebSocket Tests** — Integration-level validation (27/28 passing); Playwright complements with E2E

## Approval & Sign-Off

**FiremanDecko (Principal Architect):** ✅ Accepted
**Loki (QA Engineer):** ✅ Recommended
**Implementation Lead (ArsonWells):** (Implementation phase; approval pending code review)

---

## Appendix: Key Links & References

**Playwright Documentation:**
- [Shadow DOM Testing](https://playwright.dev/docs/css-locators/#shadow-dom)
- [WebSocket Mocking](https://playwright.dev/docs/api/class-websocketroute)
- [Authentication](https://playwright.dev/docs/auth)
- [Trace Viewer](https://playwright.dev/docs/trace-viewer)

**Vulcan Brownout Testing Resources:**
- Research: `quality/ux-testing-research.md`
- Recommendation: `quality/ux-testing-recommendation.md`
- Questions: `quality/ux-testing-questions-for-decko.md`
- Decisions: `quality/decko-ux-testing-decisions.md` (this document's companion)

**Existing Test Infrastructure:**
- Python WebSocket tests: `quality/scripts/test_sprint3_integration.py` (27/28 passing)
- Staging HA server: `homeassistant.lan:8123`
- SSH access to sandbox for test execution

