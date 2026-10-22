/**
 * ECharts option builders for each chart form. All builders return a complete option
 * (every replaceable component present) so the renderer can morph between forms.
 */
import * as echarts from 'echarts';
import { ChartPlan, Row } from './plan';
import { ChartTokens, px, hGradient, vGradient, tooltipBase, tooltipCard, ANIM } from './theme';
import { fmtValue, fmtNum, humanizeKey, humanizeValue, toNumber, UnitInfo } from './format';

type Opt = echarts.EChartsOption;

function base(t: ChartTokens): Opt {
  return {
    backgroundColor: 'transparent',
    textStyle: { fontFamily: t.font, color: t.text },
    ...ANIM,
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

function categoryAxis(t: ChartTokens, labels: string[], horizontal: boolean, maxLabelPx = 200): any {
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
      hideOverlap: !horizontal,
      ...(horizontal ? { width: px(t, maxLabelPx), overflow: 'truncate', ellipsis: '…' } : { width: px(t, 110), overflow: 'break', lineHeight: px(t, 16) }),
    },
  };
}

function pill(t: ChartTokens, color: string) {
  return {
    color: '#FFFFFF',
    backgroundColor: color,
    borderRadius: px(t, 10),
    padding: [px(t, 3), px(t, 8)],
    fontSize: px(t, 11),
    fontWeight: 600 as const,
  };
}

/** Horizontal ranked bars; diverging colours when values are negative. */
export function rankedOption(plan: ChartPlan, t: ChartTokens, opts: { compact?: boolean; title?: string; labelPx?: number } = {}): Opt {
  const rows = plan.rows;
  const unit = plan.unit;
  const n = rows.length;
  const values = rows.map((r) => r.value);
  const maxV = Math.max(...values);
  const minV = Math.min(...values);
  const diverging = minV < 0;
  const avg = rows.reduce((s, r) => s + r.value, 0) / Math.max(1, n);
  const iMax = values.indexOf(maxV);
  const iMin = values.indexOf(minV);
  const others = (r: Row) => /^Others/.test(r.label);

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
      label: { formatter: `Avg ${fmtValue(avg, unit)}`, position: 'end', color: t.sub, fontSize: px(t, 11), fontWeight: 500 },
    });

  const absMax = Math.max(Math.abs(maxV), Math.abs(minV));
  const tagged = !opts.compact && n >= 3;
  // Asymmetric domain: room on each side for value labels (+ callout pills)
  const allNegOrZero = maxV <= 0;
  const xMin = diverging ? (allNegOrZero ? minV * 1.48 : Math.min(minV * 1.25, -absMax * 0.12)) : 0;
  const xMax = allNegOrZero ? absMax * 0.25 : Math.max(maxV, 0) * (tagged ? 1.12 : 1.15) || absMax * 0.3;
  return {
    ...base(t),
    title: opts.title
      ? [{ text: opts.title, left: 0, top: 0, textStyle: { color: t.text, fontSize: px(t, 14), fontWeight: 600, fontFamily: t.font } }]
      : [],
    grid: [{ left: px(t, 8), right: px(t, opts.compact ? 48 : tagged ? 190 : 100), top: px(t, opts.title ? 34 : 16), bottom: px(t, 28), containLabel: true }],
    xAxis: [
      valueAxis(t, unit, true, {
        min: xMin,
        max: xMax,
        name: opts.compact ? undefined : unit.label || undefined,
        axisLabel: { color: t.sub, fontSize: px(t, 11), formatter: (v: number) => fmtValue(v, unit, { compact: true }), showMinLabel: !diverging, showMaxLabel: false },
      } as any),
    ],
    yAxis: [categoryAxis(t, rows.map((r) => r.label), true, opts.labelPx || (opts.compact ? 130 : 210))],
    tooltip: {
      ...tooltipBase(t),
      trigger: 'item',
      formatter: (p: any) =>
        tooltipCard(t, p.name, [
          [humanizeKey(plan.valueKey), fmtValue(p.value, unit, { withNoun: true })],
          ...extraRows(p.data?.raw, [plan.dimKey, plan.valueKey], unitForKey(plan)),
        ]),
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
          fontSize: px(t, opts.compact ? 11 : 13),
          fontWeight: 600,
          formatter: (p: any) => {
            const v = fmtValue(p.value, unit, { sign: diverging });
            if (p.data?.tag === 'top') return p.value < 0 ? v : `${v}  {top|${diverging ? 'Top earner' : 'Highest'}}`;
            if (p.data?.tag === 'loss') return p.data?.tinyNeg ? `${v}  {loss|Largest loss}` : `{loss|Largest loss}  ${v}`;
            return v;
          },
          rich: { top: pill(t, t.accentDeep), loss: pill(t, t.maroon) },
        },
        markLine: markLines.length ? { symbol: 'none', silent: true, data: markLines, animation: true } : undefined,
      } as any,
    ],
  };
}

/** Vertical columns for ordinal categories (grades, ageing buckets). */
export function columnOption(plan: ChartPlan, t: ChartTokens): Opt {
  const rows = plan.rows;
  const unit = plan.unit;
  const values = rows.map((r) => r.value);
  const maxV = Math.max(...values);
  const iMax = values.indexOf(maxV);
  const avg = values.reduce((s, v) => s + v, 0) / Math.max(1, values.length);
  return {
    ...base(t),
    grid: [{ left: px(t, 8), right: px(t, 24), top: px(t, 40), bottom: px(t, 8), containLabel: true }],
    xAxis: [categoryAxis(t, rows.map((r) => r.label), false)],
    yAxis: [valueAxis(t, unit, false, { max: maxV * 1.18 } as any)],
    tooltip: {
      ...tooltipBase(t),
      trigger: 'item',
      formatter: (p: any) =>
        tooltipCard(t, p.name, [
          [humanizeKey(plan.valueKey), fmtValue(p.value, unit, { withNoun: true })],
          ['Share', `${fmtNum((p.value / Math.max(1, plan.total)) * 100, 1)}%`],
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
          formatter: (p: any) => (p.dataIndex === iMax && rows.length >= 3 ? `{top|Peak}\n${fmtValue(p.value, unit)}` : fmtValue(p.value, unit)),
          rich: { top: { ...pill(t, t.accentDeep), lineHeight: px(t, 26) } },
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
          ['Share', `${fmtNum(p.percent, 1)}%`],
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
        emphasis: { scale: true, scaleSize: Math.round(6 * s), itemStyle: { shadowBlur: 16, shadowColor: 'rgba(26,86,219,0.35)' } },
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
  plan.rows.forEach((r) => {
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
  if (!hasTotal && steps.length >= 2) steps.push({ label: 'Net impact', start: 0, end: running, kind: 'total', v: running, raw: {} });

  const lo = Math.min(0, ...steps.map((s) => Math.min(s.start, s.end)));
  const hi = Math.max(0, ...steps.map((s) => Math.max(s.start, s.end)));
  const pad = (hi - lo) * 0.16 || 1;

  const colorOf = (k: Step['kind'], v: number) =>
    k === 'total' ? (v < 0 ? t.maroon : t.accentDeep) : k === 'pos' ? t.accent : t.maroonSoft;

  return {
    ...base(t),
    grid: [{ left: px(t, 8), right: px(t, 24), top: px(t, 36), bottom: px(t, 8), containLabel: true }],
    xAxis: [categoryAxis(t, steps.map((s) => s.label), false)],
    yAxis: [valueAxis(t, unit, false, { min: lo < 0 ? lo - pad : 0, max: hi > 0 ? hi + pad : pad } as any)],
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
                text: fmtValue(s.v, unit, { sign: s.kind !== 'total' }),
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
  return {
    ...base(t),
    grid: [{ left: px(t, 8), right: px(t, 70), top: px(t, 36), bottom: px(t, 24), containLabel: true }],
    xAxis: [valueAxis(t, unit, true, { min: 0, max: Math.ceil(maxV / 10) * 10 } as any)],
    yAxis: [categoryAxis(t, rows.map((r) => r.label), true, 240)],
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
  const colors = [t.accent, t.accentDeep, t.maroon, t.accentSoft, t.faint];
  return {
    ...base(t),
    color: colors,
    grid: [{ left: px(t, 8), right: px(t, single ? 72 : 120), top: px(t, single ? 36 : 48), bottom: px(t, 8), containLabel: true }],
    legend: single ? [] : [{ top: 0, left: 0, icon: 'roundRect', itemWidth: px(t, 14), itemHeight: px(t, 6), textStyle: { color: t.sub, fontSize: px(t, 12) } }],
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
      smooth: 0.35,
      symbol: 'circle',
      symbolSize: px(t, 7),
      showSymbol: labels.length <= 24,
      universalTransition: { enabled: true },
      lineStyle: { width: px(t, 3) },
      areaStyle: single
        ? { color: vGradient(t.dark ? 'rgba(76,151,255,0.35)' : 'rgba(49,134,255,0.28)', 'rgba(49,134,255,0)') }
        : undefined,
      endLabel: { show: true, formatter: (p: any) => fmtValue(p.value, plan.unit), color: colors[idx % colors.length], fontWeight: 700, fontSize: px(t, 13) },
      data: data.map((r) => toNumber(r[k])),
      markPoint:
        single && labels.length >= 4
          ? {
              symbol: 'roundRect',
              symbolSize: [px(t, 44), px(t, 22)],
              itemStyle: { color: t.accentDeep },
              label: { color: '#fff', fontSize: px(t, 11), fontWeight: 600, formatter: 'Peak' },
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
  const colors = [t.accent, t.accentDeep, t.accentSoft, t.faint, t.maroon];
  const ax = categoryAxis(t, labels, horizontal);
  const vx = valueAxis(t, plan.unit, horizontal);
  return {
    ...base(t),
    color: colors,
    legend: [{ top: 0, left: 0, icon: 'roundRect', itemWidth: px(t, 14), itemHeight: px(t, 10), textStyle: { color: t.sub, fontSize: px(t, 12) }, formatter: (n: string) => humanizeKey(n) }],
    grid: [{ left: px(t, 8), right: px(t, 40), top: px(t, 44), bottom: px(t, 8), containLabel: true }],
    xAxis: [horizontal ? vx : ax],
    yAxis: [horizontal ? ax : vx],
    tooltip: {
      ...tooltipBase(t),
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: t.dark ? 'rgba(255,255,255,0.04)' : 'rgba(49,134,255,0.06)' } },
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
      label: { show: data.length * plan.seriesKeys.length <= 18, position: horizontal ? 'right' : 'top', color: t.sub, fontSize: px(t, 11), formatter: (p: any) => fmtValue(p.value, unitForKey(plan)(k), { compact: true }) },
      data: data.map((r) => toNumber(r[k])),
    })) as any,
  };
}

/** Horizontal stacked bars (e.g. receivables ageing) with severity ramp and totals. */
export function stackedOption(plan: ChartPlan, t: ChartTokens, data: Record<string, any>[]): Opt {
  const keys = plan.seriesKeys;
  const sorted = [...data].sort((a, b) => keys.reduce((s, k) => s + (toNumber(b[k]) || 0), 0) - keys.reduce((s, k) => s + (toNumber(a[k]) || 0), 0)).slice(0, 12);
  const labels = sorted.map((r) => humanizeValue(r[plan.dimKey]));
  const severe = (k: string) => /(>|over|above)\s*\d+|180|365|overdue/i.test(k);
  const blues = ramp(t.dark ? '#C6E1FF' : '#B9DAFF', t.dark ? '#2F6FE0' : '#1A56DB', Math.max(1, keys.filter((k) => !severe(k)).length));
  let bi = 0;
  const colors = keys.map((k) => (severe(k) ? t.maroon : blues[bi++]));
  const totals = sorted.map((r) => keys.reduce((s, k) => s + (toNumber(r[k]) || 0), 0));
  const unit = plan.unit.kind === 'count' && /cr|₹/i.test(String(plan.unit.label)) ? plan.unit : plan.unit;
  return {
    ...base(t),
    color: colors,
    legend: [{ top: 0, left: 0, icon: 'roundRect', itemWidth: px(t, 14), itemHeight: px(t, 10), textStyle: { color: t.sub, fontSize: px(t, 12) }, data: keys }],
    grid: [{ left: px(t, 8), right: px(t, 90), top: px(t, 44), bottom: px(t, 8), containLabel: true }],
    xAxis: [valueAxis(t, unit, true)],
    yAxis: [categoryAxis(t, labels, true, 200)],
    tooltip: {
      ...tooltipBase(t),
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: t.dark ? 'rgba(255,255,255,0.04)' : 'rgba(49,134,255,0.06)' } },
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
          ['Share', `${fmtNum(p.percent, 1)}%`],
          ...extraRows(p.data?.raw, [plan.dimKey, plan.valueKey], unitForKey(plan)),
        ]),
    },
    series: [
      {
        id: 'main',
        type: 'pie',
        radius: ['0%', '76%'],
        center: ['50%', '50%'],
        minAngle: 4,
        universalTransition: { enabled: true },
        itemStyle: { borderRadius: Math.round(5 * s), borderColor: t.surface, borderWidth: 2 },
        label: {
          show: true,
          color: t.text,
          fontSize: px(t, 12),
          fontWeight: 600,
          formatter: (p: any) => `${p.name}\n${fmtNum(p.percent, 1)}%`,
        },
        labelLine: {
          show: true,
          length: px(t, 12),
          length2: px(t, 14),
          lineStyle: { color: t.sub, width: 1.2 },
        },
        emphasis: { scale: true, scaleSize: Math.round(7 * s), itemStyle: { shadowBlur: 18, shadowColor: 'rgba(26,86,219,0.35)' } },
        data: plan.rows.map((r) => ({ name: r.label, value: r.value, raw: r.raw })),
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
  const totalCount = values.reduce((s, v) => s + v, 0);

  // Smooth density overlay (moving-average smoothed bell curve)
  const densityCurve = values.map((v, i) => {
    const prev = values[Math.max(0, i - 1)];
    const next = values[Math.min(values.length - 1, i + 1)];
    return Number(((prev * 0.22 + v * 0.56 + next * 0.22) * 1.02).toFixed(1));
  });

  return {
    ...base(t),
    grid: [{ left: px(t, 12), right: px(t, 28), top: px(t, 44), bottom: px(t, 16), containLabel: true }],
    legend: [
      {
        top: 0,
        right: px(t, 16),
        icon: 'roundRect',
        itemWidth: px(t, 14),
        itemHeight: px(t, 8),
        textStyle: { color: t.sub, fontSize: px(t, 12) },
        data: ['Bin Frequency', 'Density Curve'],
      },
    ],
    xAxis: [
      {
        ...categoryAxis(t, rows.map((r) => r.label), false),
        name: rows[0]?.raw?.bin !== undefined ? humanizeKey(plan.valueKey) : undefined,
        nameLocation: 'middle',
        nameGap: px(t, 32),
        nameTextStyle: { color: t.sub, fontSize: px(t, 12), fontWeight: 500 },
      },
    ],
    yAxis: [valueAxis(t, unit, false, { max: Math.ceil(maxV * 1.22) } as any)],
    tooltip: {
      ...tooltipBase(t),
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (ps: any) => {
        const bar = Array.isArray(ps) ? ps[0] : ps;
        const r = rows[bar?.dataIndex || 0];
        const share = ((r.value / Math.max(1, totalCount)) * 100).toFixed(1);
        return tooltipCard(t, `Bin: ${r.label}`, [
          ['Frequency', fmtValue(r.value, unit, { withNoun: true }), t.accent],
          ['Distribution share', `${share}%`],
          ...(r.raw?.members ? ([['Sample', String(r.raw.members)]] as [string, string][]) : []),
        ]);
      },
    },
    series: [
      {
        id: 'main',
        name: 'Bin Frequency',
        type: 'bar',
        barWidth: '94%',
        barCategoryGap: '4%',
        universalTransition: { enabled: true },
        data: rows.map((r, i) => ({
          value: r.value,
          name: r.label,
          raw: r.raw,
          itemStyle: {
            color: i === iMax ? vGradient(t.accentDeep, t.accent) : vGradient(t.accent, t.accentSoft),
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
            const pct = ((p.value / Math.max(1, totalCount)) * 100).toFixed(0);
            return p.dataIndex === iMax && rows.length >= 3
              ? `{top|Modal Bin · ${pct}%}\n${fmtValue(p.value, unit)}`
              : `${fmtValue(p.value, unit)} (${pct}%)`;
          },
          rich: { top: { ...pill(t, t.accentDeep), lineHeight: px(t, 24) } },
        },
      } as any,
      {
        id: 'kde',
        name: 'Density Curve',
        type: 'line',
        smooth: 0.45,
        symbol: 'circle',
        symbolSize: px(t, 6),
        lineStyle: { color: t.maroon, width: px(t, 2.5), type: 'solid' },
        itemStyle: { color: t.maroon },
        data: densityCurve,
        z: 5,
      } as any,
    ],
  };
}

/** Dedicated Area chart with rich gradient fill and interactive zoom when >10 points. */
export function areaOption(plan: ChartPlan, t: ChartTokens, data: Record<string, any>[]): Opt {
  const opt = lineOption(plan, t, data);
  const series = (opt.series as any[]) || [];
  const palette = [
    ['rgba(49,134,255,0.42)', 'rgba(49,134,255,0.03)'],
    ['rgba(26,86,219,0.36)', 'rgba(26,86,219,0.02)'],
    ['rgba(142,0,12,0.32)', 'rgba(142,0,12,0.02)'],
  ];
  series.forEach((s, idx) => {
    const [cTop, cBot] = palette[idx % palette.length];
    s.areaStyle = { color: vGradient(cTop, cBot) };
    s.smooth = 0.4;
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
  const maxY = Math.max(1, ...pts.map((p) => Math.abs(p.value[1])));

  return {
    ...base(t),
    grid: [{ left: px(t, 16), right: px(t, 44), top: px(t, 36), bottom: px(t, 28), containLabel: true }],
    xAxis: [
      valueAxis(t, xUnit, true, {
        name: secondKey ? humanizeKey(secondKey) : 'Category Index',
        scale: true,
      } as any),
    ],
    yAxis: [
      valueAxis(t, yUnit, false, {
        name: humanizeKey(plan.valueKey),
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
        symbolSize: (val: number[]) => {
          const ratio = Math.abs(val[1]) / maxY;
          return px(t, 14 + Math.round(ratio * 22));
        },
        itemStyle: {
          color: (p: any) => (p.value[1] < 0 ? t.maroon : t.accent),
          opacity: 0.86,
          borderColor: t.surface,
          borderWidth: 1.5,
          shadowBlur: 10,
          shadowColor: 'rgba(49,134,255,0.25)',
        },
        label: {
          show: pts.length <= 18,
          position: 'top',
          distance: px(t, 5),
          color: t.text,
          fontSize: px(t, 11),
          fontWeight: 600,
          formatter: (p: any) => p.data?.name || '',
        },
        markLine:
          pts.length >= 4
            ? {
                silent: true,
                symbol: 'none',
                lineStyle: { color: t.sub, type: [4, 4], width: 1.1 },
                data: [{ xAxis: xAvg, label: { show: false } }, { yAxis: yAvg, label: { formatter: `Avg ${fmtValue(yAvg, yUnit)}`, color: t.sub, fontSize: px(t, 11) } }],
              }
            : undefined,
        data: pts,
      } as any,
    ],
  };
}

/** Proportional Treemap with formatted values and percentage share. */
export function treemapOption(plan: ChartPlan, t: ChartTokens, colors: string[]): Opt {
  const unit = plan.unit;
  const posRows = plan.rows.map((r) => ({ ...r, absVal: Math.max(0.01, Math.abs(r.value)) }));
  const totalAbs = posRows.reduce((s, r) => s + r.absVal, 0);
  return {
    ...base(t),
    color: colors,
    tooltip: {
      ...tooltipBase(t),
      trigger: 'item',
      formatter: (p: any) => {
        const orig = p.data?.origValue ?? p.value;
        const pct = ((Math.abs(orig) / Math.max(1, totalAbs)) * 100).toFixed(1);
        return tooltipCard(t, p.name, [
          [humanizeKey(plan.valueKey), fmtValue(orig, unit, { withNoun: true })],
          ['Share', `${pct}%`],
          ...extraRows(p.data?.raw, [plan.dimKey, plan.valueKey], unitForKey(plan)),
        ]);
      },
    },
    series: [
      {
        id: 'main',
        type: 'treemap',
        roam: false,
        nodeClick: false,
        breadcrumb: { show: false },
        universalTransition: { enabled: true },
        itemStyle: {
          borderColor: t.surface,
          borderWidth: 2,
          gapWidth: 2,
          borderRadius: px(t, 6),
        },
        label: {
          show: true,
          color: '#FFFFFF',
          fontSize: px(t, 13),
          fontWeight: 600,
          formatter: (p: any) => {
            const orig = p.data?.origValue ?? p.value;
            const pct = ((Math.abs(orig) / Math.max(1, totalAbs)) * 100).toFixed(1);
            return `${p.name}\n${fmtValue(orig, unit)} (${pct}%)`;
          },
        },
        data: posRows.map((r, i) => ({
          name: r.label,
          value: r.absVal,
          origValue: r.value,
          raw: r.raw,
          itemStyle: { color: r.value < 0 ? t.maroon : colors[i % colors.length] },
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
          ['Share', `${fmtNum(p.percent, 1)}%`],
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
          color: '#FFFFFF',
          fontSize: px(t, 12),
          fontWeight: 600,
          formatter: (p: any) => `${p.name} · ${fmtValue(p.value, unit)}`,
        },
        data: plan.rows.map((r) => ({ name: r.label, value: Math.max(0, r.value), raw: r.raw })),
      } as any,
    ],
  };
}
