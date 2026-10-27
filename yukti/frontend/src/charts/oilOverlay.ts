/**
 * Oil-price overlay (26-Oct): adds a Brent / WTI line on a right-hand $/bbl axis to any fiscal-year chart with a
 * category x-axis (revenue, PAT, realisation…). Opt-in per card; data comes from /api/market/oil (Yahoo Finance,
 * Indian-FY averages of daily closes; the running FY is provisional / live).
 */
import { ChartSpec } from '@/contracts/answerContract';
import { ChartTokens, px } from './theme';
import { legendName } from './options';

export type OilBenchmark = 'brent' | 'wti' | 'inr';

export interface OilPricePayload {
  benchmark: OilBenchmark;
  symbol: string;
  label: string;
  short: string;
  unit: string;
  live: { price: number; change_pct: number | null; as_of: string };
  fy_series: { fy: string; avg: number; days: number; provisional: boolean }[];
  daily: { date: string; close: number }[];
  source: string;
  fetched_at: string;
  stale?: boolean;
}

export const OIL_OVERLAY_EVENT = 'yukti:oil-overlay';
export interface OilOverlayEventDetail {
  value: OilBenchmark | 'off';
  targetTurnId?: string;
  handled?: boolean;
}

/** Canonical "FYxx" for labels like FY26, FY2025-26, 2025-26, FY 2026; null when the label is not a fiscal year. */
export function fyKey(label: unknown): string | null {
  const s = String(label ?? '').trim();
  let m = s.match(/^FY\s*'?(\d{2})$/i);
  if (m) return `FY${m[1]}`;
  m = s.match(/(?:FY\s*)?(\d{4})\s*[-–/]\s*(\d{2}|\d{4})$/i);
  if (m) return `FY${m[2].slice(-2)}`;
  m = s.match(/^FY\s*(\d{4})$/i);
  if (m) return `FY${m[1].slice(-2)}`;
  return null;
}

/** True for charts whose x-axis is a run of fiscal years (at least 2 points, ≥80% FY labels). */
export function isOilOverlayEligible(spec?: ChartSpec | null): boolean {
  const data = (spec?.data || []) as Record<string, unknown>[];
  if (data.length < 2) return false;
  const xKey = (spec as any)?.x || (spec as any)?.category;
  if (!xKey) return false;
  const fyCount = data.filter((r) => fyKey(r[xKey]) !== null).length;
  return fyCount >= 2 && fyCount >= data.length * 0.8;
}

/** Returns a copy of `option` with the oil line + right axis, or `option` unchanged when it cannot be aligned. */
export function withOilOverlay(option: any, oil: OilPricePayload, t: ChartTokens): any {
  if (!option) return option;
  const xa = Array.isArray(option.xAxis) ? option.xAxis[0] : option.xAxis;
  if (!xa || xa.type !== 'category' || !Array.isArray(xa.data)) return option;
  const byFy = new Map(oil.fy_series.map((p) => [p.fy, p]));
  let labels: string[] = xa.data.map((d: any) => (d && typeof d === 'object' ? d.value : d));
  const points = labels.map((l) => {
    const k = fyKey(l);
    return k ? byFy.get(k) : undefined;
  });
  if (points.filter(Boolean).length < 2) return option;

  // The running FY (live, provisional) usually has no revenue yet: add an "FYxx YTD" slot carrying only the oil value,
  // so the live Yahoo price is visible on the chart itself.
  const fyNum = (k: string | null) => (k ? parseInt(k.slice(2), 10) : -1);
  const lastFy = Math.max(...labels.map((l) => fyNum(fyKey(l))));
  const live = oil.fy_series.find((p) => p.provisional && fyNum(p.fy) === lastFy + 1);
  let extended = false;
  if (live) {
    labels = [...labels, `${live.fy} YTD`];
    points.push(live);
    extended = true;
  }

  // dashed ink line: clearly distinct from the categorical revenue series
  const color = t.text;
  const isFx = oil.benchmark === 'inr';
  const money = (v: number, dp = 0) => (isFx ? `₹${v.toFixed(1)}` : `$${dp ? v.toFixed(dp) : Math.round(v)}`);
  const name = `${oil.short} (${oil.unit}, FY avg)`;
  const yAxes = Array.isArray(option.yAxis) ? [...option.yAxis] : [option.yAxis];
  const rightUsed = yAxes.some((a: any) => a && a.position === 'right');
  yAxes.push({
    type: 'value',
    name: isFx ? '₹ per $' : `${oil.short} $/bbl`,
    position: 'right',
    offset: rightUsed ? px(t, 64) : 0,
    scale: true,
    splitNumber: 4,
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { show: false },
    nameTextStyle: { color, fontSize: px(t, 12), align: 'right' },
    axisLabel: { color, fontSize: px(t, 12), formatter: (v: number) => money(v) },
  });
  const oilAxis = yAxes.length - 1;

  const series = [
    ...(Array.isArray(option.series) ? option.series : [option.series]).map((s: any) => {
      if (!s) return s;
      let out = s;
      // the main series' end label sits where the new right axis goes: keep it but shift it inwards
      if (out.endLabel) out = { ...out, endLabel: { ...out.endLabel, offset: [-px(t, 4), -px(t, 14)] } };
      // the YTD slot has no value for the existing series
      if (extended && Array.isArray(out.data)) out = { ...out, data: [...out.data, null] };
      return out;
    }),
    {
      id: 'oil',
      name,
      type: 'line',
      yAxisIndex: oilAxis,
      z: 5,
      smooth: 0.2,
      symbol: 'circle',
      symbolSize: px(t, 7),
      lineStyle: { width: px(t, 2.25), color, type: [6, 4] },
      itemStyle: { color },
      label: {
        show: labels.length <= 12,
        position: 'top',
        color,
        fontSize: px(t, 11),
        fontWeight: 600,
        formatter: (p: any) => (p.value == null ? '' : `${money(p.value)}${p.data?.provisional ? ' · live' : ''}`),
      },
      data: points.map((p) =>
        p
          ? {
              value: p.avg,
              provisional: p.provisional,
              symbol: p.provisional ? 'emptyCircle' : 'circle',
              symbolSize: p.provisional ? px(t, 10) : px(t, 7),
            }
          : null,
      ),
    },
  ];

  const grid = (Array.isArray(option.grid) ? option.grid : [option.grid]).map((g: any, i: number) =>
    i === 0 && g ? { ...g, right: Math.max(Number(g.right) || 0, px(t, rightUsed ? 128 : 72)), top: Math.max(Number(g.top) || 0, px(t, 48)) } : g,
  );

  const origFmt = option.tooltip?.formatter;
  const tooltip = {
    ...(option.tooltip || {}),
    trigger: 'axis',
    formatter: (ps: any) => {
      const arr = Array.isArray(ps) ? ps : [ps];
      const rest = arr.filter((p: any) => p.seriesId !== 'oil');
      const oilP = arr.find((p: any) => p.seriesId === 'oil');
      const head = typeof origFmt === 'function' && rest.length ? origFmt(rest) : rest.map((p: any) => `${p.seriesName}: ${p.value}`).join('<br/>');
      if (!oilP || oilP.value == null) return head;
      const live = oilP.data?.provisional ? ' (FY to date, live)' : ' (FY average)';
      const val = isFx ? `₹${Number(oilP.value).toFixed(2)} per $` : `$${Number(oilP.value).toFixed(2)}/bbl`;
      return `${head}<div style="margin-top:6px;font-size:12px;color:${color};font-weight:600">● ${oil.short}: ${val}${live}</div>`;
    },
  };

  const xAxis = Array.isArray(option.xAxis)
    ? option.xAxis.map((a: any, i: number) => (i === 0 ? { ...a, data: labels } : a))
    : { ...option.xAxis, data: labels };

  return {
    ...option,
    xAxis,
    grid,
    yAxis: yAxes,
    series,
    tooltip,
    legend: [
      {
        top: 0,
        left: 0,
        icon: 'roundRect',
        itemWidth: px(t, 14),
        itemHeight: px(t, 6),
        textStyle: { color: t.sub, fontSize: px(t, 12) },
        formatter: (n: string) => (n === name ? n : legendName(n)),
      },
    ],
  };
}

/** Pearson correlation between the chart's main series and the oil series over the FYs both have (null if < 3). */
export function oilCorrelation(spec: ChartSpec | null | undefined, oil: OilPricePayload): { r: number; n: number } | null {
  const data = (spec?.data || []) as Record<string, any>[];
  const xKey = (spec as any)?.x || (spec as any)?.category;
  const yKey = (spec as any)?.y || (spec as any)?.value;
  if (!xKey || !yKey) return null;
  const byFy = new Map(oil.fy_series.filter((p) => !p.provisional).map((p) => [p.fy, p.avg]));
  const pairs: [number, number][] = [];
  for (const r of data) {
    const k = fyKey(r[xKey]);
    const y = Number(r[yKey]);
    const o = k ? byFy.get(k) : undefined;
    if (o !== undefined && Number.isFinite(y)) pairs.push([y, o]);
  }
  if (pairs.length < 3) return null;
  const n = pairs.length;
  const mx = pairs.reduce((a, p) => a + p[0], 0) / n;
  const my = pairs.reduce((a, p) => a + p[1], 0) / n;
  let sxy = 0, sxx = 0, syy = 0;
  for (const [x, y] of pairs) {
    sxy += (x - mx) * (y - my);
    sxx += (x - mx) ** 2;
    syy += (y - my) ** 2;
  }
  if (!sxx || !syy) return null;
  return { r: sxy / Math.sqrt(sxx * syy), n };
}
