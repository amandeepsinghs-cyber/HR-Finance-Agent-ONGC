const { chromium } = require('playwright');
const { spawn } = require('child_process');
const http = require('http');
const path = require('path');

const PORT = 3200;
const SCREENSHOTS_DIR = path.join(__dirname, '../screenshots');

function waitForServer(url, timeoutMs = 30000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const check = () => {
      http.get(url, (res) => {
        if (res.statusCode === 200 || res.statusCode === 304) {
          resolve();
        } else {
          setTimeout(check, 400);
        }
      }).on('error', () => {
        if (Date.now() - start > timeoutMs) {
          reject(new Error(`Server at ${url} did not respond within ${timeoutMs}ms`));
        } else {
          setTimeout(check, 400);
        }
      });
    };
    check();
  });
}

async function run() {
  console.log('--- Starting Yukti AI Smoke Test & Screenshot Capture ---');

  // Spawn Next.js production server
  const server = spawn('npm', ['run', 'start'], {
    cwd: path.join(__dirname, '..'),
    env: { ...process.env, PORT: String(PORT) },
    stdio: 'inherit',
  });

  const cleanup = () => {
    try {
      server.kill('SIGTERM');
    } catch (e) {}
  };

  process.on('exit', cleanup);
  process.on('SIGINT', cleanup);
  process.on('SIGTERM', cleanup);

  try {
    console.log(`Waiting for Next.js server on port ${PORT}...`);
    await waitForServer(`http://localhost:${PORT}`);
    console.log('Server is ready! Launching headless Chromium browser...');

    const browser = await chromium.launch({
      executablePath: '/usr/bin/google-chrome',
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--font-render-hinting=none'],
    });

    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 }, // 16:9 Big screen presentation viewport
      deviceScaleFactor: 1.5, // Crisp high-DPI screenshots
    });

    const page = await context.newPage();
    console.log(`Navigating to http://localhost:${PORT}...`);
    await page.goto(`http://localhost:${PORT}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // Helper to send typed input
    const typeAndSend = async (text) => {
      const input = page.locator('input[placeholder*="Ask question"]');
      await input.fill(text);
      await page.keyboard.press('Enter');
      await page.waitForTimeout(1000);
    };

    // Helper to advance demo
    const pressSpace = async () => {
      await page.keyboard.press('Space');
      await page.waitForTimeout(800);
    };

    // Helper to switch theme
    const toggleTheme = async () => {
      await page.keyboard.press('KeyT');
      await page.waitForTimeout(400);
    };

    console.log('Capturing Light Mode screenshots...');

    // 1. Home with Greeting (Light) - True opening state (orb + greeting + 3 starter chips)
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'home_greeting_light.png') });
    console.log('  ✓ home_greeting_light.png');

    // 2. Advance to C1 Donut (Light) via Spacebar
    await pressSpace();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'c1_donut_light.png') });
    console.log('  ✓ c1_donut_light.png');

    // 3. Refine: E5+ Senior Overstay (Light)
    await typeAndSend('Only E5 and above');
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'refine_light.png') });
    console.log('  ✓ refine_light.png');

    // 4. Refusal Card (Light)
    // Switch to E2 role and ask for Mumbai transfer list
    await page.locator('button:has-text("Role:")').click();
    await page.waitForTimeout(300);
    await page.locator('button:has-text("E2 · HR")').click();
    await page.waitForTimeout(500);
    await typeAndSend('Show me the draft transfer list for Mumbai');
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'refusal_card_light.png') });
    console.log('  ✓ refusal_card_light.png');

    // 5. Document Preview (Light)
    // Switch back to CMD role and ask for Parliament reply
    await page.locator('button:has-text("Role:")').click();
    await page.waitForTimeout(300);
    await page.locator('button:has-text("CMD")').click();
    await page.waitForTimeout(500);
    await typeAndSend('Draft a reply to Parliament question on North East vacancies');
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'document_preview_light.png') });
    console.log('  ✓ document_preview_light.png');

    // 6. Map of Headcount by Asset (Light)
    await typeAndSend('Show geographic map of all work centres and headcount');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'map_light.png') });
    console.log('  ✓ map_light.png');

    // 7. Minimised Voice Orb (Light)
    await page.locator('button[title="Minimise to Voice Orb only"]').click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'minimised_orb_light.png') });
    console.log('  ✓ minimised_orb_light.png');

    // Restore docked
    await page.locator('button[title="Expand Conversation"]').click();
    await page.waitForTimeout(400);

    // 8. Full-Screen Chat (Light)
    await page.locator('button[title="Full Screen View"]').click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'fullscreen_chat_light.png') });
    console.log('  ✓ fullscreen_chat_light.png');

    // Restore docked
    await page.locator('button[title="Restore Docked View"]').click();
    await page.waitForTimeout(400);

    // SWITCH TO DARK MODE
    console.log('Switching to Dark Mode...');
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(800);
    await toggleTheme();
    await page.waitForTimeout(600);

    // 9. Home Greeting in Dark Mode (True opening state)
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'home_greeting_dark.png') });
    console.log('  ✓ home_greeting_dark.png');

    // 10. Advance to C1 Donut in Dark Mode via Spacebar
    await pressSpace();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'c1_donut_dark.png') });
    console.log('  ✓ c1_donut_dark.png');

    // 10. Refine in Dark Mode
    await typeAndSend('Only E5 and above');
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'refine_dark.png') });
    console.log('  ✓ refine_dark.png');

    // 11. Refusal Card in Dark Mode
    await page.locator('button:has-text("Role:")').click();
    await page.waitForTimeout(300);
    await page.locator('button:has-text("E2 · HR")').click();
    await page.waitForTimeout(500);
    await typeAndSend('Show me the draft transfer list for Mumbai');
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'refusal_card_dark.png') });
    console.log('  ✓ refusal_card_dark.png');

    // 12. Document Preview in Dark Mode
    await page.locator('button:has-text("Role:")').click();
    await page.waitForTimeout(300);
    await page.locator('button:has-text("CMD")').click();
    await page.waitForTimeout(500);
    await typeAndSend('Draft a reply to Parliament question on North East vacancies');
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'document_preview_dark.png') });
    console.log('  ✓ document_preview_dark.png');

    // 13. Map in Dark Mode
    await typeAndSend('Show geographic map of all work centres and headcount');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'map_dark.png') });
    console.log('  ✓ map_dark.png');

    // 14. Minimised Orb in Dark Mode
    await page.locator('button[title="Minimise to Voice Orb only"]').click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'minimised_orb_dark.png') });
    console.log('  ✓ minimised_orb_dark.png');

    // Restore docked
    await page.locator('button[title="Expand Conversation"]').click();
    await page.waitForTimeout(400);

    // 15. Full-Screen Chat in Dark Mode
    await page.locator('button[title="Full Screen View"]').click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'fullscreen_chat_dark.png') });
    console.log('  ✓ fullscreen_chat_dark.png');

    await browser.close();
    console.log('--- Smoke test and all 16 screenshot captures completed successfully! ---');
  } catch (err) {
    console.error('Smoke test error:', err);
    process.exitCode = 1;
  } finally {
    cleanup();
  }
}

run();
