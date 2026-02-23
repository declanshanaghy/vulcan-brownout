import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for Vulcan Brownout E2E tests
 *
 * Projects:
 * - chromium: Mock WebSocket (fast feedback, <5s per test)
 * - staging: Real HA backend (integration tests against staging environment)
 *
 * Run staging tests: STAGING_MODE=true npx playwright test --project=staging
 * Or use: npm run test:staging
 */

const isStaging = process.env.STAGING_MODE === 'true';

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
    baseURL: process.env.HA_URL || 'http://homeassistant.lan:8123',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  ...(isStaging && {
    globalSetup: require.resolve('./global-setup-staging.ts'),
  }),

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
      },
    },
    {
      name: 'staging',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/staging-auth.json',
        actionTimeout: 15000,
        navigationTimeout: 30000,
      },
      timeout: 60000,
      retries: 1,
      grepInvert: /@mock-only/,
    },
  ],
});
