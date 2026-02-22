/**
 * Test: Panel Loading & Initialization
 * Validates that the Vulcan Brownout panel loads correctly and displays initial state
 */

import { test, expect } from '@playwright/test';
import { VulcanBrownoutPanel } from '../pages/vulcan-panel.page';
import { WebSocketMock } from '../utils/ws-mock';
import { generateDeviceList } from '../utils/device-factory';

test.describe('Vulcan Brownout - Panel Loading', () => {
  test('should load panel and verify DOM structure', async ({ page }) => {
    // Setup WebSocket mock BEFORE navigation
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    // Mock initial device list response
    wsMock.mockQueryDevices(generateDeviceList(0, 9));

    // Setup subscription mock
    wsMock.mockSubscribe('test-subscription-id');

    // Create page object and navigate
    const panel = new VulcanBrownoutPanel(page);
    console.log('Navigating to panel...');
    await panel.goto();

    // Debug: Check what's on the page
    const hasPanel = await panel.panel.count();
    console.log(`Found ${hasPanel} panel elements`);

    if (hasPanel === 0) {
      const pageContent = await page.content();
      console.log('Page contains vulcan-brownout-panel:', pageContent.includes('vulcan-brownout-panel'));
      const hasHome = await page.locator('home-assistant').count();
      console.log(`Found ${hasHome} home-assistant elements`);
    }

    // Verify panel element is in DOM
    await expect(panel.panel).toBeVisible();

    // Verify panel contains expected UI elements
    await expect(panel.deviceList).toBeVisible();
    await expect(panel.settingsButton).toBeVisible();
    await expect(panel.notificationButton).toBeVisible();
  });

  test('should display device list with correct count', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateDeviceList(0, 9);
    wsMock.mockQueryDevices(devices);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Verify device count matches mock data
    const deviceCount = await panel.getDeviceCount();
    expect(deviceCount).toBe(9);
  });

  test('should render device items with correct attributes', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateDeviceList(0, 3);
    wsMock.mockQueryDevices(devices);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Get first device item
    const firstItem = await panel.getDeviceAtIndex(0);

    // Verify device item contains expected elements
    const name = await firstItem.locator('.device-name').isVisible();
    const battery = await firstItem.locator('.battery-level').isVisible();
    const status = await firstItem.locator('.device-status').isVisible();

    expect(name).toBe(true);
    expect(battery).toBe(true);
    expect(status).toBe(true);

    // Verify device data is populated
    const deviceName = await firstItem.locator('.device-name').textContent();
    expect(deviceName).toBeTruthy();
  });

  test('should display battery level information', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateDeviceList(0, 5);
    wsMock.mockQueryDevices(devices);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Check all devices have battery levels
    for (let i = 0; i < 5; i++) {
      const level = await panel.getDeviceLevelAtIndex(i);
      expect(level).not.toBeNull();
      expect(level).toBeGreaterThanOrEqual(0);
      expect(level).toBeLessThanOrEqual(100);
    }
  });

  test('should handle empty device list gracefully', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    // Mock empty device list
    wsMock.mockQueryDevices([]);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Panel should still be visible even with no devices
    await expect(panel.panel).toBeVisible();

    // Empty state should be displayed
    await expect(panel.emptyState).toBeVisible();

    // Device count should be 0
    const deviceCount = await panel.getDeviceCount();
    expect(deviceCount).toBe(0);
  });

  test('should display all control buttons', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Verify buttons are visible and interactive
    await expect(panel.settingsButton).toBeVisible();
    await expect(panel.settingsButton).toBeEnabled();

    await expect(panel.notificationButton).toBeVisible();
    await expect(panel.notificationButton).toBeEnabled();

    // Verify connection badge
    await expect(panel.connectionBadge).toBeVisible();
    await expect(panel.connectionDot).toBeVisible();
  });

  test('should verify panel is accessible and responsive', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 9));

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Run basic accessibility check
    await panel.verifyAccessible();

    // Take screenshot for visual verification
    await panel.screenshot('panel-load-success');
  });

  test('should load within acceptable time', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 20));

    const panel = new VulcanBrownoutPanel(page);

    const startTime = Date.now();
    await panel.goto();
    const loadTime = Date.now() - startTime;

    // Panel should load in under 5 seconds
    expect(loadTime).toBeLessThan(5000);

    // Verify panel is ready
    await expect(panel.panel).toBeVisible();
  });

  test('should display correct number of devices based on data', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    // Mock devices with known count
    const devices = generateDeviceList(0, 20);
    wsMock.mockQueryDevices(devices);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    const deviceCount = await panel.getDeviceCount();
    expect(deviceCount).toBe(20);
  });

  test('should show connection status badge', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));
    wsMock.mockSubscribe('test-subscription-id');

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Verify connection badge is visible
    await expect(panel.connectionBadge).toBeVisible();

    // Verify connection dot exists
    await expect(panel.connectionDot).toBeVisible();

    // Check for connection status text
    const badgeText = await panel.connectionBadge.textContent();
    expect(badgeText).toBeTruthy();
  });
});
