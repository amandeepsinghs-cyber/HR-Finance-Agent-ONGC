'use client';

import React, { useEffect, useRef, useState } from 'react';
import { PersonaType } from '@/contracts/answerContract';
import { OrbState } from './VoiceOrb';
import { Sun, Moon, ChevronDown, Check, SkipBack, SkipForward, Languages } from 'lucide-react';
import { IconButton } from './ui/primitives';

interface TopBarProps {
  currentPersona: PersonaType;
  onPersonaChange: (p: PersonaType) => void;
  isDark: boolean;
  onThemeToggle: () => void;
  language: 'en' | 'hi' | 'hi-en';
  onLanguageToggle: () => void;
  state: OrbState;
  statusLine?: string | null;
  isLiveMode: boolean;
  onToggleLiveMode: () => void;
  backend: 'checking' | 'online' | 'offline';
  demo?: { index: number; total: number; onPrev: () => void; onNext: () => void };
  micLevel?: () => number;
}

// Board members are shown by role only; officer personas carry the officer's name.
export const PERSONAS: { id: PersonaType; label: string; role: string; name?: string }[] = [
  { id: 'CMD', label: 'CMD', role: 'Chairman & CEO' },
  { id: 'DIR_HR', label: 'Dir HR', role: 'Director (HR)' },
  { id: 'DIR_FIN', label: 'Dir Fin', role: 'Director (Finance)' },
  { id: 'E2_HR', label: 'E2 · HR', role: 'Assistant Manager, HR', name: 'Pooja Verma' },
  { id: 'E3_FIN', label: 'E3 · Fin', role: 'Deputy Manager, Finance', name: 'Rajesh Kulkarni' },
];

const STATE_LABEL: Record<OrbState, string> = {
  idle: 'Ready',
  listening: 'Listening',
  thinking: 'Thinking',
  speaking: 'Speaking',
};

/** Five-bar live level meter driven by the mic RMS. */
export const LevelMeter: React.FC<{ level: () => number; active: boolean; className?: string }> = ({ level, active, className = '' }) => {
  const refs = useRef<(HTMLSpanElement | null)[]>([]);
  useEffect(() => {
    if (!active) return;
    let raf = 0;
    const weights = [0.55, 0.85, 1, 0.8, 0.5];
    const loop = () => {
      const lv = level();
      refs.current.forEach((el, i) => {
        if (!el) return;
        const jitter = 0.85 + Math.random() * 0.3;
        const h = Math.max(0.18, Math.min(1, lv * weights[i] * 1.6 * jitter));
        el.style.transform = `scaleY(${h})`;
      });
      raf = requestAnimationFrame(loop);
    };
    loop();
    return () => cancelAnimationFrame(raf);
  }, [active, level]);
  return (
    <span className={`inline-flex items-center gap-[2px] h-[0.95rem] ${className}`} aria-hidden data-testid="level-meter">
      {[0, 1, 2, 3, 4].map((i) => (
        <span
          key={i}
          ref={(el) => {
            refs.current[i] = el;
          }}
          className="w-[3px] h-full rounded-full bg-current origin-center transition-transform duration-75"
          style={{ transform: 'scaleY(0.2)' }}
        />
      ))}
    </span>
  );
};

export const TopBar: React.FC<TopBarProps> = ({
  currentPersona,
  onPersonaChange,
  isDark,
  onThemeToggle,
  language,
  onLanguageToggle,
  state,
  statusLine,
  isLiveMode,
  onToggleLiveMode,
  backend,
  demo,
  micLevel,
}) => {
  const [open, setOpen] = useState(false);
  const ddRef = useRef<HTMLDivElement | null>(null);
  const active = PERSONAS.find((p) => p.id === currentPersona) || PERSONAS[0];

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ddRef.current && !ddRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  // Single state pill: interaction state + connection merged (U4.1). Dot colour = token, aura when Yukti is active.
  const stateTone =
    state === 'listening' ? 'text-[var(--accent)]' : state === 'thinking' ? 'text-ongc-amber' : state === 'speaking' ? 'text-[var(--accent-deep)]' : 'text-[var(--ink-3)]';
  const conn = !isLiveMode
    ? { label: 'Demo', tone: 'warning' as const }
    : backend === 'online'
    ? { label: 'Live', tone: 'positive' as const }
    : backend === 'checking'
    ? { label: 'Connecting', tone: 'neutral' as const }
    : { label: 'Offline', tone: 'maroon' as const };
  const connDot = { warning: 'bg-warning-fill', positive: 'bg-[var(--positive-fill)]', neutral: 'bg-[var(--ink-3)] animate-pulse', maroon: 'bg-[var(--maroon)] animate-pulse' }[conn.tone];
  const auraState = state === 'listening' || state === 'speaking' ? 'listening' : state === 'thinking' ? 'thinking' : 'off';

  return (
    <header className="relative z-30 h-[var(--topbar-h)] px-6 flex items-center justify-between gap-4 border-b border-[var(--hairline)] bg-[var(--glass)] backdrop-blur-xl">
      {/* Brand */}
      <div className="flex items-center gap-3 min-w-0 flex-1">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/brand/ongc_logo.png" alt="ONGC" className="w-8 h-8 rounded-[var(--radius-sm)] object-contain bg-[var(--card)] ring-1 ring-[var(--hairline)] p-[2px]" />
        <div className="leading-tight min-w-0">
          <div className="font-display font-semibold text-title tracking-[-0.01em] text-[var(--ink)]">Yukti</div>
          <div className="text-caption text-[var(--ink-3)] whitespace-nowrap">HR &amp; Finance · ONGC</div>
        </div>
      </div>

      {/* Centre: one state pill (state · connection). Clicking toggles live/demo. */}
      <button
        onClick={onToggleLiveMode}
        data-testid="voice-state"
        data-state={state}
        title={isLiveMode ? 'Connected to the live agent. Click to use offline demo answers.' : 'Using offline demo answers. Click to go live.'}
        className="hidden md:flex items-center gap-2.5 pl-2 pr-3.5 py-1 rounded-pill bg-[var(--surface)] border border-[var(--hairline)] text-label max-w-[38vw] hover:bg-[var(--surface-2)] transition-colors"
      >
        <span data-aura={auraState} className="yk-aura-ring rounded-full w-6 h-6 shrink-0">
          <span className={`yk-aura-surface rounded-full w-full h-full grid place-items-center bg-[var(--card)] ${stateTone}`}>
            {state === 'listening' && micLevel ? <LevelMeter level={micLevel} active className={stateTone} /> : <span className={`w-2 h-2 rounded-full bg-current ${state !== 'idle' ? 'animate-pulse' : ''}`} />}
          </span>
        </span>
        <span className="font-medium text-[var(--ink)]">{STATE_LABEL[state]}</span>
        {statusLine && state === 'thinking' && <span className="text-[var(--ink-2)] truncate font-normal">· {statusLine}</span>}
        <span aria-hidden className="w-px h-4 bg-[var(--hairline)]" />
        <span data-testid="connection-pill" className="flex items-center gap-1.5 text-[var(--ink-2)] font-normal">
          <span className={`w-1.5 h-1.5 rounded-full ${connDot}`} />
          {conn.label}
        </span>
      </button>

      {/* Right: role · language · theme */}
      <div className="flex items-center justify-end gap-1.5 shrink-0 flex-1">
        {demo && (
          <div className="flex items-center gap-0.5 rounded-pill bg-[var(--surface)] border border-[var(--hairline)] p-0.5 text-caption" title="Demo script (← / →)">
            <button onClick={demo.onPrev} className="icon-btn !w-7 !h-7" aria-label="Previous demo answer">
              <SkipBack className="w-3.5 h-3.5" />
            </button>
            <span className="px-1 tabular-nums text-[var(--ink-2)]">
              {demo.index + 1}/{demo.total}
            </span>
            <button onClick={demo.onNext} className="icon-btn !w-7 !h-7" aria-label="Next demo answer">
              <SkipForward className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        <div className="relative" ref={ddRef}>
          <button
            onClick={() => setOpen((o) => !o)}
            aria-haspopup="listbox"
            aria-expanded={open}
            data-testid="persona-button"
            title="Switch role (access level)"
            className="flex items-center gap-2 pl-3 pr-2 py-1.5 rounded-pill hover:bg-[var(--surface)] text-label transition-colors"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-ongc-maroon" />
            <span className="font-semibold text-[var(--ink)]">{active.name ? `${active.label} · ${active.name}` : active.role}</span>
            <ChevronDown className={`w-4 h-4 text-[var(--ink-3)] transition-transform ${open ? 'rotate-180' : ''}`} />
          </button>
          {open && (
            <div role="listbox" className="absolute right-0 top-[calc(100%+0.5rem)] w-[18rem] rounded-[var(--radius-lg)] border border-[var(--hairline)] bg-[var(--card)] shadow-[var(--panel-shadow)] p-1.5 z-50">
              {PERSONAS.map((p) => {
                const sel = p.id === currentPersona;
                return (
                  <button
                    key={p.id}
                    role="option"
                    aria-selected={sel}
                    data-testid={`persona-${p.id}`}
                    onClick={() => {
                      onPersonaChange(p.id);
                      setOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2 rounded-[var(--radius-md)] flex items-center justify-between gap-3 transition-colors ${sel ? 'bg-[var(--accent-pale)]' : 'hover:bg-[var(--surface)]'}`}
                  >
                    <span className="min-w-0">
                      <span className="block text-label font-semibold text-[var(--ink)]">
                        {p.role}
                        {p.name && <span className="font-normal text-[var(--ink-2)]"> · {p.name}</span>}
                      </span>
                      <span className="block text-caption text-[var(--ink-3)]">{p.id.startsWith('E') ? 'Aggregates only (names hidden)' : 'Full access incl. named records'}</span>
                    </span>
                    {sel && <Check className="w-4 h-4 text-[var(--accent)] shrink-0" />}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <span aria-hidden className="w-px h-5 bg-[var(--hairline)] mx-1" />
        <button onClick={onLanguageToggle} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-pill text-label font-medium text-[var(--ink-2)] hover:bg-[var(--surface)] hover:text-[var(--ink)]" title="Answer language">
          <Languages className="w-4 h-4" />
          {language === 'hi' ? 'हिन्दी' : language === 'hi-en' ? 'Hinglish' : 'English'}
        </button>
        <IconButton onClick={onThemeToggle} label={isDark ? 'Switch to light mode' : 'Switch to dark mode'} data-testid="theme-toggle">
          {isDark ? <Sun /> : <Moon />}
        </IconButton>
      </div>
    </header>
  );
};
