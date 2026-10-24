'use client';

/**
 * P4.7 (SPEC-10 §4.4, §4.7): one export menu per answer card — Excel, CSV, PDF, PNG, SVG, Word, Google Sheets,
 * Google Docs. PNG/SVG appear only when a chart is on screen. Sheets/Docs are honest: they download a local
 * file and the card shows the "not connected yet" toast; no Google URL is ever opened.
 */
import React, { useEffect, useRef, useState } from 'react';
import { Download, Loader2 } from 'lucide-react';
import { Chip } from './ui/primitives';
import { EXPORT_MENU, ExportFormat } from '@/services/exportIntent';

export interface ExportMenuProps {
  /** a live chart is on screen (enables PNG/SVG) */
  hasChart: boolean;
  /** formats the backend allows for this answer; undefined = all; [] = export disabled */
  allowed?: ExportFormat[];
  busy: ExportFormat | null;
  onPick: (format: ExportFormat) => void;
}

export const ExportMenu: React.FC<ExportMenuProps> = ({ hasChart, allowed, busy, onPick }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);
  const items = EXPORT_MENU.filter((m) => (!m.chartOnly || hasChart) && (!allowed || allowed.includes(m.format)));

  useEffect(() => {
    if (!open) return;
    ref.current?.querySelector<HTMLButtonElement>('[role="menuitem"]')?.focus();
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  if (!items.length) return null;
  return (
    <div className="relative shrink-0" ref={ref}>
      <Chip
        onClick={() => setOpen((o) => !o)}
        className="!py-2"
        aria-haspopup="menu"
        aria-expanded={open}
        data-testid="export-button"
      >
        {busy ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Download className="w-4 h-4 text-[var(--accent-deep)] dark:text-[var(--accent-soft)]" />
        )}
        Export
      </Chip>
      {open && (
        <div
          role="menu"
          data-testid="export-menu"
          className="absolute right-0 top-[calc(100%+0.4rem)] w-[13rem] rounded-[var(--radius-lg)] border border-[var(--hairline)] bg-[var(--card)] shadow-[var(--panel-shadow)] p-1.5 z-40"
        >
          {items.map((m, i) => (
            <React.Fragment key={m.format}>
              {m.format === 'sheets' && i > 0 && <div className="my-1 border-t border-[var(--hairline)]" aria-hidden />}
              <button
                type="button"
                role="menuitem"
                data-testid={`export-item-${m.format}`}
                disabled={!!busy}
                onClick={() => {
                  setOpen(false);
                  onPick(m.format);
                }}
                className="w-full text-left px-3 py-2 rounded-[var(--radius-sm)] text-label text-[var(--ink)] hover:bg-[var(--surface)] disabled:opacity-50"
              >
                {m.label}
              </button>
            </React.Fragment>
          ))}
        </div>
      )}
    </div>
  );
};

export default ExportMenu;
