/**
 * Signed P&L bridge (SPEC-09 §4.3; BUG-08, BUG-09). TypeScript twin of `backend/app/brain/bridge.py`.
 *
 * Both implementations read the same single source, `yukti/contracts/statement_line_classes.json`
 * (synced into `src/contracts/generated/` by `scripts/sync_contracts.mjs`), and are tested against the shared
 * fixtures in `yukti/contracts/fixtures/bridge/`. The bridge starts at reported revenue, applies every line with
 * its accounting sign, checks each reported subtotal on the way, and must land on reported PAT within ₹0.5 cr.
 * Anything else is a BridgeError: this module never invents EBITDA, DD&A or "OPEX & Levies".
 */
import classesJson from '@/contracts/generated/statement_line_classes.json';

export type BridgeClass = 'start' | 'add' | 'deduct' | 'signed' | 'subtotal' | 'end' | 'skip';
export type BridgeErrorCode = 'missing_start' | 'missing_end' | 'subtotal_mismatch' | 'pat_mismatch' | 'single_value';

export interface BridgeBar {
  label: string;
  value: number;
  type: 'total' | 'delta';
  line_code?: string;
  /** line codes folded into this bar (merged small deductions) */
  merged?: string[];
}

export interface BridgeOk {
  ok: true;
  period: string;
  unit: string;
  bars: BridgeBar[];
  /** |running total − reported PAT| in ₹ crore */
  residual: number;
}

export interface BridgeError {
  ok: false;
  code: BridgeErrorCode;
  reason: string;
}

export type BridgeResult = BridgeOk | BridgeError;

export interface StatementLine {
  line_code?: string;
  label?: string;
  /** per-period values (statement visual / fixtures) */
  values?: Record<string, number | null | undefined>;
  /** single-period value (legacy statement table rows) */
  value?: number | null;
  amount_cr?: number | null;
}

interface ClassesFile {
  tolerance_inr_cr: number;
  small_deduct_threshold_pct_of_revenue: number;
  merged_deduct_label: string;
  classes: Record<string, BridgeClass>;
  lines?: Record<string, { label?: string }>;
}

const CFG = classesJson as unknown as ClassesFile;
export const BRIDGE_TOLERANCE_CR = CFG.tolerance_inr_cr;

export function bridgeClassOf(lineCode?: string): BridgeClass | undefined {
  if (!lineCode) return undefined;
  return CFG.classes[lineCode];
}

const round2 = (n: number) => Math.round(n * 100) / 100;

function valueOf(line: StatementLine, period?: string): number | null {
  if (line.values && period !== undefined) {
    const v = line.values[period];
    return typeof v === 'number' && Number.isFinite(v) ? v : null;
  }
  const v = line.value ?? line.amount_cr;
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}

const labelOf = (line: StatementLine) =>
  line.label || (line.line_code && CFG.lines?.[line.line_code]?.label) || line.line_code || 'Line';

/**
 * Build the signed bridge for one period. Rows must be in statement order.
 * `granularity: "standard"` folds deductions below 2% of revenue into one "Other expenses (net)" delta per segment,
 * emitted immediately before the next subtotal/end (never across a subtotal), so every subtotal check still holds.
 */
export function bridge(rows: StatementLine[], period?: string, granularity: 'standard' | 'full' = 'standard'): BridgeResult {
  const classified = rows
    .map((r) => ({ r, cls: bridgeClassOf(r.line_code), v: valueOf(r, period) }))
    .filter((x) => x.cls && x.cls !== 'skip' && x.v !== null) as { r: StatementLine; cls: BridgeClass; v: number }[];

  const start = classified.find((x) => x.cls === 'start');
  if (!start) return { ok: false, code: 'missing_start', reason: 'no start line (Revenue from operations) in the statement' };
  const end = classified.find((x) => x.cls === 'end');
  if (!end) return { ok: false, code: 'missing_end', reason: 'no end line (PAT / profit for the year) in the statement' };

  const tol = CFG.tolerance_inr_cr;
  const threshold = Math.abs(start.v) * CFG.small_deduct_threshold_pct_of_revenue;
  const bars: BridgeBar[] = [{ label: labelOf(start.r), value: start.v, type: 'total', line_code: start.r.line_code }];
  let running = start.v;
  let pending = 0;
  let pendingCodes: string[] = [];

  const flush = () => {
    if (!pendingCodes.length) return;
    bars.push({ label: CFG.merged_deduct_label, value: round2(pending), type: 'delta', merged: pendingCodes });
    pending = 0;
    pendingCodes = [];
  };

  for (const x of classified) {
    if (x === start) continue;
    if (x.cls === 'add' || x.cls === 'deduct' || x.cls === 'signed') {
      const delta = x.cls === 'add' ? Math.abs(x.v) : x.cls === 'deduct' ? -Math.abs(x.v) : x.v;
      running += delta;
      if (granularity === 'standard' && x.cls === 'deduct' && Math.abs(x.v) < threshold) {
        pending += delta;
        pendingCodes.push(x.r.line_code || labelOf(x.r));
      } else {
        bars.push({ label: labelOf(x.r), value: round2(delta), type: 'delta', line_code: x.r.line_code });
      }
    } else if (x.cls === 'subtotal' || x.cls === 'end') {
      flush();
      if (Math.abs(running - x.v) > tol) {
        const name = labelOf(x.r);
        return x.cls === 'end'
          ? { ok: false, code: 'pat_mismatch', reason: `lines do not add up to reported PAT (${name}): off by ₹${round2(Math.abs(running - x.v))} cr` }
          : { ok: false, code: 'subtotal_mismatch', reason: `lines do not add up to reported subtotal ${name}${x.r.line_code ? ` (${x.r.line_code})` : ''}: off by ₹${round2(Math.abs(running - x.v))} cr` };
      }
      running = x.v; // re-anchor on the reported figure (removes rounding drift)
      bars.push({ label: labelOf(x.r), value: x.v, type: 'total', line_code: x.r.line_code });
      if (x.cls === 'end') return { ok: true, period: period || '', unit: '₹ Cr', bars, residual: 0 };
    }
  }
  return { ok: false, code: 'missing_end', reason: 'statement ended before the PAT line' };
}

/** A single KPI / one-row visual can never be bridged (BEH-04.13, BEH-07.34). */
export function singleValueError(): BridgeError {
  return { ok: false, code: 'single_value', reason: 'a single value cannot be shown as a bridge' };
}

/** Honest user-facing copy for a BridgeError (SPEC-09 §4.3 step 6); EN only on the client, HI comes from the backend. */
export function bridgeErrorCopy(err: BridgeError): string {
  return `I can't build a reliable bridge from these lines (${err.reason}). Here is the statement table.`;
}

/** Bars → chart rows understood by `waterfallOption` (typed rows: `type` total/delta). */
export function bridgeChartRows(res: BridgeOk): { step: string; amount_cr: number; type: 'total' | 'delta' }[] {
  return res.bars.map((b) => ({ step: b.label, amount_cr: b.value, type: b.type }));
}
