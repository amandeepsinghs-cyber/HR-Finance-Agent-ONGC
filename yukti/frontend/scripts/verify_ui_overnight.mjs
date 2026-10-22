import { chromium } from 'playwright';

const BASE_URL = process.env.YUKTI_URL || 'http://127.0.0.1:3200';

async function main() {
  const browser = await chromium.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: true,
    args: ['--no-sandbox', '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'],
  });
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();

  const errors = [];
  page.on('pageerror', (err) => errors.push(err.message));

  console.log(`[1] Loading ${BASE_URL}...`);
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="voice-orb"]', { timeout: 15000 });

  // Verify chat input works and triggers Turn 1
  console.log('[2] Submitting Turn 1: "How many employees are here in Ahmedabad?"...');
  const input = page.locator('[data-testid="chat-input"]');
  await input.fill('How many employees are here in Ahmedabad?');
  await input.press('Enter');

  await page.waitForSelector('[data-testid="chart-switcher-toolbar"]', { timeout: 25000 });
  const title1 = await page.locator('[data-testid="canvas-title"]').innerText();
  const body1 = await page.locator('[data-testid="canvas"]').innerText();
  console.log(`[2] Canvas Title: ${title1}`);
  if (!title1.includes('Ahmedabad') || !body1.includes('1,199')) {
    throw new Error(`Unexpected Turn 1 content: ${title1}`);
  }

  // Test interactive Plot View Switcher pills on the Canvas
  for (const kind of ['pie', 'histogram', 'scatter', 'treemap', 'table', 'bar']) {
    console.log(`[3] Clicking interactive plot switcher pill: ${kind}...`);
    // U4.3: secondary chart types live in the "More" menu
    if (!(await page.locator(`[data-testid="plot-switch-${kind}"]`).isVisible())) await page.locator('[data-testid="plot-switch-more"]').click();
    await page.locator(`[data-testid="plot-switch-${kind}"]`).click();
    await page.waitForTimeout(350);
  }

  // Submit Turn 2 follow-up: "Break it down by discipline"
  console.log('[4] Submitting Turn 2 follow-up: "Break it down by discipline"...');
  await input.fill('Break it down by discipline');
  await input.press('Enter');
  await page.waitForTimeout(2500);
  const title2 = await page.locator('[data-testid="canvas-title"]').innerText();
  console.log(`[4] Follow-up Canvas Title: ${title2}`);
  if (!title2.includes('Ahmedabad') || !title2.includes('Discipline')) {
    throw new Error(`Multi-turn context lost on Turn 2: ${title2}`);
  }

  // Submit Turn 3 follow-up: "Draw a histogram of employee ages"
  console.log('[5] Submitting Turn 3 follow-up: "Draw a histogram of employee ages"...');
  await input.fill('Draw a histogram of employee ages');
  await input.press('Enter');
  await page.waitForSelector('[data-chart-form="histogram"]', { timeout: 20000 });
  const title3 = await page.locator('[data-testid="canvas-title"]').innerText();
  console.log(`[5] Histogram Canvas Title: ${title3}`);

  // Submit Turn 4 follow-up: "Draft a briefing note on this"
  console.log('[6] Submitting Turn 4 follow-up: "Draft a briefing note on this"...');
  await input.fill('Draft a briefing note on this');
  await input.press('Enter');
  await page.waitForSelector('[data-visual-type="document"]', { timeout: 20000 });
  const title4 = await page.locator('[data-testid="canvas-title"]').innerText();
  console.log(`[6] Document Canvas Title: ${title4}`);

  if (errors.length > 0) {
    throw new Error(`Page runtime errors: ${errors.join('; ')}`);
  }

  console.log('PLAYWRIGHT UI E2E VERIFICATION PASSED!');
  await browser.close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
