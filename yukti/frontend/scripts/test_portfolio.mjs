#!/usr/bin/env node
// P4.4 (SPEC-09 §4.5–4.6): portfolio batch A — combo, 100% stacked, heatmap, box, gauge — plan + option builders
// against fixtures in src/fixtures/charts/portfolioA, plus compat rules (no fabricated scatter axis, histogram only
// for distributions). Run: node scripts/test_portfolio.mjs
import { readFileSync, readdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const require = createRequire(import.meta.url);
const ts = require('typescript');
const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const cache = {};
const classes = JSON.parse(readFileSync(join(root, 'src/contracts/generated/statement_line_classes.json'), 'utf8'));
function load(rel) {
  if (cache[rel]) return cache[rel];
  const js = ts.transpileModule(readFileSync(join(root, rel), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true },
  }).outputText;
  const mod = { exports: {} };
  cache[rel] = mod.exports;
  const req = (name) => {
    if (name === 'echarts') return require('echarts');
    if (name === '@/contracts/generated/statement_line_classes.json') return classes;
    if (name === '@/design/tokens.json') return JSON.parse(readFileSync(join(root, 'src/design/tokens.json'), 'utf8'));
    if (name.startsWith('../')) return load(`src/${name.slice(3)}.ts`);
    if (name.startsWith('@/contracts/')) return {};
    if (name.startsWith('./')) return load(`src/charts/${name.slice(2)}.ts`);
    if (name.startsWith('@/charts/')) return load(`src/charts/${name.slice('@/charts/'.length)}.ts`);
    throw new Error(`unexpected import ${name} in ${rel}`);
  };
  new Function('module', 'exports', 'require', js)(mod, mod.exports, req);
  cache[rel] = mod.exports;
  return mod.exports;
}
const { planChart } = load('src/charts/plan.ts');
const opts = load('src/charts/options.ts');
const { replot } = load('src/charts/compat.ts');
const { getTokens } = load('src/charts/theme.ts');
const t = getTokens ? getTokens(false) : null;

let passed = 0;
const test = (name, fn) => {
  fn();
  passed += 1;
  console.log(`ok - ${name}`);
};
const fx = (n) => JSON.parse(readFileSync(join(root, 'src/fixtures/charts/portfolioA', n), 'utf8'));

test('tokens available for option builders', () => assert.ok(t && t.accent));

test('combo: value bars on left axis + % line on right axis', () => {
  const f = fx('combo_revenue_margin.json');
  const plan = planChart(f);
  assert.equal(plan.form, 'combo');
  assert.deepEqual(plan.seriesKeys, ['revenue_cr', 'pat_margin_pct']);
  const o = opts.comboOption(plan, t, f.data);
  assert.equal(o.yAxis.length, 2);
  assert.equal(o.series[0].type, 'bar');
  assert.equal(o.series[0].yAxisIndex, 0);
  assert.equal(o.series[1].type, 'line');
  assert.equal(o.series[1].yAxisIndex, 1);
  assert.deepEqual(o.series[1].data, [36.5, 25.0, 29.3, 25.8, 24.8]);
});

test('stacked_100: every category sums to 100%', () => {
  const f = fx('stacked100_grade_mix.json');
  const plan = planChart(f);
  assert.equal(plan.form, 'stacked100');
  const o = opts.stacked100Option(plan, t, f.data);
  for (let i = 0; i < f.data.length; i++) {
    const sum = o.series.reduce((s, ser) => s + ser.data[i], 0);
    assert.ok(Math.abs(sum - 100) < 0.05, `row ${i}: ${sum}`);
  }
});

test('heatmap: category × category cells with visualMap and labels (≤ 120 cells)', () => {
  const f = fx('heatmap_overtime.json');
  const plan = planChart(f);
  assert.equal(plan.form, 'heatmap');
  assert.ok(plan.dim2Key && plan.dim2Key !== plan.dimKey);
  const o = opts.heatmapOption(plan, t, f.data);
  assert.equal(o.series[0].type, 'heatmap');
  assert.equal(o.series[0].data.length, 6);
  assert.equal(o.series[0].label.show, true);
  assert.ok(o.visualMap[0].max > o.visualMap[0].min);
});

test('box: quartiles per group from records, 1.5×IQR outlier as a point', () => {
  const f = fx('box_tenure.json');
  const plan = planChart(f);
  assert.equal(plan.form, 'box');
  const o = opts.boxOption(plan, t, f.data);
  assert.equal(o.series[0].type, 'boxplot');
  assert.equal(o.series[0].data.length, 2);
  assert.deepEqual(o.series[1].data, [[0, 30]]);
  assert.deepEqual(opts.fiveNumber([1, 2, 3, 4, 5]), [1, 2, 3, 4, 5]);
});

test('gauge: single value vs target; without a target → KPI', () => {
  const f = fx('gauge_mou.json');
  const plan = planChart(f);
  assert.equal(plan.form, 'gauge');
  const o = opts.gaugeOption(plan, t, f.data);
  assert.equal(o.series[0].type, 'gauge');
  assert.equal(o.series[0].data[0].value, 87.5);
  const noTarget = planChart({ ...f, data: [{ parameter: 'MoU score', achievement_pct: 87.5 }] });
  assert.equal(noTarget.form, 'kpi');
});

test('compat: scatter with one measure → nearest view + note (no fabricated rank axis)', () => {
  const v = { type: 'chart', mode: 'replace', chart: { kind: 'bar', data: [{ wc: 'Delhi', headcount: 943 }, { wc: 'Mumbai', headcount: 3500 }, { wc: 'Mehsana', headcount: 2100 }], x: 'wc', y: 'headcount' } };
  const r = replot(v, 'scatter');
  assert.equal(r.status, 'alternative');
  assert.match(r.note, /two measures/i);
  assert.ok(!(r.visual.chart?.data || []).some((row) => 'rank' in row || 'benchmark' in row));
});

test('compat: histogram on a time series → line + note', () => {
  const v = { type: 'chart', mode: 'replace', chart: { kind: 'line', data: [{ fy: 'FY22', revenue_cr: 1 }, { fy: 'FY23', revenue_cr: 2 }, { fy: 'FY24', revenue_cr: 3 }], x: 'fy', y: 'revenue_cr' } };
  const r = replot(v, 'histogram');
  assert.equal(r.applied, 'line');
  assert.match(r.note, /distributions/i);
});

test('compat: combo needs two measures; gauge needs a target', () => {
  const one = { type: 'chart', mode: 'replace', chart: { kind: 'bar', data: [{ fy: 'FY22', revenue_cr: 1 }, { fy: 'FY23', revenue_cr: 2 }, { fy: 'FY24', revenue_cr: 3 }] } };
  assert.equal(replot(one, 'combo').status, 'alternative');
  assert.equal(replot(one, 'gauge').status, 'alternative');
});

test('every contract chart kind used by the planner has a renderer case', () => {
  const src = readFileSync(join(root, 'src/components/renderers/ChartRenderer.tsx'), 'utf8');
  for (const form of ['combo', 'stacked100', 'heatmap', 'box', 'gauge']) assert.match(src, new RegExp(`case '${form}'`));
});

console.log(`\n${passed} passed`);
