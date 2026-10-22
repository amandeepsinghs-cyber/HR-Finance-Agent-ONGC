/* Unit tests for the chart compatibility matrix + transform engine (U5.7). Run: npx --yes tsx scripts/test_compat.ts */
import assert from 'node:assert/strict';
import { replot, profile, kindsFor, ReplotKind } from '../src/charts/compat';
import { planChart } from '../src/charts/plan';
import type { VisualContainer } from '../src/contracts/answerContract';
import roster from '../src/fixtures/v2/v2_roster_419.json';
import pnl from '../src/fixtures/v2/v2_finance_pnl.json';
import hc from '../src/fixtures/v2/v2_insights_drilldowns.json';
import grades from '../src/fixtures/c1_donut_by_grade.json';
import combo from '../src/fixtures/c11_combo_headcount_prod.json';

const KINDS: ReplotKind[] = ['bar', 'hbar', 'donut', 'pie', 'line', 'area', 'histogram', 'scatter', 'treemap', 'waterfall', 'funnel', 'grouped_bar', 'stacked_bar', 'bullet', 'table'];

const V = {
  records: (roster as any).visual as VisualContainer,
  categorical_neg: (pnl as any).visual as VisualContainer,
  categorical: (hc as any).visual as VisualContainer,
  ordinal_multi: (grades as any).visual as VisualContainer,
  multi_neg: (combo as any).visual as VisualContainer,
  time: { type: 'chart', mode: 'replace', title: 'Revenue trend', chart: { kind: 'line', x: 'fy', y: 'revenue_cr', unit: '₹ Cr', data: ['FY22', 'FY23', 'FY24', 'FY25', 'FY26'].map((fy, i) => ({ fy, revenue_cr: 100000 + i * 7000 })) } } as VisualContainer,
  distribution: { type: 'chart', mode: 'replace', title: 'Age distribution', chart: { kind: 'histogram', x: 'bin', y: 'count', data: ['21–30', '31–40', '41–50', '51–60'].map((bin, i) => ({ bin, count: [120, 340, 280, 90][i] })) } } as VisualContainer,
  single: { type: 'chart', mode: 'replace', title: 'PAT', chart: { kind: 'bar', x: 'metric', y: 'value', data: [{ metric: 'PAT', value: 38329 }] } } as VisualContainer,
  table_arrays: { type: 'table', mode: 'replace', title: 'Arrays', table: { columns: ['work_centre', 'headcount'], rows: [['Delhi', 4120], ['Mumbai', 3880], ['Dehradun', 2100], ['Vadodara', 1600]] } } as VisualContainer,
};

let passed = 0;
const t = (name: string, fn: () => void) => {
  fn();
  passed++;
};

// 1. Shapes are detected correctly
t('shapes', () => {
  assert.equal(profile(V.records).shape, 'records');
  assert.equal(profile(V.categorical_neg).shape, 'categorical');
  assert.equal(profile(V.categorical_neg).hasNegative, true);
  assert.equal(profile(V.categorical).shape, 'categorical');
  assert.equal(profile(V.ordinal_multi).shape, 'multi_measure');
  assert.equal(profile(V.ordinal_multi).ordinal, true);
  assert.equal(profile(V.time).shape, 'time');
  assert.equal(profile(V.distribution).shape, 'distribution');
  assert.equal(profile(V.single).shape, 'single');
  assert.equal(profile(V.table_arrays).rows[0].work_centre, 'Delhi'); // array rows normalised
});

// 2. Every shape × every kind returns a renderable visual; fallbacks/transforms carry a 1-line note
for (const [shape, vis] of Object.entries(V)) {
  for (const k of KINDS) {
    t(`${shape} × ${k}`, () => {
      const r = replot(vis, k);
      assert.ok(['chart', 'table'].includes(r.visual.type), `${shape}×${k}: type ${r.visual.type}`);
      assert.ok(KINDS.includes(r.applied), `${shape}×${k}: applied ${r.applied}`);
      if (r.status !== 'native') assert.ok(r.note && r.note.length < 140 && !r.note.includes('\n'), `${shape}×${k}: note`);
      if (r.visual.type === 'chart') {
        assert.ok((r.visual.chart?.data || []).length > 0, `${shape}×${k}: empty data`);
        const plan = planChart(r.visual.chart!);
        assert.ok(plan.rows.length > 0, `${shape}×${k}: plan empty`);
        assert.ok(plan.rows.every((row) => Number.isFinite(row.value)), `${shape}×${k}: NaN`);
      } else {
        assert.ok((r.visual.table?.rows || []).length > 0, `${shape}×${k}: empty table`);
      }
      // source is preserved so repeated re-plots never drift
      assert.ok((r.visual as any).source?.rows?.length > 0, `${shape}×${k}: source kept`);
    });
  }
}

// 3. Specific semantics
t('histogram → pie: slices = bins (records)', () => {
  const h = replot(V.records, 'histogram');
  assert.equal(h.applied, 'histogram');
  const hPlan = planChart(h.visual.chart!);
  const pie = replot(h.visual, 'pie');
  assert.equal(pie.applied, 'pie');
  assert.match(pie.note || '', /bins/);
  const pPlan = planChart(pie.visual.chart!);
  assert.deepEqual(pPlan.rows.map((r) => r.label), hPlan.rows.map((r) => r.label));
  assert.deepEqual(pPlan.rows.map((r) => r.value), hPlan.rows.map((r) => r.value));
  assert.equal(pPlan.rows.reduce((s, r) => s + r.value, 0), 419);
});

t('histogram → pie: slices = bins (already-binned distribution keeps order)', () => {
  const pie = replot(V.distribution, 'pie');
  const plan = planChart(pie.visual.chart!);
  assert.deepEqual(plan.rows.map((r) => r.label), ['21–30', '31–40', '41–50', '51–60']);
});

t('pie of losses → diverging bars + note', () => {
  const r = replot(V.categorical_neg, 'pie');
  assert.equal(r.status, 'alternative');
  assert.equal(r.applied, 'hbar');
  assert.match(r.note!, /losses/);
  assert.equal(planChart(r.visual.chart!).form, 'diverging');
});

t('time → pie falls back to columns over time', () => {
  const r = replot(V.time, 'pie');
  assert.equal(r.applied, 'bar');
  assert.match(r.note!, /time/);
});

t('line on nominal categories → bar + note; line on grades is native', () => {
  assert.equal(replot(V.categorical, 'line').applied, 'bar');
  assert.equal(replot(V.ordinal_multi, 'line').status, 'native');
});

t('records → pie counts people by a categorical column', () => {
  const r = replot(V.records, 'donut');
  assert.equal(r.status, 'transform');
  const plan = planChart(r.visual.chart!);
  assert.equal(plan.rows.reduce((s, x) => s + x.value, 0), 419);
});

t('repeated re-plots do not drift (pie → table → bar equals bar)', () => {
  const direct = replot(V.categorical, 'bar');
  const chain = replot(replot(replot(V.categorical, 'pie').visual, 'table').visual, 'bar');
  assert.deepEqual(chain.visual.chart?.data, direct.visual.chart?.data);
});

t('metric selection for multi-measure pie', () => {
  const r = replot(V.ordinal_multi, 'pie', { metric: 'due' });
  assert.equal(r.visual.chart?.value, 'due');
});

t('kindsFor lists all kinds with a status', () => {
  const ks = kindsFor(V.categorical_neg);
  assert.equal(ks.length, KINDS.length);
  assert.equal(ks.find((k) => k.kind === 'pie')?.status, 'alternative');
});

// performance: 2,000-row roster histogram → pie under 50 ms
{
  const big = { type: 'table', mode: 'replace', title: 'Big', table: { columns: ['emp_name', 'grade', 'continuous_stay_years'], rows: Array.from({ length: 2000 }, (_, i) => ({ emp_name: `P${i}`, grade: `E${i % 9}`, continuous_stay_years: 5 + (i % 170) / 10 })) } } as VisualContainer;
  const t0 = performance.now();
  const h = replot(big, 'histogram');
  const p = replot(h.visual, 'pie');
  planChart(p.visual.chart!);
  const ms = performance.now() - t0;
  assert.ok(ms < 50, `took ${ms} ms`);
  passed++;
}

// G4 regressions (U5 review)
t('B2: ordinal histogram draws the existing buckets (prebinned), never re-bins by value', () => {
  const r = replot(V.ordinal_multi, 'histogram');
  assert.equal(r.visual.chart?.prebinned, true);
  const plan = planChart(r.visual.chart!);
  assert.deepEqual(plan.rows.map((x) => x.label).slice(0, 3), ['E1', 'E2', 'E3']);
  // histogram (ordinal) → pie uses the grades, not value bins
  const pie = replot(r.visual, 'pie');
  assert.notEqual(pie.note, 'Slices are the histogram bins.');
});
t('I1: categorical → histogram → bar returns the categories, not bins', () => {
  const big = { type: 'chart', mode: 'replace', chart: { kind: 'hbar', x: 'asset', y: 'pbt_cr', data: Array.from({ length: 40 }, (_, i) => ({ asset: `Asset ${i}`, pbt_cr: 100 + ((i * 37) % 900) })) } } as VisualContainer;
  const h = replot(big, 'histogram');
  assert.equal(h.applied, 'histogram');
  const bar = replot(h.visual, 'bar');
  assert.deepEqual(bar.visual.chart?.data, replot(big, 'bar').visual.chart?.data);
  // few values → honest fallback, not a 14-value "distribution"
  assert.equal(replot(V.categorical, 'histogram').applied, 'hbar');
  // but pie from that histogram reuses the bins
  assert.match(replot(h.visual, 'pie').note || '', /bins/);
  void V;
});
t('I2: Indian FY labels "2022-23" are time, not a distribution', () => {
  const v = { type: 'chart', mode: 'replace', chart: { kind: 'line', x: 'fiscal', y: 'pat_cr', data: ['2021-22', '2022-23', '2023-24', '2024-25'].map((f, i) => ({ fiscal: f, pat_cr: 30000 + i })) } } as VisualContainer;
  assert.equal(profile(v).shape, 'time');
  assert.equal(replot(v, 'pie').applied, 'bar');
});
t('I3: a long aggregate table is not "people"; year columns are not measures', () => {
  const rows = Array.from({ length: 46 }, (_, i) => ({ work_centre: `WC${i}`, region: ['N', 'S', 'E', 'W'][i % 4], headcount: 100 + i, sanctioned: 120 + i, vacancy: 20 }));
  const v = { type: 'table', mode: 'replace', table: { columns: ['work_centre', 'region', 'headcount', 'sanctioned', 'vacancy'], rows } } as VisualContainer;
  assert.notEqual(profile(v).shape, 'records');
  const yr = { type: 'chart', mode: 'replace', chart: { kind: 'bar', x: 'asset', y: 'pbt_cr', data: [{ asset: 'A', year: 2026, pbt_cr: 1 }, { asset: 'B', year: 2026, pbt_cr: 2 }, { asset: 'C', year: 2026, pbt_cr: 3 }] } } as VisualContainer;
  assert.ok(!profile(yr).measures.includes('year'));
});
t('R1: wc_name / field_name dimensions are entities, not people', () => {
  const v = { type: 'chart', mode: 'replace', chart: { kind: 'hbar', x: 'wc_name', y: 'headcount', data: Array.from({ length: 14 }, (_, i) => ({ wc_name: `Centre ${i}`, headcount: 100 + i * 10 })) } } as VisualContainer;
  assert.equal(profile(v).shape, 'categorical');
  assert.equal(profile(v).people, false);
});
t('R2: backend histogram over grades draws the grades', () => {
  const plan = planChart({ kind: 'histogram', x: 'grade', y: 'count', data: ['E1', 'E2', 'E3', 'E4', 'E5', 'E6'].map((g, i) => ({ grade: g, count: [35, 90, 87, 67, 57, 35][i] })) } as any);
  assert.deepEqual(plan.rows.map((r) => r.label), ['E1', 'E2', 'E3', 'E4', 'E5', 'E6']);
});
t('I7: re-plot strips the compare view', () => {
  const cmp = { type: 'chart', mode: 'compare', title: 'C', compare: { items: [{ label: 'A' }, { label: 'B' }] }, chart: { kind: 'grouped_bar', x: 'grade', data: [{ grade: 'E1', A: 1, B: 2 }, { grade: 'E2', A: 3, B: 4 }] } } as unknown as VisualContainer;
  assert.equal(replot(cmp, 'table').visual.compare, undefined);
});
t('N2: funnel / waterfall on nominal positive categories fall back with a note', () => {
  assert.equal(replot(V.categorical, 'funnel').applied, 'hbar');
  assert.equal(replot(V.categorical, 'waterfall').applied, 'hbar');
  assert.equal(replot(V.categorical_neg, 'waterfall').status, 'native');
});

console.log(`compat engine: ${passed} passed (${Object.keys(V).length} shapes × ${KINDS.length} kinds + semantics)`);

// U5.6: mixed units never share one axis
import { mixedUnits } from '../src/charts/plan';
import mou from '../src/fixtures/c10_mou_bullet.json';
{
  const rows = ['FY22', 'FY23', 'FY24', 'FY25', 'FY26'].map((fy, i) => ({ fy, capex_cr: 30000 + i * 1000, achievement_pct: 90 + i, crude_mmt: 19 + i * 0.1 }));
  assert.equal(mixedUnits(rows, ['capex_cr', 'achievement_pct', 'crude_mmt']), true);
  const plan = planChart({ kind: 'line', x: 'fy', data: rows } as any);
  assert.equal(plan.form, 'multiples');
  assert.equal(plan.seriesKeys.length, 3);
  const same = ['FY22', 'FY23', 'FY24'].map((fy, i) => ({ fy, onshore_cr: 100 + i, offshore_cr: 140 + i }));
  assert.equal(planChart({ kind: 'line', x: 'fy', data: same } as any).form, 'line');
  // MoU fixture keeps its bullet form (vs target)
  assert.equal(planChart((mou as any).visual.chart).form, 'bullet');
  console.log('mixed units: 4 passed');
}
