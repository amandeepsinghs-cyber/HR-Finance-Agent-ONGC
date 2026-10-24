'use client';

/**
 * P4.5 B1 showcase: typed finance visuals (sensitivity grid, tornado) rendered through the real AnswerCard from
 * illustrative fixtures, light/dark. Used by the screenshot harness and the rubric scorecards (P4.8).
 */
import React, { useEffect, useState } from 'react';
import { AnswerCard } from '@/components/AnswerCard';
import type { AnswerContract } from '@/contracts/answerContract';
import grid from '@/fixtures/charts/portfolioB/sensitivity_grid.json';
import tornado from '@/fixtures/charts/portfolioB/tornado.json';
import bubble from '@/fixtures/charts/portfolioB/bubble.json';
import sunburst from '@/fixtures/charts/portfolioB/sunburst.json';
import sankey from '@/fixtures/charts/portfolioB/sankey.json';
import actions from '@/fixtures/charts/portfolioB/actions.json';

const contractOf = (id: string, visual: unknown, text: string): AnswerContract =>
  ({
    turn_id: `fixture-${id}`,
    persona: 'CMD',
    display_text: text,
    visual,
    sources: [{ kind: 'document', label: 'Illustrative UI fixture (not ONGC data)' }],
  }) as unknown as AnswerContract;

const FIXTURES: Record<string, AnswerContract> = {
  grid: contractOf('grid', grid, 'Illustrative fixture: how value per share moves with WACC and terminal growth.'),
  tornado: contractOf('tornado', tornado, 'Illustrative fixture: which drivers move value per share the most.'),
  bubble: contractOf('bubble', bubble, 'Illustrative fixture: assets by cost, margin and output.'),
  sunburst: contractOf('sunburst', sunburst, 'Illustrative fixture: revenue split by segment and product.'),
  sankey: contractOf('sankey', sankey, 'Illustrative fixture: where the volume goes.'),
  actions: contractOf('actions', actions, 'Illustrative fixture: the top actions and who should act.'),
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
            <p className="text-label font-semibold uppercase tracking-wider text-[var(--ink-3)]">Design System · P4.5</p>
            <h1 className="text-2xl font-bold tracking-tight text-[var(--ink)]">Finance visuals (illustrative fixtures)</h1>
          </div>
          <div className="flex gap-2">
            {Object.keys(FIXTURES).map((k) => (
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
