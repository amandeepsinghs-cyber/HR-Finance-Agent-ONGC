'use client';

import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { ChartSpec } from '@/contracts/answerContract';
import { formatIndianNumber } from '@/utils/numberFormat';

interface ChartRendererProps {
  spec: ChartSpec;
  isDark?: boolean;
  title?: string;
  onPointClick?: (point: any) => void;
}

export const ChartRenderer: React.FC<ChartRendererProps> = ({
  spec,
  isDark = false,
  title,
  onPointClick,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartInstanceRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    if (!chartInstanceRef.current) {
      chartInstanceRef.current = echarts.init(containerRef.current, isDark ? 'dark' : undefined, {
        renderer: 'canvas',
      });
    }

    const chart = chartInstanceRef.current;

    // Responsive resize listener
    const handleResize = () => {
      chart.resize();
    };
    window.addEventListener('resize', handleResize);

    const bgTextColor = isDark ? '#FFFFFF' : '#1F1F1F';
    const subTextColor = isDark ? '#C4C7C5' : '#5F6368';
    const gridLineColor = isDark ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.06)';

    // AlphaEvolve Palette: Blue ramp #3186FF -> #76BBFF plus neutrals, with maroon (#8E000C) for emphasis/alerts
    const palette = [
      '#1A56DB', // Deep Cobalt Blue
      '#2563EB', // Royal Blue
      '#3186FF', // Bright Accent Blue (AlphaEvolve)
      '#4F96FF', // Vivid Cerulean
      '#76BBFF', // Soft Sky Blue (AlphaEvolve Secondary)
      '#93C5FD', // Light Sky Blue
      '#64748B', // Slate Neutral
      '#94A3B8', // Light Slate Neutral
      '#CBD5E1', // Pale Neutral
      '#8E000C', // Official ONGC Maroon (Emphasis / Alert)
    ];

    let option: echarts.EChartsOption = {};

    switch (spec.kind) {
      case 'donut': {
        const catKey = spec.category || 'grade';
        const valKey = spec.value || 'count';

        // Cap to top 12 categories (+ Others) if > 12
        let rawDonutData = spec.data;
        if (rawDonutData.length > 12) {
          const sorted = [...rawDonutData].sort((a, b) => (Number(b[valKey]) || 0) - (Number(a[valKey]) || 0));
          const top11 = sorted.slice(0, 11);
          const otherSum = sorted.slice(11).reduce((sum, item) => sum + (Number(item[valKey]) || 0), 0);
          top11.push({ [catKey]: 'Others', [valKey]: otherSum });
          rawDonutData = top11;
        }

        const chartData = rawDonutData.map((d) => ({
          name: d[catKey] || d.name,
          value: d[valKey] || d.value,
          item: d,
        }));

        option = {
          backgroundColor: 'transparent',
          color: palette,
          tooltip: {
            trigger: 'item',
            backgroundColor: isDark ? '#1E2024' : '#FFFFFF',
            borderColor: isDark ? '#2D3139' : '#E0E3E7',
            textStyle: { color: bgTextColor, fontSize: 14 },
            formatter: (params: any) => {
              const item = params.data.item || {};
              const dueInfo = item.due !== undefined ? `<br/><span style="color:#D93025;font-weight:600;">Due for rotation: ${item.due}</span>` : '';
              const exemptInfo = item.exempt ? `<br/><span style="color:#5F6368">Superannuation exempt: ${item.exempt}</span>` : '';
              return `<strong>${params.name}</strong><br/>Total: <b>${params.value}</b> (${params.percent}%)${dueInfo}${exemptInfo}`;
            },
          },
          legend: {
            orient: 'horizontal',
            bottom: '2%',
            textStyle: { color: subTextColor, fontSize: 13 },
            type: 'scroll',
          },
          series: [
            {
              name: title || 'Distribution',
              type: 'pie',
              radius: ['50%', '76%'],
              center: ['50%', '46%'],
              avoidLabelOverlap: true,
              itemStyle: {
                borderRadius: 5,
                borderColor: isDark ? '#121316' : '#FFFFFF',
                borderWidth: 2,
              },
              label: {
                show: true,
                position: 'outside',
                color: bgTextColor,
                formatter: '{b}: {c}',
                fontSize: 13,
                fontWeight: 500,
              },
              emphasis: {
                label: {
                  show: true,
                  fontSize: 15,
                  fontWeight: 'bold',
                },
                itemStyle: {
                  shadowBlur: 10,
                  shadowOffsetX: 0,
                  shadowColor: 'rgba(0, 0, 0, 0.25)',
                },
              },
              data: chartData,
            },
          ],
        };
        break;
      }

      case 'hbar': {
        const yKey = spec.y || 'field';
        const valKey = spec.value || 'pbt_cr';
        const unit = spec.unit || '';
        let sortedData = [...spec.data];
        if (spec.sort === 'desc') {
          sortedData.sort((a, b) => (Number(a[valKey]) || 0) - (Number(b[valKey]) || 0)); // Ascending for hbar displays top on top
        }

        // Cap to top 12 categories
        if (sortedData.length > 12) {
          sortedData = sortedData.slice(-12);
        }

        const yCategories = sortedData.map((d) => d[yKey] || d.name);
        const seriesData = sortedData.map((d) => {
          const val = Number(d[valKey]) || 0;
          return {
            value: val,
            itemStyle: {
              color: val < 0 ? '#8E000C' : '#3186FF',
              borderRadius: val < 0 ? [4, 0, 0, 4] : [0, 4, 4, 0],
            },
          };
        });

        option = {
          backgroundColor: 'transparent',
          tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: isDark ? '#1E2024' : '#FFFFFF',
            borderColor: isDark ? '#2D3139' : '#E0E3E7',
            textStyle: { color: bgTextColor },
            formatter: (params: any) => {
              const p = params[0];
              const raw = sortedData[p.dataIndex];
              const rev = raw?.revenue_cr ? `<br/>Gross Revenue: ${formatIndianNumber(raw.revenue_cr, { currency: true, unit: 'Cr' })}` : '';
              return `<strong>${p.name}</strong><br/>Value: <b>${formatIndianNumber(p.value, { unit })}</b>${rev}`;
            },
          },
          grid: {
            left: '26%',
            right: '8%',
            bottom: '8%',
            top: '4%',
            containLabel: false,
          },
          xAxis: {
            type: 'value',
            splitLine: { lineStyle: { color: gridLineColor } },
            axisLabel: {
              color: subTextColor,
              formatter: (v: number) => unit ? `${v} ${unit}` : `${v}`,
            },
          },
          yAxis: {
            type: 'category',
            data: yCategories,
            axisLabel: { color: bgTextColor, fontSize: 13, fontWeight: 500 },
            axisTick: { show: false },
            axisLine: { lineStyle: { color: gridLineColor } },
          },
          series: [
            {
              type: 'bar',
              data: seriesData,
              barWidth: '55%',
              label: {
                show: true,
                position: 'right',
                formatter: (p: any) => unit ? `${p.value} ${unit}` : `${p.value}`,
                color: bgTextColor,
                fontSize: 12,
              },
            },
          ],
        };
        break;
      }

      case 'grouped_bar': {
        const xKey = spec.x || 'asset';
        const categories = spec.data.map((d) => d[xKey]);
        const keys = Object.keys(spec.data[0] || {}).filter((k) => k !== xKey && typeof spec.data[0][k] === 'number');

        option = {
          backgroundColor: 'transparent',
          color: ['#3186FF', '#8E000C', '#76BBFF', '#64748B'],
          tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: isDark ? '#1E2024' : '#FFFFFF',
            borderColor: isDark ? '#2D3139' : '#E0E3E7',
            textStyle: { color: bgTextColor },
          },
          legend: {
            bottom: '2%',
            textStyle: { color: subTextColor },
          },
          grid: {
            left: '5%',
            right: '4%',
            bottom: '12%',
            top: '8%',
            containLabel: true,
          },
          xAxis: {
            type: 'category',
            data: categories,
            axisLabel: { color: bgTextColor, interval: 0, rotate: 12, fontSize: 12 },
          },
          yAxis: {
            type: 'value',
            name: spec.unit || '% Change',
            nameTextStyle: { color: subTextColor },
            splitLine: { lineStyle: { color: gridLineColor } },
            axisLabel: { color: subTextColor },
          },
          series: keys.map((key) => ({
            name: key,
            type: 'bar',
            barGap: '15%',
            data: spec.data.map((d) => d[key]),
            itemStyle: { borderRadius: [4, 4, 0, 0] },
          })),
        };
        break;
      }

      case 'stacked_bar': {
        const xKey = spec.x || 'customer';
        const categories = spec.data.map((d) => d[xKey]);
        const keys = Object.keys(spec.data[0] || {}).filter((k) => k !== xKey && typeof spec.data[0][k] === 'number');

        option = {
          backgroundColor: 'transparent',
          color: ['#1A56DB', '#3186FF', '#76BBFF', '#64748B', '#8E000C'],
          tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: isDark ? '#1E2024' : '#FFFFFF',
            borderColor: isDark ? '#2D3139' : '#E0E3E7',
            textStyle: { color: bgTextColor },
          },
          legend: {
            bottom: '2%',
            textStyle: { color: subTextColor },
          },
          grid: {
            left: '5%',
            right: '4%',
            bottom: '12%',
            top: '8%',
            containLabel: true,
          },
          xAxis: {
            type: 'category',
            data: categories,
            axisLabel: { color: bgTextColor, interval: 0, rotate: 10, fontSize: 12 },
          },
          yAxis: {
            type: 'value',
            name: '₹ Crore',
            splitLine: { lineStyle: { color: gridLineColor } },
            axisLabel: { color: subTextColor },
          },
          series: keys.map((key) => ({
            name: key,
            type: 'bar',
            stack: 'total',
            data: spec.data.map((d) => d[key]),
          })),
        };
        break;
      }

      case 'waterfall': {
        const stages = spec.data.map((d) => d.stage);
        const amounts = spec.data.map((d) => d.amount_cr);

        // Compute waterfall bases
        const baseValues: number[] = [];
        const barValues: number[] = [];
        let runningTotal = 0;

        for (let i = 0; i < amounts.length; i++) {
          const amt = amounts[i];
          const isTotal = spec.data[i].type === 'total';

          if (isTotal) {
            baseValues.push(0);
            barValues.push(amt);
            runningTotal = amt;
          } else {
            if (amt >= 0) {
              baseValues.push(runningTotal);
              barValues.push(amt);
              runningTotal += amt;
            } else {
              runningTotal += amt;
              baseValues.push(runningTotal);
              barValues.push(Math.abs(amt));
            }
          }
        }

        option = {
          backgroundColor: 'transparent',
          tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: isDark ? '#1E2024' : '#FFFFFF',
            borderColor: isDark ? '#2D3139' : '#E0E3E7',
            textStyle: { color: bgTextColor },
            formatter: (params: any) => {
              const idx = params[0].dataIndex;
              const d = spec.data[idx];
              return `<strong>${d.stage}</strong><br/>Delta: <b>${formatIndianNumber(d.amount_cr, { currency: true, unit: 'Cr' })}</b>`;
            },
          },
          grid: {
            left: '5%',
            right: '4%',
            bottom: '14%',
            top: '8%',
            containLabel: true,
          },
          xAxis: {
            type: 'category',
            data: stages,
            axisLabel: { color: bgTextColor, interval: 0, rotate: 10, fontSize: 12 },
          },
          yAxis: {
            type: 'value',
            name: '₹ Crore',
            splitLine: { lineStyle: { color: gridLineColor } },
            axisLabel: { color: subTextColor },
          },
          series: [
            {
              name: 'Base',
              type: 'bar',
              stack: 'all',
              itemStyle: { borderColor: 'transparent', color: 'transparent' },
              emphasis: { itemStyle: { borderColor: 'transparent', color: 'transparent' } },
              data: baseValues,
            },
            {
              name: 'Amount',
              type: 'bar',
              stack: 'all',
              label: {
                show: true,
                position: 'top',
                color: bgTextColor,
                formatter: (p: any) => {
                  const val = amounts[p.dataIndex];
                  return `${val > 0 ? '+' : ''}${val}`;
                },
              },
              data: barValues.map((v, i) => {
                const amt = amounts[i];
                const isTotal = spec.data[i].type === 'total';
                let col = '#3186FF';
                if (isTotal) col = '#1A73E8';
                else if (amt < 0) col = '#8E000C';
                else col = '#3186FF';

                return {
                  value: v,
                  itemStyle: { color: col, borderRadius: [4, 4, 0, 0] },
                };
              }),
            },
          ],
        };
        break;
      }

      case 'bullet': {
        const categories = spec.data.map((d) => d.parameter);
        const actuals = spec.data.map((d) => d.achievement_pct);

        option = {
          backgroundColor: 'transparent',
          tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: isDark ? '#1E2024' : '#FFFFFF',
            borderColor: isDark ? '#2D3139' : '#E0E3E7',
            textStyle: { color: bgTextColor },
            formatter: (params: any) => {
              const raw = spec.data[params[0].dataIndex];
              return `<strong>${raw.parameter}</strong><br/>Weightage: ${raw.weight}%<br/>Target: ${raw.target_val}<br/>Actual: ${raw.actual_val}<br/>Achievement: <b>${raw.achievement_pct}%</b> (${raw.status})`;
            },
          },
          grid: {
            left: '28%',
            right: '10%',
            bottom: '8%',
            top: '5%',
            containLabel: false,
          },
          xAxis: {
            type: 'value',
            max: 110,
            splitLine: { lineStyle: { color: gridLineColor } },
            axisLabel: { color: subTextColor, formatter: '{value}%' },
          },
          yAxis: {
            type: 'category',
            data: categories,
            axisLabel: { color: bgTextColor, fontSize: 13 },
            axisTick: { show: false },
          },
          series: [
            {
              type: 'bar',
              barWidth: 20,
              data: actuals.map((val) => ({
                value: val,
                itemStyle: {
                  color: val >= 98 ? '#3186FF' : val >= 94 ? '#76BBFF' : '#8E000C',
                  borderRadius: [0, 4, 4, 0],
                },
              })),
              label: {
                show: true,
                position: 'right',
                formatter: '{c}%',
                color: bgTextColor,
                fontWeight: 600,
              },
              markLine: {
                symbol: 'none',
                data: [{ xAxis: 100, lineStyle: { color: '#8E000C', type: 'dashed', width: 2 } }],
                label: { formatter: 'MoU Target (100%)', position: 'end', color: '#8E000C' },
              },
            },
          ],
        };
        break;
      }

      default: {
        // Default Bar chart
        const xKey = spec.x || Object.keys(spec.data[0] || {})[0];
        const valKey = spec.y || spec.value || Object.keys(spec.data[0] || {})[1];
        const unit = spec.unit || '';

        // Cap to top 12 categories (+ Others) if > 12
        let barData = spec.data;
        if (barData.length > 12) {
          const sorted = [...barData].sort((a, b) => (Number(b[valKey]) || 0) - (Number(a[valKey]) || 0));
          const top11 = sorted.slice(0, 11);
          const otherSum = sorted.slice(11).reduce((sum, item) => sum + (Number(item[valKey]) || 0), 0);
          top11.push({ [xKey]: 'Others', [valKey]: otherSum });
          barData = top11;
        }

        option = {
          backgroundColor: 'transparent',
          color: palette,
          tooltip: {
            trigger: 'axis',
            backgroundColor: isDark ? '#1E2024' : '#FFFFFF',
            borderColor: isDark ? '#2D3139' : '#E0E3E7',
            textStyle: { color: bgTextColor },
          },
          grid: {
            left: '5%',
            right: '4%',
            bottom: '10%',
            top: '8%',
            containLabel: true,
          },
          xAxis: {
            type: 'category',
            data: barData.map((d) => d[xKey]),
            axisLabel: { color: bgTextColor, interval: 0, rotate: 15, fontSize: 12 },
          },
          yAxis: {
            type: 'value',
            splitLine: { lineStyle: { color: gridLineColor } },
            axisLabel: {
              color: subTextColor,
              formatter: (v: number) => unit ? `${v} ${unit}` : `${v}`,
            },
          },
          series: [
            {
              type: 'bar',
              data: barData.map((d) => d[valKey]),
              itemStyle: { borderRadius: [4, 4, 0, 0] },
            },
          ],
        };
      }
    }

    chart.setOption(option, true);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [spec, isDark, title]);

  return (
    <div className="w-full h-full min-h-[360px] relative">
      <div ref={containerRef} className="w-full h-full min-h-[360px]" />
    </div>
  );
};
