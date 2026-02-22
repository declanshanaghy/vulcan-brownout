/**
 * Debug test for vulcan-brownout-panel rendering
 * Simplified to avoid navigation context issues
 */

import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import * as dotenv from 'dotenv';

// Load credentials
dotenv.config({ path: path.join(__dirname, '..', '.env.test') });
const HA_USERNAME = process.env.HA_USERNAME || 'sprocket';
const HA_PASSWORD = process.env.HA_PASSWORD || '';
const HA_URL = process.env.HA_URL || 'http://homeassistant.lan:8123';
const PANEL_URL = process.env.PANEL_URL || '/vulcan-brownout';

// Ensure output directory exists
const outputDir = path.join(__dirname, '..', 'debug-output');
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

test('Debug: vulcan-brownout-panel rendering', async ({ page, context }) => {
  const consoleLogs: Array<{ type: string; text: string; timestamp: string }> = [];
  const jsErrors: Array<{ message: string; stack?: string; timestamp: string }> = [];

  // Capture console messages
  page.on('console', (msg) => {
    const timestamp = new Date().toISOString();
    consoleLogs.push({
      type: msg.type(),
      text: msg.text(),
      timestamp,
    });
    console.log(`[${msg.type().toUpperCase()}] ${msg.text()}`);
  });

  // Capture uncaught exceptions
  page.on('pageerror', (error) => {
    const timestamp = new Date().toISOString();
    jsErrors.push({
      message: error.message,
      stack: error.stack,
      timestamp,
    });
    console.error(`[JS ERROR] ${error.message}`);
    if (error.stack) {
      console.error(error.stack);
    }
  });

  console.log(`\n=== Starting Debug Test ===`);
  console.log(`Target URL: ${HA_URL}${PANEL_URL}`);

  // Navigate
  console.log('Step 1: Navigating to panel...');
  await page.goto(`${HA_URL}${PANEL_URL}`, { 
    waitUntil: 'domcontentloaded',
    timeout: 30000 
  });
  
  const currentUrl = page.url();
  console.log(`Current URL: ${currentUrl}`);
  await page.waitForTimeout(3000);

  // Check if on auth page
  if (currentUrl.includes('/auth/')) {
    console.log('Step 2: On auth page, logging in...');
    const usernameInput = page.locator('input[name="username"]').first();
    await usernameInput.waitFor({ state: 'visible', timeout: 10000 });
    await usernameInput.fill(HA_USERNAME);
    console.log('Username filled');

    const passwordInput = page.locator('input[name="password"]').first();
    await passwordInput.fill(HA_PASSWORD);
    console.log('Password filled');

    const loginButton = page.getByRole('button', { name: /log in/i });
    await loginButton.click();
    console.log('Login button clicked, waiting for navigation...');

    await page.waitForURL((url) => !url.toString().includes('/auth/'), { timeout: 15000 });
    await page.waitForTimeout(3000);
    console.log(`Navigated to: ${page.url()}`);
  } else {
    console.log('Step 2: Already authenticated');
  }

  // Capture HTML early
  console.log('Step 3: Capturing page HTML...');
  const html = await page.content();
  const htmlPath = path.join(outputDir, 'page-content.html');
  fs.writeFileSync(htmlPath, html, 'utf-8');
  console.log(`HTML saved (${html.length} bytes)`);

  // Check for elements
  console.log('Step 4: Checking for DOM elements...');
  const haShellCount = await page.locator('home-assistant').count();
  const panelCount = await page.locator('vulcan-brownout-panel').count();
  
  console.log(`HA shell elements: ${haShellCount}`);
  console.log(`vulcan-brownout-panel elements: ${panelCount}`);

  // Get page structure
  console.log('Step 5: Analyzing page structure...');
  try {
    const structureInfo = await page.evaluate(() => {
      const info: any = {};
      info.documentTitle = document.title;
      info.bodyClass = document.body.className;
      info.htmlLang = document.documentElement.lang;
      
      info.hasHomeAssistant = !!document.querySelector('home-assistant');
      info.hasPanelElement = !!document.querySelector('vulcan-brownout-panel');
      
      // Check for root elements
      const rootElements = Array.from(document.children).map(el => ({
        tag: el.tagName.toLowerCase(),
        class: el.className,
      }));
      info.rootElements = rootElements;
      
      // Get all custom elements currently in DOM
      const allElements = document.querySelectorAll('*');
      const customTags = new Set<string>();
      allElements.forEach(el => {
        if (el.tagName.includes('-')) {
          customTags.add(el.tagName.toLowerCase());
        }
      });
      info.foundCustomElements = Array.from(customTags);
      
      // Get undefined elements
      const undefinedElements = new Set<string>();
      document.querySelectorAll(':not(:defined)').forEach((el) => {
        undefinedElements.add(el.tagName.toLowerCase());
      });
      info.undefinedElements = Array.from(undefinedElements);
      
      return info;
    });
    
    console.log('\n=== Page Structure ===');
    console.log(JSON.stringify(structureInfo, null, 2));
    console.log('=== End Structure ===\n');
    
    const structurePath = path.join(outputDir, 'page-structure.json');
    fs.writeFileSync(structurePath, JSON.stringify(structureInfo, null, 2), 'utf-8');
  } catch (e) {
    console.error('Could not analyze structure:', e);
  }

  // Take screenshot
  console.log('Step 6: Taking screenshot...');
  const screenshotPath = path.join(outputDir, 'debug-screenshot.png');
  await page.screenshot({ 
    path: screenshotPath, 
    fullPage: true 
  });
  console.log(`Screenshot saved`);

  // Log HTML snippet if panel tag found
  if (html.includes('vulcan-brownout-panel')) {
    const panelIndex = html.indexOf('vulcan-brownout-panel');
    const start = Math.max(0, panelIndex - 300);
    const end = Math.min(html.length, panelIndex + 1500);
    const snippet = html.substring(start, end);
    console.log('\n=== HTML snippet around panel ===');
    console.log(snippet);
    console.log('=== End snippet ===\n');
  } else {
    console.log('\nWARNING: vulcan-brownout-panel tag NOT found in HTML');
    
    // Show what's in the body instead
    const bodyStart = html.indexOf('<body');
    const bodyEnd = html.indexOf('</body>') + 7;
    if (bodyStart > -1 && bodyEnd > bodyStart) {
      const bodyContent = html.substring(bodyStart, Math.min(bodyEnd, bodyStart + 2000));
      console.log('\n=== Body content (first 2000 chars) ===');
      console.log(bodyContent);
      console.log('=== End body ===\n');
    }
  }

  // Save diagnostic data
  console.log('Step 7: Saving diagnostic data...');
  fs.writeFileSync(
    path.join(outputDir, 'console-logs.json'),
    JSON.stringify(consoleLogs, null, 2),
    'utf-8'
  );
  fs.writeFileSync(
    path.join(outputDir, 'js-errors.json'),
    JSON.stringify(jsErrors, null, 2),
    'utf-8'
  );

  console.log('\n=== SUMMARY ===');
  console.log(`Console messages: ${consoleLogs.length}`);
  console.log(`JS errors: ${jsErrors.length}`);
  console.log(`HA shell found: ${haShellCount > 0 ? 'YES' : 'NO'}`);
  console.log(`Panel found: ${panelCount > 0 ? 'YES' : 'NO'}`);
  console.log(`HTML size: ${html.length} bytes`);
  console.log('\nOutput files:');
  fs.readdirSync(outputDir).forEach(file => {
    const stat = fs.statSync(path.join(outputDir, file));
    console.log(`  - ${file} (${stat.size} bytes)`);
  });
  console.log('=== END SUMMARY ===\n');

  // This test should not fail on missing panel - we're just diagnosing
  expect(true).toBe(true);
});
