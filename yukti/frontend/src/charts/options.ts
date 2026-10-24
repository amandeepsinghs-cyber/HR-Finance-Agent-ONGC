/**
 * ECharts option builders for each chart form. All builders return a complete option
 * (every replaceable component present) so the renderer can morph between forms.
 */
import * as echarts from 'echarts';
import { ChartPlan, Row } from './plan';
import { ChartTokens, px, hGradient, vGradient, tooltipBase, tooltipCard, anim, alpha, labelOn } from './theme';
import { fmtValue, fmtNum, fmtShare, sharePct, humanizeKey, humanizeValue, toNumber, UnitInfo } from './format';

type Opt = echarts.EChartsOption;

/** BUG-43: legend entries show display names, never raw data keys; the unit lives on the value axis, so the
 * "(₹ Cr)" / "(%)" / "($)" suffix that humanizeKey adds is dropped here. */
export function legendName(key: string): string {
  return humanizeKey(key).replace(/\s\((₹ Cr|%|\$)\)$/, '');
}

function base(t: ChartTokens): Opt {
  return {
    backgroundColor: 'transparent',
    textStyle: { fontFamily: t.font, color: t.text },
    ...anim(),
    title: [],
    legend: [],
    graphic: [],
    grid: [],
    xAxis: [],
    yAxis: [],
    series: [],
    dataZoom: [],
  } as Opt;
}

/** Rounded axis bounds on a 1/2/2.5/5 × 10ⁿ step (≈ `ticks` intervals) that contain [lo, hi]. */
export function niceBounds(lo: number, hi: number, ticks = 4): { min: number; max: number; interval: number } {
  const span = Math.max(1e-9, hi - lo);
  const raw = span / ticks;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) || 10 * mag;
  return { min: Math.floor(lo / step) * step, max: Math.ceil(hi / step) * step, interval: step };
}

/** Sequential ramp between two hex colours. */
export function ramp(from: string, to: string, n: number): string[] {
  const h = (c: string) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16));
  const a = h(from);
  const b = h(to);
  return Array.from({ length: n }, (_, i) => {
    const f = n === 1 ? 1 : i / (n - 1);
    const c = a.map((v, k) => Math.round(v + (b[k] - v) * f));
    return `#${c.map((v) => v.toString(16).padStart(2, '0')).join('')}`;
  });
}

function extraRows(raw: Record<string, any>, skip: string[], unitFor: (k: string) => UnitInfo): [string, string][] {
  const out: [string, string][] = [];
  for (const [k, v] of Object.entries(raw || {})) {
    if (skip.includes(k) || out.length >= 4) continue;
    if (/^(lat|lon|type)$/i.test(k)) continue;
    const n = toNumber(v);
    out.push([humanizeKey(k), n !== null ? fmtValue(n, unitFor(k)) : humanizeValue(v)]);
  }
  return out;
}

function unitForKey(plan: ChartPlan) {
  return (k: string): UnitInfo => {
    if (k === plan.valueKey) return plan.unit;
    if (/_cr$|crore/i.test(k)) return { kind: 'currency', noun: '', label: '₹ Crore' };
    if (/pct|%|percent|rate/i.test(k)) return { kind: 'percent', noun: '', label: '%' };
    return { kind: 'count', noun: '', label: '' };
  };
}

function valueAxis(t: ChartTokens, unit: UnitInfo, horizontal: boolean, extra: Partial<echarts.XAXisComponentOption> = {}): any {
  return {
    type: 'value',
    name: unit.label || undefined,
    nameLocation: 'end',
    nameGap: px(t, horizontal ? 12 : 14),
    nameTextStyle: { color: t.sub, fontSize: px(t, 12), align: horizontal ? 'right' : 'left', padding: horizontal ? [px(t, 28), 0, 0, 0] : 0 },
    splitNumber: 4,
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: t.grid, type: [4, 4] } },
    axisLabel: { color: t.sub, fontSize: px(t, 12), formatter: (v: number) => fmtValue(v, unit, { compact: true }) },
    ...extra,
  };
}

function categoryAxis(t: ChartTokens, labels: string[], horizontal: boolean, maxLabelPx = 200, wrap = false): any {
  // Rubric C3: never hide or overlap category labels. Crowded vertical axes rotate (with truncation);
  // short sets wrap. (Long categorical labels are better as H-bar; the planner prefers that in U5.7.)
  // `wrap` (horizontal only): long names break onto two lines instead of truncating (bullet KPIs).
  const totalChars = labels.reduce((n, l) => n + String(l).length, 0);
  const crowded = !horizontal && (totalChars > 56 || (labels.length > 4 && labels.some((l) => String(l).length > 12)));
  return {
    type: 'category',
    data: labels,
    inverse: horizontal,
    axisTick: { show: false },
    axisLine: { show: !horizontal, lineStyle: { color: t.axis } },
    axisLabel: {
      color: t.text,
      fontSize: px(t, 13),
      fontWeight: 500,
      margin: px(t, 12),
      interval: 0,
      hideOverlap: false,
      ...(horizontal
        ? wrap
          ? { width: px(t, maxLabelPx), overflow: 'break', lineHeight: px(t, 17) }
          : { width: px(t, maxLabelPx), overflow: 'truncate', ellipsis: '…' }
        : crowded
          ? { rotate: 30, width: px(t, 120), overflow: 'truncate', ellipsis: '…', fontSize: px(t, 12) }
          : { width: px(t, 110), overflow: 'break', lineHeight: px(t, 16) }),
    },
  };
}

function pill(t: ChartTokens, color: string) {
  return {
    color: t.onAccent,
    backgroundColor: color,
    borderRadius: px(t, 10),
    padding: [px(t, 3), px(t, 8)],
    fontSize: px(t, 11),
    fontWeight: 600 as const,
  };
}

/** Horizontal ranked bars; diverging colours when values are negative. */
export function rankedOption(plan: ChartPlan, t: ChartTokens, opts: { compact?: boolean; title?: string; labelPx?: number; domain?: { min: number; max: number } } = {}): Opt {
  const others = (r: Row) => /^(all\s+)?others?(\s*\(.*\))?$/i.test(r.label.trim());
  // Rubric C1: an aggregate "Others" bucket is never ranked; pin it last (bottom) and exclude it
  // from max/min/average so it can't be tagged "Highest" or skew the reference line.
  const rows = [...plan.rows.filter((r) => !others(r)), ...plan.rows.filter(others)];
  const unit = plan.unit;
  const n = rows.length;
  const ranked = rows.filter((r) => !others(r));
  const rankedValues = ranked.length ? ranked.map((r) => r.value) : rows.map((r) => r.value);
  const values = rows.map((r) => r.value);
  const maxV = Math.max(...values);
  const minV = Math.min(...values);
  const diverging = minV < 0;
  const avg = rankedValues.reduce((s, v) => s + v, 0) / Math.max(1, rankedValues.length);
  const rankedMax = Math.max(...rankedValues);
  const rankedMin = Math.min(...rankedValues);
  const iMax = rows.findIndex((r) => !others(r) && r.value === rankedMax);
  const iMin = rows.findIndex((r) => !others(r) && r.value === rankedMin);

  const data = rows.map((r, i) => {
    const neg = r.value < 0;
    let color: any = neg ? hGradient(t.maroonSoft, t.maroon) : hGradient(t.accentSoft, t.accent);
    if (!diverging && i === iMax) color = hGradient(t.accent, t.accentDeep);
    if (neg) color = new echarts.graphic.LinearGradient(1, 0, 0, 0, [
      { offset: 0, color: t.maroonSoft },
      { offset: 1, color: t.maroon },
    ]);
    if (others(r)) color = t.faint;
    const tag = !opts.compact && n >= 3 ? (diverging ? (i === iMin ? 'loss' : i === iMax ? 'top' : '') : i === iMax ? 'top' : '') : '';
    const tinyNeg = neg && Math.abs(r.value) < Math.max(1, maxV) * 0.25;
    return {
      value: r.value,
      name: r.label,
      raw: r.raw,
      tag,
      tinyNeg,
      itemStyle: { color, borderRadius: neg ? [px(t, 8), 0, 0, px(t, 8)] : [0, px(t, 8), px(t, 8), 0] },
      label: { position: neg && !tinyNeg ? 'left' : 'right' },
    };
  });

  const markLines: any[] = [];
  if (diverging) markLines.push({ xAxis: 0, lineStyle: { color: t.sub, type: 'solid', width: 1.2 }, label: { show: false } });
  else if (n >= 4 && !opts.compact)
    markLines.push({
      xAxis: avg,
      lineStyle: { color: t.sub, type: [5, 4], width: 1.2 },
      // Rubric C3: label sits at the top end of the line (category axis is inverted), on a halo,
      // so it never collides with the value-axis tick labels at the bottom.
      label: {
        formatter: `Avg ${fmtValue(avg, unit)}`,
        position: 'start',
        distance: px(t, 6),
        color: t.sub,
        fontSize: px(t, 11),
        fontWeight: 500,
        backgroundColor: t.labelHalo,
        padding: [px(t, 2), px(t, 6)],
        borderRadius: px(t, 6),
      },
    });

  const absMax = Math.max(Math.abs(maxV), Math.abs(minV));
  const tagged = !opts.compact && n >= 3;
  // Asymmetric domain: room on each side for value labels (+ callout pills)
  const allNegOrZero = maxV <= 0;
  // opts.domain: a shared domain (small multiples) so bar lengths compare across panels.
  const xMin = opts.domain ? opts.domain.min : diverging ? (allNegOrZero ? minV * 1.48 : Math.min(minV * (opts.compact ? 1.5 : 1.25), -absMax * 0.12)) : 0;
  const xMax = opts.domain ? opts.domain.max : allNegOrZero ? absMax * 0.25 : Math.max(maxV, 0) * (tagged ? 1.12 : 1.15) || absMax * 0.3;
  return {
    ...base(t),
    title: opts.title
      ? [{ text: opts.title, left: 0, top: 0, textStyle: { color: t.text, fontSize: px(t, 14), fontWeight: 600, fontFamily: t.font } }]
      : [],
    grid: [{ left: px(t, 8), right: px(t, opts.compact ? 48 : tagged ? 150 : 90), top: px(t, (opts.title ? 34 : 16) + (!diverging && n >= 4 && !opts.compact ? 18 : 0)), bottom: px(t, 28), containLabel: true }],
    xAxis: [
      valueAxis(t, unit, true, {
        min: xMin,
        max: xMax,
        name: undefined, // Rubric C3: tick labels already carry the unit; a name collides with the last tick
        axisLabel: { color: t.sub, fontSize: px(t, 11), formatter: (v: number) => fmtValue(v, unit, { compact: true }), showMinLabel: !diverging, showMaxLabel: false },
      } as any),
    ],
    yAxis: [categoryAxis(t, rows.map((r) => r.label), true, opts.labelPx || (opts.compact ? 130 : 210))],
    tooltip: {
      ...tooltipBase(t),
      trigger: 'item',
      formatter: (p: any) => {
        // Rubric C6: value, share and rank (aggregates and ± data have no meaningful share / rank).
        const isOthers = others({ label: String(p.name || ''), raw: {}, value: 0 });
        const allTotal = values.reduce((s, v) => s + v, 0);
        const rank = isOthers ? -1 : ranked.findIndex((r) => r.label === p.name);
        return tooltipCard(t, p.name, [
          [humanizeKey(plan.valueKey), fmtValue(p.value, unit, { withNoun: true })],
          ...(!diverging && allTotal > 0 ? ([['Share', fmtShare((p.value / allTotal) * 100)]] as [string, string][]) : []),
          ...(rank >= 0 && ranked.length > 1 ? ([['Rank', `${rank + 1} of ${ranked.length}`]] as [string, string][]) : []),
          ...extraRows(p.data?.raw, [plan.dimKey, plan.valueKey], unitForKey(plan)),
        ]);
      },
    },
    series: [
      {
        id: 'main',
        type: 'bar',
        data,
        barWidth: n <= 4 ? '46%' : '62%',
        barMaxWidth: px(t, 38),
        universalTransition: { enabled: true },
        showBackground: !diverging,
        backgroundStyle: { color: t.dark ? 'rgba(255,255,255,0.03)' : 'rgba(31,31,31,0.025)', borderRadius: [0, px(t, 8), px(t, 8), 0] },
        label: {
          show: true,
          distance: px(t, 8),
          color: t.text,
          fontSize: px(t, opts.compact ? 12 : 13),
          fontWeight: 600,
          // Rubric C3: a canvas-coloured halo box so the Avg reference line never runs through a value label.
          backgroundColor: t.labelHalo,
          padding: [px(t, 1), px(t, 4)],
          borderRadius: px(t, 4),
          formatter: (p: any) => {
            const v = fmtValue(p.value, unit, { sign: diverging });
            if (p.data?.tag === 'top') return p.value < 0 ? v : `${v}  {top|${diverging ? 'Top earner' : 'Highest'}}`;
            if (p.data?.tag === 'loss') return p.data?.tinyNeg ? `${v}  {loss|Largest loss}` : `{loss|Largest loss}  ${v}`;
            return v;
          },
          rich: { top: { ...pill(t, t.accentDeep), textBorderWidth: 0 }, loss: { ...pill(t, t.maroon), textBorderWidth: 0 } },
        },
        // z 1: reference lines sit beneath bars and labels (subtle guide, never over a value).
        markLine: markLines.length ? { symbol: 'none', silent: true, z: 1, data: markLines, animation: true } : undefined,
      } as any,
    ],
  };
}

/** Vertical columns for ordinal categories (grades, ageing buckets). */
export function columnOption(plan: ChartPlan, t: ChartTokens): Opt {
  // Rubric C1: nominal categories are ranked (desc); ordinal/time categories keep their natural order.
  const rows = plan.ordinal || plan.timeLike ? plan.rows : [...plan.rows].sort((a, b) => b.value - a.value);
  const unit = plan.unit;
  const values = rows.map((r) => r.value);
  const maxV = Math.max(...values);
  const iMax = values.indexOf(maxV);
  const avg = values.reduce((s, v) => s + v, 0) / Math.max(1, values.length);
  return {
    ...base(t),
    grid: [{ left: px(t, 28), right: px(t, 24), top: px(t, 56), bottom: px(t, 8), containLabel: true }],
    xAxis: [categoryAxis(t, rows.map((r) => r.label), false)],
    yAxis: [valueAxis(t, unit, false, { max: maxV * 1.18, nameLocation: 'middle', nameRotate: 90, nameGap: px(t, 44), nameTextStyle: { color: t.sub, fontSize: px(t, 12) }, axisLabel: { color: t.sub, fontSize: px(t, 12), showMaxLabel: false, formatter: (v: number) => fmtValue(v, unit, { compact: true }) } } as any)],
    tooltip: {
      ...tooltipBase(t),
      trigger: 'item',
      formatter: (p: any) =>
        tooltipCard(t, p.name, [
          [humanizeKey(plan.valueKey), fmtValue(p.value, unit, { withNoun: true })],
          ['Share', sharePct(p.value, Math.max(1, plan.total))],
          ...extraRows(p.data?.raw, [plan.dimKey, plan.valueKey], unitForKey(plan)),
        ]),
    },
    series: [
      {
        id: 'main',
        type: 'bar',
        universalTransition: { enabled: true },
        barWidth: rows.length <= 5 ? '42%' : '58%',
        barMaxWidth: px(t, 64),
        data: rows.map((r, i) => ({
          value: r.value,
          name: r.label,
          raw: r.raw,
          itemStyle: {
            color: i === iMax ? vGradient(t.accentDeep, t.accent) : vGradient(t.accent, t.accentSoft),
            borderRadius: [px(t, 8), px(t, 8), px(t, 2), px(t, 2)],
          },
        })),
        label: {
          show: true,
          position: 'top',
          distance: px(t, 6),
          color: t.text,
          fontSize: px(t, 13),
          fontWeight: 600,
          textBorderColor: t.labelHalo,
          textBorderWidth: 3,
          formatter: (p: any) => (p.dataIndex === iMax && rows.length >= 3 ? `{top|Peak}\n${fmtValue(p.value, unit)}` : fmtValue(p.value, unit)),
          rich: { top: { ...pill(t, t.accentDeep), lineHeight: px(t, 26), textBorderWidth: 0 } },
        },
        markLine:
          rows.length >= 4
            ? {
                symbol: 'none',
                silent: true,
                data: [
                  {
                    yAxis: avg,
                    lineStyle: { color: t.sub, type: [5, 4], width: 1.2 },
                    label: { formatter: `Avg ${fmtValue(avg, unit)}`, position: 'insideEndTop', color: t.sub, fontSize: px(t, 11) },
                  },
                ],
              }
            : undefined,
      } as any,
    ],
  };
}

/** Donut with centre total; legend rendered as HTML by the renderer. */
export function donutOption(plan: ChartPlan, t: ChartTokens, colors: string[]): Opt {
  const unit = plan.unit;
  const s = t.scale;
  return {
    ...base(t),
    color: colors,
    tooltip: {
      ...tooltipBase(t),
      trigger: 'item',
      formatter: (p: any) =>
        tooltipCard(t, p.name, [
          [humanizeKey(plan.valueKey), fmtValue(p.value, unit, { withNoun: true }), p.color],
          ['Share', fmtShare(p.percent)],
          ...extraRows(p.data?.raw, [plan.dimKey, plan.valueKey], unitForKey(plan)),
        ]),
    },
    graphic: [
      {
        type: 'group',
        left: 'center',
        top: 'middle',
        children: [
          {
            type: 'text',
            left: 'center',
            top: -Math.round(22 * s),
            style: { text: fmtValue(plan.total, unit), fill: t.text, font: `700 ${Math.round(40 * s)}px 'Google Sans', Inter, sans-serif`, textAlign: 'center' },
          },
          {
            type: 'text',
            left: 'center',
            top: Math.round(26 * s),
            style: { text: (unit.noun || 'Total').replace(/^\w/, (c) => c.toUpperCase()), fill: t.sub, font: `500 ${Math.round(14 * s)}px 'Google Sans Text', Inter, sans-serif`, textAlign: 'center' },
          },
        ],
      } as any,
    ],
    series: [
      {
        id: 'main',
        type: 'pie',
        radius: ['60%', '86%'],
        center: ['50%', '50%'],
        padAngle: 1.2,
        minAngle: 3,
        universalTransition: { enabled: true },
        itemStyle: { borderRadius: Math.round(6 * s), borderColor: t.surface, borderWidth: 2 },
        label: { show: false },
        labelLine: { show: false },
        emphasis: { scale: true, scaleSize: Math.round(6 * s), itemStyle: { shadowBlur: 16, shadowColor: t.shadowAccent } },
        data: plan.rows.map((r) => ({ name: r.label, value: r.value, raw: r.raw })),
        animationType: 'expansion',
      } as any,
    ],
  };
}

/** Waterfall with connectors; appends a net total when the data has none. */
export function waterfallOption(plan: ChartPlan, t: ChartTokens): Opt {
  const unit = plan.unit;
  type Step = { label: string; start: number; end: number; kind: 'pos' | 'neg' | 'total'; v: number; raw: any };
  const steps: Step[] = [];
  let running = 0;
  let hasTotal = false;
  let sourceRows = plan.rows;
  if (sourceRows.length > 9 && !sourceRows.some((r) => /total|base|start|end/i.test(String(r.raw?.type || '')))) {
    const top8 = sourceRows.slice(0, 8);
    const rest = sourceRows.slice(8);
    const restSum = Number(rest.reduce((s, r) => s + r.value, 0).toFixed(2));
    sourceRows = [...top8, { label: `Others (${rest.length})`, value: restSum, raw: {} }];
  }
  sourceRows.forEach((r) => {
    const typ = String(r.raw?.type || '').toLowerCase();
    if (/total|base|start|end/.test(typ)) {
      hasTotal = true;
      steps.push({ label: r.label, start: 0, end: r.value, kind: 'total', v: r.value, raw: r.raw });
      running = r.value;
    } else {
      steps.push({ label: r.label, start: running, end: running + r.value, kind: r.value >= 0 ? 'pos' : 'neg', v: r.value, raw: r.raw });
      running += r.value;
    }
  });
  if (!hasTotal && steps.length >= 2) steps.push({ label: 'Total', start: 0, end: running, kind: 'total', v: running, raw: {} });

  const lo = Math.min(0, ...steps.map((s) => Math.min(s.start, s.end)));
  const hi = Math.max(0, ...steps.map((s) => Math.max(s.start, s.end)));
  const pad = (hi - lo) * 0.08 || 1;
  // Rubric C3: rounded axis ends (₹50,000 not ₹46,423) — nice step from the padded span.
  const nice = niceBounds(lo < 0 ? lo - pad : 0, hi > 0 ? hi + pad : pad, 5);

  const colorOf = (k: Step['kind'], v: number) =>
    k === 'total' ? (v < 0 ? t.maroon : t.accentDeep) : k === 'pos' ? t.accent : t.maroonSoft;

  return {
    ...base(t),
    grid: [{ left: px(t, 8), right: px(t, 24), top: px(t, 36), bottom: px(t, 8), containLabel: true }],
    xAxis: [categoryAxis(t, steps.map((s) => s.label), false)],
    // Tick labels already carry "₹ … Cr"; an axis name would be redundant (reviewer C3).
    yAxis: [valueAxis(t, unit, false, { name: undefined, min: nice.min, max: nice.max, interval: nice.interval } as any)],
    tooltip: {
      ...tooltipBase(t),
      trigger: 'item',
      formatter: (p: any) => {
        const s = steps[p.dataIndex];
        return tooltipCard(t, s.label, [
          [s.kind === 'total' ? 'Total' : 'Change', fmtValue(s.v, unit, { sign: s.kind !== 'total' })],
          ...(s.kind !== 'total' ? ([['Running total', fmtValue(s.end, unit)]] as [string, string][]) : []),
          ...extraRows(s.raw, [plan.dimKey, plan.valueKey], unitForKey(plan)),
        ]);
      },
    },
    series: [
      {
        id: 'main',
        type: 'custom',
        universalTransition: { enabled: true },
        data: steps.map((s, i) => [i, s.start, s.end]),
        encode: { x: 0, y: [1, 2] },
        renderItem: (params: any, api: any) => {
          const i = api.value(0);
          const s = steps[i];
          const a = api.coord([i, s.start]);
          const b = api.coord([i, s.end]);
          const band = api.size([1, 0])[0];
          const w = Math.min(band * 0.58, px(t, 84));
          const top = Math.min(a[1], b[1]);
          const h = Math.max(2, Math.abs(a[1] - b[1]));
          const r = Math.min(px(t, 8), h / 2);
          const color = colorOf(s.kind, s.v);
          const children: any[] = [
            {
              type: 'rect',
              shape: { x: a[0] - w / 2, y: top, width: w, height: h, r },
              style: {
                fill:
                  s.kind === 'total'
                    ? new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color },
                        { offset: 1, color: s.v < 0 ? t.maroonSoft : t.accent },
                      ])
                    : color,
                opacity: s.kind === 'total' ? 1 : 0.92,
              },
            },
            {
              type: 'text',
              style: {
                // P4.1 (SPEC-09 §4.3): accounting labels — deductions read "(₹x Cr)", additions "+₹x Cr", totals plain
                text: s.kind === 'total' ? fmtValue(s.v, unit) : s.v < 0 ? `(${fmtValue(Math.abs(s.v), unit)})` : fmtValue(s.v, unit, { sign: true }),
                x: a[0],
                y: s.end >= s.start ? top - px(t, 8) : top + h + px(t, 8),
                textAlign: 'center',
                textVerticalAlign: s.end >= s.start ? 'bottom' : 'top',
                fill: s.kind === 'total' ? color : t.text,
                font: `${s.kind === 'total' ? 700 : 600} ${px(t, s.kind === 'total' ? 15 : 13)}px 'Google Sans', Inter, sans-serif`,
              },
            },
          ];
          if (i < steps.length - 1) {
            const next = steps[i + 1];
            const yLevel = b[1];
            const nextStartY = api.coord([i + 1, next.kind === 'total' ? s.end : next.start])[1];
            children.push({
              type: 'line',
              shape: { x1: a[0] + w / 2, y1: yLevel, x2: a[0] + band - w / 2, y2: nextStartY },
              style: { stroke: t.sub, lineWidth: 1, lineDash: [3, 3], opacity: 0.7 },
            });
          }
          return { type: 'group', children };
        },
      } as any,
      {
        id: 'zero',
        type: 'line',
        data: [],
        markLine: { symbol: 'none', silent: true, data: [{ yAxis: 0 }], lineStyle: { color: t.sub, width: 1.2, type: 'solid' }, label: { show: false } },
      } as any,
    ],
  };
}

/** Bullet charts: qualitative bands, actual bar and target tick per row. */
export function bulletOption(plan: ChartPlan, t: ChartTokens): Opt {
  const unit = plan.unit.kind === 'count' && /pct|achiev/i.test(plan.valueKey) ? ({ kind: 'percent', noun: '', label: '% of target' } as UnitInfo) : plan.unit;
  const rows = plan.rows;
  const targets = rows.map((r) => toNumber(plan.targetKey ? r.raw?.[plan.targetKey] : undefined) ?? plan.target ?? 100);
  const maxV = Math.max(...rows.map((r) => r.value), ...targets) * 1.1;
  // Rubric C1: the worst performer (lowest actual / target) gets an outline so the eye lands on it first.
  const ratios = rows.map((r, i) => r.value / Math.max(1e-9, targets[i]));
  const iWorst = rows.length >= 3 ? ratios.indexOf(Math.min(...ratios)) : -1;
  return {
    ...base(t),
    grid: [{ left: px(t, 20), right: px(t, 70), top: px(t, 36), bottom: px(t, 40), containLabel: true }],
    xAxis: [
      valueAxis(t, unit, true, {
        min: 0,
        max: Math.ceil(maxV / 10) * 10,
        nameLocation: 'middle',
        nameGap: px(t, 34),
        nameTextStyle: { color: t.sub, fontSize: px(t, 12) },
      } as any),
    ],
    yAxis: [categoryAxis(t, rows.map((r) => r.label), true, 200, true)],
    tooltip: {
      ...tooltipBase(t),
      trigger: 'item',
      formatter: (p: any) => {
        const r = rows[p.dataIndex];
        return tooltipCard(t, r.label, [
          [humanizeKey(plan.valueKey), fmtValue(r.value, unit)],
          ['Target', fmtValue(targets[p.dataIndex], unit)],
          ...extraRows(r.raw, [plan.dimKey, plan.valueKey, plan.targetKey || ''], unitForKey(plan)),
        ]);
      },
    },
    legend: [],
    series: [
      {
        id: 'main',
        type: 'custom',
        universalTransition: { enabled: true },
        data: rows.map((r, i) => [r.value, i, targets[i]]),
        encode: { x: [0, 2], y: 1 },
        renderItem: (params: any, api: any) => {
          const i = api.value(1);
          const v = api.value(0);
          const T = api.value(2);
          const bandH = api.size([0, 1])[1];
          const y = api.coord([0, i])[1];
          const x0 = api.coord([0, i])[0];
          const xEnd = api.coord([maxV, i])[0];
          const hB = Math.min(bandH * 0.62, px(t, 40));
          const hA = hB * 0.42;
          const zones = [0, T * 0.8, T * 0.9, Math.ceil(maxV / 10) * 10];
          const children: any[] = [];
          for (let z = 0; z < 3; z++) {
            const xa = api.coord([zones[z], i])[0];
            const xb = z === 2 ? xEnd : api.coord([zones[z + 1], i])[0];
            children.push({
              type: 'rect',
              shape: { x: xa, y: y - hB / 2, width: Math.max(0, xb - xa), height: hB, r: z === 0 ? [px(t, 6), 0, 0, px(t, 6)] : z === 2 ? [0, px(t, 6), px(t, 6), 0] : 0 },
              style: { fill: t.band[2 - z] },
              silent: true,
            });
          }
          if (i === iWorst) {
            const xa0 = api.coord([0, i])[0];
            children.push({
              type: 'rect',
              shape: { x: xa0 - px(t, 3), y: y - hB / 2 - px(t, 3), width: xEnd - xa0 + px(t, 6), height: hB + px(t, 6), r: px(t, 8) },
              style: { fill: 'transparent', stroke: t.text, lineWidth: px(t, 1.5) },
              silent: true,
            });
          }
          const xv = api.coord([v, i])[0];
          const ok = v >= T;
          const near = v >= T * 0.9;
          children.push({
            type: 'rect',
            shape: { x: x0, y: y - hA / 2, width: Math.max(2, xv - x0), height: hA, r: [0, px(t, 5), px(t, 5), 0] },
            style: { fill: ok ? hGradient(t.accent, t.accentDeep) : near ? hGradient(t.accentSoft, t.accent) : hGradient(t.maroonSoft, t.maroon) },
          });
          const xt = api.coord([T, i])[0];
          children.push({
            type: 'rect',
            shape: { x: xt - px(t, 1.5), y: y - hB * 0.48, width: px(t, 3), height: hB * 0.96, r: px(t, 1.5) },
            style: { fill: t.text },
          });
          children.push({
            type: 'text',
            style: {
              text: fmtValue(v, unit),
              x: Math.max(xv, xt) + px(t, 10),
              y,
              textVerticalAlign: 'middle',
              fill: ok ? t.accentDeep : near ? t.text : t.maroon,
              font: `700 ${px(t, 14)}px 'Google Sans', Inter, sans-serif`,
            },
          });
          return { type: 'group', children };
        },
      } as any,
    ],
    graphic: [
      {
        type: 'group',
        right: px(t, 8),
        top: 0,
        children: [
          { type: 'rect', shape: { x: 0, y: px(t, 4), width: px(t, 3), height: px(t, 14) }, style: { fill: t.text } },
          { type: 'text', style: { text: 'Target', x: px(t, 8), y: px(t, 4), fill: t.sub, font: `500 ${px(t, 12)}px 'Google Sans Text', Inter, sans-serif` } },
          { type: 'rect', shape: { x: px(t, 64), y: px(t, 6), width: px(t, 18), height: px(t, 10), r: 3 }, style: { fill: t.accent } },
          { type: 'text', style: { text: 'Actual', x: px(t, 88), y: px(t, 4), fill: t.sub, font: `500 ${px(t, 12)}px 'Google Sans Text', Inter, sans-serif` } },
        ],
      } as any,
    ],
  };
}

/** Line / area for time series (single or multi series). */
export function lineOption(plan: ChartPlan, t: ChartTokens, data: Record<string, any>[]): Opt {
  const labels = data.map((r) => humanizeValue(r[plan.dimKey]));
  const keys = plan.seriesKeys.length ? plan.seriesKeys : [plan.valueKey];
  const single = keys.length === 1;
  // Rubric C4: series colours from the categorical palette (maroon is reserved for loss/negative).
  const colors = t.categorical;
  return {
    ...base(t),
    color: colors,
    grid: [{ left: px(t, 8), right: px(t, single ? 112 : 132), top: px(t, single ? 36 : 48), bottom: px(t, 8), containLabel: true }],
    legend: single ? [] : [{ top: 0, left: 0, icon: 'roundRect', itemWidth: px(t, 14), itemHeight: px(t, 6), textStyle: { color: t.sub, fontSize: px(t, 12) }, formatter: legendName }],
    xAxis: [{ ...categoryAxis(t, labels, false), boundaryGap: false }],
    yAxis: [valueAxis(t, plan.unit, false, { scale: true } as any)],
    tooltip: {
      ...tooltipBase(t),
      trigger: 'axis',
      axisPointer: { type: 'line', lineStyle: { color: t.axis } },
      formatter: (ps: any) => {
        const arr = Array.isArray(ps) ? ps : [ps];
        return tooltipCard(t, arr[0]?.name || '', arr.map((p: any) => [humanizeKey(p.seriesName), fmtValue(p.value, plan.unit), p.color]));
      },
    },
    series: keys.map((k, idx) => ({
      id: idx === 0 ? 'main' : `s${idx}`,
      name: k,
      type: 'line',
      smooth: 0.25,
      smoothMonotone: 'x',
      symbol: 'circle',
      symbolSize: px(t, 7),
      showSymbol: labels.length <= 24,
      universalTransition: { enabled: true },
      lineStyle: { width: px(t, 3) },
      areaStyle: single
        ? { color: vGradient(alpha(t.accent, t.dark ? 0.35 : 0.28), alpha(t.accent, 0)) }
        : undefined,
      endLabel: { show: true, formatter: (p: any) => fmtValue(p.value, plan.unit), color: colors[idx % colors.length], fontWeight: 700, fontSize: px(t, 13) },
      data: data.map((r) => toNumber(r[k])),
      markPoint:
        single && labels.length >= 4
          ? {
              symbol: 'roundRect',
              symbolSize: [px(t, 44), px(t, 22)],
              itemStyle: { color: t.accentDeep },
              label: { color: t.onAccent, fontSize: px(t, 11), fontWeight: 600, formatter: 'Peak' },
              data: [{ type: 'max', symbolOffset: [0, -px(t, 20)] }],
            }
          : undefined,
    })) as any,
  };
}

/** Grouped bars (all-positive multi-metric). */
export function groupedOption(plan: ChartPlan, t: ChartTokens, data: Record<string, any>[]): Opt {
  const labels = data.map((r) => humanizeValue(r[plan.dimKey]));
  const horizontal = labels.reduce((s, l) => s + l.length, 0) / Math.max(1, labels.length) > 10;
  const colors = t.categorical;
  const ax = categoryAxis(t, labels, horizontal);
  // Rubric C3: the unit name sits centred along the value axis, never in the legend row.
  const vx = valueAxis(t, plan.unit, horizontal, {
    nameLocation: 'middle',
    nameRotate: horizontal ? 0 : 90,
    nameGap: px(t, horizontal ? 32 : 48),
    nameTextStyle: { color: t.sub, fontSize: px(t, 12) },
  } as any);
  return {
    ...base(t),
    color: colors,
    legend: [{ top: 0, left: 0, icon: 'roundRect', itemWidth: px(t, 14), itemHeight: px(t, 10), textStyle: { color: t.sub, fontSize: px(t, 12) }, formatter: legendName }],
    grid: [{ left: px(t, horizontal ? 8 : 20), right: px(t, 40), top: px(t, 48), bottom: px(t, horizontal ? 36 : 8), containLabel: true }],
    xAxis: [horizontal ? vx : ax],
    yAxis: [horizontal ? ax : vx],
    tooltip: {
      ...tooltipBase(t),
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: t.dark ? 'rgba(255,255,255,0.04)' : alpha(t.accent, 0.06) } },
      formatter: (ps: any) => tooltipCard(t, ps[0]?.name, ps.map((p: any) => [humanizeKey(p.seriesName), fmtValue(p.value, unitForKey(plan)(p.seriesName)), p.color])),
    },
    series: plan.seriesKeys.map((k, idx) => ({
      id: idx === 0 ? 'main' : `s${idx}`,
      name: k,
      type: 'bar',
      barGap: '18%',
      barMaxWidth: px(t, 28),
      universalTransition: { enabled: true },
      itemStyle: { borderRadius: horizontal ? [0, px(t, 6), px(t, 6), 0] : [px(t, 6), px(t, 6), 0, 0] },
      label: { show: data.length * plan.seriesKeys.length <= 18, position: horizontal ? 'right' : 'top', color: t.text, fontSize: px(t, 12), fontWeight: 500, formatter: (p: any) => fmtValue(p.value, unitForKey(plan)(k), { compact: true }) },
      data: data.map((r) => toNumber(r[k])),
    })) as any,
  };
}

/** Horizontal stacked bars (e.g. receivables ageing) with severity ramp and totals. */
export function stackedOption(plan: ChartPlan, t: ChartTokens, data: Record<string, any>[]): Opt {
  const keys = plan.seriesKeys;
  const sorted = [...data].sort((a, b) => keys.reduce((s, k) => s + (toNumber(b[k]) || 0), 0) - keys.reduce((s, k) => s + (toNumber(a[k]) || 0), 0)).slice(0, 12);
  const labels = sorted.map((r) => humanizeValue(r[plan.dimKey]));
  // Severity = buckets beyond 90 days (lower bound ≥ 90: "91-180", ">180", "180+ days", "overdue"). Severity
  // shades run maroonSoft → maroon so the oldest bucket is the darkest; current buckets use the blue ramp.
  const lowerBound = (k: string) => {
    const m = String(k).match(/\d+/);
    return m ? parseInt(m[0], 10) : NaN;
  };
  const severe = (k: string) => /overdue/i.test(k) || lowerBound(k) >= 90;
  const nSevere = keys.filter(severe).length;
  const blues = ramp(t.sequential[t.dark ? 0 : 2], t.sequential[t.dark ? 4 : 5], Math.max(1, keys.length - nSevere));
  const reds = nSevere === 1 ? [t.maroon] : ramp(t.maroonSoft, t.maroon, Math.max(1, nSevere));
  let bi = 0;
  let ri = 0;
  const colors = keys.map((k) => (severe(k) ? reds[ri++] : blues[bi++]));
  const totals = sorted.map((r) => keys.reduce((s, k) => s + (toNumber(r[k]) || 0), 0));
  const unit = plan.unit.kind === 'count' && /cr|₹/i.test(String(plan.unit.label)) ? plan.unit : plan.unit;
  return {
    ...base(t),
    color: colors,
    legend: [{ top: 0, left: 0, icon: 'roundRect', itemWidth: px(t, 14), itemHeight: px(t, 10), textStyle: { color: t.sub, fontSize: px(t, 12) }, data: keys, formatter: legendName }],
    grid: [{ left: px(t, 8), right: px(t, 90), top: px(t, 44), bottom: px(t, 8), containLabel: true }],
    xAxis: [valueAxis(t, unit, true, { name: undefined } as any)],
    yAxis: [categoryAxis(t, labels, true, 200)],
    tooltip: {
      ...tooltipBase(t),
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: t.dark ? 'rgba(255,255,255,0.04)' : alpha(t.accent, 0.06) } },
      formatter: (ps: any) => {
        const arr = (ps as any[]).filter((p) => p.seriesId !== 'total');
        const tot = totals[arr[0]?.dataIndex] || 0;
        return tooltipCard(t, arr[0]?.name, [...arr.map((p: any) => [humanizeKey(p.seriesName), fmtValue(p.value, unit), p.color] as [string, string, string]), ['Total', fmtValue(tot, unit)]]);
      },
    },
    series: [
      ...keys.map((k, idx) => ({
        id: idx === 0 ? 'main' : `s${idx}`,
        name: k,
        type: 'bar',
        stack: 'total',
        barWidth: '58%',
        barMaxWidth: px(t, 34),
        universalTransition: { enabled: true },
        itemStyle: { borderColor: t.surface, borderWidth: 1, borderRadius: idx === keys.length - 1 ? [0, px(t, 6), px(t, 6), 0] : 0 },
        emphasis: { focus: 'series' },
        data: sorted.map((r) => toNumber(r[k]) || 0),
      })),
      {
        id: 'total',
        type: 'bar',
        stack: 'total',
        data: sorted.map(() => 0),
        label: { show: true, position: 'right', color: t.text, fontWeight: 700, fontSize: px(t, 13), formatter: (p: any) => fmtValue(totals[p.dataIndex], unit) },
        tooltip: { show: false },
      },
    ] as any,
  };
}

/** Classic full-radius Pie chart with outside leader callouts + interactive legend. */
export function pieOption(plan: ChartPlan, t: ChartTokens, colors: string[]): Opt {
  const unit = plan.unit;
  const s = t.scale;
  return {
    ...base(t),
    color: colors,
    tooltip: {
      ...tooltipBase(t),
      trigger: 'item',
      formatter: (p: any) =>
        tooltipCard(t, p.name, [
          [humanizeKey(plan.valueKey), fmtValue(p.value, unit, { withNoun: true }), p.color],
          ['Share', fmtShare(p.percent)],
          ...extraRows(p.data?.raw, [plan.dimKey, plan.valueKey], unitForKey(plan)),
        ]),
    },
    series: [
      {
        id: 'main',
        type: 'pie',
        radius: ['0%', '62%'],
        center: ['50%', '50%'],
        minAngle: 4,
        universalTransition: { enabled: true },
        itemStyle: { borderRadius: Math.round(5 * s), borderColor: t.surface, borderWidth: 2 },
        label: {
          show: true,
          color: t.text,
          fontSize: px(t, 12),
          fontWeight: 600,
          lineHeight: px(t, 16),
          // Never truncated: long names wrap to a second line; the HTML legend carries every slice.
          width: px(t, 110),
          overflow: 'break',
          // Labels hug the canvas edges so a long name wraps inside the card instead of clipping.
          alignTo: 'edge',
          edgeDistance: px(t, 8),
          formatter: (p: any) => `${p.name}\n${fmtShare(p.percent)}`,
        },
        labelLine: {
          show: true,
          length: px(t, 12),
          length2: px(t, 14),
          lineStyle: { color: t.sub, width: 1.2 },
        },
        labelLayout: { hideOverlap: true },
        emphasis: { scale: true, scaleSize: Math.round(7 * s), itemStyle: { shadowBlur: 18, shadowColor: t.shadowAccent } },
        // Rubric C3: outside callouts only for slices ≥ 6 % (the legend covers the rest) — no crowding.
        data: plan.rows.map((r) => {
          const big = r.value / Math.max(1e-9, plan.total) >= 0.06;
          return { name: r.label, value: r.value, raw: r.raw, label: { show: big }, labelLine: { show: big } };
        }),
        animationType: 'expansion',
      } as any,
    ],
  };
}

/** Histogram: contiguous binned frequency bars + overlaid Gaussian/KDE smooth density curve. */
export function histogramOption(plan: ChartPlan, t: ChartTokens): Opt {
  const rows = plan.rows;
  const unit: UnitInfo = rows[0]?.raw?.bin !== undefined ? { kind: 'count', noun: 'records', label: 'Frequency' } : plan.unit;
  const values = rows.map((r) => r.value);
  const maxV = Math.max(1, ...values);
  const iMax = values.indexOf(maxV);
  const isModal = (i: number) => values[i] === maxV;
  const totalCount = values.reduce((s, v) => s + v, 0);
  // Mean / median markers (family must-have). Bins carry numeric edges + stats from planChart.
  const stats = rows[0]?.raw?.__stats as { mean: number; median: number; lo: number; hi: number; meanValue: number; medianValue: number } | undefined;

  // Smooth density overlay (moving-average smoothed bell curve)
  const densityCurve = values.map((v, i) => {
    const prev = values[Math.max(0, i - 1)];
    const next = values[Math.min(values.length - 1, i + 1)];
    return Number(((prev * 0.22 + v * 0.56 + next * 0.22) * 1.02).toFixed(1));
  });

  return {
    ...base(t),
    grid: [{ left: px(t, 36), right: px(t, 28), top: px(t, 64), bottom: px(t, 24), containLabel: true }],
    // Mean/median caption (top-left): solid line = mean, dotted = median; values stated once, no on-plot collisions.
    graphic: stats
      ? [
          {
            type: 'text',
            left: px(t, 12),
            top: 0,
            style: {
              text: `━ Mean ${fmtNum(stats.meanValue, 1)}    ┅ Median ${fmtNum(stats.medianValue, 1)}`,
              fill: t.sub,
              fontSize: px(t, 12),
              fontFamily: t.font,
              fontWeight: 500,
            },
          },
        ]
      : [],
    legend: [
      {
        top: 0,
        right: px(t, 16),
        icon: 'roundRect',
        itemWidth: px(t, 14),
        itemHeight: px(t, 8),
        textStyle: { color: t.sub, fontSize: px(t, 12) },
        // Solid swatch for the bars (a gradient fill renders as a muddy legend chip).
        data: [{ name: 'Bin Frequency', itemStyle: { color: t.accent } }, { name: 'Density Curve', itemStyle: { color: t.sub } }],
      },
    ],
    xAxis: [
      ...(stats ? [{ type: 'value', min: stats.lo, max: stats.hi, show: false, position: 'top', gridIndex: 0 } as any] : []),
      {
        ...categoryAxis(t, rows.map((r) => r.label), false),
        position: 'bottom',
        name: rows[0]?.raw?.bin !== undefined ? humanizeKey(plan.valueKey) : undefined,
        nameLocation: 'middle',
        nameGap: px(t, rows.reduce((n, r) => n + r.label.length, 0) > 56 ? 52 : 32),
        nameTextStyle: { color: t.sub, fontSize: px(t, 12), fontWeight: 500 },
      },
    ],
    yAxis: [
      valueAxis(t, unit, false, {
        max: Math.ceil(maxV * 1.22),
        // Rubric C3: unit name centred along the axis (rotated), clear of the caption and legend rows.
        nameLocation: 'middle',
        nameRotate: 90,
        nameGap: px(t, 44),
        nameTextStyle: { color: t.sub, fontSize: px(t, 12) },
        axisLabel: { color: t.sub, fontSize: px(t, 12), showMaxLabel: false, formatter: (v: number) => fmtValue(v, unit, { compact: true }) },
      } as any),
    ],
    tooltip: {
      ...tooltipBase(t),
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (ps: any) => {
        const bar = Array.isArray(ps) ? ps[0] : ps;
        const r = rows[bar?.dataIndex || 0];
        const share = sharePct(r.value, Math.max(1, totalCount));
        return tooltipCard(t, `Bin: ${r.label}`, [
          ['Frequency', fmtValue(r.value, unit, { withNoun: true }), t.accent],
          ['Distribution share', share],
          ...(r.raw?.members ? ([['Sample', String(r.raw.members)]] as [string, string][]) : []),
        ]);
      },
    },
    series: [
      {
        id: 'main',
        name: 'Bin Frequency',
        type: 'bar',
        xAxisIndex: stats ? 1 : 0,
        barWidth: '94%',
        barCategoryGap: '4%',
        z: 6,
        universalTransition: { enabled: true },
        data: rows.map((r, i) => ({
          value: r.value,
          name: r.label,
          raw: r.raw,
          itemStyle: {
            color: isModal(i) ? vGradient(t.accentDeep, t.accent) : vGradient(t.accent, t.accentSoft),
            borderColor: t.surface,
            borderWidth: 1.5,
            borderRadius: [px(t, 5), px(t, 5), 0, 0],
          },
        })),
        label: {
          show: true,
          position: 'top',
          distance: px(t, 6),
          color: t.text,
          fontSize: px(t, 12),
          fontWeight: 600,
          formatter: (p: any) => {
            const pct = sharePct(p.value, Math.max(1, totalCount), 0);
            // Rubric C5: counts only on bars (shares live in the tooltip); modal bin called out.
            return isModal(p.dataIndex) && rows.length >= 3 ? `{top|${fmtValue(p.value, unit)} · most common (${pct})}` : fmtValue(p.value, unit);
          },
          textBorderColor: t.labelHalo,
          textBorderWidth: 3,
          // Halo box: the density curve / mean–median lines pass behind a label, never through it.
          backgroundColor: t.labelHalo,
          padding: [px(t, 1), px(t, 4)],
          borderRadius: px(t, 4),
          rich: { top: { ...pill(t, t.accentDeep), lineHeight: px(t, 24), textBorderWidth: 0 } },
        },
      } as any,
      {
        id: 'kde',
        name: 'Density Curve',
        type: 'line',
        xAxisIndex: stats ? 1 : 0,
        // Rubric C4: maroon is reserved for loss/negative. The density overlay is a neutral guide line.
        smooth: 0.45,
        smoothMonotone: 'x',
        symbol: 'none',
        lineStyle: { color: t.sub, width: px(t, 2), type: [6, 4] },
        itemStyle: { color: t.sub },
        data: densityCurve,
        z: 4,
      } as any,
      ...(stats
        ? [
            {
              id: 'stats',
              name: 'stats',
              type: 'line',
              xAxisIndex: 0,
              data: [],
              silent: true,
              z: 2,
              markLine: {
                symbol: 'none',
                silent: true,
                z: 2,
                data: [
                  { xAxis: stats.mean, lineStyle: { color: t.text, type: 'solid', width: 1.2 }, label: { show: false } },
                  { xAxis: stats.median, lineStyle: { color: t.sub, type: [3, 3], width: 1.2 }, label: { show: false } },
                ],
              },
            } as any,
          ]
        : []),
    ],
  };
}

/** Dedicated Area chart with rich gradient fill and interactive zoom when >10 points. */
export function areaOption(plan: ChartPlan, t: ChartTokens, data: Record<string, any>[]): Opt {
  const opt = lineOption(plan, t, data);
  const series = (opt.series as any[]) || [];
  const palette = [
    [alpha(t.accent, 0.42), alpha(t.accent, 0.03)],
    [alpha(t.accentDeep, 0.36), alpha(t.accentDeep, 0.02)],
    [alpha(t.categorical[2], 0.32), alpha(t.categorical[2], 0.02)],
  ];
  series.forEach((s, idx) => {
    const [cTop, cBot] = palette[idx % palette.length];
    s.areaStyle = { color: vGradient(cTop, cBot) };
    s.smooth = 0.25;
    s.smoothMonotone = 'x';
  });
  if (data.length > 10) {
    opt.dataZoom = [{ type: 'inside' }, { type: 'slider', height: px(t, 18), bottom: 0 }];
  }
  return opt;
}

/** Scatter / Bubble plot with X/Y axes, quadrant average lines, and direct labels. */
export function scatterOption(plan: ChartPlan, t: ChartTokens, data: Record<string, any>[]): Opt {
  const rows = plan.rows;
  const secondKey = plan.seriesKeys.find((k) => k !== plan.valueKey);
  const xUnit: UnitInfo = secondKey ? unitForKey(plan)(secondKey) : { kind: 'count', noun: '', label: 'Rank / Index' };
  const yUnit = plan.unit;

  const pts = rows.map((r, idx) => {
    const xVal = secondKey ? (toNumber(r.raw?.[secondKey]) ?? idx + 1) : idx + 1;
    const yVal = r.value;
    return { name: r.label, value: [xVal, yVal], raw: r.raw };
  });

  const xAvg = pts.reduce((s, p) => s + p.value[0], 0) / Math.max(1, pts.length);
  const yAvg = pts.reduce((s, p) => s + p.value[1], 0) / Math.max(1, pts.length);
  // Rubric C2: bubble size only when a third measure exists (with its own tooltip row); otherwise a fixed dot.
  const sizeKey = plan.seriesKeys.find((k) => k !== plan.valueKey && k !== secondKey);
  const sizeVals = sizeKey ? rows.map((r) => Math.abs(toNumber(r.raw?.[sizeKey]) ?? 0)) : [];
  const maxS = Math.max(1, ...sizeVals);
  const xs = pts.map((p) => p.value[0]);
  const xLo = Math.min(...xs);
  const xHi = Math.max(...xs);
  const showNames = pts.length <= 18;
  const placer = makeScatterPlacer(pts.length, px(t, 4), (i) => pts[i]?.value[0] >= xHi - (xHi - xLo) * 0.2);
  const axisName = { nameLocation: 'middle', nameTextStyle: { color: t.sub, fontSize: px(t, 12), fontWeight: 500 } };
  const avgLabel = { color: t.sub, fontSize: px(t, 11), backgroundColor: t.labelHalo, padding: [px(t, 2), px(t, 6)], borderRadius: px(t, 6) };

  return {
    ...base(t),
    grid: [{ left: px(t, 36), right: px(t, 96), top: px(t, 36), bottom: px(t, 40), containLabel: true }],
    xAxis: [
      valueAxis(t, xUnit, true, {
        ...axisName,
        name: secondKey ? humanizeKey(secondKey) : 'Category Index',
        nameGap: px(t, 32),
        scale: true,
      } as any),
    ],
    yAxis: [
      valueAxis(t, yUnit, false, {
        ...axisName,
        name: humanizeKey(plan.valueKey),
        nameRotate: 90,
        nameGap: px(t, 48),
        scale: true,
      } as any),
    ],
    tooltip: {
      ...tooltipBase(t),
      trigger: 'item',
      formatter: (p: any) => {
        const [xv, yv] = p.value || [0, 0];
        return tooltipCard(t, p.data?.name || '', [
          ...(secondKey ? ([[humanizeKey(secondKey), fmtValue(xv, xUnit)]] as [string, string][]) : []),
          [humanizeKey(plan.valueKey), fmtValue(yv, yUnit, { withNoun: true }), t.accent],
          ...extraRows(p.data?.raw, [plan.dimKey, plan.valueKey, secondKey || ''], unitForKey(plan)),
        ]);
      },
    },
    series: [
      {
        id: 'main',
        type: 'scatter',
        universalTransition: { enabled: true },
        symbolSize: sizeKey ? (_: number[], p: any) => px(t, 12 + Math.round((sizeVals[p.dataIndex] / maxS) * 22)) : px(t, 14),
        itemStyle: {
          color: (p: any) => (p.value[1] < 0 ? t.maroon : t.accent),
          opacity: 0.9,
          borderColor: t.surface,
          borderWidth: 1.5,
        },
        // Markers carry an invisible 1-char label only so the placer learns every marker's rect first (series
        // order = layout order); the visible names live in the 'scatter-labels' series below.
        label: { show: showNames, formatter: ' ', fontSize: 1, color: 'transparent' },
        labelLayout: showNames ? placer.record : undefined,
        markLine:
          pts.length >= 4
            ? {
                silent: true,
                symbol: 'none',
                z: 1,
                lineStyle: { color: t.sub, type: [4, 4], width: 1.1 },
                data: [
                  { xAxis: xAvg, label: { ...avgLabel, position: 'end', formatter: `Avg ${fmtValue(xAvg, xUnit)}` } },
                  { yAxis: yAvg, label: { ...avgLabel, position: 'end', formatter: `Avg ${fmtValue(yAvg, yUnit)}` } },
                ],
              }
            : undefined,
        data: pts,
      } as any,
      ...(showNames
        ? [
            {
              id: 'scatter-labels',
              type: 'scatter',
              silent: true,
              z: 1, // under the markers: a name never covers a point
              symbolSize: 1,
              itemStyle: { color: 'transparent' }, // (opacity 0 would also hide the label)
              tooltip: { show: false },
              label: {
                show: true,
                position: 'right',
                color: t.text,
                fontSize: px(t, 12),
                fontWeight: 600,
                textBorderColor: t.labelHalo,
                textBorderWidth: 3,
                formatter: (p: any) => p.data?.name || '',
              },
              // Rubric C3: each name avoids every marker and earlier name (right / left / above / below, then displaced
              // with a leader line). ≤ 8 points: never hidden; more: residual collisions hide (tooltip keeps them).
              labelLayout: placer.place,
              labelLine: { show: true, length2: 0, lineStyle: { color: t.sub, width: 1 } },
              data: pts.map((q) => ({ name: q.name, value: q.value })),
            } as any,
          ]
        : []),
    ],
  };
}

type Box = { x: number; y: number; width: number; height: number };
const overlapArea = (a: Box, b: Box) =>
  Math.max(0, Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x)) * Math.max(0, Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y));

/**
 * Scatter label placer. `record` runs as the marker series' labelLayout (learns every marker rect); `place` runs
 * as the label series' labelLayout afterwards (ECharts lays labels out in series order), so each name is placed
 * knowing ALL markers. Candidates: right / left / above / below of the dot, then displaced diagonals and further
 * rows (with a leader line). With ≤ 8 points nothing is hidden: the least-overlapping candidate wins.
 */
function makeScatterPlacer(n: number, gap: number, preferLeft: (i: number) => boolean) {
  const markers: Box[] = [];
  let placed: Box[] = [];
  const record = (p: any) => {
    markers[p.dataIndex] = p.rect;
    return {};
  };
  const place = (p: any) => {
    const i = p.dataIndex;
    if (i === 0) placed = [];
    const S: Box | undefined = markers[i];
    const L: Box = p.labelRect;
    if (!S) return { hideOverlap: n > 8 };
    const w = L.width;
    const h = L.height;
    const cy = S.y + S.height / 2 - h / 2;
    const xr = S.x + S.width + gap;
    const xl = S.x - gap - w;
    const xc = S.x + S.width / 2 - w / 2;
    const near = [
      { x: xr, y: cy },
      { x: xl, y: cy },
      { x: xc, y: S.y - h - 2 },
      { x: xc, y: S.y + S.height + 2 },
    ];
    if (preferLeft(i)) near.unshift(near.splice(1, 1)[0]);
    const far: { x: number; y: number }[] = [];
    for (const k of [1, 2, 3]) {
      const d = k * (h + 4);
      far.push({ x: xr + gap, y: cy - d }, { x: xr + gap, y: cy + d }, { x: xl - gap, y: cy - d }, { x: xl - gap, y: cy + d }, { x: xc, y: S.y - h - 2 - d }, { x: xc, y: S.y + S.height + 2 + d });
    }
    const cands = [...near, ...far];
    const box = (c: { x: number; y: number }): Box => ({ x: c.x - 2, y: c.y - 1, width: w + 4, height: h + 2 });
    const others = [...placed, ...markers.filter(Boolean)];
    const cost = (c: { x: number; y: number }) => others.reduce((s, b) => s + overlapArea(box(c), b), 0);
    const pick = cands.find((c) => cost(c) === 0) || cands.reduce((best, c) => (cost(c) < cost(best) ? c : best), cands[0]);
    placed.push(box(pick));
    return { x: pick.x, y: pick.y, align: 'left', verticalAlign: 'top', hideOverlap: n > 8 };
  };
  return { record, place };
}

/** Proportional Treemap with formatted values and percentage share. */
export function treemapOption(plan: ChartPlan, t: ChartTokens, colors: string[]): Opt {
  const unit = plan.unit;
  const all = plan.rows.map((r) => ({ ...r, absVal: Math.max(0.01, Math.abs(r.value)) }));
  const totalAbs = all.reduce((s, r) => s + r.absVal, 0);
  // Rubric C5: tiles under ~6 % are unreadable; fold them into one muted "Others" tile (only when ≥ 2 fold).
  const isSmall = (r: { absVal: number; value: number }) => r.value >= 0 && r.absVal / Math.max(1e-9, totalAbs) < 0.06;
  const small = all.filter(isSmall);
  const posRows =
    small.length >= 2
      ? [
          ...all.filter((r) => !isSmall(r)).sort((x, y) => y.absVal - x.absVal),
          { label: `Others (${small.length})`, raw: {}, value: small.reduce((s, r) => s + r.value, 0), absVal: small.reduce((s, r) => s + r.absVal, 0), others: true },
        ]
      : all;
  const isOthers = (r: any) => !!r.others;
  // magnitude ramp: rank tiles by size → deepest blue for the largest (independent of `colors`)
  const order = posRows.map((r, i) => [i, isOthers(r) ? -1 : r.absVal] as [number, number]).sort((a, b) => b[1] - a[1]);
  const steps = t.dark ? ramp(t.sequential[0], t.sequential[3], Math.max(1, posRows.length)) : ramp(t.sequential[5], t.sequential[2], Math.max(1, posRows.length));
  const mag: string[] = [];
  order.forEach(([idx], rank) => (mag[idx] = steps[rank]));
  const fillOf = (r: any, i: number) => (isOthers(r) ? t.faint : r.value < 0 ? t.maroon : mag[i]);
  return {
    ...base(t),
    color: colors,
    tooltip: {
      ...tooltipBase(t),
      trigger: 'item',
      formatter: (p: any) => {
        const orig = p.data?.origValue ?? p.value;
        const pct = sharePct(Math.abs(orig), Math.max(1, totalAbs));
        return tooltipCard(t, p.name, [
          [humanizeKey(plan.valueKey), fmtValue(orig, unit, { withNoun: true })],
          ['Share', pct],
          ...extraRows(p.data?.raw, [plan.dimKey, plan.valueKey], unitForKey(plan)),
        ]);
      },
    },
    series: [
      {
        // Own id: a bar/pie 'main' must not try to morph out of treemap tiles (they froze on screen, U5.9 g06/g07).
        id: 'treemap',
        type: 'treemap',
        roam: false,
        nodeClick: false,
        breadcrumb: { show: false },
        // Rubric C1: data order (largest first, "Others" pinned last) — the aggregate never leads the layout.
        sort: false,
        // No universalTransition: ECharts can't morph treemap tiles into bars (tiles froze mid-morph in U5.9 g06/g07).
        itemStyle: {
          borderColor: t.surface,
          borderWidth: 2,
          gapWidth: 2,
          borderRadius: px(t, 6),
        },
        label: {
          show: true,
          color: t.onAccent,
          fontSize: px(t, 13),
          fontWeight: 600,
          // Never truncated: names wrap inside the tile (full name + value always in the tooltip).
          overflow: 'break',
          lineHeight: px(t, 17),
          formatter: (p: any) => {
            const orig = p.data?.origValue ?? p.value;
            const pct = sharePct(Math.abs(orig), Math.max(1, totalAbs));
            return `${p.name}\n${fmtValue(orig, unit)} (${pct})`;
          },
        },
        data: posRows.map((r, i) => ({
          name: r.label,
          value: r.absVal,
          origValue: r.value,
          raw: r.raw,
          // Rubric C4: one hue family by magnitude (largest = deepest); maroon only for negatives; Others muted.
          itemStyle: { color: fillOf(r, i) },
          // Rubric C3: tiles ≥10% show name + value; 6–10% show name only; smaller tiles rely on the tooltip.
          label: {
            show: r.absVal / Math.max(1e-9, totalAbs) >= 0.04,
            color: labelOn(fillOf(r, i)),
            formatter: r.absVal / Math.max(1e-9, totalAbs) >= 0.1 ? undefined : '{b}',
          },
        })),
      } as any,
    ],
  };
}

/** Ranked stage/category Funnel chart. */
export function funnelOption(plan: ChartPlan, t: ChartTokens, colors: string[]): Opt {
  const unit = plan.unit;
  return {
    ...base(t),
    color: colors,
    tooltip: {
      ...tooltipBase(t),
      trigger: 'item',
      formatter: (p: any) =>
        tooltipCard(t, p.name, [
          [humanizeKey(plan.valueKey), fmtValue(p.value, unit, { withNoun: true }), p.color],
          ['Share', fmtShare(p.percent)],
        ]),
    },
    series: [
      {
        id: 'main',
        type: 'funnel',
        left: '10%',
        top: px(t, 20),
        bottom: px(t, 20),
        width: '72%',
        sort: 'descending',
        gap: 3,
        universalTransition: { enabled: true },
        itemStyle: { borderColor: t.surface, borderWidth: 1.5, borderRadius: px(t, 4) },
        label: {
          show: true,
          position: 'inside',
          color: t.onAccent,
          fontSize: px(t, 12),
          fontWeight: 600,
          formatter: (p: any) => `${p.name} · ${fmtValue(p.value, unit)}`,
        },
        data: plan.rows.map((r, i) => ({ name: r.label, value: Math.max(0, r.value), raw: r.raw, label: { color: labelOn(colors[i % colors.length]) } })),
      } as any,
    ],
  };
}

// ---------------------------------------------------------------------------------------------------------------
// P4.4 portfolio batch A (SPEC-09 §4.5): combo dual-axis, 100% stacked, heatmap, box plot, gauge.
// ---------------------------------------------------------------------------------------------------------------

const PCT_UNIT: UnitInfo = { kind: 'percent', noun: '', label: '%' };

/** Combo: value bars on the left axis, a % (or second-unit) line on the right axis, shared x (CFO default for value + %). */
export function comboOption(plan: ChartPlan, t: ChartTokens, data: Record<string, any>[]): Opt {
  const [barKey, lineKey] = plan.seriesKeys;
  const labels = data.map((r) => humanizeValue(r[plan.dimKey]));
  const barUnit = unitForKey(plan)(barKey);
  const lineUnit = /pct|percent|margin|rate|ratio|%/i.test(lineKey) ? PCT_UNIT : unitForKey(plan)(lineKey);
  return {
    ...base(t),
    color: [t.accent, t.maroon],
    legend: [{ top: 0, left: 0, icon: 'roundRect', itemWidth: px(t, 14), itemHeight: px(t, 10), textStyle: { color: t.sub, fontSize: px(t, 12) }, formatter: legendName }],
    grid: [{ left: px(t, 16), right: px(t, 16), top: px(t, 52), bottom: px(t, 8), containLabel: true }],
    xAxis: [categoryAxis(t, labels, false)],
    yAxis: [
      valueAxis(t, barUnit, false, { name: humanizeKey(barKey) } as any),
      valueAxis(t, lineUnit, false, { name: humanizeKey(lineKey), position: 'right', splitLine: { show: false }, nameTextStyle: { color: t.sub, fontSize: px(t, 12), align: 'right' } } as any),
    ],
    tooltip: {
      ...tooltipBase(t),
      trigger: 'axis',
      formatter: (ps: any) =>
        tooltipCard(t, ps[0]?.name, ps.map((p: any) => [humanizeKey(p.seriesName), fmtValue(p.value, p.seriesIndex === 0 ? barUnit : lineUnit), p.color])),
    },
    series: [
      {
        id: 'main',
        name: barKey,
        type: 'bar',
        yAxisIndex: 0,
        barMaxWidth: px(t, 36),
        universalTransition: { enabled: true },
        itemStyle: { borderRadius: [px(t, 6), px(t, 6), 0, 0], color: vGradient(t.accentSoft, t.accent) as any },
        label: { show: data.length <= 12, position: 'top', color: t.text, fontSize: px(t, 12), formatter: (p: any) => fmtValue(p.value, barUnit, { compact: true }) },
        data: data.map((r) => toNumber(r[barKey])),
      },
      {
        id: 's1',
        name: lineKey,
        type: 'line',
        yAxisIndex: 1,
        smooth: false,
        symbol: 'circle',
        symbolSize: px(t, 8),
        lineStyle: { width: px(t, 2.5), color: t.maroon },
        itemStyle: { color: t.maroon },
        label: { show: data.length <= 12, position: 'top', color: t.maroon, fontSize: px(t, 12), formatter: (p: any) => fmtValue(p.value, lineUnit) },
        data: data.map((r) => toNumber(r[lineKey])),
      },
    ] as any,
  };
}

/** 100% stacked: each category's parts as a share of its own total; tooltip shows % and absolute. */
export function stacked100Option(plan: ChartPlan, t: ChartTokens, data: Record<string, any>[]): Opt {
  const keys = plan.seriesKeys;
  const labels = data.map((r) => humanizeValue(r[plan.dimKey]));
  const totals = data.map((r) => keys.reduce((s, k) => s + Math.max(0, toNumber(r[k]) || 0), 0));
  const share = (r: Record<string, any>, i: number, k: string) => (totals[i] > 0 ? ((toNumber(r[k]) || 0) / totals[i]) * 100 : 0);
  const horizontal = labels.reduce((s, l) => s + l.length, 0) / Math.max(1, labels.length) > 10;
  const ax = categoryAxis(t, labels, horizontal);
  const vx = valueAxis(t, PCT_UNIT, horizontal, { max: 100, name: undefined } as any);
  return {
    ...base(t),
    color: t.categorical,
    legend: [{ top: 0, left: 0, icon: 'roundRect', itemWidth: px(t, 14), itemHeight: px(t, 10), textStyle: { color: t.sub, fontSize: px(t, 12) }, formatter: legendName }],
    grid: [{ left: px(t, 8), right: px(t, 24), top: px(t, 48), bottom: px(t, 8), containLabel: true }],
    xAxis: [horizontal ? vx : ax],
    yAxis: [horizontal ? ax : vx],
    tooltip: {
      ...tooltipBase(t),
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (ps: any) => {
        const i = ps[0]?.dataIndex ?? 0;
        return tooltipCard(
          t,
          ps[0]?.name,
          ps.map((p: any) => [humanizeKey(p.seriesName), `${fmtShare(p.value)} · ${fmtValue(toNumber(data[i]?.[p.seriesName]) || 0, unitForKey(plan)(p.seriesName))}`, p.color]),
        );
      },
    },
    series: keys.map((k, idx) => ({
      id: idx === 0 ? 'main' : `s${idx}`,
      name: k,
      type: 'bar',
      stack: 'share',
      barMaxWidth: px(t, 40),
      itemStyle: { borderColor: t.surface, borderWidth: 1 },
      label: { show: data.length <= 10, color: t.onAccent, fontSize: px(t, 11), formatter: (p: any) => (p.value >= 6 ? fmtShare(p.value) : '') },
      data: data.map((r, i) => Number(share(r, i, k).toFixed(2))),
    })) as any,
  };
}

/** Heatmap: category × category with a sequential visualMap; cell labels when ≤ 120 cells. */
export function heatmapOption(plan: ChartPlan, t: ChartTokens, data: Record<string, any>[]): Opt {
  const xKey = plan.dimKey;
  const yKey = plan.dim2Key || plan.dimKey;
  const xs = Array.from(new Set(data.map((r) => humanizeValue(r[xKey]))));
  const ys = Array.from(new Set(data.map((r) => humanizeValue(r[yKey]))));
  const cells = data.map((r) => [xs.indexOf(humanizeValue(r[xKey])), ys.indexOf(humanizeValue(r[yKey])), toNumber(r[plan.valueKey])]);
  const vals = cells.map((c) => c[2]).filter((v): v is number => typeof v === 'number');
  const lo = vals.length ? Math.min(...vals) : 0;
  const hi = vals.length ? Math.max(...vals) : 1;
  return {
    ...base(t),
    grid: [{ left: px(t, 8), right: px(t, 16), top: px(t, 16), bottom: px(t, 56), containLabel: true }],
    xAxis: [{ ...categoryAxis(t, xs, false), splitArea: { show: true } }],
    yAxis: [{ ...categoryAxis(t, ys, true, 160), inverse: true, splitArea: { show: true } }],
    visualMap: [
      {
        min: lo,
        max: hi === lo ? lo + 1 : hi,
        calculable: false,
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        itemHeight: px(t, 180),
        textStyle: { color: t.sub, fontSize: px(t, 11) },
        inRange: { color: t.sequential },
        formatter: (v: number) => fmtValue(v, plan.unit, { compact: true }),
      } as any,
    ],
    tooltip: {
      ...tooltipBase(t),
      trigger: 'item',
      formatter: (p: any) => tooltipCard(t, `${xs[p.value[0]]} · ${ys[p.value[1]]}`, [[humanizeKey(plan.valueKey), fmtValue(p.value[2], plan.unit)]]),
    },
    series: [
      {
        id: 'main',
        type: 'heatmap',
        data: cells,
        label: { show: cells.length <= 120, color: t.text, fontSize: px(t, 11), formatter: (p: any) => fmtValue(p.value[2], plan.unit, { compact: true }) },
        itemStyle: { borderColor: t.surface, borderWidth: 1 },
        emphasis: { itemStyle: { borderColor: t.text, borderWidth: 1 } },
      },
    ] as any,
  };
}

/** Five-number summary of a numeric list (inclusive quartiles). */
export function fiveNumber(values: number[]): [number, number, number, number, number] {
  const v = [...values].sort((a, b) => a - b);
  const q = (p: number) => {
    const i = (v.length - 1) * p;
    const lo = Math.floor(i);
    const hi = Math.ceil(i);
    return v[lo] + (v[hi] - v[lo]) * (i - lo);
  };
  return [v[0], q(0.25), q(0.5), q(0.75), v[v.length - 1]];
}

/** Box plot per group: quartiles computed from records (or taken from pre-aggregated min/q1/median/q3/max rows); 1.5×IQR outliers as points. */
export function boxOption(plan: ChartPlan, t: ChartTokens, data: Record<string, any>[]): Opt {
  const pre = data.length > 0 && ['min', 'q1', 'median', 'q3', 'max'].every((k) => k in data[0]);
  let groups: string[];
  let boxes: number[][];
  const outliers: [number, number][] = [];
  if (pre) {
    groups = data.map((r) => humanizeValue(r[plan.dimKey]));
    boxes = data.map((r) => ['min', 'q1', 'median', 'q3', 'max'].map((k) => toNumber(r[k]) || 0));
  } else {
    const by = new Map<string, number[]>();
    for (const r of data) {
      const g = humanizeValue(r[plan.dimKey]);
      const v = toNumber(r[plan.valueKey]);
      if (v === null) continue;
      if (!by.has(g)) by.set(g, []);
      by.get(g)!.push(v);
    }
    groups = Array.from(by.keys());
    boxes = groups.map((g, gi) => {
      const vals = by.get(g)!;
      const [, q1, md, q3] = fiveNumber(vals);
      const iqr = q3 - q1;
      const inside = vals.filter((v) => v >= q1 - 1.5 * iqr && v <= q3 + 1.5 * iqr);
      vals.filter((v) => !inside.includes(v)).forEach((v) => outliers.push([gi, v]));
      // S1: true quartiles of all values; whiskers to the furthest non-outlier points
      const body = inside.length ? inside : vals;
      return [Math.min(...body), q1, md, q3, Math.max(...body)];
    });
  }
  return {
    ...base(t),
    grid: [{ left: px(t, 16), right: px(t, 16), top: px(t, 24), bottom: px(t, 8), containLabel: true }],
    xAxis: [categoryAxis(t, groups, false)],
    yAxis: [valueAxis(t, plan.unit, false)],
    tooltip: {
      ...tooltipBase(t),
      trigger: 'item',
      formatter: (p: any) => {
        if (p.seriesType === 'scatter') return tooltipCard(t, groups[p.value[0]], [['Outlier', fmtValue(p.value[1], plan.unit)]]);
        const [, mn, q1, md, q3, mx] = p.value;
        return tooltipCard(t, p.name, [
          ['Max', fmtValue(mx, plan.unit)],
          ['Q3', fmtValue(q3, plan.unit)],
          ['Median', fmtValue(md, plan.unit)],
          ['Q1', fmtValue(q1, plan.unit)],
          ['Min', fmtValue(mn, plan.unit)],
        ]);
      },
    },
    series: [
      { id: 'main', type: 'boxplot', data: boxes, itemStyle: { color: t.accentPale, borderColor: t.accent, borderWidth: px(t, 1.5) } },
      { id: 's1', type: 'scatter', data: outliers, symbolSize: px(t, 7), itemStyle: { color: t.maroon } },
    ] as any,
  };
}

/** Gauge: one value against its target band (only used when a target exists; otherwise the planner shows a KPI). */
export function gaugeOption(plan: ChartPlan, t: ChartTokens, data: Record<string, any>[]): Opt {
  const r0 = data[0] || {};
  const value = toNumber(r0[plan.valueKey]) ?? 0;
  const target = (plan.targetKey ? toNumber(r0[plan.targetKey]) : null) ?? plan.target ?? 100;
  const max = Math.max(target * 1.25, value * 1.1, 1);
  return {
    ...base(t),
    tooltip: { ...tooltipBase(t), trigger: 'item', formatter: () => tooltipCard(t, humanizeKey(plan.valueKey), [['Actual', fmtValue(value, plan.unit)], ['Target', fmtValue(target, plan.unit)]]) },
    series: [
      {
        id: 'main',
        type: 'gauge',
        min: 0,
        max,
        startAngle: 210,
        endAngle: -30,
        radius: '88%',
        progress: { show: true, width: px(t, 14), itemStyle: { color: value >= target ? t.positive : t.accent } },
        axisLine: { lineStyle: { width: px(t, 14), color: [[Math.min(1, target / max), t.band[0]], [1, t.band[1]]] } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        pointer: { show: false },
        anchor: { show: false },
        title: { show: true, offsetCenter: [0, '38%'], color: t.sub, fontSize: px(t, 13) },
        detail: { valueAnimation: true, offsetCenter: [0, '4%'], color: t.text, fontSize: px(t, 28), fontWeight: 700, formatter: () => fmtValue(value, plan.unit) },
        markLine: undefined,
        data: [{ value, name: `Target ${fmtValue(target, plan.unit)}` }],
      },
    ] as any,
  };
}
