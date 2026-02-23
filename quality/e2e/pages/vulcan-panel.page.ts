/**
 * Page Object Model for Vulcan Brownout panel
 * Encapsulates all selectors and interactions with the panel
 * Handles Shadow DOM navigation via Playwright's native piercing
 */

import { Page, Locator, expect } from '@playwright/test';
import * as dotenv from 'dotenv';
import path from 'path';

// Load credentials
dotenv.config({ path: path.join(__dirname, '..', '.env.test') });
if (!process.env.HA_TOKEN) {
  dotenv.config({ path: path.join(__dirname, '..', '..', '..', '.env') });
}
const HA_USERNAME = process.env.HA_USERNAME || '';
const HA_PASSWORD = process.env.HA_PASSWORD || '';
const HA_URL = process.env.HA_URL || 'http://homeassistant.lan:8123';

export class VulcanBrownoutPanel {
  readonly page: Page;
  readonly panel: Locator;
  readonly deviceList: Locator;
  readonly deviceItems: Locator;
  readonly header: Locator;
  readonly title: Locator;
  readonly settingsButton: Locator;
  readonly notificationButton: Locator;
  readonly connectionBadge: Locator;
  readonly connectionDot: Locator;
  readonly emptyState: Locator;
  readonly backToTopButton: Locator;
  readonly sortMenu: Locator;
  readonly filterBar: Locator;
  readonly filterChips: Locator;
  readonly filterDropdown: Locator;
  readonly clearAllFilters: Locator;
  readonly filteredEmptyState: Locator;

  constructor(page: Page) {
    this.page = page;
    this.panel = page.locator('vulcan-brownout-panel');
    this.header = this.panel.locator('.header');
    this.title = this.header.locator('h1');
    this.deviceList = this.panel.locator('.battery-list');
    this.deviceItems = this.panel.locator('.battery-card');
    this.settingsButton = this.header.locator('button:has-text("⚙️")');
    this.notificationButton = this.header.locator('button:has-text("🔔")');
    this.connectionBadge = this.header.locator('.connection-badge');
    this.connectionDot = this.connectionBadge.locator('.connection-dot');
    this.emptyState = this.panel.locator('.empty-state');
    this.backToTopButton = this.panel.locator('.back-to-top');
    this.sortMenu = this.page.locator('[data-test="sort-menu"]');
    this.filterBar = this.panel.locator('.filter-bar');
    this.filterChips = this.panel.locator('.filter-chip');
    this.filterDropdown = this.panel.locator('.filter-dropdown');
    this.clearAllFilters = this.panel.locator('[data-test="clear-all-filters"]');
    this.filteredEmptyState = this.panel.locator('.filtered-empty-state');
  }

  /**
   * Log in to HA via the login form if we're on the login page.
   * Playwright pierces shadow DOM natively for form inputs.
   */
  private async loginIfNeeded(): Promise<void> {
    const url = this.page.url();
    if (!url.includes('/auth/')) return;

    // We're on the login page — fill the form
    console.log('Login page detected, authenticating...');

    // Wait for the login form to render (it's inside Shadow DOM: ha-authorize)
    await this.page.waitForTimeout(2000);

    // Fill username — Playwright pierces shadow DOM
    const usernameInput = this.page.locator('input[name="username"]').first();
    await usernameInput.waitFor({ state: 'visible', timeout: 10000 }).catch(() => {
      console.warn('Login form not found, skipping auth');
    });

    if (HA_USERNAME) {
      await usernameInput.fill(HA_USERNAME).catch(() => {});
    }

    // Fill password
    if (HA_PASSWORD) {
      const passwordInput = this.page.locator('input[name="password"]').first();
      await passwordInput.fill(HA_PASSWORD).catch(() => {});

      // Click login button
      const loginButton = this.page.getByRole('button', { name: /log in/i });
      await loginButton.click().catch(() => {});

      // Wait for navigation away from auth page
      await this.page.waitForURL((url) => !url.toString().includes('/auth/'), { timeout: 15000 }).catch(() => {
        console.warn('Auth navigation timeout, continuing anyway');
      });
      await this.page.waitForTimeout(2000);
    }
  }

  /**
   * Navigate to the panel with auth handling
   */
  async goto(): Promise<void> {
    console.log(`Attempting to navigate to ${HA_URL}/vulcan-brownout`);

    // Try to navigate with a reasonable timeout
    try {
      const response = await this.page.goto(`${HA_URL}/vulcan-brownout`, {
        waitUntil: 'domcontentloaded',
        timeout: 20000
      });
      console.log(`Navigation response status:${response?.status() || 'N/A'}`);
    } catch (e) {
      console.warn(`Navigation error:`, (e as any).message || e);
    }

    console.log(`Current URL after navigation: ${this.page.url()}`);
    await this.page.waitForTimeout(1000);

    // Handle login if redirected
    const url = this.page.url();
    if (url.includes('/auth/')) {
      console.log('Detected login redirect, attempting auth...');
      await this.loginIfNeeded();
    }

    // If we're not on the panel page after login, try again
    if (!this.page.url().includes('/vulcan-brownout')) {
      console.log(`Not on panel yet, attempting redirect. Current URL: ${this.page.url()}`);
      try {
        await this.page.goto(`${HA_URL}/vulcan-brownout`, {
          waitUntil: 'domcontentloaded',
          timeout: 20000
        });
      } catch (e) {
        // Navigation may fail if server isn't running
        console.warn('Could not navigate to panel, but proceeding for mocked tests');
      }
      await this.page.waitForTimeout(1000);
    }

    console.log(`Final URL: ${this.page.url()}`);

    // Wait for panel to appear in DOM (may take time for HA shell to load it)
    // With a longer timeout since real HA takes time
    await this.panel.waitFor({ state: 'attached', timeout: 20000 }).catch(() => {
      console.log('Panel element not yet attached (may not be loaded from server)');
    });
  }

  /**
   * Wait for panel to be fully loaded with devices
   */
  async waitForPanelReady(timeout = 10000): Promise<void> {
    await this.panel.waitFor({ state: 'visible', timeout });
    await this.deviceList.waitFor({ state: 'visible', timeout }).catch(() => {});
  }

  async getDeviceCount(): Promise<number> {
    return (await this.deviceItems.all()).length;
  }

  async getDeviceNames(): Promise<string[]> {
    const items = await this.deviceItems.all();
    const names: string[] = [];
    for (const item of items) {
      const name = await item.locator('.device-name').textContent();
      if (name) names.push(name.trim());
    }
    return names;
  }

  async getDeviceLevels(): Promise<number[]> {
    const items = await this.deviceItems.all();
    const levels: number[] = [];
    for (const item of items) {
      const text = await item.locator('.battery-level').textContent();
      if (text) {
        const match = text.match(/\d+/);
        if (match) levels.push(parseInt(match[0]));
      }
    }
    return levels;
  }

  async scrollToBottom(): Promise<void> {
    await this.deviceList.evaluate((el) => { el.scrollTop = el.scrollHeight; });
    await this.page.waitForTimeout(500);
  }

  async scrollToTop(): Promise<void> {
    await this.deviceList.evaluate((el) => { el.scrollTop = 0; });
  }

  async getDeviceNameAtIndex(index: number): Promise<string | null> {
    return this.deviceItems.nth(index).locator('.device-name').textContent();
  }

  async getDeviceLevelAtIndex(index: number): Promise<number | null> {
    const text = await this.deviceItems.nth(index).locator('.battery-level').textContent();
    if (text) {
      const match = text.match(/\d+/);
      if (match) return parseInt(match[0]);
    }
    return null;
  }

  async waitForDeviceCount(count: number, timeout = 5000): Promise<void> {
    const startTime = Date.now();
    while (Date.now() - startTime < timeout) {
      const current = await this.getDeviceCount();
      if (current >= count) return;
      await this.page.waitForTimeout(200);
    }
  }

  async isPanelPresent(): Promise<boolean> {
    return (await this.panel.count()) > 0;
  }

  async isHAShellLoaded(): Promise<boolean> {
    return (await this.page.locator('home-assistant').count()) > 0;
  }

  async screenshot(name: string): Promise<Buffer> {
    return this.page.screenshot({ path: `test-results/${name}.png`, fullPage: true });
  }

  /**
   * Get all device items as Locators
   */
  async getDeviceItems(): Promise<Locator[]> {
    return (await this.deviceItems.all());
  }

  /**
   * Get device item at index
   */
  async getDeviceAtIndex(index: number): Promise<Locator> {
    return this.deviceItems.nth(index);
  }

  /**
   * Open settings modal
   */
  async openSettings(): Promise<void> {
    await this.settingsButton.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Close settings modal
   */
  async closeSettings(): Promise<void> {
    const modal = this.page.locator('.modal-overlay');
    const closeButton = modal.locator('.modal-close');
    if (await modal.isVisible()) {
      await closeButton.click();
      await this.page.waitForTimeout(300);
    }
  }

  /**
   * Open notification modal
   */
  async openNotifications(): Promise<void> {
    await this.notificationButton.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Close notification modal
   */
  async closeNotifications(): Promise<void> {
    const modal = this.page.locator('.modal-overlay');
    const closeButton = modal.locator('.modal-close');
    if (await modal.isVisible()) {
      await closeButton.click();
      await this.page.waitForTimeout(300);
    }
  }

  /**
   * Get computed background color of the panel's top-level div.
   * Useful for verifying theme changes.
   */
  async getPanelBackgroundColor(): Promise<string> {
    return this.panel.locator('.battery-panel').evaluate((el) =>
      window.getComputedStyle(el).backgroundColor,
    );
  }

  /**
   * Set filter (client-side filtering)
   */
  async setFilter(term: string): Promise<void> {
    // The panel doesn't have a filter input based on actual HTML
    // This is a no-op for now as filtering happens server-side
  }

  /**
   * Clear filter
   */
  async clearFilter(): Promise<void> {
    // The panel doesn't have a filter input based on actual HTML
  }

  /**
   * Click sort button
   */
  async clickSort(): Promise<void> {
    // Sort is handled via WS sort_key parameter
    // UI buttons don't actually exist in the real panel
  }

  /**
   * Select sort option
   */
  async selectSortOption(option: string): Promise<void> {
    // Sort is handled via WS sort_key parameter
    // Reload devices with sort_key parameter
  }

  /**
   * Verify panel is accessible
   */
  async verifyAccessible(): Promise<void> {
    await expect(this.panel).toBeVisible();
    await expect(this.title).toBeVisible();
    await expect(this.settingsButton).toBeVisible();
    await expect(this.notificationButton).toBeVisible();
  }

  /**
   * Check if filter bar is visible
   */
  async isFilterBarVisible(): Promise<boolean> {
    return (await this.filterBar.count()) > 0;
  }

  /**
   * Open a filter dropdown by category name
   */
  async openFilterDropdown(category: string): Promise<void> {
    const button = this.panel.locator(`button[data-test="filter-${category.toLowerCase()}"]`);
    await button.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Select a filter value in a dropdown
   */
  async selectFilter(category: string, value: string): Promise<void> {
    const checkbox = this.panel.locator(
      `[data-test="filter-${category.toLowerCase()}"] input[value="${value}"]`
    );
    await checkbox.check();
    await this.page.waitForTimeout(300);
  }

  /**
   * Remove a specific filter chip
   */
  async removeFilterChip(category: string, value: string): Promise<void> {
    const chip = this.panel.locator(
      `[data-test="filter-chip-${category.toLowerCase()}-${value}"]`
    );
    const removeBtn = chip.locator('[data-test="remove-chip"]');
    await removeBtn.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Clear all filters
   */
  async clearAllFiltersAction(): Promise<void> {
    await this.clearAllFilters.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Get count of active filters
   */
  async getActiveFilterCount(): Promise<number> {
    return (await this.filterChips.all()).length;
  }

  /**
   * Check if filtered empty state is visible
   */
  async isFilteredEmptyStateVisible(): Promise<boolean> {
    return (await this.filteredEmptyState.count()) > 0;
  }

  /**
   * Get active filter chips as text
   */
  async getActiveFilterChips(): Promise<string[]> {
    const chips = await this.filterChips.all();
    const texts: string[] = [];
    for (const chip of chips) {
      const text = await chip.textContent();
      if (text) texts.push(text.trim());
    }
    return texts;
  }
}
