import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for Vulcan Brownout E2E tests
 *
 * Target environments (set via TARGET_ENV):
 * - mock    (default): Docker HA frontend + intercepted vulcan-brownout WebSocket (fast feedback)
 * - docker: Docker HA with real vulcan-brownout integration (full local stack)
 * - staging: Staging HA server with real integration (end-to-end validation)
 *
 * Usage:
 *   TARGET_ENV=mock    npx playwright test --project=mock
 *   TARGET_ENV=docker  npx playwright test --project=docker
 *   TARGET_ENV=staging npx playwright test --project=staging
 * Or use the npm scripts:
 *   npm run test:mock | test:docker | test:staging
 */

const targetEnv = (process.env.TARGET_ENV || 'mock') as 'mock' | 'docker' | 'staging';
const isMock = targetEnv === 'mock';

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
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  ...(!isMock && {
    globalSetup: require.resolve('./global-setup.ts'),
  }),

  projects: [
    {
      name: 'mock',
      use: {
        ...devices['Desktop Chrome'],
        baseURL: process.env.HA_URL || 'http://localhost:8123',
      },
    },
    {
      name: 'docker',
      use: {
        ...devices['Desktop Chrome'],
        baseURL: process.env.HA_URL || 'http://localhost:8123',
        storageState: 'playwright/.auth/docker-auth.json',
        actionTimeout: 15000,
        navigationTimeout: 30000,
      },
      timeout: 60000,
      retries: 1,
      grepInvert: /@mock-only/,
    },
    {
      name: 'staging',
      use: {
        ...devices['Desktop Chrome'],
        baseURL: process.env.HA_URL || 'http://homeassistant.lan:8123',
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
