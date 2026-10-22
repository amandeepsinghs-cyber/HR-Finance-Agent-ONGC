'use client';

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
    { icon: Activity, tag: 'People · Growth', title: 'Where did headcount grow the most?', q: 'Which areas saw the most headcount increase in the last 5 years, and which saw none?' },
    { icon: TrendingUp, tag: 'Finance · FY26', title: 'Most profitable and loss-making fields', q: 'Which fields or assets were the most profitable and which made losses in FY26?' },
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
STARTERS.E3_FIN = STARTERS.E2_HR;

const ADDRESS: Record<string, string> = { CMD: 'Chairman', DIR_HR: 'Director', DIR_FIN: 'Director', E2_HR: 'Pooja', E3_FIN: 'Rajesh' };

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
}> = ({ onSelect, onTalk, isMicActive, orbState = 'idle', isDark = false, audioEngine, messages = [], liveInterimText, persona = 'CMD' }) => {
  const lastTurn = messages[messages.length - 1];
  const starters = STARTERS[persona] || STARTERS.CMD;
  // Time-aware greeting computed on the client after mount (server render may run in UTC).
  const [hello, setHello] = useState('Hello');
  useEffect(() => setHello(greetingWord()), []);
  // Orb scales with the fluid type scale (rem), so it keeps its proportion on 4K / big screens.
  const [orbPx, setOrbPx] = useState(156);
  useEffect(() => {
    const fit = () => {
      const rem = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
      setOrbPx(Math.round(Math.min(300, Math.max(140, rem * 9.75))));
    };
    fit();
    window.addEventListener('resize', fit);
    return () => window.removeEventListener('resize', fit);
  }, []);
  const name = ADDRESS[persona] || 'Chairman';

  return (
    <div className="relative flex-1 flex flex-col items-center justify-center text-center px-6 pt-6 pb-36 w-full" data-testid="greeting">
      {/* AI aura bloom (D-16): feathery light behind Yukti's presence only */}
      <div className="pointer-events-none absolute -inset-x-16 -top-10 h-[80%] [mask-image:radial-gradient(ellipse_at_center,black_35%,transparent_72%)] [-webkit-mask-image:radial-gradient(ellipse_at_center,black_35%,transparent_72%)]" aria-hidden>
        <div className="yk-aura-bloom" />
      </div>

      <div className="relative flex flex-col items-center max-w-[60rem] w-full">
        <div data-testid="greeting-talk" className="cursor-pointer">
          <VoiceOrb
            state={orbState}
            isDark={isDark}
            size={orbPx}
            onClick={onTalk}
            audioEngine={audioEngine}
            label={isMicActive ? 'Stop listening' : 'Start talking to Yukti'}
            pressed={!!isMicActive}
          />
        </div>

        <h1 className="mt-6 text-display font-display text-[var(--ink)]">
          {hello}, {name}
        </h1>
        <p className="mt-2 text-body text-[var(--ink-2)]">I&apos;m Yukti, your HR &amp; Finance agent. Ask by voice or type below.</p>

        {liveInterimText ? (
          <p className="mt-5 text-body text-[var(--ink-2)] max-w-[44rem] animate-pulse">&ldquo;{liveInterimText}&rdquo;</p>
        ) : lastTurn ? (
          <p className="mt-5 text-body text-[var(--ink-2)] max-w-[42rem]">{lastTurn.text}</p>
        ) : null}

        <div className="mt-10 grid w-full gap-3 grid-cols-1 sm:grid-cols-2 xl:grid-cols-4" data-testid="starter-cards">
          {starters.map((c) => {
            const Icon = c.icon;
            return (
              <Card
                key={c.title}
                as={'button' as any}
                variant="glass"
                onClick={() => onSelect?.(c.q)}
                className="group text-left px-5 py-4 transition duration-fast hover:-translate-y-0.5 hover:border-[var(--accent-soft)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent)]"
              >
                <span className="flex items-center gap-2 text-caption uppercase tracking-[0.06em] text-[var(--ink-3)]">
                  <Icon className="w-3.5 h-3.5 text-[var(--accent-deep)] dark:text-[var(--accent-soft)]" />
                  {c.tag}
                </span>
                <span className="mt-2 block text-label font-semibold text-[var(--ink)] leading-snug group-hover:text-[var(--accent-deep)] dark:group-hover:text-[var(--accent-soft)]">
                  {c.title}
                </span>
              </Card>
            );
          })}
        </div>
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
          onNavigateToAlternative={() => onNavigateToAlternative?.(latest.contract?.access?.alternative)}
        />
      ) : null}
    </div>
  );
};
