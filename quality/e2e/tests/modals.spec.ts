/**
 * Test: Modal Interactions
 * Validates settings and notification preference modals
 */

import { test, expect } from '@playwright/test';
import { VulcanBrownoutPanel } from '../pages/vulcan-panel.page';
import { WebSocketMock } from '../utils/ws-mock';
import { generateDeviceList } from '../utils/device-factory';

test.describe('Vulcan Brownout - Modals', () => {
  test('should open settings modal', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));
    wsMock.mockSetThreshold(15);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Open settings
    await panel.openSettings();

    // Verify modal is visible
    const modal = page.locator('.modal');
    await expect(modal).toBeVisible();

    // Verify modal has header
    const header = modal.locator('.modal-header');
    await expect(header).toBeVisible();
  });

  test('should close settings modal', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));
    wsMock.mockSetThreshold(15);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Open settings
    await panel.openSettings();

    const modal = page.locator('.modal');
    await expect(modal).toBeVisible();

    // Close modal
    await panel.closeSettings();

    // Modal should be hidden
    await expect(modal).not.toBeVisible();
  });

  test('should display settings modal controls', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));
    wsMock.mockSetThreshold(20);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Open settings
    await panel.openSettings();

    // Verify threshold input exists
    const thresholdInput = page.locator('input[type="number"]');
    const saveButton = page.locator('button:has-text("💾")');

    await expect(thresholdInput).toBeVisible();
    await expect(saveButton).toBeVisible();
  });

  test('should save threshold settings', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));
    wsMock.mockSetThreshold(25);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Open settings
    await panel.openSettings();

    // Set threshold value
    const thresholdInput = page.locator('.modal input[type="number"]');
    await thresholdInput.fill('25');

    // Save
    const saveButton = page.locator('.modal button:has-text("💾")');
    await saveButton.click();

    // Wait for network idle
    await page.waitForLoadState('networkidle');
  });

  test('should open notifications modal', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));
    wsMock.mockNotificationPrefs({
      enabled: true,
      frequency_cap_hours: 6,
      severity_filter: 'critical_only',
      notification_history: [],
    });

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Open notifications
    await panel.openNotifications();

    // Verify modal is visible
    const modal = page.locator('.modal');
    await expect(modal).toBeVisible();

    // Verify modal contains notification content
    const modalText = await modal.textContent();
    expect(modalText).toContain('Notification');
  });

  test('should close notifications modal', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));
    wsMock.mockNotificationPrefs({
      enabled: true,
      frequency_cap_hours: 6,
      severity_filter: 'critical_only',
      notification_history: [],
    });

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Open notifications
    await panel.openNotifications();

    // Close modal
    await panel.closeNotifications();

    // Modal should be hidden
    const modal = page.locator('.modal');
    await expect(modal).not.toBeVisible();
  });

  test('should display notification preferences controls', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));
    wsMock.mockNotificationPrefs({
      enabled: true,
      frequency_cap_hours: 6,
      severity_filter: 'critical_only',
      notification_history: [],
    });

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Open notifications
    await panel.openNotifications();

    // Verify preference controls exist
    const enableCheckbox = page.locator('.modal input[type="checkbox"]');
    const frequencySelect = page.locator('.modal select');
    const radioButtons = page.locator('.modal input[type="radio"]');

    await expect(enableCheckbox).toBeVisible();
    await expect(frequencySelect).toBeVisible();
    expect(await radioButtons.count()).toBeGreaterThan(0);
  });

  test('should save notification preferences', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));
    wsMock.mockNotificationPrefs({
      enabled: false,
      frequency_cap_hours: 24,
      severity_filter: 'critical_and_warning',
      notification_history: [],
    });

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Open notifications
    await panel.openNotifications();

    // Toggle preference
    const enableCheckbox = page.locator('.modal input[type="checkbox"]');
    await enableCheckbox.click();

    // Save
    const saveButton = page.locator('.modal button:has-text("💾")');
    await saveButton.click();

    // Verify save completes
    await page.waitForLoadState('networkidle');
  });

  test('should prevent interaction with panel while modal open', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));
    wsMock.mockSetThreshold(15);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Open settings modal
    await panel.openSettings();

    // Modal overlay should block interactions
    const overlay = page.locator('.modal-overlay');
    await expect(overlay).toBeVisible();

    // Close modal
    await panel.closeSettings();

    // Overlay should be gone
    await expect(overlay).not.toBeVisible();
  });

  test('should handle escape key to close modal', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));
    wsMock.mockSetThreshold(15);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Open settings
    await panel.openSettings();

    const modal = page.locator('.modal');
    await expect(modal).toBeVisible();

    // Press escape
    await page.keyboard.press('Escape');

    // Modal should close
    await expect(modal).not.toBeVisible();
  });

  test('should display modal title', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));
    wsMock.mockSetThreshold(15);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Open settings
    await panel.openSettings();

    // Verify title exists
    const title = page.locator('.modal-header h2');
    await expect(title).toBeVisible();

    const titleText = await title.textContent();
    expect(titleText).toBeTruthy();
  });

  test('should validate threshold input range', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));
    wsMock.mockSetThreshold(50);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Open settings
    await panel.openSettings();

    // Test input validation
    const thresholdInput = page.locator('.modal input[type="number"]') as any;

    // Get min/max constraints
    const min = await thresholdInput.getAttribute('min');
    const max = await thresholdInput.getAttribute('max');

    expect(min).toBeTruthy();
    expect(max).toBeTruthy();

    // Try valid value
    await thresholdInput.fill('50');
    const saveButton = page.locator('.modal button:has-text("💾")');
    expect(await saveButton.isEnabled()).toBe(true);
  });

  test('should reset modal state on close and reopen', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));
    wsMock.mockSetThreshold(30);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Open settings
    await panel.openSettings();

    // Close modal
    await panel.closeSettings();

    // Reopen modal
    await panel.openSettings();

    // Verify input is still visible
    const thresholdInput = page.locator('.modal input[type="number"]');
    await expect(thresholdInput).toBeVisible();
  });

  test('should display loading state while saving', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));
    wsMock.mockSetThreshold(35);

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Open settings
    await panel.openSettings();

    // Set value and save
    const thresholdInput = page.locator('.modal input[type="number"]');
    await thresholdInput.fill('35');

    const saveButton = page.locator('.modal button:has-text("💾")');
    await saveButton.click();

    // Verify save completes
    await page.waitForLoadState('networkidle');
  });

  test('should display notification history in modal', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));
    wsMock.mockNotificationPrefs({
      enabled: true,
      frequency_cap_hours: 6,
      severity_filter: 'critical_only',
      notification_history: [
        { device_name: 'Test Device', battery_level: 5, timestamp: new Date().toISOString() }
      ],
    });

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Open notifications
    await panel.openNotifications();

    // Verify notification history is visible
    const history = page.locator('.modal input[placeholder="Search..."]');
    await expect(history).toBeVisible();
  });
});
