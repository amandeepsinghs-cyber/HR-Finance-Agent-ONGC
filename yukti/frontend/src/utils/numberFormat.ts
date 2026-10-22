/**
 * Indian Number Formatting Utilities (Lakh / Crore System)
 * @deprecated use '@/charts/format'
 */

import { fmtNum, fmtCompact, fmtPct } from '@/charts/format';

export interface FormatIndianNumberOptions {
  currency?: boolean;
  decimals?: number;
  compact?: boolean;
  unit?: string;
}

/**
 * @deprecated use '@/charts/format' (fmtNum / fmtCompact / fmtValue)
 */
export function formatIndianNumber(
  val: number | string | undefined | null,
  options?: FormatIndianNumberOptions
): string {
  if (val === undefined || val === null || val === '') return '—';
  const num = typeof val === 'string' ? parseFloat(val) : val;
  if (typeof num !== 'number' || Number.isNaN(num)) return String(val);

  const prefix = options?.currency ? '₹' : '';
  const unitSuffix = options?.unit ? ` ${options.unit}` : '';

  if (options?.compact) {
    return `${prefix}${fmtCompact(num)}${unitSuffix}`;
  }

  const isInt = Number.isInteger(num);
  const decimals = options?.decimals !== undefined ? options.decimals : (isInt ? 0 : 2);
  const formatted = fmtNum(num, decimals);
  return `${prefix}${formatted}${unitSuffix}`;
}

/**
 * @deprecated use '@/charts/format' (fmtPct)
 */
export function formatPercent(val: number | string | undefined | null): string {
  if (val === undefined || val === null || val === '') return '—';
  const num = typeof val === 'string' ? parseFloat(val) : val;
  if (typeof num !== 'number' || !Number.isFinite(num)) return String(val);
  const dec = Number.isInteger(num) ? 0 : 1;
  return fmtPct(num, dec);
}
