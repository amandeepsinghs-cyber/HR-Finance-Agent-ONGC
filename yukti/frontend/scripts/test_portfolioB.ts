// P4.5 B1 (SPEC-09 §5, SPEC-02 §8): sensitivity grid + tornado builders.
// Run: npx --yes tsx scripts/test_portfolioB.ts
import assert from 'node:assert/strict';
import grid from '../src/fixtures/charts/portfolioB/sensitivity_grid.json';
import tor from '../src/fixtures/charts/portfolioB/tornado.json';
import { mixHex, gridCells, gridCellColor, sensitivityGridOption, sortTornado, tornadoOption, driverLabel, fmtOutput } from '../src/charts/financeOptions';
import { getTokens } from '../src/charts/theme';

let n = 0;
const ok = (name: string, fn: () => void) => {
  fn();
  n++;
  console.log(`  ✓ ${name}`);
};
const G = (grid as any).sensitivity_grid;
const T = (tor as any).tornado;

console.log('sensitivity grid');
ok('9×9 = 81 cells, exactly 1 base cell', () => {
  const cells = gridCells(G);
  assert.equal(cells.length, 81);
  assert.equal(cells.filter((c) => c.isBase).length, 1);
  const b = cells.find((c) => c.isBase)!;
  assert.deepEqual([b.row, b.col], [G.base.row_idx, G.base.col_idx]);
});
ok('n/m exactly where WACC − g < 1pp (SPEC-02 §8)', () => {
  const cells = gridCells(G);
  for (const c of cells) {
    const w = G.row_input.values[c.row];
    const g = G.col_input.values[c.col];
    assert.equal(c.value === null, w - g < 1 - 1e-9, `w=${w} g=${g}`);
  }
  assert.equal(fmtOutput(null, 'INR'), 'n/m');
});
ok('exact cell values are shown (no rounding beyond 1 dp)', () => {
  const opt: any = sensitivityGridOption(G, getTokens(false));
  const fmt = opt.series[0].label.formatter;
  const cells = gridCells(G);
  const i = cells.findIndex((c) => c.isBase);
  assert.equal(fmt({ dataIndex: i }), `₹${G.cells[G.base.row_idx][G.base.col_idx]}`);
});
ok('diverging colours: above base = accent, below = maroon, base = surface, base outlined', () => {
  for (const dark of [false, true]) {
    const t = getTokens(dark);
    const cells = gridCells(G);
    const base = cells.find((c) => c.isBase)!;
    assert.equal(gridCellColor(base, t), t.surface);
    const valued = cells.filter((c) => c.value !== null);
    const hi = valued.reduce((a, c) => (c.tone > a.tone ? c : a)); // most above base
    const lo = valued.reduce((a, c) => (c.tone < a.tone ? c : a)); // most below base
    assert.ok(hi.tone > 0 && lo.tone < 0);
    // the strongest cells are the max tint of their side's colour mixed into the surface
    assert.equal(gridCellColor(hi, t), mixHex(t.accent, t.surface, 0.1 + 0.45 * Math.abs(hi.tone)), 'high = accent tint');
    assert.equal(gridCellColor(lo, t), mixHex(t.maroon, t.surface, 0.1 + 0.45 * Math.abs(lo.tone)), 'low = maroon tint');
    const vm = (sensitivityGridOption(G, t) as any).visualMap[0];
    assert.equal(vm.dimension, 3);
    const centre = vm.pieces.find((pc: any) => pc.gte !== undefined && pc.gte <= 0 && pc.lt > 0);
    assert.equal(centre.color, t.surface, 'centre bin = surface (base)');
    assert.ok(vm.pieces.some((pc: any) => pc.value === 2), 'explicit n/m piece');
    const opt: any = sensitivityGridOption(G, t);
    const baseItem = opt.series[0].data[cells.indexOf(base)];
    assert.equal(baseItem.itemStyle.borderWidth, 2);
  }
});
ok('axes carry names and units', () => {
  const opt: any = sensitivityGridOption(G, getTokens(false));
  assert.match(opt.xAxis[0].name, /Terminal g/);
  assert.match(opt.yAxis[0].name, /WACC/);
  assert.equal(opt.xAxis[0].data[0], '1%');
});

console.log('tornado');
ok('sorted by |high − low| desc, largest on top', () => {
  const s = sortTornado(T.bars);
  const w = s.map((b) => Math.abs(b.high_inr - b.low_inr));
  for (let i = 1; i < w.length; i++) assert.ok(w[i - 1] >= w[i]);
  assert.equal(s[0].driver, 'brent'); // 91 > wacc 81
  const opt: any = tornadoOption(T, getTokens(false));
  assert.equal(opt.yAxis[0].inverse, true);
  assert.equal(opt.yAxis[0].data[0], driverLabel(s[0]));
});
ok('bars centred on base: values are deltas from base; labels show absolute ₹', () => {
  const opt: any = tornadoOption(T, getTokens(true));
  const s = sortTornado(T.bars);
  assert.equal(opt.series[0].data[0].value, s[0].low_inr - T.output.base);
  assert.equal(opt.series[1].data[0].value, s[0].high_inr - T.output.base);
  assert.equal(opt.series[0].label.formatter({ value: s[0].low_inr - T.output.base }), `₹${s[0].low_inr}`);
  assert.equal(opt.series[0].markLine.data[0].xAxis, 0);
  assert.match(opt.series[0].markLine.label.formatter, /^Base ₹250/);
  assert.ok(opt.xAxis[0].max >= Math.max(...s.map((b) => Math.abs(b.high_inr - T.output.base))));
});
ok('labels name the input ranges', () => {
  assert.equal(driverLabel(T.bars[1]), 'Brent (-$10/bbl / +$10/bbl)');
  assert.equal(driverLabel({ driver: 'holdco_discount', low_input: '0%', high_input: '30%', low_inr: 1, high_inr: 2 }), 'Holdco discount (0% / 30%)');
});
ok('label sits on the outer end of each bar', () => {
  const opt: any = tornadoOption(T, getTokens(false));
  for (const ser of opt.series) for (const d of ser.data) assert.equal(d.label.position, d.value < 0 ? 'left' : 'right');
});
ok('fixtures are labelled illustrative (truth rule D-35)', () => {
  assert.match(G.source, /Illustrative/);
  assert.match(T.source, /Illustrative/);
});

console.log(`\n${n} passed`);
