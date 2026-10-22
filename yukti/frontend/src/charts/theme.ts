/**
 * Chart theme tokens (AlphaEvolve deck + ONGC maroon), light & dark.
 * All colours are read from the single design-token source: src/design/tokens.json (U1.1).
 */
import * as echarts from 'echarts';
import TOKENS from '@/design/tokens.json';

export interface ChartTokens {
  dark: boolean;
  text: string;
  sub: string;
  faint: string;
  grid: string;
  axis: string;
  surface: string;
  tooltipBg: string;
  tooltipBorder: string;
  accent: string;
  accentSoft: string;
  accentDeep: string;
  accentPale: string;
  maroon: string;
  maroonSoft: string;
  positive: string;
  band: [string, string, string];
  categorical: string[];
  /** ramp ordered LOW→HIGH magnitude (light: light→dark tints drawn with separating borders; dark: dim→bright, each step ≥3:1 on the card) */
  sequential: string[];
  /** marker outline on maps/scatter */
  markerBorder: string;
  shadowAccent: string;
  shadowMaroon: string;
  /** halo/stroke colour drawn behind on-chart labels (matches the canvas) */
  labelHalo: string;
  mapArea: string;
  mapBorder: string;
  /** text colour on top of accent/maroon fills */
  onAccent: string;
  font: string;
  /** font scale relative to 16px root (big-screen legibility) */
  scale: number;
}

export function rootScale(): number {
  if (typeof window === 'undefined') return 1;
  const fs = parseFloat(getComputedStyle(document.documentElement).fontSize || '16');
  return Math.max(0.9, Math.min(1.6, fs / 16));
}

export function getTokens(dark: boolean): ChartTokens {
  // Values come from the single token source (src/design/tokens.json, U1.1). Read directly from
  // JSON (not computed CSS) so charts are correct even before the <html class="dark"> toggle lands.
  const scale = rootScale();
  const th = dark ? TOKENS.themes.dark : TOKENS.themes.light;
  const pal = dark ? TOKENS.chartPalettes.dark : TOKENS.chartPalettes.light;
  return {
    dark,
    text: th['chart-text'],
    sub: th['chart-sub'],
    faint: th['chart-faint'],
    grid: th['chart-grid'],
    axis: th['chart-axis'],
    surface: th.card,
    tooltipBg: th['chart-tooltip-bg'],
    tooltipBorder: th['chart-tooltip-border'],
    accent: th.accent,
    accentSoft: th['accent-soft'],
    accentDeep: th['accent-deep'],
    accentPale: th['accent-pale'],
    maroon: pal.diverging.negative,
    maroonSoft: pal.diverging.negativeSoft,
    positive: th['positive-fill'],
    band: [th['chart-band-1'], th['chart-band-2'], th['chart-band-3']],
    categorical: pal.categorical,
    sequential: pal.sequential,
    labelHalo: th['chart-label-halo'],
    mapArea: th['chart-map-area'],
    mapBorder: th['chart-map-border'],
    markerBorder: th['chart-marker-border'],
    shadowAccent: th['chart-shadow-accent'],
    shadowMaroon: th['chart-shadow-maroon'],
    onAccent: th['on-accent'],
    font: TOKENS.typography['font-sans'],
    scale,
  };
}

export const px = (t: ChartTokens, base: number) => Math.round(base * t.scale);

export function hGradient(from: string, to: string) {
  return new echarts.graphic.LinearGradient(0, 0, 1, 0, [
    { offset: 0, color: from },
    { offset: 1, color: to },
  ]);
}

export function vGradient(top: string, bottom: string) {
  return new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: top },
    { offset: 1, color: bottom },
  ]);
}

export function tooltipBase(t: ChartTokens): echarts.TooltipComponentOption {
  return {
    backgroundColor: t.tooltipBg,
    borderColor: t.tooltipBorder,
    borderWidth: 1,
    padding: [px(t, 10), px(t, 14)],
    extraCssText: `border-radius:${px(t, 12)}px;box-shadow:0 12px 32px -8px rgba(0,0,0,${t.dark ? 0.6 : 0.18});backdrop-filter:blur(8px);`,
    textStyle: { color: t.text, fontSize: px(t, 13), fontFamily: t.font },
    confine: true,
  };
}

export function tooltipCard(t: ChartTokens, title: string, rows: [string, string, string?][]): string {
  const r = rows
    .map(
      ([k, v, color]) =>
        `<div style="display:flex;justify-content:space-between;gap:${px(t, 18)}px;margin-top:${px(t, 4)}px;font-size:${px(t, 13)}px;">` +
        `<span style="color:${t.sub};display:flex;align-items:center;gap:6px;">${color ? `<span style="width:8px;height:8px;border-radius:50%;background:${color};display:inline-block"></span>` : ''}${k}</span>` +
        `<span style="font-weight:600;color:${t.text};font-variant-numeric:tabular-nums;">${v}</span></div>`
    )
    .join('');
  return `<div style="min-width:${px(t, 160)}px"><div style="font-weight:600;font-size:${px(t, 14)}px;color:${t.text};margin-bottom:${px(t, 2)}px;">${title}</div>${r}</div>`;
}

export const ANIM = {
  animationDuration: TOKENS.chartMotion.enterMs,
  animationDurationUpdate: TOKENS.chartMotion.updateMs,
  animationEasing: TOKENS.chartMotion.easing as 'cubicOut',
  animationEasingUpdate: TOKENS.chartMotion.easingUpdate as 'cubicInOut',
};

/** Chart motion honouring prefers-reduced-motion (rubric C7): no animation at all when the user asks for it. */
export function anim(): typeof ANIM | { animation: false } {
  if (typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return { animation: false };
  return ANIM;
}

/** `#RRGGBB` (or an existing rgb/rgba string) → rgba with the given alpha. */
export function alpha(color: string, a: number): string {
  if (color.startsWith('#') && color.length >= 7) {
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(color.slice(i, i + 2), 16));
    return `rgba(${r}, ${g}, ${b}, ${a})`;
  }
  const m = color.match(/rgba?\(([^)]+)\)/);
  if (m) {
    const [r, g, b] = m[1].split(',').map((v) => v.trim());
    return `rgba(${r}, ${g}, ${b}, ${a})`;
  }
  return color;
}

/** Readable label colour for text drawn ON a fill: dark ink on light fills, white on dark fills (WCAG luminance). */
export function labelOn(fill: string): string {
  if (!fill.startsWith('#') || fill.length < 7) return TOKENS.themes.light['on-accent'];
  const lin = (c: number) => {
    const v = c / 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  };
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(fill.slice(i, i + 2), 16));
  const L = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  // contrast vs white = 1.05/(L+0.05); vs ink(#1F1F1F, L≈0.0137) = (L+0.05)/0.0637
  return 1.05 / (L + 0.05) >= (L + 0.05) / 0.0637 ? TOKENS.themes.light['on-accent'] : TOKENS.themes.light.ink;
}
