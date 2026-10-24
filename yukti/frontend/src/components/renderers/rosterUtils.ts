import { TableSpec, RowAction } from '@/contracts/answerContract';
import { PERSONA_DIRECTORY, personaRank } from '@/personas';
import { humanizeValue, toNumber, fmtNum } from '@/charts/format';

export interface NormalizedRow extends Record<string, any> {
  __rowKey: string;
  __originalIndex: number;
}

export interface FilterableColumn {
  col: string;
  options: string[];
}

// P2H.2: ranks for all 11 personas (junior 1 · director 2 · CMD 3); unknown → 0
export const ROLE_RANK: Record<string, number> = Object.fromEntries(PERSONA_DIRECTORY.map((p) => [p.id, personaRank(p.id)]));

export function isActionAllowed(action: RowAction, persona?: string): boolean {
  if (!action.min_role) return true;
  // unknown min_role -> hide the action
  if (!Object.prototype.hasOwnProperty.call(ROLE_RANK, action.min_role)) {
    return false;
  }
  const requiredRank = ROLE_RANK[action.min_role];
  // missing persona must NOT default to 'CMD'; unknown persona -> rank 0
  const userRank =
    persona && Object.prototype.hasOwnProperty.call(ROLE_RANK, persona)
      ? ROLE_RANK[persona]
      : 0;
  return userRank >= requiredRank;
}

export function getColumnWidth(col: string): string {
  switch (col.toLowerCase()) {
    case 'emp_name':
    case 'name':
      return '14rem';
    case 'emp_id':
    case 'id':
      return '7.5rem';
    case 'grade':
      return '6rem';
    case 'discipline':
      return '10.5rem';
    case 'work_centre':
    case 'work_center':
      return '13.5rem';
    case 'continuous_stay_years':
      return '9rem';
    case 'posted_since':
      return '8rem';
    default:
      return '9.5rem';
  }
}

export function normalizeRows(
  columns: string[],
  rawRows: (Record<string, any> | (string | number | boolean | null)[])[]
): NormalizedRow[] {
  return (rawRows || []).map((r, i) => {
    let rowObj: Record<string, any>;
    if (Array.isArray(r)) {
      rowObj = {};
      (columns || []).forEach((c, idx) => {
        rowObj[c] = r[idx];
      });
    } else {
      rowObj = { ...r };
    }
    const empId = rowObj.emp_id && rowObj.emp_id !== '••••' ? String(rowObj.emp_id) : null;
    const name = rowObj.emp_name || rowObj.name || null;
    const key = empId ? `id_${empId}` : (name ? `name_${name}_${i}` : `row_${i}`);
    return {
      ...rowObj,
      __rowKey: key,
      __originalIndex: i,
    };
  });
}

export function formatRosterCell(
  column: string,
  value: any,
  isMasked: boolean
): { text: string; isMasked: boolean; numeric: boolean } {
  if (isMasked || value === '••••') {
    return { text: '••••', isMasked: true, numeric: false };
  }
  if (value === null || value === undefined) {
    return { text: '—', isMasked: false, numeric: false };
  }
  if (column === 'continuous_stay_years') {
    const n = toNumber(value);
    if (n !== null) {
      return { text: `${n.toFixed(1)} yrs`, isMasked: false, numeric: true };
    }
  }
  const n = toNumber(value);
  if (n !== null && !/(^|_)(id|code|year|fy)$/i.test(column)) {
    return { text: fmtNum(n), isMasked: false, numeric: true };
  }
  return { text: humanizeValue(value), isMasked: false, numeric: false };
}

export function detectNumericColumns(columns: string[], rows: NormalizedRow[]): Set<string> {
  const set = new Set<string>();
  for (const col of columns) {
    if (col === 'continuous_stay_years') {
      set.add(col);
      continue;
    }
    if (/(^|_)(id|code|year|fy)$/i.test(col)) continue;
    let numCount = 0;
    let validCount = 0;
    for (const r of rows) {
      const v = r[col];
      if (v !== null && v !== undefined && v !== '••••') {
        validCount++;
        if (toNumber(v) !== null) numCount++;
      }
    }
    if (validCount > 0 && numCount / validCount >= 0.8) {
      set.add(col);
    }
  }
  return set;
}

export function discoverFilterableColumns(
  columns: string[],
  rows: NormalizedRow[],
  maskedColumns: Set<string>
): FilterableColumn[] {
  const result: FilterableColumn[] = [];
  const preferred = ['grade', 'discipline', 'work_centre'];
  const allCandidates: string[] = [];

  for (const p of preferred) {
    if (columns.includes(p) && !allCandidates.includes(p)) {
      allCandidates.push(p);
    }
  }
  for (const c of columns) {
    if (!allCandidates.includes(c) && !/(^|_)(id|name|years|stay|date|since)$/i.test(c)) {
      allCandidates.push(c);
    }
  }

  for (const col of allCandidates) {
    if (maskedColumns.has(col)) continue;
    const unique = new Set<string>();
    for (const r of rows) {
      const v = r[col];
      if (v !== null && v !== undefined && v !== '••••' && String(v).trim() !== '') {
        unique.add(String(v));
      }
    }
    if (unique.size >= 2 && unique.size <= 20) {
      const sortedOptions = Array.from(unique).sort((a, b) =>
        a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' })
      );
      result.push({ col, options: sortedOptions });
    }
  }
  return result;
}

export function filterAndSortRows(
  rows: NormalizedRow[],
  columns: string[],
  searchQuery: string,
  filters: Record<string, string>,
  sortCol: string | null,
  sortDir: 'asc' | 'desc' | null,
  numericCols: Set<string>
): NormalizedRow[] {
  const searchTargets: string[] = [];
  for (const candidate of ['emp_name', 'emp_id', 'name']) {
    if (columns.includes(candidate)) {
      searchTargets.push(candidate);
    }
  }
  if (searchTargets.length === 0) {
    const firstText = columns.find((c) => !numericCols.has(c));
    if (firstText) searchTargets.push(firstText);
  }

  const query = searchQuery.trim().toLowerCase();

  const filtered = rows.filter((r) => {
    if (query) {
      const matched = searchTargets.some((col) => {
        const val = r[col];
        return val !== null && val !== undefined && String(val).toLowerCase().includes(query);
      });
      if (!matched) return false;
    }

    for (const [col, filterVal] of Object.entries(filters)) {
      if (!filterVal || filterVal === 'All') continue;
      if (String(r[col] ?? '') !== filterVal) {
        return false;
      }
    }

    return true;
  });

  if (!sortCol || !sortDir) {
    return filtered.slice().sort((a, b) => a.__originalIndex - b.__originalIndex);
  }

  const isNumeric = numericCols.has(sortCol);
  const dirMultiplier = sortDir === 'asc' ? 1 : -1;

  return filtered.slice().sort((a, b) => {
    const valA = a[sortCol];
    const valB = b[sortCol];

    if (isNumeric) {
      const numA = toNumber(valA);
      const numB = toNumber(valB);
      if (numA !== null && numB !== null) {
        return (numA - numB) * dirMultiplier;
      }
      if (numA === null && numB !== null) return 1;
      if (numA !== null && numB === null) return -1;
    }

    const strA = String(valA ?? '');
    const strB = String(valB ?? '');
    return strA.localeCompare(strB, undefined, { numeric: true }) * dirMultiplier;
  });
}
