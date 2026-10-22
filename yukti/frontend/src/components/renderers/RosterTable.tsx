'use client';

import React, { useMemo, useState, useRef, useEffect, useCallback } from 'react';
import { TableSpec, RowAction } from '@/contracts/answerContract';
import { humanizeKey, fmtNum } from '@/charts/format';
import {
  Lock,
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Download,
  FileText,
  X,
  Filter,
} from 'lucide-react';
import clsx from 'clsx';
import {
  normalizeRows,
  detectNumericColumns,
  discoverFilterableColumns,
  filterAndSortRows,
  formatRosterCell,
  isActionAllowed,
  getColumnWidth,
  NormalizedRow,
} from './rosterUtils';

export interface RosterTableProps {
  table: TableSpec;
  persona?: string;
  onRowAction?: (actionId: string, rows: Record<string, any>[]) => void;
  onExport?: (columns: string[], rows: Record<string, any>[]) => void;
  height?: string; /* CSS, default 'min(62vh, 44rem)' */
}

const ROW_HEIGHT = 40; // 2.5rem at base 16px
const OVERSCAN = 8;

export const RosterTable: React.FC<RosterTableProps> = ({
  table,
  persona,
  onRowAction,
  onExport,
  height = 'min(62vh, 44rem)',
}) => {
  const columns = useMemo(() => table?.columns || [], [table?.columns]);
  const rawRows = useMemo(() => table?.rows || [], [table?.rows]);
  const masking = table?.masking;
  const isAggregateOrRefused = masking?.level === 'aggregate' || masking?.level === 'refused';
  const maskedSet = useMemo(() => new Set(masking?.masked_columns || []), [masking?.masked_columns]);

  // Normalized rows with stable IDs
  const normalizedRows = useMemo(() => normalizeRows(columns, rawRows), [columns, rawRows]);

  // Detected numeric columns
  const numericCols = useMemo(() => detectNumericColumns(columns, normalizedRows), [columns, normalizedRows]);

  // Filterable categorical columns (2 - 20 distinct values)
  const filterableCols = useMemo(
    () => discoverFilterableColumns(columns, normalizedRows, maskedSet),
    [columns, normalizedRows, maskedSet]
  );

  // States
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc' | null>(null);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());

  // Filter & sort
  const filteredRows = useMemo(
    () =>
      filterAndSortRows(
        normalizedRows,
        columns,
        searchQuery,
        filters,
        sortCol,
        sortDir,
        numericCols
      ),
    [normalizedRows, columns, searchQuery, filters, sortCol, sortDir, numericCols]
  );

  // Scroll & virtualizer container
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const headerCheckboxRef = useRef<HTMLInputElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(700);
  const rafRef = useRef<number | null>(null);

  // Container height observer
  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const updateHeight = () => {
      if (el.clientHeight > 0) {
        setContainerHeight(el.clientHeight);
      }
    };
    updateHeight();
    const ro = new ResizeObserver(updateHeight);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Passive throttled scroll listener for 60fps virtualization
  const handleScroll = useCallback(() => {
    if (rafRef.current !== null) return;
    rafRef.current = requestAnimationFrame(() => {
      if (scrollContainerRef.current) {
        setScrollTop(scrollContainerRef.current.scrollTop);
      }
      rafRef.current = null;
    });
  }, []);

  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    el.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      el.removeEventListener('scroll', handleScroll);
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [handleScroll]);

  // Reset scroll on filter/sort change
  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = 0;
    }
    setScrollTop(0);
  }, [searchQuery, filters, sortCol, sortDir]);

  // Indeterminate header checkbox state
  useEffect(() => {
    if (headerCheckboxRef.current) {
      const selectedFilteredCount = filteredRows.filter((r) => selectedKeys.has(r.__rowKey)).length;
      headerCheckboxRef.current.indeterminate =
        selectedFilteredCount > 0 && selectedFilteredCount < filteredRows.length;
    }
  }, [filteredRows, selectedKeys]);

  // Virtual window calculation
  const totalRowsCount = filteredRows.length;
  const rawStartIndex = Math.floor(scrollTop / ROW_HEIGHT);
  const startIndex = Math.max(0, rawStartIndex - OVERSCAN);
  const visibleCount = Math.ceil(containerHeight / ROW_HEIGHT) + OVERSCAN * 2;
  const endIndex = Math.min(totalRowsCount, startIndex + visibleCount);
  const visibleRows = filteredRows.slice(startIndex, endIndex);

  const topSpacerHeight = startIndex * ROW_HEIGHT;
  const bottomSpacerHeight = Math.max(0, (totalRowsCount - endIndex) * ROW_HEIGHT);
  const totalColsCount = columns.length + (isAggregateOrRefused ? 0 : 1);

  // Selection handlers
  const toggleRowSelection = (rowKey: string) => {
    if (isAggregateOrRefused) return;
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(rowKey)) {
        next.delete(rowKey);
      } else {
        next.add(rowKey);
      }
      return next;
    });
  };

  const allFilteredSelected =
    filteredRows.length > 0 && filteredRows.every((r) => selectedKeys.has(r.__rowKey));

  const toggleSelectAll = () => {
    if (isAggregateOrRefused) return;
    if (allFilteredSelected) {
      setSelectedKeys((prev) => {
        const next = new Set(prev);
        filteredRows.forEach((r) => next.delete(r.__rowKey));
        return next;
      });
    } else {
      setSelectedKeys((prev) => {
        const next = new Set(prev);
        filteredRows.forEach((r) => next.add(r.__rowKey));
        return next;
      });
    }
  };

  const clearSelection = () => {
    setSelectedKeys(new Set());
  };

  // Row actions allowed by persona
  const allowedRowActions = useMemo(() => {
    if (isAggregateOrRefused) return [];
    const actions = table?.row_actions || [];
    return actions.filter((act) => isActionAllowed(act, persona));
  }, [table?.row_actions, isAggregateOrRefused, persona]);

  // Selected row records (cleaned of internal properties, strictly present in current table)
  const selectedRowRecords = useMemo(() => {
    return normalizedRows
      .filter((r) => selectedKeys.has(r.__rowKey))
      .map(({ __rowKey, __originalIndex, ...rest }) => rest);
  }, [normalizedRows, selectedKeys]);

  // Selected count derived directly from actual records present (not stale key set)
  const selectedCount = selectedRowRecords.length;

  // Prune any selected keys that no longer exist in the current normalizedRows
  useEffect(() => {
    const currentKeySet = new Set(normalizedRows.map((r) => r.__rowKey));
    setSelectedKeys((prev) => {
      let changed = false;
      const next = new Set<string>();
      prev.forEach((k) => {
        if (currentKeySet.has(k)) {
          next.add(k);
        } else {
          changed = true;
        }
      });
      return changed ? next : prev;
    });
  }, [normalizedRows]);

  // Header sort toggle (asc -> desc -> original)
  const handleSortClick = (col: string) => {
    if (sortCol !== col) {
      setSortCol(col);
      setSortDir('asc');
    } else if (sortDir === 'asc') {
      setSortDir('desc');
    } else if (sortDir === 'desc') {
      setSortCol(null);
      setSortDir(null);
    }
  };

  // Masking reason & title
  const lockTitle = useMemo(() => {
    const reason = masking?.reason || '';
    const ruleRef = masking?.rule_ref || '';
    if (reason && ruleRef) return `${reason} (${ruleRef})`;
    return reason || ruleRef || 'Restricted by access policy';
  }, [masking?.reason, masking?.rule_ref]);

  // Total count for count display (M = total_rows ?? rows.length)
  const totalCount = table?.total_rows ?? normalizedRows.length;

  return (
    <div className="relative rounded-card border border-[var(--hairline)] bg-[var(--card)] flex flex-col overflow-hidden">
      {/* Masking Banner for aggregate / refused */}
      {isAggregateOrRefused && masking && (
        <div
          data-testid="roster-masking-banner"
          className="flex items-center gap-2.5 px-5 py-3 bg-[var(--surface-2)] border-b border-[var(--hairline)] text-label font-medium text-[var(--ink)]"
        >
          <Lock className="w-4 h-4 text-[var(--accent-deep)] dark:text-[var(--accent-soft)] shrink-0" />
          <span>
            {masking.reason || 'Restricted dataset'}
            {masking.rule_ref ? ` (${masking.rule_ref})` : ''}
          </span>
        </div>
      )}

      {/* Top Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-[var(--hairline)] bg-[var(--card)]">
        <div className="flex flex-wrap items-center gap-3 flex-1 min-w-[280px]">
          {/* Search Box */}
          <div className="relative flex items-center min-w-[200px] max-w-xs flex-1">
            <Search className="absolute left-3 w-4 h-4 text-[var(--ink-3)] pointer-events-none" />
            <input
              type="text"
              data-testid="roster-search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by name or ID..."
              aria-label="Search roster"
              className="w-full pl-9 pr-8 py-1.5 rounded-pill border border-[var(--hairline)] bg-[var(--surface)] text-label text-[var(--ink)] placeholder:text-[var(--ink-3)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                aria-label="Clear search"
                className="absolute right-2.5 p-0.5 rounded-full text-[var(--ink-3)] hover:text-[var(--ink)] hover:bg-[var(--surface-2)]"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Categorical Filters (2-20 values) */}
          {filterableCols.map(({ col, options }) => (
            <div key={col} className="flex items-center gap-1.5">
              <label htmlFor={`filter-${col}`} className="text-label text-[var(--ink-2)] font-medium">
                {humanizeKey(col)}:
              </label>
              <select
                id={`filter-${col}`}
                data-testid={`roster-filter-${col}`}
                value={filters[col] || ''}
                onChange={(e) => setFilters((prev) => ({ ...prev, [col]: e.target.value }))}
                aria-label={`Filter by ${humanizeKey(col)}`}
                className="px-2.5 py-1.5 rounded-pill border border-[var(--hairline)] bg-[var(--surface)] text-label text-[var(--ink)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] cursor-pointer"
              >
                <option value="">All</option>
                {options.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>

        {/* Count & Export */}
        <div className="flex items-center gap-3 shrink-0">
          <span data-testid="roster-count" className="text-label text-[var(--ink-2)] font-medium">
            Showing {filteredRows.length} of {totalCount}
          </span>
          <button
            type="button"
            data-testid="roster-export"
            onClick={() => {
              const rowsToExport =
                selectedCount > 0
                  ? selectedRowRecords
                  : filteredRows.map(({ __rowKey, __originalIndex, ...rest }) => rest);
              onExport?.(columns, rowsToExport);
            }}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-pill text-label font-medium bg-[var(--surface)] border border-[var(--hairline)] text-[var(--ink)] hover:bg-[var(--surface-2)] transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export</span>
          </button>
        </div>
      </div>

      {/* Virtual Table Scroll Container */}
      <div
        ref={scrollContainerRef}
        data-testid="roster-scroll-container"
        className="data-table-wrap overflow-auto relative min-h-0"
        style={{ height, maxHeight: height }}
      >
        <table
          className="data-table w-full table-fixed border-collapse"
          role="grid"
          aria-rowcount={filteredRows.length + 1}
        >
          <colgroup>
            {!isAggregateOrRefused && <col style={{ width: '3.25rem' }} />}
            {columns.map((col) => (
              <col key={col} style={{ width: getColumnWidth(col) }} />
            ))}
          </colgroup>
          <thead>
            <tr className="h-10" aria-rowindex={1}>
              {!isAggregateOrRefused && (
                <th className="px-3 py-2 text-center w-12 bg-[var(--surface)] sticky top-0 z-10 border-b border-[var(--hairline)]">
                  <input
                    ref={headerCheckboxRef}
                    data-testid="roster-select-all"
                    type="checkbox"
                    aria-label="Select all rows"
                    checked={allFilteredSelected}
                    onChange={toggleSelectAll}
                    className="rounded border-[var(--hairline)] text-[var(--accent)] focus:ring-[var(--accent)] w-4 h-4 cursor-pointer"
                  />
                </th>
              )}
              {columns.map((col) => {
                const isNumeric = numericCols.has(col);
                const isMaskedCol = maskedSet.has(col);
                const isSorted = sortCol === col;
                const ariaSort = isSorted
                  ? sortDir === 'asc'
                    ? 'ascending'
                    : 'descending'
                  : 'none';
                const buttonAriaLabel = isMaskedCol
                  ? `Sort by ${humanizeKey(col)} — hidden by policy: ${lockTitle}`
                  : `Sort by ${humanizeKey(col)}`;

                return (
                  <th
                    key={col}
                    aria-sort={ariaSort}
                    className={clsx(
                      isNumeric && 'text-right',
                      'px-3 py-2.5 font-semibold text-label text-[var(--ink-2)] bg-[var(--surface)] border-b border-[var(--hairline)] sticky top-0 z-10 select-none'
                    )}
                  >
                    <button
                      type="button"
                      data-testid={`roster-sort-${col}`}
                      onClick={() => handleSortClick(col)}
                      className={clsx(
                        'inline-flex items-center gap-1.5 hover:text-[var(--ink)] transition-colors',
                        isNumeric && 'flex-row-reverse w-full'
                      )}
                      aria-label={buttonAriaLabel}
                    >
                      <span>{humanizeKey(col)}</span>
                      {isMaskedCol && (
                        <span
                          title={lockTitle}
                          aria-label={lockTitle}
                          className="inline-flex items-center"
                        >
                          <Lock
                            data-testid={`roster-lock-${col}`}
                            className="w-3.5 h-3.5 text-[var(--ink-3)] shrink-0 inline-block"
                          />
                        </span>
                      )}
                      <span className="shrink-0 text-[var(--ink-3)]">
                        {isSorted ? (
                          sortDir === 'asc' ? (
                            <ArrowUp className="w-3.5 h-3.5 text-[var(--accent-deep)] dark:text-[var(--accent-soft)]" />
                          ) : (
                            <ArrowDown className="w-3.5 h-3.5 text-[var(--accent-deep)] dark:text-[var(--accent-soft)]" />
                          )
                        ) : (
                          <ArrowUpDown className="w-3.5 h-3.5 opacity-40 hover:opacity-100" />
                        )}
                      </span>
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {topSpacerHeight > 0 && (
              <tr style={{ height: `${topSpacerHeight}px` }} aria-hidden="true">
                <td
                  colSpan={totalColsCount}
                  style={{ height: `${topSpacerHeight}px`, padding: 0, border: 'none' }}
                />
              </tr>
            )}

            {visibleRows.map((r, idx) => {
              const isSelected = selectedKeys.has(r.__rowKey);
              const rowIndex = startIndex + idx + 2;
              return (
                <tr
                  key={r.__rowKey}
                  aria-rowindex={rowIndex}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.target === e.currentTarget && (e.key === ' ' || e.code === 'Space')) {
                      e.preventDefault();
                      toggleRowSelection(r.__rowKey);
                    }
                  }}
                  style={{ height: `${ROW_HEIGHT}px` }}
                  className={clsx(
                    'h-10 transition-colors',
                    isSelected ? 'bg-[var(--accent-pale)]' : 'hover:bg-[var(--surface)]',
                    'focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent)]'
                  )}
                >
                  {!isAggregateOrRefused && (
                    <td className="px-3 py-2 text-center w-12 border-b border-[var(--hairline)]">
                      <input
                        type="checkbox"
                        data-testid={`roster-select-row-${r.__rowKey}`}
                        checked={isSelected}
                        onChange={() => toggleRowSelection(r.__rowKey)}
                        aria-label={`Select ${r.emp_name || 'row'}`}
                        className="rounded border-[var(--hairline)] text-[var(--accent)] focus:ring-[var(--accent)] w-4 h-4 cursor-pointer"
                      />
                    </td>
                  )}
                  {columns.map((col, colIdx) => {
                    const isMaskedCol = maskedSet.has(col);
                    const cell = formatRosterCell(col, r[col], isMaskedCol);
                    return (
                      <td
                        key={col}
                        className={clsx(
                          'px-3 py-2 text-label border-b border-[var(--hairline)] truncate max-w-xs',
                          cell.numeric && 'num tabular-nums text-right',
                          colIdx === 0 && 'font-medium text-[var(--ink)]'
                        )}
                      >
                        {cell.isMasked ? (
                          <span
                            className="text-[var(--ink-3)] select-none font-mono"
                            aria-label="hidden by policy"
                          >
                            ••••
                          </span>
                        ) : (
                          <span>{cell.text}</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}

            {bottomSpacerHeight > 0 && (
              <tr style={{ height: `${bottomSpacerHeight}px` }} aria-hidden="true">
                <td
                  colSpan={totalColsCount}
                  style={{ height: `${bottomSpacerHeight}px`, padding: 0, border: 'none' }}
                />
              </tr>
            )}
          </tbody>
        </table>

        {filteredRows.length === 0 && (
          <div data-testid="roster-empty" className="py-16 text-center text-label text-[var(--ink-2)]">
            No matching people
          </div>
        )}
      </div>

      {/* Sticky Bottom Action Bar when >= 1 row selected */}
      {selectedCount > 0 && !isAggregateOrRefused && (
        <div
          data-testid="roster-action-bar"
          className="sticky bottom-0 z-20 flex items-center justify-between gap-3 px-5 py-3 bg-[var(--surface)] border-t border-[var(--hairline)] shadow-[var(--card-shadow)]"
        >
          <div className="flex items-center gap-2">
            <span
              data-testid="roster-selected-count"
              className="text-label font-medium text-[var(--ink)]"
            >
              {selectedCount} selected
            </span>
          </div>

          <div className="flex items-center gap-2.5">
            {allowedRowActions.map((action) => (
              <button
                key={action.id}
                type="button"
                data-testid={`roster-action-${action.id}`}
                onClick={() => onRowAction?.(action.id, selectedRowRecords)}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-pill text-label font-medium bg-[var(--accent)] text-[var(--on-accent)] hover:opacity-95 transition-opacity"
              >
                {action.action === 'draft_transfer_note' && <FileText className="w-3.5 h-3.5" />}
                <span>
                  {action.label} ({selectedCount})
                </span>
              </button>
            ))}

            <button
              type="button"
              data-testid="roster-action-export"
              onClick={() => onExport?.(columns, selectedRowRecords)}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-pill text-label font-medium bg-[var(--card)] border border-[var(--hairline)] text-[var(--ink)] hover:bg-[var(--surface-2)] transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export ({selectedCount})</span>
            </button>

            <button
              type="button"
              data-testid="roster-action-clear"
              onClick={clearSelection}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-pill text-label font-medium text-[var(--ink-2)] hover:text-[var(--ink)] hover:bg-[var(--surface-2)] transition-colors"
            >
              <X className="w-3.5 h-3.5" />
              <span>Clear</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
