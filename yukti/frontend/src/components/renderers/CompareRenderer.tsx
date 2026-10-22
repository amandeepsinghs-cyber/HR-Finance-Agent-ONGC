'use client';

import React, { useMemo, useState } from 'react';
import * as echarts from 'echarts';
import { CompareSpec, CompareItem } from '@/contracts/answerContract';
import { useChartTokens } from './ChartRenderer';
import { ChartTokens, px, tooltipBase, tooltipCard, anim, alpha } from '@/charts/theme';
import { parseUnit, fmtValue, fmtShare, cleanText, toNumber, UnitInfo } from '@/charts/format';
import { normalizeRows } from '@/charts/normalize';
import { EChart } from '@/charts/EChart';
import { KpiRenderer } from './KpiRenderer';

export interface CompareRendererProps {
  compare: CompareSpec;
  isDark?: boolean;
  unit?: string;
  title?: string;
}

interface ExtractedItem {
  item: CompareItem;
  rows: Record<string, any>[];
  catKey: string;
  valKey: string;
  map: Map<string, number>;
}

function extractItemData(item: CompareItem): ExtractedItem {
  const rawRows = item.chart?.data || [];
  const rows = normalizeRows(undefined, rawRows);

  let catKey = item.chart?.x || item.chart?.category;
  let valKey = item.chart?.y || item.chart?.value;

  if (rows.length > 0) {
    const first = rows[0];
    const keys = Object.keys(first);

    if (!catKey) {
      catKey = keys.find((k) => toNumber(first[k]) === null) || keys[0] || 'category';
    }
    if (!valKey) {
      valKey = keys.find((k) => k !== catKey && toNumber(first[k]) !== null) || keys[1] || 'value';
    }
  }

  const resolvedCat = catKey || 'category';
  const resolvedVal = valKey || 'value';

  const map = new Map<string, number>();
  for (const r of rows) {
    const cat = String(r[resolvedCat] ?? '');
    const num = toNumber(r[resolvedVal]);
    if (cat && num !== null) {
      map.set(cat, num);
    }
  }

  return { item, rows, catKey: resolvedCat, valKey: resolvedVal, map };
}

function isMaroonColor(color: string, t: ChartTokens): boolean {
  const c = color.toLowerCase();
  if (c === t.maroon.toLowerCase() || c === t.maroonSoft.toLowerCase()) return true;
  if (/^#(8e000c|c2414b|ee6b74|b83a43|6a1814|fc413d|ff6b66)/i.test(c)) return true;
  return false;
}

function buildSingleBarOption(
  item: CompareItem,
  info: ExtractedItem,
  t: ChartTokens,
  color: string,
  unitInfo: UnitInfo
): echarts.EChartsOption {
  const cats = Array.from(info.map.keys());
  const data = cats.map((c) => (info.map.has(c) ? info.map.get(c)! : null));
  return {
    backgroundColor: 'transparent',
    textStyle: { fontFamily: t.font, color: t.text },
    ...anim(),
    grid: {
      left: px(t, 8),
      right: px(t, 16),
      top: px(t, 24),
      bottom: px(t, 8),
      containLabel: true,
    },
    tooltip: {
      ...tooltipBase(t),
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const p = Array.isArray(params) ? params[0] : params;
        if (!p) return '';
        const val = info.map.has(p.name) ? info.map.get(p.name)! : null;
        const formatted = val !== null ? fmtValue(val, unitInfo) : '—';
        return tooltipCard(t, p.name, [[item.label, formatted, color]]);
      },
    },
    xAxis: {
      type: 'category',
      data: cats,
      axisTick: { show: false },
      axisLine: { show: true, lineStyle: { color: t.axis } },
      axisLabel: { color: t.text, fontSize: px(t, 12), interval: 0 },
    },
    yAxis: {
      type: 'value',
      name: unitInfo.label || undefined,
      splitLine: { lineStyle: { color: t.grid, type: [4, 4] } },
      axisLabel: { color: t.sub, fontSize: px(t, 11), formatter: (v: number) => fmtValue(v, unitInfo, { compact: true }) },
    },
    series: [
      {
        id: 'main',
        name: item.label,
        type: 'bar',
        barMaxWidth: px(t, 24),
        itemStyle: { color, borderRadius: [px(t, 4), px(t, 4), 0, 0] },
        data,
      },
    ],
  };
}

export const CompareRenderer: React.FC<CompareRendererProps> = ({
  compare,
  isDark = false,
  unit,
  title,
}) => {
  const t = useChartTokens(isDark);
  const items = useMemo(() => compare?.items || [], [compare?.items]);

  const extracted = useMemo(() => items.map(extractItemData), [items]);

  const categories = useMemo(() => {
    const cats: string[] = [];
    const seen = new Set<string>();
    for (const info of extracted) {
      for (const r of info.rows) {
        const cat = String(r[info.catKey] ?? '');
        if (cat && !seen.has(cat)) {
          seen.add(cat);
          cats.push(cat);
        }
      }
    }
    return cats;
  }, [extracted]);

  // U5.9: sites differ in size (2,450 vs 6,820) — "% of site" puts each grade on the same footing.
  const [asShare, setAsShare] = useState(false);
  const totals = useMemo(() => extracted.map((e) => Array.from(e.map.values()).reduce((s, v) => s + v, 0)), [extracted]);
  const shareOf = (idx: number, v: number | null) => (v === null ? null : (v / Math.max(1e-9, totals[idx] || 0)) * 100);
  const shareUnit: UnitInfo = { kind: 'percent', noun: '', label: '% of site' };

  const resolvedUnit = unit || compare?.metric || items[0]?.chart?.unit;
  const unitInfo = useMemo(() => parseUnit(resolvedUnit, compare?.metric), [resolvedUnit, compare?.metric]);

  // Non-maroon categorical palette (maroon reserved for loss)
  const colors = useMemo(() => {
    const nonMaroon = t.categorical.filter((c) => !isMaroonColor(c, t));
    return nonMaroon.length >= 2 ? nonMaroon : t.categorical;
  }, [t]);

  const groupedOption = useMemo<echarts.EChartsOption>(() => {
    return {
      backgroundColor: 'transparent',
      textStyle: { fontFamily: t.font, color: t.text },
      ...anim(),
      legend: {
        top: 0,
        left: 0,
        icon: 'roundRect',
        itemWidth: px(t, 14),
        itemHeight: px(t, 10),
        textStyle: { color: t.sub, fontSize: px(t, 12), fontFamily: t.font },
        data: items.map((i) => i.label),
      },
      grid: {
        left: px(t, 28),
        right: px(t, 24),
        top: px(t, 52),
        bottom: px(t, 8),
        containLabel: true,
      },
      tooltip: {
        ...tooltipBase(t),
        trigger: 'axis',
        axisPointer: {
          type: 'shadow',
          shadowStyle: {
            color: t.dark ? alpha(t.text, 0.04) : alpha(t.accent, 0.06),
          },
        },
        formatter: (params: any) => {
          const list = Array.isArray(params) ? params : [params];
          if (!list.length) return '';
          const catName = list[0]?.name || '';
          const rows: [string, string, string?][] = items.map((item, idx) => {
            const val = extracted[idx]?.map.has(catName) ? extracted[idx].map.get(catName)! : null;
            const formattedVal = val !== null ? `${fmtValue(val, unitInfo)} · ${fmtShare(shareOf(idx, val) as number)}` : '—';
            return [item.label, formattedVal, colors[idx % colors.length]];
          });

          if (items.length === 2) {
            const v0 = extracted[0]?.map.has(catName) ? extracted[0].map.get(catName)! : null;
            const v1 = extracted[1]?.map.has(catName) ? extracted[1].map.get(catName)! : null;
            const diffLabel = `${items[0].label} − ${items[1].label}`;
            if (v0 !== null && v1 !== null) {
              const diff = asShare ? (shareOf(0, v0) as number) - (shareOf(1, v1) as number) : v0 - v1;
              rows.push([diffLabel, asShare ? `${diff > 0 ? '+' : diff < 0 ? '−' : ''}${Math.abs(diff).toFixed(1)} pts` : fmtValue(diff, unitInfo, { sign: true })]);
            } else {
              rows.push([diffLabel, '—']);
            }
          }

          return tooltipCard(t, catName, rows);
        },
      },
      xAxis: {
        type: 'category',
        data: categories,
        axisTick: { show: false },
        axisLine: { show: true, lineStyle: { color: t.axis } },
        axisLabel: {
          color: t.text,
          fontSize: px(t, 13),
          fontWeight: 500,
          margin: px(t, 12),
          interval: 0,
          hideOverlap: false,
        },
      },
      yAxis: {
        type: 'value',
        // Rubric C3: unit name centred and rotated along the axis, clear of the legend row.
        name: (asShare ? shareUnit.label : unitInfo.label) || undefined,
        nameLocation: 'middle',
        nameRotate: 90,
        nameGap: px(t, 48),
        nameTextStyle: {
          color: t.sub,
          fontSize: px(t, 12),
          fontFamily: t.font,
        },
        splitNumber: 4,
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: t.grid, type: [4, 4] } },
        axisLabel: {
          color: t.sub,
          fontSize: px(t, 12),
          fontFamily: t.font,
          formatter: (v: number) => (asShare ? `${Math.round(v)}%` : fmtValue(v, unitInfo, { compact: true })),
        },
      },
      series: items.map((item, idx) => {
        const info = extracted[idx];
        const seriesData = categories.map((cat) => (info.map.has(cat) ? (asShare ? shareOf(idx, info.map.get(cat)!) : info.map.get(cat)!) : null));
        return {
          id: idx === 0 ? 'main' : `s${idx}`,
          name: item.label,
          type: 'bar',
          barGap: '20%',
          barMaxWidth: px(t, 28),
          universalTransition: { enabled: true },
          itemStyle: {
            color: colors[idx % colors.length],
            borderRadius: [px(t, 4), px(t, 4), 0, 0],
          },
          label: {
            show: categories.length <= 12,
            position: 'top',
            color: t.text,
            fontSize: px(t, 12),
            fontWeight: 500,
            fontFamily: t.font,
            formatter: (p: any) =>
              p.value !== null && p.value !== undefined ? (asShare ? fmtShare(p.value) : fmtValue(p.value, unitInfo, { compact: true })) : '',
          },
          data: seriesData,
        };
      }),
    };
  }, [items, categories, extracted, t, unitInfo, colors, asShare, totals]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!items.length) {
    return (
      <div data-testid="compare-view" className="h-full grid place-items-center text-[var(--ink-2)]">
        No comparison data available.
      </div>
    );
  }

  // Small multiples mode
  if (compare?.shared_axis === false) {
    return (
      <div data-testid="compare-view" className="w-full flex flex-col gap-6">
        {title && <h2 className="text-lg font-semibold text-[var(--ink)] tracking-tight">{cleanText(title)}</h2>}

        {/* Header columns with labels and KPIs */}
        <div
          className="grid gap-4 w-full"
          style={{
            gridTemplateColumns: `repeat(${Math.min(items.length, 4)}, minmax(0, 1fr))`,
          }}
        >
          {items.map((item, idx) => (
            <div
              key={item.label}
              className="flex flex-col gap-2 p-4 rounded-xl border border-[var(--hairline)] bg-[var(--surface)]"
            >
              <div className="flex items-center gap-2">
                <span
                  className="w-3 h-3 rounded-full shrink-0"
                  style={{ backgroundColor: colors[idx % colors.length] }}
                />
                <h3
                  data-testid="compare-label"
                  className="text-base font-semibold text-[var(--ink)] tracking-tight truncate"
                  title={item.label}
                >
                  {item.label}
                </h3>
              </div>
              {item.kpis && item.kpis.length > 0 && (
                <div className="mt-1">
                  <KpiRenderer kpis={item.kpis} isDark={isDark} hero={false} />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Small multiples grid */}
        <div
          className="grid gap-4 w-full"
          style={{
            gridTemplateColumns: `repeat(${Math.min(items.length, 3)}, minmax(0, 1fr))`,
          }}
        >
          {items.map((item, idx) => {
            const info = extracted[idx];
            const singleOpt = buildSingleBarOption(item, info, t, colors[idx % colors.length], unitInfo);
            return (
              <div
                key={item.label}
                className="h-[22rem] p-4 rounded-xl border border-[var(--hairline)] bg-[var(--card)]"
              >
                <h4 className="text-sm font-semibold text-[var(--ink-2)] mb-2">{item.label}</h4>
                <div className="w-full h-[calc(100%-2rem)]">
                  <EChart option={singleOpt} testId={idx === 0 ? 'compare-chart' : `compare-chart-${idx}`} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // Standard grouped bar mode with shared axis
  return (
    <div data-testid="compare-view" className="w-full flex flex-col gap-6">
      {title && <h2 className="text-lg font-semibold text-[var(--ink)] tracking-tight">{cleanText(title)}</h2>}

      {/* Header row: one column per item (2–4), each with label + KPIs */}
      <div
        className="grid gap-4 w-full"
        style={{
          gridTemplateColumns: `repeat(${Math.min(items.length, 4)}, minmax(0, 1fr))`,
        }}
      >
        {items.map((item, idx) => (
          <div
            key={item.label}
            className="flex flex-col gap-2 p-4 rounded-xl border border-[var(--hairline)] bg-[var(--surface)]"
          >
            <div className="flex items-center gap-2">
              <span
                className="w-3 h-3 rounded-full shrink-0"
                style={{ backgroundColor: colors[idx % colors.length] }}
              />
              <h3
                data-testid="compare-label"
                className="text-base font-semibold text-[var(--ink)] tracking-tight truncate"
                title={item.label}
              >
                {item.label}
              </h3>
            </div>
            {item.kpis && item.kpis.length > 0 && (
              <div className="mt-1">
                <KpiRenderer kpis={item.kpis} isDark={isDark} hero={false} />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Accessible legend metadata for assertions & assistive tools */}
      <div
        data-testid="compare-legend"
        data-legend-labels={JSON.stringify(items.map((i) => i.label))}
        className="sr-only"
        aria-hidden="true"
      >
        {items.map((i) => i.label).join(', ')}
      </div>

      {/* Grouped bar chart */}
      <div
        className="w-full h-[26rem] min-h-[22rem] p-4 rounded-xl border border-[var(--hairline)] bg-[var(--card)]"
        data-testid="compare-chart-container"
      >
        {unitInfo.kind === 'count' && items.length >= 2 && (
          <div className="relative z-10 float-right -mb-8 flex gap-1 rounded-full border border-[var(--hairline)] p-0.5 text-[0.8125rem]" role="group" aria-label="Measure">
            {[
              { k: false, label: 'Count' },
              { k: true, label: '% of site' },
            ].map((o) => (
              <button
                key={o.label}
                type="button"
                data-testid={o.k ? 'compare-mode-share' : 'compare-mode-count'}
                aria-pressed={asShare === o.k}
                onClick={() => setAsShare(o.k)}
                className={`rounded-full px-3 py-0.5 font-medium transition-colors ${asShare === o.k ? 'bg-[var(--accent-pale)] text-[var(--ink)]' : 'text-[var(--ink-2)] hover:text-[var(--ink)]'}`}
              >
                {o.label}
              </button>
            ))}
          </div>
        )}
        <EChart
          option={groupedOption}
          testId="compare-chart"
        />
      </div>
    </div>
  );
};
