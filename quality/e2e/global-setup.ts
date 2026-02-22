/**
 * Global setup: Authentication via HA login form
 * Logs in once, saves browser state for all test contexts.
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
const AUTH_FILE = path.join(__dirname, 'playwright', '.auth', 'auth.json');

export default async function globalSetup(config: FullConfig) {
  const authDir = path.dirname(AUTH_FILE);
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true });
  }

  // For mocked tests, we don't need real authentication
  // Just create a minimal auth file
  if (!fs.existsSync(AUTH_FILE)) {
    console.log('Creating minimal auth state for mocked tests...');
    const minimalAuth = {
      cookies: [],
      origins: [
        {
          origin: HA_URL,
          localStorage: [
            {
              name: 'hassio_user',
              value: 'test-user'
            }
          ]
        }
      ]
    };
    fs.writeFileSync(AUTH_FILE, JSON.stringify(minimalAuth, null, 2));
    console.log(`Auth state created at ${AUTH_FILE}`);
    return;
  }

  // Reuse existing auth
  const ageMs = Date.now() - fs.statSync(AUTH_FILE).mtime.getTime();
  console.log(`Using existing auth (${Math.round(ageMs / 60000)} min old)`);
}
