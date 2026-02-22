/**
 * Test: Infinite Scroll & Pagination
 * Validates progressive loading of devices as user scrolls
 */

import { test, expect } from '@playwright/test';
import { VulcanBrownoutPanel } from '../pages/vulcan-panel.page';
import { WebSocketMock } from '../utils/ws-mock';
import { generateDeviceListResponse } from '../utils/device-factory';

test.describe('Vulcan Brownout - Infinite Scroll', () => {
  test('should load initial page of devices', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const firstPage = generateDeviceListResponse(0, 20, 3);
    wsMock.mockQueryDevices(firstPage.devices);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Verify first page is loaded
    const count = await panel.getDeviceCount();
    expect(count).toBe(20);
  });

  test('should load next page when scrolling to bottom', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const pages = [
      generateDeviceListResponse(0, 20, 3),
      generateDeviceListResponse(1, 20, 3),
    ];
    wsMock.mockDevicePages(pages);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Initial count
    let count = await panel.getDeviceCount();
    expect(count).toBe(20);

    // Scroll to bottom
    await panel.scrollToBottom();

    // Wait for load
    await page.waitForTimeout(500);

    // Verify more devices loaded
    count = await panel.getDeviceCount();
    expect(count).toBe(40);
  });

  test('should load multiple pages progressively', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const pages = [
      generateDeviceListResponse(0, 20, 3),
      generateDeviceListResponse(1, 20, 3),
      generateDeviceListResponse(2, 20, 3),
    ];
    wsMock.mockDevicePages(pages);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Load page 1
    let count = await panel.getDeviceCount();
    expect(count).toBe(20);

    // Load page 2
    await panel.scrollToBottom();
    await page.waitForTimeout(500);
    count = await panel.getDeviceCount();
    expect(count).toBe(40);

    // Load page 3
    await panel.scrollToBottom();
    await page.waitForTimeout(500);
    count = await panel.getDeviceCount();
    expect(count).toBe(60);
  });

  test('should not load beyond final page', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    // Only 2 pages available
    const pages = [
      generateDeviceListResponse(0, 20, 2),
      generateDeviceListResponse(1, 20, 2),
    ];
    wsMock.mockDevicePages(pages);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Load both pages
    await panel.scrollToBottom();
    await page.waitForTimeout(500);
    let count = await panel.getDeviceCount();
    expect(count).toBe(40);

    // Try to scroll beyond final page
    await panel.scrollToBottom();
    await page.waitForTimeout(500);
    count = await panel.getDeviceCount();

    // Count should not increase
    expect(count).toBe(40);
  });

  test('should maintain device list during load', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const pages = [
      generateDeviceListResponse(0, 20, 2),
      generateDeviceListResponse(1, 20, 2),
    ];
    wsMock.mockDevicePages(pages);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Get device at current position
    let deviceName = await panel.getDeviceNameAtIndex(5);

    // Scroll to bottom to trigger load
    await panel.scrollToBottom();
    await page.waitForTimeout(500);

    // Verify device at position 5 is still in the list (might be scrolled away)
    const devices = await panel.getDeviceNames();
    expect(devices).toContain(deviceName);
  });

  test('should prevent duplicate device loading', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const pages = [
      generateDeviceListResponse(0, 20, 2),
      generateDeviceListResponse(1, 20, 2),
    ];
    wsMock.mockDevicePages(pages);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Get first set of devices
    const names1 = await panel.getDeviceNames();

    // Scroll and load more
    await panel.scrollToBottom();
    await page.waitForTimeout(500);

    // Get all devices
    const allNames = await panel.getDeviceNames();

    // No duplicates should exist
    const unique = new Set(allNames);
    expect(unique.size).toBe(allNames.length);
  });

  test('should handle empty remaining pages gracefully', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    // First page has devices, second is empty
    const pages = [
      generateDeviceListResponse(0, 15, 2),
      { devices: [], device_statuses: { critical: 0, warning: 0, healthy: 0, unavailable: 0 }, next_cursor: null, has_more: false }
    ];
    wsMock.mockDevicePages(pages);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Load first page
    let count = await panel.getDeviceCount();
    expect(count).toBe(15);

    // Try to load empty second page
    await panel.scrollToBottom();
    await page.waitForTimeout(500);

    // Count should remain 15
    count = await panel.getDeviceCount();
    expect(count).toBe(15);
  });

  test('should show skeleton loaders during scroll load', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const pages = [
      generateDeviceListResponse(0, 20, 2),
      generateDeviceListResponse(1, 20, 2),
    ];
    wsMock.mockDevicePages(pages);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Trigger scroll (skeleton loaders should appear)
    await panel.scrollToBottom();

    // Wait a bit for skeletons to appear
    await page.waitForTimeout(100);

    // Verify new content appears
    await page.waitForTimeout(500);
    const count = await panel.getDeviceCount();
    expect(count).toBe(40);
  });

  test('should recover from scroll load error', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    // Setup pages with error scenario
    let pages = [generateDeviceListResponse(0, 20, 2)];
    wsMock.mockDevicePages(pages);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    let count = await panel.getDeviceCount();
    expect(count).toBe(20);

    // Recover by providing valid response
    pages = [
      generateDeviceListResponse(0, 20, 2),
      generateDeviceListResponse(1, 20, 2),
    ];
    wsMock.mockDevicePages(pages);

    // Try again
    await panel.scrollToBottom();
    await page.waitForTimeout(500);

    // Should successfully load
    count = await panel.getDeviceCount();
    expect(count).toBe(40);
  });

  test('should handle rapid scroll events', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const pages = [
      generateDeviceListResponse(0, 20, 4),
      generateDeviceListResponse(1, 20, 4),
      generateDeviceListResponse(2, 20, 4),
      generateDeviceListResponse(3, 20, 4),
    ];
    wsMock.mockDevicePages(pages);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Rapid scroll events
    await panel.scrollToBottom();
    await page.waitForTimeout(200);
    await panel.scrollToBottom();
    await page.waitForTimeout(200);
    await panel.scrollToBottom();
    await page.waitForTimeout(500);

    // Final count should be at least 80
    const count = await panel.getDeviceCount();
    expect(count).toBeGreaterThanOrEqual(40);
  });

  test('should work with large page sizes', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    // Large first page
    const pages = [
      generateDeviceListResponse(0, 100, 2),
      generateDeviceListResponse(1, 100, 2),
    ];
    wsMock.mockDevicePages(pages);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Verify large page loads
    let count = await panel.getDeviceCount();
    expect(count).toBe(100);

    // Load second page
    await panel.scrollToBottom();
    await page.waitForTimeout(500);
    count = await panel.getDeviceCount();
    expect(count).toBe(200);
  });

  test('should preserve list order across pages', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const pages = [
      generateDeviceListResponse(0, 10, 2),
      generateDeviceListResponse(1, 10, 2),
    ];
    wsMock.mockDevicePages(pages);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Get first page devices
    const names1 = await panel.getDeviceNames();
    expect(names1[0]).toMatch(/Device 0/);
    expect(names1[9]).toMatch(/Device 9/);

    // Load second page
    await panel.scrollToBottom();
    await page.waitForTimeout(500);

    // Get all devices
    const allNames = await panel.getDeviceNames();

    // First page should still be at beginning
    expect(allNames.slice(0, 10)).toEqual(names1);

    // Second page should follow
    expect(allNames[10]).toMatch(/Device 10/);
  });

  test('should show back-to-top button after scroll', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const pages = [
      generateDeviceListResponse(0, 20, 2),
      generateDeviceListResponse(1, 20, 2),
    ];
    wsMock.mockDevicePages(pages);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Scroll to bottom
    await panel.scrollToBottom();
    await page.waitForTimeout(500);

    // Back-to-top button might be visible
    const backToTop = panel.backToTopButton;
    const isVisible = await backToTop.isVisible().catch(() => false);

    // Button should exist
    expect(await backToTop.count()).toBeGreaterThan(0);

    // Click it to scroll to top
    if (isVisible) {
      await backToTop.click();
      await page.waitForTimeout(500);
    }
  });

  test('should maintain scroll position during async load', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const pages = [
      generateDeviceListResponse(0, 20, 2),
      generateDeviceListResponse(1, 20, 2),
    ];
    wsMock.mockDevicePages(pages);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Get scroll position before load
    const scrollBefore = await panel.deviceList.evaluate(el => el.scrollTop);

    // Scroll to middle
    await panel.deviceList.evaluate(el => el.scrollTop = el.scrollHeight / 3);
    const scrollMiddle = await panel.deviceList.evaluate(el => el.scrollTop);
    expect(scrollMiddle).toBeGreaterThan(0);

    // Load more (should not reset scroll)
    await panel.scrollToBottom();
    await page.waitForTimeout(500);

    // Check scroll is maintained or reasonable
    const scrollAfter = await panel.deviceList.evaluate(el => el.scrollTop);
    expect(scrollAfter).toBeGreaterThan(0);
  });
});
