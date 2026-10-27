'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { X, ChevronDown, MousePointerClick } from 'lucide-react';
import { AFTER_EVERY_ANSWER, COMPONENTS, ComponentDetail, DIAGRAM_H, DIAGRAM_W, LADDER, LadderBand } from './content';

/** Click-through architecture (27-Oct): A = clickable diagram cards → side panel; B = orchestrator ladder. */

const pct = (v: number, of: number) => `${(v / of) * 100}%`;

const BAND_TONE: Record<LadderBand['tone'], { chip: string; rail: string }> = {
  control: { chip: 'bg-[var(--surface-2)] text-[var(--ink)]', rail: 'border-l-[var(--ink-3)]' },
  safety: { chip: 'bg-[var(--maroon-pale)] text-[var(--maroon-deep)]', rail: 'border-l-[var(--maroon)]' },
  simple: { chip: 'bg-[var(--positive-pale)] text-[var(--positive)]', rail: 'border-l-[var(--positive)]' },
  specialist: { chip: 'bg-[var(--warning-pale)] text-[var(--ink)]', rail: 'border-l-[var(--warning)]' },
  general: { chip: 'bg-[var(--accent-pale)] text-[var(--accent-deep)]', rail: 'border-l-[var(--accent)]' },
};

function DetailPanel({ item, onClose, onOpenLadder }: { item: ComponentDetail; onClose: () => void; onOpenLadder: () => void }) {
  const [technical, setTechnical] = useState(false);
  const closeRef = useRef<HTMLButtonElement | null>(null);
  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-labelledby="arch-panel-title" data-testid="arch-panel">
      <button aria-label="Close details" className="absolute inset-0 bg-[var(--ink)] opacity-20 cursor-default" onClick={onClose} />
      <aside className="absolute right-0 top-0 h-full w-full max-w-[30rem] overflow-y-auto bg-[var(--card)] border-l border-[var(--hairline)] shadow-[var(--panel-shadow)] p-6">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-[0.75rem] font-semibold uppercase tracking-[0.06em] text-[var(--ink-3)]">{item.kind}</div>
            <h3 id="arch-panel-title" className="font-display text-[1.35rem] font-bold text-[var(--ink)] leading-tight mt-0.5">
              {item.title}
            </h3>
          </div>
          <button
            ref={closeRef}
            onClick={onClose}
            aria-label="Close"
            className="inline-grid place-items-center w-9 h-9 rounded-[var(--radius-md)] text-[var(--ink-2)] hover:bg-[var(--surface-2)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent)]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <p className="mt-3 text-[1rem] text-[var(--ink)]">{item.oneLiner}</p>

        <div role="tablist" aria-label="Level of detail" className="mt-5 inline-flex rounded-[var(--radius-pill)] bg-[var(--surface)] border border-[var(--hairline)] p-0.5 text-[0.85rem]">
          {(['Plain words', 'Technical'] as const).map((lbl, i) => {
            const on = technical === (i === 1);
            return (
              <button
                key={lbl}
                role="tab"
                aria-selected={on}
                data-testid={i === 1 ? 'arch-tab-technical' : 'arch-tab-plain'}
                onClick={() => setTechnical(i === 1)}
                className={`px-3.5 py-1 rounded-[var(--radius-pill)] font-medium transition-colors ${on ? 'bg-[var(--card)] text-[var(--ink)] shadow-[var(--card-shadow)]' : 'text-[var(--ink-2)] hover:text-[var(--ink)]'}`}
              >
                {lbl}
              </button>
            );
          })}
        </div>

        {!technical ? (
          <ul className="mt-4 space-y-2.5 text-[0.93rem] text-[var(--ink-2)]">
            {item.plain.map((p) => (
              <li key={p} className="flex gap-2">
                <span aria-hidden className="mt-[0.55rem] w-1.5 h-1.5 shrink-0 rounded-full bg-[var(--accent)]" />
                <span>{p}</span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="mt-4 space-y-4 text-[0.9rem] text-[var(--ink-2)]">
            <section>
              <h4 className="font-semibold text-[var(--ink)] mb-1.5">How it works</h4>
              <ul className="list-disc pl-5 space-y-1.5">
                {item.how.map((h) => (
                  <li key={h}>{h}</li>
                ))}
              </ul>
            </section>
            <section className="grid grid-cols-2 gap-3">
              <div className="rounded-[var(--radius-md)] bg-[var(--surface)] border border-[var(--hairline)] p-3">
                <div className="text-[0.75rem] font-semibold uppercase tracking-[0.05em] text-[var(--ink-3)]">In</div>
                <div className="mt-1">{item.inputs}</div>
              </div>
              <div className="rounded-[var(--radius-md)] bg-[var(--surface)] border border-[var(--hairline)] p-3">
                <div className="text-[0.75rem] font-semibold uppercase tracking-[0.05em] text-[var(--ink-3)]">Out</div>
                <div className="mt-1">{item.outputs}</div>
              </div>
            </section>
            <section>
              <h4 className="font-semibold text-[var(--ink)] mb-1.5">Code</h4>
              <ul className="space-y-1">
                {item.code.map((c) => (
                  <li key={c}>
                    <code className="text-[0.8rem] bg-[var(--surface)] border border-[var(--hairline)] rounded px-1.5 py-0.5 break-all">{c}</code>
                  </li>
                ))}
              </ul>
            </section>
          </div>
        )}

        <section className="mt-5">
          <h4 className="font-semibold text-[var(--ink)] mb-1.5 text-[0.9rem]">Guardrails</h4>
          <div className="flex flex-wrap gap-1.5">
            {item.guardrails.map((g) => (
              <span key={g} className="text-[0.8rem] px-2.5 py-1 rounded-[var(--radius-pill)] bg-[var(--positive-pale)] text-[var(--positive)] font-medium">
                {g}
              </span>
            ))}
          </div>
        </section>

        {item.example && (
          <section className="mt-5 rounded-[var(--radius-md)] border border-[var(--hairline)] bg-[var(--surface)] p-3 text-[0.88rem]">
            <span className="font-semibold text-[var(--ink)]">Example · </span>
            {item.example}
          </section>
        )}

        {item.id === 'orchestrator' && (
          <button
            onClick={onOpenLadder}
            data-testid="arch-open-ladder"
            className="mt-5 w-full rounded-[var(--radius-md)] bg-[var(--accent)] text-[var(--on-accent)] font-semibold py-2.5 hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent-deep)]"
          >
            See the 15-step routing ladder →
          </button>
        )}
      </aside>
    </div>
  );
}

function Ladder() {
  const [open, setOpen] = useState<string | null>('14');
  return (
    <div className="space-y-3">
      {LADDER.map((band) => {
        const tone = BAND_TONE[band.tone];
        return (
          <div key={band.id} className={`rounded-[var(--radius-md)] border border-[var(--hairline)] border-l-4 ${tone.rail} bg-[var(--card)] p-4`}>
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span className={`text-[0.75rem] font-bold uppercase tracking-[0.06em] px-2 py-0.5 rounded-[var(--radius-pill)] ${tone.chip}`}>{band.name}</span>
              <span className="text-[0.85rem] text-[var(--ink-3)]">{band.why}</span>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {band.steps.map((s) => {
                const isOpen = open === s.n;
                return (
                  <div key={s.n} className="rounded-[var(--radius-md)] border border-[var(--hairline)] bg-[var(--surface)]">
                    <button
                      onClick={() => setOpen(isOpen ? null : s.n)}
                      aria-expanded={isOpen}
                      data-testid={`ladder-step-${s.n}`}
                      className="w-full flex items-center gap-3 px-3 py-2.5 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent)] rounded-[var(--radius-md)]"
                    >
                      <span className="shrink-0 w-7 h-7 rounded-full grid place-items-center bg-[var(--card)] border border-[var(--hairline)] text-[0.8rem] font-bold text-[var(--ink)]">
                        {s.n}
                      </span>
                      <span className="flex-1 min-w-0">
                        <span className="block font-semibold text-[var(--ink)] text-[0.92rem]">{s.title}</span>
                        <span className="block text-[0.8rem] text-[var(--ink-3)] truncate">{s.example}</span>
                      </span>
                      <ChevronDown className={`w-4 h-4 text-[var(--ink-3)] transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                    </button>
                    {isOpen && (
                      <div className="px-3 pb-3 pl-[3.25rem] text-[0.86rem] text-[var(--ink-2)]">
                        <p>{s.plain}</p>
                        <p className="mt-1.5">
                          <code className="text-[0.76rem] bg-[var(--card)] border border-[var(--hairline)] rounded px-1.5 py-0.5">{s.handler}</code>
                        </p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
      <div className="rounded-[var(--radius-md)] border border-dashed border-[var(--hairline)] bg-[var(--card)] p-4">
        <div className="font-semibold text-[var(--ink)] text-[0.92rem]">After every answer — whichever step produced it</div>
        <ul className="mt-2 grid gap-1.5 md:grid-cols-2 text-[0.86rem]">
          {AFTER_EVERY_ANSWER.map((a) => (
            <li key={a} className="flex gap-2">
              <span aria-hidden className="mt-[0.5rem] w-1.5 h-1.5 shrink-0 rounded-full bg-[var(--positive)]" />
              {a}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function ArchitectureExplorer() {
  const [selected, setSelected] = useState<ComponentDetail | null>(null);
  const ladderRef = useRef<HTMLDivElement | null>(null);
  const close = useCallback(() => setSelected(null), []);
  const openLadder = useCallback(() => {
    setSelected(null);
    setTimeout(() => ladderRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50);
  }, []);

  return (
    <>
      <div className="mt-6 flex items-center gap-2 text-[0.85rem] text-[var(--ink-2)]">
        <MousePointerClick className="w-4 h-4 text-[var(--accent)]" />
        Click any box on the diagram for details.
      </div>
      <div className="relative mt-2 rounded-[var(--radius-md)] border border-[var(--hairline)] shadow-[var(--card-shadow)] overflow-hidden" data-testid="arch-diagram">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/architecture/yukti_architecture.png"
          alt="Yukti AI architecture: users, Identity-Aware Proxy, Cloud Run with web app, turn orchestrator and specialist modules, Gemini Live, Gemini 2.5 Flash, BigQuery and Yahoo Finance"
          className="block w-full"
        />
        {COMPONENTS.map((c) => (
          <button
            key={c.id}
            onClick={() => setSelected(c)}
            aria-label={`${c.title}: show details`}
            title={`${c.title} — click for details`}
            data-testid={`arch-hotspot-${c.id}`}
            className="absolute rounded-[0.6rem] border-2 border-transparent hover:border-[var(--accent)] focus-visible:border-[var(--accent)] focus-visible:outline-none transition-colors cursor-pointer"
            style={{ left: pct(c.box.x, DIAGRAM_W), top: pct(c.box.y, DIAGRAM_H), width: pct(c.box.w, DIAGRAM_W), height: pct(c.box.h, DIAGRAM_H) }}
          />
        ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {COMPONENTS.map((c) => (
          <button
            key={c.id}
            onClick={() => setSelected(c)}
            className="text-[0.78rem] px-2.5 py-1 rounded-[var(--radius-pill)] border border-[var(--hairline)] bg-[var(--card)] text-[var(--ink-2)] hover:text-[var(--ink)] hover:border-[var(--accent)]"
          >
            {c.title}
          </button>
        ))}
        <a href="/architecture/yukti_architecture.svg" target="_blank" rel="noreferrer" className="text-[0.78rem] px-2.5 py-1 text-[var(--accent-deep)] hover:underline">
          Open full size ↗
        </a>
      </div>

      <div ref={ladderRef} className="scroll-mt-6" data-testid="arch-ladder">
        <h2 className="font-display text-[1.2rem] font-bold text-[var(--ink)] mt-10 mb-1">Inside the orchestrator</h2>
        <p className="text-[0.92rem] mb-4">
          Every question goes down this ladder in order; <strong className="text-[var(--ink)]">the first step that matches answers it</strong>. The
          route is decided by code, not by AI. Click a step for details.
        </p>
        <Ladder />
      </div>

      {selected && <DetailPanel item={selected} onClose={close} onOpenLadder={openLadder} />}
    </>
  );
}
