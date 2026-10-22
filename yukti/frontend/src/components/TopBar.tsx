'use client';

import React, { useEffect, useRef, useState } from 'react';
import { PersonaType } from '@/contracts/answerContract';
import { OrbState } from './VoiceOrb';
import { Sun, Moon, ChevronDown, Check, SkipBack, SkipForward, Languages } from 'lucide-react';

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

  const dotColor =
    state === 'listening' ? 'text-[var(--accent)]' : state === 'thinking' ? 'text-[#E37400]' : state === 'speaking' ? 'text-[var(--accent-deep)]' : 'text-[var(--ink-3)]';

  const conn = !isLiveMode
    ? { label: 'Demo answers', cls: 'bg-[#FEF7E0] text-[#7A4F01] dark:bg-[rgba(253,214,99,0.12)] dark:text-[#FDD663]', dot: 'bg-[#F9AB00]' }
    : backend === 'online'
    ? { label: 'Live', cls: 'bg-[var(--positive-pale)] text-[var(--positive)]', dot: 'bg-[var(--positive)]' }
    : backend === 'checking'
    ? { label: 'Connecting', cls: 'bg-[var(--surface-2)] text-[var(--ink-2)]', dot: 'bg-[var(--ink-3)] animate-pulse' }
    : { label: 'Offline', cls: 'bg-[var(--maroon-pale)] text-[var(--maroon)]', dot: 'bg-[var(--maroon)] animate-pulse' };

  return (
    <header className="relative z-30 h-[var(--topbar-h)] px-[1.5rem] flex items-center justify-between gap-4 border-b border-[var(--hairline)] bg-[color-mix(in_srgb,var(--canvas)_88%,transparent)] backdrop-blur-xl">
      <div className="flex items-center gap-[1rem] min-w-0">
        <div className="flex items-center gap-[0.7rem] shrink-0">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/brand/ongc_logo.png" alt="ONGC" className="w-[2.4rem] h-[2.4rem] rounded-[0.6rem] object-contain bg-white ring-1 ring-[var(--hairline)] p-[2px]" />
          <div className="leading-tight">
            <div className="font-display font-semibold text-[1.12rem] tracking-[-0.01em]">Yukti</div>
            <div className="text-[0.72rem] text-[var(--ink-2)] whitespace-nowrap">HR &amp; Finance · ONGC</div>
          </div>
        </div>

        <span className="h-6 w-px bg-[var(--hairline)]" />

        <div className="relative" ref={ddRef}>
          <button
            onClick={() => setOpen((o) => !o)}
            aria-haspopup="listbox"
            aria-expanded={open}
            data-testid="persona-button"
            className="flex items-center gap-2 pl-3 pr-2 py-[0.4rem] rounded-full border border-[var(--hairline)] bg-[var(--card)] hover:bg-[var(--surface)] text-[0.85rem] transition-colors"
          >
            <span className="w-2 h-2 rounded-full bg-[#8E000C]" />
            <span className="text-[var(--ink-2)]">Speaking as</span>
            <span className="font-semibold">{active.label}</span>
            <ChevronDown className={`w-4 h-4 text-[var(--ink-3)] transition-transform ${open ? 'rotate-180' : ''}`} />
          </button>
          {open && (
            <div role="listbox" className="absolute left-0 top-[calc(100%+0.5rem)] w-[18rem] rounded-[1rem] border border-[var(--hairline)] bg-[var(--card)] shadow-[var(--panel-shadow)] p-1.5 z-50">
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
                    className={`w-full text-left px-3 py-2 rounded-[0.7rem] flex items-center justify-between gap-3 transition-colors ${sel ? 'bg-[var(--accent-pale)]' : 'hover:bg-[var(--surface)]'}`}
                  >
                    <span className="min-w-0">
                      <span className="block text-[0.88rem] font-semibold">
                        {p.label}
                        {p.name && <span className="font-normal text-[var(--ink-2)]"> · {p.name}</span>}
                      </span>
                      <span className="block text-[0.75rem] text-[var(--ink-2)]">{p.role}</span>
                    </span>
                    {sel && <Check className="w-4 h-4 text-[var(--accent)] shrink-0" />}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Interaction state (always visible) */}
      <div
        data-testid="voice-state"
        data-state={state}
        className="hidden md:flex items-center gap-2 px-3.5 py-[0.35rem] rounded-full bg-[var(--surface)] border border-[var(--hairline)] text-[0.82rem] max-w-[34vw]"
      >
        {state === 'listening' && micLevel ? (
          <LevelMeter level={micLevel} active className={dotColor} />
        ) : (
          <span className={`w-2 h-2 rounded-full bg-current ${dotColor} ${state !== 'idle' ? 'animate-pulse' : ''}`} />
        )}
        <span className="font-medium">{STATE_LABEL[state]}</span>
        {statusLine && state === 'thinking' && <span className="text-[var(--ink-2)] truncate">· {statusLine}</span>}
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {demo && (
          <div className="flex items-center gap-1 rounded-full bg-[var(--surface)] border border-[var(--hairline)] p-0.5 text-[0.78rem]" title="Demo script (← / →)">
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
        <button
          onClick={onToggleLiveMode}
          data-testid="connection-pill"
          title={isLiveMode ? 'Connected to the live agent. Click to use offline demo answers.' : 'Using offline demo answers. Click to go live.'}
          className={`flex items-center gap-1.5 px-3 py-[0.35rem] rounded-full text-[0.8rem] font-medium transition-colors ${conn.cls}`}
        >
          <span className={`w-2 h-2 rounded-full ${conn.dot}`} />
          {conn.label}
        </button>
        <button onClick={onLanguageToggle} className="flex items-center gap-1.5 px-3 py-[0.35rem] rounded-full border border-[var(--hairline)] text-[0.8rem] font-medium hover:bg-[var(--surface)]" title="Answer language">
          <Languages className="w-4 h-4 text-[var(--accent)]" />
          {language === 'hi' ? 'हिन्दी' : language === 'hi-en' ? 'Hinglish' : 'English'}
        </button>
        <button onClick={onThemeToggle} className="icon-btn border border-[var(--hairline)] !rounded-full" aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'} data-testid="theme-toggle">
          {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
      </div>
    </header>
  );
};
