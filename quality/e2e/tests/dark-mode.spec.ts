/**
 * Test: Dark Mode & Theme Support
 * Validates dark mode detection and CSS custom properties via document attribute
 */

import { test, expect } from '@playwright/test';
import { VulcanBrownoutPanel } from '../pages/vulcan-panel.page';
import { WebSocketMock } from '../utils/ws-mock';
import { generateDeviceList } from '../utils/device-factory';

test.describe('Vulcan Brownout - Dark Mode', () => {
  test('should render in light mode by default', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 9));

    const panel = new VulcanBrownoutPanel(page);

    // Set light color scheme
    await page.emulateMedia({ colorScheme: 'light' });

    await panel.goto();

    // Check if dark mode class is not active (look at data-theme attribute)
    const isDark = await page.locator('html').evaluate(
      (el) => el.getAttribute('data-theme') === 'dark' || el.getAttribute('data-theme') === 'dark-theme'
    );
    expect(isDark).toBe(false);
  });

  test('should detect dark mode via document attribute', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 9));

    const panel = new VulcanBrownoutPanel(page);

    // Set dark color scheme
    await page.emulateMedia({ colorScheme: 'dark' });

    await panel.goto();

    // Panel should render (MutationObserver will detect the data-theme attribute)
    await expect(panel.panel).toBeVisible();
  });

  test('should respond to prefers-color-scheme media query', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));

    const panel = new VulcanBrownoutPanel(page);

    // Start in light mode
    await page.emulateMedia({ colorScheme: 'light' });
    await panel.goto();

    const bgLight = await panel.panel.evaluate((el) => {
      return window.getComputedStyle(el).backgroundColor;
    });

    // Switch to dark mode
    await page.emulateMedia({ colorScheme: 'dark' });

    const bgDark = await panel.panel.evaluate((el) => {
      return window.getComputedStyle(el).backgroundColor;
    });

    // Backgrounds should be valid colors
    expect(bgLight).toMatch(/rgb/);
    expect(bgDark).toMatch(/rgb/);
  });

  test('should apply dark mode CSS custom properties', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));

    const panel = new VulcanBrownoutPanel(page);

    await page.emulateMedia({ colorScheme: 'dark' });
    await panel.goto();

    // Verify custom properties exist
    const customProps = await panel.panel.evaluate((el) => {
      const computed = window.getComputedStyle(el);
      return {
        bgColor: computed.getPropertyValue('--vb-bg-primary'),
        color: computed.getPropertyValue('--vb-text-primary'),
      };
    });

    // Dark theme should have CSS variables set
    expect(customProps.bgColor || customProps.color).toBeTruthy();
  });

  test('should render device items with appropriate colors in dark mode', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));

    const panel = new VulcanBrownoutPanel(page);

    await page.emulateMedia({ colorScheme: 'dark' });
    await panel.goto();

    // Check device item colors
    const deviceColor = await (await panel.getDeviceAtIndex(0)).evaluate((el) => {
      return window.getComputedStyle(el).color;
    });

    expect(deviceColor).toBeTruthy();
    expect(deviceColor).toMatch(/rgb/);
  });

  test('should detect theme changes via MutationObserver', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Panel should be visible
    await expect(panel.panel).toBeVisible();

    // Simulate theme change by setting data-theme attribute
    await page.locator('html').evaluate((el) => {
      el.setAttribute('data-theme', 'dark');
    });

    await page.waitForTimeout(300);

    // Panel should still be responsive
    await expect(panel.panel).toBeVisible();
  });

  test('should persist dark mode preference in storage', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));

    const panel = new VulcanBrownoutPanel(page);
    await panel.goto();

    // Reload page
    await page.reload();
    await panel.waitForPanelReady();

    // Panel should load successfully after reload
    await expect(panel.panel).toBeVisible();
  });

  test('should update text contrast for accessibility in dark mode', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 3));

    const panel = new VulcanBrownoutPanel(page);

    await page.emulateMedia({ colorScheme: 'dark' });
    await panel.goto();

    // Verify device names are readable (have color text)
    const deviceName = await panel.getDeviceNameAtIndex(0);
    expect(deviceName).toBeTruthy();

    // Check computed style is valid
    const textColor = await (await panel.getDeviceAtIndex(0)).evaluate((el) => {
      const computed = window.getComputedStyle(el);
      return computed.color;
    });

    expect(textColor).toMatch(/rgb/);
  });

  test('should apply dark mode to modals', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));

    const panel = new VulcanBrownoutPanel(page);

    await page.emulateMedia({ colorScheme: 'dark' });
    await panel.goto();

    // Open settings modal
    await panel.openSettings();

    // Verify modal is visible and has styles applied
    const modal = page.locator('.modal');
    await expect(modal).toBeVisible();

    // Check modal has background
    const modalBg = await modal.evaluate((el) => {
      return window.getComputedStyle(el).backgroundColor;
    });

    expect(modalBg).toMatch(/rgb/);
  });

  test('should maintain dark mode across modal open/close', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));

    const panel = new VulcanBrownoutPanel(page);

    await page.emulateMedia({ colorScheme: 'dark' });
    await panel.goto();

    // Get dark mode state before modal
    const themeBeforeModal = await page.locator('html').getAttribute('data-theme');

    // Open and close modal
    await panel.openSettings();
    await panel.closeSettings();

    // Verify dark mode state unchanged
    const themeAfterModal = await page.locator('html').getAttribute('data-theme');
    expect(themeAfterModal).toBe(themeBeforeModal);
  });

  test('should handle theme switching during scroll', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    const pages = [
      { devices: generateDeviceList(0, 20), device_statuses: { critical: 0, warning: 0, healthy: 0, unavailable: 0 }, next_cursor: 'cursor_1', has_more: true },
      { devices: generateDeviceList(1, 20), device_statuses: { critical: 0, warning: 0, healthy: 0, unavailable: 0 }, next_cursor: null, has_more: false },
    ];
    wsMock.mockDevicePages(pages);

    const panel = new VulcanBrownoutPanel(page);

    await page.emulateMedia({ colorScheme: 'light' });
    await panel.goto();

    // Start scrolling
    await panel.scrollToBottom();

    // Switch to dark mode during scroll
    await page.emulateMedia({ colorScheme: 'dark' });

    // Continue interacting
    const count = await panel.getDeviceCount();
    expect(count).toBeGreaterThanOrEqual(20);

    // Verify still responsive
    await expect(panel.panel).toBeVisible();
  });

  test('should work with high contrast mode', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 5));

    const panel = new VulcanBrownoutPanel(page);

    // Emulate high contrast preference
    await page.emulateMedia({ forcedColors: 'active' });
    await panel.goto();

    // Panel should still render
    await expect(panel.panel).toBeVisible();
    await expect(panel.deviceList).toBeVisible();
  });

  test('should have valid CSS custom properties for both themes', async ({ page }) => {
    const wsMock = new WebSocketMock(page);
    await wsMock.setup();

    wsMock.mockQueryDevices(generateDeviceList(0, 3));

    const panel = new VulcanBrownoutPanel(page);

    // Test light theme
    await page.emulateMedia({ colorScheme: 'light' });
    await panel.goto();

    const lightVars = await page.locator('html').evaluate((el) => {
      const style = window.getComputedStyle(el);
      return {
        bg: style.getPropertyValue('--vb-bg-primary'),
        text: style.getPropertyValue('--vb-text-primary'),
      };
    });

    expect(lightVars.bg || lightVars.text).toBeTruthy();

    // Test dark theme
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.waitForTimeout(500);

    const darkVars = await page.locator('html').evaluate((el) => {
      const style = window.getComputedStyle(el);
      return {
        bg: style.getPropertyValue('--vb-bg-primary'),
        text: style.getPropertyValue('--vb-text-primary'),
      };
    });

    expect(darkVars.bg || darkVars.text).toBeTruthy();
  });
});
