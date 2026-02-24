/**
 * Global setup for non-mock tests: Real HA authentication
 * Launches a browser, performs the HA login form flow, and saves
 * authenticated browser state for all test contexts.
 *
 * Runs for TARGET_ENV=docker and TARGET_ENV=staging.
 *
 * Config resolution order:
 *  1. YAML config via ConfigLoader (primary source, env-specific)
 *  2. quality/e2e/.env.test  (local override, gitignored)
 *  3. Process environment variables
 *
 * Auth state is saved per environment:
 *  - docker:  playwright/.auth/docker-auth.json
 *  - staging: playwright/.auth/staging-auth.json
 */

import { chromium, FullConfig } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { spawnSync } from 'child_process';
import * as dotenv from 'dotenv';

const repoRoot = path.resolve(__dirname, '..', '..');
const pythonBin = path.join(repoRoot, 'quality', 'venv', 'bin', 'python');
const targetEnv = (process.env.TARGET_ENV || 'staging') as 'docker' | 'staging';

// Map TARGET_ENV to ConfigLoader arguments
const configLoaderEnv = targetEnv === 'docker' ? 'docker' : 'staging';
const configLoaderBaseDir = targetEnv === 'docker' ? 'development/environments' : 'quality/environments';

// Auth file is per environment
const AUTH_FILE = path.join(__dirname, 'playwright', '.auth', `${targetEnv}-auth.json`);

// 1. Load YAML config via ConfigLoader (primary source)
if (!process.env.HA_USERNAME) {
  if (!fs.existsSync(pythonBin)) {
    throw new Error(
      'quality/venv/ not found.\n' +
      'Run: ansible-playbook quality/ansible/setup.yml\n' +
      '  or: python3 -m venv quality/venv && quality/venv/bin/pip install -r quality/requirements.txt'
    );
  }

  const script = [
    'import sys, json',
    `sys.path.insert(0, ${JSON.stringify(path.join(repoRoot, 'development', 'scripts'))})`,
    'from config_loader import ConfigLoader',
    `loader = ConfigLoader('${configLoaderEnv}', env_base_dir='${configLoaderBaseDir}')`,
    'print(json.dumps(loader.get_env_vars()))',
  ].join('\n');

  const result = spawnSync(pythonBin, ['-c', script], {
    cwd: repoRoot,
    encoding: 'utf8',
  });

  if (result.error) {
    throw new Error(`Failed to invoke quality/venv Python: ${result.error.message}`);
  }
  if (result.status !== 0) {
    throw new Error(
      `ConfigLoader failed (exit ${result.status}):\n${result.stderr || '(no stderr)'}\n` +
      `Check ${configLoaderBaseDir}/${configLoaderEnv}/vulcan-brownout-config.yaml and vulcan-brownout-secrets.yaml`
    );
  }

  const cfg: Record<string, string> = JSON.parse(result.stdout.trim());
  for (const [k, v] of Object.entries(cfg)) {
    if (v && !process.env[k]) {
      process.env[k] = v;
    }
  }
  console.log(`Loaded ${targetEnv} config from ${configLoaderBaseDir}/${configLoaderEnv}/ YAML`);
}

// 2. Local .env.test override (optional, gitignored — for one-off local tweaks)
dotenv.config({ path: path.join(__dirname, '.env.test'), override: false });

const HA_URL = process.env.HA_URL || (targetEnv === 'docker' ? 'http://localhost:8123' : 'http://homeassistant.lan:8123');
const HA_USERNAME = process.env.HA_USERNAME || '';
const HA_PASSWORD = process.env.HA_PASSWORD || '';

export default async function globalSetup(config: FullConfig) {
  const authDir = path.dirname(AUTH_FILE);
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true });
  }

  // Reuse existing auth if fresh (< 30 minutes old)
  if (fs.existsSync(AUTH_FILE)) {
    const ageMs = Date.now() - fs.statSync(AUTH_FILE).mtime.getTime();
    if (ageMs < 30 * 60 * 1000) {
      console.log(`Reusing ${targetEnv} auth (${Math.round(ageMs / 60000)} min old)`);
      return;
    }
    console.log(`${targetEnv} auth expired, re-authenticating...`);
  }

  if (!HA_USERNAME || !HA_PASSWORD) {
    throw new Error(
      `${targetEnv} tests require HA_USERNAME and HA_PASSWORD.\n` +
      `Set them in ${configLoaderBaseDir}/${configLoaderEnv}/vulcan-brownout-secrets.yaml`
    );
  }

  console.log(`Performing real HA login for ${targetEnv} tests (${HA_URL})...`);

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
      ).catch(async (err) => {
        const screenshotPath = path.join(__dirname, 'playwright', '.auth', `${targetEnv}-login-failure.png`);
        await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
        console.error(`Login failed — screenshot saved to ${screenshotPath}`);
        console.error(`Current URL: ${page.url()}`);
        const bodyText = await page.locator('body').innerText().catch(() => '(could not read body)');
        console.error(`Page text: ${bodyText.slice(0, 500)}`);
        throw err;
      });

      // Wait for HA to fully load after login
      await page.waitForTimeout(3000);
      console.log('Login successful');
    } else {
      console.log('No login required (already authenticated or no auth configured)');
    }

    // Save authenticated browser state
    await context.storageState({ path: AUTH_FILE });
    console.log(`${targetEnv} auth saved to ${AUTH_FILE}`);
  } finally {
    await browser.close();
  }
}
