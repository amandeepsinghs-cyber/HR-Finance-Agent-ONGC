'use client';

/**
 * PersonaPicker (P2H.2, SPEC-06 §4.4): the demo "Sign in as…" dialog. Lists the 11 personas from the server
 * directory (`/api/auth/personas`), grouped Leadership / HR / Finance. Picking one starts a new signed session
 * (the parent calls `POST /api/auth/session`); this is the ONLY way to change persona in the UI.
 */
import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Check, X } from 'lucide-react';
import { PERSONA_DIRECTORY, personaInfo, type PersonaGroup, type PublicPersona } from '@/personas';
import type { PersonaType } from '@/contracts/answerContract';

export interface PersonaPickerProps {
  open: boolean;
  current: PersonaType | null;
  /** blocking first sign-in: no close button, Escape / backdrop do nothing (BEH-01.01) */
  required?: boolean;
  onPick: (id: PersonaType) => void;
  onClose: () => void;
}

const GROUPS: PersonaGroup[] = ['Leadership', 'HR', 'Finance'];
const ACCESS_NOTE: Record<string, string> = {
  cmd: 'Everything, including named and confidential records',
  director: 'Named records within own function; cross-function as aggregates',
  junior: 'Own records, policies and aggregates (names hidden)',
};

export function PersonaPicker({ open, current, required = false, onPick, onClose }: PersonaPickerProps) {
  const [server, setServer] = useState<PublicPersona[] | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open || server) return;
    let alive = true;
    fetch('/api/auth/personas', { credentials: 'same-origin', cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => {
        if (alive && j?.personas) setServer((j.personas as PublicPersona[]).filter((p) => personaInfo(p.persona_id)));
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [open, server]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && !required && onClose();
    document.addEventListener('keydown', onKey);
    dialogRef.current?.querySelector<HTMLButtonElement>('[aria-checked="true"], button[data-persona]')?.focus();
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose, required]);

  if (!open || typeof document === 'undefined') return null;

  const rows = PERSONA_DIRECTORY.map((p) => {
    const s = server?.find((x) => x.persona_id === p.id);
    return { ...p, display_name: s?.display_name || p.display_name, designation: s?.functional_designation || s?.designation || p.designation };
  });

  // Portal to <body>: the TopBar uses backdrop-blur, which makes it the containing block for `position: fixed`
  // descendants — rendered inside it, the modal was centred on the 92 px header and its top was cut off.
  return createPortal(
    <div data-testid="persona-picker-overlay" className="fixed inset-0 z-[70] grid place-items-center bg-[color-mix(in_srgb,var(--ink)_28%,transparent)] p-4" onMouseDown={(e) => e.target === e.currentTarget && !required && onClose()}>
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="persona-picker-title"
        data-testid="persona-picker"
        className="w-[min(40rem,96vw)] max-h-[88vh] overflow-y-auto rounded-[var(--radius-lg)] border border-[var(--hairline)] bg-[var(--card)] shadow-[var(--panel-shadow)]"
      >
        <div className="flex items-start justify-between gap-4 px-5 pt-4 pb-3 border-b border-[var(--hairline)]">
          <div>
            <h2 id="persona-picker-title" className="text-[1.05rem] font-semibold text-[var(--ink)]">
              Sign in as…
            </h2>
            <p className="text-caption text-[var(--ink-2)] mt-0.5">Demo identities (illustrative). Access follows the role you pick; it cannot be changed by voice or text.</p>
          </div>
          {!required && <button type="button" onClick={onClose} aria-label="Close" className="w-8 h-8 grid place-items-center rounded-full text-[var(--ink-2)] hover:bg-[var(--surface)]">
            <X className="w-4 h-4" />
          </button>}
        </div>
        <div className="px-3 py-3 grid gap-3">
          {GROUPS.map((g) => (
            <section key={g} aria-label={g}>
              <div className="px-2 pb-1 text-label uppercase tracking-[0.08em] text-[var(--ink-3)]">{g}</div>
              <div role="radiogroup" className="grid sm:grid-cols-2 gap-1">
                {rows
                  .filter((p) => p.group === g)
                  .map((p) => {
                    const sel = p.id === current;
                    return (
                      <button
                        key={p.id}
                        type="button"
                        role="radio"
                        aria-checked={sel}
                        data-persona={p.id}
                        data-testid={`persona-${p.id}`}
                        onClick={() => onPick(p.id)}
                        className={`text-left px-3 py-2 rounded-[var(--radius-md)] flex items-start justify-between gap-3 transition-colors ${
                          sel ? 'bg-[var(--accent-pale)]' : 'hover:bg-[var(--surface)]'
                        }`}
                      >
                        <span className="min-w-0">
                          <span className="block text-label font-semibold text-[var(--ink)]">{p.display_name}</span>
                          <span className="block text-caption text-[var(--ink-2)]">{p.designation}</span>
                          <span className="block text-caption text-[var(--ink-3)]">{ACCESS_NOTE[p.tier]}</span>
                        </span>
                        {sel && <Check className="w-4 h-4 text-[var(--accent)] shrink-0 mt-0.5" />}
                      </button>
                    );
                  })}
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>,
    document.body,
  );
}
