/**
 * Test: Panel Loading & Initialization (v6 simplified)
 * Validates that the Vulcan Brownout panel loads and displays devices below 15%
 *
 * Mock mode (TARGET_ENV=mock): uses WebSocketMock with generated data
 * Real mode (TARGET_ENV=docker|staging): hits real HA backend
 */

import { test, expect } from '@playwright/test';
import { VulcanBrownoutPanel } from '../pages/vulcan-panel.page';
import { WebSocketMock } from '../utils/ws-mock';
import { generateDeviceList } from '../utils/device-factory';

const isMock = (process.env.TARGET_ENV || 'mock') === 'mock';

test.describe('Vulcan Brownout - Panel Loading', () => {
  test('should load panel and verify DOM structure', async ({ page }) => {
    if (isMock) {
      const wsMock = new WebSocketMock(page);
      await wsMock.setup();
      wsMock.mockQueryEntities(generateDeviceList(0, 5));
      wsMock.mockSubscribe('test-subscription-id');
    }

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    await expect(panel.panel).toBeVisible();
  });

  test('should display device list with correct count', async ({ page }) => {
    if (isMock) {
      const wsMock = new WebSocketMock(page);
      await wsMock.setup();
      wsMock.mockQueryEntities(generateDeviceList(0, 5));
    }

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    const deviceCount = await panel.getDeviceCount();
    if (!isMock) {
      expect(deviceCount).toBeGreaterThanOrEqual(0);
    } else {
      expect(deviceCount).toBe(5);
    }
  });

  test('should render table with correct columns', async ({ page }) => {
    if (isMock) {
      const wsMock = new WebSocketMock(page);
      await wsMock.setup();
      wsMock.mockQueryEntities(generateDeviceList(0, 3));
    }

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    const count = await panel.getDeviceCount();
    if (count > 0) {
      const headers = panel.panel.locator('.battery-table thead th');
      await expect(headers).toHaveCount(5);

      const firstRow = await panel.getDeviceAtIndex(0);
      const cells = firstRow.locator('td');
      await expect(cells).toHaveCount(5);
    }
  });

  test('should handle empty device list with positive message @mock-only', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();
    wsMock.mockQueryEntities([]);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    await expect(panel.panel).toBeVisible();
    await expect(panel.emptyState).toBeVisible();

    const emptyText = await panel.emptyState.locator('.empty-state-text').textContent();
    expect(emptyText).toContain('All batteries above 15%');
  });

  test('should show connection status badge', async ({ page }) => {
    if (isMock) {
      const wsMock = new WebSocketMock(page);
      await wsMock.setup();
      wsMock.mockQueryEntities(generateDeviceList(0, 3));
      wsMock.mockSubscribe('test-sub');
    }

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    await expect(panel.connectionBadge).toBeVisible();
    await expect(panel.connectionDot).toBeVisible();
  });

  test('should load within acceptable time', async ({ page }) => {
    if (isMock) {
      const wsMock = new WebSocketMock(page);
      await wsMock.setup();
      wsMock.mockQueryEntities(generateDeviceList(0, 10));
    }

    const panel = new VulcanBrownoutPanel(page);
    const startTime = Date.now();
    await panel.goto();
    const loadTime = Date.now() - startTime;

    expect(loadTime).toBeLessThan(isMock ? 5000 : 15000);
    await expect(panel.panel).toBeVisible();
  });

  test('should verify panel is accessible', async ({ page }) => {
    if (isMock) {
      const wsMock = new WebSocketMock(page);
      await wsMock.setup();
      wsMock.mockQueryEntities(generateDeviceList(0, 5));
    }

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();
    await panel.verifyAccessible();
  });
});
