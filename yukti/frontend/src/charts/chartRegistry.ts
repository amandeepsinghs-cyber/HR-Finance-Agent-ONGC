/**
 * P4.7 (SPEC-10 §4.4): maps a mounted chart's host element to its live ECharts instance, so an answer card can
 * export exactly what is on screen (PNG/SVG) without threading refs through every renderer.
 */
import type { ECharts } from 'echarts';

const registry = new WeakMap<Element, ECharts>();

export function registerChart(el: Element, chart: ECharts): void {
  registry.set(el, chart);
}

export function unregisterChart(el: Element): void {
  registry.delete(el);
}

/** All live chart instances inside `root` (document order), e.g. one per small-multiple panel. */
export function chartsWithin(root: Element | null | undefined): ECharts[] {
  if (!root) return [];
  const out: ECharts[] = [];
  root.querySelectorAll('[data-echart]').forEach((el) => {
    const c = registry.get(el);
    if (c && !c.isDisposed()) out.push(c);
  });
  return out;
}
