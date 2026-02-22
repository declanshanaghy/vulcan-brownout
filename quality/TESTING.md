# E2E Testing Quick Start

## Prerequisites
- Node.js 18+
- HA long-lived access token in .env

## Setup
```bash
cd quality/e2e
npm install
npx playwright install chromium
```

## Run
```bash
npx playwright test                    # All tests
npx playwright test panel.spec.ts      # Single suite
npx playwright test --headed           # With browser
```

## Test Suites (68 tests)
1. Panel Loading & Initial State
2. Infinite Scroll & Pagination
3. Settings & Threshold Configuration
4. Notification Preferences
5. Dark Mode / Theme Switching
6. Empty State & Error Handling

## Key Patterns
- Shadow DOM: `page.locator('vulcan-brownout-panel >> .battery-list')`
- Auth: HA token injected via fixture
- WebSocket: Test via UI observation (verify device cards update)
- Test data: Pre-provisioned entities in staging HA

See decko-ux-testing-decisions.md for architectural decisions.
