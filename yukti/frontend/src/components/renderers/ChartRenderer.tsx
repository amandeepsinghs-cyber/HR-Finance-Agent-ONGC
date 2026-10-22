'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { ChartSpec, KpiTile } from '@/contracts/answerContract';
import { planChart, ChartPlan, Row } from '@/charts/plan';
import { getTokens, ChartTokens } from '@/charts/theme';
import { EChart } from '@/charts/EChart';
import {
  rankedOption,
  columnOption,
  donutOption,
  pieOption,
  histogramOption,
  areaOption,
  scatterOption,
  treemapOption,
  funnelOption,
  waterfallOption,
  bulletOption,
  lineOption,
  groupedOption,
  stackedOption,
  ramp,
} from '@/charts/options';
import { fmtValue, fmtNum, humanizeKey, humanizeValue, parseUnit, toNumber } from '@/charts/format';
import { KpiRenderer } from './KpiRenderer';

interface ChartRendererProps {
  spec: ChartSpec;
  isDark?: boolean;
  title?: string;
}

/** Recompute tokens when the root font-size (big-screen scale) changes. */
export function useChartTokens(isDark: boolean): ChartTokens {
  const [scaleKey, setScaleKey] = useState(0);
  useEffect(() => {
    let last = getComputedStyle(document.documentElement).fontSize;
    const onResize = () => {
      const now = getComputedStyle(document.documentElement).fontSize;
      if (now !== last) {
        last = now;
        setScaleKey((k) => k + 1);
      }
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  return useMemo(() => getTokens(isDark), [isDark, scaleKey]);
}

function donutColors(plan: ChartPlan, t: ChartTokens): string[] {
  const n = plan.rows.length;
  // Rubric C4: lightest ordinal slice must stay visible (light: from sequential[2]; dark: from [0], ≥3:1).
  if (plan.ordinal) return ramp(t.sequential[t.dark ? 0 : 2], t.sequential[5], n);
  return t.categorical.slice(0, n);
}

const DonutWithLegend: React.FC<{ plan: ChartPlan; t: ChartTokens; isPie?: boolean }> = ({ plan, t, isPie = false }) => {
  const colors = donutColors(plan, t);
  const option = useMemo(() => (isPie ? pieOption(plan, t, colors) : donutOption(plan, t, colors)), [plan, t, isPie]); // eslint-disable-line react-hooks/exhaustive-deps
  const maxV = Math.max(...plan.rows.map((r) => r.value));
  return (
    <div className="grid h-full min-h-0 grid-cols-1 md:grid-cols-[minmax(0,1.15fr)_minmax(0,0.95fr)] md:grid-rows-[minmax(0,1fr)] gap-6 items-center">
      <div className="h-full min-h-[18rem]">
        <EChart option={option} testId={isPie ? 'chart-pie' : 'chart-donut'} />
      </div>
      {/* Rubric C3/C5: legend never clips. It scrolls within the card, and dense mode applies for > 6 rows. */}
      <ul className={`flex flex-col self-center max-h-full min-h-0 overflow-y-auto pr-1 ${plan.rows.length > 6 ? 'gap-0 text-[0.875rem]' : 'gap-[0.35rem] text-[0.9rem]'}`} aria-label="Legend">
        {plan.rows.map((r, i) => {
          const pct = (r.value / Math.max(1, plan.total)) * 100;
          return (
            <li key={r.label} className={`grid grid-cols-[0.75rem_minmax(0,1fr)_auto_3.2rem] items-center gap-3 ${plan.rows.length > 6 ? 'py-[0.1rem]' : 'py-[0.3rem]'} border-b border-[var(--hairline)] last:border-0`}>
              <span className="w-3 h-3 rounded-[4px]" style={{ background: colors[i % colors.length] }} />
              <span className="truncate font-medium text-[var(--ink)]" title={r.label}>
                {r.label}
                <span className="block h-[3px] mt-1 rounded-full bg-[var(--track)]">
                  <span className="block h-full rounded-full" style={{ width: `${(r.value / maxV) * 100}%`, background: colors[i % colors.length] }} />
                </span>
              </span>
              <span className="font-semibold tabular-nums text-[var(--ink)]">{fmtValue(r.value, plan.unit)}</span>
              <span className="text-right tabular-nums text-[var(--ink-2)]">{fmtNum(pct, 1)}%</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
};

/** Panel title for small multiples (each panel = one measure, its own unit axis). */
function withTitle(opt: any, title: string, t: ChartTokens): any {
  if (!opt) return opt;
  return { ...opt, title: { text: title, left: 0, top: 0, textStyle: { color: t.text, fontSize: Math.round(14 * ((t as any).scale || 1)), fontWeight: 600 } }, grid: Array.isArray(opt.grid) ? opt.grid.map((g: any) => ({ ...g, top: Math.max(+g.top || 0, 40) })) : { ...(opt.grid || {}), top: 40 } };
}

const SmallMultiples: React.FC<{ plan: ChartPlan; spec: ChartSpec; t: ChartTokens }> = ({ plan, spec, t }) => {
  const data = (spec.data || []) as Record<string, any>[];
  const first = plan.seriesKeys[0];
  // Time series / ordered buckets keep their order (one line or column per measure); categories are ranked.
  const ordered = plan.timeLike || plan.ordinal;
  const order = ordered ? data : [...data].sort((a, b) => (toNumber(b[first]) || 0) - (toNumber(a[first]) || 0));
  const panels = plan.seriesKeys.map((k) => {
    const rows: Row[] = order.map((r) => ({ label: humanizeValue(r[plan.dimKey]), raw: r, value: toNumber(r[k]) ?? 0 }));
    // keep a shared unit (e.g. "Executives") when the split was only by size; drop it when families differ
    const sharedUnit = new Set(plan.seriesKeys.map((x) => parseUnit(spec.unit, x).kind)).size === 1 ? spec.unit : undefined;
    const sub: ChartPlan = { ...plan, valueKey: k, seriesKeys: [k], rows, unit: parseUnit(sharedUnit, k), total: rows.reduce((s, r) => s + r.value, 0) };
    const asLine = plan.timeLike || spec.kind === 'line' || spec.kind === 'area';
    const option = asLine
      ? withTitle(lineOption(sub, t, order), humanizeKey(k), t)
      : plan.ordinal
        ? withTitle(columnOption(sub, t), humanizeKey(k), t)
        : rankedOption(sub, t, { compact: true, title: humanizeKey(k), labelPx: 115 });
    return { k, option };
  });
  return (
    <div className="grid h-full gap-6" style={{ gridTemplateColumns: `repeat(${Math.min(panels.length, 3)}, minmax(0, 1fr))` }}>
      {panels.map((p) => (
        <div key={p.k} className="h-full min-h-[18rem]">
          <EChart option={p.option} testId="chart-multiple" />
        </div>
      ))}
    </div>
  );
};

export const ChartRenderer: React.FC<ChartRendererProps> = ({ spec, isDark = false }) => {
  const t = useChartTokens(isDark);
  const plan = useMemo(() => planChart(spec), [spec]);

  const option = useMemo(() => {
    const data = (spec.data || []) as Record<string, any>[];
    const colors = donutColors(plan, t);
    switch (plan.form) {
      case 'ranked':
      case 'diverging':
        return rankedOption(plan, t);
      case 'column':
        return columnOption(plan, t);
      case 'histogram':
        return histogramOption(plan, t);
      case 'waterfall':
        return waterfallOption(plan, t);
      case 'bullet':
        return bulletOption(plan, t);
      case 'line':
        return lineOption(plan, t, data);
      case 'area':
        return areaOption(plan, t, data);
      case 'scatter':
        return scatterOption(plan, t, data);
      case 'treemap':
        return treemapOption(plan, t, colors);
      case 'funnel':
        return funnelOption(plan, t, colors);
      case 'grouped':
        return groupedOption(plan, t, data);
      case 'stacked':
        return stackedOption(plan, t, data);
      default:
        return null;
    }
  }, [plan, t, spec.data]);

  if (!plan.rows.length) {
    return <div className="h-full grid place-items-center text-[var(--ink-2)]">No data returned for this view.</div>;
  }

  if (plan.form === 'kpi') {
    const row = plan.rows[0].raw;
    const kpis: KpiTile[] = Object.entries(row)
      .filter(([, v]) => toNumber(v) !== null)
      .slice(0, 3)
      .map(([k, v]) => ({ label: humanizeKey(k), value: toNumber(v) as number, unit: parseUnit(spec.unit, k).noun }));
    return <KpiRenderer kpis={kpis} isDark={isDark} hero />;
  }

  return (
    <div className="w-full h-full" data-chart-form={plan.form}>
      {plan.form === 'donut' ? (
        <DonutWithLegend plan={plan} t={t} isPie={false} />
      ) : plan.form === 'pie' ? (
        <DonutWithLegend plan={plan} t={t} isPie={true} />
      ) : plan.form === 'multiples' ? (
        <SmallMultiples plan={plan} spec={spec} t={t} />
      ) : option ? (
        <EChart option={option} testId={`chart-${plan.form}`} />
      ) : null}
    </div>
  );
};
