'use client';

import React from 'react';
import { KpiTile } from '@/contracts/answerContract';
import { formatIndianNumber } from '@/utils/numberFormat';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface KpiRendererProps {
  kpis: KpiTile[];
  isDark?: boolean;
}

export const KpiRenderer: React.FC<KpiRendererProps> = ({ kpis, isDark = false }) => {
  if (!kpis || kpis.length === 0) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 w-full">
      {kpis.map((kpi, idx) => {
        const isNum = typeof kpi.value === 'number';
        const formattedVal = isNum ? formatIndianNumber(kpi.value) : kpi.value;
        const delta = kpi.delta || '';
        const isPositive = delta.startsWith('+') || delta.toLowerCase().includes('profit') || delta.toLowerCase().includes('excellent') || delta.toLowerCase().includes('norm met');
        const isNegative = delta.startsWith('-') || delta.toLowerCase().includes('loss') || delta.toLowerCase().includes('negative') || delta.toLowerCase().includes('drop');

        return (
          <div
            key={idx}
            className={`p-5 rounded-2xl border transition-all duration-300 relative overflow-hidden group ${
              isDark
                ? 'bg-zinc-900/90 border-zinc-800 hover:border-zinc-700'
                : 'bg-white border-zinc-200/80 hover:border-blue-200 shadow-sm'
            }`}
          >
            {/* Top Label */}
            <div className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-2">
              {kpi.label}
            </div>

            {/* Emphasized Big Numeral */}
            <div className="flex items-baseline gap-2 mb-2">
              <span data-testid="kpi-value" className="text-4xl md:text-5xl font-display font-bold tracking-tight text-zinc-900 dark:text-zinc-50 group-hover:text-accent transition-colors">
                {formattedVal}
              </span>
              {kpi.unit && (
                <span className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
                  {kpi.unit}
                </span>
              )}
            </div>

            {/* Delta / Status Pill */}
            {delta && (
              <div className="flex items-center gap-1.5 pt-1">
                <span
                  className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    isPositive
                      ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300'
                      : isNegative
                      ? 'bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300'
                      : 'bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300'
                  }`}
                >
                  {isPositive && <TrendingUp className="w-3 h-3" />}
                  {isNegative && <TrendingDown className="w-3 h-3" />}
                  {!isPositive && !isNegative && <Minus className="w-3 h-3" />}
                  <span>{delta}</span>
                </span>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
