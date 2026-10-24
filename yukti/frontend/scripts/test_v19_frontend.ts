// P2H.3 frontend (SPEC-07 §4.1, §4.3): explicit level order, column kind, roster labels/sort/format.
// Run: npx --yes tsx scripts/test_v19_frontend.ts
import assert from 'node:assert/strict';
import { planChart } from '../src/charts/plan';
import {
  gradeRank,
  isYearsColumn,
  columnLabel,
  formatRosterCell,
  detectNumericColumns,
  normalizeRows,
  filterAndSortRows,
  discoverFilterableColumns,
} from '../src/components/renderers/rosterUtils';

let n = 0;
const ok = (name: string, fn: () => void) => {
  fn();
  n++;
  console.log(`  ✓ ${name}`);
};

const LEVELS = ['E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7', 'E8', 'E9', 'GRP-B', 'GRP-C', 'GRP-D'];
// Deliberately non-monotonic counts: a value sort would scramble the axis.
const COUNTS = [61, 120, 154, 140, 133, 98, 77, 40, 12, 60, 38, 10];
const t1 = LEVELS.map((g, i) => ({ grade: g, headcount: COUNTS[i] }));

console.log('P2H.3 frontend: chart order');
ok('kind=column + x_order=explicit keeps E1→E9→GRP order and draws columns', () => {
  const p = planChart({ kind: 'column', data: t1, x: 'grade', y: 'headcount', x_order: 'explicit' } as any);
  assert.equal(p.form, 'column');
  assert.equal(p.ordinal, true);
  assert.deepEqual(p.rows.map((r) => r.label), LEVELS);
});
ok('x_order=explicit keeps backend order even for non-level labels', () => {
  const data = [
    { bucket: 'Under review', n: 5 },
    { bucket: 'Approved', n: 50 },
    { bucket: 'Closed', n: 20 },
  ];
  const p = planChart({ kind: 'column', data, x: 'bucket', y: 'n', x_order: 'explicit' } as any);
  assert.deepEqual(p.rows.map((r) => r.label), ['Under review', 'Approved', 'Closed']);
});
ok('histogram of levels (legacy kind) is not re-binned and keeps order', () => {
  const p = planChart({ kind: 'histogram', data: t1, x: 'grade', y: 'headcount' } as any);
  assert.deepEqual(p.rows.map((r) => r.label), LEVELS);
});

console.log('P2H.3 frontend: roster');
ok('gradeRank orders E1<E2<E10 and executives before GRP-B<GRP-C<GRP-D, unknown last', () => {
  const shuffled = ['GRP-C', 'E10', 'E2', 'X', 'GRP-B', 'E1', 'GRP-D', 'e9'];
  const sorted = [...shuffled].sort((a, b) => gradeRank(a) - gradeRank(b));
  assert.deepEqual(sorted, ['E1', 'E2', 'e9', 'E10', 'GRP-B', 'GRP-C', 'GRP-D', 'X']);
});
ok('years columns are numeric and formatted to 1 dp without a unit suffix', () => {
  assert.ok(isYearsColumn('delhi_tenure_years'));
  assert.ok(isYearsColumn('ongc_tenure_years'));
  assert.ok(isYearsColumn('years_to_retirement'));
  assert.equal(formatRosterCell('years_to_retirement', 30, false).text, '30.0');
  assert.equal(formatRosterCell('delhi_tenure_years', 7.2649, false).text, '7.3');
  assert.equal(formatRosterCell('ongc_tenure_years', '21.04', false).text, '21.0');
  assert.equal(formatRosterCell('continuous_stay_years', 6.01, false).text, '6.0 yrs'); // legacy unchanged
  assert.equal(formatRosterCell('exemption', null, false).text, '—');
});
ok('columnLabel prefers backend labels ("Tenure in Delhi (yrs)")', () => {
  const labels = { delhi_tenure_years: 'Tenure in Delhi (yrs)', grade: 'Level' };
  assert.equal(columnLabel('delhi_tenure_years', labels), 'Tenure in Delhi (yrs)');
  assert.equal(columnLabel('grade', labels), 'Level');
  assert.equal(columnLabel('exemption', labels, (k) => k.toUpperCase()), 'EXEMPTION');
});

const cols = ['name', 'functional_designation', 'grade', 'ongc_tenure_years', 'delhi_tenure_years', 'years_to_retirement', 'exemption'];
const roster = normalizeRows(cols, [
  ['A', 'Chief Manager (HR)', 'E5', 22.1, 6.2, 9.4, null],
  ['B', 'Manager (Drilling)', 'E10', 12.0, 9.9, 18.0, 'pre_retirement'],
  ['C', 'Asst. Executive Engineer', 'E2', 5.5, 5.1, 30.2, null],
  ['D', 'Office Superintendent', 'GRP-B', 28.0, 7.7, 1.5, 'medical'],
  ['E', 'Deputy Manager', 'E9', 25.0, 12.3, 3.3, null],
]);
const numeric = detectNumericColumns(cols, roster);

ok('years_to_retirement and tenure columns detected numeric', () => {
  for (const c of ['ongc_tenure_years', 'delhi_tenure_years', 'years_to_retirement']) assert.ok(numeric.has(c), c);
});
ok('default sort delhi_tenure_years desc', () => {
  const out = filterAndSortRows(roster, cols, '', {}, 'delhi_tenure_years', 'desc', numeric);
  assert.deepEqual(out.map((r) => r.name), ['E', 'B', 'D', 'A', 'C']);
});
ok('sorting by Level uses grade_level_order, not alphabetical', () => {
  const asc = filterAndSortRows(roster, cols, '', {}, 'grade', 'asc', numeric);
  assert.deepEqual(asc.map((r) => r.grade), ['E2', 'E5', 'E9', 'E10', 'GRP-B']);
  const desc = filterAndSortRows(roster, cols, '', {}, 'grade', 'desc', numeric);
  assert.deepEqual(desc.map((r) => r.grade), ['GRP-B', 'E10', 'E9', 'E5', 'E2']);
});
ok('Level filter options are in level order', () => {
  const f = discoverFilterableColumns(cols, roster, new Set());
  const g = f.find((x) => x.col === 'grade');
  assert.ok(g);
  assert.deepEqual(g!.options, ['E2', 'E5', 'E9', 'E10', 'GRP-B']);
});

console.log(`\n${n} passed`);
