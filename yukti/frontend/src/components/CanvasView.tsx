'use client';

import { altQuestion } from '@/personas';
import { PERSONA_DIRECTORY } from '@/personas';
import React, { useEffect, useState } from 'react';
import { VoiceOrb, OrbState } from './VoiceOrb';
import { VoiceAudioEngine } from '@/services/audioAnalyser';
import { ChatMessage } from './FloatingConversationPanel';
import { ConversationFeed } from './ConversationFeed';
import { AnswerCard } from './AnswerCard';
import type { Turn } from '@/state/feed';
import type { SpecPatch, VisualContainer } from '@/contracts/answerContract';
import { latestAnswered } from '@/state/feed';
import { Users, TrendingUp, Target, Scale, BarChart3, Activity } from 'lucide-react';
import { Card } from './ui/primitives';

interface CanvasViewProps {
  /** conversation feed (U2.2); empty = greeting */
  turns: Turn[];
  isDark?: boolean;
  onNavigateToAlternative?: (q?: string) => void;
  onSelectStarter?: (q: string) => void;
  onAsk?: (q: string, specPatch?: SpecPatch) => void;
  onRetry?: (q: string, turnId?: string) => void;
  onNewSession?: () => void;
  onReplot?: (turnId: string, visual: VisualContainer) => void;
  busy?: boolean;
  statusLine?: string | null;
  onTalk?: () => void;
  isMicActive?: boolean;
  orbState?: OrbState;
  audioEngine?: VoiceAudioEngine;
  messages?: ChatMessage[];
  liveInterimText?: string;
  /** active persona: drives the greeting name and suggestion cards (U4.5) */
  persona?: string;
}

/** Feed is on unless explicitly disabled (NEXT_PUBLIC_FEED_V2=0 falls back to the single-answer canvas). */
const FEED_V2 = process.env.NEXT_PUBLIC_FEED_V2 !== '0';

type Starter = { icon: React.ComponentType<{ className?: string }>; tag: string; title: string; q: string };

// U4.5: persona-specific suggestions (HR · HR · Finance · Policy). E-level personas get aggregate/self-service asks (D-11).
const STARTERS: Record<string, Starter[]> = {
  CMD: [
    { icon: Users, tag: 'People · Transfers', title: 'Delhi HQ: executives posted 5+ years', q: 'How many executives have been posted in Delhi for 5 years or more?' },
    { icon: TrendingUp, tag: 'Finance · FY26', title: 'Most profitable and loss-making fields', q: 'Which fields or assets were the most profitable and which made losses in FY26?' },
    { icon: Target, tag: 'Performance · DPE', title: 'MoU target scorecard', q: 'How are we tracking against our MoU targets with MoPNG/DPE for this year?' },
    { icon: Scale, tag: 'Policy', title: 'Station tenure and rotation rules', q: 'What is the minimum tenure at a station, and the maximum cumulative stay in one city?' },
  ],
  DIR_HR: [
    { icon: Users, tag: 'People · Transfers', title: 'Delhi HQ: 5+ year postings', q: 'How many executives have been posted in Delhi for 5 years or more?' },
    { icon: Target, tag: 'People · Succession', title: 'E7+ retiring in 3 years without a successor', q: 'How many E7+ officers retire in the next 3 years, and which roles have no ready successor?' },
    { icon: TrendingUp, tag: 'Finance · People cost', title: 'Payroll and overtime by work centre', q: 'What is the FY26 payroll and overtime cost by work centre?' },
    { icon: Scale, tag: 'Policy', title: 'Transfer policy for long-stay officers', q: 'What does the transfer policy say about officers posted 5 years or more?' },
  ],
  DIR_FIN: [
    { icon: TrendingUp, tag: 'Finance · FY26', title: 'Most profitable and loss-making fields', q: 'Which fields or assets were the most profitable and which made losses in FY26?' },
    { icon: BarChart3, tag: 'Finance · Capex', title: 'Under-invested fields vs reserves', q: 'Where have we invested the most capex in the last 5 years, and which fields are under-invested relative to their reserves?' },
    { icon: Target, tag: 'Performance · DPE', title: 'MoU target scorecard', q: 'How are we tracking against our MoU targets with MoPNG/DPE for this year?' },
    { icon: Scale, tag: 'Receivables', title: 'Receivables ageing by customer', q: 'How old are receivables from oil marketing companies and gas buyers, by customer?' },
  ],
  E2_HR: [
    { icon: Scale, tag: 'Policy', title: 'My leave entitlements', q: 'What leave am I entitled to under the ONGC leave rules?' },
    { icon: Scale, tag: 'Policy', title: 'Station tenure norms', q: 'What is the minimum tenure at a station, and the maximum cumulative stay in one city?' },
    { icon: Users, tag: 'People · Aggregate', title: 'Headcount by work centre', q: 'What is the headcount by work centre?' },
    { icon: TrendingUp, tag: 'Finance · Public', title: 'ONGC FY26 revenue and profit', q: 'What were ONGC revenue and profit in FY26?' },
  ],
};
// P2H.2: E1–E4 in HR and Finance share the junior starters (aggregate / self-service asks, D-11)
for (const id of ['E1_HR', 'E3_HR', 'E4_HR', 'E1_FIN', 'E2_FIN', 'E3_FIN', 'E4_FIN']) STARTERS[id] = STARTERS.E2_HR;

const ADDRESS: Record<string, string> = Object.fromEntries(PERSONA_DIRECTORY.map((p) => [p.id, p.address]));

function greetingWord(): string {
  const h = new Date().getHours();
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
}

const Greeting: React.FC<{
  onSelect?: (q: string) => void;
  onTalk?: () => void;
  isMicActive?: boolean;
  orbState?: OrbState;
  isDark?: boolean;
  audioEngine?: VoiceAudioEngine;
  messages?: ChatMessage[];
  liveInterimText?: string;
  persona?: string;
}> = ({ onSelect, onTalk, isMicActive, orbState = 'idle', isDark = false, audioEngine, messages = [], liveInterimText, persona }) => {
  const lastTurn = messages[messages.length - 1];
  // P2H.2 G4 M3: unknown / not-signed-in persona gets no starter questions (never the CMD set)
  const starters = (persona && STARTERS[persona]) || [];
  // Time-aware greeting computed on the client after mount (server render may run in UTC).
  const [hello, setHello] = useState('Hello');
  useEffect(() => setHello(greetingWord()), []);
  // Orb scales with the fluid type scale (rem), so it keeps its proportion on 4K / big screens.
  const [orbPx, setOrbPx] = useState(236);
  useEffect(() => {
    const fit = () => {
      const rem = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
      // aurora wave on the greeting (≈ 236 px at 1440p, scales on 4K); sponsor preferred this over the 288 px trial (26-Oct)
      setOrbPx(Math.round(Math.min(420, Math.max(200, rem * 14.75))));
    };
    fit();
    window.addEventListener('resize', fit);
    return () => window.removeEventListener('resize', fit);
  }, []);
  const name = (persona && ADDRESS[persona]) || ''; // M3: no CMD name for an unknown persona

  return (
    <div className="relative flex-1 flex flex-col items-center justify-between text-center px-6 pt-4 pb-32 w-full min-h-[calc(100vh-14.5rem)]" data-testid="greeting">
      {/* AI aura bloom (D-16): feathery pastel light behind Yukti's presence only (static per D-25) */}
      <div className="pointer-events-none absolute -inset-x-16 -top-10 h-[80%] [mask-image:radial-gradient(ellipse_at_center,black_35%,transparent_72%)] [-webkit-mask-image:radial-gradient(ellipse_at_center,black_35%,transparent_72%)]" aria-hidden>
        <div className="yk-aura-bloom" />
      </div>

      <div className="relative my-auto flex flex-col items-center max-w-[60rem] w-full">
        {/* FEAT-004 / V12 / D-29: centre-stage "Aurora wave" voice orb above the greeting (the sponsor-selected design,
            restored 26-Oct after the 23-Oct WIP snapshot swapped it for a cloud sphere; refs in docs/design_refs/aurora_wave).
            Tap to talk; it reflects listening / thinking / speaking via orbState + the live audio engine. */}
        <div className="relative flex flex-col items-center" data-testid="greeting-talk">
          <VoiceOrb
            state={orbState}
            isDark={isDark}
            size={orbPx}
            onClick={onTalk}
            audioEngine={audioEngine}
            label={orbState === 'speaking' ? 'Stop Yukti speaking' : isMicActive ? 'Stop listening' : 'Start talking to Yukti'}
            pressed={!!isMicActive}
          />
        </div>

        <h1 className="mt-6 text-display font-display text-[var(--ink)]">
          {name ? `${hello}, ${name}` : hello}
        </h1>
        <p className="mt-2 text-body text-[var(--ink-2)]">I&apos;m Yukti, your HR &amp; Finance agent. Ask by voice or type below.</p>

        {liveInterimText ? (
          <p className="mt-5 text-body text-[var(--ink-2)] max-w-[44rem] animate-pulse">&ldquo;{liveInterimText}&rdquo;</p>
        ) : lastTurn ? (
          <p className="mt-5 text-body text-[var(--ink-2)] max-w-[42rem]">{lastTurn.text}</p>
        ) : null}
      </div>

      <div className="relative mt-auto pt-8 w-full max-w-[54rem] flex flex-col items-center gap-1.5" data-testid="starter-cards">
        {starters.slice(0, 3).map((c) => (
          <button
            key={c.title}
            type="button"
            onClick={() => onSelect?.(c.q)}
            className="text-center px-3 py-1 text-caption font-normal text-[var(--ink-3)] hover:text-[var(--ink-2)] transition-colors duration-fast focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent)]"
          >
            {c.q}
          </button>
        ))}
      </div>
    </div>
  );
};

export const CanvasView: React.FC<CanvasViewProps> = ({
  turns,
  isDark = false,
  onNavigateToAlternative,
  onSelectStarter,
  onAsk,
  onRetry,
  onNewSession,
  onReplot,
  busy,
  statusLine,
  onTalk,
  isMicActive,
  orbState = 'idle',
  audioEngine,
  messages = [],
  persona,
  liveInterimText,
}) => {
  const latest = latestAnswered(turns);
  return (
    <div className={`min-h-full flex flex-col px-[2.25rem] pt-[1.25rem] ${turns.length ? 'pb-[2.5rem]' : 'pb-[9.5rem]'} gap-[1.15rem] max-w-[104rem] mx-auto w-full`} data-testid="canvas">
      {busy && <div className="fixed left-0 right-0 top-[var(--topbar-h)] h-[2px] yk-shimmer z-20" aria-hidden />}

      {turns.length === 0 ? (
        <Greeting
          onSelect={onSelectStarter}
          onTalk={onTalk}
          isMicActive={isMicActive}
          orbState={orbState}
          isDark={isDark}
          audioEngine={audioEngine}
          messages={messages}
          liveInterimText={liveInterimText}
          persona={persona}
        />
      ) : FEED_V2 ? (
        <ConversationFeed
          turns={turns}
          isDark={isDark}
          persona={persona}
          statusLine={statusLine}
          liveInterimText={liveInterimText}
          onAsk={onAsk}
          onRetry={onRetry}
          onNewSession={onNewSession}
          onReplot={onReplot}
          onNavigateToAlternative={onNavigateToAlternative}
        />
      ) : latest?.contract ? (
        <AnswerCard
          key={latest.id}
          contract={latest.contract}
          isDark={isDark}
          persona={persona}
          fresh={latest.fresh}
          isLatest
          onAsk={onAsk}
          onReplot={onReplot ? (v) => onReplot(latest.id, v) : undefined}
          onNavigateToAlternative={() => onNavigateToAlternative?.(altQuestion(latest.contract?.access?.alternative))}
        />
      ) : null}
    </div>
  );
};
