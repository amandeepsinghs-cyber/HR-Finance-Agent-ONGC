'use client';

/**
 * StatementTable (P4.3, SPEC-09 §4.2, FEAT-025; fixes BUG-38 cut-off labels, BUG-39 artificial numbering).
 *
 * A financial statement is a statement, not a grid: indented line labels that always wrap (never truncated),
 * sticky first column, latest-first FY columns with a unit row, tabular right-aligned figures in Indian grouping,
 * negatives in parentheses in default ink, bold subtotals with a hairline rule and totals with a double rule,
 * a muted YoY column, and a source footnote. No sorting, no inline bars (S7).
 */
import React from 'react';
import type { StatementRow, StatementSpec } from '@/contracts/answerContract';
import { fmtAccounting } from '@/charts/format';

export interface StatementTableProps {
  statement: StatementSpec;
  /** Enter / click on a line → "Why did {line} change?" (S12) */
  onWhy?: (row: StatementRow) => void;
}

const UNIT_LABEL: Record<string, string> = { INR_crore: '₹ crore', INR_cr: '₹ crore', INR_mn: '₹ million', INR_million: '₹ million' };
const STATEMENT_LABEL: Record<string, string> = { pnl: 'Statement of Profit and Loss', balance_sheet: 'Balance Sheet', cash_flow: 'Cash Flow Statement' };

function yoyText(v: number | null | undefined): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return '—';
  const s = Math.abs(v).toFixed(1);
  return v > 0 ? `+${s}%` : v < 0 ? `−${s}%` : '0.0%';
}

export function StatementTable({ statement, onWhy }: StatementTableProps) {
  const periods = statement.periods || [];
  const unit = statement.unit || 'INR_crore';
  const showYoy = !!statement.show_yoy && periods.length >= 2;
  const restated = statement.sections.some((s) => s.rows.some((r) => r.is_restated));
  const docs = Array.from(
    new Set(statement.sections.flatMap((s) => s.rows.map((r) => r.source?.doc).filter((d): d is string => !!d))),
  );
  const pages = Array.from(
    new Set(statement.sections.flatMap((s) => s.rows.map((r) => r.source?.page).filter((p): p is number => typeof p === 'number' && p > 0))),
  ).sort((a, b) => a - b);
  const sourceText = statement.source?.primary || (docs.length ? `${docs.join('; ')}${pages.length ? `, pp. ${pages.slice(0, 6).join(', ')}${pages.length > 6 ? '…' : ''}` : ''}` : '');

  return (
    <figure className="yk-statement w-full" data-testid="statement-table" data-statement={statement.statement}>
      <div className="w-full overflow-x-auto rounded-[var(--radius-md,0.9rem)] border border-[var(--hairline)] bg-[var(--card)]">
        <table className="yk-statement__table w-full border-collapse text-[0.92rem]">
          <caption className="sr-only">
            {statement.title || STATEMENT_LABEL[statement.statement] || 'Financial statement'}
          </caption>
          <thead>
            <tr>
              <th scope="col" className="yk-statement__label-cell yk-statement__head text-left">
                {STATEMENT_LABEL[statement.statement] || 'Line item'}
                {statement.scope ? <span className="yk-statement__scope"> · {statement.scope === 'consolidated' ? 'Consolidated' : 'Standalone'}</span> : null}
              </th>
              {periods.map((p) => (
                <th key={p} scope="col" className="yk-statement__head text-right" data-testid="statement-period">
                  {statement.period_labels?.[p] || p}
                </th>
              ))}
              {showYoy && (
                <th scope="col" className="yk-statement__head yk-statement__yoy text-right">
                  YoY %
                </th>
              )}
            </tr>
            <tr>
              <th scope="col" className="yk-statement__label-cell yk-statement__unit text-left" />
              {periods.map((p) => (
                <th key={p} scope="col" className="yk-statement__unit text-right">
                  {UNIT_LABEL[unit] || unit}
                </th>
              ))}
              {showYoy && <th scope="col" className="yk-statement__unit text-right">{periods[0]} vs {periods[1]}</th>}
            </tr>
          </thead>
          <tbody>
            {statement.sections.map((sec) => (
              <React.Fragment key={sec.id}>
                <tr className="yk-statement__section" data-testid="statement-section">
                  <th scope="rowgroup" colSpan={1 + periods.length + (showYoy ? 1 : 0)} className="yk-statement__label-cell text-left">
                    {sec.label}
                  </th>
                </tr>
                {sec.rows.map((r, i) => {
                  const kindClass = r.kind === 'total' ? 'yk-statement__row--total' : r.kind === 'subtotal' ? 'yk-statement__row--subtotal' : 'yk-statement__row--line';
                  const why = onWhy && r.kind === 'line' ? () => onWhy(r) : undefined;
                  return (
                    <tr
                      key={`${sec.id}-${r.line_code || i}`}
                      className={`yk-statement__row ${kindClass}`}
                      data-testid="statement-row"
                      data-kind={r.kind}
                      data-level={r.level}
                      tabIndex={why ? 0 : undefined}
                      onKeyDown={why ? (e) => e.key === 'Enter' && why() : undefined}
                      title={r.source?.doc ? `${r.source.doc}${r.source.page ? `, p. ${r.source.page}` : ''}` : undefined}
                    >
                      <th scope="row" className="yk-statement__label-cell text-left" style={{ paddingLeft: `calc(0.9rem + ${Math.max(0, Math.min(3, r.level || 0)) * 16}px)` }}>
                        <span className="yk-statement__label">{r.label}</span>
                        {r.is_restated ? <sup className="yk-statement__mark" aria-label="restated">†</sup> : null}
                        {r.note_ref ? <span className="yk-statement__note">Note {r.note_ref}</span> : null}
                        {why ? (
                          <button type="button" className="yk-statement__why" onClick={why} aria-label={`Why did ${r.label} change?`}>
                            Why?
                          </button>
                        ) : null}
                      </th>
                      {periods.map((p) => (
                        <td key={p} className="yk-statement__num text-right" data-testid="statement-cell">
                          {fmtAccounting(r.values?.[p], unit)}
                        </td>
                      ))}
                      {showYoy && (
                        <td className={`yk-statement__num yk-statement__yoy text-right ${typeof r.yoy_pct === 'number' && r.yoy_pct < 0 ? 'yk-statement__yoy--neg' : ''}`}>
                          {yoyText(r.yoy_pct)}
                        </td>
                      )}
                    </tr>
                  );
                })}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
      <figcaption className="yk-statement__foot" data-testid="statement-footnote">
        <span>Figures in {UNIT_LABEL[unit] || unit}; negative values in parentheses.</span>
        {statement.scope ? <span> {statement.scope === 'consolidated' ? 'Consolidated' : 'Standalone'} basis.</span> : null}
        {sourceText ? <span> Source: {sourceText}.</span> : null}
        {statement.as_of ? <span> As of {statement.as_of}.</span> : null}
        {restated ? <span> † restated in a later annual report.</span> : null}
        {statement.synthetic ? <span> Illustrative fixture data.</span> : null}
        {statement.footnotes?.filter((f) => !/negative values in parentheses/i.test(f)).map((f) => (
          <span key={f}> {f}</span>
        ))}
      </figcaption>
    </figure>
  );
}
