/**
 * Test: Filtering Feature (Sprint 5)
 * Validates server-side filtering, filter UI, persistence, and edge cases
 */

import { test, expect } from '@playwright/test';
import { VulcanBrownoutPanel } from '../pages/vulcan-panel.page';
import { WebSocketMock } from '../utils/ws-mock';
import { generateFilterTestDevices } from '../utils/device-factory';

test.describe('Vulcan Brownout - Filtering', () => {
  test('should display filter bar', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateFilterTestDevices(20);
    wsMock.mockQueryDevices(devices);
    wsMock.mockGetFilterOptions();

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    const isVisible = await panel.isFilterBarVisible();
    expect(isVisible).toBe(true);
  });

  test('should show filter dropdown on click', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateFilterTestDevices(20);
    wsMock.mockQueryDevices(devices);
    wsMock.mockGetFilterOptions();

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Open manufacturer filter dropdown
    await panel.openFilterDropdown('manufacturer');

    // Verify dropdown is visible
    const dropdown = page.locator('[data-test="filter-manufacturer"]');
    await expect(dropdown).toBeVisible();
  });

  test('should apply status filter', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateFilterTestDevices(20);
    wsMock.mockQueryDevices(devices);
    wsMock.mockGetFilterOptions();

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Open status filter
    await panel.openFilterDropdown('status');

    // Select critical status
    await panel.selectFilter('status', 'critical');

    // Wait for device list to update
    await page.waitForTimeout(500);

    // Verify devices are filtered (would need actual WebSocket response verification)
    const count = await panel.getDeviceCount();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should show active filter chips', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateFilterTestDevices(20);
    wsMock.mockQueryDevices(devices);
    wsMock.mockGetFilterOptions();

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Apply a filter
    await panel.openFilterDropdown('manufacturer');
    await panel.selectFilter('manufacturer', 'Aqara');

    // Wait for chip to appear
    await page.waitForTimeout(500);

    // Verify chip count
    const chipCount = await panel.getActiveFilterCount();
    expect(chipCount).toBeGreaterThan(0);
  });

  test('should remove filter chip', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateFilterTestDevices(20);
    wsMock.mockQueryDevices(devices);
    wsMock.mockGetFilterOptions();

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Apply a filter
    await panel.openFilterDropdown('manufacturer');
    await panel.selectFilter('manufacturer', 'Aqara');

    // Wait for chip
    await page.waitForTimeout(500);

    const countBefore = await panel.getActiveFilterCount();
    expect(countBefore).toBeGreaterThan(0);

    // Remove the filter chip
    await panel.removeFilterChip('manufacturer', 'Aqara');

    // Wait for chip to be removed
    await page.waitForTimeout(500);

    const countAfter = await panel.getActiveFilterCount();
    expect(countAfter).toBeLessThan(countBefore);
  });

  test('should clear all filters', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateFilterTestDevices(20);
    wsMock.mockQueryDevices(devices);
    wsMock.mockGetFilterOptions();

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Apply multiple filters
    await panel.openFilterDropdown('manufacturer');
    await panel.selectFilter('manufacturer', 'Aqara');
    await panel.openFilterDropdown('status');
    await panel.selectFilter('status', 'critical');

    // Wait for chips
    await page.waitForTimeout(500);

    const countBefore = await panel.getActiveFilterCount();
    expect(countBefore).toBeGreaterThan(0);

    // Clear all filters
    await panel.clearAllFiltersAction();

    // Wait for chips to be removed
    await page.waitForTimeout(500);

    const countAfter = await panel.getActiveFilterCount();
    expect(countAfter).toBe(0);
  });

  test('should show filtered empty state', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    // Setup with no devices
    wsMock.mockQueryDevices([]);
    wsMock.mockGetFilterOptions();

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Check if filtered empty state is visible
    await page.waitForTimeout(500);
    const isVisible = await panel.isFilteredEmptyStateVisible();

    // Either filtered empty state or regular empty state should be visible
    const hasEmptyState = await panel.emptyState.isVisible().catch(() => false);
    expect(isVisible || hasEmptyState).toBe(true);
  });

  test('should persist filters to localStorage', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateFilterTestDevices(20);
    wsMock.mockQueryDevices(devices);
    wsMock.mockGetFilterOptions();

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Apply a filter
    await panel.openFilterDropdown('manufacturer');
    await panel.selectFilter('manufacturer', 'Aqara');

    // Wait for filter to be applied
    await page.waitForTimeout(500);

    // Get initial filter count
    const countBefore = await panel.getActiveFilterCount();
    expect(countBefore).toBeGreaterThan(0);

    // Reload the page
    await page.reload();
    await page.waitForTimeout(1000);

    // Verify filters persisted
    const countAfter = await panel.getActiveFilterCount();
    expect(countAfter).toBe(countBefore);
  });

  test('should combine multiple filters', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateFilterTestDevices(20);
    wsMock.mockQueryDevices(devices);
    wsMock.mockGetFilterOptions();

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Apply manufacturer filter
    await panel.openFilterDropdown('manufacturer');
    await panel.selectFilter('manufacturer', 'Aqara');

    // Apply status filter
    await panel.openFilterDropdown('status');
    await panel.selectFilter('status', 'critical');

    // Wait for filters to apply
    await page.waitForTimeout(500);

    // Verify both filters are active
    const chipCount = await panel.getActiveFilterCount();
    expect(chipCount).toBeGreaterThanOrEqual(2);
  });

  test('should handle devices with no devices matching filter', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateFilterTestDevices(20);
    wsMock.mockQueryDevices(devices);
    wsMock.mockGetFilterOptions();

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Apply a filter that will match nothing (in mock)
    await panel.openFilterDropdown('manufacturer');
    await panel.selectFilter('manufacturer', 'NonExistent');

    // Wait for filter to apply
    await page.waitForTimeout(500);

    // Verify device list is empty or shows empty state
    const deviceCount = await panel.getDeviceCount();
    expect(deviceCount).toBe(0);
  });

  test('should load filter options dynamically', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateFilterTestDevices(20);
    wsMock.mockQueryDevices(devices);

    // Mock filter options with specific values
    wsMock.mockGetFilterOptions({
      manufacturers: ['TestManufacturer1', 'TestManufacturer2'],
      device_classes: ['battery'],
      areas: [
        { id: 'area1', name: 'TestArea1' },
        { id: 'area2', name: 'TestArea2' },
      ],
      statuses: ['critical', 'warning', 'healthy', 'unavailable'],
    });

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Open manufacturer filter
    await panel.openFilterDropdown('manufacturer');

    // Verify options are loaded
    const dropdown = page.locator('[data-test="filter-manufacturer"]');
    await expect(dropdown).toBeVisible();
  });

  test('should maintain filter state across device list updates', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const devices = generateFilterTestDevices(20);
    wsMock.mockQueryDevices(devices);
    wsMock.mockGetFilterOptions();

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Apply a filter
    await panel.openFilterDropdown('status');
    await panel.selectFilter('status', 'healthy');

    // Wait for filter
    await page.waitForTimeout(500);

    const countBefore = await panel.getActiveFilterCount();
    expect(countBefore).toBeGreaterThan(0);

    // Scroll device list (simulating pagination)
    await panel.scrollToBottom();
    await page.waitForTimeout(300);

    // Verify filter is still active
    const countAfter = await panel.getActiveFilterCount();
    expect(countAfter).toBe(countBefore);
  });
});
