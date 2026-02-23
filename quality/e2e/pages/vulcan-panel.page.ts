/**
 * Page Object Model for Vulcan Brownout panel (v6 simplified)
 * Handles Shadow DOM navigation via Playwright's native piercing
 */

import { Page, Locator, expect } from '@playwright/test';
import * as dotenv from 'dotenv';
import path from 'path';

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
  readonly connectionBadge: Locator;
  readonly connectionDot: Locator;
  readonly emptyState: Locator;

  constructor(page: Page) {
    this.page = page;
    this.panel = page.locator('vulcan-brownout-panel');
    this.header = this.panel.locator('.header');
    this.title = this.header.locator('h1');
    this.deviceList = this.panel.locator('.table-container');
    this.deviceItems = this.panel.locator('.battery-table tbody tr');
    this.connectionBadge = this.header.locator('.connection-badge');
    this.connectionDot = this.connectionBadge.locator('.connection-dot');
    this.emptyState = this.panel.locator('.empty-state');
  }

  private async loginIfNeeded(): Promise<void> {
    const url = this.page.url();
    if (!url.includes('/auth/')) return;

    console.log('Login page detected, authenticating...');
    await this.page.waitForTimeout(2000);

    const usernameInput = this.page.locator('input[name="username"]').first();
    await usernameInput.waitFor({ state: 'visible', timeout: 10000 }).catch(() => {
      console.warn('Login form not found, skipping auth');
    });

    if (HA_USERNAME) {
      await usernameInput.fill(HA_USERNAME).catch(() => {});
    }

    if (HA_PASSWORD) {
      const passwordInput = this.page.locator('input[name="password"]').first();
      await passwordInput.fill(HA_PASSWORD).catch(() => {});

      const loginButton = this.page.getByRole('button', { name: /log in/i });
      await loginButton.click().catch(() => {});

      await this.page.waitForURL(
        (url) => !url.toString().includes('/auth/'),
        { timeout: 15000 }
      ).catch(() => {
        console.warn('Auth navigation timeout, continuing anyway');
      });
      await this.page.waitForTimeout(2000);
    }
  }

  async goto(): Promise<void> {
    try {
      await this.page.goto(`${HA_URL}/vulcan-brownout`, {
        waitUntil: 'domcontentloaded',
        timeout: 20000,
      });
    } catch (e) {
      console.warn('Navigation error:', (e as any).message || e);
    }

    await this.page.waitForTimeout(1000);

    if (this.page.url().includes('/auth/')) {
      await this.loginIfNeeded();
    }

    if (!this.page.url().includes('/vulcan-brownout')) {
      try {
        await this.page.goto(`${HA_URL}/vulcan-brownout`, {
          waitUntil: 'domcontentloaded',
          timeout: 20000,
        });
      } catch (e) {
        console.warn('Could not navigate to panel');
      }
      await this.page.waitForTimeout(1000);
    }

    await this.panel.waitFor({ state: 'attached', timeout: 20000 }).catch(() => {
      console.log('Panel element not yet attached');
    });
  }

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
      const name = await item.locator('td:nth-child(2)').textContent();
      if (name) names.push(name.trim());
    }
    return names;
  }

  async getDeviceLevels(): Promise<number[]> {
    const items = await this.deviceItems.all();
    const levels: number[] = [];
    for (const item of items) {
      const text = await item.locator('td:nth-child(5)').textContent();
      if (text) {
        const match = text.match(/\d+/);
        if (match) levels.push(parseInt(match[0]));
      }
    }
    return levels;
  }

  async getDeviceAtIndex(index: number): Promise<Locator> {
    return this.deviceItems.nth(index);
  }

  async getDeviceLevelAtIndex(index: number): Promise<number | null> {
    const text = await this.deviceItems.nth(index).locator('td:nth-child(5)').textContent();
    if (text) {
      const match = text.match(/\d+/);
      if (match) return parseInt(match[0]);
    }
    return null;
  }

  async getPanelBackgroundColor(): Promise<string> {
    return this.panel.locator('.battery-panel').evaluate((el) =>
      window.getComputedStyle(el).backgroundColor,
    );
  }

  async screenshot(name: string): Promise<Buffer> {
    return this.page.screenshot({ path: `test-results/${name}.png`, fullPage: true });
  }

  async verifyAccessible(): Promise<void> {
    await expect(this.panel).toBeVisible();
    await expect(this.title).toBeVisible();
  }
}
