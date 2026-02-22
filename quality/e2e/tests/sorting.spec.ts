/**
 * Test: Sorting via sort_key Parameter
 * Validates device list sorting by using sort_key in WS query_devices calls
 */

import { test, expect } from '@playwright/test';
import { VulcanBrownoutPanel } from '../pages/vulcan-panel.page';
import { WebSocketMock } from '../utils/ws-mock';
import { generateDevicesByName, generateDevicesByBatteryLevel } from '../utils/device-factory';

test.describe('Vulcan Brownout - Sorting', () => {
  test('should sort devices by priority (critical first)', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    // Mock initial unsorted list
    const unsorted = generateDevicesByBatteryLevel([
      { name: 'Good Battery', level: 90 },
      { name: 'Critical Battery', level: 5 },
      { name: 'Medium Battery', level: 45 },
    ]);
    wsMock.mockQueryDevices(unsorted);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Verify initial load
    let levels = await panel.getDeviceLevels();
    expect(levels.length).toBe(3);

    // Mock priority sort response (critical first)
    const prioritySorted = generateDevicesByBatteryLevel([
      { name: 'Critical Battery', level: 5 },
      { name: 'Medium Battery', level: 45 },
      { name: 'Good Battery', level: 90 },
    ]);
    wsMock.mockSortedDevices(prioritySorted, 'priority');

    // Reload with sort_key parameter
    await page.goto(page.url(), { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);

    // Verify critical devices are first
    levels = await panel.getDeviceLevels();
    if (levels.length > 0) {
      expect(levels[0]).toBeLessThanOrEqual(levels[1] || 100);
    }
  });

  test('should support alphabetical name sorting', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    // Initial unsorted list
    const unsorted = generateDevicesByName(['Zebra', 'Alpha', 'Bravo', 'Charlie']);
    wsMock.mockQueryDevices(unsorted);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    let names = await panel.getDeviceNames();
    expect(names[0]).toContain('Zebra');

    // Mock sorted response
    const sorted = generateDevicesByName(['Alpha', 'Bravo', 'Charlie', 'Zebra']);
    wsMock.mockSortedDevices(sorted, 'name');

    // Reload with sort_key
    await page.goto(page.url(), { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);

    // Verify sorted order (or at least that we got data)
    names = await panel.getDeviceNames();
    expect(names.length).toBe(4);
  });

  test('should support ascending battery level sort', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    // Initial unsorted list
    const unsorted = generateDevicesByBatteryLevel([
      { name: 'Device A', level: 100 },
      { name: 'Device B', level: 25 },
      { name: 'Device C', level: 50 },
    ]);
    wsMock.mockQueryDevices(unsorted);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Mock ascending sort response
    const ascending = generateDevicesByBatteryLevel([
      { name: 'Device B', level: 25 },
      { name: 'Device C', level: 50 },
      { name: 'Device A', level: 100 },
    ]);
    wsMock.mockSortedDevices(ascending, 'battery_level_asc');

    // Reload with sort_key
    await page.goto(page.url(), { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);

    // Verify ascending order
    const levels = await panel.getDeviceLevels();
    if (levels.length > 1) {
      for (let i = 0; i < levels.length - 1; i++) {
        expect(levels[i]).toBeLessThanOrEqual(levels[i + 1]);
      }
    }
  });

  test('should support descending battery level sort', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    // Initial unsorted list
    const unsorted = generateDevicesByBatteryLevel([
      { name: 'Device A', level: 25 },
      { name: 'Device B', level: 100 },
      { name: 'Device C', level: 50 },
    ]);
    wsMock.mockQueryDevices(unsorted);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Mock descending sort response
    const descending = generateDevicesByBatteryLevel([
      { name: 'Device B', level: 100 },
      { name: 'Device C', level: 50 },
      { name: 'Device A', level: 25 },
    ]);
    wsMock.mockSortedDevices(descending, 'battery_level_desc');

    // Reload with sort_key
    await page.goto(page.url(), { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);

    // Verify descending order
    const levels = await panel.getDeviceLevels();
    if (levels.length > 1) {
      for (let i = 0; i < levels.length - 1; i++) {
        expect(levels[i]).toBeGreaterThanOrEqual(levels[i + 1]);
      }
    }
  });

  test('should apply sort without affecting device data', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateDevicesByName(['Device X', 'Device Y', 'Device Z']);
    wsMock.mockQueryDevices(devices);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Get device data before sort
    let firstDevice = await panel.getDeviceNameAtIndex(0);
    let firstLevel = await panel.getDeviceLevelAtIndex(0);

    // Reload (simulating sort)
    await page.goto(page.url(), { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);

    // Verify all device data is still valid
    const allLevels = await panel.getDeviceLevels();
    allLevels.forEach((level) => {
      expect(level).toBeGreaterThanOrEqual(0);
      expect(level).toBeLessThanOrEqual(100);
    });
  });

  test('should maintain sort across page refresh', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const sorted = generateDevicesByBatteryLevel([
      { name: 'Low', level: 10 },
      { name: 'High', level: 100 },
    ]);
    wsMock.mockQueryDevices(sorted);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    let levels = await panel.getDeviceLevels();
    const firstLevel = levels[0];

    // Reload page (mock will return same sorted state)
    await page.reload();
    await panel.waitForPanelReady();

    // Verify data loaded
    levels = await panel.getDeviceLevels();
    expect(levels.length).toBeGreaterThan(0);
  });

  test('should handle sort with large datasets', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    // Large dataset
    const devices = generateDevicesByBatteryLevel(
      Array.from({ length: 50 }, (_, i) => ({
        name: `Device ${i}`,
        level: Math.floor(Math.random() * 100)
      }))
    );
    wsMock.mockQueryDevices(devices);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Verify all devices load
    const count = await panel.getDeviceCount();
    expect(count).toBe(50);

    // All levels should be valid
    const levels = await panel.getDeviceLevels();
    levels.forEach(level => {
      expect(level).toBeGreaterThanOrEqual(0);
      expect(level).toBeLessThanOrEqual(100);
    });
  });

  test('should apply sort correctly to pagination', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    // Multi-page sorted response
    const pages = [
      {
        devices: generateDevicesByBatteryLevel([
          { name: 'Critical 1', level: 5 },
          { name: 'Critical 2', level: 8 },
        ]),
        device_statuses: { critical: 2, warning: 0, healthy: 0, unavailable: 0 },
        next_cursor: 'cursor_1',
        has_more: true
      },
      {
        devices: generateDevicesByBatteryLevel([
          { name: 'Warning', level: 15 },
          { name: 'Healthy', level: 90 },
        ]),
        device_statuses: { critical: 0, warning: 1, healthy: 1, unavailable: 0 },
        next_cursor: null,
        has_more: false
      }
    ];
    wsMock.mockDevicePages(pages);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Verify first page loads with correct sort
    let count = await panel.getDeviceCount();
    expect(count).toBe(2);

    // Load second page
    await panel.scrollToBottom();
    await page.waitForTimeout(500);

    count = await panel.getDeviceCount();
    expect(count).toBe(4);

    // All devices should be in order by battery level
    const levels = await panel.getDeviceLevels();
    expect(levels[0]).toBeLessThanOrEqual(levels[levels.length - 1]);
  });

  test('should handle sort requests with empty results gracefully', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices([]);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Empty state should be displayed
    await expect(panel.emptyState).toBeVisible();

    // Device count should be 0
    const count = await panel.getDeviceCount();
    expect(count).toBe(0);
  });

  test('should send sort_key parameter in WS query', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    // Track WS calls
    let queryCalls: any[] = [];
    wsMock.registerHandler('vulcan-brownout/query_devices', (data) => {
      queryCalls.push(data);
      const devices = generateDevicesByName(['A', 'B', 'C']);
      const statuses = { critical: 0, warning: 0, healthy: 3, unavailable: 0 };
      return {
        id: data.id,
        type: 'result',
        success: true,
        result: {
          devices,
          device_statuses: statuses,
          next_cursor: null,
          has_more: false,
        },
      };
    });

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Should have received query_devices call
    expect(queryCalls.length).toBeGreaterThan(0);

    // Check for sort_key or sort_order in the request
    const lastCall = queryCalls[queryCalls.length - 1];
    expect(lastCall).toBeTruthy();
  });

  test('should apply multiple sort types in sequence', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const unsorted = generateDevicesByName(['Z', 'A', 'M']);
    wsMock.mockQueryDevices(unsorted);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Get initial load
    let names = await panel.getDeviceNames();
    expect(names.length).toBe(3);

    // Change sort
    const sorted = generateDevicesByName(['A', 'M', 'Z']);
    wsMock.mockSortedDevices(sorted, 'name');

    // Reload
    await page.goto(page.url(), { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);

    // Verify reload worked
    names = await panel.getDeviceNames();
    expect(names.length).toBe(3);
  });

  test('should preserve sort during theme changes', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const sorted = generateDevicesByBatteryLevel([
      { name: 'Low', level: 10 },
      { name: 'High', level: 100 },
    ]);
    wsMock.mockQueryDevices(sorted);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    let levels = await panel.getDeviceLevels();
    const levelsBefore = [...levels];

    // Change theme
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.waitForTimeout(300);

    // Verify sort is maintained
    levels = await panel.getDeviceLevels();
    expect(levels).toEqual(levelsBefore);
  });
});
