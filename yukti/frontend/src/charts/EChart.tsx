'use client';

import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';


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
    // notMerge: a new chart type must not inherit the previous one's series settings (same id 'main' used to merge
    // ranked showBackground / barMaxWidth into columns and freeze morphs — U5.9). universalTransition still morphs.
    inst.current.setOption(option, { notMerge: true });
    requestAnimationFrame(() => inst.current?.resize());
  }, [option]);

  return <div ref={el} data-testid={testId} className={`w-full h-full min-w-0 overflow-hidden ${className}`} style={style} />;
};
