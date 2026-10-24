#!/usr/bin/env node
// P4.1 (BUG-08/09/22): parity tests for src/charts/bridge.ts and src/charts/kindPrecedence.ts against the SHARED
// fixtures in yukti/contracts/fixtures (the same files the backend's tests/test_bridge.py and
// tests/test_kind_precedence.py use). Self-contained: transpiles the TS with the local `typescript` package.
// Run: node scripts/test_bridge.mjs
import { readFileSync, readdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const require = createRequire(import.meta.url);
const ts = require('typescript');
const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const contracts = join(root, '..', 'contracts');
const classes = JSON.parse(readFileSync(join(contracts, 'statement_line_classes.json'), 'utf8'));

function load(rel, deps = {}) {
  const src = readFileSync(join(root, rel), 'utf8');
  const js = ts.transpileModule(src, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true } }).outputText;
  const mod = { exports: {} };
  const req = (name) => {
    if (name in deps) return deps[name];
    throw new Error(`unexpected import ${name} in ${rel}`);
  };
  new Function('module', 'exports', 'require', js)(mod, mod.exports, req);
  return mod.exports;
}

const bridgeMod = load('src/charts/bridge.ts', { '@/contracts/generated/statement_line_classes.json': classes });
const { bridge, singleValueError } = bridgeMod;
const { resolveKind } = load('src/charts/kindPrecedence.ts');

let passed = 0;
const test = (name, fn) => {
  fn();
  passed += 1;
  console.log(`ok - ${name}`);
};
const rowsOf = (st) => st.sections.flatMap((s) => s.rows);

// 1. Synthetic P&L fixture: every period bridges and lands on reported PAT within ₹0.5 cr.
const pnl = JSON.parse(readFileSync(join(contracts, 'fixtures/bridge/pnl_fixture_synthetic.json'), 'utf8'));
for (const fy of pnl.periods) {
  for (const gran of ['standard', 'full']) {
    test(`pnl ${fy} (${gran}) ends at reported PAT, typed bars only`, () => {
      const res = bridge(rowsOf(pnl), fy, gran);
      assert.equal(res.ok, true, res.reason);
      const pat = rowsOf(pnl).find((r) => classes.classes[r.line_code] === 'end').values[fy];
      const last = res.bars[res.bars.length - 1];
      assert.equal(last.type, 'total');
      assert.equal(last.value, pat);
      // running sum of deltas from the start bar re-creates every total within tolerance
      let run = res.bars[0].value;
      for (const b of res.bars.slice(1)) {
        if (b.type === 'delta') run += b.value;
        else {
          assert.ok(Math.abs(run - b.value) <= 0.5, `${b.label}: ${run} vs ${b.value}`);
          run = b.value;
        }
      }
      assert.ok(res.bars.every((b) => b.type === 'total' || b.type === 'delta'));
      assert.ok(!res.bars.some((b) => /ebitda|opex\s*&\s*levies/i.test(b.label) && !rowsOf(pnl).some((r) => r.label === b.label)), 'no invented lines');
      assert.ok(!res.bars.some((b) => /^others(\s*\(|$)/i.test(b.label)), "never an unsigned Others bar");
      if (gran === 'full') assert.ok(!res.bars.some((b) => b.merged), 'full granularity never merges');
    });
  }
}

test('standard granularity folds deductions < 2% of revenue into one signed "Other expenses (net)" before PBT', () => {
  const res = bridge(rowsOf(pnl), 'FY26', 'standard');
  const merged = res.bars.filter((b) => b.merged);
  assert.ok(merged.length >= 1);
  for (const m of merged) {
    assert.equal(m.label, classes.merged_deduct_label);
    assert.ok(m.value < 0);
  }
  const iMerged = res.bars.findIndex((b) => b.merged);
  assert.equal(res.bars[iMerged + 1].type, 'total', 'merged bar is flushed immediately before the next subtotal');
});

// 2. Error fixtures: exact codes + reason wording.
for (const f of readdirSync(join(contracts, 'fixtures/bridge')).filter((n) => n.startsWith('error_'))) {
  const fx = JSON.parse(readFileSync(join(contracts, 'fixtures/bridge', f), 'utf8'));
  test(`${f} → BridgeError ${fx.expected_error.code}`, () => {
    const res = fx.expected_error.code === 'single_value' ? singleValueError() : bridge(rowsOf(fx), fx.periods?.[0]);
    assert.equal(res.ok, false);
    assert.equal(res.code, fx.expected_error.code);
    assert.ok(res.reason.toLowerCase().includes(fx.expected_error.reason_contains.toLowerCase()), res.reason);
  });
}

// 3. Kind precedence: 30/30 shared utterances.
const kp = JSON.parse(readFileSync(join(contracts, 'fixtures/kind_precedence_30.json'), 'utf8'));
let kpOk = 0;
for (const c of kp.cases) {
  test(`${c.id} "${c.utterance}" → ${c.expected_kind}`, () => {
    assert.equal(resolveKind(c.utterance), c.expected_kind);
    kpOk += 1;
  });
}
assert.equal(kpOk, kp.cases.length);

// 4. Grep guard: no EBITDA / OPEX synthesis left in the chart pipeline.
for (const rel of ['src/charts/plan.ts', 'src/charts/compat.ts', 'src/charts/options.ts']) {
  test(`${rel} has no P&L synthesis`, () => {
    const src = readFileSync(join(root, rel), 'utf8');
    assert.equal(/\b0\.68\b|\brev ?\* ?0\.|\(rev ?\+ ?pbt\) ?\/ ?2|'OPEX & Levies'/.test(src), false);
  });
}

console.log(`\n${passed} passed`);
