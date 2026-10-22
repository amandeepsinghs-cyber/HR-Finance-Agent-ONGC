'use client';

import React, { useState } from 'react';
import { RosterTable } from '@/components/renderers/RosterTable';
import { Sun, Moon } from 'lucide-react';
import clsx from 'clsx';

import v2Roster419 from '@/fixtures/v2/v2_roster_419.json';
import v2Roster2000 from '@/fixtures/v2/v2_roster_2000.json';
import v2RosterPartialDirfin from '@/fixtures/v2/v2_roster_partial_dirfin.json';
import v2RosterAggregateE2 from '@/fixtures/v2/v2_roster_aggregate_e2.json';

interface TabItem {
  id: '419' | '2000' | 'partial' | 'aggregate';
  label: string;
  data: any;
  persona?: string;
}

const TABS: TabItem[] = [
  {
    id: '419',
    label: 'Delhi Roster (419)',
    data: v2Roster419,
    persona: v2Roster419.persona,
  },
  {
    id: '2000',
    label: 'All-India (2,000)',
    data: v2Roster2000,
    persona: v2Roster2000.persona,
  },
  {
    id: 'partial',
    label: 'Partial Masked (DIR_FIN)',
    data: v2RosterPartialDirfin,
    persona: v2RosterPartialDirfin.persona,
  },
  {
    id: 'aggregate',
    label: 'Aggregate (E2_HR)',
    data: v2RosterAggregateE2,
    persona: v2RosterAggregateE2.persona,
  },
];

export default function RosterDesignSystemPage() {
  const [activeTabId, setActiveTabId] = useState<TabItem['id']>('419');
  const [log, setLog] = useState<string>('Ready');
  const [isDark, setIsDark] = useState<boolean>(false);

  const activeTab = TABS.find((t) => t.id === activeTabId) || TABS[0];
  const tableSpec = activeTab.data?.visual?.table;

  const handleRowAction = (actionId: string, rows: Record<string, any>[]) => {
    const names = rows.map((r) => r.emp_name || r.name || r.emp_id).join(', ');
    setLog(`Action: ${actionId} | Rows: ${rows.length} | Names: ${names}`);
  };

  const handleExport = (columns: string[], rows: Record<string, any>[]) => {
    setLog(`Export: ${rows.length} rows | Columns: ${columns.length}`);
  };

  const toggleTheme = () => {
    const nextDark = !isDark;
    setIsDark(nextDark);
    if (nextDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  return (
    <div className="min-h-screen bg-[var(--canvas)] text-[var(--ink)] p-6 space-y-6">
      {/* Header bar */}
      <header className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-[var(--hairline)]">
        <div>
          <h1 className="text-headline font-display text-[var(--ink)]">
            Design System · Roster Table (U5.2)
          </h1>
          <p className="text-body text-[var(--ink-2)] mt-1">
            Executive-grade virtualized roster table supporting sort, search, filter, masking, and bulk action workflows.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            data-testid="roster-theme-toggle"
            onClick={toggleTheme}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-pill border border-[var(--hairline)] bg-[var(--card)] text-label font-medium text-[var(--ink)] hover:bg-[var(--surface)] transition-colors"
          >
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            <span>{isDark ? 'Light' : 'Dark'}</span>
          </button>
        </div>
      </header>

      {/* Fixture Tabs */}
      <nav aria-label="Roster fixtures" className="flex flex-wrap items-center gap-2">
        {TABS.map((tab) => {
          const isActive = tab.id === activeTabId;
          return (
            <button
              key={tab.id}
              type="button"
              data-testid={`roster-tab-${tab.id}`}
              onClick={() => setActiveTabId(tab.id)}
              className={clsx(
                'px-4 py-2 rounded-pill text-label font-medium transition-colors',
                isActive
                  ? 'bg-[var(--accent-deep)] text-[var(--on-accent)] dark:bg-[var(--accent-pale)] dark:text-[var(--accent-soft)]'
                  : 'bg-[var(--card)] border border-[var(--hairline)] text-[var(--ink)] hover:bg-[var(--surface-2)]'
              )}
            >
              {tab.label}
            </button>
          );
        })}
      </nav>

      {/* Log Output Line */}
      <section aria-labelledby="log-heading" className="space-y-1.5">
        <div id="log-heading" className="text-label font-medium text-[var(--ink-2)]">
          Event Log:
        </div>
        <div
          data-testid="roster-log"
          className="px-4 py-2.5 rounded-[var(--radius-md)] bg-[var(--surface-2)] border border-[var(--hairline)] font-mono text-label text-[var(--ink)] break-all"
        >
          {log}
        </div>
      </section>

      {/* Active Roster Table */}
      <main className="space-y-4">
        {tableSpec ? (
          <RosterTable
            key={activeTab.id}
            table={tableSpec}
            persona={activeTab.persona}
            onRowAction={handleRowAction}
            onExport={handleExport}
            height="min(62vh, 44rem)"
          />
        ) : (
          <div className="p-8 text-center text-label text-[var(--ink-2)]">
            No table data found in fixture.
          </div>
        )}
      </main>
    </div>
  );
}
