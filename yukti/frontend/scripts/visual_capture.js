// Visual capture: drives the UI through key states and screenshots them.
// Usage: URL=http://localhost:3201 OUT=dir MODE=mock|live SIZES=1440x900,1920x1080 node visual_capture.js
const { chromium } = require('playwright');
const fs = require('fs');
const URL = process.env.URL || 'http://localhost:3200';
const OUT = process.env.OUT || './screenshots/after';
const MODE = process.env.MODE || 'mock';
const SIZES = (process.env.SIZES || '1440x900').split(',').map((s) => s.split('x').map(Number));
const ONLY = process.env.ONLY ? process.env.ONLY.split(',') : null;
fs.mkdirSync(OUT, { recursive: true });

const SCENES = [
  { id: 'c1_delhi_tenure', q: 'How many executives have been posted in Delhi for 5 years or more?' },
  { id: 'c1_followup_e5', q: 'Only E5 and above' },
  { id: 'c6_loss_fields', q: 'Which fields or assets were the most profitable and which made losses in FY26?' },
  { id: 'w1_brent60_waterfall', q: 'If Brent falls to $60 per barrel, which fields go into loss?' },
  { id: 'x7_parliament_reply', q: 'Draft a reply to a Parliament question on vacancies in ONGC in the North-East region, category-wise.' },
  { id: 'p1_clause', q: 'What is the minimum tenure at a station, and the maximum cumulative stay in one city?' },
  { id: 'map_headcount', q: 'Show me the geographic distribution of ONGC executives across work centres on a map of India.' },
  { id: 'c10_mou_bullet', q: 'How are we tracking against our MoU targets with MoPNG/DPE for this year?' },
  { id: 'c11_multiples', q: 'Which assets added headcount but lost production over 5 years?' },
  { id: 'f6_receivables', q: 'How old are receivables from oil marketing companies and gas buyers, by customer?' },
  { id: 'h10_table', q: 'Generate an Excel transfer proposal for FY27 using rotation rules.' },
  { id: 'd2_refusal_e2', q: 'Show me the draft transfer list for Mumbai.', persona: 'E2_HR' },
];

async function ask(page, q) {
  const before = await page.locator('[data-testid="agent-turn"], [data-testid="error-turn"]').count();
  await page.fill('[data-testid="chat-input"]', q);
  await page.keyboard.press('Enter');
  const t0 = Date.now();
  await page.waitForFunction(
    (n) => document.querySelectorAll('[data-testid="agent-turn"], [data-testid="error-turn"]').length > n,
    before,
    { timeout: 120000 }
  );
  await page.waitForTimeout(1600); // let charts animate in
  return Date.now() - t0;
}

(async () => {
  const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', args: ['--autoplay-policy=no-user-gesture-required'] });
  const report = [];
  for (const [w, h] of SIZES) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    const errors = [];
    page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
    page.on('pageerror', (e) => errors.push('pageerror ' + e.message));
    page.on('response', (r) => r.status() >= 400 && errors.push(`http ${r.status()} ${r.url()}`));
    await page.goto(`${URL}/${MODE === 'mock' ? '?mock=1' : ''}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1200);
    const tag = `${w}x${h}`;
    if (!ONLY || ONLY.includes('greeting')) await page.screenshot({ path: `${OUT}/greeting_${tag}.png` });
    for (const s of SCENES) {
      if (ONLY && !ONLY.includes(s.id)) continue;
      if (s.persona) {
        await page.locator('[data-testid="persona-button"]').click({ force: true });
        await page.locator(`[data-testid="persona-${s.persona}"]`).click({ force: true });
        await page.waitForTimeout(400);
      }
      const ms = await ask(page, s.q);
      const title = await page.locator('[data-testid="canvas-title"]').textContent().catch(() => '');
      const form = await page.locator('[data-chart-form]').getAttribute('data-chart-form').catch(() => null);
      report.push({ size: tag, scene: s.id, ms, title, form });
      await page.screenshot({ path: `${OUT}/${s.id}_${tag}.png` });
      if (s.persona) {
        await page.locator('[data-testid="persona-button"]').click({ force: true });
        await page.locator('[data-testid="persona-CMD"]').click({ force: true });
      }
    }
    if (!ONLY || ONLY.includes('dark')) {
      await page.locator('[data-testid="theme-toggle"]').click({ force: true });
      await page.waitForTimeout(900);
      await page.screenshot({ path: `${OUT}/dark_${tag}.png` });
      await page.locator('[data-testid="theme-toggle"]').click({ force: true });
    }
    if (!ONLY || ONLY.includes('minimised')) {
      await page.locator('[data-testid="panel-minimise"]').click({ force: true });
      await page.waitForTimeout(900);
      await page.screenshot({ path: `${OUT}/minimised_orb_${tag}.png` });
    }
    report.push({ size: tag, consoleErrors: errors });
    await ctx.close();
  }
  await browser.close();
  console.log(JSON.stringify(report, null, 1));
})();
