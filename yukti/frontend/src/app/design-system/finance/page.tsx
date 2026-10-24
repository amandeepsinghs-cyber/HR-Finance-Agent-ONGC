'use client';

/**
 * P4.5 & P4.8 showcase: typed finance visuals (statement, waterfall, combo, sensitivity_grid, tornado, dcf_model,
 * bubble, sunburst, sankey, actions, clarify) rendered through the real AnswerCard from illustrative fixtures,
 * light/dark. Used by the screenshot harness (`scripts/shoot_finance_visuals.ts`) and rubric scorecards (P4.8).
 */
import React, { useEffect, useState } from 'react';
import { AnswerCard } from '@/components/AnswerCard';
import type { AnswerContract, StatementRow, StatementSpec } from '@/contracts/answerContract';
import { bridge, bridgeChartRows, type BridgeOk } from '@/charts/bridge';
import pnlFx from '@/fixtures/charts/portfolioB/statement_pnl.json';
import comboFx from '@/fixtures/charts/portfolioA/combo_revenue_margin.json';
import grid from '@/fixtures/charts/portfolioB/sensitivity_grid.json';
import tornado from '@/fixtures/charts/portfolioB/tornado.json';
import bubble from '@/fixtures/charts/portfolioB/bubble.json';
import sunburst from '@/fixtures/charts/portfolioB/sunburst.json';
import sankey from '@/fixtures/charts/portfolioB/sankey.json';
import actions from '@/fixtures/charts/portfolioB/actions.json';
import dcfModel from '@/fixtures/charts/portfolioB/dcf_model.json';

const contractOf = (id: string, visual: unknown, text: string, extra?: Partial<AnswerContract>): AnswerContract =>
  ({
    turn_id: `fixture-${id}`,
    persona: 'CMD',
    display_text: text,
    visual,
    sources: [{ kind: 'document', label: 'Illustrative UI fixture · Standalone P&L p.1 (as of FY26)' }],
    ...extra,
  }) as unknown as AnswerContract;

const stmtSpec: StatementSpec = {
  ...(pnlFx as unknown as StatementSpec),
  source: { primary: 'Synthetic Fixture (pre-SPEC-01) p.1', basis: 'Standalone · Ind AS', verified: true },
  as_of: 'FY26',
};
const allStmtRows: StatementRow[] = stmtSpec.sections.flatMap((s) => s.rows);
const fy26Bridge = bridge(allStmtRows, 'FY26') as BridgeOk;

const FIXTURES: Record<string, AnswerContract> = {
  statement: contractOf(
    'statement',
    {
      type: 'statement',
      mode: 'replace',
      title: 'Standalone P&L FY22–FY26: FY26 PAT at ₹32,866 Cr (−7.7% YoY) on ₹1,32,508 Cr revenue',
      kpis: [
        { label: 'Revenue from operations (FY26)', value: '₹1,32,508 Cr', delta: '-3.9% YoY' },
        { label: 'Profit before tax (FY26)', value: '₹43,662 Cr', delta: '-8.3% YoY' },
        { label: 'Profit for the year (FY26)', value: '₹32,866 Cr', delta: '-7.7% YoY' },
      ],
      statement: stmtSpec,
    },
    'Illustrative fixture: 5-year Standalone Statement of Profit and Loss (FY22–FY26) in accounting layout.',
    { query_spec: { version: 1, domain: 'finance', metric: 'pnl_statement', period: { fy: 'FY26' } } as any },
  ),
  waterfall: contractOf(
    'waterfall',
    {
      type: 'chart',
      mode: 'replace',
      title: 'FY26 Standalone P&L Bridge: Revenue ₹1,32,508 Cr to PAT ₹32,866 Cr (residual ₹0.00 Cr)',
      chart: {
        kind: 'waterfall',
        x: 'step',
        y: 'amount_cr',
        unit: '₹ Cr',
        data: fy26Bridge.ok ? bridgeChartRows(fy26Bridge) : [],
      },
    },
    'Illustrative fixture: signed P&L bridge from Revenue from operations to Profit for the year (FY26).',
  ),
  combo: contractOf(
    'combo',
    {
      type: 'chart',
      mode: 'replace',
      title: 'Revenue peaked at ₹1,55,517 Cr in FY23 while PAT margin held at 24.8% in FY26',
      chart: {
        kind: 'combo',
        x: 'fy',
        y: 'revenue_cr',
        unit: '₹ Cr',
        data: (comboFx as any).data,
      },
    },
    'Illustrative fixture: dual-axis combo chart pairing Revenue (₹ Cr bars) with PAT margin (% line) across FY22–FY26.',
  ),
  sensitivity_grid: contractOf('sensitivity_grid', grid, 'Illustrative fixture: how value per share moves with WACC and terminal growth.'),
  grid: contractOf('grid', grid, 'Illustrative fixture: how value per share moves with WACC and terminal growth.'),
  tornado: contractOf('tornado', tornado, 'Illustrative fixture: which drivers move value per share the most.'),
  dcf_model: contractOf('dcf_model', dcfModel, 'Illustrative fixture: DCF valuation model with ₹205.45/sh intrinsic value (+36.96% vs ₹150.00 market).'),
  bubble: contractOf('bubble', bubble, 'Illustrative fixture: assets by cost, margin and output.'),
  sunburst: contractOf('sunburst', sunburst, 'Illustrative fixture: revenue split by segment and product.'),
  sankey: contractOf('sankey', sankey, 'Illustrative fixture: where the volume goes.'),
  actions: contractOf('actions', actions, 'Illustrative fixture: the top actions and who should act.'),
  // P2F.1 (SPEC-08 §3.2): options come from the coverage manifest in production; fixed here for the showcase
  clarify: {
    ...contractOf('clarify', { type: 'none', mode: 'replace' }, 'Which year would you like: FY26, FY25, or the last five or ten years?'),
    clarify: {
      slot: 'fiscal_period',
      question: 'Which year would you like: FY26, FY25, or the last five or ten years?',
      options: [
        { label: 'FY26 (latest)', value: 'FY26' },
        { label: 'FY25 (last year)', value: 'FY25' },
        { label: 'Last 5 years', value: 'FY22..FY26' },
        { label: 'Last 10 years', value: 'FY17..FY26' },
      ],
    },
  } as unknown as AnswerContract,
};

export default function FinanceDesignSystemPage() {
  const [isDark, setIsDark] = useState(false);
  const [which, setWhich] = useState<string>('grid');

  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    if (q.get('dark') === '1') setIsDark(true);
    const v = q.get('v');
    if (v && FIXTURES[v]) setWhich(v);
  }, []);
  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark);
  }, [isDark]);

  return (
    <main className="min-h-screen p-8 bg-[var(--canvas)] text-[var(--ink)]">
      <div className="max-w-6xl mx-auto flex flex-col gap-6">
        <header className="flex items-center justify-between border-b border-[var(--hairline)] pb-4">
          <div>
            <p className="text-label font-semibold uppercase tracking-wider text-[var(--ink-3)]">Design System · P4.5 & P4.8</p>
            <h1 className="text-2xl font-bold tracking-tight text-[var(--ink)]">Finance visuals (illustrative fixtures)</h1>
          </div>
          <div className="flex flex-wrap gap-2">
            {Object.keys(FIXTURES)
              .filter((k) => k !== 'grid')
              .map((k) => (
                <button
                  key={k}
                  type="button"
                  data-testid={`fixture-${k}`}
                  onClick={() => setWhich(k)}
                  className={`px-3 py-2 text-label rounded-lg border border-[var(--hairline)] ${which === k ? 'bg-[var(--surface-2)]' : 'bg-[var(--card)]'}`}
                >
                  {k}
                </button>
              ))}
            <button
              type="button"
              data-testid="finance-theme"
              onClick={() => setIsDark((d) => !d)}
              className="px-3 py-2 text-label rounded-lg border border-[var(--hairline)] bg-[var(--card)]"
            >
              {isDark ? 'Light' : 'Dark'}
            </button>
          </div>
        </header>
        <AnswerCard key={`${which}-${isDark}`} contract={FIXTURES[which]} isDark={isDark} persona="CMD" isLatest />
      </div>
    </main>
  );
}
