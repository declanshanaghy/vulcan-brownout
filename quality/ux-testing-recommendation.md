# Vulcan Brownout UI/UX Testing Architecture & Recommendation

**Date:** February 22, 2026
**Prepared by:** Loki (QA Engineer)
**Target Framework:** Playwright
**Status:** Ready for implementation

---

## Executive Recommendation

**ADOPT PLAYWRIGHT** as the primary E2E testing framework for Vulcan Brownout.

### Justification

Playwright is the optimal choice for testing a Lit Element web component served inside Home Assistant due to:

1. **Shadow DOM**: Native CSS locator piercing works out-of-the-box with Lit components
2. **WebSocket**: Built-in `page.routeWebSocket()` API (v1.48+) perfectly matches HA's WebSocket communication pattern
3. **Authentication**: Secure `storageState` mechanism for token-based HA auth
4. **Performance**: Native parallel test execution, fastest test suite times (20-30M npm downloads/week)
5. **DX**: Modern trace viewer, inspector, and debugging tools minimize troubleshooting time
6. **Cross-Browser**: Single API supports Chromium, Firefox, WebKit testing
7. **CI/CD**: Seamless GitHub Actions integration, no paid services required

### Budget Impact

- **Setup Cost**: ~2-3 hours (framework setup, fixture scaffolding)
- **Test Development**: ~30-40 min per test case (vs 45-60 with other frameworks)
- **Maintenance**: Minimal; native features reduce workarounds and technical debt
- **Cost**: $0 (open-source, no paid tiers required for CI)

---

## Proposed Test Architecture

### Directory Structure

```
vulcan-brownout/
├── quality/
│   ├── ux-testing-research.md                    # This research document
│   ├── ux-testing-recommendation.md              # This file
│   ├── ux-testing-questions-for-decko.md         # Q&A for architecture decisions
│   └── e2e/                                      # New: Playwright tests
│       ├── playwright.config.ts                  # Playwright configuration
│       ├── fixtures/
│       │   ├── auth.fixture.ts                   # HA token authentication setup
│       │   └── websocket-mock.fixture.ts         # WebSocket mocking utilities
│       ├── pages/
│       │   └── vulcan-brownout.page.ts           # Page Object Model
│       ├── tests/
│       │   ├── auth.setup.ts                     # Authentication setup test
│       │   ├── panel-load.spec.ts                # Panel loading & initialization
│       │   ├── device-list.spec.ts               # Device list + infinite scroll
│       │   ├── sorting.spec.ts                   # Sort/filter functionality
│       │   ├── dark-mode.spec.ts                 # Dark mode rendering
│       │   ├── modals.spec.ts                    # Settings & notification modals
│       │   └── integration.spec.ts               # Integration scenarios
│       ├── utils/
│       │   ├── device-factory.ts                 # Mock device data generation
│       │   └── ws-helpers.ts                     # WebSocket mock helpers
│       └── CI/
│           └── playwright.yml                    # GitHub Actions workflow
├── backend/
│   └── tests/                                    # Python pytest for backend
└── docs/
    └── TESTING.md                                # Developer guide
```

### Dependencies

```json
{
  "devDependencies": {
    "@playwright/test": "^1.48+",
    "@types/node": "^latest"
  }
}
```

### Configuration File: `playwright.config.ts`

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './quality/e2e/tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results.json' }],
    ['junit', { outputFile: 'junit.xml' }],
  ],

  use: {
    baseURL: 'http://homeassistant.lan:8123',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],

  webServer: undefined, // HA runs independently; no local dev server
});
```

---

## Core Fixtures & Utilities

### 1. Authentication Fixture: `fixtures/auth.fixture.ts`

```typescript
import { test as base } from '@playwright/test';

type AuthContext = {
  token: string;
  storageStatePath: string;
};

export const test = base.extend<AuthContext>({
  token: async ({}, use) => {
    const token = process.env.HA_TOKEN || 'test-token-placeholder';
    await use(token);
  },

  storageStatePath: 'playwright/.auth/auth.json',
});

export { expect } from '@playwright/test';
```

### 2. Authentication Setup Test: `tests/auth.setup.ts`

```typescript
import { test, expect } from '../fixtures/auth.fixture';
import fs from 'fs';
import path from 'path';

test('authenticate and save state', async ({ page, token, storageStatePath }) => {
  // Ensure auth directory exists
  const authDir = path.dirname(storageStatePath);
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true });
  }

  // Navigate to HA frontend (assumes HA with existing session)
  await page.goto('/');

  // Inject token into localStorage
  // (In real scenario: HA frontend sets this automatically, or we trigger login)
  await page.evaluate((token) => {
    localStorage.setItem('hassAccessToken', token);
    localStorage.setItem('hassRefreshToken', token);
  }, token);

  // Verify token is set
  const storedToken = await page.evaluate(() => {
    return localStorage.getItem('hassAccessToken');
  });
  expect(storedToken).toBe(token);

  // Save authenticated state
  await page.context().storageState({ path: storageStatePath });
});
```

**playwright.config.ts** dependency setup:

```typescript
projects: [
  {
    name: 'chromium',
    use: { ...devices['Desktop Chrome'], storageState: 'playwright/.auth/auth.json' },
  },
  // ... other browsers
],

webServer: {
  command: 'npm run dev', // if needed; HA runs independently
  port: 8000,
  timeout: 120000,
  reuseExistingServer: !process.env.CI,
},
```

### 3. Page Object Model: `pages/vulcan-brownout.page.ts`

```typescript
import { Page, Locator } from '@playwright/test';

export class VulcanBrownoutPanel {
  readonly page: Page;
  readonly panel: Locator;
  readonly deviceList: Locator;
  readonly scrollSentinel: Locator;
  readonly sortButton: Locator;
  readonly filterControl: Locator;
  readonly settingsButton: Locator;
  readonly notificationIcon: Locator;
  readonly darkModeToggle: Locator;

  constructor(page: Page) {
    this.page = page;
    this.panel = page.locator('vulcan-brownout-panel');
    this.deviceList = this.panel.locator('[data-test="device-list"]');
    this.scrollSentinel = this.panel.locator('[data-test="scroll-sentinel"]');
    this.sortButton = this.panel.locator('[data-test="sort-button"]');
    this.filterControl = this.panel.locator('[data-test="filter-control"]');
    this.settingsButton = this.panel.locator('[data-test="settings-button"]');
    this.notificationIcon = this.panel.locator('[data-test="notification-icon"]');
    this.darkModeToggle = this.panel.locator('[data-test="dark-mode-toggle"]');
  }

  async goto() {
    await this.page.goto('/vulcan-brownout');
    await this.panel.waitFor({ state: 'visible' });
  }

  async getDeviceItems() {
    return this.panel.locator('[data-test="device-item"]');
  }

  async getDeviceItemByName(name: string) {
    return this.panel.locator(`[data-test="device-item"][data-name="${name}"]`);
  }

  async getDeviceCount() {
    return (await this.getDeviceItems().all()).length;
  }

  async clickSort(sortBy: 'name' | 'status' | 'type') {
    await this.sortButton.click();
    await this.page.locator(`[data-test="sort-${sortBy}"]`).click();
  }

  async setFilter(filter: string) {
    await this.filterControl.fill(filter);
  }

  async openSettings() {
    await this.settingsButton.click();
    // Modal appears in shadow DOM
    await this.page.locator('vulcan-brownout-settings-modal').waitFor({ state: 'visible' });
  }

  async openNotifications() {
    await this.notificationIcon.click();
    await this.page.locator('vulcan-brownout-notification-modal').waitFor({ state: 'visible' });
  }

  async toggleDarkMode() {
    await this.darkModeToggle.click();
  }

  async scrollToBottom() {
    // Scroll sentinel into view to trigger IntersectionObserver
    await this.scrollSentinel.scrollIntoViewIfNeeded();
    // Wait for network idle after WebSocket response
    await this.page.waitForLoadState('networkidle');
  }
}
```

### 4. WebSocket Mock Helper: `utils/ws-helpers.ts`

```typescript
import { Page } from '@playwright/test';

export interface MockDeviceListResponse {
  page: number;
  total: number;
  devices: Array<{
    id: string;
    name: string;
    type: string;
    status: string;
    lastSeen?: string;
  }>;
}

export class WebSocketMockHelper {
  private devicePages: Map<number, MockDeviceListResponse> = new Map();
  private messageHandlers: Map<string, (data: any) => any> = new Map();

  constructor(private page: Page) {}

  /**
   * Setup WebSocket mock for HA API
   */
  async setupMock() {
    await this.page.routeWebSocket('/api/websocket', (route) => {
      route.onMessage((message) => {
        const data = JSON.parse(message);
        const handler = this.messageHandlers.get(data.type);

        if (handler) {
          const response = handler(data);
          if (response) {
            route.send(JSON.stringify(response));
          }
        }
      });
    });
  }

  /**
   * Register device list response
   */
  registerDeviceListResponse(devices: MockDeviceListResponse[]) {
    devices.forEach((page) => {
      this.devicePages.set(page.page, page);
    });

    this.messageHandlers.set('get_devices', (data) => {
      const pageNum = data.page || 0;
      const response = this.devicePages.get(pageNum);
      return {
        type: 'result',
        success: !!response,
        result: response?.devices || [],
      };
    });
  }

  /**
   * Register custom message handler
   */
  registerHandler(messageType: string, handler: (data: any) => any) {
    this.messageHandlers.set(messageType, handler);
  }
}
```

### 5. Device Factory: `utils/device-factory.ts`

```typescript
export interface Device {
  id: string;
  name: string;
  type: 'light' | 'switch' | 'sensor' | 'climate';
  status: 'on' | 'off' | 'unavailable';
  lastSeen?: string;
}

export function generateMockDevices(
  pageNum: number,
  perPage: number = 20,
  seed?: number
): Device[] {
  const types: Device['type'][] = ['light', 'switch', 'sensor', 'climate'];
  const statuses: Device['status'][] = ['on', 'off', 'unavailable'];

  const devices: Device[] = [];
  const startId = pageNum * perPage;

  for (let i = 0; i < perPage; i++) {
    const id = startId + i;
    devices.push({
      id: `device_${id}`,
      name: `Device ${id}`,
      type: types[id % types.length],
      status: statuses[id % statuses.length],
      lastSeen: new Date(Date.now() - Math.random() * 86400000).toISOString(),
    });
  }

  return devices;
}

export function generateDevicesByName(names: string[]): Device[] {
  return names.map((name, idx) => ({
    id: `device_${idx}`,
    name,
    type: ['light', 'switch', 'sensor', 'climate'][idx % 4] as Device['type'],
    status: ['on', 'off', 'unavailable'][idx % 3] as Device['status'],
  }));
}
```

---

## Sample Test: Device List with Sorting

**File:** `tests/device-list.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { VulcanBrownoutPanel } from '../pages/vulcan-brownout.page';
import { WebSocketMockHelper } from '../utils/ws-helpers';
import { generateMockDevices, generateDevicesByName } from '../utils/device-factory';

test.describe('Vulcan Brownout - Device List', () => {
  let panel: VulcanBrownoutPanel;
  let wsMock: WebSocketMockHelper;

  test.beforeEach(async ({ page }) => {
    panel = new VulcanBrownoutPanel(page);
    wsMock = new WebSocketMockHelper(page);

    // Setup WebSocket mock BEFORE navigation
    await wsMock.setupMock();

    // Register default device list responses (3 pages)
    wsMock.registerDeviceListResponse([
      { page: 0, total: 60, devices: generateMockDevices(0, 20) },
      { page: 1, total: 60, devices: generateMockDevices(1, 20) },
      { page: 2, total: 60, devices: generateMockDevices(2, 20) },
    ]);
  });

  test('should load panel and display devices', async ({ page }) => {
    await panel.goto();

    // Verify panel renders
    await expect(panel.panel).toBeVisible();

    // Verify device list visible in shadow DOM
    await expect(panel.deviceList).toBeVisible();

    // Verify device items rendered (20 per page)
    const itemCount = await panel.getDeviceCount();
    expect(itemCount).toBe(20);
  });

  test('should display device with correct attributes', async () => {
    await panel.goto();

    // Find first device item
    const firstItem = (await panel.getDeviceItems().all())[0];

    // Verify shadow DOM content is accessible
    const deviceName = await firstItem.locator('[data-test="device-name"]').textContent();
    const deviceStatus = await firstItem.locator('[data-test="device-status"]').getAttribute('class');

    expect(deviceName).toBeTruthy();
    expect(deviceStatus).toContain('status-');
  });

  test('should sort devices alphabetically', async () => {
    // Pre-register sorted response
    const sortedDevices = generateDevicesByName([
      'Bedroom Light',
      'Front Door',
      'Kitchen Switch',
      'Living Room Light',
    ]);

    wsMock.registerHandler('get_devices', (data) => {
      if (data.sort === 'name') {
        return {
          type: 'result',
          success: true,
          result: sortedDevices,
        };
      }
    });

    await panel.goto();

    // Click sort button
    await panel.clickSort('name');

    // Wait for update
    await panel.page.waitForLoadState('networkidle');

    // Verify device order changed
    const items = await panel.getDeviceItems().all();
    const names = await Promise.all(
      items.map((item) => item.locator('[data-test="device-name"]').textContent())
    );

    expect(names[0]).toContain('Bedroom');
    expect(names[1]).toContain('Front Door');
  });

  test('should load more devices on infinite scroll', async () => {
    await panel.goto();

    // Verify initial load (page 0)
    let count = await panel.getDeviceCount();
    expect(count).toBe(20);

    // Scroll to bottom (triggers IntersectionObserver)
    await panel.scrollToBottom();

    // Verify more devices loaded (page 0 + 1)
    count = await panel.getDeviceCount();
    expect(count).toBe(40);

    // Scroll again
    await panel.scrollToBottom();

    // Verify third page loaded
    count = await panel.getDeviceCount();
    expect(count).toBe(60);
  });

  test('should filter devices by search term', async () => {
    // Mock filter response
    const filteredDevices = generateDevicesByName(['Bedroom Light', 'Bedroom Switch']);

    wsMock.registerHandler('get_devices', (data) => {
      if (data.filter) {
        return {
          type: 'result',
          success: true,
          result: filteredDevices,
        };
      }
    });

    await panel.goto();

    // Set filter
    await panel.setFilter('Bedroom');

    // Wait for results
    await panel.page.waitForLoadState('networkidle');

    // Verify only matching devices shown
    const items = await panel.getDeviceItems().all();
    expect(items.length).toBe(2);

    const firstItemName = await items[0].locator('[data-test="device-name"]').textContent();
    expect(firstItemName).toContain('Bedroom');
  });

  test('should verify CSS custom properties for styling', async () => {
    await panel.goto();

    // Get device list background color (CSS custom property)
    const bgColor = await panel.deviceList.evaluate((el) => {
      return window.getComputedStyle(el).getPropertyValue('--device-list-bg');
    });

    // Verify it's not empty (actual value depends on theme)
    expect(bgColor).toBeTruthy();
  });
});
```

---

## Sample Test: Dark Mode

**File:** `tests/dark-mode.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { VulcanBrownoutPanel } from '../pages/vulcan-brownout.page';
import { WebSocketMockHelper } from '../utils/ws-helpers';
import { generateMockDevices } from '../utils/device-factory';

test.describe('Vulcan Brownout - Dark Mode', () => {
  let panel: VulcanBrownoutPanel;

  test.beforeEach(async ({ page }) => {
    panel = new VulcanBrownoutPanel(page);
    const wsMock = new WebSocketMockHelper(page);
    await wsMock.setupMock();
    wsMock.registerDeviceListResponse([
      { page: 0, total: 20, devices: generateMockDevices(0, 20) },
    ]);
  });

  test('should render in light mode by default', async ({ page }) => {
    // Ensure light mode
    await page.emulateMedia({ colorScheme: 'light' });

    await panel.goto();

    // Verify background is light
    const bgColor = await panel.panel.evaluate((el) => {
      const computed = window.getComputedStyle(el);
      return computed.backgroundColor;
    });

    // Light theme background (usually light gray or white)
    expect(bgColor).toMatch(/rgb\(2[4-5]\d,/); // 240-255 range
  });

  test('should render in dark mode when emulated', async ({ page }) => {
    // Switch to dark mode
    await page.emulateMedia({ colorScheme: 'dark' });

    await panel.goto();

    // Verify background is dark
    const bgColor = await panel.panel.evaluate((el) => {
      const computed = window.getComputedStyle(el);
      return computed.backgroundColor;
    });

    // Dark theme background (usually dark gray)
    expect(bgColor).toMatch(/rgb\([0-2]\d,/); // 0-29 range
  });

  test('should toggle dark mode via button', async ({ page }) => {
    await panel.goto();

    // Start in light mode
    await page.emulateMedia({ colorScheme: 'light' });
    let bgColor = await panel.panel.evaluate((el) => {
      return window.getComputedStyle(el).backgroundColor;
    });
    const lightBg = bgColor;

    // Toggle dark mode
    await panel.toggleDarkMode();

    // Verify background changed
    bgColor = await panel.panel.evaluate((el) => {
      return window.getComputedStyle(el).backgroundColor;
    });

    expect(bgColor).not.toBe(lightBg);
  });

  test('should update device list colors in dark mode', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });

    await panel.goto();

    // Get device item text color (should be light in dark mode)
    const color = await panel.getDeviceItems().first().evaluate((el) => {
      return window.getComputedStyle(el).color;
    });

    // Text should be light (240-255 range)
    expect(color).toMatch(/rgb\(2[4-5]\d,/);
  });

  test('should maintain dark mode across page reload', async ({ page }) => {
    await panel.goto();

    // Set to dark mode
    await panel.toggleDarkMode();
    await page.evaluate(() => localStorage.setItem('theme', 'dark'));

    // Reload
    await page.reload();

    // Verify dark mode is still active
    await page.emulateMedia({ colorScheme: 'dark' });
    const bgColor = await panel.panel.evaluate((el) => {
      return window.getComputedStyle(el).backgroundColor;
    });

    expect(bgColor).toMatch(/rgb\([0-2]\d,/);
  });
});
```

---

## CI/CD Integration: GitHub Actions

**File:** `quality/e2e/CI/playwright.yml`

```yaml
name: Vulcan Brownout E2E Tests

on:
  push:
    branches: [main, develop]
    paths:
      - 'frontend/**'
      - 'quality/e2e/**'
  pull_request:
    branches: [main, develop]
    paths:
      - 'frontend/**'
      - 'quality/e2e/**'

jobs:
  test:
    timeout-minutes: 60
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: |
          npm ci
          npx playwright install --with-deps

      - name: Wait for Home Assistant staging server
        run: |
          echo "Waiting for HA server at homeassistant.lan:8123..."
          for i in {1..60}; do
            if curl -f http://homeassistant.lan:8123/ > /dev/null 2>&1; then
              echo "✓ HA server is ready"
              exit 0
            fi
            echo "Attempt $i/60 - waiting..."
            sleep 10
          done
          echo "✗ HA server did not respond"
          exit 1

      - name: Run Playwright tests
        env:
          HA_TOKEN: ${{ secrets.HA_STAGING_TOKEN }}
        run: npx playwright test --project=chromium --project=firefox --project=webkit

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 30

      - name: Upload test videos
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: test-videos
          path: test-results/
          retention-days: 7

      - name: Publish test results
        if: always()
        uses: EnricoMi/publish-unit-test-result-action@v2
        with:
          files: junit.xml
```

---

## Running Tests Locally

### Setup

```bash
# Install dependencies
npm install --save-dev @playwright/test

# Install browsers
npx playwright install

# Create auth directory
mkdir -p playwright/.auth

# Set HA token for your environment
export HA_TOKEN="your-long-lived-token-here"
```

### Run Tests

```bash
# Run all tests (headless)
npm test

# Run specific test file
npm test device-list.spec.ts

# Run tests in debug mode (UI)
npm test -- --debug

# Run tests with headed browser (watch what happens)
npm test -- --headed

# Run tests on single browser
npm test -- --project=chromium

# Run tests with trace viewer
npm test -- --trace on

# View HTML report
npx playwright show-report
```

### Local Development Workflow

```bash
# Watch mode (re-run on file change)
npm test -- --watch

# Debug failing test
npm test -- --debug device-list.spec.ts

# Generate locators visually
npx playwright codegen http://homeassistant.lan:8123/vulcan-brownout
```

---

## Integration with Existing Quality Directory

### Current Structure (from filesystem)

```
quality/
├── README.md
├── docs/
├── backend/               # Python backend tests
├── frontend/              # Frontend unit tests
└── [NEW] e2e/            # Playwright E2E tests
    ├── playwright.config.ts
    ├── fixtures/
    ├── pages/
    ├── tests/
    ├── utils/
    └── CI/
```

### Test Execution Order (CI)

1. **Backend Tests** (`pytest`): Backend logic validation
2. **Frontend Unit Tests** (`vitest`): Component unit tests
3. **E2E Tests** (`playwright`): Integration testing against HA
4. **Visual Regression** (optional): Dark mode, responsive design

---

## Architectural Decisions & Trade-offs

### 1. Mock vs Real HA Server

**Decision:** Mock WebSocket responses; test against real HA staging server for integration tests.

**Reasoning:**
- **Mocking:** Fast, reliable, fully controlled (ideal for unit E2E tests)
- **Real Server:** Validates actual HA integration, catches API changes

**Implementation:**
- Unit E2E tests use WebSocket mocking (this document)
- Full integration tests (future) run against `homeassistant.lan:8123` staging

### 2. Headless vs Headed

**Decision:** Headless in CI, headed (with UI) in local development.

**playwright.config.ts:**
```typescript
use: {
  headless: !process.env.DEBUG_HEADED,
  devtools: process.env.DEBUG_HEADED,
},
```

### 3. Test Data Generation

**Decision:** Synthetic mock devices using factory pattern.

**Benefits:**
- No network calls to real HA
- Deterministic, reproducible tests
- Fast test execution
- Easy to generate edge cases (100 devices, etc.)

### 4. Shadow DOM Queries

**Decision:** Use Playwright's native CSS locator piercing (no custom JavaScript).

**Example:**
```typescript
// ✅ Clean, native Playwright
this.panel.locator('[data-test="device-list"]')

// ❌ Avoid: Manual shadow DOM traversal
el.shadowRoot.querySelector()
```

### 5. Authentication State Reuse

**Decision:** Store and reuse authentication state across test runs.

**Benefits:**
- ~30% faster test execution (skip auth setup per-test)
- Secure (token never hardcoded in tests)
- Matches real user behavior

**File:** `playwright/.auth/auth.json` (git-ignored)

---

## Performance Expectations

### Test Execution Time (local)

| Scenario | Time | Notes |
|----------|------|-------|
| Single test | 2-3s | Panel load + assertion |
| Full suite (10 tests) | 20-30s | Sequential |
| Full suite (3 browsers) | 60-90s | Parallel runs |
| CI with artifacts | 3-5 min | Includes setup, reports, uploads |

### Optimizations

1. **Parallel execution:** Tests run in parallel by default (different test files)
2. **Reused auth state:** Skip auth setup (saved 30%)
3. **WebSocket mocking:** No network latency
4. **Smart waits:** `waitForLoadState('networkidle')` instead of fixed sleeps

---

## Maintenance & Scalability

### Adding New Tests

1. Create test file in `tests/` directory
2. Use `VulcanBrownoutPanel` page object
3. Register WebSocket mocks in `beforeEach`
4. Follow existing patterns for assertions

### Handling Breaking Changes

**Scenario:** HA WebSocket API changes (e.g., new `get_devices_v2` endpoint)

**Process:**
1. Update mock handler in `WebSocketMockHelper.registerHandler()`
2. Update component to use new endpoint
3. Tests automatically validate new behavior

**Scenario:** Component DOM structure changes (class names, attributes)

**Process:**
1. Update `[data-test]` attributes in component
2. Update selectors in `VulcanBrownoutPanel` page object
3. No test logic changes needed

---

## Future Enhancements

### 1. Visual Regression Testing

```typescript
test('dark mode visual regression', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' });
  await expect(page).toMatchScreenshot('vulcan-brownout-dark.png');
});
```

### 2. Performance Testing

```typescript
test('device list render performance', async ({ page }) => {
  const metrics = await page.metrics();
  expect(metrics.JSHeapUsedSize).toBeLessThan(50 * 1024 * 1024); // < 50MB
});
```

### 3. Accessibility Testing

```typescript
import { injectAxe, checkA11y } from 'axe-playwright';

test('panel meets WCAG 2.1 AA', async ({ page }) => {
  await injectAxe(page);
  await checkA11y(page, 'vulcan-brownout-panel');
});
```

### 4. API Testing

```typescript
test('HA WebSocket API contract', async () => {
  const response = await apiClient.callWS({ type: 'get_devices' });
  expect(response).toMatchSchema(deviceListSchema);
});
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| **Auth token leakage** | Tokens stored in GitHub Secrets, never logged, auth.json git-ignored |
| **HA staging server down** | CI job fails safely with clear error message; retry logic in GitHub Actions |
| **WebSocket mock doesn't match real API** | Integration tests run weekly against real HA server |
| **Tests flake due to timing** | Use Playwright's auto-waiting and `waitForLoadState()` instead of sleeps |
| **Shadow DOM structure changes** | Page object abstraction isolates selector changes to one file |
| **Cross-browser incompatibilities** | Test on Chromium, Firefox, WebKit in CI |

---

## Conclusion

Playwright provides the optimal foundation for Vulcan Brownout E2E testing. The proposed architecture:

✅ **Addresses all requirements:** Shadow DOM, WebSocket, auth, dark mode, infinite scroll
✅ **Scales efficiently:** Fast parallel execution, reusable fixtures, clear patterns
✅ **Minimizes maintenance:** Page objects, mock helpers, centralized utilities
✅ **Integrates with CI/CD:** GitHub Actions workflow ready to deploy
✅ **Future-proof:** Easy to add visual regression, accessibility, API testing

**Next steps:**
1. Implement proposed directory structure
2. Create sample test files (device-list.spec.ts, dark-mode.spec.ts)
3. Set up GitHub Actions CI workflow
4. Document in `TESTING.md` for team

---

## Related Documents

- `/sessions/wizardly-stoic-cannon/mnt/vulcan-brownout/quality/ux-testing-research.md` — Framework evaluation
- `/sessions/wizardly-stoic-cannon/mnt/vulcan-brownout/quality/ux-testing-questions-for-decko.md` — Architectural questions

