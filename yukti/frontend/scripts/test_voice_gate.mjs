#!/usr/bin/env node
// P0.10 (BUG-17/18): unit tests for src/services/voiceGate.ts (mic half-duplex gate, voice barge-in detector,
// speak_id tracker). Self-contained: transpiles the TS module with the local `typescript` package, no network.
// Run: node scripts/test_voice_gate.mjs
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const require = createRequire(import.meta.url);
const ts = require('typescript');
const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const src = readFileSync(join(root, 'src/services/voiceGate.ts'), 'utf8');
const js = ts.transpileModule(src, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
const mod = { exports: {} };
new Function('module', 'exports', js)(mod, mod.exports);
const { micGateOpen, PLAYBACK_TAIL_MS, BargeInDetector, SpeakTracker } = mod.exports;

let passed = 0;
const test = (name, fn) => {
  fn();
  passed += 1;
  console.log(`ok - ${name}`);
};

test('gate closed while Yukti audio plays', () => {
  assert.equal(micGateOpen({ playing: true, nowMs: 1000, tailUntilMs: 0, bargeOpen: false }), false);
});
test('gate stays closed during the 300 ms tail, opens after', () => {
  assert.equal(PLAYBACK_TAIL_MS, 300);
  const end = 5000;
  assert.equal(micGateOpen({ playing: false, nowMs: end + 299, tailUntilMs: end + PLAYBACK_TAIL_MS, bargeOpen: false }), false);
  assert.equal(micGateOpen({ playing: false, nowMs: end + 300, tailUntilMs: end + PLAYBACK_TAIL_MS, bargeOpen: false }), true);
});
test('deliberate barge-in re-opens the gate even while playing', () => {
  assert.equal(micGateOpen({ playing: true, nowMs: 1000, tailUntilMs: 9e9, bargeOpen: true }), true);
});
test('idle mic (nothing playing, no tail) is open', () => {
  assert.equal(micGateOpen({ playing: false, nowMs: 1000, tailUntilMs: 0, bargeOpen: false }), true);
});

test('echo at the old trigger level (0.55 for 3 s) never barges in', () => {
  const d = new BargeInDetector();
  let fired = false;
  for (let t = 0; t < 3000; t += 50) fired = d.update(0.55, 0.5, true, 50) || fired;
  assert.equal(fired, false);
});
test('loud playback raises the bar: 0.7 mic with 0.9 playback level does not fire', () => {
  const d = new BargeInDetector();
  let fired = false;
  for (let t = 0; t < 2000; t += 50) fired = d.update(0.7, 0.9, true, 50) || fired;
  assert.equal(fired, false);
});

// G4 r2 MF-1: replay the reviewer's syllabic echo patterns for 10 s at many periods; they must NEVER fire.
const echoPattern = (lo, hi, duty, periodTicks, out, correlatedOut) => (i) => {
  const onTicks = Math.max(1, Math.round(periodTicks * duty));
  const on = i % periodTicks < onTicks;
  return { mic: on ? hi : lo, out: correlatedOut ? (on ? 0.8 : 0.2) : out };
};
const replay = (gen, ms = 10000) => {
  const d = new BargeInDetector();
  let firedAt = -1;
  for (let i = 0; i * 50 < ms; i++) {
    const { mic, out } = gen(i);
    if (d.update(mic, out, true, 50) && firedAt < 0) firedAt = i * 50;
  }
  return firedAt;
};
for (const [lo, hi, duty] of [[0.4, 0.7, 0.5], [0.3, 0.66, 0.34]]) {
  for (const periodTicks of [2, 3, 4, 5, 6, 8, 10, 12, 14, 16]) {
    for (const correlated of [false, true]) {
      test(`echo ${lo}<->${hi} at ${Math.round(duty * 100)}% duty, period ${periodTicks * 50} ms, ${correlated ? 'playback-correlated' : 'out 0.5'}: never fires in 10 s`, () => {
        assert.equal(replay(echoPattern(lo, hi, duty, periodTicks, 0.5, correlated)), -1);
      });
    }
  }
}
test('a short loud burst (200 ms cough/echo spike) does not fire', () => {
  const gen = (i) => ({ mic: i >= 20 && i < 24 ? 0.95 : 0.3, out: 0.4 });
  assert.equal(replay(gen, 3000), -1);
});
test('continuous speech above the threshold fires at ~0.5 s', () => {
  const gen = (i) => ({ mic: i < 20 ? 0.3 : 0.9, out: 0.4 }); // 1 s of echo floor, then the user talks
  const at = replay(gen, 3000);
  assert.ok(at >= 1000 + 400 && at <= 1000 + 550, `fired at ${at}`); // 9 of 10 ticks loud = 450 ms of speech
});
test('continuous speech with one 50 ms dip still fires', () => {
  const gen = (i) => ({ mic: i < 20 ? 0.3 : i === 24 ? 0.3 : 0.9, out: 0.4 });
  assert.ok(replay(gen, 3000) > 0);
});
test('speech whose level tracks the playback exactly (echo-correlated) does not fire', () => {
  const gen = (i) => {
    const out = 0.3 + 0.6 * Math.abs(Math.sin(i / 3));
    return { mic: Math.min(0.98, out + 0.3), out };
  };
  assert.equal(replay(gen, 10000), -1);
});
test('nothing fires when no audio is playing', () => {
  const d = new BargeInDetector();
  let fired = false;
  for (let t = 0; t < 2000; t += 50) fired = d.update(0.95, 0, false, 50) || fired;
  assert.equal(fired, false);
});

test('speak turn: Live transcripts are dropped until its own turn_complete', () => {
  const s = new SpeakTracker();
  s.userTurn();
  const id = s.begin();
  assert.equal(s.acceptAgentTranscript(), false);
  s.complete('some-other-speak'); // stale completion of an older speak never ends this one
  assert.equal(s.activeId(), id);
  s.complete(id);
  assert.equal(s.activeId(), null);
  assert.equal(s.acceptAgentTranscript(), false, 'late chunks after turn_complete are dropped');
  s.userTurn();
  assert.equal(s.acceptAgentTranscript(), true, 'next voice turn re-opens transcripts');
});
test('server interruption ends the speak; a newer speak is unaffected by an older id', () => {
  const s = new SpeakTracker();
  const a = s.begin();
  const b = s.begin();
  s.interrupted(a);
  assert.equal(s.activeId(), b);
  s.interrupted(b);
  assert.equal(s.activeId(), null);
});
test('reset on WS close/error clears a stuck speak (MF-2)', () => {
  const s = new SpeakTracker();
  s.begin();
  assert.equal(s.acceptAgentTranscript(), false);
  s.reset();
  assert.equal(s.activeId(), null);
  assert.equal(s.acceptAgentTranscript(), true);
});
test('normal voice turn: transcripts accepted between user turn and turn_complete', () => {
  const s = new SpeakTracker();
  s.userTurn();
  assert.equal(s.acceptAgentTranscript(), true);
  s.complete(null);
  assert.equal(s.acceptAgentTranscript(), false);
});

console.log(`\n${passed} passed`);
