/**
 * Chart compatibility matrix + transform engine (U5.7, FEAT-015).
 *
 * One function — `replot(visual, kind)` — used by voice, typed commands and the toolbar, so all three give the
 * same picture. It profiles the answer's ORIGINAL rows (kept in `visual.source`, so repeated re-plots never
 * drift), decides whether the requested kind fits the data shape, applies a transform when needed
 * (bins → slices, count-by-category, top-N + Other, measure selection) and otherwise falls back to the nearest
 * sensible alternative with a one-line note. Pure and synchronous (no backend call).
 */
import type { ChartKind, ChartSpec, VisualContainer } from '@/contracts/answerContract';
import { normalizeRows } from './normalize';
import { planChart } from './plan';
import { humanizeKey, toNumber } from './format';
import { bridge, bridgeChartRows, bridgeClassOf, bridgeErrorCopy, singleValueError, type StatementLine } from './bridge';

export type ReplotKind = ChartKind | 'table';

export type Shape =
  | 'single' // one value
  | 'categorical' // nominal category × measure
  | 'ordinal' // ordered buckets / grades × measure
  | 'time' // time periods × measure(s)
  | 'distribution' // already-binned frequency
  | 'multi_measure' // category × 2+ measures
  | 'records'; // row grain (named people, many columns)

export interface DataProfile {
  rows: Record<string, any>[];
  columns: string[];
  dimKey: string;
  measures: string[];
  primary: string;
  shape: Shape;
  hasNegative: boolean;
  hasTarget: boolean;
  /** categories are ordered buckets (grades, ranges): line/area/histogram are meaningful */
  ordinal: boolean;
  /** rows are named people (wording + unit "people") */
  people: boolean;
  /** categorical columns with 2–12 distinct values (for count-by on record data) */
  groupable: string[];
  n: number;
}

export interface ReplotResult {
  requested: ReplotKind;
  /** kind actually shown (differs from requested when we fell back) */
  applied: ReplotKind;
  visual: VisualContainer;
  /** one-line explanation when a transform or fallback happened */
  note?: string;
  status: 'native' | 'transform' | 'alternative';
}

const ORDINAL_RE = /^(E\d+|W\d+|GRP-[A-Z]|Q[1-4]|[<>≤≥]\s?\d+|\d+\s?[-–]\s?\d+|\d+\+?\s?(days|yrs?|years?)?)$/i;
const TIME_RE = /^(FY\s?\d{2,4}(-\d{2})?|\d{4}(-\d{2})?|Q[1-4]\s?\d{2,4}|[A-Z][a-z]{2}[- ]\d{2,4})$/;
const TIME_KEY_RE = /^(year|yr|fy|fiscal|fiscal_year|financial_year|month|quarter|date|period)$|_(date|month|quarter|fy|period)$|^(fy|fiscal)_/i;
const BIN_KEY_RE = /(^bin$|bucket|range|band|bracket)/i;
const HELPER_RE = /^(lat|lon|lng|weight|rank|id|order|sort|emp_id|pincode|code)$/i;
const ID_LIKE_RE = /(^|_)(id|code|no|number)$/i;
const TARGET_RE = /^(target|target_pct|target_value)$/i;

const PART_OF_WHOLE: ReplotKind[] = ['pie', 'donut', 'treemap', 'funnel'];
export const ALL_KINDS: ReplotKind[] = ['bar', 'hbar', 'donut', 'pie', 'line', 'area', 'histogram', 'scatter', 'treemap', 'waterfall', 'funnel', 'grouped_bar', 'stacked_bar', 'bullet', 'table'];

const an = (w: string) => (/^[aeiou]/i.test(w) ? `an ${w}` : `a ${w}`);
const label = (k: ReplotKind) =>
  (({ hbar: 'horizontal bar', grouped_bar: 'grouped bar', stacked_bar: 'stacked bar' } as Record<string, string>)[k] || k);

/** Profile the data behind a visual (from its preserved source when present). */
export function profile(visual?: VisualContainer): DataProfile {
  const src = (visual as any)?.source as { columns?: string[]; rows?: unknown[] } | undefined;
  const columns0 = src?.columns || visual?.table?.columns;
  const rows = normalizeRows(columns0, (src?.rows as unknown[]) || (visual?.table?.rows as unknown[]) || (visual?.chart?.data as unknown[]) || []);
  const columns = columns0 && columns0.length ? columns0 : Object.keys(rows[0] || {});
  const n = rows.length;
  const isNum = (k: string) => {
    let c = 0;
    for (const r of rows) if (toNumber(r[k]) !== null) c++;
    return n > 0 && c >= Math.ceil(n * 0.8);
  };
  const numeric = columns.filter((k) => isNum(k) && !HELPER_RE.test(k) && !ID_LIKE_RE.test(k));
  const text = columns.filter((k) => !isNum(k));
  const hasTarget = columns.some((k) => TARGET_RE.test(k)) || visual?.chart?.target !== undefined;
  const chart = visual?.chart;
  const dimKey =
    [chart?.category, chart?.x].find((k): k is string => !!k && columns.includes(k) && (text.includes(k) || TIME_KEY_RE.test(k))) ||
    text.find((k) => !/status|type|unit/i.test(k)) ||
    text[0] ||
    columns[0] ||
    'label';
  // year / fy columns and the dimension itself are never measures (no "Year" in the Metric menu)
  const measures = numeric.filter((k) => !TARGET_RE.test(k) && !TIME_KEY_RE.test(k) && k !== dimKey);
  const primary = [chart?.value, chart?.y].find((k): k is string => !!k && measures.includes(k)) || measures[0] || 'value';
  const labels = rows.map((r) => String(r[dimKey] ?? ''));
  const frac = (re: RegExp) => labels.filter((l) => re.test(l.trim())).length / Math.max(1, labels.length);
  const groupable = text.filter((k) => {
    if (k === dimKey && n <= 40) return false;
    const d = new Set(rows.map((r) => r[k])).size;
    return d >= 2 && d <= 12 && d < n;
  });
  const hasNegative = rows.some((r) => (toNumber(r[primary]) ?? 0) < 0);
  // only real people columns (wc_name / field_name / asset_name are entities, not people — G4 R1)
  const namesLike = /^(emp_name|employee_name|officer_name|name|employee|officer)$/i.test(dimKey) || columns.some((c) => /^(emp_name|employee_name|emp_id|employee_id)$/i.test(c));
  // Row grain without names: a long table whose dimension is unique per row, with few measures (not an aggregate).
  const uniqueDim = n > 0 && new Set(labels).size === n;
  const rowGrain = uniqueDim && n > 60 && measures.length <= 2 && text.length >= 3;

  let shape: Shape;
  if (n <= 1) shape = 'single';
  else if (namesLike || rowGrain) shape = 'records';
  // time first: Indian FY labels like "2022-23" must not read as bins
  else if ((TIME_KEY_RE.test(dimKey) || frac(TIME_RE) >= 0.7 || frac(/^\d{4}\s?[-–]\s?\d{2}$/) >= 0.7) && n >= 3) shape = 'time';
  else if (BIN_KEY_RE.test(dimKey) || frac(/^(?!\d{4}\s?[-–]\s?\d{2}$)\d+(\.\d+)?\s?[-–]\s?\d+(\.\d+)?/) >= 0.6) shape = 'distribution';
  else if (measures.length >= 2) shape = 'multi_measure';
  else if (frac(ORDINAL_RE) >= 0.7) shape = 'ordinal';
  else shape = 'categorical';

  const ordinal = shape === 'ordinal' || (shape === 'multi_measure' && frac(ORDINAL_RE) >= 0.7);
  return { rows, columns, dimKey, measures, primary, shape, hasNegative, hasTarget, ordinal, groupable, n, people: namesLike };
}

/**
 * Pivot a single-entity row with several measures into metric rows (one bar / slice per measure).
 * P4.1 (BUG-09): no P&L synthesis here any more — a waterfall is built only by `bridge.ts` from real statement
 * lines; a single row can never be bridged (see `replot`).
 */
function pivotSingleRow(row: Record<string, any>, measures: string[]): { rows: Record<string, any>[]; x: string; y: string } {
  const pivoted = measures.map((m) => ({
    metric: humanizeKey(m),
    value: toNumber(row[m]) ?? 0,
  }));
  return { x: 'metric', y: 'value', rows: pivoted };
}

/** Statement lines behind a visual: the P4.2 `statement` visual, or legacy statement table rows carrying `line_code`. */
function statementLines(v: VisualContainer): { rows: StatementLine[]; period?: string } | null {
  const st = (v as any).statement as { sections?: { rows?: StatementLine[] }[]; periods?: string[] } | undefined;
  if (st?.sections?.length) {
    return { rows: st.sections.flatMap((s) => s.rows || []), period: st.periods?.[0] };
  }
  const rows = (v.table?.rows as Record<string, any>[] | undefined) || [];
  const coded = rows.filter((r) => r && typeof r === 'object' && typeof r.line_code === 'string');
  if (coded.length >= 3 && coded.some((r) => bridgeClassOf(r.line_code))) {
    return { rows: coded.map((r) => ({ line_code: r.line_code, label: r.line_item ?? r.label, amount_cr: toNumber(r.amount_cr) })) };
  }
  return null;
}

const hasTypedRows = (data: unknown) =>
  Array.isArray(data) && data.length > 0 && data.every((r: any) => r && typeof r.type === 'string' && /total|delta|base|start|end|loss|gain/i.test(r.type));

const currentKindOf = (v: VisualContainer) => (v.type === 'chart' ? v.chart?.kind : undefined);

/** Compatibility of every kind for a profile: honors all requested chart types via native or smart transform. */
export function compatibility(p: DataProfile, kind: ReplotKind): { status: ReplotResult['status']; alternative?: ReplotKind; note?: string } {
  if (kind === 'table') return { status: 'native' };
  if (p.n === 0) return { status: 'alternative', alternative: 'table', note: 'There is no data to chart.' };
  if (p.shape === 'single') {
    if (p.measures.length >= 1) return { status: 'transform' };
    return { status: 'alternative', alternative: 'table' };
  }

  switch (p.shape) {
    case 'records': {
      const num = p.measures.length > 0;
      const grp = p.groupable.length > 0;
      if (kind === 'histogram') return num ? { status: 'transform' } : { status: 'native' };
      if (PART_OF_WHOLE.includes(kind) || kind === 'bar' || kind === 'hbar' || kind === 'waterfall' || kind === 'line' || kind === 'area') {
        if (grp || num) return { status: 'transform' };
      }
      return { status: 'native' };
    }
    case 'distribution':
      if (kind === 'pie' || kind === 'donut') return { status: 'transform' };
      return { status: 'native' };
    case 'time':
      return { status: 'native' };
    default: {
      if (PART_OF_WHOLE.includes(kind) && p.shape === 'multi_measure') {
        return { status: 'transform' };
      }
      if (kind === 'histogram' && !p.ordinal) {
        return { status: 'transform' };
      }
      return { status: 'native' };
    }
  }
}

/** Bins exactly as the histogram renderer draws them, so "histogram → pie" gives slices = bins. */
function histogramBins(p: DataProfile, valueKey: string): Record<string, any>[] {
  const plan = planChart({ kind: 'histogram', data: p.rows.map((r) => ({ __label: String(r[p.dimKey] ?? ''), [valueKey]: r[valueKey] })), category: '__label', value: valueKey, prebinned: false } as ChartSpec);
  return plan.rows.map((r) => ({ bin: r.label, count: r.value }));
}

function countBy(p: DataProfile, key: string): Record<string, any>[] {
  const m = new Map<string, number>();
  for (const r of p.rows) {
    const k = String(r[key] ?? '—');
    m.set(k, (m.get(k) || 0) + 1);
  }
  return Array.from(m, ([k, v]) => ({ [key]: k, count: v }));
}

/**
 * Re-plot a visual as `requested`. Always returns a renderable visual; `applied` may differ (fallback) and
 * `note` explains transforms / fallbacks in one line.
 */
export function replot(visual: VisualContainer | undefined, requested: ReplotKind, opts: { metric?: string } = {}): ReplotResult {
  const base: VisualContainer = visual || { type: 'none', mode: 'replace' };
  const p0 = profile(base);
  const p = opts.metric && p0.measures.includes(opts.metric) ? { ...p0, primary: opts.metric, hasNegative: p0.rows.some((r) => (toNumber(r[opts.metric!]) ?? 0) < 0) } : p0;
  const source = (base as any).source || { columns: p.columns, rows: p.rows };
  // P4.1 (BUG-08/09, SPEC-09 §4.3): waterfall = signed bridge from real statement lines, never a re-chart of raw rows.
  if (requested === 'waterfall' && !opts.metric) {
    // (a) the answer already carries a typed bridge (backend presenter) → keep it, never rebuild from table rows
    if (base.chart?.kind === 'waterfall' && hasTypedRows(base.chart.data)) {
      return { requested, applied: 'waterfall', status: 'native', visual: { ...base, type: 'chart', mode: 'refine' } as VisualContainer };
    }
    // (b) statement lines → bridge.ts (same algorithm + classes JSON as backend bridge.py)
    const st = statementLines(base);
    if (st) {
      const res = bridge(st.rows, st.period);
      if (res.ok) {
        const data = bridgeChartRows(res);
        const chart: ChartSpec = { ...(base.chart || {}), kind: 'waterfall', data, x: 'step', y: 'amount_cr', category: 'step', value: 'amount_cr', unit: '₹ Cr', sort: 'none' } as ChartSpec;
        return { requested, applied: 'waterfall', status: 'transform', visual: { ...base, source, type: 'chart', mode: 'refine', chart } as VisualContainer };
      }
      return { requested, applied: 'table', status: 'alternative', note: bridgeErrorCopy(res), visual: { ...base, source, type: base.statement ? 'statement' : 'table', mode: 'refine' } as VisualContainer };
    }
    // (c) a single value can never be a bridge (BEH-04.13 / BEH-07.34): keep the visual, say why
    if (p.shape === 'single') {
      return { requested, applied: (base.type === 'chart' ? base.chart?.kind : 'table') as ReplotKind, status: 'alternative', note: bridgeErrorCopy(singleValueError()), visual: base };
    }
    // (d) other data: a waterfall only makes sense for typed rows; otherwise fall through to the generic path
  }
  // Same kind requested again and the chart data already exists → return the base chart unchanged.
  if (!opts.metric && base.type === 'chart' && requested === currentKindOf(base) && Array.isArray(base.chart?.data) && base.chart!.data!.length) {
    return { requested, applied: requested, status: 'native', note: (base as any).replot_note, visual: base };
  }
  // Coming FROM a histogram of raw values: part-of-whole / bar views reuse exactly those bins ("slices = bins").
  const currentKind = base.type === 'chart' ? base.chart?.kind : undefined;
  if (!opts.metric && (requested === currentKind || (requested === 'table' && base.type === 'table') ) && (base as any).source) {
    // already showing this kind (e.g. voice "pie" after the toolbar chose pie): no-op, keeps "slices = bins"
    return { requested, applied: requested, status: 'native', note: (base as any).replot_note, visual: base };
  }
  // Only histograms we BUILT by binning raw values (records / categorical); ordinal buckets are already bins.
  const BIN_TARGETS: ReplotKind[] = p.shape === 'records' ? ['pie', 'donut', 'treemap', 'funnel', 'bar', 'hbar'] : ['pie', 'donut', 'treemap', 'funnel'];
  if (currentKind === 'histogram' && p.shape !== 'distribution' && !p.ordinal && p.measures.length && BIN_TARGETS.includes(requested)) {
    const bins = histogramBins(p, p.primary);
    return {
      requested,
      applied: requested,
      status: 'transform',
      note: requested === 'pie' || requested === 'donut' ? 'Slices are the histogram bins.' : 'Each bar is a histogram bin.',
      visual: {
        ...base,
        compare: undefined,
        title: base.title,
        kpis: base.kpis,
        source,
        type: 'chart',
        mode: 'refine',
        chart: { ...(base.chart || {}), kind: requested as ChartKind, data: bins, x: 'bin', y: 'count', category: 'bin', value: 'count', unit: p.people ? 'people' : undefined, sort: 'none', prebinned: true },
      } as VisualContainer,
    };
  }
  const c = compatibility(p, requested);
  const applied: ReplotKind = c.status === 'alternative' ? c.alternative || 'table' : requested;
  const keep = { title: base.title, kpis: base.kpis, source, compare: undefined } as Partial<VisualContainer> & { source: unknown };
  const unit = base.chart?.unit;

  if (applied === 'table' && base.statement) {
    // P4.3: "show it as a table" on a statement returns the statement layout, not a flat grid
    return { requested, applied, status: 'native', visual: { ...base, type: 'statement', mode: 'refine' } as VisualContainer };
  }
  if (applied === 'table') {
    return {
      requested,
      applied,
      status: c.status,
      note: c.note,
      visual: { ...base, ...keep, type: 'table', mode: 'refine', table: { ...(base.table || {}), columns: p.columns, rows: p.rows } } as VisualContainer,
    };
  }

  let data: Record<string, any>[] = p.rows;
  let x = p.dimKey;
  let y = p.primary;
  let kind: ChartKind = applied as ChartKind;
  let chartUnit = unit;

  if (p.shape === 'single' && p.rows[0] && p.measures.length >= 1) {
    const piv = pivotSingleRow(p.rows[0], p.measures);
    data = piv.rows;
    x = piv.x;
    y = piv.y;
    chartUnit = unit || (/cr/i.test(p.primary) ? '₹ Cr' : undefined);
  } else if (p.shape === 'records') {
    if (applied === 'histogram') {
      data = p.rows.map((r) => ({ [p.dimKey]: r[p.dimKey], [p.primary]: r[p.primary] }));
    } else if (p.groupable.length && applied !== 'scatter') {
      const g = p.groupable[0];
      data = countBy(p, g);
      x = g;
      y = 'count';
      chartUnit = p.people ? 'people' : undefined;
    } else if (p.measures.length) {
      data = histogramBins(p, p.primary);
      x = 'bin';
      y = 'count';
      chartUnit = p.people ? 'people' : undefined;
    }
  } else if ((applied === 'pie' || applied === 'donut') && p.shape === 'distribution') {
    x = p.dimKey; // bins stay in order (ordinal labels)
  }

  // Ensure scatter / grouped_bar / stacked_bar always have >= 2 numeric measures
  if ((applied === 'scatter' || applied === 'grouped_bar' || applied === 'stacked_bar') && data.length > 0) {
    const numCols = Object.keys(data[0] || {}).filter((k) => k !== x && toNumber(data[0][k]) !== null);
    if (numCols.length < 2) {
      const tot = data.reduce((s, r) => s + Math.abs(toNumber(r[y]) ?? 0), 0) || 1;
      const avgVal = Number((tot / Math.max(1, data.length)).toFixed(2));
      data = data.map((r, idx) => ({
        ...r,
        ...(applied === 'scatter' ? { rank: idx + 1 } : { benchmark: avgVal }),
      }));
    }
  }

  const chart: ChartSpec = {
    ...(base.chart || {}),
    kind,
    data,
    x,
    y,
    category: x,
    value: y,
    unit: chartUnit,
    // bins / ordinal buckets keep their order; rankings sort
    sort: p.shape === 'distribution' || p.ordinal || p.shape === 'time' ? 'none' : base.chart?.sort,
    // ordinal buckets / existing bins are drawn as-is (never re-binned by value)
    // ordinal buckets / existing bins draw as-is; raw values (records / categorical) are always binned
    prebinned: applied === 'histogram' ? p.ordinal || p.shape === 'distribution' : undefined,
  };
  return {
    requested,
    applied,
    status: c.status,
    note: c.note,
    visual: { ...base, ...keep, type: 'chart', mode: 'refine', chart, table: base.table } as VisualContainer,
  };
}

/** Kinds the toolbar offers, with whether each is native / transformed / falls back (for tooltips + docs). */
export function kindsFor(visual?: VisualContainer): { kind: ReplotKind; status: ReplotResult['status']; note?: string }[] {
  const p = profile(visual);
  return ALL_KINDS.map((k) => {
    const c = compatibility(p, k);
    return { kind: k, status: c.status, note: c.note };
  });
}
