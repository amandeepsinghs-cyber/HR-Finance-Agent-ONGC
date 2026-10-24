'use client';

/**
 * P4.5 B2: `visual.type = "actions"` (SPEC-08 §7.3) — the top-5 actions as numbered cards plus the
 * "Five things for others to act on" delegation table. Every word comes from the contract (no hard-coded copy
 * besides headings); impacts are always labelled as modelled estimates. Owner/assignment columns are hidden when
 * the backend omits them for E1–E4 personas ("for discussion", SPEC-08 §7.4).
 */
import React from 'react';
import type { ActionsSpec, ActionItem } from '@/contracts/answerContract';
import { fmtNum } from '@/charts/format';

const OWNER_LABEL: Record<string, string> = { CMD: 'CMD', DIR_FIN: 'Director (Finance)', DIR_HR: 'Director (HR)' };

export function impactText(i: ActionItem['impact']): string {
  const f = (v?: number) => (typeof v === 'number' && Number.isFinite(v) ? `₹${fmtNum(v, Math.abs(v) >= 100 ? 0 : 1)} cr` : '');
  const range = i.low !== undefined && i.high !== undefined ? `${f(i.low)} – ${f(i.high)}` : f(i.mid);
  const mid = i.mid !== undefined && i.low !== undefined ? ` (mid ${f(i.mid)})` : '';
  const kind = i.kind === 'annual' ? ' a year' : i.kind === 'one_off' ? ' one-off' : '';
  return `${range}${mid}${kind}`.trim();
}

export const ActionsCard: React.FC<{ actions: ActionsSpec }> = ({ actions }) => {
  const items = [...(actions.items || [])].sort((a, b) => a.rank - b.rank).slice(0, 5);
  const showOwner = items.some((i) => !!i.owner) || (actions.delegation_table || []).some((r) => !!r.owner);
  return (
    <div className="flex flex-col gap-5" data-testid="actions-card">
      <ol className="grid gap-3">
        {items.map((it) => (
          <li
            key={it.lever_id || it.rank}
            data-testid="action-item"
            className="rounded-card border border-[var(--hairline)] bg-[var(--card)] p-4 flex gap-4"
          >
            <span className="shrink-0 w-8 h-8 rounded-full grid place-items-center bg-[var(--accent-pale)] text-[var(--accent-deep)] dark:text-[var(--accent-soft)] font-semibold tabular-nums">
              {it.rank}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <h3 className="text-body font-semibold text-[var(--ink)]">{it.title}</h3>
                <span className="text-label tabular-nums text-[var(--ink)]" data-testid="action-impact">
                  {impactText(it.impact)}
                  <span className="ml-2 text-caption text-[var(--ink-3)]">{it.impact?.label || 'Modelled estimate'}</span>
                </span>
              </div>
              <p className="mt-1 text-label text-[var(--ink-2)]">{it.what_to_do}</p>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-caption text-[var(--ink-3)]">
                {showOwner && it.owner && <span>Owner: {OWNER_LABEL[it.owner] || it.owner}</span>}
                {it.horizon_days && <span>Horizon: {it.horizon_days} days</span>}
                <span>KPI: {it.kpi}</span>
                {typeof it.confidence === 'number' && <span>Confidence: {Math.round(it.confidence * 100)}%</span>}
              </div>
              {it.evidence?.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {it.evidence.map((e, k) => (
                    <span key={k} className="px-2 py-0.5 rounded-pill border border-[var(--hairline)] text-caption text-[var(--ink-2)]">
                      {e.type === 'ar' ? 'Annual report' : 'Data'}: {e.ref}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </li>
        ))}
      </ol>

      {(actions.delegation_table || []).length > 0 && (
        <section aria-label="Five things for others to act on">
          <h3 className="mb-2 text-label font-semibold uppercase tracking-[0.06em] text-[var(--ink-2)]">
            {showOwner ? 'Five things for others to act on' : 'Points for discussion'}
          </h3>
          <div className="data-table-wrap overflow-x-auto">
            <table className="data-table w-full border-collapse text-label" data-testid="delegation-table">
              <thead>
                <tr className="text-left text-[var(--ink-2)]">
                  <th className="px-3 py-2 border-b border-[var(--hairline)] w-10">#</th>
                  {showOwner && <th className="px-3 py-2 border-b border-[var(--hairline)]">Owner</th>}
                  <th className="px-3 py-2 border-b border-[var(--hairline)]">Ask</th>
                  <th className="px-3 py-2 border-b border-[var(--hairline)]">By when</th>
                  <th className="px-3 py-2 border-b border-[var(--hairline)]">KPI to report</th>
                  <th className="px-3 py-2 border-b border-[var(--hairline)]">Evidence</th>
                </tr>
              </thead>
              <tbody>
                {actions.delegation_table.map((r, i) => (
                  <tr key={i} className="align-top">
                    <td className="px-3 py-2 border-b border-[var(--hairline)] tabular-nums">{i + 1}</td>
                    {showOwner && <td className="px-3 py-2 border-b border-[var(--hairline)]">{r.owner ? OWNER_LABEL[r.owner] || r.owner : '—'}</td>}
                    <td className="px-3 py-2 border-b border-[var(--hairline)] text-[var(--ink)]">{r.ask}</td>
                    <td className="px-3 py-2 border-b border-[var(--hairline)]">{r.by_when || '—'}</td>
                    <td className="px-3 py-2 border-b border-[var(--hairline)]">{r.kpi || '—'}</td>
                    <td className="px-3 py-2 border-b border-[var(--hairline)] text-[var(--ink-2)]">{r.evidence || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
};

export default ActionsCard;
