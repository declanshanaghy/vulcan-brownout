/**
 * Test: Theme Integration via HA Profile Settings
 *
 * Validates that the Battery Monitoring panel respects the user's chosen
 * HA theme (Auto / Light / Dark) by navigating to the profile page,
 * selecting a theme radio button, then verifying the panel's background
 * colour changes accordingly.
 *
 * This test runs ONLY against a real HA instance (staging project).
 * Tag: @mock-only is NOT present so it will be included in staging runs.
 */

import { test, expect } from '@playwright/test';
import { VulcanBrownoutPanel } from '../pages/vulcan-panel.page';

const HA_URL = process.env.HA_URL || 'http://homeassistant.lan:8123';

/**
 * Parse an "rgb(r, g, b)" string into numeric components.
 */
function parseRgb(rgb: string): { r: number; g: number; b: number } | null {
  const m = rgb.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
  if (!m) return null;
  return { r: Number(m[1]), g: Number(m[2]), b: Number(m[3]) };
}

/**
 * Navigate to the HA profile page and select a theme radio button.
 * Matches the video flow: Sprocket → profile → Theme → click radio.
 *
 * HA's profile page uses deeply nested Shadow DOM (ha-formfield → ha-radio),
 * so we traverse shadow roots via JS to find and click the correct radio.
 */
async function setThemeViaProfile(
  page: import('@playwright/test').Page,
  theme: 'Auto' | 'Light' | 'Dark',
): Promise<void> {
  // Navigate to profile page (matches video: clicking Sprocket)
  await page.goto(`${HA_URL}/profile/general`, {
    waitUntil: 'domcontentloaded',
    timeout: 20000,
  });
  await page.waitForTimeout(3000);

  // HA wraps theme radios in <ha-formfield label="Dark"> inside nested
  // shadow roots. Traverse shadow DOM to find and click the right one.
  const clicked = await page.evaluate((label: string) => {
    function findAllInShadows(root: Document | Element | ShadowRoot, selector: string): Element[] {
      const results: Element[] = [];
      results.push(...root.querySelectorAll(selector));
      for (const child of root.querySelectorAll('*')) {
        if (child.shadowRoot) {
          results.push(...findAllInShadows(child.shadowRoot, selector));
        }
      }
      return results;
    }

    const formfields = findAllInShadows(document, 'ha-formfield');
    for (const ff of formfields) {
      if (ff.getAttribute('label') === label) {
        (ff as HTMLElement).click();
        return true;
      }
    }
    return false;
  }, theme);

  if (!clicked) {
    throw new Error(`Could not find ha-formfield with label="${theme}" on profile page`);
  }

  // Wait for HA to apply the theme (CSS custom properties update)
  await page.waitForTimeout(2000);
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
  test('should switch between Dark and Light themes via HA profile', async ({ page }) => {
    const panel = new VulcanBrownoutPanel(page);

    // ── Step 1: Set Dark theme via profile ──────────────────────────
    await setThemeViaProfile(page, 'Dark');

    // Navigate to Battery Monitoring panel (mirrors sidebar click in video)
    await panel.goto();
    await panel.waitForPanelReady();

    // Verify dark background (low RGB values)
    const darkBg = parseRgb(await getPanelBgColor(panel));
    expect(darkBg, 'Expected valid rgb() for dark background').toBeTruthy();
    expect(darkBg!.r, `Dark R=${darkBg!.r} should be < 100`).toBeLessThan(100);
    expect(darkBg!.g, `Dark G=${darkBg!.g} should be < 100`).toBeLessThan(100);
    expect(darkBg!.b, `Dark B=${darkBg!.b} should be < 100`).toBeLessThan(100);

    // ── Step 2: Switch to Light theme ───────────────────────────────
    await setThemeViaProfile(page, 'Light');

    await panel.goto();
    await panel.waitForPanelReady();

    // Verify light background (high RGB values)
    const lightBg = parseRgb(await getPanelBgColor(panel));
    expect(lightBg, 'Expected valid rgb() for light background').toBeTruthy();
    expect(lightBg!.r, `Light R=${lightBg!.r} should be > 200`).toBeGreaterThan(200);
    expect(lightBg!.g, `Light G=${lightBg!.g} should be > 200`).toBeGreaterThan(200);
    expect(lightBg!.b, `Light B=${lightBg!.b} should be > 200`).toBeGreaterThan(200);
  });
});
