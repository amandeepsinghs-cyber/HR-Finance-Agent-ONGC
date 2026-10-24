'use client';

/**
 * P4.5 B1: typed finance visuals — `sensitivity_grid` and `tornado` (SPEC-09 §5). Rendered with ECharts so the
 * card's PNG/SVG export (P4.7) works on them like any chart.
 */
import React, { useMemo } from 'react';
import type { SensitivityGridSpec, TornadoSpec } from '@/contracts/answerContract';
import { EChart } from '@/charts/EChart';
import { getTokens } from '@/charts/theme';
import { sensitivityGridOption, tornadoOption, fmtOutput } from '@/charts/financeOptions';

function Caption({ children }: { children: React.ReactNode }) {
  return <p className="shrink-0 mt-2 text-caption text-[var(--ink-3)]">{children}</p>;
}

export const SensitivityGrid: React.FC<{ spec: SensitivityGridSpec; isDark?: boolean }> = ({ spec, isDark = false }) => {
  const t = useMemo(() => getTokens(isDark), [isDark]);
  const option = useMemo(() => sensitivityGridOption(spec, t), [spec, t]);
  const baseVal = spec.cells?.[spec.base.row_idx]?.[spec.base.col_idx];
  const hasNm = spec.cells.some((r) => r.some((v) => v === null));
  return (
    <div className="w-full h-full flex flex-col" data-testid="sensitivity-grid" data-chart-form="sensitivity_grid">
      <div className="flex-1 min-h-0">
        <EChart option={option} testId="chart-sensitivity_grid" />
      </div>
      <Caption>
        {spec.output.name} ({spec.output.unit === 'INR' ? '₹' : spec.output.unit}). Outlined cell = base case
        {typeof baseVal === 'number' ? ` (${fmtOutput(baseVal, spec.output.unit)})` : ''}.
        {hasNm ? ' n/m = not meaningful (WACC − g < 1 pp).' : ''}
        {spec.source ? ` Source: ${spec.source}.` : ''}
      </Caption>
    </div>
  );
};

export const Tornado: React.FC<{ spec: TornadoSpec; isDark?: boolean }> = ({ spec, isDark = false }) => {
  const t = useMemo(() => getTokens(isDark), [isDark]);
  const option = useMemo(() => tornadoOption(spec, t), [spec, t]);
  return (
    <div className="w-full h-full flex flex-col" data-testid="tornado" data-chart-form="tornado">
      <div className="flex-1 min-h-0">
        <EChart option={option} testId="chart-tornado" />
      </div>
      <Caption>
        {spec.output.name} swing per driver around the base case ({fmtOutput(spec.output.base, spec.output.unit)}), largest first.
        {spec.source ? ` Source: ${spec.source}.` : ''}
      </Caption>
    </div>
  );
};
