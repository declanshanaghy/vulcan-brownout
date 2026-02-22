import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for Vulcan Brownout E2E tests
 *
 * Architecture decisions:
 * - Mock WebSocket (fast feedback, <5s per test)
 * - Headless by default (headless + screenshot on failure)
 * - Chromium only for MVP (add Firefox/WebKit later)
 * - Base URL: HA panel at homeassistant.lan:8123
 * - Authentication via stored state (auth.json)
 */

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results.json' }],
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
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/auth.json',
      },
    },
    // Future: Add Firefox and WebKit after MVP
    // {
    //   name: 'firefox',
    //   use: {
    //     ...devices['Desktop Firefox'],
    //     storageState: 'playwright/.auth/auth.json',
    //   },
    // },
    // {
    //   name: 'webkit',
    //   use: {
    //     ...devices['Desktop Safari'],
    //     storageState: 'playwright/.auth/auth.json',
    //   },
    // },
  ],

  // Setup test runs once to establish authentication
  globalSetup: require.resolve('./global-setup.ts'),
});
