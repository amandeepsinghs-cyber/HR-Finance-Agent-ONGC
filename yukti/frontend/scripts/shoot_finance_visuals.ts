/**
 * P4.8 (SPEC-09 §4.7) & P4.5 (`dcf_model`): Finance visuals screenshot harness.
 * Renders the 5 finance rubric visuals (`statement`, `waterfall`, `combo`, `sensitivity_grid`, `tornado`)
 * plus `dcf_model` in light + dark at 1440×900 into `docs/reviews/assets/P4_*.png`, asserting 0 console/page errors.
 *
 * Run: npx --yes tsx scripts/shoot_finance_visuals.ts
 */
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ASSETS_DIR = resolve(__dirname, '../../../docs/reviews/assets');
const P45_DIR = resolve(ASSETS_DIR, 'P4.5');
const BASE_URL = process.env.YUKTI_URL || 'http://127.0.0.1:3402';

const VISUALS = ['statement', 'waterfall', 'combo', 'sensitivity_grid', 'tornado'] as const;

async function main() {
  mkdirSync(ASSETS_DIR, { recursive: true });
  mkdirSync(P45_DIR, { recursive: true });

  const browser = await chromium.launch({
    executablePath: '/usr/bin/google-chrome',
    args: ['--no-sandbox', '--disable-gpu'],
  });
  const errors: string[] = [];

  try {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    page.on('console', (m) => {
      if (m.type() === 'error') errors.push(`[console] ${m.text()}`);
    });
    page.on('pageerror', (e) => {
      errors.push(`[pageerror] ${e.message}`);
    });

    for (const v of VISUALS) {
      for (const dark of [false, true]) {
        const theme = dark ? 'dark' : 'light';
        const url = `${BASE_URL}/design-system/finance?v=${v}${dark ? '&dark=1' : ''}`;
        await page.goto(url, { waitUntil: 'networkidle' });
        await page.waitForSelector('[data-testid="answer-card"]', { timeout: 15000 });
        await page.waitForTimeout(800);
        const outPath = resolve(ASSETS_DIR, `P4_${v}_${theme}.png`);
        await page.screenshot({ path: outPath, fullPage: false });
        console.log(`Captured ${outPath}`);
      }
    }

    // Also capture and exercise all 6 tabs of DcfModelCard (P4.5)
    for (const dark of [false, true]) {
      const theme = dark ? 'dark' : 'light';
      const url = `${BASE_URL}/design-system/finance?v=dcf_model${dark ? '&dark=1' : ''}`;
      await page.goto(url, { waitUntil: 'networkidle' });
      await page.waitForSelector('[data-testid="dcf-model-card"]', { timeout: 15000 });
      await page.waitForTimeout(600);
      const outPath = resolve(P45_DIR, `P4_dcf_model_${theme}.png`);
      await page.screenshot({ path: outPath, fullPage: false });
      console.log(`Captured ${outPath}`);

      for (const tabId of ['fcff', 'wacc', 'bridge', 'sensitivity', 'tornado', 'summary']) {
        await page.click(`[data-testid="dcf-tab-${tabId}"]`);
        await page.waitForSelector(`[data-testid="dcf-panel-${tabId}"]`, { timeout: 5000 });
        await page.waitForTimeout(250);
      }
    }

    await ctx.close();
  } finally {
    await browser.close();
  }

  if (errors.length > 0) {
    console.error('Console/page errors detected:', errors);
    process.exit(1);
  }
  console.log('All 10 P4.8 finance rubric screenshots + 2 P4.5 dcf_model screenshots captured with 0 errors.');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
