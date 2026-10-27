'use client';

/**
 * OilOverlayBar (26-Oct): opt-in Brent / WTI overlay controls for fiscal-year charts, plus a LIVE badge with the
 * current price and a 12-month daily sparkline from Yahoo Finance (proof of the live integration).
 */
import React, { useMemo } from 'react';
import { Fuel, X } from 'lucide-react';
import { Chip } from './ui/primitives';
import { OilBenchmark, OilPricePayload } from '@/charts/oilOverlay';

interface Props {
  active: OilBenchmark | null;
  data: OilPricePayload | null;
  loading: boolean;
  error: string | null;
  correlation: { r: number; n: number } | null;
  seriesLabel: string;
  onSet: (v: OilBenchmark | 'off') => void;
}

function ago(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 90) return 'just now';
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return new Date(iso).toLocaleDateString();
}

const Sparkline: React.FC<{ values: number[] }> = ({ values }) => {
  const d = useMemo(() => {
    if (values.length < 2) return '';
    const w = 132, h = 30;
    const lo = Math.min(...values), hi = Math.max(...values);
    const span = hi - lo || 1;
    return values
      .map((v, i) => `${i ? 'L' : 'M'}${((i / (values.length - 1)) * w).toFixed(1)},${(h - ((v - lo) / span) * (h - 4) - 2).toFixed(1)}`)
      .join(' ');
  }, [values]);
  if (!d) return null;
  return (
    <svg width={132} height={30} viewBox="0 0 132 30" aria-hidden className="shrink-0 text-[var(--accent)]">
      <path d={d} fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinejoin="round" />
    </svg>
  );
};

export const OilOverlayBar: React.FC<Props> = ({ active, data, loading, error, correlation, seriesLabel, onSet }) => {
  if (!active) {
    return (
      <div className="flex flex-wrap items-center gap-2" data-testid="oil-overlay-bar">
        <Chip size="sm" icon={<Fuel className="w-3.5 h-3.5" />} onClick={() => onSet('brent')} data-testid="oil-overlay-brent">
          + Brent oil price
        </Chip>
        <button
          type="button"
          onClick={() => onSet('wti')}
          className="text-caption text-[var(--ink-3)] hover:text-[var(--ink-2)] underline-offset-2 hover:underline"
          data-testid="oil-overlay-wti"
        >
          or WTI
        </button>
        <Chip size="sm" onClick={() => onSet('inr')} data-testid="oil-overlay-inr" title="Rupee per US dollar (live)">
          + ₹/$ rate
        </Chip>
      </div>
    );
  }
  const live = data?.live;
  const up = (live?.change_pct ?? 0) >= 0;
  const closes = (data?.daily || []).map((p) => p.close);
  const strength = correlation ? (Math.abs(correlation.r) >= 0.7 ? 'closely' : Math.abs(correlation.r) >= 0.4 ? 'partly' : 'loosely') : '';
  return (
    <div className="flex flex-col gap-1.5" data-testid="oil-overlay-bar" data-oil={active}>
      <div className="flex flex-wrap items-center gap-2">
        <Chip size="sm" selected={active === 'brent'} onClick={() => onSet('brent')} data-testid="oil-overlay-brent">
          Brent
        </Chip>
        <Chip size="sm" selected={active === 'wti'} onClick={() => onSet('wti')} data-testid="oil-overlay-wti">
          WTI
        </Chip>
        <Chip size="sm" selected={active === 'inr'} onClick={() => onSet('inr')} data-testid="oil-overlay-inr">
          ₹/$
        </Chip>
        <button
          type="button"
          onClick={() => onSet('off')}
          aria-label="Remove oil price"
          title="Remove oil price"
          className="inline-flex items-center gap-1 text-caption text-[var(--ink-3)] hover:text-[var(--ink-2)]"
          data-testid="oil-overlay-off"
        >
          <X className="w-3.5 h-3.5" /> Remove
        </button>
        <span className="flex-1" />
        {loading && <span className="text-caption text-[var(--ink-3)]">Fetching live {active === 'wti' ? 'WTI' : active === 'inr' ? 'rupee' : 'Brent'} prices…</span>}
        {error && !loading && <span className="text-caption text-[var(--maroon)]">{error}</span>}
        {live && !loading && (
          <span className="inline-flex items-center gap-2.5 rounded-pill border border-[var(--hairline)] bg-[var(--surface)] px-3 py-1" data-testid="oil-live-badge">
            <span className="inline-flex items-center gap-1.5 text-caption font-semibold tracking-wide">
              <span className={`w-2 h-2 rounded-full ${data?.stale ? 'bg-[var(--ink-3)]' : 'bg-[var(--positive)] animate-pulse'}`} aria-hidden />
              {data?.stale ? 'SAVED COPY' : 'LIVE'}
            </span>
            <span className="text-label font-semibold text-[var(--ink)]">
              {data?.short} {data?.benchmark === 'inr' ? `₹${live.price.toFixed(2)}` : `$${live.price.toFixed(2)}`}
            </span>
            {live.change_pct !== null && (
              <span className={`text-caption font-semibold ${up ? 'text-[var(--positive)]' : 'text-[var(--maroon)]'}`}>
                {up ? '▲' : '▼'} {Math.abs(live.change_pct).toFixed(1)}%
              </span>
            )}
            <Sparkline values={closes} />
            <span className="text-caption text-[var(--ink-3)]" title={data?.source}>
              Yahoo Finance · {ago(data?.fetched_at || live.as_of)}
            </span>
          </span>
        )}
      </div>
      {correlation && !loading && (
        <p className="text-caption text-[var(--ink-2)]" data-testid="oil-correlation">
          {seriesLabel} moved {strength} with {data?.benchmark === 'inr' ? 'the rupee per dollar rate' : data?.short} over {correlation.n} fiscal years (correlation{' '}
          {correlation.r.toFixed(2)}). Dashed line: {data?.benchmark === 'inr' ? '₹ per $' : data?.short} yearly average; the open circle is this fiscal year to date, from live
          prices.
        </p>
      )}
    </div>
  );
};
