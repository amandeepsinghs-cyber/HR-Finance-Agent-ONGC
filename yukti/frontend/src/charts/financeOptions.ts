/**
 * P4.5 B1 (SPEC-09 §4.5 rows 19–20, §5; SPEC-02 §8): typed finance visuals.
 *  - Sensitivity grid: heatmap with the exact value in every cell, a diverging colour scale centred on the base
 *    case, the base cell outlined, and `null` cells shown as "n/m".
 *  - Tornado: per-driver low/high swing bars centred on the base value, sorted by |high − low| (largest on top),
 *    with the input ranges in the labels.
 * Pure functions (no React) so they are unit-testable.
 */
import * as echarts from 'echarts';
import type { SensitivityGridSpec, TornadoSpec, TornadoBarSpec } from '@/contracts/answerContract';
import { ChartTokens, px, tooltipBase, tooltipCard, anim, alpha } from './theme';
import { fmtNum } from './format';
import { niceBounds } from './options';

type Opt = echarts.EChartsOption;

/** "₹312.4" for INR outputs; plain grouped number otherwise. */
export function fmtOutput(v: number | null | undefined, unit: string): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return 'n/m';
  const n = fmtNum(v, Math.abs(v) >= 1000 ? 0 : 1);
  return /inr|₹|rupee/i.test(unit) ? `₹${n}` : unit === '%' ? `${n}%` : n;
}

function fmtAxis(v: number, unit: string): string {
  return unit === '%' ? `${fmtNum(v, 1)}%` : `${fmtNum(v)}${unit ? ` ${unit}` : ''}`;
}

export interface GridCell {
  row: number;
  col: number;
  value: number | null;
  isBase: boolean;
  /** −1 … +1: position relative to the base value (0 = base) */
  tone: number;
}

/** Cells with a diverging tone centred on the base cell; tone scaled by the largest |Δ| in the grid. */
export function gridCells(spec: SensitivityGridSpec): GridCell[] {
  const baseVal = spec.cells?.[spec.base.row_idx]?.[spec.base.col_idx];
  const flat: GridCell[] = [];
  let maxAbs = 0;
  spec.cells.forEach((row, r) =>
    row.forEach((v, c) => {
      if (typeof v === 'number' && typeof baseVal === 'number') maxAbs = Math.max(maxAbs, Math.abs(v - baseVal));
    }),
  );
  spec.cells.forEach((row, r) =>
    row.forEach((v, c) => {
      const isBase = r === spec.base.row_idx && c === spec.base.col_idx;
      const tone = typeof v === 'number' && typeof baseVal === 'number' && maxAbs > 0 ? (v - baseVal) / maxAbs : 0;
      flat.push({ row: r, col: c, value: typeof v === 'number' && Number.isFinite(v) ? v : null, isBase, tone });
    }),
  );
  return flat;
}

/** Opaque mix of two `#RRGGBB` colours (f = share of `a`). Falls back to `b` for non-hex input. */
export function mixHex(a: string, b: string, f: number): string {
  if (!/^#[0-9a-f]{6}/i.test(a) || !/^#[0-9a-f]{6}/i.test(b)) return b;
  const h = (c: string) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16));
  const [x, y] = [h(a), h(b)];
  return `#${x.map((v, k) => Math.round(v * f + y[k] * (1 - f)).toString(16).padStart(2, '0')).join('')}`;
}

// ≤ 55 % tint keeps the cell text at body-ink contrast in both themes (rubric F: exact values legible)
const MAX_TINT = 0.55;
const NM_TONE = 2; // outside [-1, 1]: drawn with the visualMap's out-of-range (n/m) colour

/** Diverging ramp used by the grid's (hidden) visualMap: maroon below base → surface at base → accent above. */
/** (kept for callers/tests) the diverging ramp end-points: maroon tint → surface → accent tint. */
export function gridRamp(t: ChartTokens): string[] {
  return [mixHex(t.maroon, t.surface, MAX_TINT), mixHex(t.maroon, t.surface, 0.25), t.surface, mixHex(t.accent, t.surface, 0.25), mixHex(t.accent, t.surface, MAX_TINT)];
}

/** 21 tone bins (−1 … +1, step 0.1) coloured like gridCellColor, plus the n/m piece. */
export function gridPieces(t: ChartTokens): { gte?: number; lt?: number; value?: number; color: string }[] {
  const pieces: { gte?: number; lt?: number; value?: number; color: string }[] = [];
  for (let k = -10; k <= 10; k++) {
    const tone = k / 10;
    const color = k === 0 ? t.surface : mixHex(tone > 0 ? t.accent : t.maroon, t.surface, 0.1 + (MAX_TINT - 0.1) * Math.abs(tone));
    pieces.push({ gte: (k - 0.5) / 10, lt: (k + 0.5) / 10, color });
  }
  pieces.push({ value: NM_TONE, color: alpha(t.faint, 0.18) });
  return pieces;
}

export function gridCellColor(cell: GridCell, t: ChartTokens): string {
  if (cell.value === null) return alpha(t.faint, 0.18);
  if (cell.isBase || Math.abs(cell.tone) < 1e-9) return t.surface;
  return mixHex(cell.tone > 0 ? t.accent : t.maroon, t.surface, 0.1 + (MAX_TINT - 0.1) * Math.min(1, Math.abs(cell.tone)));
}

export function sensitivityGridOption(spec: SensitivityGridSpec, t: ChartTokens): Opt {
  const xs = spec.col_input.values.map((v) => fmtAxis(v, spec.col_input.unit));
  const ys = spec.row_input.values.map((v) => fmtAxis(v, spec.row_input.unit));
  const cells = gridCells(spec);
  return {
    backgroundColor: 'transparent',
    textStyle: { fontFamily: t.font, color: t.text },
    ...anim(),
    title: [],
    legend: [],
    graphic: [],
    grid: [{ left: px(t, 36), right: px(t, 16), top: px(t, 40), bottom: px(t, 12), containLabel: true }],
    xAxis: [
      {
        type: 'category',
        data: xs,
        position: 'top',
        name: `${spec.col_input.name} →`,
        nameLocation: 'middle',
        nameGap: px(t, 26),
        nameTextStyle: { color: t.sub, fontSize: px(t, 12), fontWeight: 600 },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: t.sub, fontSize: px(t, 12) },
        splitArea: { show: false },
      },
    ],
    yAxis: [
      {
        type: 'category',
        data: ys,
        inverse: true,
        name: `${spec.row_input.name} ↓`,
        nameLocation: 'middle',
        nameGap: px(t, 48),
        nameRotate: 90,
        nameTextStyle: { color: t.sub, fontSize: px(t, 12), fontWeight: 600 },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: t.sub, fontSize: px(t, 12) },
      },
    ],
    // ECharts heatmaps require a visualMap (it overrides per-item colours): a hidden piecewise map on the tone
    // dimension (index 3) gives the diverging colour around the base case, plus an explicit n/m piece.
    visualMap: [{ show: false, type: 'piecewise', dimension: 3, pieces: gridPieces(t) } as any],
    tooltip: {
      ...tooltipBase(t),
      trigger: 'item',
      formatter: (p: any) => {
        const c = cells[p.dataIndex];
        return tooltipCard(t, `${spec.row_input.name} ${ys[c.row]} · ${spec.col_input.name} ${xs[c.col]}`, [
          [spec.output.name, c.value === null ? 'n/m (not meaningful)' : fmtOutput(c.value, spec.output.unit)],
          ...(c.isBase ? ([['Case', 'Base']] as [string, string][]) : []),
        ]);
      },
    },
    series: [
      {
        id: 'main',
        type: 'heatmap',
        data: cells.map((c) => ({
          value: [c.col, c.row, c.value === null ? 0 : c.value, c.value === null ? NM_TONE : c.tone],
          itemStyle: {
            borderColor: c.isBase ? t.text : t.surface,
            borderWidth: c.isBase ? 2 : 1,
          },
          label: { fontWeight: c.isBase ? 700 : 500 },
        })),
        label: {
          show: true,
          color: t.text,
          fontSize: px(t, cells.length > 100 ? 10 : 12),
          formatter: (p: any) => fmtOutput(cells[p.dataIndex].value, spec.output.unit),
        },
        emphasis: { itemStyle: { borderColor: t.text, borderWidth: 2 } },
      },
    ] as any,
  };
}

/** Bars sorted by |high − low| descending (largest swing first). Stable for ties. */
export function sortTornado(bars: TornadoBarSpec[]): TornadoBarSpec[] {
  return bars
    .map((b, i) => ({ b, i, w: Math.abs((b.high_inr ?? 0) - (b.low_inr ?? 0)) }))
    .sort((a, z) => z.w - a.w || a.i - z.i)
    .map((x) => x.b);
}

const DRIVER_LABELS: Record<string, string> = {
  brent: 'Brent',
  opex: 'Opex/boe',
  opex_boe: 'Opex/boe',
  capex: 'Capex',
  production: 'Production',
  wacc: 'WACC',
  terminal_g: 'Terminal g',
  g: 'Terminal g',
  inr_usd: 'INR/USD',
  fx: 'INR/USD',
  holdco_discount: 'Holdco discount',
};

export function driverLabel(b: TornadoBarSpec): string {
  const name = DRIVER_LABELS[b.driver?.toLowerCase?.()] || b.driver.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
  return `${name} (${b.low_input} / ${b.high_input})`;
}

export function tornadoOption(spec: TornadoSpec, t: ChartTokens): Opt {
  const bars = sortTornado(spec.bars || []);
  const baseV = spec.output.base;
  const unit = spec.output.unit;
  const labels = bars.map(driverLabel);
  const lows = bars.map((b) => b.low_inr - baseV);
  const highs = bars.map((b) => b.high_inr - baseV);
  const ext = Math.max(1e-9, ...lows.map(Math.abs), ...highs.map(Math.abs));
  // symmetric, round-numbered axis around the base (1/2/2.5/5 × 10ⁿ steps) with room for the end labels
  const nb = niceBounds(-ext * 1.2, ext * 1.2, 6);
  const pad = Math.max(Math.abs(nb.min), Math.abs(nb.max));
  const endLabel = {
    show: true,
    color: t.text,
    fontSize: px(t, 12),
    formatter: (p: any) => fmtOutput(baseV + Number(p.value), unit),
  };
  // the value label sits at the bar's outer end, whichever side of the base line the bar falls on
  const withSide = (vals: number[]) => vals.map((v) => ({ value: v, label: { position: v < 0 ? 'left' : 'right' } }));
  return {
    backgroundColor: 'transparent',
    textStyle: { fontFamily: t.font, color: t.text },
    ...anim(),
    title: [],
    graphic: [],
    legend: [
      {
        top: 0,
        left: 0,
        icon: 'roundRect',
        itemWidth: px(t, 14),
        itemHeight: px(t, 10),
        textStyle: { color: t.sub, fontSize: px(t, 12) },
        data: ['Low case', 'High case'],
      },
    ],
    grid: [{ left: px(t, 8), right: px(t, 72), top: px(t, 40), bottom: px(t, 28), containLabel: true }],
    xAxis: [
      {
        type: 'value',
        min: -pad,
        max: pad,
        interval: nb.interval,
        axisLine: { show: false },
        splitLine: { lineStyle: { color: t.grid, type: 'dashed' } },
        axisLabel: { color: t.sub, fontSize: px(t, 11), formatter: (v: number) => fmtOutput(baseV + v, unit) },
      },
    ],
    yAxis: [
      {
        type: 'category',
        data: labels,
        inverse: true, // largest swing on top
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: t.text, fontSize: px(t, 12), width: px(t, 220), overflow: 'break' },
      },
    ],
    tooltip: {
      ...tooltipBase(t),
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (ps: any) => {
        const i = (Array.isArray(ps) ? ps[0] : ps)?.dataIndex ?? 0;
        const b = bars[i];
        return tooltipCard(t, labels[i], [
          [`Low (${b.low_input})`, fmtOutput(b.low_inr, unit), t.maroon],
          [`High (${b.high_input})`, fmtOutput(b.high_inr, unit), t.accent],
          ['Swing', fmtOutput(Math.abs(b.high_inr - b.low_inr), unit)],
        ]);
      },
    },
    series: [
      {
        id: 'main',
        name: 'Low case',
        type: 'bar',
        data: withSide(lows),
        barWidth: '58%',
        barGap: '-100%', // low and high share one row, both drawn from the base line
        itemStyle: { color: t.maroon, borderRadius: 3 },
        label: endLabel,
        markLine: {
          symbol: 'none',
          silent: true,
          lineStyle: { color: t.text, width: 1.5 },
          // label above the plot (start of the inverse category axis), clear of the value-axis ticks
          label: { formatter: `Base ${fmtOutput(baseV, unit)}`, color: t.text, fontSize: px(t, 12), fontWeight: 600, position: 'start' },
          data: [{ xAxis: 0 }],
        },
      },
      {
        id: 's1',
        name: 'High case',
        type: 'bar',
        data: withSide(highs),
        barWidth: '58%',
        itemStyle: { color: t.accent, borderRadius: 3 },
        label: endLabel,
      },
    ] as any,
  };
}
