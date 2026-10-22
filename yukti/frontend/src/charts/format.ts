/**
 * Units, Indian number formatting and human labels for the chart system.
 */
import { DISCIPLINE_NAMES, WORK_CENTRE_NAMES } from './codes';

export type UnitKind = 'currency' | 'percent' | 'count' | 'plain';

export interface UnitInfo {
  kind: UnitKind;
  /** Noun for counts ("executives"), empty when unknown. */
  noun: string;
  /** Axis / legend label, e.g. "₹ Crore", "% change", "Executives". */
  label: string;
  /** Raw prefix/suffix for plain units (e.g. "$/BOE"). */
  suffix?: string;
}

const ACRONYMS = ['PBT', 'EBITDA', 'HR', 'BOE', 'FY', 'MOU', 'NE', 'SC', 'ST', 'OBC', 'EWS', 'UR', 'PWD', 'HQ', 'ID', 'MMT', 'BCM', 'DPE', 'MOPNG', 'OMC', 'CMD', 'JV', 'APM', 'DD&A', 'IT', 'HSE', 'MM', 'F&A', 'CBM', 'KG', 'PG', 'GM', 'DGM', 'CGM', 'ED', 'PEC', 'RTI', 'JRTP', 'BE', 'RE', 'NPV', 'IRR'];
const ACR_MAP: Record<string, string> = Object.fromEntries(ACRONYMS.map((a) => [a.toLowerCase(), a === 'MOU' ? 'MoU' : a === 'MOPNG' ? 'MoPNG' : a]));

const KEY_LABELS: Record<string, string> = {
  grade: 'Grade',
  grade_id: 'Grade',
  current_grade_id: 'Grade',
  wc_id: 'Work centre',
  work_centre: 'Work centre',
  work_center: 'Work centre',
  wc_name: 'Work centre',
  discipline_id: 'Discipline',
  discipline: 'Discipline',
  pbt_cr: 'PBT (₹ Cr)',
  revenue_cr: 'Revenue (₹ Cr)',
  ebitda_cr: 'EBITDA (₹ Cr)',
  amount_cr: 'Amount (₹ Cr)',
  count: 'Count',
  headcount: 'Headcount',
  total_executives: 'Executives',
  executive_count: 'Executives',
  num_executives: 'Executives',
  due: 'Due for rotation',
  exempt: 'Exempt',
  achievement_pct: 'Achievement (%)',
  target_val: 'Target',
  actual_val: 'Actual',
  weight: 'Weight (%)',
  parameter: 'Parameter',
  field: 'Field',
  field_name: 'Field',
  asset: 'Asset',
  stage: 'Stage',
  status: 'Status',
  customer: 'Customer',
  fiscal_year: 'Fiscal year',
  fy: 'Fiscal year',
};

/** "grade_id" -> "Grade", "pbt_cr" -> "PBT (₹ Cr)", "Stay >= 5y" -> "Stay ≥ 5y" */
export function humanizeKey(key: string): string {
  if (!key) return '';
  const k = key.trim();
  const lower = k.toLowerCase();
  if (/^f\d+_?$/.test(lower)) return 'Total';
  if (KEY_LABELS[lower]) return KEY_LABELS[lower];
  if (/[A-Z ]/.test(k) && !k.includes('_')) return k.replace(/>=/g, '≥').replace(/<=/g, '≤');
  let s = lower;
  let suffix = '';
  if (s.endsWith('_cr')) {
    s = s.slice(0, -3);
    suffix = ' (₹ Cr)';
  } else if (s.endsWith('_pct') || s.endsWith('_percent')) {
    s = s.replace(/_(pct|percent)$/, '');
    suffix = ' (%)';
  } else if (s.endsWith('_usd')) {
    s = s.slice(0, -4);
    suffix = ' ($)';
  }
  s = s.replace(/_id$/, '').replace(/_inr$/, '').replace(/_name$/, '');
  const words = s.split(/[_\s]+/).filter(Boolean).map((w, i) => {
    if (ACR_MAP[w]) return ACR_MAP[w];
    return i === 0 ? w.charAt(0).toUpperCase() + w.slice(1) : w;
  });
  return words.join(' ') + suffix;
}

/** Entity codes -> names. "DISC-FIN" -> "Finance & Accounts (F&A)", "WC-DEL" -> "Delhi HQ" */
export function humanizeValue(v: any): string {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'boolean') return v ? 'Yes' : 'No';
  const s = String(v);
  if (/^DISC-[A-Z0-9]+$/.test(s)) return DISCIPLINE_NAMES[s] || s.slice(5);
  if (/^WC-[A-Z0-9-]+$/.test(s)) return WORK_CENTRE_NAMES[s] || s.slice(3);
  return s;
}

/** Remove engineering artefacts from prose: "(WC-DEL)", "(hrfin_gold.v_x)", "[1]". */
export function cleanText(s: string): string {
  if (!s) return '';
  return s
    .replace(/\s*\[(\d+)\]/g, '')
    .replace(/\s*\((?:WC|DISC)-[A-Z0-9-]+\)/g, '')
    .replace(/\s*\(?\b(?:hrfin_gold|hrfin_silver|hrfin_bronze)\.[a-z0-9_]+\)?/gi, '')
    .replace(/\b(DISC-[A-Z0-9]+|WC-[A-Z0-9-]+)\b/g, (m) => humanizeValue(m))
    .replace(/\b([a-z]+(?:_[a-z0-9]+)+)\b(?=\s*[:=])/g, (m) => humanizeKey(m))
    .replace(/>=/g, '≥')
    .replace(/<=/g, '≤')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

export function parseUnit(unit?: string, valueKey?: string): UnitInfo {
  const u = (unit || '').trim();
  const k = (valueKey || '').toLowerCase();
  if (/₹|\binr\b|crore|\bcr\b/i.test(u) || /(_cr|crore|_inr)$/.test(k)) {
    return { kind: 'currency', noun: '', label: '₹ Crore' };
  }
  if (/%|pct|percent/i.test(u) || /(_pct|percent|_rate|growth)/.test(k) || /%/.test(valueKey || '')) {
    return { kind: 'percent', noun: '', label: u && u !== '%' ? u : '%' };
  }
  if (/\$|usd/i.test(u)) return { kind: 'plain', noun: '', label: u, suffix: u };
  const noun = /^(count|value|number|n)$/i.test(u) ? '' : u.toLowerCase();
  return { kind: 'count', noun, label: noun ? noun.charAt(0).toUpperCase() + noun.slice(1) : '' };
}

export function groupIndian(intStr: string): string {
  let neg = false;
  if (intStr.startsWith('-')) {
    neg = true;
    intStr = intStr.slice(1);
  }
  if (intStr.length <= 3) return (neg ? '-' : '') + intStr;
  const last3 = intStr.slice(-3);
  const rest = intStr.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ',');
  return (neg ? '-' : '') + rest + ',' + last3;
}

/** Indian grouping with sensible precision (419, 7,132, 46.2, 3.88). */
export function fmtNum(v: number, decimals?: number): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  const abs = Math.abs(v);
  const d = decimals !== undefined ? decimals : Number.isInteger(v) || abs >= 1000 ? 0 : abs >= 100 ? 0 : abs >= 10 ? 1 : 2;
  const fixed = v.toFixed(d);
  const [i, f] = fixed.split('.');
  const fs = f ? f.replace(/0+$/, '') : '';
  return groupIndian(i) + (fs ? `.${fs}` : '');
}

/** Compact Indian: 1,35,000 -> "1.35 L", 2,31,17,000 -> "2.31 Cr" (for counts); currency handled separately. */
export function fmtCompact(v: number): string {
  const abs = Math.abs(v);
  const sign = v < 0 ? '-' : '';
  if (abs >= 1e7) return `${sign}${(abs / 1e7).toFixed(abs >= 1e8 ? 0 : 1).replace(/\.0$/, '')} Cr`;
  if (abs >= 1e5) return `${sign}${(abs / 1e5).toFixed(abs >= 1e6 ? 0 : 1).replace(/\.0$/, '')} L`;
  if (abs >= 1e3) return `${sign}${(abs / 1e3).toFixed(abs >= 1e4 ? 0 : 1).replace(/\.0$/, '')}k`;
  return fmtNum(v);
}

export function fmtValue(v: number, unit: UnitInfo, opts: { compact?: boolean; sign?: boolean; withNoun?: boolean } = {}): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  const sign = opts.sign && v > 0 ? '+' : '';
  switch (unit.kind) {
    case 'currency': {
      const abs = Math.abs(v);
      const neg = v < 0 ? '−' : sign;
      if (opts.compact && abs >= 1e5) return `${neg}₹${(abs / 1e5).toFixed(2).replace(/\.?0+$/, '')} L Cr`;
      if (opts.compact && abs >= 1e4) return `${neg}₹${(abs / 1e3).toFixed(0)}k Cr`;
      return `${neg}₹${fmtNum(abs)} Cr`;
    }
    case 'percent':
      return `${sign}${fmtNum(v, Math.abs(v) >= 100 ? 0 : 1)}%`;
    case 'plain':
      return `${sign}${fmtNum(v)}${unit.suffix ? ` ${unit.suffix}` : ''}`;
    default: {
      const s = `${sign}${opts.compact ? fmtCompact(v) : fmtNum(v)}`;
      return opts.withNoun && unit.noun ? `${s} ${unit.noun}` : s;
    }
  }
}

export function isNumeric(v: any): v is number {
  return typeof v === 'number' && Number.isFinite(v);
}

export function toNumber(v: any): number | null {
  if (isNumeric(v)) return v;
  if (typeof v === 'string' && /^-?[\d,]+(\.\d+)?$/.test(v.trim())) return parseFloat(v.replace(/,/g, ''));
  return null;
}
