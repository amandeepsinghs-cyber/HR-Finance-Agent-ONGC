'use client';

import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { MapSpec } from '@/contracts/answerContract';
import { INDIA_GEO_JSON } from '@/data/indiaGeoJson';
import { formatIndianNumber } from '@/utils/numberFormat';

interface MapRendererProps {
  mapSpec: MapSpec;
  isDark?: boolean;
}

export const MapRenderer: React.FC<MapRendererProps> = ({ mapSpec, isDark = false }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartInstanceRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Register India GeoJSON map
    try {
      echarts.registerMap('india', INDIA_GEO_JSON as any);
    } catch (e) {
      console.warn('Map registration error:', e);
    }

    if (!chartInstanceRef.current) {
      chartInstanceRef.current = echarts.init(containerRef.current, isDark ? 'dark' : undefined, {
        renderer: 'canvas',
      });
    }

    const chart = chartInstanceRef.current;

    const handleResize = () => chart.resize();
    window.addEventListener('resize', handleResize);

    const scatterData = (mapSpec.points || []).map((pt) => ({
      name: pt.name,
      value: [pt.lon, pt.lat, pt.value || 100],
      ptData: pt,
    }));

    const bgMapColor = isDark ? '#1E2024' : '#F1F3F4';
    const borderColor = isDark ? '#373B44' : '#D0D5DD';
    const hoverColor = isDark ? '#2A2D35' : '#E8F0FE';

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: isDark ? '#1E2024' : '#FFFFFF',
        borderColor: isDark ? '#2D3139' : '#E0E3E7',
        textStyle: { color: isDark ? '#F1F3F4' : '#1F1F1F', fontSize: 13 },
        formatter: (params: any) => {
          const pt = params.data?.ptData;
          if (!pt) return params.name;
          const statusBadge = pt.status
            ? `<span style="background:#3186FF20;color:#3186FF;padding:2px 6px;border-radius:4px;font-size:11px;font-weight:600;">${pt.status}</span>`
            : '';
          return `
            <div style="font-weight:600;font-size:14px;margin-bottom:4px;">${pt.name}</div>
            <div style="margin-bottom:4px;">${statusBadge}</div>
            <div>${pt.metricLabel || 'Deployed Count'}: <b>${formatIndianNumber(pt.value)}</b></div>
            <div style="color:#5F6368;font-size:11px;margin-top:2px;">Work Centre: ${pt.wc_id || 'ONGC Asset'}</div>
          `;
        },
      },
      geo: {
        map: 'india',
        roam: true,
        zoom: 1.15,
        center: [82.5, 22.0],
        itemStyle: {
          areaColor: bgMapColor,
          borderColor: borderColor,
          borderWidth: 1.2,
        },
        emphasis: {
          itemStyle: {
            areaColor: hoverColor,
            borderColor: '#3186FF',
          },
          label: { show: false },
        },
      },
      series: [
        {
          name: 'ONGC Assets & Work Centres',
          type: 'effectScatter',
          coordinateSystem: 'geo',
          data: scatterData,
          symbolSize: (val: any) => {
            const count = val[2] || 100;
            return Math.max(12, Math.min(26, 10 + count / 200));
          },
          showEffectOn: 'render',
          rippleEffect: {
            brushType: 'stroke',
            scale: 3.5,
            period: 4,
          },
          itemStyle: {
            color: '#3186FF',
            shadowBlur: 10,
            shadowColor: 'rgba(49, 134, 255, 0.6)',
          },
          label: {
            show: true,
            formatter: (params: any) => {
              const val = params.data?.value?.[2] || 0;
              // De-overlap: statically label only top assets (>16,000 count), others reveal on hover
              return val >= 16000 ? params.name : '';
            },
            position: 'right',
            offset: [8, 0],
            fontSize: 11,
            fontWeight: 600,
            color: isDark ? '#FFFFFF' : '#1F1F1F',
          },
          emphasis: {
            scale: 1.3,
            label: {
              show: true,
              formatter: '{b}',
              position: 'top',
              fontSize: 12,
              fontWeight: 'bold',
              color: isDark ? '#FFFFFF' : '#1F1F1F',
            },
          },
          labelLayout: {
            hideOverlap: true,
            moveOverlap: 'shiftY',
          },
        },
      ],
    };

    chart.setOption(option, true);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [mapSpec, isDark]);

  return (
    <div className="w-full h-full min-h-[460px] relative">
      <div ref={containerRef} className="w-full h-full min-h-[460px]" />
      <div className="absolute bottom-2 left-2 text-[10px] text-zinc-500 dark:text-zinc-400 bg-white/80 dark:bg-zinc-900/80 px-2 py-0.5 rounded backdrop-blur-sm border border-zinc-200 dark:border-zinc-800">
        Survey of India Boundary (DataMeet, CC BY 2.5 IN)
      </div>
    </div>
  );
};
