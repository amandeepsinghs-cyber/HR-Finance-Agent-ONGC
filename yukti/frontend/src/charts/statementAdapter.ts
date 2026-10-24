/**
 * Legacy statement-table adapter (P4.3; BUG-38/39). Until the backend emits `visual.type="statement"` (P4.2 behind
 * the `statement` contract token) and verified SSOT rows land (P1), statement answers arrive as flat tables
 * (`line_item, note_ref, amount_cr, prior_fy_cr, yoy_change_pct, …`). This converts them into a StatementSpec so they
 * render with the StatementTable: no invented "A1." / "I." numbering (hierarchy by indentation only), labels wrap,
 * subtotals/totals ruled. Values are passed through untouched (never recomputed); missing → null ("—").
 */
import type { StatementKind, StatementRow, StatementSpec, TableSpec } from '@/contracts/answerContract';
import { toNumber } from './format';

const PREFIX_RE = /^\s*(?:[—–-]+\s*)?(?:(?:[IVX]{1,4}|[A-Z]\d{0,2}|\d{1,2})[.)]\s+)?/;
const TOTAL_RE = /^(profit|loss)\s+(for|after)\b|\bprofit after tax\b|^pat\b|^total comprehensive|^net (increase|decrease) in cash|^total (equity and liabilities|assets)\b/i;
const SUBTOTAL_RE = /^(total|net cash|ebitda|ebit\b|profit before|pbt\b|gross profit|operating profit|net worth|capital employed)/i;

export function cleanStatementLabel(raw: string): string {
  return String(raw || '').replace(PREFIX_RE, '').replace(/\s{2,}/g, ' ').trim();
}

function levelOf(raw: string): number {
  if (/^\s{2,}|^\s*[—–]/.test(raw)) return 2;
  return 1;
}

/** Previous Indian FY label: FY24 → FY23, FY2023-24 → FY2022-23. */
export function priorFy(fy: string): string {
  const m = /^FY\s?(\d{2})$/i.exec(fy);
  if (m) return `FY${String(Number(m[1]) - 1).padStart(2, '0')}`;
  const m4 = /^FY\s?(\d{4})-(\d{2})$/i.exec(fy);
  if (m4) return `FY${Number(m4[1]) - 1}-${String(Number(m4[2]) - 1).padStart(2, '0')}`;
  return 'Prior year';
}

export function statementKindForMetric(metric?: string): StatementKind | null {
  if (metric === 'pnl_statement') return 'pnl';
  if (metric === 'balance_sheet') return 'balance_sheet';
  if (metric === 'cash_flow_statement') return 'cash_flow';
  return null;
}

/** Returns a StatementSpec for a legacy statement table, or null when the table is not a statement. */
export function legacyStatementFromTable(table: TableSpec | undefined, opts: { metric?: string; fy?: string; title?: string }): StatementSpec | null {
  const kind = statementKindForMetric(opts.metric);
  if (!kind || !table?.rows?.length) return null;
  const cols = table.columns || Object.keys((table.rows[0] as Record<string, unknown>) || {});
  if (!cols.includes('line_item') || !cols.includes('amount_cr')) return null;
  const fy = (opts.fy || 'FY').toUpperCase().replace(/\s/g, '');
  const prior = priorFy(fy);
  const hasPrior = cols.includes('prior_fy_cr');
  const rows: StatementRow[] = (table.rows as Record<string, unknown>[]).map((r) => {
    const raw = String(r.line_item ?? '');
    const label = cleanStatementLabel(raw);
    const rowKind: StatementRow['kind'] = TOTAL_RE.test(label) ? 'total' : SUBTOTAL_RE.test(label) ? 'subtotal' : 'line';
    const values: Record<string, number | null> = { [fy]: toNumber(r.amount_cr) };
    if (hasPrior) values[prior] = toNumber(r.prior_fy_cr);
    return {
      line_code: typeof r.line_code === 'string' ? r.line_code : undefined,
      label,
      level: rowKind === 'line' ? levelOf(raw) : 0,
      kind: rowKind,
      values,
      yoy_pct: toNumber(r.yoy_change_pct),
      note_ref: r.note_ref ? String(r.note_ref).replace(/^note\s*/i, '') : undefined,
    };
  });
  return {
    statement: kind,
    title: opts.title,
    unit: 'INR_crore',
    periods: hasPrior ? [fy, prior] : [fy],
    show_yoy: cols.includes('yoy_change_pct') && hasPrior,
    sections: [{ id: 'all', label: kind === 'pnl' ? 'Statement of Profit and Loss' : kind === 'balance_sheet' ? 'Balance Sheet' : 'Cash Flow Statement', rows }],
    footnotes: ['Legacy snapshot layout: line hierarchy approximated until verified annual-report rows are available.'],
  };
}
