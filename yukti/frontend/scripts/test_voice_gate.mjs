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
test('a short loud burst (200 ms cough/echo spike) does not fire', () => {
  const d = new BargeInDetector();
  let fired = false;
  for (let t = 0; t < 1000; t += 50) fired = d.update(0.3, 0.4, true, 50) || fired; // learn echo floor
  for (let t = 0; t < 200; t += 50) fired = d.update(0.95, 0.4, true, 50) || fired;
  for (let t = 0; t < 600; t += 50) fired = d.update(0.3, 0.4, true, 50) || fired;
  assert.equal(fired, false);
});
test('sustained clearly-louder speech fires at ~0.4 s', () => {
  const d = new BargeInDetector();
  for (let t = 0; t < 1000; t += 50) d.update(0.3, 0.4, true, 50);
  let firedAt = -1;
  let count = 0;
  for (let t = 50; t <= 1000; t += 50) {
    if (d.update(0.9, 0.4, true, 50)) {
      count += 1;
      if (firedAt < 0) firedAt = t;
    }
  }
  assert.equal(firedAt, 400);
  assert.ok(count >= 1);
});
test('speech with syllable dips still fires (leaky counter)', () => {
  const d = new BargeInDetector();
  let fired = false;
  for (let i = 0; i < 30 && !fired; i += 1) fired = d.update(i % 4 === 3 ? 0.2 : 0.9, 0.3, true, 50);
  assert.equal(fired, true);
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
test('normal voice turn: transcripts accepted between user turn and turn_complete', () => {
  const s = new SpeakTracker();
  s.userTurn();
  assert.equal(s.acceptAgentTranscript(), true);
  s.complete(null);
  assert.equal(s.acceptAgentTranscript(), false);
});

console.log(`\n${passed} passed`);
