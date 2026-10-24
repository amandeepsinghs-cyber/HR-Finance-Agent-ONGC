'use client';

/**
 * P4.5 (SPEC-02 §9.1, SPEC-09 §5, FEAT-026): DCF valuation composite card (`visual.type = 'dcf_model'`).
 * Six tabs reuse existing renderers:
 *   1. Summary — KPI tiles (verdict text strictly from contract) + key valuation summary rows
 *   2. FCFF — explicit forecast table rendered via StatementTable
 *   3. WACC — cost-of-capital build-up rendered via StatementTable
 *   4. Bridge — Enterprise-to-Equity waterfall rendered via ChartRenderer (kind='waterfall')
 *   5. Sensitivity — 9×9 WACC × g grid rendered via SensitivityGrid
 *   6. Tornado — one-way driver swings rendered via Tornado
 */
import React, { useMemo, useState } from 'react';
import type { ChartSpec, DcfModelSpec, KpiTile, StatementRow, StatementSpec } from '@/contracts/answerContract';
import { KpiRenderer } from './KpiRenderer';
import { StatementTable } from './StatementTable';
import { ChartRenderer } from './ChartRenderer';
import { SensitivityGrid, Tornado } from './FinanceVisuals';

export type DcfTabId = 'summary' | 'fcff' | 'wacc' | 'bridge' | 'sensitivity' | 'tornado';

const TABS: { id: DcfTabId; label: string }[] = [
  { id: 'summary', label: 'Summary' },
  { id: 'fcff', label: 'FCFF' },
  { id: 'wacc', label: 'WACC' },
  { id: 'bridge', label: 'Bridge' },
  { id: 'sensitivity', label: 'Sensitivity' },
  { id: 'tornado', label: 'Tornado' },
];

export function buildFcffStatement(spec: DcfModelSpec): StatementSpec {
  if (spec.fcff_statement) return spec.fcff_statement;
  const years = spec.forecast.years || [];
  const { revenue, ebit, fcff, discount_factor, pv_fcff } = spec.forecast.lines;
  const byYear = (arr?: number[]) => {
    const out: Record<string, number | null> = {};
    years.forEach((y, i) => {
      out[y] = typeof arr?.[i] === 'number' ? Number(arr[i].toFixed(2)) : null;
    });
    return out;
  };
  const rows: StatementRow[] = [];
  if (revenue?.length) {
    rows.push({ line_code: 'DCF.REV', label: 'Revenue from operations', level: 0, kind: 'line', values: byYear(revenue) });
  }
  if (ebit?.length) {
    rows.push({ line_code: 'DCF.EBIT', label: 'Operating profit (EBIT)', level: 0, kind: 'subtotal', values: byYear(ebit) });
  }
  rows.push(
    { line_code: 'DCF.FCFF', label: 'Free cash flow to firm (FCFF)', level: 0, kind: 'subtotal', values: byYear(fcff) },
    { line_code: 'DCF.DF', label: 'Discount factor (end-year)', level: 1, kind: 'line', values: byYear(discount_factor) },
    { line_code: 'DCF.PV_FCFF', label: 'Present value of FCFF', level: 0, kind: 'total', values: byYear(pv_fcff) },
  );
  return {
    statement: 'cash_flow',
    title: 'Explicit forecast FCFF & present value schedule',
    unit: '₹ crore',
    periods: years,
    show_yoy: false,
    sections: [{ id: 'fcff_schedule', label: 'Forecast horizon (₹ crore, except discount factor)', rows }],
    as_of: spec.as_of,
    synthetic: spec.provenance_label === 'illustrative',
  };
}

export function buildWaccStatement(spec: DcfModelSpec): StatementSpec {
  if (spec.wacc_statement) return spec.wacc_statement;
  const w = spec.wacc_build;
  const p = spec.as_of || 'Current';
  const weightDebt = typeof w.weight_debt === 'number' ? w.weight_debt : Number((100 - w.weight_equity).toFixed(2));
  const rows: StatementRow[] = [
    { line_code: 'WACC.RF', label: 'Risk-free rate (Rf, 10Y G-Sec %)', level: 1, kind: 'line', values: { [p]: w.rf_used_pct } },
    { line_code: 'WACC.BETA', label: 'Adjusted beta (Blume)', level: 1, kind: 'line', values: { [p]: w.beta_adj } },
    { line_code: 'WACC.ERP', label: 'Total equity risk premium (India %)', level: 1, kind: 'line', values: { [p]: w.erp_total_pct } },
    { line_code: 'WACC.KE', label: 'Cost of equity (Ke %)', level: 0, kind: 'subtotal', values: { [p]: w.ke_pct } },
    ...(typeof w.kd_pretax_pct === 'number'
      ? [{ line_code: 'WACC.KD_PRE', label: 'Pre-tax cost of debt (%)', level: 1, kind: 'line' as const, values: { [p]: w.kd_pretax_pct } }]
      : []),
    { line_code: 'WACC.TAX', label: 'Effective tax rate (%)', level: 1, kind: 'line', values: { [p]: w.tax_rate_pct } },
    { line_code: 'WACC.KD', label: 'Post-tax cost of debt (Kd %)', level: 0, kind: 'subtotal', values: { [p]: w.kd_used_pct } },
    { line_code: 'WACC.WE', label: 'Equity weight (%)', level: 1, kind: 'line', values: { [p]: w.weight_equity } },
    { line_code: 'WACC.WD', label: 'Debt weight (%)', level: 1, kind: 'line', values: { [p]: weightDebt } },
    { line_code: 'WACC.TOTAL', label: 'Weighted average cost of capital (WACC %)', level: 0, kind: 'total', values: { [p]: w.wacc_pct } },
  ];
  return {
    statement: 'pnl',
    title: 'WACC build-up',
    unit: '% / ratio',
    periods: [p],
    show_yoy: false,
    sections: [{ id: 'wacc_build', label: 'Cost of capital components', rows }],
    as_of: spec.as_of,
    synthetic: spec.provenance_label === 'illustrative',
  };
}

export function buildBridgeChartSpec(spec: DcfModelSpec): ChartSpec {
  return {
    kind: 'waterfall',
    x: 'label',
    y: 'value',
    unit: '₹ Cr',
    data: (spec.bridge || []).map((b, idx, arr) => ({
      label: b.label,
      value: b.value_inr_cr,
      type:
        b.type ||
        (idx === arr.length - 1 || /enterprise value|equity value/i.test(b.label) ? 'total' : 'delta'),
      source: b.source,
    })),
  };
}

export const DcfModelCard: React.FC<{ spec: DcfModelSpec; isDark?: boolean; initialTab?: DcfTabId }> = ({
  spec,
  isDark = false,
  initialTab = 'summary',
}) => {
  const [tab, setTab] = useState<DcfTabId>(initialTab);

  const summaryKpis: KpiTile[] = useMemo(() => {
    const ps = spec.per_share;
    const sign = ps.upside_pct >= 0 ? '+' : '';
    return [
      { label: 'Intrinsic value / share', value: `₹${ps.intrinsic_inr.toFixed(2)}` },
      {
        label: 'Market price / share',
        value: `₹${ps.market_inr.toFixed(2)}`,
        delta: ps.market_date ? `As of ${ps.market_date}` : undefined,
      },
      { label: 'Implied upside / (downside)', value: `${sign}${ps.upside_pct.toFixed(2)}%` },
      { label: 'Valuation verdict', value: ps.verdict },
    ];
  }, [spec.per_share]);

  const sumPvFcff = useMemo(
    () => (spec.forecast.lines.pv_fcff || []).reduce((acc, v) => acc + (Number.isFinite(v) ? v : 0), 0),
    [spec.forecast.lines.pv_fcff],
  );
  const fcffStatement = useMemo(() => buildFcffStatement(spec), [spec]);
  const waccStatement = useMemo(() => buildWaccStatement(spec), [spec]);
  const bridgeSpec = useMemo(() => buildBridgeChartSpec(spec), [spec]);

  return (
    <div className="flex flex-col gap-5" data-testid="dcf-model-card">
      <div
        role="tablist"
        aria-label="DCF valuation views"
        className="flex flex-wrap items-center gap-1.5 border-b border-[var(--hairline)] pb-2.5"
        data-testid="dcf-tabs"
      >
        {TABS.map((t) => {
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={active}
              data-testid={`dcf-tab-${t.id}`}
              onClick={() => setTab(t.id)}
              className={`px-3.5 py-1.5 rounded-pill text-label transition-colors border ${
                active
                  ? 'bg-[var(--accent-pale)] text-[var(--accent-deep)] dark:text-[var(--accent-soft)] border-[var(--accent)] font-semibold'
                  : 'bg-[var(--surface)] text-[var(--ink-2)] border-[var(--hairline)] hover:text-[var(--ink)]'
              }`}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      {tab === 'summary' && (
        <div className="flex flex-col gap-5" data-testid="dcf-panel-summary">
          <KpiRenderer kpis={summaryKpis} isDark={isDark} />
          <div className="rounded-[var(--radius-lg)] border border-[var(--hairline)] bg-[var(--surface)] overflow-hidden">
            <table className="w-full text-[0.86rem]">
              <thead>
                <tr className="border-b border-[var(--hairline)] text-left text-caption text-[var(--ink-3)]">
                  <th className="py-2.5 px-4 font-medium">Valuation component</th>
                  <th className="py-2.5 px-4 font-medium text-right">Value</th>
                  <th className="py-2.5 px-4 font-medium">Basis / notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--hairline)]">
                <tr>
                  <td className="py-2.5 px-4 text-[var(--ink)]">Σ PV of explicit FCFF ({spec.forecast.years.length}Y)</td>
                  <td className="py-2.5 px-4 text-right font-mono tabular-nums text-[var(--ink)]">
                    ₹{sumPvFcff.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} Cr
                  </td>
                  <td className="py-2.5 px-4 text-[var(--ink-2)]">
                    {spec.forecast.years[0]}–{spec.forecast.years[spec.forecast.years.length - 1]} @ WACC {spec.wacc_build.wacc_pct.toFixed(2)}%
                  </td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 text-[var(--ink)]">PV of terminal value</td>
                  <td className="py-2.5 px-4 text-right font-mono tabular-nums text-[var(--ink)]">
                    ₹{spec.terminal.pv_tv_inr_cr.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} Cr
                  </td>
                  <td className="py-2.5 px-4 text-[var(--ink-2)]">
                    {spec.terminal.method === 'gordon'
                      ? `Gordon growth g = ${spec.terminal.g_pct.toFixed(2)}% (undiscounted TV ₹${spec.terminal.tv_inr_cr.toLocaleString('en-IN', { maximumFractionDigits: 1 })} Cr)`
                      : `Exit multiple ${spec.terminal.exit_multiple?.toFixed(1)}×`}
                  </td>
                </tr>
                {spec.bridge.map((b) => (
                  <tr
                    key={b.label}
                    className={b.type === 'total' || /enterprise value|equity value/i.test(b.label) ? 'font-semibold bg-[var(--surface-2)]/50' : ''}
                  >
                    <td className="py-2.5 px-4 text-[var(--ink)]">{b.label}</td>
                    <td className="py-2.5 px-4 text-right font-mono tabular-nums text-[var(--ink)]">
                      {b.value_inr_cr < 0
                        ? `(₹${Math.abs(b.value_inr_cr).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} Cr)`
                        : `₹${b.value_inr_cr.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} Cr`}
                    </td>
                    <td className="py-2.5 px-4 text-[var(--ink-3)] text-caption">{b.source || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'fcff' && (
        <div data-testid="dcf-panel-fcff">
          <StatementTable statement={fcffStatement} />
        </div>
      )}

      {tab === 'wacc' && (
        <div data-testid="dcf-panel-wacc">
          <StatementTable statement={waccStatement} />
        </div>
      )}

      {tab === 'bridge' && (
        <div className="h-[25rem] w-full" data-testid="dcf-panel-bridge">
          <ChartRenderer spec={bridgeSpec} isDark={isDark} title="Enterprise to Equity Value Bridge (₹ Cr)" />
        </div>
      )}

      {tab === 'sensitivity' && (
        <div className="h-[27rem] w-full" data-testid="dcf-panel-sensitivity">
          <SensitivityGrid spec={spec.sensitivity_grid} isDark={isDark} />
        </div>
      )}

      {tab === 'tornado' && (
        <div className="h-[25rem] w-full" data-testid="dcf-panel-tornado">
          <Tornado spec={spec.tornado} isDark={isDark} />
        </div>
      )}

      <footer
        className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[var(--hairline)] text-caption text-[var(--ink-3)]"
        data-testid="dcf-disclaimer"
      >
        <span className="font-medium text-[var(--ink-2)]">{spec.disclaimer}</span>
        <span className="font-mono">
          Run {spec.run_id} · As of {spec.as_of}
          {spec.engine_version ? ` · ${spec.engine_version}` : ''}
        </span>
      </footer>
    </div>
  );
};

export default DcfModelCard;
