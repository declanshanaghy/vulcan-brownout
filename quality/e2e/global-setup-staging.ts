/**
 * Global setup for staging tests: Real HA authentication
 * Launches a browser, performs the HA login form flow, and saves
 * authenticated browser state for all staging test contexts.
 */

import { chromium, FullConfig } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import * as dotenv from 'dotenv';

dotenv.config({ path: path.join(__dirname, '.env.test') });
if (!process.env.HA_USERNAME) {
  dotenv.config({ path: path.join(__dirname, '..', '..', '.env') });
}

const HA_URL = process.env.HA_URL || 'http://homeassistant.lan:8123';
const HA_USERNAME = process.env.HA_USERNAME || '';
const HA_PASSWORD = process.env.HA_PASSWORD || '';
const AUTH_FILE = path.join(__dirname, 'playwright', '.auth', 'staging-auth.json');

export default async function globalSetup(config: FullConfig) {
  const authDir = path.dirname(AUTH_FILE);
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true });
  }

  // Reuse existing auth if fresh (< 30 minutes old)
  if (fs.existsSync(AUTH_FILE)) {
    const ageMs = Date.now() - fs.statSync(AUTH_FILE).mtime.getTime();
    if (ageMs < 30 * 60 * 1000) {
      console.log(`Reusing staging auth (${Math.round(ageMs / 60000)} min old)`);
      return;
    }
    console.log('Staging auth expired, re-authenticating...');
  }

  if (!HA_USERNAME || !HA_PASSWORD) {
    throw new Error(
      'Staging tests require HA_USERNAME and HA_PASSWORD in .env.test or root .env. ' +
      'These must be valid credentials for the staging HA instance.'
    );
  }

  console.log(`Performing real HA login for staging tests (${HA_URL})...`);

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await page.goto(`${HA_URL}/vulcan-brownout`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });

    // Wait for potential login redirect
    await page.waitForTimeout(2000);

    if (page.url().includes('/auth/')) {
      console.log('Login page detected, filling credentials...');

      const usernameInput = page.locator('input[name="username"]').first();
      await usernameInput.waitFor({ state: 'visible', timeout: 15000 });
      await usernameInput.fill(HA_USERNAME);

      const passwordInput = page.locator('input[name="password"]').first();
      await passwordInput.fill(HA_PASSWORD);

      const loginButton = page.getByRole('button', { name: /log in/i });
      await loginButton.click();

      await page.waitForURL(
        (url) => !url.toString().includes('/auth/'),
        { timeout: 20000 }
      );

      // Wait for HA to fully load after login
      await page.waitForTimeout(3000);
      console.log('Login successful');
    } else {
      console.log('No login required (already authenticated or no auth configured)');
    }

    // Save authenticated browser state
    await context.storageState({ path: AUTH_FILE });
    console.log(`Staging auth saved to ${AUTH_FILE}`);
  } finally {
    await browser.close();
  }
}
