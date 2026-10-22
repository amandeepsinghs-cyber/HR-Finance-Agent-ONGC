'use client';

import React, { useMemo } from 'react';
import * as echarts from 'echarts';
import { MapSpec } from '@/contracts/answerContract';
import { INDIA_GEO_JSON } from '@/data/indiaGeoJson';
import { EChart } from '@/charts/EChart';
import { useChartTokens } from './ChartRenderer';
import { px, tooltipBase, tooltipCard, ANIM } from '@/charts/theme';
import { fmtNum, humanizeValue } from '@/charts/format';

interface MapRendererProps {
  mapSpec: MapSpec;
  isDark?: boolean;
}

let registered = false;
function ensureMap() {
  if (registered) return;
  echarts.registerMap('india', INDIA_GEO_JSON as any);
  registered = true;
}

const NEG_STATUS = /loss|deficit|negative|critical|shortfall/i;

export const MapRenderer: React.FC<MapRendererProps> = ({ mapSpec, isDark = false }) => {
  const t = useChartTokens(isDark);
  const points = useMemo(() => [...(mapSpec.points || [])].sort((a, b) => (b.value || 0) - (a.value || 0)), [mapSpec]);
  const metric = points[0]?.metricLabel || 'Value';
  const total = points.reduce((s, p) => s + (p.value || 0), 0);

  const option = useMemo(() => {
    ensureMap();
    const maxV = Math.max(1, ...points.map((p) => Math.abs(p.value || 0)));
    const size = (v: number) => px(t, 8) + Math.sqrt(Math.abs(v) / maxV) * px(t, 46);
    const top5 = new Set(points.slice(0, 5).map((p) => p.name));
    const data = points.map((p) => {
      const neg = (p.value || 0) < 0 || NEG_STATUS.test(String(p.status || ''));
      return {
        name: humanizeValue(p.name),
        value: [p.lon, p.lat, p.value || 0],
        pt: p,
        symbolSize: size(p.value || 0),
        itemStyle: {
          color: new echarts.graphic.RadialGradient(0.4, 0.35, 0.75, [
            { offset: 0, color: neg ? t.maroonSoft : t.accentSoft },
            { offset: 1, color: neg ? t.maroon : t.accentDeep },
          ]),
          opacity: 0.88,
          borderColor: t.dark ? 'rgba(255,255,255,0.65)' : '#FFFFFF',
          borderWidth: 1.5,
          shadowBlur: px(t, 14),
          shadowColor: neg ? 'rgba(142,0,12,0.35)' : 'rgba(26,86,219,0.35)',
        },
        label: { show: top5.has(p.name) },
      };
    });
    return {
      backgroundColor: 'transparent',
      ...ANIM,
      title: [],
      legend: [],
      graphic: [],
      grid: [],
      xAxis: [],
      yAxis: [],
      dataZoom: [],
      tooltip: {
        ...tooltipBase(t),
        trigger: 'item',
        formatter: (p: any) => {
          const pt = p.data?.pt;
          if (!pt) return '';
          const share = total > 0 ? ` · ${fmtNum(((pt.value || 0) / total) * 100, 1)}% of shown` : '';
          return tooltipCard(t, humanizeValue(pt.name), [
            [pt.metricLabel || 'Value', fmtNum(pt.value || 0)],
            ...(pt.status ? ([['Type', String(pt.status)]] as [string, string][]) : []),
            ...(share ? ([['Share', share.replace(' · ', '').replace(' of shown', '')]] as [string, string][]) : []),
          ]);
        },
      },
      geo: {
        map: 'india',
        roam: true,
        scaleLimit: { min: 0.8, max: 6 },
        zoom: 1.08,
        center: [82.8, 22.6],
        silent: true,
        itemStyle: {
          areaColor: t.dark ? '#1F2228' : '#EEF3FA',
          borderColor: t.dark ? '#3A3F48' : '#B8C7DB',
          borderWidth: 1.2,
          shadowColor: t.dark ? 'rgba(0,0,0,0.5)' : 'rgba(26,86,219,0.12)',
          shadowBlur: px(t, 24),
          shadowOffsetY: px(t, 6),
        },
        emphasis: { disabled: true },
      },
      series: [
        {
          id: 'main',
          type: 'scatter',
          coordinateSystem: 'geo',
          data,
          universalTransition: { enabled: true },
          label: {
            position: 'right',
            distance: px(t, 6),
            color: t.text,
            fontSize: px(t, 12),
            fontWeight: 600,
            textBorderColor: t.dark ? '#121316' : '#FFFFFF',
            textBorderWidth: 3,
            formatter: (p: any) => `${p.name}\n{v|${fmtNum(p.value[2])}}`,
            rich: { v: { color: t.sub, fontSize: px(t, 11), fontWeight: 500, textBorderColor: t.dark ? '#121316' : '#FFFFFF', textBorderWidth: 3 } },
          },
          labelLayout: { hideOverlap: true, moveOverlap: 'shiftY' },
          emphasis: { scale: 1.15, label: { show: true }, itemStyle: { opacity: 1 } },
          zlevel: 1,
        },
        {
          id: 'pulse',
          type: 'effectScatter',
          coordinateSystem: 'geo',
          data: data.slice(0, 1).map((d) => ({ ...d, label: { show: false } })),
          rippleEffect: { brushType: 'stroke', scale: 2.2, period: 3.5 },
          itemStyle: { color: 'transparent', borderColor: t.accent, borderWidth: 1.5 },
          silent: true,
          zlevel: 0,
        },
      ],
    } as echarts.EChartsOption;
  }, [points, t, total]);

  const maxV = Math.max(1, ...points.map((p) => p.value || 0));

  return (
    <div className="grid h-full gap-6 grid-cols-1 lg:grid-cols-[minmax(0,1.7fr)_minmax(15rem,1fr)]">
      <div className="relative h-full min-h-[24rem]">
        <EChart option={option} testId="india-map" />
        <div className="absolute left-2 bottom-1 text-[0.68rem] text-[var(--ink-3)]">
          Boundary: Survey of India (DataMeet, CC BY 2.5 IN) · scroll to zoom
        </div>
      </div>
      <div className="flex flex-col min-h-0">
        <div className="text-[0.78rem] font-medium text-[var(--ink-2)] mb-2">
          {metric} · top {Math.min(8, points.length)} of {points.length}
        </div>
        <ol className="flex flex-col gap-[0.45rem] overflow-y-auto pr-1">
          {points.slice(0, 8).map((p, i) => (
            <li key={p.name} className="grid grid-cols-[1.4rem_minmax(0,1fr)_auto] items-center gap-2 text-[0.9rem]">
              <span className="text-[var(--ink-3)] tabular-nums text-[0.8rem]">{i + 1}</span>
              <span className="min-w-0">
                <span className="block truncate font-medium text-[var(--ink)]" title={humanizeValue(p.name)}>
                  {humanizeValue(p.name)}
                </span>
                <span className="block h-[4px] mt-1 rounded-full bg-[var(--track)]">
                  <span
                    className="block h-full rounded-full"
                    style={{ width: `${((p.value || 0) / maxV) * 100}%`, background: 'linear-gradient(90deg, var(--accent-soft), var(--accent))' }}
                  />
                </span>
              </span>
              <span className="font-semibold tabular-nums text-[var(--ink)]">{fmtNum(p.value || 0)}</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
};
