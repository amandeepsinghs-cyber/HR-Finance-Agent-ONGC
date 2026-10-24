'use client';

import { PERSONA_DIRECTORY, personaInfo } from '@/personas';
import { PersonaPicker } from './PersonaPicker';
import React, { useEffect, useRef, useState } from 'react';
import { PersonaType } from '@/contracts/answerContract';
import { OrbState } from './VoiceOrb';
import { Sun, Moon, ChevronDown, SkipBack, SkipForward, Languages } from 'lucide-react';
import { IconButton } from './ui/primitives';

interface TopBarProps {
  /** null = not signed in (P2H.2 G4 M2/M3): the button reads "Sign in as…" and never shows CMD */
  currentPersona: PersonaType | null;
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

// P2H.2: persona labels come from the shared directory (11 personas, D-41/D-60); the server is the source of truth.
export const PERSONAS = PERSONA_DIRECTORY.map((p) => ({ id: p.id, label: p.short, role: p.designation, name: p.display_name }));

const STATE_LABEL: Record<OrbState, string> = {
  idle: 'Ready',
  listening: 'Listening',
  thinking: 'Thinking',
  speaking: 'Speaking',
};

/** Five-bar live level meter driven by the mic RMS. */
export const LevelMeter: React.FC<{ level: () => number; active: boolean; size?: 'sm' | 'lg'; className?: string }> = ({
  level,
  active,
  size = 'sm',
  className = '',
}) => {
  const refs = useRef<(HTMLSpanElement | null)[]>([]);
  useEffect(() => {
    if (!active) return;
    let raf = 0;
    const weights = [0.55, 0.88, 1, 0.82, 0.52];
    const loop = (now: number) => {
      const lv = level();
      refs.current.forEach((el, i) => {
        if (!el) return;
        const jitter = 0.85 + Math.random() * 0.3;
        const gentleWave = 0.24 + 0.14 * Math.abs(Math.sin(now * 0.0065 + i * 0.95));
        const h = Math.max(gentleWave, Math.min(1, (lv * 2.1 + 0.15) * weights[i] * jitter));
        el.style.transform = `scaleY(${h})`;
      });
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [active, level]);
  const boxCls = size === 'lg' ? 'gap-[3px] h-[1.35rem]' : 'gap-[2px] h-[0.95rem]';
  const barCls = size === 'lg' ? 'w-[3.5px]' : 'w-[3px]';
  return (
    <span className={`inline-flex items-center ${boxCls} ${className}`} aria-hidden data-testid="level-meter">
      {[0, 1, 2, 3, 4].map((i) => (
        <span
          key={i}
          ref={(el) => {
            refs.current[i] = el;
          }}
          className={`${barCls} h-full rounded-full bg-current origin-center transition-transform duration-75`}
          style={{ transform: 'scaleY(0.25)' }}
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
  const active = currentPersona ? personaInfo(currentPersona) : undefined;

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
      {/* Brand — ONGC official website scale (80px emblem + Yukti AI Agent / HR and Finance in ONGC Red) */}
      <div className="flex items-center gap-4 min-w-0 flex-1 py-1">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/brand/ongc_logo.png"
          alt="Oil and Natural Gas Corporation Limited"
          className="w-[4.5rem] h-[4.5rem] xl:w-[5rem] xl:h-[5rem] shrink-0 rounded-[var(--radius-sm)] object-cover shadow-[var(--card-shadow)]"
        />
        <div className="min-w-0 flex flex-col justify-center leading-tight space-y-0.5">
          <div className="flex items-baseline gap-1.5 flex-wrap leading-none">
            <span className="font-display font-bold text-[1.35rem] xl:text-[1.5rem] tracking-[-0.02em] text-[var(--brand-red)] leading-none">
              Yukti AI Agent ,
            </span>
            <span className="text-[0.88rem] xl:text-[0.95rem] font-semibold tracking-[0.01em] text-[var(--brand-red-deep)] whitespace-nowrap leading-none">
              HR and Finance
            </span>
          </div>
          <div className="text-[0.76rem] font-medium text-[var(--ink-2)] truncate leading-tight pt-0.5">
            Oil and Natural Gas Corporation Limited
          </div>
          <div className="text-[0.76rem] text-[var(--ink-3)] font-normal truncate leading-tight">
            A Maharatna Company
          </div>
        </div>
      </div>

      {/* Right: state pill (Ready · Live) · role · language · theme */}
      <div className="flex items-center justify-end gap-2 shrink-0">
        <div
          data-testid="voice-state"
          data-state={state}
          role="status"
          aria-live="polite"
          className="flex items-center gap-2 pl-2 pr-1.5 py-1 rounded-pill bg-[var(--surface)] border border-[var(--hairline)] text-label"
        >
          <span data-aura={auraState} className="yk-aura-ring rounded-full w-6 h-6 shrink-0">
            <span className={`yk-aura-surface rounded-full w-full h-full grid place-items-center bg-[var(--card)] ${stateTone}`}>
              {state === 'listening' && micLevel ? <LevelMeter level={micLevel} active className={stateTone} /> : <span className={`w-2 h-2 rounded-full bg-current ${state !== 'idle' ? 'animate-pulse' : ''}`} />}
            </span>
          </span>
          <span className="font-medium text-[var(--ink)]">{STATE_LABEL[state]}</span>
          {statusLine && state === 'thinking' && <span className="text-[var(--ink-2)] truncate font-normal max-w-[14rem]">· {statusLine}</span>}
          <span aria-hidden className="hidden md:block w-px h-4 bg-[var(--hairline)]" />
          <button
            type="button"
            onClick={onToggleLiveMode}
            data-testid="connection-pill"
            aria-label={isLiveMode ? `Connection: ${conn.label}. Switch to offline demo answers` : 'Connection: demo answers. Switch to live agent'}
            title={isLiveMode ? 'Connected to the live agent. Click to use offline demo answers.' : 'Using offline demo answers. Click to go live.'}
            className="flex items-center gap-1.5 px-2 py-0.5 rounded-pill text-[var(--ink-2)] font-normal hover:bg-[var(--surface-2)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent)]"
          >
            <span className={`w-1.5 h-1.5 rounded-full ${connDot}`} />
            {conn.label}
          </button>
        </div>
        <span aria-hidden className="w-px h-5 bg-[var(--hairline)] mx-0.5" />
        {demo && (
          <div className="flex items-center gap-0.5 rounded-pill bg-[var(--surface)] border border-[var(--hairline)] p-0.5 text-caption" title="Demo script (← / →)">
            <IconButton onClick={demo.onPrev} className="!w-7 !h-7 [&>svg]:!w-3.5 [&>svg]:!h-3.5" label="Previous demo answer">
              <SkipBack className="w-3.5 h-3.5" />
            </IconButton>
            <span className="px-1 tabular-nums text-[var(--ink-2)]">
              {demo.index + 1}/{demo.total}
            </span>
            <IconButton onClick={demo.onNext} className="!w-7 !h-7 [&>svg]:!w-3.5 [&>svg]:!h-3.5" label="Next demo answer">
              <SkipForward className="w-3.5 h-3.5" />
            </IconButton>
          </div>
        )}

        <div className="relative" ref={ddRef}>
          <button
            onClick={() => setOpen(true)}
            aria-haspopup="dialog"
            aria-expanded={open}
            data-testid="persona-button"
            title={active ? `Signed in as ${active.display_name}, ${active.designation} (illustrative identity). Click to sign in as another role.` : 'Not signed in. Click to choose a demo identity.'}
            className="flex items-center gap-2 pl-3 pr-2 py-1.5 rounded-pill hover:bg-[var(--surface)] text-label transition-colors"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-ongc-maroon" />
            <span className="font-semibold text-[var(--ink)]">{!active ? 'Sign in as…' : active.tier === 'junior' ? `${active.short} · ${active.display_name}` : active.designation}</span>
            <ChevronDown className="w-4 h-4 text-[var(--ink-3)]" />
          </button>
          <PersonaPicker
            open={open}
            current={currentPersona}
            onClose={() => setOpen(false)}
            onPick={(id) => {
              setOpen(false);
              if (id !== currentPersona) onPersonaChange(id);
            }}
          />
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
