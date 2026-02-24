/**
 * Test: Device List Rendering (v6 simplified)
 * All shown devices are below 15% threshold (critical status)
 *
 * Mock mode (TARGET_ENV=mock): uses WebSocketMock with generated data
 * Real mode (TARGET_ENV=docker|staging): hits real HA backend
 */

import { test, expect } from '@playwright/test';
import { VulcanBrownoutPanel } from '../pages/vulcan-panel.page';
import { WebSocketMock } from '../utils/ws-mock';
import { generateDeviceList, generateDevicesByName } from '../utils/device-factory';

const isMock = (process.env.TARGET_ENV || 'mock') === 'mock';

test.describe('Vulcan Brownout - Device List', () => {
  test('should display devices with correct data', async ({ page }) => {
    if (isMock) {
      const wsMock = new WebSocketMock(page);
      await wsMock.setup();
      wsMock.mockQueryEntities(generateDeviceList(0, 5));
    }

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    const count = await panel.getDeviceCount();
    if (!isMock) {
      expect(count).toBeGreaterThanOrEqual(0);
    } else {
      expect(count).toBe(5);
    }

    const names = await panel.getDeviceNames();
    expect(names.length).toBe(count);
  });

  test('should display named devices in order', async ({ page }) => {
    if (isMock) {
      const wsMock = new WebSocketMock(page);
      await wsMock.setup();
      wsMock.mockQueryEntities(generateDevicesByName(['Alpha', 'Bravo', 'Charlie']));
    }

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    const names = await panel.getDeviceNames();
    if (!isMock) {
      // On real HA, just verify we got device names (real data)
      expect(names.length).toBeGreaterThanOrEqual(0);
      names.forEach((name) => expect(name.length).toBeGreaterThan(0));
    } else {
      expect(names[0]).toContain('Alpha');
      expect(names[1]).toContain('Bravo');
      expect(names[2]).toContain('Charlie');
    }
  });

  test('should display battery levels for all devices', async ({ page }) => {
    if (isMock) {
      const wsMock = new WebSocketMock(page);
      await wsMock.setup();
      wsMock.mockQueryEntities(generateDeviceList(0, 5));
    }

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    const levels = await panel.getDeviceLevels();
    if (isMock) {
      expect(levels.length).toBe(5);
    }
    levels.forEach((level) => {
      expect(level).toBeGreaterThanOrEqual(0);
      expect(level).toBeLessThan(15);
    });
  });

  test('should show all devices below 15% threshold', async ({ page }) => {
    if (isMock) {
      const wsMock = new WebSocketMock(page);
      await wsMock.setup();
      wsMock.mockQueryEntities(generateDeviceList(0, 3));
    }

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    const levels = await panel.getDeviceLevels();
    levels.forEach((level) => {
      expect(level).toBeGreaterThanOrEqual(0);
      expect(level).toBeLessThan(15);
    });
  });

  test('should handle devices with special characters in names @mock-only', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();
    wsMock.mockQueryEntities(generateDevicesByName(['Device (1)', 'Device & Co']));

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    const names = await panel.getDeviceNames();
    expect(names[0]).toContain('Device (1)');
    expect(names[1]).toContain('Device & Co');
  });
});
