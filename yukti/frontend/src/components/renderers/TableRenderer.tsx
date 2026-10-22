'use client';

import React, { useMemo, useState } from 'react';
import { TableSpec } from '@/contracts/answerContract';
import { humanizeKey, humanizeValue, toNumber, fmtNum } from '@/charts/format';
import { ArrowDown, ArrowUp } from 'lucide-react';

interface TableRendererProps {
  table: TableSpec;
  isDark?: boolean;
  maxRows?: number;
}

const HIDDEN = /^(lat|lon|lng|sql|query_id)$/i;

function cellText(key: string, v: any): { text: string; numeric: boolean; negative: boolean } {
  const n = toNumber(v);
  if (n !== null && !/(^|_)(id|code|year|fy)$/i.test(key)) {
    const k = key.toLowerCase();
    let text = fmtNum(n);
    if (/_cr$|crore|₹/.test(k)) text = `₹${fmtNum(n)}`;
    else if (/pct|percent|%/.test(k)) text = `${fmtNum(n, Math.abs(n) >= 100 ? 0 : 1)}%`;
    return { text, numeric: true, negative: n < 0 };
  }
  return { text: humanizeValue(v), numeric: false, negative: false };
}

export const TableRenderer: React.FC<TableRendererProps> = ({ table, maxRows = 200 }) => {
  const columns = (table.columns || []).filter((c) => !HIDDEN.test(c));
  const rows = useMemo(
    () =>
      (table.rows || []).map((r) => {
        if (Array.isArray(r)) {
          const o: Record<string, any> = {};
          (table.columns || []).forEach((c, i) => (o[c] = r[i]));
          return o;
        }
        return r as Record<string, any>;
      }),
    [table]
  );
  const [sort, setSort] = useState<{ key: string; dir: 1 | -1 } | null>(null);

  const numericCols = useMemo(
    () =>
      new Set(
        columns.filter(
          (c) =>
            rows.filter((r) => toNumber(r[c]) !== null).length >= Math.max(1, rows.length * 0.8) &&
            !/(^|_)(id|code|year|fy)$/i.test(c)
        )
      ),
    [columns, rows]
  );

  const firstNumCol = useMemo(() => columns.find((c) => numericCols.has(c)), [columns, numericCols]);

  const maxAbsVal = useMemo(() => {
    if (!firstNumCol) return 0;
    let max = 0;
    for (const r of rows) {
      const n = toNumber(r[firstNumCol]);
      if (n !== null && !isNaN(n)) {
        const abs = Math.abs(n);
        if (abs > max) max = abs;
      }
    }
    return max;
  }, [firstNumCol, rows]);

  const sorted = useMemo(() => {
    if (!sort) return rows;
    return [...rows].sort((a, b) => {
      const av = a[sort.key];
      const bv = b[sort.key];
      const an = toNumber(av);
      const bn = toNumber(bv);
      if (an !== null && bn !== null) return (an - bn) * sort.dir;
      return String(humanizeValue(av)).localeCompare(String(humanizeValue(bv))) * sort.dir;
    });
  }, [rows, sort]);

  if (!columns.length) return null;

  return (
    <div className="data-table-wrap" data-testid="data-table">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((c) => {
              const num = numericCols.has(c);
              const active = sort?.key === c;
              return (
                <th key={c} className={num ? 'num' : ''} aria-sort={active ? (sort!.dir === 1 ? 'ascending' : 'descending') : 'none'}>
                  <button
                    type="button"
                    onClick={() => setSort((s) => (s?.key === c ? { key: c, dir: (s.dir * -1) as 1 | -1 } : { key: c, dir: num ? -1 : 1 }))}
                    className={`inline-flex items-center gap-1 ${num ? 'flex-row-reverse' : ''}`}
                  >
                    <span>{humanizeKey(c)}</span>
                    {active ? (sort!.dir === 1 ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />) : null}
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sorted.slice(0, maxRows).map((r, i) => (
            <tr key={i}>
              {columns.map((c, ci) => {
                const { text, numeric, negative } = cellText(c, r[c]);
                const isFirstNum = c === firstNumCol;
                const numVal = isFirstNum ? toNumber(r[c]) : null;
                const barPct =
                  isFirstNum && numVal !== null
                    ? maxAbsVal > 0
                      ? Math.min(100, Math.max(0, (Math.abs(numVal) / maxAbsVal) * 100))
                      : 0
                    : null;
                return (
                  <td key={c} className={`${numeric ? 'num tabular-nums' : ''} ${negative ? 'neg' : ''} ${ci === 0 ? 'first' : ''}`}>
                    <span>{text}</span>
                    {isFirstNum && barPct !== null && (
                      <div className="bar-cell" aria-hidden="true">
                        <div className="bar-fill" style={{ width: `${barPct}%` }} />
                      </div>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > maxRows && (
        <div className="px-4 py-2 text-[0.8rem] text-[var(--ink-2)]">
          Showing {maxRows} of {fmtNum(rows.length)} rows. Export for the full list.
        </div>
      )}
    </div>
  );
};
