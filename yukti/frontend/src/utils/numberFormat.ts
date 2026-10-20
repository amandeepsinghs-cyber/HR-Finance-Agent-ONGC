/**
 * Indian Number Formatting Utilities (Lakh / Crore System)
 * Formats numbers in standard Indian financial notation (e.g. 23,117 / ₹1,32,508 Cr / 419)
 * Strict rule: Integers format WITHOUT decimals (419 not 419.00). Decimals only for fractional numbers.
 */

export function formatIndianNumber(
  val: number | string | undefined | null,
  options?: {
    currency?: boolean;
    decimals?: number;
    compact?: boolean;
    unit?: string;
  }
): string {
  if (val === undefined || val === null || val === '') return '—';

  const num = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(num)) return String(val);

  const prefix = options?.currency ? '₹' : '';

  // Determine decimals: if not specified, integer = 0, float = 2
  const isInt = Number.isInteger(num);
  let decimals = options?.decimals !== undefined ? options.decimals : (isInt ? 0 : 2);

  if (options?.compact) {
    const abs = Math.abs(num);
    const sign = num < 0 ? '-' : '';

    if (abs >= 10000000) {
      // Crores (1 Cr = 10^7)
      const cr = abs / 10000000;
      const dec = Number.isInteger(cr) ? 0 : 2;
      return `${sign}${prefix}${formatIndianGrouping(cr.toFixed(dec))} Cr`;
    }
    if (abs >= 100000) {
      // Lakhs (1 Lakh = 10^5)
      const lakh = abs / 100000;
      const dec = Number.isInteger(lakh) ? 0 : 2;
      return `${sign}${prefix}${formatIndianGrouping(lakh.toFixed(dec))} L`;
    }
    if (abs >= 1000) {
      const k = abs / 1000;
      const dec = Number.isInteger(k) ? 0 : 1;
      return `${sign}${prefix}${k.toFixed(dec)}k`;
    }
  }

  const parts = num.toFixed(decimals).split('.');
  const integerPart = formatIndianGrouping(parts[0]);
  const decimalPart = parts[1];

  const sign = num < 0 && !integerPart.startsWith('-') ? '-' : '';
  const unitSuffix = options?.unit ? ` ${options.unit}` : '';
  const formattedDecimal = decimals > 0 && decimalPart ? `.${decimalPart}` : '';

  return `${sign}${prefix}${integerPart}${formattedDecimal}${unitSuffix}`;
}

function formatIndianGrouping(intStr: string): string {
  let isNegative = false;
  if (intStr.startsWith('-')) {
    isNegative = true;
    intStr = intStr.slice(1);
  }

  if (intStr.length <= 3) {
    return (isNegative ? '-' : '') + intStr;
  }

  const lastThree = intStr.substring(intStr.length - 3);
  const otherNumbers = intStr.substring(0, intStr.length - 3);
  const groupedOther = otherNumbers.replace(/\B(?=(\d{2})+(?!\d))/g, ',');

  return (isNegative ? '-' : '') + groupedOther + ',' + lastThree;
}

export function formatPercent(val: number | string | undefined | null): string {
  if (val === undefined || val === null || val === '') return '—';
  const num = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(num)) return String(val);
  const sign = num > 0 ? '+' : '';
  const dec = Number.isInteger(num) ? 0 : 1;
  return `${sign}${num.toFixed(dec)}%`;
}
