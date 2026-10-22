'use client';

import React from 'react';
import { KpiTile } from '@/contracts/answerContract';
import { fmtNum, cleanText } from '@/charts/format';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';

interface KpiRendererProps {
  kpis: KpiTile[];
  isDark?: boolean;
  hero?: boolean;
  /** Optional mini-trend / distribution for the first tile. */
  spark?: { values: number[]; kind: 'line' | 'bars'; highlight?: number };
}

export type Tone = 'good' | 'bad' | 'neutral';
export type Direction = 'up' | 'down' | 'neutral';
export type Polarity = 'higher_is_better' | 'lower_is_better';

export function polarityOf(kpi: KpiTile): Polarity {
  const label = (kpi.label || '').toLowerCase();
  // Profit-type metrics are higher-is-better even when the label mentions loss (e.g. "Net profit/(loss)").
  if (/profit|p&l|\bpbt\b|\bpat\b|ebitda|revenue|margin/i.test(label)) return 'higher_is_better';
  if (/vacanc|attrition|lifting cost|cost per|opex|overtime|ltifr|incident|grievance|receivable|overdue|\bloss(es)?\b|debt|absent|separation|backlog|downtime|water cut/i.test(label)) {
    return 'lower_is_better';
  }
  return 'higher_is_better';
}

export function directionOf(kpi: KpiTile): Direction {
  const d = (kpi.delta || '').toLowerCase();
  if (/^\s*[-−]/.test(kpi.delta || '') || /loss|negative|drop|decline|below|overdue|steepest/.test(d)) return 'down';
  if (/^\s*\+/.test(kpi.delta || '') || /profit|excellent|very good|met|growth|above|healthy/.test(d)) return 'up';
  if (typeof kpi.value === 'number' && kpi.value < 0) return 'down';
  return 'neutral';
}

// Words that already carry meaning are mapped straight to good/bad (never flipped by polarity).
const BAD_WORDS = /\b(loss(es)?|loss-making|overdue|breach(ed)?|below target|missed|negative|deficit|critical|poor)\b/i;
const GOOD_WORDS = /\b(excellent|very good|healthy|met|achieved|above target|on track|surplus)\b/i;

export function toneOf(kpi: KpiTile): Tone {
  const d = kpi.delta || '';
  if (/\bnot\s+(met|on track|achieved|healthy)\b/i.test(d)) return 'bad'; // negation beats GOOD_WORDS
  if (BAD_WORDS.test(d)) return 'bad';
  if (GOOD_WORDS.test(d)) return 'good';
  // Otherwise: sign/direction words decide direction, and metric polarity decides meaning.
  const dir = directionOf(kpi);
  if (dir === 'neutral') return 'neutral';
  const pol = polarityOf(kpi);
  if ((dir === 'up' && pol === 'higher_is_better') || (dir === 'down' && pol === 'lower_is_better')) {
    return 'good';
  }
  return 'bad';
}

function formatKpiValue(kpi: KpiTile): { prefix: string; num: string; suffix: string } {
  const unit = (kpi.unit || '').trim();
  if (typeof kpi.value !== 'number') return { prefix: '', num: String(kpi.value), suffix: unit };
  const isCurrency = /₹|cr\b|crore/i.test(unit);
  const v = kpi.value;
  const neg = v < 0 ? '−' : '';
  const num = fmtNum(Math.abs(v));
  if (isCurrency) {
    const rest = unit.replace(/₹\s*/g, '').trim();
    return { prefix: `${neg}₹`, num, suffix: rest };
  }
  if (unit === '%' || unit.startsWith('%')) return { prefix: neg, num, suffix: unit };
  return { prefix: neg, num, suffix: unit };
}

const Spark: React.FC<{ spark: NonNullable<KpiRendererProps['spark']> }> = ({ spark }) => {
  const vals = spark.values.slice(0, 24);
  if (vals.length < 2) return null;
  const w = 120;
  const h = 34;
  const max = Math.max(...vals);
  const min = Math.min(0, ...vals);
  const y = (v: number) => h - ((v - min) / (max - min || 1)) * (h - 4) - 2;
  if (spark.kind === 'bars') {
    const bw = w / vals.length;
    return (
      <svg viewBox={`0 0 ${w} ${h}`} className="w-[5.5rem] h-[1.6rem] shrink-0 -mt-0.5" aria-hidden>
        {vals.map((v, i) => (
          <rect
            key={i}
            x={i * bw + bw * 0.15}
            y={y(v)}
            width={bw * 0.7}
            height={Math.max(1.5, h - 2 - y(v))}
            rx={1.5}
            fill={i === spark.highlight ? 'var(--accent-deep)' : 'var(--accent-soft)'}
            opacity={i === spark.highlight ? 1 : 0.75}
          />
        ))}
      </svg>
    );
  }
  const pts = vals.map((v, i) => `${(i / (vals.length - 1)) * w},${y(v)}`).join(' ');
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-[5.5rem] h-[1.6rem] shrink-0 -mt-0.5" aria-hidden>
      <defs>
        <linearGradient id="kspark" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="var(--accent)" stopOpacity="0.35" />
          <stop offset="1" stopColor="var(--accent)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={`0,${h} ${pts} ${w},${h}`} fill="url(#kspark)" />
      <polyline points={pts} fill="none" stroke="var(--accent)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
};

export const KpiRenderer: React.FC<KpiRendererProps> = ({ kpis, hero = false, spark }) => {
  if (!kpis || kpis.length === 0) return null;
  const tiles = kpis.slice(0, 4);
  return (
    <div
      className="grid gap-[1rem] w-full"
      style={{ gridTemplateColumns: `repeat(auto-fit, minmax(min(100%, ${hero ? '16rem' : '13.5rem'}), 1fr))` }}
    >
      {tiles.map((kpi, idx) => {
        const direction = directionOf(kpi);
        const tone = toneOf(kpi);
        const { prefix, num, suffix } = formatKpiValue(kpi);
        const delta = cleanText(kpi.delta || '');
        const showSpark = idx === 0 && spark;
        return (
          <div key={idx} className="kpi-tile group" data-tone={tone} data-primary={idx === 0 ? 'true' : undefined}>
            <div className="flex items-start justify-between gap-3">
              <div className="text-[0.78rem] font-medium tracking-[0.01em] text-[var(--ink-2)] truncate" title={kpi.label}>
                {cleanText(kpi.label)}
              </div>
              {showSpark && <Spark spark={spark!} />}
            </div>
            <div className="flex items-end justify-between gap-3 mt-[0.35rem]">
              <div className="flex items-baseline gap-[0.4rem] min-w-0">
                <span
                  data-testid="kpi-value"
                  className={`font-display font-semibold tabular-nums tracking-[-0.025em] leading-none ${
                    hero ? 'text-[3.4rem]' : 'text-[2.6rem]'
                  } ${typeof kpi.value === 'number' && kpi.value < 0 ? 'text-[var(--maroon)]' : 'text-[var(--ink)]'}`}
                >
                  {prefix && <span className="text-[0.62em] align-[0.28em] mr-[0.04em] font-medium">{prefix}</span>}
                  {num}
                </span>
                {suffix && <span className="text-[0.95rem] font-medium text-[var(--ink-2)] truncate">{suffix}</span>}
              </div>
            </div>
            {delta && (
              <div className="mt-[0.7rem]">
                <span className="delta-chip" data-tone={tone}>
                  {direction === 'up' && <ArrowUpRight className="w-[0.9em] h-[0.9em]" />}
                  {direction === 'down' && <ArrowDownRight className="w-[0.9em] h-[0.9em]" />}
                  <span className="truncate">{delta}</span>
                </span>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
