// Automated voice E2E: real Chrome + fake microphone fed from a WAV file.
// Asserts: mic -> 16 kHz PCM16 frames reach /ws/live (through the UI origin), a user
// transcript appears, Leda's 24 kHz audio arrives and is scheduled for playback, the
// canvas updates from the contract; reports speech-end -> first audio and -> canvas.
//
// Usage: URL=http://localhost:3200 WAV=/abs/q.wav [EXPECT_TURNS=1] [OUT=dir] node scripts/voice_e2e_test.js
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const URL = process.env.URL || 'http://localhost:3200';
const WAV = process.env.WAV;
const EXPECT_TURNS = parseInt(process.env.EXPECT_TURNS || '1', 10);
const OUT = process.env.OUT || path.join(__dirname, '..', 'screenshots', 'voice');
const TIMEOUT = parseInt(process.env.TIMEOUT_MS || '90000', 10);
if (!WAV || !fs.existsSync(WAV)) {
  console.error('Set WAV=/absolute/path/to/question.wav');
  process.exit(2);
}
fs.mkdirSync(OUT, { recursive: true });

(async () => {
  const browser = await chromium.launch({
    executablePath: '/usr/bin/google-chrome',
    args: [
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
      `--use-file-for-fake-audio-capture=${WAV}%noloop`,
      '--autoplay-policy=no-user-gesture-required',
      '--disable-audio-output',
    ],
  });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, permissions: ['microphone'] });
  const page = await ctx.newPage();
  const consoleErrors = [];
  const wsFrames = { sentAudio: 0, sentBytes: 0, recvAudio: 0, recvBytes: 0, types: {} };
  page.on('console', (m) => m.type() === 'error' && consoleErrors.push(m.text()));
  page.on('pageerror', (e) => consoleErrors.push('pageerror ' + e.message));
  page.on('websocket', (ws) => {
    if (!ws.url().includes('/ws/live')) return;
    console.log('[ws] opened', ws.url().replace(/session_id=[^&]+/, 'session_id=…'));
    ws.on('framesent', (f) => {
      try {
        const m = JSON.parse(f.payload);
        if (m.type === 'audio') {
          wsFrames.sentAudio++;
          wsFrames.sentBytes += Math.floor((m.data.length * 3) / 4);
        } else console.log('[ws] sent', m.type);
      } catch {}
    });
    ws.on('framereceived', (f) => {
      try {
        const m = JSON.parse(f.payload);
        wsFrames.types[m.type] = (wsFrames.types[m.type] || 0) + 1;
        if (m.type === 'audio') {
          wsFrames.recvAudio++;
          wsFrames.recvBytes += Math.floor((m.data.length * 3) / 4);
        } else if (m.type !== 'agent_transcript') console.log('[ws] recv', m.type, (m.text || m.message || (m.contract && m.contract.visual && m.contract.visual.title) || '').toString().slice(0, 90));
      } catch {}
    });
  });

  await page.goto(URL, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="connection-pill"]:has-text("Live")', { timeout: 15000 });
  const titleBefore = await page.locator('[data-testid="canvas-title"]').textContent().catch(() => null);

  const t0 = Date.now();
  await page.click('[data-testid="mic-button"]');
  await page.waitForSelector('[data-testid="voice-orb"][data-state="listening"]', { timeout: 8000 });
  await page.waitForTimeout(2500);
  console.log('[ui] after 2.5s listening, wsFrames.sentAudio =', wsFrames.sentAudio, 'sentBytes =', wsFrames.sentBytes);
  await page.screenshot({ path: `${OUT}/voice_listening.png` });

  // 1) user transcript bubble (spoken)
  // After ~8.5s of WAV playback, if server-side VAD hasn't auto-finalized the fake stream,
  // toggle mic off to send explicit audio_stream_end.
  try {
    await page.waitForSelector('[data-testid="user-turn"][data-voice="true"]', { timeout: 9000 });
  } catch {
    console.log('[ui] clicking mic-button to finalize fake audio stream (audio_stream_end)...');
    await page.click('[data-testid="mic-button"]');
    await page.waitForSelector('[data-testid="user-turn"][data-voice="true"]', { timeout: TIMEOUT });
  }
  const userText = await page.locator('[data-testid="user-turn"][data-voice="true"]').first().innerText();
  console.log('[ui] user transcript:', userText.split('\n')[0]);

  // 2) agent audio + canvas update
  await page.waitForFunction(() => (window.__yukti?.engine?.getStats()?.chunks || 0) > 0, null, { timeout: TIMEOUT });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${OUT}/voice_speaking.png` });
  await page.waitForFunction((n) => (window.__yukti?.telemetry?.turns?.length || 0) >= n, EXPECT_TURNS, { timeout: TIMEOUT + 60000 });
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${OUT}/voice_done.png` });

  const result = await page.evaluate(() => {
    const y = window.__yukti;
    return {
      telemetry: y.telemetry.turns,
      playback: y.engine.getStats(),
      counters: y.client.counters,
      canvasTitle: document.querySelector('[data-testid="canvas-title"]')?.textContent,
      userTurns: [...document.querySelectorAll('[data-testid="user-turn"]')].map((e) => e.innerText.split('\n')[0]),
      agentTurns: [...document.querySelectorAll('[data-testid="agent-turn"]')].map((e) => e.innerText.split('\n')[0].slice(0, 160)),
      chartForm: document.querySelector('[data-chart-form]')?.getAttribute('data-chart-form'),
    };
  });

  const checks = {
    'mic frames sent to /ws/live (via UI origin)': wsFrames.sentAudio > 0,
    'user transcript shown in thread': result.userTurns.length > 0,
    'agent 24 kHz audio received': wsFrames.recvAudio > 0,
    'agent audio scheduled for playback': result.playback.bytes > 0 && result.playback.scheduledSeconds > 0.5,
    'canvas updated from contract': !!result.canvasTitle && result.canvasTitle !== titleBefore,
    'no console errors': consoleErrors.length === 0,
  };
  console.log('\n=== VOICE E2E RESULT ===');
  console.log(JSON.stringify({ wav: path.basename(WAV), elapsedMs: Date.now() - t0, wsFrames, ...result, consoleErrors }, null, 1));
  for (const [k, v] of Object.entries(checks)) console.log(`${v ? 'PASS' : 'FAIL'}  ${k}`);
  await browser.close();
  process.exit(Object.values(checks).every(Boolean) ? 0 : 1);
})().catch((e) => {
  console.error('VOICE E2E ERROR', e);
  process.exit(1);
});
