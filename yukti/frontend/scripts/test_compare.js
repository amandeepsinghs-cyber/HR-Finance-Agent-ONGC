#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { chromium } = require('playwright');

const PORT = process.env.PORT || 3312;
const BASE_URL = `http://localhost:${PORT}/design-system/compare`;
const SHOTS_DIR = '/usr/local/google/home/amandeepsinghs/.gemini/jetski/brain/e78fe9c5-323e-45b3-88d4-49ebd381ba24/scratch/compare_shots';

fs.mkdirSync(SHOTS_DIR, { recursive: true });

async function run() {
  const consoleErrors = [];

  const launchOpts = {
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--font-render-hinting=none'],
  };
  if (fs.existsSync('/usr/bin/google-chrome')) {
    launchOpts.executablePath = '/usr/bin/google-chrome';
  }

  const browser = await chromium.launch(launchOpts);
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1.5,
  });

  const page = await context.newPage();

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  page.on('pageerror', (err) => {
    consoleErrors.push(err.message);
  });

  try {
    await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForSelector('[data-testid="compare-view"]', { timeout: 10000 });
    await page.waitForSelector('[data-testid="compare-chart"] canvas', { timeout: 10000 });
    await page.waitForTimeout(600); // allow chart entrance animation

    // 1. Verify Entity Labels
    const labelLocators = page.locator('[data-testid="compare-label"]');
    const labelCount = await labelLocators.count();
    const entityLabels = [];
    for (let i = 0; i < labelCount; i++) {
      entityLabels.push((await labelLocators.nth(i).textContent()).trim());
    }

    assert(entityLabels.includes('Delhi HQ'), 'Entity labels must include "Delhi HQ"');
    assert(entityLabels.includes('Mumbai (Western Offshore)'), 'Entity labels must include "Mumbai (Western Offshore)"');

    // 2. Verify Canvas Present & Visible
    const canvas = page.locator('[data-testid="compare-chart"] canvas');
    const canvasPresent = await canvas.isVisible();
    assert(canvasPresent, 'Chart canvas must be present and visible');

    // 3. Verify Legend Labels
    const legendAttr = await page.locator('[data-testid="compare-legend"]').getAttribute('data-legend-labels');
    const legendLabels = legendAttr ? JSON.parse(legendAttr) : [];
    assert(legendLabels.includes('Delhi HQ'), 'Legend must include "Delhi HQ"');
    assert(legendLabels.includes('Mumbai (Western Offshore)'), 'Legend must include "Mumbai (Western Offshore)"');

    // 4. Capture Light Theme Screenshot
    const lightPath = path.join(SHOTS_DIR, 'compare_light.png');
    await page.screenshot({ path: lightPath, fullPage: true });

    // 5. Toggle to Dark Theme
    const themeBtn = page.locator('[data-testid="compare-theme"]');
    await themeBtn.click();
    await page.waitForTimeout(600); // allow transition and chart re-render

    // 6. Capture Dark Theme Screenshot
    const darkPath = path.join(SHOTS_DIR, 'compare_dark.png');
    await page.screenshot({ path: darkPath, fullPage: true });

    // 7. Verify no console errors
    assert.strictEqual(consoleErrors.length, 0, `Expected 0 console errors, got: ${JSON.stringify(consoleErrors)}`);

    const result = {
      entityLabels,
      legendLabels,
      canvasPresent,
      consoleErrors,
      screenshots: [lightPath, darkPath],
      success: true,
    };

    console.log(JSON.stringify(result, null, 2));
    await browser.close();
    process.exit(0);
  } catch (err) {
    console.error('Test failed with error:', err);
    if (consoleErrors.length > 0) {
      console.error('Console errors logged:', consoleErrors);
    }
    await browser.close();
    process.exit(1);
  }
}

run();
