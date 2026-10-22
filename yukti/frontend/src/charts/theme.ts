/**
 * Chart theme tokens (AlphaEvolve deck + ONGC maroon), light & dark.
 */
import * as echarts from 'echarts';

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
  const scale = rootScale();
  return dark
    ? {
        dark,
        text: '#E8EAED',
        sub: '#A8ADB4',
        faint: '#6B7078',
        grid: 'rgba(255,255,255,0.07)',
        axis: 'rgba(255,255,255,0.18)',
        surface: '#17181B',
        tooltipBg: 'rgba(32,33,36,0.96)',
        tooltipBorder: 'rgba(255,255,255,0.10)',
        accent: '#4C97FF',
        accentSoft: '#8EC5FF',
        accentDeep: '#2F6FE0',
        accentPale: 'rgba(118,187,255,0.22)',
        maroon: '#E0525C',
        maroonSoft: '#B83A43',
        positive: '#5BB974',
        band: ['rgba(255,255,255,0.05)', 'rgba(255,255,255,0.09)', 'rgba(255,255,255,0.14)'],
        categorical: ['#4C97FF', '#8EC5FF', '#2F6FE0', '#C6E1FF', '#9AA0A6', '#5F84C9', '#E0525C', '#6B7078', '#B5D7FF'],
        font: "'Google Sans Text', 'Google Sans', Inter, 'Noto Sans Devanagari', system-ui, sans-serif",
        scale,
      }
    : {
        dark,
        text: '#1F1F1F',
        sub: '#5F6368',
        faint: '#9AA0A6',
        grid: 'rgba(31,31,31,0.07)',
        axis: '#DADCE0',
        surface: '#FFFFFF',
        tooltipBg: 'rgba(255,255,255,0.98)',
        tooltipBorder: '#E3E6EA',
        accent: '#3186FF',
        accentSoft: '#76BBFF',
        accentDeep: '#1A56DB',
        accentPale: '#DCEBFF',
        maroon: '#8E000C',
        maroonSoft: '#C2414B',
        positive: '#1E8E3E',
        band: ['#F1F3F4', '#E8EAED', '#DADCE0'],
        categorical: ['#3186FF', '#76BBFF', '#1A56DB', '#B9DAFF', '#80868B', '#5C8FE6', '#8E000C', '#BDC1C6', '#0B3D91'],
        font: "'Google Sans Text', 'Google Sans', Inter, 'Noto Sans Devanagari', system-ui, sans-serif",
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
  animationDuration: 700,
  animationDurationUpdate: 650,
  animationEasing: 'cubicOut' as const,
  animationEasingUpdate: 'cubicInOut' as const,
};
