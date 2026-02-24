/**
 * Test: Theme Integration (Dark / Light mode)
 *
 * Validates that the Battery Monitoring panel's background colour changes
 * when the browser colour scheme is switched between dark and light.
 *
 * HA 2026.x uses "Use default theme" which respects the OS/browser
 * prefers-color-scheme media feature. Playwright's page.emulateMedia()
 * sets this directly — no profile page navigation required.
 *
 * This test runs ONLY against a real HA instance (docker / staging projects).
 * Tag: @mock-only is NOT present so it will be included in those runs.
 */

import { test, expect } from '@playwright/test';
import { VulcanBrownoutPanel } from '../pages/vulcan-panel.page';

/**
 * Parse an "rgb(r, g, b)" string into numeric components.
 */
function parseRgb(rgb: string): { r: number; g: number; b: number } | null {
  const m = rgb.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
  if (!m) return null;
  return { r: Number(m[1]), g: Number(m[2]), b: Number(m[3]) };
}

/**
 * Read the computed background-color of the panel's top-level div.
 */
async function getPanelBgColor(panel: VulcanBrownoutPanel): Promise<string> {
  return panel.panel.locator('.battery-panel').evaluate((el) =>
    window.getComputedStyle(el).backgroundColor,
  );
}

test.describe('Vulcan Brownout - Theme Integration', () => {
  test('should switch between Dark and Light themes', async ({ page }) => {
    const panel = new VulcanBrownoutPanel(page);

    // ── Step 1: Dark mode ────────────────────────────────────────────
    // HA "Use default theme" follows prefers-color-scheme; emulateMedia
    // sets it directly without needing profile page navigation.
    await page.emulateMedia({ colorScheme: 'dark' });

    await panel.goto();
    await panel.waitForPanelReady();

    // Wait for HA CSS custom properties to apply
    await page.waitForTimeout(1000);

    const darkBg = parseRgb(await getPanelBgColor(panel));
    expect(darkBg, 'Expected valid rgb() for dark background').toBeTruthy();
    expect(darkBg!.r, `Dark R=${darkBg!.r} should be < 100`).toBeLessThan(100);
    expect(darkBg!.g, `Dark G=${darkBg!.g} should be < 100`).toBeLessThan(100);
    expect(darkBg!.b, `Dark B=${darkBg!.b} should be < 100`).toBeLessThan(100);

    // ── Step 2: Light mode ───────────────────────────────────────────
    await page.emulateMedia({ colorScheme: 'light' });

    await panel.goto();
    await panel.waitForPanelReady();

    // Wait for HA CSS custom properties to apply
    await page.waitForTimeout(1000);

    const lightBg = parseRgb(await getPanelBgColor(panel));
    expect(lightBg, 'Expected valid rgb() for light background').toBeTruthy();
    expect(lightBg!.r, `Light R=${lightBg!.r} should be > 200`).toBeGreaterThan(200);
    expect(lightBg!.g, `Light G=${lightBg!.g} should be > 200`).toBeGreaterThan(200);
    expect(lightBg!.b, `Light B=${lightBg!.b} should be > 200`).toBeGreaterThan(200);
  });
});
