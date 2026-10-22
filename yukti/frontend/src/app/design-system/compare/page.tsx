'use client';

import React, { useEffect, useState } from 'react';
import { CompareRenderer } from '@/components/renderers/CompareRenderer';
import { CompareSpec } from '@/contracts/answerContract';
import v2CompareDelhiMumbai from '@/fixtures/v2/v2_compare_delhi_mumbai.json';

export default function CompareDesignSystemPage() {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  const compareSpec = v2CompareDelhiMumbai.visual.compare as unknown as CompareSpec;
  const title = v2CompareDelhiMumbai.visual.title;
  const unit = v2CompareDelhiMumbai.visual.chart?.unit;

  return (
    <main className="min-h-screen p-8 bg-[var(--canvas)] text-[var(--ink)] transition-colors">
      <div className="max-w-6xl mx-auto flex flex-col gap-6">
        <header className="flex items-center justify-between border-b border-[var(--hairline)] pb-4">
          <div>
            <p className="text-label font-semibold uppercase tracking-wider text-[var(--ink-3)]">
              Design System · FEAT-009
            </p>
            <h1 className="text-2xl font-bold tracking-tight text-[var(--ink)]">Compare View Showcase</h1>
          </div>
          <button
            type="button"
            data-testid="compare-theme"
            onClick={() => setIsDark((d) => !d)}
            className="px-4 py-2 text-sm font-medium rounded-lg border border-[var(--hairline)] bg-[var(--card)] text-[var(--ink)] hover:bg-[var(--surface)] transition-colors cursor-pointer"
          >
            Toggle {isDark ? 'Light' : 'Dark'}
          </button>
        </header>

        <section className="p-6 rounded-2xl border border-[var(--hairline)] bg-[var(--card)] shadow-[var(--card-shadow)]">
          <CompareRenderer
            compare={compareSpec}
            isDark={isDark}
            title={title}
            unit={unit}
          />
        </section>
      </div>
    </main>
  );
}
