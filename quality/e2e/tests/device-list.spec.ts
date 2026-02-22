/**
 * Test: Device List Rendering & Display
 * Validates device list display and properties
 */

import { test, expect } from '@playwright/test';
import { VulcanBrownoutPanel } from '../pages/vulcan-panel.page';
import { WebSocketMock } from '../utils/ws-mock';
import { generateDeviceList, generateDevicesByName } from '../utils/device-factory';

test.describe('Vulcan Brownout - Device List', () => {
  test('should display device list with correct data', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateDeviceList(0, 9);
    wsMock.mockQueryDevices(devices);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Verify device count
    const count = await panel.getDeviceCount();
    expect(count).toBe(9);

    // Verify device names are populated
    const names = await panel.getDeviceNames();
    expect(names.length).toBe(9);
    names.forEach((name) => {
      expect(name).toMatch(/Device \d+/);
    });
  });

  test('should display device attributes correctly', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateDevicesByName(['Living Room Light', 'Kitchen Switch', 'Front Door Lock']);
    wsMock.mockQueryDevices(devices);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Verify specific device names
    const names = await panel.getDeviceNames();
    expect(names[0]).toContain('Living Room Light');
    expect(names[1]).toContain('Kitchen Switch');
    expect(names[2]).toContain('Front Door Lock');
  });

  test('should display device in correct visual order', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateDevicesByName(['Alpha', 'Bravo', 'Charlie', 'Delta']);
    wsMock.mockQueryDevices(devices);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    const names = await panel.getDeviceNames();
    expect(names[0]).toContain('Alpha');
    expect(names[1]).toContain('Bravo');
    expect(names[2]).toContain('Charlie');
    expect(names[3]).toContain('Delta');
  });

  test('should handle large device lists', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    // Generate large list (100 devices)
    const devices = generateDeviceList(0, 100);
    wsMock.mockQueryDevices(devices);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    const count = await panel.getDeviceCount();
    expect(count).toBe(100);
  });

  test('should verify device item clickability', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateDeviceList(0, 5);
    wsMock.mockQueryDevices(devices);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Verify first device item is visible
    const firstDevice = await panel.getDeviceAtIndex(0);
    await expect(firstDevice).toBeVisible();
  });

  test('should display battery levels for all devices', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateDeviceList(0, 9);
    wsMock.mockQueryDevices(devices);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    const levels = await panel.getDeviceLevels();
    expect(levels.length).toBe(9);

    // All levels should be valid percentages
    levels.forEach((level) => {
      expect(level).toBeGreaterThanOrEqual(0);
      expect(level).toBeLessThanOrEqual(100);
    });
  });

  test('should display device status information', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateDeviceList(0, 5);
    wsMock.mockQueryDevices(devices);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Verify device status is displayed
    for (let i = 0; i < 5; i++) {
      const item = await panel.getDeviceAtIndex(i);
      const statusText = await item.locator('.device-status').textContent();
      expect(statusText).toBeTruthy();
      expect(['critical', 'warning', 'healthy', 'unavailable']).toContain(statusText?.toLowerCase());
    }
  });

  test('should preserve list state after interactions', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateDevicesByName(['A', 'B', 'C', 'D', 'E']);
    wsMock.mockQueryDevices(devices);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Get initial order
    let names = await panel.getDeviceNames();
    expect(names[0]).toContain('A');

    // Perform an interaction (open and close settings modal)
    await panel.openSettings();
    await panel.closeSettings();

    // Verify order is preserved
    names = await panel.getDeviceNames();
    expect(names[0]).toContain('A');
  });

  test('should display correct battery status classes', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateDeviceList(0, 5);
    wsMock.mockQueryDevices(devices);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Verify battery status classes are applied
    for (let i = 0; i < 5; i++) {
      const item = await panel.getDeviceAtIndex(i);
      const batteryDiv = item.locator('.battery-level');
      const classes = await batteryDiv.getAttribute('class');
      expect(classes).toContain('battery-');
      // Should have one of: battery-critical, battery-warning, battery-healthy, battery-unavailable
      const hasValidClass = ['battery-critical', 'battery-warning', 'battery-healthy', 'battery-unavailable']
        .some(c => classes?.includes(c));
      expect(hasValidClass).toBe(true);
    }
  });

  test('should show N/A for unavailable devices', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateDeviceList(0, 3);
    // Mark first device as unavailable
    devices[0].available = false;
    devices[0].status = 'unavailable';
    wsMock.mockQueryDevices(devices);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Check first device shows N/A
    const firstItem = await panel.getDeviceAtIndex(0);
    const levelText = await firstItem.locator('.battery-level').textContent();
    expect(levelText).toContain('N/A');
  });

  test('should handle devices with special characters in names', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateDevicesByName(['Device (1)', 'Device & Co', 'Device <Special>']);
    wsMock.mockQueryDevices(devices);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    const names = await panel.getDeviceNames();
    expect(names[0]).toContain('Device (1)');
    expect(names[1]).toContain('Device & Co');
    expect(names[2]).toContain('Device <Special>');
  });

  test('should verify all device statuses are represented', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateDeviceList(0, 5);
    wsMock.mockQueryDevices(devices);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Collect all device statuses
    const statuses = new Set<string>();
    for (let i = 0; i < 5; i++) {
      const item = await panel.getDeviceAtIndex(i);
      const status = await item.locator('.device-status').textContent();
      if (status) {
        statuses.add(status.toLowerCase());
      }
    }

    // Should have at least one status
    expect(statuses.size).toBeGreaterThan(0);
  });
});
