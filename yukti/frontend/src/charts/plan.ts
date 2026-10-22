/**
 * Chart planning: picks the best visual form from the contract's data shape + units,
 * overriding the backend's suggested kind when it is weak.
 */
import { ChartSpec } from '@/contracts/answerContract';
import { UnitInfo, parseUnit, toNumber, humanizeValue, fmtInt, fmtNum } from './format';

export type ChartForm =
  | 'pie'
  | 'donut'
  | 'ranked' // horizontal bars, sorted, top N
  | 'column' // vertical bars for ordinal categories (grades, buckets)
  | 'histogram' // contiguous frequency bars + overlaid bell/density curve
  | 'diverging' // horizontal bars with +/- (profit vs loss)
  | 'waterfall'
  | 'bullet'
  | 'line'
  | 'area'
  | 'scatter'
  | 'treemap'
  | 'funnel'
  | 'grouped'
  | 'stacked'
  | 'multiples'
  | 'kpi';

export interface Row {
  label: string;
  raw: Record<string, any>;
  value: number;
}

export interface ChartPlan {
  form: ChartForm;
  dimKey: string;
  valueKey: string;
  seriesKeys: string[];
  rows: Row[];
  unit: UnitInfo;
  target?: number;
  targetKey?: string;
  ordinal: boolean;
  timeLike: boolean;
  hasNegative: boolean;
  total: number;
  annotations: { x: any; label: string }[];
}

const ORDINAL_RE = /^(E\d+|W\d+|GRP-[A-Z]|FY\s?\d{2,4}(-\d{2})?|Q[1-4]|\d{4}(-\d{2})?|[<>≤≥]\s?\d+|\d+\s?[-–]\s?\d+|\d+\+?\s?(days|yrs?|years?)?)/i;
const TIME_KEY_RE = /(year|month|quarter|date|^fy$|fiscal|period)/i;
const HELPER_NUMERIC = /^(lat|lon|lng|weight|rank|id|order|sort)$/i;

function numericKeys(data: Record<string, any>[]): string[] {
  const keys = Object.keys(data[0] || {});
  return keys.filter((k) => {
    let n = 0;
    for (const r of data) if (toNumber(r[k]) !== null) n++;
    return n >= Math.max(1, Math.ceil(data.length * 0.8));
  });
}

function isTextKey(data: Record<string, any>[], k?: string): k is string {
  if (!k || !data.length || !(k in data[0])) return false;
  return data.some((r) => r[k] !== null && r[k] !== undefined && toNumber(r[k]) === null);
}

export function planChart(spec: ChartSpec): ChartPlan {
  const data = (spec.data || []).filter((r) => r && typeof r === 'object' && !Array.isArray(r));
  const nums = numericKeys(data);
  const keys = Object.keys(data[0] || {});

  // Dimension: requested category/x/y if textual, else first textual key
  const dimKey =
    [spec.category, spec.x, spec.y, (spec as any).label].find((k) => isTextKey(data, k)) ||
    keys.find((k) => isTextKey(data, k) && !/status|type|unit/i.test(k)) ||
    keys[0] ||
    'label';

  // Value: requested value/y/x if numeric, else first numeric non-helper key
  const valueKey =
    [spec.value, spec.y, spec.x].find((k) => k && nums.includes(k)) ||
    nums.find((k) => !HELPER_NUMERIC.test(k) && k !== dimKey) ||
    nums[0] ||
    'value';

  const unit = parseUnit(spec.unit, valueKey);

  let rows: Row[] = data.map((r) => ({ label: humanizeValue(r[dimKey]), raw: r, value: toNumber(r[valueKey]) ?? 0 }));
  const labels = rows.map((r) => r.label);
  const ordinal = labels.length > 0 && labels.filter((l) => ORDINAL_RE.test(l)).length >= Math.ceil(labels.length * 0.7);
  const timeLike =
    (TIME_KEY_RE.test(dimKey) || labels.filter((l) => /^(FY\s?\d{2}|\d{4}(-\d{2})?|Q[1-4]\s?\d{2,4}|[A-Z][a-z]{2}[- ]\d{2,4})/.test(l)).length >= Math.ceil(labels.length * 0.7)) &&
    rows.length >= 3;
  const hasNegative = rows.some((r) => r.value < 0);
  const avgLabelLen = labels.reduce((s, l) => s + l.length, 0) / Math.max(1, labels.length);

  const metricKeys = nums.filter((k) => k !== dimKey && !HELPER_NUMERIC.test(k));
  const kind = spec.kind;
  const hasType = data.some((r) => typeof r.type === 'string' && /total|loss|gain|delta|base/i.test(r.type));
  const targetKey = keys.find((k) => /^(target|target_pct|target_value)$/i.test(k));
  const hasTarget = spec.target !== undefined || !!targetKey;

  let form: ChartForm;
  let seriesKeys: string[] = [valueKey];

  if (data.length === 1 && kind !== 'bullet' && kind !== 'pie' && kind !== 'donut') {
    form = 'kpi';
  } else if (kind === 'pie') {
    form = 'pie';
  } else if (kind === 'donut') {
    form = 'donut';
  } else if (kind === 'histogram') {
    form = 'histogram';
  } else if (kind === 'area') {
    form = 'area';
  } else if (kind === 'scatter') {
    form = 'scatter';
    if (metricKeys.length >= 2) seriesKeys = metricKeys.slice(0, 3);
  } else if (kind === 'treemap') {
    form = 'treemap';
  } else if (kind === 'funnel') {
    form = 'funnel';
  } else if (kind === 'waterfall' || hasType) {
    form = 'waterfall';
  } else if (kind === 'bullet' || kind === 'gauge' || (hasTarget && /achiev|actual|pct/i.test(valueKey))) {
    form = 'bullet';
  } else if (kind === 'line') {
    if (metricKeys.length >= 2) seriesKeys = metricKeys.slice(0, 6);
    form = 'line';
  } else if (kind === 'bar') {
    form = 'column';
  } else if (kind === 'hbar') {
    form = hasNegative ? 'diverging' : 'ranked';
  } else if ((kind === 'grouped_bar' || kind === 'stacked_bar' || !!spec.series) && metricKeys.length >= 2) {
    seriesKeys = metricKeys.slice(0, 6);
    const anyNeg = data.some((r) => seriesKeys.some((k) => (toNumber(r[k]) ?? 0) < 0));
    if (kind === 'stacked_bar' && !anyNeg) form = 'stacked';
    else if (timeLike) form = 'line';
    else if (anyNeg && seriesKeys.length <= 4) form = 'multiples';
    else form = 'grouped';
  } else if (timeLike) {
    form = 'line';
  } else if (hasNegative) {
    form = 'diverging';
  } else if (spec.top_n || spec.sort === 'desc') {
    form = ordinal ? 'column' : 'ranked';
  } else if (ordinal && rows.length <= 16) {
    form = 'column';
  } else if (avgLabelLen > 10 || rows.length > 8) {
    form = 'ranked';
  } else if (rows.length <= 5 && rows.every((r) => r.value >= 0)) {
    form = 'donut';
  } else {
    form = 'ranked';
  }

  // Auto-bin into contiguous frequency intervals if form === 'histogram' and rows aren't already binned intervals
  const looksBinned =
    dimKey === 'bin' ||
    /bin|bucket|range|band|bracket/i.test(dimKey) ||
    labels.filter((l) => /[-–+<>≤≥]|\bto\b/i.test(l)).length >= Math.ceil(labels.length * 0.5);
  if (form === 'histogram' && !looksBinned && rows.length >= 5) {
    const vals = rows.map((r) => r.value).filter((v) => Number.isFinite(v));
    const minV = Math.min(...vals);
    const maxV = Math.max(...vals);
    if (maxV > minV) {
      const kBins0 = Math.min(8, Math.max(5, Math.round(Math.sqrt(vals.length) + 2)));
      // Integer data (ages, years, counts) → integer bin edges ("22–26"), never "22.0–26.8".
      const allInt = vals.every((v) => Number.isInteger(v));
      const step = allInt ? Math.max(1, Math.ceil((maxV - minV + 1) / kBins0)) : (maxV - minV) / kBins0;
      const kBins = allInt ? Math.ceil((maxV - minV + 1) / step) : kBins0;
      const sorted = [...vals].sort((a, b) => a - b);
      const mid = Math.floor(sorted.length / 2);
      const median = sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
      const mean = vals.reduce((s, v) => s + v, 0) / vals.length;
      const binned: Row[] = [];
      for (let i = 0; i < kBins; i++) {
        const lo = minV + i * step;
        const hi = allInt ? Math.min(maxV, lo + step - 1) : i === kBins - 1 ? maxV : minV + (i + 1) * step;
        const hits = rows.filter((r) =>
          allInt ? r.value >= lo && r.value <= hi : i === kBins - 1 ? r.value >= lo && r.value <= hi : r.value >= lo && r.value < hi,
        );
        const fmtB = (n: number) => (allInt || Math.abs(step) >= 10 ? fmtInt(Math.round(n)) : fmtNum(n, 1));
        const label = allInt && lo === hi ? fmtB(lo) : `${fmtB(lo)}–${fmtB(hi)}`;
        binned.push({
          label,
          value: hits.length,
          raw: {
            bin: label,
            count: hits.length,
            share_pct: Number(((hits.length / rows.length) * 100).toFixed(1)),
            members: hits.slice(0, 3).map((h) => h.label).join(', '),
            // value-axis stats for mean/median markers (category index space: bin i spans [i-0.5, i+0.5])
            ...(i === 0
              ? {
                  __stats: {
                    mean: (mean - minV) / step - 0.5,
                    median: (median - minV) / step - 0.5,
                    lo: -0.5,
                    hi: kBins - 0.5,
                    meanValue: mean,
                    medianValue: median,
                  },
                }
              : {}),
          },
        });
      }
      rows = binned;
    }
  }

  // Ranking order + top N
  if (form === 'ranked' || form === 'diverging' || form === 'funnel') {
    rows = [...rows].sort((a, b) => b.value - a.value);
    const topN = spec.top_n || (form === 'ranked' || form === 'funnel' ? 12 : 16);
    if (rows.length > topN) {
      if (form === 'diverging') {
        const pos = rows.filter((r) => r.value >= 0).slice(0, Math.ceil(topN / 2));
        const neg = rows.filter((r) => r.value < 0).slice(-Math.floor(topN / 2));
        rows = [...pos, ...neg];
      } else {
        const rest = rows.slice(topN - 1);
        rows = [...rows.slice(0, topN - 1), { label: `Others (${rest.length})`, raw: {}, value: rest.reduce((s, r) => s + r.value, 0) }];
      }
    }
  }
  if ((form === 'donut' || form === 'pie') && rows.length > 1 && !ordinal) {
    rows = [...rows].sort((a, b) => b.value - a.value);
    if (rows.length > 10) {
      const rest = rows.slice(9);
      rows = [...rows.slice(0, 9), { label: `Others (${rest.length})`, raw: {}, value: rest.reduce((s, r) => s + r.value, 0) }];
    }
  }

  const total = rows.reduce((s, r) => s + r.value, 0);
  return {
    form,
    dimKey,
    valueKey,
    seriesKeys,
    rows,
    unit,
    target: spec.target,
    targetKey,
    ordinal,
    timeLike,
    hasNegative,
    total,
    annotations: spec.annotations || [],
  };
}
