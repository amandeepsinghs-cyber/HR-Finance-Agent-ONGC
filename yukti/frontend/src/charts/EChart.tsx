'use client';

import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

const REPLACE = ['series', 'xAxis', 'yAxis', 'grid', 'graphic', 'legend', 'title', 'dataZoom'];

interface EChartProps {
  option: echarts.EChartsOption;
  className?: string;
  style?: React.CSSProperties;
  testId?: string;
}

/** Thin ECharts host: one instance per mount, ResizeObserver, morphing updates. */
export const EChart: React.FC<EChartProps> = ({ option, className = '', style, testId }) => {
  const el = useRef<HTMLDivElement | null>(null);
  const inst = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!el.current) return;
    const chart = echarts.init(el.current, undefined, { renderer: 'canvas' });
    inst.current = chart;
    const ro = new ResizeObserver(() => chart.resize({ animation: { duration: 200 } }));
    ro.observe(el.current);
    return () => {
      ro.disconnect();
      chart.dispose();
      inst.current = null;
    };
  }, []);

  useEffect(() => {
    if (!inst.current) return;
    inst.current.setOption(option, { replaceMerge: REPLACE } as any);
    requestAnimationFrame(() => inst.current?.resize());
  }, [option]);

  return <div ref={el} data-testid={testId} className={`w-full h-full min-w-0 overflow-hidden ${className}`} style={style} />;
};
