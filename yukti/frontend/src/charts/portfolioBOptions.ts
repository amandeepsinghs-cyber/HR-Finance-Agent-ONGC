/**
 * P4.5 B2 (SPEC-09 §4.5 rows 17, 22, 26): bubble, sunburst and sankey builders.
 *  - Bubble: x · y · size encodings, a size legend (smallest / largest), labels for ≤ 50 bubbles.
 *  - Sunburst: text columns are levels (outer = last), numeric column is the leaf value; parents = Σ children.
 *  - Sankey: {source, target, value} links; node totals conserve flow (in = out for pass-through nodes).
 */
import * as echarts from 'echarts';
import type { ChartPlan } from './plan';
import { ChartTokens, px, tooltipBase, tooltipCard, anim, alpha, labelOn } from './theme';
import { mixHex } from './financeOptions';
import { fmtValue, humanizeKey, humanizeValue, parseUnit, toNumber } from './format';

type Opt = echarts.EChartsOption;

function shell(t: ChartTokens): Opt {
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

// ------------------------------------------------------------------------------------------------ bubble

export function bubbleKeys(plan: ChartPlan, spec: { x?: string; y?: string; value?: string }): { x: string; y: string; size: string } {
  const [a, b, c] = plan.seriesKeys;
  const x = spec.x && plan.seriesKeys.includes(spec.x) ? spec.x : a;
  const y = spec.y && plan.seriesKeys.includes(spec.y) && spec.y !== x ? spec.y : [a, b, c].find((k) => k !== x)!;
  const size = spec.value && spec.value !== x && spec.value !== y ? spec.value : [a, b, c].find((k) => k !== x && k !== y)!;
  return { x, y, size };
}

/** Bubble radius in px: area ∝ value (sqrt scale), 8–48 px diameter. */
export function bubbleSize(v: number, max: number): number {
  if (!(max > 0) || !(v > 0)) return 8;
  return 8 + 40 * Math.sqrt(v / max);
}

export function bubbleOption(plan: ChartPlan, t: ChartTokens, data: Record<string, any>[], spec: { x?: string; y?: string; value?: string; unit?: string }): Opt {
  const { x, y, size } = bubbleKeys(plan, spec);
  const maxSize = Math.max(0, ...data.map((r) => toNumber(r[size]) ?? 0));
  const label = plan.dimKey;
  const showLabels = data.length <= 50;
  const minSize = Math.min(...data.map((r) => toNumber(r[size]) ?? Infinity).filter((v) => Number.isFinite(v)));
  return {
    ...shell(t),
    grid: [{ left: px(t, 44), right: px(t, 24), top: px(t, 48), bottom: px(t, 40), containLabel: true }],
    xAxis: [
      {
        type: 'value',
        name: humanizeKey(x),
        nameLocation: 'middle',
        nameGap: px(t, 28),
        nameTextStyle: { color: t.sub, fontSize: px(t, 12) },
        axisLabel: { color: t.sub, fontSize: px(t, 11) },
        splitLine: { lineStyle: { color: t.grid, type: 'dashed' } },
        scale: true,
      },
    ],
    yAxis: [
      {
        type: 'value',
        name: humanizeKey(y),
        nameLocation: 'middle',
        nameRotate: 90,
        nameGap: px(t, 40),
        nameTextStyle: { color: t.sub, fontSize: px(t, 12) },
        axisLabel: { color: t.sub, fontSize: px(t, 11) },
        splitLine: { lineStyle: { color: t.grid, type: 'dashed' } },
        scale: true,
      },
    ],
    // Size legend: what the smallest and largest bubbles mean (rubric: every encoding has a key)
    graphic: [
      {
        type: 'text',
        right: px(t, 24),
        top: 0,
        style: {
          text: `Bubble size = ${humanizeKey(size)} (${fmtValue(minSize, plan.unit, { compact: true })} – ${fmtValue(maxSize, plan.unit, { compact: true })})`,
          fill: t.sub,
          fontSize: px(t, 12),
        },
      },
    ] as any,
    tooltip: {
      ...tooltipBase(t),
      trigger: 'item',
      formatter: (p: any) => {
        const r = data[p.dataIndex];
        return tooltipCard(t, humanizeValue(r[label]), [
          [humanizeKey(x), String(fmtValue(toNumber(r[x]) ?? 0, parseUnit(undefined, x)))],
          [humanizeKey(y), String(fmtValue(toNumber(r[y]) ?? 0, parseUnit(undefined, y)))],
          [humanizeKey(size), String(fmtValue(toNumber(r[size]) ?? 0, parseUnit(spec?.unit, size)))],
        ]);
      },
    },
    series: [
      {
        id: 'main',
        type: 'scatter',
        data: data.map((r) => [toNumber(r[x]) ?? 0, toNumber(r[y]) ?? 0, toNumber(r[size]) ?? 0]),
        symbolSize: (v: number[]) => bubbleSize(v[2], maxSize),
        itemStyle: { color: alpha(t.accent, 0.55), borderColor: t.accent, borderWidth: 1 },
        label: {
          show: showLabels,
          position: 'top',
          color: t.text,
          fontSize: px(t, 11),
          formatter: (p: any) => humanizeValue(data[p.dataIndex][label]),
        },
        labelLayout: { hideOverlap: true },
        emphasis: { focus: 'self' },
      },
    ] as any,
  };
}

// ------------------------------------------------------------------------------------------------ sunburst

export interface SunNode {
  name: string;
  value: number;
  children?: SunNode[];
}

/** Rows → tree using the text columns in order as levels; parents carry Σ children (conservation). */
export function sunburstTree(data: Record<string, any>[], levels: string[], valueKey: string): SunNode[] {
  const root: SunNode = { name: 'root', value: 0, children: [] };
  for (const r of data) {
    const v = toNumber(r[valueKey]) ?? 0;
    let node = root;
    node.value += v;
    for (const lvl of levels) {
      const name = humanizeValue(r[lvl]) || '—';
      node.children = node.children || [];
      let child = node.children.find((c) => c.name === name);
      if (!child) {
        child = { name, value: 0 };
        node.children.push(child);
      }
      child.value += v;
      node = child;
    }
  }
  const strip = (n: SunNode): SunNode => (n.children?.length ? { ...n, children: n.children.map(strip) } : { name: n.name, value: n.value });
  return (root.children || []).map(strip);
}

/** Explicit colours per node (top level from the palette, descendants as lighter tints) with a readable label
 * colour computed for each fill (dark ink on light fills, white on dark) — rubric: labels legible in both themes. */
export function colourSunburst(nodes: SunNode[], t: ChartTokens, parent?: string, depth = 0): any[] {
  return nodes.map((n, i) => {
    const base = parent ?? t.categorical[i % t.categorical.length];
    const color = depth === 0 ? base : mixHex(base, t.surface, Math.max(0.45, 0.8 - 0.15 * depth));
    return {
      name: n.name,
      value: n.value,
      itemStyle: { color },
      label: { color: labelOn(color) },
      ...(n.children ? { children: colourSunburst(n.children, t, base, depth + 1) } : {}),
    };
  });
}

export function sunburstOption(plan: ChartPlan, t: ChartTokens, data: Record<string, any>[], levels: string[]): Opt {
  const tree = sunburstTree(data, levels, plan.valueKey);
  const total = tree.reduce((s, n) => s + n.value, 0);
  return {
    ...shell(t),
    tooltip: {
      ...tooltipBase(t),
      trigger: 'item',
      formatter: (p: any) =>
        tooltipCard(t, (p.treePathInfo || []).slice(1).map((x: any) => x.name).join(' › ') || p.name, [
          [humanizeKey(plan.valueKey), String(fmtValue(p.value, plan.unit))],
          ['Share of total', `${((100 * p.value) / Math.max(1e-9, total)).toFixed(1)}%`],
        ]),
    },
    series: [
      {
        id: 'main',
        type: 'sunburst',
        data: colourSunburst(tree, t),
        radius: ['12%', '92%'],
        sort: undefined, // keep data order (ranked upstream)
        nodeClick: 'rootToNode',
        itemStyle: { borderColor: t.surface, borderWidth: 2 },
        label: { fontSize: px(t, 12), minAngle: 8, overflow: 'truncate' },
        levels: [{}, { label: { rotate: 'tangential' } }, { label: { rotate: 'radial' } }, { label: { show: false } }],
      },
    ] as any,
  };
}

// ------------------------------------------------------------------------------------------------ sankey

export interface SankeyLink {
  source: string;
  target: string;
  value: number;
}

export function sankeyLinks(data: Record<string, any>[], valueKey: string): SankeyLink[] {
  const k = (r: Record<string, any>, name: string) => r[Object.keys(r).find((x) => x.toLowerCase() === name) || name];
  return data
    .map((r) => ({ source: humanizeValue(k(r, 'source')), target: humanizeValue(k(r, 'target')), value: toNumber(r[valueKey]) ?? 0 }))
    .filter((l) => l.source && l.target && l.value > 0 && l.source !== l.target);
}

/** Per node: total in, total out. Pass-through nodes (both > 0) must balance; returns the worst imbalance. */
export function sankeyBalance(links: SankeyLink[]): { nodes: Record<string, { in: number; out: number }>; maxPassThroughGap: number } {
  const nodes: Record<string, { in: number; out: number }> = {};
  for (const l of links) {
    nodes[l.source] = nodes[l.source] || { in: 0, out: 0 };
    nodes[l.target] = nodes[l.target] || { in: 0, out: 0 };
    nodes[l.source].out += l.value;
    nodes[l.target].in += l.value;
  }
  let gap = 0;
  for (const n of Object.values(nodes)) if (n.in > 0 && n.out > 0) gap = Math.max(gap, Math.abs(n.in - n.out));
  return { nodes, maxPassThroughGap: gap };
}

export function sankeyOption(plan: ChartPlan, t: ChartTokens, data: Record<string, any>[]): Opt {
  const links = sankeyLinks(data, plan.valueKey);
  const { nodes } = sankeyBalance(links);
  return {
    ...shell(t),
    tooltip: {
      ...tooltipBase(t),
      trigger: 'item',
      formatter: (p: any) =>
        p.dataType === 'edge'
          ? tooltipCard(t, `${p.data.source} → ${p.data.target}`, [[humanizeKey(plan.valueKey), String(fmtValue(p.data.value, plan.unit))]])
          : tooltipCard(t, p.name, [
              ['In', String(fmtValue(nodes[p.name]?.in || 0, plan.unit))],
              ['Out', String(fmtValue(nodes[p.name]?.out || 0, plan.unit))],
            ]),
    },
    series: [
      {
        id: 'main',
        type: 'sankey',
        left: px(t, 8),
        right: px(t, 120),
        top: px(t, 16),
        bottom: px(t, 16),
        nodeGap: px(t, 12),
        draggable: false,
        emphasis: { focus: 'adjacency' },
        data: Object.keys(nodes).map((name) => ({ name })),
        links,
        lineStyle: { color: 'gradient', opacity: 0.35, curveness: 0.5 },
        label: { color: t.text, fontSize: px(t, 12), formatter: (p: any) => `${p.name}  ${fmtValue(Math.max(nodes[p.name]?.in || 0, nodes[p.name]?.out || 0), plan.unit, { compact: true })}` },
        itemStyle: { borderColor: t.surface, borderWidth: 1 },
        color: t.categorical,
      },
    ] as any,
  };
}
