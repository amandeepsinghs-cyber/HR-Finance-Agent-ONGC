'use client';

import React, { useState } from 'react';
import { PersonaType } from '@/contracts/answerContract';
import { OrbState } from './VoiceOrb';
import {
  Sun,
  Moon,
  ChevronDown,
  User,
  Activity,
  Languages,
  Sparkles,
  Play,
  SkipForward,
  SkipBack,
} from 'lucide-react';

interface TopBarProps {
  currentPersona: PersonaType;
  onPersonaChange: (p: PersonaType) => void;
  isDark: boolean;
  onThemeToggle: () => void;
  language: 'en' | 'hi' | 'hi-en';
  onLanguageToggle: () => void;
  state: OrbState;
  onPrevDemo?: () => void;
  onNextDemo?: () => void;
  currentDemoIndex?: number;
  totalDemos?: number;
  isLiveMode?: boolean;
  onToggleLiveMode?: () => void;
  backendHealthy?: boolean;
}

const PERSONAS: { id: PersonaType; label: string; role: string; name?: string }[] = [
  { id: 'CMD', label: 'CMD', role: 'Chairman & CEO' },
  { id: 'DIR_HR', label: 'Dir HR', role: 'Director (HR)' },
  { id: 'DIR_FIN', label: 'Dir Fin', role: 'Director (Finance)' },
  { id: 'E2_HR', label: 'E2 · HR', role: 'Assistant Manager (HR)', name: 'Pooja Verma' },
  { id: 'E3_FIN', label: 'E3 · Fin', role: 'Deputy Manager (Finance)', name: 'Rajesh Kulkarni' },
];

export const TopBar: React.FC<TopBarProps> = ({
  currentPersona,
  onPersonaChange,
  isDark,
  onThemeToggle,
  language,
  onLanguageToggle,
  state,
  onPrevDemo,
  onNextDemo,
  currentDemoIndex = 0,
  totalDemos = 12,
  isLiveMode = true,
  onToggleLiveMode,
  backendHealthy = true,
}) => {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const activeObj = PERSONAS.find((p) => p.id === currentPersona) || PERSONAS[0];

  return (
    <header className="w-full h-16 border-b border-border-light dark:border-border-dark bg-white/95 dark:bg-canvas-dark/95 backdrop-blur-md px-6 flex items-center justify-between z-30 select-none transition-colors">
      {/* Left: ONGC Mark + Yukti AI Brand */}
      <div className="flex items-center gap-4">
        {/* Official ONGC Corporate Logo */}
        <div className="flex items-center gap-2.5">
          <div
            title="Oil and Natural Gas Corporation Limited (Official Logo)"
            className="w-10 h-10 rounded-xl bg-white p-1 flex items-center justify-center shadow-xs ring-1 ring-zinc-200 dark:ring-zinc-700 shrink-0"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/brand/ongc_logo.png"
              alt="ONGC Logo"
              className="w-full h-full object-contain"
            />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-display font-bold text-lg tracking-tight text-zinc-900 dark:text-zinc-50">
                Yukti AI
              </span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase bg-accent/10 text-accent dark:bg-accent/20">
                v1.0
              </span>
            </div>
            <div className="text-[11px] font-medium text-zinc-500 dark:text-zinc-400 leading-none">
              HR & Finance Executive Intelligence
            </div>
          </div>
        </div>

        <div className="h-6 w-[1px] bg-zinc-200 dark:bg-zinc-800 mx-1 hidden sm:block" />

        {/* Persona Selector Dropdown */}
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-zinc-200 dark:border-zinc-700/80 hover:border-accent text-xs font-semibold bg-zinc-50 dark:bg-zinc-800/80 text-zinc-800 dark:text-zinc-200 transition-all shadow-sm"
          >
            <span className="w-2 h-2 rounded-full bg-ongc-maroon" />
            <span>Role:</span>
            <span className="text-accent font-bold">{activeObj.label}</span>
            <ChevronDown className="w-3.5 h-3.5 text-zinc-400" />
          </button>

          {dropdownOpen && (
            <div className="absolute top-full left-0 mt-2 w-72 rounded-2xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 shadow-2xl py-2 z-50 animate-in fade-in zoom-in-95 duration-150">
              <div className="px-3 py-1 text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                Select Active Persona
              </div>
              {PERSONAS.map((p) => {
                const isSelected = p.id === currentPersona;
                return (
                  <button
                    key={p.id}
                    onClick={() => {
                      onPersonaChange(p.id);
                      setDropdownOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2 text-xs flex items-center justify-between transition-colors ${
                      isSelected
                        ? 'bg-blue-50 dark:bg-zinc-800 text-accent font-bold'
                        : 'hover:bg-zinc-100 dark:hover:bg-zinc-800/60 text-zinc-700 dark:text-zinc-300'
                    }`}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold">{p.label}</span>
                        {p.name && <span className="text-zinc-400 text-[11px]">— {p.name}</span>}
                      </div>
                      <div className="text-[10px] text-zinc-400 font-normal">{p.role}</div>
                    </div>
                    {isSelected && <span className="w-2 h-2 rounded-full bg-accent" />}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Center: Live Interaction State Pill */}
      <div className="hidden md:flex items-center gap-2 px-3.5 py-1 rounded-full border border-zinc-200/80 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/60 text-xs">
        <span
          className={`w-2 h-2 rounded-full ${
            state === 'listening'
              ? 'bg-emerald-500 animate-pulse'
              : state === 'thinking'
              ? 'bg-amber-500 animate-spin'
              : state === 'speaking'
              ? 'bg-accent animate-pulse'
              : 'bg-zinc-400'
          }`}
        />
        <span className="text-zinc-500 dark:text-zinc-400 font-medium capitalize">
          Voice: {state}
        </span>
      </div>

      {/* Right Controls: Demo Player, Language, Theme */}
      <div className="flex items-center gap-3">
        {/* Demo Script Player Controls */}
        <div className="flex items-center gap-1 bg-zinc-100 dark:bg-zinc-800/70 p-1 rounded-xl text-xs">
          <button
            onClick={onPrevDemo}
            title="Previous Scenario"
            className="p-1 rounded-lg hover:bg-white dark:hover:bg-zinc-700 text-zinc-600 dark:text-zinc-300 transition-colors"
          >
            <SkipBack className="w-3.5 h-3.5" />
          </button>
          <span className="px-2 font-mono text-[11px] font-semibold text-zinc-700 dark:text-zinc-300">
            {currentDemoIndex + 1}/{totalDemos}
          </span>
          <button
            onClick={onNextDemo}
            title="Next Scenario (Spacebar)"
            className="p-1 rounded-lg hover:bg-white dark:hover:bg-zinc-700 text-zinc-600 dark:text-zinc-300 transition-colors"
          >
            <SkipForward className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Live ADK Backend / Mock Mode Toggle */}
        {onToggleLiveMode && (
          <button
            onClick={onToggleLiveMode}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all shadow-xs ${
              isLiveMode
                ? backendHealthy
                  ? 'bg-emerald-50 dark:bg-emerald-950/60 border-emerald-300 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300'
                  : 'bg-rose-50 dark:bg-rose-950/60 border-rose-300 dark:border-rose-800 text-rose-700 dark:text-rose-300'
                : 'bg-amber-50 dark:bg-amber-950/60 border-amber-300 dark:border-amber-800 text-amber-700 dark:text-amber-300'
            }`}
            title={isLiveMode ? 'Live Backend Connected — click to switch to Mock Mode' : 'Mock Mode Active — click to switch to Live Backend'}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isLiveMode
                  ? backendHealthy
                    ? 'bg-emerald-500'
                    : 'bg-rose-500 animate-pulse'
                  : 'bg-amber-500'
              }`}
            />
            <span>
              {isLiveMode
                ? backendHealthy
                  ? 'Live ADK'
                  : 'Offline (Click for Mock)'
                : 'Mock Mode'}
            </span>
          </button>
        )}

        {/* Language Switcher */}
        <button
          onClick={onLanguageToggle}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border border-zinc-200 dark:border-zinc-700 text-xs font-semibold hover:border-accent transition-colors bg-white dark:bg-zinc-800 text-zinc-700 dark:text-zinc-200"
          title="Toggle Language (EN / हिन्दी)"
        >
          <Languages className="w-3.5 h-3.5 text-accent" />
          <span>{language === 'hi' ? 'हि' : language === 'hi-en' ? 'EN|हि' : 'EN'}</span>
        </button>

        {/* Light / Dark Mode Toggle */}
        <button
          onClick={onThemeToggle}
          className="p-2 rounded-xl border border-zinc-200 dark:border-zinc-700 hover:border-accent transition-colors text-zinc-700 dark:text-zinc-200 bg-white dark:bg-zinc-800"
          title={`Switch to ${isDark ? 'Light' : 'Dark'} Mode`}
        >
          {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-zinc-700" />}
        </button>
      </div>
    </header>
  );
};
