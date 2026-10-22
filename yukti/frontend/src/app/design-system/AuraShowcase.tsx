'use client';

/**
 * AI Aura prototype (Verbatim 16): feathery, rotating Google-hue light for AI-presence elements only.
 * Rendered on /design-system for sponsor review before it is used in U4 (ask bar, greeting) and U3 (orb).
 */
import React from 'react';
import { Mic, Sparkles, ArrowUp } from 'lucide-react';
import { Card, CardHeader, CardBody } from '@/components/ui/primitives';
import { VoiceOrb, OrbState } from '@/components/VoiceOrb';

type AuraState = 'idle' | 'listening' | 'thinking';

function AskBar({ state, label }: { state: AuraState; label: string }) {
  return (
    <div className="space-y-2">
      <div className="text-caption uppercase tracking-[0.08em] text-[var(--ink-3)]">{label}</div>
      <div data-aura={state} className="yk-aura-ring rounded-pill">
       <div className="yk-aura-surface rounded-pill flex items-center gap-3 pl-5 pr-2 py-2 bg-[var(--card)] border border-[var(--hairline)]">
        <span className="flex-1 text-body text-[var(--ink-3)]">
          {state === 'listening' ? 'Listening…' : state === 'thinking' ? 'Yukti is thinking…' : 'Ask Yukti anything about HR, Finance or policy'}
        </span>
        <span className="inline-grid place-items-center w-9 h-9 rounded-full text-[var(--ink-2)]">
          <Mic className="w-[1.1rem] h-[1.1rem]" />
        </span>
        <span className="inline-grid place-items-center w-9 h-9 rounded-full bg-[var(--surface-2)] text-[var(--ink-2)]">
          <ArrowUp className="w-[1.1rem] h-[1.1rem]" />
        </span>
       </div>
      </div>
    </div>
  );
}

export function AuraShowcase({ isDark = false }: { isDark?: boolean }) {
  return (
    <Card as="section" data-testid="ds-aura">
      <CardHeader
        eyebrow="AI presence · prototype"
        title="AI Aura"
        subtitle="Google brand hues rendered as feathery light, used only where Yukti is present or thinking. Never on data, page backgrounds or text."
      />
      <CardBody className="space-y-10">
        {/* 1. Greeting with bloom */}
        <div data-testid="ds-aura-greeting" className="relative overflow-hidden rounded-card border border-[var(--hairline)] bg-[var(--card)] px-10 py-14">
          <div className="yk-aura-bloom" aria-hidden />
          <div className="relative text-center space-y-3">
            <div className="inline-flex items-center gap-2 text-label text-[var(--ink-2)]">
              <Sparkles className="w-4 h-4" /> Yukti · HR &amp; Finance
            </div>
            <h2 className="text-display font-display text-[var(--ink)]">Hello, I am Yukti</h2>
            <p className="text-body text-[var(--ink-2)]">Your HR and Finance agent. How can I help, Chairman?</p>
          </div>
        </div>

        {/* 2. Ask bar in three states */}
        <div data-testid="ds-aura-askbar" className="grid gap-8 md:grid-cols-3">
          <AskBar state="idle" label="Idle · slow drift" />
          <AskBar state="listening" label="Listening · gentle sweep" />
          <AskBar state="thinking" label="Thinking · faster sweep" />
        </div>

        {/* 3. Infinity-ribbon voice orb in its four states (U3) */}
        <div data-testid="ds-orb-states" className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {(['idle', 'listening', 'thinking', 'speaking'] as OrbState[]).map((st) => (
            <div key={st} className="flex flex-col items-center gap-2 rounded-card border border-[var(--hairline)] bg-[var(--card)] py-6">
              <VoiceOrb state={st} isDark={isDark} size={150} interactive={false} />
              <span className="text-label capitalize text-[var(--ink-2)]">{st}</span>
            </div>
          ))}
        </div>

        {/* 3. Orb placeholder glow (final ribbon orb arrives in U3) */}
        <div data-testid="ds-aura-orb" className="flex items-center gap-10">
          <div data-aura="listening" className="yk-aura-ring rounded-full w-24 h-24">
            <div className="yk-aura-surface rounded-full w-full h-full bg-[var(--card)] grid place-items-center border border-[var(--hairline)]">
              <Sparkles className="w-7 h-7 text-[var(--ink-2)]" />
            </div>
          </div>
          <p className="text-body text-[var(--ink-2)] max-w-xl">
            Orb halo preview. In U3 the calm infinity-ribbon orb takes these same aura hues, intensifying while listening and speaking.
          </p>
        </div>
      </CardBody>
    </Card>
  );
}
