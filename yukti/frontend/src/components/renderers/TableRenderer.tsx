'use client';

import React, { useState, useMemo } from 'react';
import { TableSpec } from '@/contracts/answerContract';
import { ChevronDown, ChevronUp, ChevronsUpDown, ChevronLeft, ChevronRight, Search } from 'lucide-react';
import { formatIndianNumber } from '@/utils/numberFormat';

interface TableRendererProps {
  table: TableSpec;
  isDark?: boolean;
}

export const TableRenderer: React.FC<TableRendererProps> = ({ table, isDark = false }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 8;

  const columns = table.columns;

  const normalizedRows = useMemo(() => {
    return table.rows.map((row) => {
      if (Array.isArray(row)) {
        const obj: Record<string, any> = {};
        columns.forEach((col, idx) => {
          obj[col] = row[idx];
        });
        return obj;
      }
      return row;
    });
  }, [table, columns]);

  const filteredRows = useMemo(() => {
    if (!searchTerm.trim()) return normalizedRows;
    const term = searchTerm.toLowerCase();
    return normalizedRows.filter((r) =>
      Object.values(r).some((v) => String(v).toLowerCase().includes(term))
    );
  }, [normalizedRows, searchTerm]);

  const sortedRows = useMemo(() => {
    if (!sortCol) return filteredRows;
    return [...filteredRows].sort((a, b) => {
      const valA = a[sortCol];
      const valB = b[sortCol];
      if (typeof valA === 'number' && typeof valB === 'number') {
        return sortDir === 'asc' ? valA - valB : valB - valA;
      }
      return sortDir === 'asc'
        ? String(valA).localeCompare(String(valB))
        : String(valB).localeCompare(String(valA));
    });
  }, [filteredRows, sortCol, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sortedRows.length / pageSize));
  const paginatedRows = sortedRows.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const handleSort = (col: string) => {
    if (sortCol === col) {
      if (sortDir === 'asc') setSortDir('desc');
      else {
        setSortCol(null);
        setSortDir('asc');
      }
    } else {
      setSortCol(col);
      setSortDir('asc');
    }
  };

  return (
    <div data-testid="table-renderer" className="w-full flex flex-col h-full space-y-3">
      {/* Search & Meta Bar */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search records..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
            className={`w-full pl-9 pr-3 py-1.5 text-sm rounded-lg border transition-colors outline-none ${
              isDark
                ? 'bg-zinc-900 border-zinc-700 text-zinc-100 focus:border-accent'
                : 'bg-white border-zinc-200 text-zinc-900 focus:border-accent'
            }`}
          />
        </div>
        <div className="text-xs text-zinc-500 font-medium">
          Showing {sortedRows.length} {sortedRows.length === 1 ? 'record' : 'records'}
        </div>
      </div>

      {/* Table Container */}
      <div className={`flex-1 overflow-auto rounded-xl border ${isDark ? 'border-zinc-800' : 'border-zinc-200'}`}>
        <table className="w-full text-left text-sm border-collapse">
          <thead>
            <tr className={isDark ? 'bg-zinc-800/80 border-b border-zinc-700' : 'bg-zinc-50 border-b border-zinc-200'}>
              {columns.map((col) => {
                const isCurrent = sortCol === col;
                return (
                  <th
                    key={col}
                    onClick={() => handleSort(col)}
                    className="py-3 px-4 text-xs font-semibold uppercase tracking-wider text-zinc-600 dark:text-zinc-300 cursor-pointer select-none hover:text-accent transition-colors"
                  >
                    <div className="flex items-center gap-1.5">
                      <span>{col}</span>
                      {isCurrent ? (
                        sortDir === 'asc' ? (
                          <ChevronUp className="w-3.5 h-3.5 text-accent" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5 text-accent" />
                        )
                      ) : (
                        <ChevronsUpDown className="w-3.5 h-3.5 text-zinc-400 opacity-50" />
                      )}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {paginatedRows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="text-center py-8 text-zinc-400">
                  No records matching search query.
                </td>
              </tr>
            ) : (
              paginatedRows.map((row, idx) => (
                <tr
                  key={idx}
                  className={`transition-colors ${
                    isDark ? 'hover:bg-zinc-800/40 text-zinc-200' : 'hover:bg-blue-50/40 text-zinc-800'
                  }`}
                >
                  {columns.map((col) => {
                    const val = row[col];
                    const isNum = typeof val === 'number';
                    return (
                      <td key={col} className="py-2.5 px-4 font-normal">
                        {isNum ? formatIndianNumber(val) : String(val ?? '—')}
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs pt-1">
          <div className="text-zinc-500">
            Page {currentPage} of {totalPages}
          </div>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className={`p-1.5 rounded-lg border transition-all ${
                currentPage === 1
                  ? 'opacity-40 cursor-not-allowed border-transparent'
                  : 'hover:border-accent hover:text-accent border-zinc-200 dark:border-zinc-700'
              }`}
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className={`p-1.5 rounded-lg border transition-all ${
                currentPage === totalPages
                  ? 'opacity-40 cursor-not-allowed border-transparent'
                  : 'hover:border-accent hover:text-accent border-zinc-200 dark:border-zinc-700'
              }`}
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
