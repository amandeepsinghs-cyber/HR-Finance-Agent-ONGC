#!/usr/bin/env node
/**
 * P4.7 Playwright check (SPEC-10 AC 4, 6, 7): export menu items download real files with §4.9 names; PNG ≥ 1600 px;
 * SVG is valid markup; typed intents ("download the chart as png", Hindi PDF) export from the latest card;
 * Sheets/Docs show the honest toast and never open a Google URL.
 *
 *   URL=http://127.0.0.1:3402 MODE=mock node tests/export_menu.spec.js     # fixtures: PNG/SVG + intents
 *   URL=http://127.0.0.1:3402 MODE=live node tests/export_menu.spec.js     # + server formats (needs backend)
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const URL = process.env.URL || 'http://127.0.0.1:3402';
const MODE = process.env.MODE || 'mock';
const OUT = process.env.OUT || path.join(process.cwd(), '..', '..', 'docs', 'reviews', 'assets', 'P4.7');
const NAMING = /^yukti_[a-z0-9_-]+_\d{8}-\d{4}(_aggregate)?\.(xlsx|csv|pdf|png|svg|docx|eml)$/;
const CHART_Q = process.env.CHART_Q || 'Show revenue for the last 5 years';
fs.mkdirSync(OUT, { recursive: true });

const results = [];
const record = (name, ok, info = '') => {
  results.push({ name, ok, info });
  console.log(`${ok ? '✓' : '✗'} ${name}${info ? ' — ' + info : ''}`);
};

function pngSize(buf) {
  // IHDR: width/height big-endian at bytes 16..23
  return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
}

async function ask(page, q) {
  const before = await page.locator('[data-testid="agent-turn"], [data-testid="error-turn"]').count();
  await page.fill('[data-testid="chat-input"]', q);
  await page.keyboard.press('Enter');
  await page
    .waitForFunction((n) => document.querySelectorAll('[data-testid="agent-turn"], [data-testid="error-turn"]').length > n, before, {
      timeout: 120000,
    })
    .catch(() => {});
  await page.waitForTimeout(1800);
}

async function menuDownload(page, format) {
  const card = page.locator('[data-testid="answer-card"]').last();
  await card.locator('[data-testid="export-button"]').click();
  const item = card.locator(`[data-testid="export-item-${format}"]`);
  if (!(await item.count())) return { missing: true };
  const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 60000 }), item.click()]);
  const file = path.join(OUT, dl.suggestedFilename());
  await dl.saveAs(file);
  return { file, name: dl.suggestedFilename() };
}

async function intentDownload(page, text) {
  const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 60000 }), ask(page, text)]);
  const file = path.join(OUT, dl.suggestedFilename());
  await dl.saveAs(file);
  return { file, name: dl.suggestedFilename() };
}

(async () => {
  const browser = await chromium.launch({
    executablePath: fs.existsSync('/usr/bin/google-chrome') ? '/usr/bin/google-chrome' : undefined,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true });
  const page = await ctx.newPage();
  const errors = [];
  const googleHits = [];
  page.on('pageerror', (e) => errors.push('pageerror ' + e.message));
  page.on('request', (r) => /docs\.google\.com/.test(r.url()) && googleHits.push(r.url()));
  ctx.on('page', (p) => googleHits.push('popup ' + p.url()));

  await page.goto(`${URL}/${MODE === 'mock' ? '?mock=1' : ''}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  await ask(page, CHART_Q);
  const hasChart = (await page.locator('[data-testid="answer-card"]').last().locator('[data-echart]').count()) > 0;
  record('chart answer on screen', hasChart, CHART_Q);

  // Menu contents
  await page.locator('[data-testid="answer-card"]').last().locator('[data-testid="export-button"]').click();
  const items = await page.locator('[data-testid="answer-card"]').last().locator('[data-testid^="export-item-"]').evaluateAll((els) =>
    els.map((e) => e.getAttribute('data-testid').replace('export-item-', '')),
  );
  record('menu lists 8 items for a chart', JSON.stringify(items) === JSON.stringify(['xlsx', 'csv', 'pdf', 'png', 'svg', 'docx', 'sheets', 'docs']), items.join(','));
  await page.screenshot({ path: path.join(OUT, 'export_menu_open.png') });
  await page.keyboard.press('Escape');

  // PNG via menu
  const png = await menuDownload(page, 'png');
  if (png.file) {
    const { w, h } = pngSize(fs.readFileSync(png.file));
    record('PNG name matches §4.9', NAMING.test(png.name), png.name);
    record('PNG ≥ 1600 px wide', w >= 1600, `${w}×${h}`);
  } else record('PNG menu item', false, 'missing');

  // SVG via menu
  const svg = await menuDownload(page, 'svg');
  if (svg.file) {
    const txt = fs.readFileSync(svg.file, 'utf8');
    record('SVG name matches §4.9', NAMING.test(svg.name), svg.name);
    record('SVG is markup with title text', txt.startsWith('<svg') && txt.includes('</svg>') && /<text[^>]*>[^<]+<\/text>/.test(txt), `${txt.length} bytes`);
  } else record('SVG menu item', false, 'missing');

  // Typed intents
  const ip = await intentDownload(page, 'download the chart as png').catch((e) => ({ err: e.message }));
  record('intent "download the chart as png" → .png', !!ip.name && ip.name.endsWith('.png'), ip.name || ip.err);
  const toast = await page.locator('[role="status"], [data-testid="toast"]').last().textContent().catch(() => '');
  record('ready toast shown after export', /ready|तैयार/i.test(toast || ''), (toast || '').slice(0, 80));

  if (MODE === 'live') {
    for (const f of ['xlsx', 'csv', 'pdf', 'docx']) {
      const r = await menuDownload(page, f).catch((e) => ({ err: e.message }));
      record(`${f} via menu`, !!r.name && NAMING.test(r.name), r.name || r.err);
    }
    for (const f of ['sheets', 'docs']) {
      const r = await menuDownload(page, f).catch((e) => ({ err: e.message }));
      const t = await page.locator('[role="status"], [data-testid="toast"]').last().textContent().catch(() => '');
      record(`${f} downloads a local file`, !!r.name && /\.(xlsx|docx)$/.test(r.name), r.name || r.err);
      record(`${f} honest toast`, /isn't connected yet|जुड़ा नहीं/i.test(t || ''), (t || '').slice(0, 90));
    }
    const hi = await intentDownload(page, 'इसे पीडीएफ में डाउनलोड करो').catch((e) => ({ err: e.message }));
    record('Hindi intent → .pdf', !!hi.name && hi.name.endsWith('.pdf'), hi.name || hi.err);
  }

  record('no docs.google.com request or popup', googleHits.length === 0, googleHits.join(' | '));
  record('no page errors', errors.length === 0, errors.slice(0, 3).join(' | '));
  await page.screenshot({ path: path.join(OUT, `after_exports_${MODE}.png`) });
  await browser.close();
  const failed = results.filter((r) => !r.ok);
  fs.writeFileSync(path.join(OUT, `export_menu_${MODE}.json`), JSON.stringify(results, null, 2));
  console.log(`\n${results.length - failed.length}/${results.length} passed`);
  process.exit(failed.length ? 1 : 0);
})();
