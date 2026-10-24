#!/usr/bin/env node
// P4.3 (SPEC-09 §4.2 S1–S9; BUG-38/39): StatementTable + fmtAccounting + legacy adapter tests.
// Renders the component to static HTML with react-dom/server against the shared P&L fixture
// (yukti/contracts/fixtures/bridge/pnl_fixture_synthetic.json — statement-shaped, labelled synthetic).
// Run: node scripts/test_statement.mjs
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const require = createRequire(import.meta.url);
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const root = join(dirname(fileURLToPath(import.meta.url)), '..');

const cache = {};
function load(rel) {
  if (cache[rel]) return cache[rel];
  const src = readFileSync(join(root, rel), 'utf8');
  const js = ts.transpileModule(src, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText;
  const mod = { exports: {} };
  const req = (name) => {
    if (name === 'react' || name === 'react/jsx-runtime') return require(name);
    if (name === '@/charts/format') return load('src/charts/format.ts');
    if (name === './format') return load('src/charts/format.ts');
    if (name.startsWith('./')) return load(`src/charts/${name.slice(2)}.ts`);
    if (name.startsWith('@/contracts/')) return {};
    throw new Error(`unexpected import ${name} in ${rel}`);
  };
  new Function('module', 'exports', 'require', js)(mod, mod.exports, req);
  cache[rel] = mod.exports;
  return mod.exports;
}

const { fmtAccounting } = load('src/charts/format.ts');
const { StatementTable } = load('src/components/renderers/StatementTable.tsx');
const { legacyStatementFromTable, cleanStatementLabel } = load('src/charts/statementAdapter.ts');

let passed = 0;
const test = (name, fn) => {
  fn();
  passed += 1;
  console.log(`ok - ${name}`);
};

// S4/S5 formatter
test('fmtAccounting: Indian grouping, 0 dp ≥ 100, 2 dp below, (neg), null → —', () => {
  assert.equal(fmtAccounting(-1234.4, 'INR_crore'), '(1,234)');
  assert.equal(fmtAccounting(137000, 'INR_crore'), '1,37,000');
  assert.equal(fmtAccounting(45.678, 'INR_crore'), '45.68');
  assert.equal(fmtAccounting(-0.004, 'INR_crore'), '0.00');
  assert.equal(fmtAccounting(null), '—');
  assert.equal(fmtAccounting(undefined), '—');
  assert.equal(fmtAccounting(0), '0.00');
});

const fx = JSON.parse(readFileSync(join(root, '..', 'contracts', 'fixtures', 'bridge', 'pnl_fixture_synthetic.json'), 'utf8'));
const html = renderToStaticMarkup(React.createElement(StatementTable, { statement: fx }));

test('S1: label column is a sticky-styled row header with level indentation', () => {
  assert.match(html, /class="yk-statement__label-cell[^"]*"[^>]*style="padding-left:calc\(0\.9rem \+ 16px\)"/);
  const css = readFileSync(join(root, 'src/app/globals.css'), 'utf8');
  assert.match(css, /\.yk-statement__label-cell\s*\{[^}]*position:\s*sticky/);
});
test('BUG-38: labels wrap and are never truncated (no ellipsis / nowrap on the label column)', () => {
  const css = readFileSync(join(root, 'src/app/globals.css'), 'utf8');
  const block = /\.yk-statement__label-cell\s*\{([^}]*)\}/.exec(css)[1];
  assert.match(block, /white-space:\s*normal/);
  assert.doesNotMatch(block, /text-overflow:\s*ellipsis|nowrap/);
  assert.doesNotMatch(html, /truncate/);
});
test('S2: FY columns latest-first with period labels and a unit row', () => {
  const heads = [...html.matchAll(/data-testid="statement-period"[^>]*>([^<]+)</g)].map((m) => m[1]);
  assert.deepEqual(heads, fx.periods.map((p) => fx.period_labels[p]));
  assert.match(html, /₹ crore/);
});
test('S3/S4: figures rendered with accounting formatter in numeric cells', () => {
  assert.match(html, /class="yk-statement__num text-right" data-testid="statement-cell">1,32,508</);
  const css = readFileSync(join(root, 'src/app/globals.css'), 'utf8');
  assert.match(css, /\.yk-statement__num\s*\{[^}]*tabular-nums/);
});
test('S5: negatives in parentheses, never a minus sign in figures', () => {
  assert.match(html, />\(300\)</); // exceptional items −300 in the fixture
  const cells = [...html.matchAll(/data-testid="statement-cell">([^<]+)</g)].map((m) => m[1]);
  assert.ok(cells.every((c) => !/^[-−]/.test(c)));
});
test('S6: subtotal and total rows carry their kind classes', () => {
  assert.match(html, /yk-statement__row--subtotal" data-testid="statement-row" data-kind="subtotal"/);
  assert.match(html, /yk-statement__row--total" data-testid="statement-row" data-kind="total"/);
});
test('S7: no sorting controls, no inline bars', () => {
  assert.doesNotMatch(html, /aria-sort|sortable|inline-bar|yk-bar/);
});
test('S8: YoY column only when show_yoy', () => {
  assert.match(html, /YoY %/);
  const off = renderToStaticMarkup(React.createElement(StatementTable, { statement: { ...fx, show_yoy: false } }));
  assert.doesNotMatch(off, /YoY %/);
});
test('S9: footnote with unit, basis, source and synthetic marker', () => {
  assert.match(html, /data-testid="statement-footnote"/);
  assert.match(html, /negative values in parentheses/);
  assert.match(html, /Standalone basis/);
  assert.match(html, /Illustrative fixture data|Source:/);
});
test('null values render as — (never 0)', () => {
  const st = JSON.parse(JSON.stringify(fx));
  st.sections[0].rows[0].values.FY22 = null;
  const h = renderToStaticMarkup(React.createElement(StatementTable, { statement: st }));
  assert.match(h, /data-testid="statement-cell">—</);
});

// BUG-39 legacy adapter
test('BUG-39: legacy labels lose invented numbering ("A1.", "I.", "— ") and keep hierarchy by level', () => {
  assert.equal(cleanStatementLabel('A1. Oil & Gas Producing Properties (Net Block)'), 'Oil & Gas Producing Properties (Net Block)');
  assert.equal(cleanStatementLabel('I. Revenue from Operations (Gross)'), 'Revenue from Operations (Gross)');
  assert.equal(cleanStatementLabel('   — Crude Oil Revenue'), 'Crude Oil Revenue');
  assert.equal(cleanStatementLabel('Total Assets'), 'Total Assets');
  const st = legacyStatementFromTable(
    {
      columns: ['line_item', 'note_ref', 'amount_cr', 'prior_fy_cr', 'yoy_delta_cr', 'yoy_change_pct', 'pct_of_revenue'],
      rows: [
        { line_item: 'I. Revenue from Operations (Gross)', amount_cr: 138402, prior_fy_cr: 155517, yoy_change_pct: -11.0 },
        { line_item: '   — Crude Oil Revenue', amount_cr: 100000, prior_fy_cr: 110000, yoy_change_pct: -9.1 },
        { line_item: 'Profit Before Tax', amount_cr: 53016, prior_fy_cr: 50000 },
        { line_item: 'Profit for the Year (PAT)', amount_cr: 40526, prior_fy_cr: 38829 },
      ],
    },
    { metric: 'pnl_statement', fy: 'FY24' },
  );
  assert.deepEqual(st.periods, ['FY24', 'FY23']);
  const labels = st.sections[0].rows.map((r) => r.label);
  assert.ok(labels.every((l) => !/^([A-Z]\d*|[IVX]+)\.\s/.test(l)));
  assert.equal(st.sections[0].rows[1].level, 2);
  assert.equal(st.sections[0].rows[2].kind, 'subtotal');
  assert.equal(st.sections[0].rows[3].kind, 'total');
  assert.equal(st.sections[0].rows[0].values.FY24, 138402);
  assert.equal(legacyStatementFromTable({ columns: ['grade', 'headcount'], rows: [{ grade: 'E1', headcount: 3 }] }, { metric: 'headcount' }), null);
});

console.log(`\n${passed} passed`);
