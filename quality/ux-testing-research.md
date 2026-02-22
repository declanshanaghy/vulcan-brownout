# Vulcan Brownout UI/UX Testing Framework Research
**Date:** February 22, 2026
**Researcher:** Loki (QA Engineer)
**Target Application:** Vulcan Brownout (Lit Element web component at http://homeassistant.lan:8123/vulcan-brownout)

---

## Executive Summary

This document evaluates six leading UI/UX interaction testing frameworks for Vulcan Brownout, with special focus on Shadow DOM support (critical for Lit components), WebSocket interception, token-based authentication, and developer experience. **Playwright emerges as the top recommendation** for its superior Shadow DOM handling, built-in WebSocket mocking, cross-browser capabilities, and modern developer experience. However, WebdriverIO offers a strong alternative for teams prioritizing W3C WebDriver standards and Lit-specific tooling.

---

## Table of Contents

1. [Framework Comparison Matrix](#framework-comparison-matrix)
2. [Detailed Framework Evaluations](#detailed-framework-evaluations)
3. [Shadow DOM Deep Dive](#shadow-dom-deep-dive)
4. [WebSocket Testing Patterns](#websocket-testing-patterns)
5. [Authentication Strategies for Home Assistant](#authentication-strategies-for-home-assistant)
6. [Dark Mode & CSS Custom Properties Testing](#dark-mode--css-custom-properties-testing)
7. [Infinite Scroll & IntersectionObserver Testing](#infinite-scroll--intersectionobserver-testing)
8. [Key Findings & Tradeoffs](#key-findings--tradeoffs)

---

## Framework Comparison Matrix

| Criterion | Playwright | Cypress | WebdriverIO | Puppeteer | Testing Library | Vitest |
|-----------|-----------|---------|-------------|-----------|-----------------|--------|
| **Shadow DOM Support** | ⭐⭐⭐⭐⭐ Native piercing | ⭐⭐⭐⭐ .shadow() method | ⭐⭐⭐⭐⭐ shadow$() | ⭐⭐ JS only | ⭐⭐ Via extension | ⭐⭐⭐ Browser mode |
| **WebSocket Mocking** | ⭐⭐⭐⭐⭐ Native v1.48+ | ⭐⭐⭐ Via plugin | ⭐⭐⭐ Via CDP | ⭐⭐⭐ Via CDP | ❌ Not supported | ⭐⭐⭐⭐ Browser mode |
| **Token-Based Auth** | ⭐⭐⭐⭐⭐ Native headers | ⭐⭐⭐⭐ Via env | ⭐⭐⭐⭐ Native support | ⭐⭐⭐ Via headers | ⭐⭐ Manual | ⭐⭐⭐ Browser |
| **Cross-Browser** | ⭐⭐⭐⭐⭐ Chromium/FF/WebKit | ⭐⭐⭐ Chrome/FF | ⭐⭐⭐⭐ Multi-protocol | ⭐ Chrome only | N/A | ⭐⭐⭐⭐ Browser-agnostic |
| **Dark Mode Testing** | ⭐⭐⭐⭐⭐ emulateMedia() | ⭐⭐⭐ Plugin-based | ⭐⭐⭐ Via CSS | ⭐⭐⭐ Via emulation | ⭐⭐⭐ CSS-based | ⭐⭐⭐⭐ Real browser |
| **Infinite Scroll** | ⭐⭐⭐⭐ Auto-waiting | ⭐⭐⭐⭐ Stable | ⭐⭐⭐⭐ Via scrolling API | ⭐⭐⭐ Manual scroll | ⭐⭐⭐ User-centric | ⭐⭐⭐⭐ Real viewport |
| **Developer Experience** | ⭐⭐⭐⭐⭐ Best-in-class | ⭐⭐⭐⭐⭐ Time-travel debug | ⭐⭐⭐ Good | ⭐⭐⭐ Straightforward | ⭐⭐⭐⭐ User-focused | ⭐⭐⭐ Modern |
| **Setup Complexity** | ⭐⭐⭐⭐⭐ Easy | ⭐⭐⭐⭐⭐ Easy | ⭐⭐⭐ Moderate | ⭐⭐⭐⭐ Easy | ⭐⭐⭐⭐⭐ Easy | ⭐⭐⭐⭐ Easy |
| **Performance** | ⭐⭐⭐⭐⭐ Fastest | ⭐⭐⭐ Good | ⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Unit-test speeds | ⭐⭐⭐⭐⭐ Fastest |
| **Community & Maintenance** | ⭐⭐⭐⭐⭐ Microsoft-backed | ⭐⭐⭐⭐⭐ Very active | ⭐⭐⭐⭐ Active | ⭐⭐⭐⭐⭐ Google-backed | ⭐⭐⭐⭐⭐ React Testing | ⭐⭐⭐⭐⭐ Very active |
| **Node.js Native** | ⭐⭐⭐⭐⭐ Yes | ⭐⭐⭐⭐⭐ Yes | ⭐⭐⭐⭐⭐ Yes | ⭐⭐⭐⭐⭐ Yes | ⭐⭐⭐⭐⭐ Yes | ⭐⭐⭐⭐⭐ Yes |
| **CI/CD Integration** | ⭐⭐⭐⭐⭐ Native | ⭐⭐⭐⭐ Good | ⭐⭐⭐⭐ Good | ⭐⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Easy | ⭐⭐⭐⭐⭐ Simple |

---

## Detailed Framework Evaluations

### 1. Playwright (Microsoft) — **TOP RECOMMENDATION**

**Status:** Production-ready, v1.48+ with WebSocket support
**Language:** Node.js (TypeScript/JavaScript)
**WebSocket Support:** Native `page.routeWebSocket()` since v1.48

#### Strengths

- **Shadow DOM:** Locators naturally pierce Shadow DOM by default. CSS and text locators work cross-browser without explicit JavaScript code. No configuration needed.
  - Reference: [Shadow DOM Testing That Doesn't Flake (Using Playwright)](https://medium.com/@erik.amaral/shadow-dom-testing-that-doesnt-flake-using-playwright-1c9313d086d3)
  - Reference: [Playwright's Playbook: Conquering ShadowDOM Elements with Ease](https://medium.com/helpshift-engineering/playwrights-playbook-conquering-shadowdom-elements-with-ease-35b65bfb8008)

- **WebSocket Mocking:** Native support via `page.routeWebSocket()` and `browserContext.routeWebSocket()`. Can mock or inspect messages. No need for external libraries.
  - Reference: [Playwright WebSocketRoute API](https://playwright.dev/docs/api/class-websocketroute)

- **Authentication:** Excellent token-based auth support via extraHTTPHeaders. Can set Authorization headers globally across contexts.
  - Reference: [Playwright Authentication Guide](https://playwright.dev/docs/auth)

- **Cross-Browser:** Supports Chromium, Firefox, WebKit (Safari) with a single API.

- **Dark Mode:** Built-in `emulateMedia({ colorScheme: 'dark' })` for testing both light/dark modes. CSS custom properties fully supported.
  - Reference: [Mastering Dark & Light Mode Testing with Playwright](https://runebook.dev/en/docs/playwright/api/class-testoptions/test-options-color-scheme)

- **Developer Experience:** Auto-waiting, smart locators, built-in debugging (trace viewer, inspector), excellent CI/CD integration. Modern async/await syntax.

- **Performance:** Fastest E2E framework (20-30M NPM downloads/week as of 2026). Parallel test execution native to framework.

#### Weaknesses

- XPath does not pierce Shadow DOM (use CSS or text locators instead)
- Closed Shadow DOM roots not supported (but Lit uses open roots by default)

#### Fit for Vulcan Brownout

✅ **EXCELLENT**
- Lit Element components work seamlessly
- WebSocket mocking handles HA API calls perfectly
- Dark mode testing is straightforward
- Token-based auth matches HA's architecture
- IntersectionObserver testing works with native waiting

---

### 2. Cypress (Cypress Inc.)

**Status:** Production-ready, v5.2+
**Language:** Node.js (JavaScript/TypeScript)
**WebSocket Support:** Via plugin ecosystem

#### Strengths

- **Shadow DOM:** Built-in `.shadow()` method since v5.2. Works with open Shadow DOM. Records actions/assertions in Cypress Studio.
  - Reference: [Interact and Assert on Shadow DOM in Cypress Studio](https://www.cypress.io/blog/interact-and-assert-on-shadow-dom-in-cypress-studio)

- **Developer Experience:** Unmatched. Time-travel debugging, visual command log, automatic screenshots on failure, instant feedback.

- **Stability:** Very stable for most modern web applications.

#### Weaknesses

- **Shadow DOM Limitation:** Cypress Studio does not support closed Shadow DOM (Lit uses open, so this is acceptable)
- **WebSocket:** No native mocking. Requires plugin or manual workaround (DevTools Protocol). Not as clean as Playwright's approach.
- **Parallelization:** Native support added, but optimal parallelization requires Cypress Cloud (paid service) or external tooling
- **Single browser focus:** Primary support for Chrome-family browsers; Firefox and Safari support is experimental
- **Browser coverage:** Cannot test Safari (WebKit) without workarounds

#### Fit for Vulcan Brownout

✅ **VERY GOOD**
- Shadow DOM support is solid for open roots (Lit's default)
- Excellent for TDD/debugging during development
- WebSocket testing requires workarounds; not ideal for HA WebSocket-heavy testing
- Great for smaller, focused test suites but may hit parallelization bottlenecks at scale

---

### 3. WebdriverIO

**Status:** Production-ready, v8+
**Language:** Node.js (JavaScript/TypeScript)
**WebSocket Support:** Via Chrome DevTools Protocol

#### Strengths

- **Lit Component Testing:** Official documentation specifically addresses Lit web components. Provides dedicated Lit preset for component testing.
  - Reference: [Lit | WebdriverIO](https://webdriver.io/docs/component-testing/lit/)

- **Shadow DOM:** Built-in `shadow$()` and `shadow$$()` methods. Robust support for querying nested shadow roots.
  - Reference: [WebdriverIO shadow$ API](https://webdriver.io/docs/api/element/shadow$/)

- **W3C WebDriver Standard:** Uses W3C WebDriver Protocol instead of proprietary protocols. More portable and standardized.

- **Mobile Testing:** Seamless integration with Appium for native mobile testing if needed in future.

- **Dark Mode:** CSS-based color scheme testing supported.

#### Weaknesses

- **WebSocket Mocking:** Requires Chrome DevTools Protocol setup; not as clean as Playwright's native routing
- **Learning Curve:** More complex setup and API than Playwright for teams new to WebDriver
- **Community:** Smaller community compared to Playwright or Cypress
- **Performance:** Generally good but not as optimized as Playwright for CI/CD parallelization
- **Documentation:** Less comprehensive than Playwright's official guides

#### Fit for Vulcan Brownout

✅ **EXCELLENT ALTERNATIVE**
- Lit-specific tooling and documentation
- Shadow DOM support is equally strong (arguably clearer with `shadow$()` method)
- W3C WebDriver standard provides future-proofing
- WebSocket handling requires more boilerplate than Playwright
- Best if team already familiar with WebDriver

---

### 4. Puppeteer (Google)

**Status:** Production-ready, v20+
**Language:** Node.js (JavaScript/TypeScript)
**WebSocket Support:** Via Chrome DevTools Protocol (limited)

#### Strengths

- **Official Chrome Tool:** Developed by Google Chrome team. Direct CDP access.
- **Performance:** Fast for Chrome-based automation.
- **Simplicity:** Straightforward API for basic automation.

#### Weaknesses

- **Shadow DOM:** No native piercing. Requires JavaScript execution for each shadow root traversal. Cumbersome for complex components.
  ```javascript
  // Ugly approach required
  const element = await page.evaluateHandle(() => {
    return document.querySelector('vulcan-brownout-panel').shadowRoot.querySelector('.device-list');
  });
  ```

- **WebSocket Limitation:** Known issue (#3547). Request interception doesn't capture WebSocket traffic. Not suitable for HA WebSocket-heavy testing.
  - Reference: [Puppeteer GitHub Issue #3547](https://github.com/puppeteer/puppeteer/issues/3547)

- **Single Browser:** Chrome/Chromium only. No Firefox or Safari support.

- **Not E2E-focused:** Designed for web scraping/automation, not E2E testing (lacks fixtures, parallelization, reporting).

#### Fit for Vulcan Brownout

❌ **POOR**
- Shadow DOM requires manual JavaScript traversal
- WebSocket interception not supported (deal-breaker for HA testing)
- Single browser limits cross-browser testing
- Better suited for scraping than E2E testing

---

### 5. Testing Library (@testing-library)

**Status:** Production-ready for unit/component testing
**Language:** Node.js (JavaScript/TypeScript)
**WebSocket Support:** Not applicable (unit testing focus)

#### Strengths

- **User-Centric Queries:** Encourages testing like users interact with the app (by role, label, etc.)
- **Lightweight:** Minimal setup for unit testing
- **Wide Adoption:** Popular in React/Vue ecosystems

#### Weaknesses

- **Shadow DOM:** Core library does NOT support Shadow DOM querying. Community has created extensions (shadow-dom-testing-library) but these are third-party.
  - Reference: [Feature request: Shadow DOM support · Issue #413](https://github.com/testing-library/dom-testing-library/issues/413)

- **E2E Testing:** Not designed for E2E scenarios. Lacks capabilities for:
  - WebSocket interception
  - Multi-page navigation
  - Authentication flows
  - Real browser testing (primarily JSDOM/Happy-DOM)

- **Infinite Scroll:** Difficult to test with IntersectionObserver patterns without browser context

#### Fit for Vulcan Brownout

❌ **NOT SUITABLE**
- Designed for unit testing, not E2E testing
- Shadow DOM support is a limitation without third-party extensions
- No WebSocket support
- Better used alongside an E2E framework (e.g., Testing Library + Playwright) for component unit tests

---

### 6. Vitest with Browser Mode

**Status:** Browser mode stabilized in v4.0 (Feb 2025)
**Language:** Node.js (JavaScript/TypeScript)
**WebSocket Support:** Native in browser mode (real browser)

#### Strengths

- **Real Browser Testing:** v4.0 stabilized browser mode runs tests in actual Playwright/WebDriverIO instances (not JSDOM)
- **Web APIs:** Full support for all browser APIs (fetch, WebSockets, IntersectionObserver, localStorage, etc.)
- **Fast Iteration:** Best for unit/component testing with real browser context
- **Visual Testing:** Built-in visual regression testing with `toMatchScreenshot()` (useful for dark mode testing)
  - Reference: [Vitest 4.0 Release Notes](https://vitest.dev/guide/browser/)

- **Playwright Integration:** Uses Playwright under the hood for browser control

#### Weaknesses

- **Shadow DOM Printing:** Vitest's snapshot testing and console output don't properly display Shadow DOM contents (Issue #7688)
  - Reference: [Unable to Access Shadow DOM Text Value in Vitest](https://github.com/vitest-dev/vitest/issues/7688)

- **Test Type Mismatch:** Primarily for component/unit testing, not full E2E scenarios
- **Learning Curve:** Different testing philosophy from traditional E2E frameworks

#### Fit for Vulcan Brownout

⚠️ **COMPLEMENTARY TOOL**
- Best used for Lit component unit tests (not full-stack E2E)
- Can supplement Playwright E2E tests with unit-level testing
- Real browser context is excellent for Shadow DOM component testing
- Not recommended as primary E2E framework (doesn't test navigation, multi-page flows)

---

## Shadow DOM Deep Dive

### The Challenge

Vulcan Brownout is built as a Lit Element web component (`vulcan-brownout-panel`) with Shadow DOM encapsulation. Traditional DOM queries cannot penetrate Shadow DOM boundaries:

```javascript
// ❌ Won't work
document.querySelector('.device-list')  // Hidden inside shadowRoot

// ✅ Must pierce the shadow root
document.querySelector('vulcan-brownout-panel').shadowRoot.querySelector('.device-list')
```

### Framework Capabilities Comparison

#### **Playwright: Native Piercing** ⭐⭐⭐⭐⭐

```typescript
// Just works. No special syntax needed.
await page.locator('vulcan-brownout-panel .device-list').click();
await expect(page.locator('vulcan-brownout-panel .device-item')).toHaveCount(10);
```

- CSS locators pierce by default
- Text locators pierce by default
- No configuration required
- Works cross-browser (Chromium, Firefox, WebKit)

#### **Cypress: .shadow() Method** ⭐⭐⭐⭐

```typescript
// Uses explicit .shadow() command
cy.get('vulcan-brownout-panel')
  .shadow()
  .find('.device-list')
  .should('exist');
```

- Clean, chainable syntax
- Works for open Shadow DOM (Lit's default)
- Not supported in Cypress Studio for closed roots
- Firefox/Safari support varies

#### **WebdriverIO: shadow$() & shadow$$()**  ⭐⭐⭐⭐⭐

```typescript
// Dedicated shadow element queries
const list = await $('vulcan-brownout-panel').shadow$('.device-list');
await expect(list).toBeDisplayed();
```

- Official support for Lit components
- Query-by-selector approach similar to light DOM
- Robust nested shadow DOM support
- W3C WebDriver standard

#### **Puppeteer: Manual JavaScript** ⭐⭐

```typescript
// Requires JavaScript execution for each operation
const count = await page.evaluate(() => {
  return document.querySelector('vulcan-brownout-panel')
    .shadowRoot.querySelectorAll('.device-item').length;
});
```

- Cumbersome for complex selectors
- Requires evaluate() wrapper for each shadow traversal
- No waiting/retry logic built-in
- Error-prone for nested shadow roots

#### **Testing Library: Extensions Needed** ⭐⭐

```typescript
// Must use shadow-dom-testing-library extension
import { render } from '@testing-library/dom';
import { getByShadowRole } from 'shadow-dom-testing-library';

const { container } = render(html`<vulcan-brownout-panel></vulcan-brownout-panel>`);
const item = getByShadowRole(container, 'button', { name: /sort/i });
```

- Core library lacks Shadow DOM support
- Third-party extension required
- Adds dependency for E2E testing scenario

#### **Vitest Browser Mode: Real Browser, Limited Output** ⭐⭐⭐

```typescript
// Shadow DOM works in real browser context
const element = screen.getByRole('button', { name: /sort/i });
await userEvent.click(element);
```

- Works in real browser (Playwright/WebDriverIO backed)
- Shadow DOM traversal works fine
- Issue: Snapshots don't properly capture shadow content (GitHub #7688)
- Best for unit tests, not full E2E

### Recommendation for Vulcan Brownout

**Playwright** and **WebdriverIO** provide equally excellent Shadow DOM support for Lit components. Playwright's native piercing is simpler; WebdriverIO's `shadow$()` is more explicit. Both are superior to alternatives.

---

## WebSocket Testing Patterns

### Home Assistant WebSocket Context

Vulcan Brownout communicates with HA via WebSocket API using `this.hass.callWS()`. The HA frontend provides a `hass` object with WebSocket utilities. Tests must:

1. Intercept/mock WebSocket messages (e.g., device list queries)
2. Respond to test scenarios (success, error, timeout)
3. Verify the component handles async updates

### Framework Approaches

#### **Playwright: Native WebSocket Routing** ⭐⭐⭐⭐⭐ (BEST)

```typescript
// Setup WebSocket mock (v1.48+)
await page.routeWebSocket('/api/websocket', (route) => {
  const wsRoute = route;
  wsRoute.onMessage((message) => {
    const data = JSON.parse(message);

    if (data.type === 'get_devices') {
      wsRoute.send(JSON.stringify({
        type: 'result',
        success: true,
        result: { devices: [/* mocked devices */] }
      }));
    }
  });
});

// Test can now control WebSocket responses
await page.goto('http://homeassistant.lan:8123/vulcan-brownout');
await expect(page.locator('.device-list')).toContainText('Device 1');
```

- Native since v1.48
- Clean route handler pattern
- Can mock or pass through (`wsRoute.connectToServer()`)
- Works cross-browser

#### **Cypress: Plugin-Based Approach** ⭐⭐⭐

```typescript
// Requires cypress-websocket-mock or similar plugin
cy.mockWebsocket({
  url: '/api/websocket',
  onMessage: (message) => {
    if (message.type === 'get_devices') {
      return { type: 'result', devices: [] };
    }
  }
});
```

- Not built-in; adds external dependency
- More complex setup than Playwright
- Less documentation in ecosystem

#### **WebdriverIO: Chrome DevTools Protocol** ⭐⭐⭐

```typescript
// Via CDP (less elegant than Playwright)
const { network } = await browser.createCDPSession();
await network.enable();
await network.onWebSocketCreated(({ requestId, url }) => {
  // Handle WebSocket
});
```

- Works but more verbose
- Requires CDP knowledge
- Less user-friendly than Playwright's abstraction

#### **Puppeteer: Limited Support** ⭐⭐

- WebSocket interception not supported by request interception API
- Must use CDP events directly
- Cumbersome for test scenarios
- Known limitation: [Issue #3547](https://github.com/puppeteer/puppeteer/issues/3547)

### Testing Infinite Scroll with WebSocket

Vulcan Brownout has infinite scroll + device list. Pattern:

```typescript
// Playwright example: test infinite scroll + WebSocket
await page.routeWebSocket('/api/websocket', (route) => {
  let pageNum = 0;
  route.onMessage((msg) => {
    const data = JSON.parse(msg);
    if (data.type === 'get_devices') {
      const devices = generateMockDevices(pageNum++, 20);
      route.send(JSON.stringify({
        type: 'result',
        result: devices
      }));
    }
  });
});

await page.goto('http://homeassistant.lan:8123/vulcan-brownout');
await expect(page.locator('[data-test="device-item"]')).toHaveCount(20);

// Scroll to bottom, trigger IntersectionObserver, loads next page
await page.locator('[data-test="scroll-sentinel"]').scrollIntoViewIfNeeded();
await expect(page.locator('[data-test="device-item"]')).toHaveCount(40);
```

### Recommendation

**Playwright** is the clear winner for WebSocket testing. Native `routeWebSocket()` is purpose-built for this scenario and far simpler than alternatives.

---

## Authentication Strategies for Home Assistant

### Home Assistant Token-Based Auth

HA uses long-lived tokens. Vulcan Brownout requires:
1. Token in localStorage/sessionStorage (set by HA frontend)
2. Token in WebSocket authentication handshake
3. Token in HTTP Authorization header (if REST API calls made)

### Framework Strategies

#### **Playwright: Best Approach** ⭐⭐⭐⭐⭐

Option A: Store authentication state in browser storage

```typescript
// playwright.config.ts
export default defineConfig({
  use: {
    // Reuse authenticated state across tests
    storageState: 'auth.json',
  },
});

// auth.setup.ts - runs once before test suite
test('authenticate', async ({ page }) => {
  // Navigate to HA login
  await page.goto('http://homeassistant.lan:8123/');

  // HA frontend sets token to localStorage automatically
  // (if using HA's native auth flow)

  // Or manually inject token:
  await page.evaluate(() => {
    localStorage.setItem('hassRefreshToken', 'YOUR_TOKEN_HERE');
    localStorage.setItem('hassAccessToken', 'YOUR_TOKEN_HERE');
  });

  // Save state
  await page.context().storageState({ path: 'auth.json' });
});

// vulcan-brownout.spec.ts - uses saved state
test('load device list', async ({ page }) => {
  // Browser context already authenticated via auth.json
  await page.goto('http://homeassistant.lan:8123/vulcan-brownout');
  await expect(page.locator('.device-list')).toBeVisible();
});
```

Option B: Header-based for WebSocket/REST

```typescript
// For direct API calls (if testing REST endpoints)
await page.setExtraHTTPHeaders({
  'Authorization': `Bearer ${process.env.HA_TOKEN}`
});
```

#### **Cypress: Environment Variables** ⭐⭐⭐⭐

```typescript
// cypress.env.json
{
  "HA_TOKEN": "eyJhbGc...",
  "HA_BASE_URL": "http://homeassistant.lan:8123"
}

// cypress/e2e/vulcan.cy.ts
beforeEach(() => {
  // Set token in localStorage before each test
  cy.window().then(win => {
    win.localStorage.setItem('hassRefreshToken', Cypress.env('HA_TOKEN'));
    win.localStorage.setItem('hassAccessToken', Cypress.env('HA_TOKEN'));
  });
});
```

#### **WebdriverIO: Session State** ⭐⭐⭐⭐

```typescript
// wdio.conf.ts
export const config = {
  beforeSession: (caps, specs) => {
    // Set auth state before browser session
  },
};

// test file
it('should load panel with auth', async () => {
  await browser.setWindowsLocalStorage({
    hassAccessToken: process.env.HA_TOKEN,
  });
});
```

### Security Considerations

⚠️ **DO NOT commit tokens to git.** Strategies:

1. **Environment Variables:** Load from `.env.local` (git-ignored)
   ```bash
   export HA_TOKEN="eyJhbGc..."
   ```

2. **GitHub Actions Secrets:** For CI/CD
   ```yaml
   - name: Run tests
     env:
       HA_TOKEN: ${{ secrets.HA_STAGING_TOKEN }}
     run: npm test
   ```

3. **Stored Auth State:** Save to file (git-ignored), reuse across test runs
   ```json
   // playwright/.auth/auth.json (in .gitignore)
   {
     "cookies": [...],
     "localStorage": [{ "name": "hassAccessToken", "value": "..." }]
   }
   ```

### Recommendation

**Playwright's `storageState` approach** is the most secure and maintainable:
- Reuses auth across test suite runs (faster tests)
- Auth file is easy to regenerate
- Clear separation between auth setup and test logic
- Works across browser contexts

---

## Dark Mode & CSS Custom Properties Testing

### Vulcan Brownout Requirements

The panel supports dark mode via CSS custom properties (e.g., `--primary-color`, `--bg-color`). Tests must verify:
1. Light mode renders correctly
2. Dark mode renders correctly
3. CSS custom property overrides work
4. Contrast ratios remain accessible

### Framework Capabilities

#### **Playwright: Built-in emulation** ⭐⭐⭐⭐⭐

```typescript
// Test dark mode
test('dark mode', async ({ page }) => {
  // Option A: Set at test level
  test.use({ colorScheme: 'dark' });

  await page.goto('http://homeassistant.lan:8123/vulcan-brownout');
  await expect(page.locator('vulcan-brownout-panel')).toHaveCSS(
    '--bg-color',
    'rgb(30, 30, 30)' // dark mode value
  );
});

// Option B: Change mid-test
await page.emulateMedia({ colorScheme: 'dark' });
await expect(page.locator('.device-list')).toHaveCSS('background-color', 'rgb(20, 20, 20)');

// Option C: Check computed CSS
const bgColor = await page.locator('vulcan-brownout-panel').evaluate(
  el => window.getComputedStyle(el).getPropertyValue('--bg-color')
);
```

- Native `emulateMedia()` for color scheme
- `toHaveCSS()` assertion for property validation
- Works across all browsers
- Full support for CSS custom properties

#### **Cypress: Plugin or workaround** ⭐⭐⭐

```typescript
// Requires plugin or manual approach
cy.get('vulcan-brownout-panel').should('have.css', 'background-color')
  .and('equal', 'rgb(20, 20, 20)');

// Or via invoke to get computed style
cy.get('vulcan-brownout-panel').invoke('css', 'background-color')
  .should('equal', 'rgb(20, 20, 20)');
```

- Less ergonomic than Playwright
- Plugin-based dark mode emulation less straightforward
- Works but requires more manual assertions

#### **WebdriverIO: CSS validation** ⭐⭐⭐

```typescript
const element = $('vulcan-brownout-panel');
const bgColor = await element.getCSSProperty('background-color');
expect(bgColor.value).toEqual('rgb(20, 20, 20)');
```

- Functional but more verbose
- CSS custom properties require `getComputedStyle()` evaluation
- No built-in color scheme emulation

#### **Testing Library: CSS-based** ⭐⭐⭐

```typescript
// Via getComputedStyle
const element = screen.getByRole('region', { name: /vulcan/i });
const bgColor = window.getComputedStyle(element).backgroundColor;
expect(bgColor).toBe('rgb(20, 20, 20)');
```

- Works for unit tests
- No built-in dark mode emulation
- Manual CSS validation

### Visual Regression Testing for Dark Mode

**Vitest Browser Mode** with `toMatchScreenshot()`:

```typescript
test('dark mode visual regression', async () => {
  await page.emulateMedia({ colorScheme: 'dark' });
  await expect(page).toMatchScreenshot('vulcan-brownout-dark.png');
});
```

Useful for ensuring dark mode styling is correct across components.

### Recommendation

**Playwright's `emulateMedia()` and `toHaveCSS()`** provide the cleanest dark mode testing. Pair with visual regression testing (Vitest or Playwright) for comprehensive coverage.

---

## Infinite Scroll & IntersectionObserver Testing

### Vulcan Brownout Pattern

The device list uses IntersectionObserver to detect when the user scrolls near the bottom, triggering a WebSocket call for the next page:

```typescript
// Pseudo-code: how Lit component detects scroll
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      this.hass.callWS({ type: 'get_devices', page: nextPage++ });
    }
  });
});
observer.observe(sentinelElement);
```

### Testing Approach

#### **Playwright: Scroll + IntersectionObserver** ⭐⭐⭐⭐

```typescript
test('infinite scroll loads more devices', async ({ page }) => {
  // Mock WebSocket to return paginated results
  await page.routeWebSocket('/api/websocket', (route) => {
    let page = 0;
    route.onMessage((msg) => {
      const data = JSON.parse(msg);
      if (data.type === 'get_devices') {
        const devices = generateDevices(page++, 20);
        route.send(JSON.stringify({ type: 'result', result: devices }));
      }
    });
  });

  await page.goto('http://homeassistant.lan:8123/vulcan-brownout');

  // Verify initial load
  const items = page.locator('[data-test="device-item"]');
  await expect(items).toHaveCount(20);

  // Scroll to bottom (triggers IntersectionObserver)
  await page.locator('[data-test="scroll-sentinel"]').scrollIntoViewIfNeeded();

  // Wait for next page to load
  await page.waitForLoadState('networkidle');

  // Verify new items loaded
  await expect(items).toHaveCount(40);
});
```

- `scrollIntoViewIfNeeded()` triggers sentinel visibility
- IntersectionObserver fires automatically in real browser
- WebSocket mock provides paginated data
- Works reliably without manual waits

#### **Cypress: Scroll and verify** ⭐⭐⭐⭐

```typescript
cy.get('[data-test="device-item"]').should('have.length', 20);
cy.get('[data-test="scroll-sentinel"]').scrollIntoView();
cy.get('[data-test="device-item"]').should('have.length', 40);
```

- Straightforward scroll approach
- Requires `.mockWebsocket()` plugin for WebSocket
- IntersectionObserver works in real browser

#### **WebdriverIO: Scroll Action** ⭐⭐⭐⭐

```typescript
const items = $$('[data-test="device-item"]');
expect(items).toHaveLength(20);

// Scroll sentinel into view
const sentinel = $('[data-test="scroll-sentinel"]');
await sentinel.scrollIntoView();

// Wait for more items
await browser.waitUntil(
  async () => (await $$('[data-test="device-item"]')).length > 20,
  { timeout: 5000 }
);

const updatedItems = $$('[data-test="device-item"]');
expect(updatedItems).toHaveLength(40);
```

- Works reliably
- `scrollIntoView()` available
- Manual wait loops less elegant than Playwright's `waitForLoadState()`

### Key Considerations

1. **Sentinel Element:** Use a dedicated sentinel element (e.g., `[data-test="scroll-sentinel"]`) that IntersectionObserver watches
2. **Mocking Data:** WebSocket mock must return realistic paginated results
3. **Network Waits:** After scroll, wait for WebSocket response and DOM update
4. **Viewport Size:** IntersectionObserver depends on viewport. Test with realistic window dimensions

### Recommendation

**Playwright** handles infinite scroll + IntersectionObserver most naturally. The combination of `scrollIntoViewIfNeeded()`, WebSocket mocking, and `waitForLoadState()` makes tests clean and reliable.

---

## Key Findings & Tradeoffs

### 1. Shadow DOM Support (Critical for Lit)

| Framework | Approach | Score | Notes |
|-----------|----------|-------|-------|
| **Playwright** | Native CSS/text locator piercing | 5/5 | No config, works everywhere |
| **WebdriverIO** | `shadow$()` explicit method | 5/5 | Clear, W3C standard, Lit-specific |
| **Cypress** | `.shadow()` command | 4/5 | Open DOM only, Studio limitations |
| **Puppeteer** | Manual JavaScript evaluation | 2/5 | Cumbersome, error-prone |
| **Testing Library** | Extension required | 2/5 | Not designed for E2E |
| **Vitest** | Real browser context | 3/5 | Works but snapshot issues |

**Winner:** Playwright and WebdriverIO (tie)

### 2. WebSocket Mocking (HA Integration)

| Framework | Capability | Score | Notes |
|-----------|-----------|-------|-------|
| **Playwright** | Native `routeWebSocket()` v1.48+ | 5/5 | Purpose-built, clean API |
| **WebdriverIO** | CDP-based, verbose | 3/5 | Works but requires knowledge |
| **Cypress** | Plugin ecosystem | 3/5 | Not built-in, adds dependency |
| **Puppeteer** | Not supported | 1/5 | Known limitation #3547 |
| **Testing Library** | N/A | 0/5 | Unit testing only |
| **Vitest** | Real browser context | 4/5 | Works via real WS, no mocking |

**Winner:** Playwright (native support)

### 3. Authentication (Token-Based)

| Framework | Approach | Score | Notes |
|-----------|----------|-------|-------|
| **Playwright** | `storageState` reuse | 5/5 | Cleanest, most secure |
| **Cypress** | Environment vars + localStorage | 4/5 | Works, less elegant |
| **WebdriverIO** | Session state management | 4/5 | Functional |
| **Puppeteer** | Manual localStorage setup | 3/5 | Straightforward but basic |
| **Testing Library** | Manual setup | 2/5 | Designed for unit tests |
| **Vitest** | Browser context setup | 3/5 | Works but test-focused |

**Winner:** Playwright (secure state reuse)

### 4. Developer Experience (Setup & Debugging)

| Framework | DX Score | Debugging | CI/CD Setup |
|-----------|----------|-----------|------------|
| **Playwright** | 5/5 | Trace viewer, inspector, codegen | Native, straightforward |
| **Cypress** | 5/5 | Time-travel debug, command log | Good (Cloud optional) |
| **WebdriverIO** | 3/5 | Basic logging | Good but more complex |
| **Puppeteer** | 3/5 | Basic logging | Straightforward |
| **Testing Library** | 4/5 | Clear component output | Very easy |
| **Vitest** | 4/5 | Real browser, snapshots | Very easy |

**Winner:** Cypress (for debugging), Playwright (for overall balance)

### 5. Performance

| Framework | Test Speed | Parallelization | CI/CD Time |
|-----------|-----------|-----------------|-----------|
| **Playwright** | ⭐⭐⭐⭐⭐ Fastest | Native, efficient | Excellent |
| **Cypress** | ⭐⭐⭐⭐ Very fast | Good (Cloud needed) | Good |
| **WebdriverIO** | ⭐⭐⭐⭐ Excellent | Good | Good |
| **Puppeteer** | ⭐⭐⭐⭐ Very fast | Manual | Good |
| **Testing Library** | ⭐⭐⭐⭐⭐ Fastest (unit) | N/A | Excellent |
| **Vitest** | ⭐⭐⭐⭐⭐ Fastest (unit) | Native | Excellent |

**Winner:** Playwright (for E2E), Vitest (for unit tests)

### 6. Ecosystem & Maintenance

| Framework | Community | Maintenance | Documentation |
|-----------|-----------|-------------|---|
| **Playwright** | Microsoft-backed, 20-30M downloads/week | Active, frequent releases | Excellent |
| **Cypress** | Very active, 10-15M downloads/week | Actively maintained | Excellent |
| **WebdriverIO** | Active community | Well-maintained | Good |
| **Puppeteer** | Google-backed | Well-maintained | Good |
| **Testing Library** | Very active ecosystem | Actively maintained | Excellent |
| **Vitest** | Very active (Vite ecosystem) | Actively maintained | Good, improving |

**Winner:** Playwright and Cypress (both well-supported)

---

## Summary Table: Recommendation by Use Case

| Use Case | Best Framework | Rationale |
|----------|---|---|
| **Full E2E Testing** | Playwright | Shadow DOM + WebSocket + auth + performance |
| **Developer-Focused DX** | Cypress | Time-travel debugging, instant feedback |
| **W3C Standards Compliance** | WebdriverIO | Future-proofing, standard protocol |
| **HA Custom Integrations** | Playwright | HA WebSocket patterns, token auth |
| **Component Unit Testing** | Vitest Browser Mode | Real browser, web APIs, fast |
| **Lit Element Testing** | WebdriverIO or Playwright | Lit-specific docs (WebdriverIO), DX (Playwright) |
| **Mobile Testing (Future)** | WebdriverIO | Appium integration ready |
| **Simpler Projects** | Cypress | Excellent DX, lower complexity |

---

## Conclusion

For Vulcan Brownout, **Playwright is the optimal choice** due to:

1. ✅ **Superior Shadow DOM support** (natural piercing, no config)
2. ✅ **Native WebSocket mocking** (purpose-built for HA API testing)
3. ✅ **Excellent token-based auth handling** (secure storageState approach)
4. ✅ **Best-in-class performance** (parallel test execution)
5. ✅ **Modern developer experience** (trace viewer, inspector, debugging)
6. ✅ **Cross-browser coverage** (Chromium, Firefox, WebKit)
7. ✅ **Extensive documentation** (Microsoft-backed project)
8. ✅ **Active HA community adoption** (growing precedent)

**WebdriverIO is a strong alternative** if the team prefers W3C WebDriver standards or already uses Appium. Both frameworks will work excellently for Vulcan Brownout.

**Cypress is excellent for developer experience** but has trade-offs in WebSocket support and parallelization (requires paid Cloud). Consider it if the team values debugging over automation.

---

## Sources

- [Shadow DOM Testing That Doesn't Flake (Using Playwright)](https://medium.com/@erik.amaral/shadow-dom-testing-that-doesnt-flake-using-playwright-1c9313d086d3)
- [Playwright's Playbook: Conquering ShadowDOM Elements with Ease](https://medium.com/helpshift-engineering/playwrights-playbook-conquering-shadowdom-elements-with-ease-35b65bfb8008)
- [Playwright WebSocketRoute API](https://playwright.dev/docs/api/class-websocketroute)
- [Playwright Authentication Guide](https://playwright.dev/docs/auth)
- [Interact and Assert on Shadow DOM in Cypress Studio](https://www.cypress.io/blog/interact-and-assert-on-shadow-dom-in-cypress-studio)
- [Lit | WebdriverIO](https://webdriver.io/docs/component-testing/lit/)
- [WebdriverIO shadow$ API](https://webdriver.io/docs/api/element/shadow$/)
- [Puppeteer GitHub Issue #3547](https://github.com/puppeteer/puppeteer/issues/3547)
- [Feature request: Shadow DOM support · Issue #413](https://github.com/testing-library/dom-testing-library/issues/413)
- [Mastering Dark & Light Mode Testing with Playwright](https://runebook.dev/en/docs/playwright/api/class-testoptions/test-options-color-scheme)
- [Vitest 4.0 Release Notes](https://vitest.dev/guide/browser/)
- [Unable to Access Shadow DOM Text Value in Vitest](https://github.com/vitest-dev/vitest/issues/7688)
- [Testing – Lit](https://lit.dev/docs/tools/testing/)
- [Home Assistant Developer Docs - Testing](https://developers.home-assistant.io/docs/development_testing/)
- [pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component)
- [WebSocket API | Home Assistant Developer Docs](https://developers.home-assistant.io/docs/api/websocket/)

