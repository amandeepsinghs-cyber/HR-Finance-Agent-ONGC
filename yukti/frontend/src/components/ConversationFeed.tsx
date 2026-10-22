'use client';

/**
 * ConversationFeed (U2.2–U2.6): the CMD's conversation as a scrolling feed of turn cards
 * (question → answer). The newest card scrolls into view automatically; scrolling up > 100 px pauses
 * that and shows a "Jump to latest" pill. Every historic card stays fully interactive.
 */
import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { AnswerCard } from './AnswerCard';
import type { Turn } from '@/state/feed';
import { cleanText } from '@/charts/format';
import { AlertTriangle, ArrowDown, Mic, Plus, RotateCcw } from 'lucide-react';

interface ConversationFeedProps {
  turns: Turn[];
  isDark?: boolean;
  persona?: string;
  statusLine?: string | null;
  liveInterimText?: string;
  onAsk?: (q: string) => void;
  onRetry?: (q: string, turnId?: string) => void;
  onNewSession?: () => void;
  onNavigateToAlternative?: (q?: string) => void;
}

const timeOf = (ms?: number) => (ms ? new Date(ms).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '');

const QuestionBubble: React.FC<{ turn: Turn }> = ({ turn }) => (
  <div className="flex justify-end" data-testid="turn-question">
    <div className="max-w-[min(48rem,80%)] flex flex-col items-end gap-1">
      <div className="rounded-[1.25rem] rounded-br-[0.4rem] bg-[var(--surface)] border border-[var(--hairline)] px-4 py-2.5 text-body text-[var(--ink)] leading-snug">
        {cleanText(turn.question) || '…'}
      </div>
      <div className="flex items-center gap-1.5 text-label font-normal text-[var(--ink-3)] pr-1">
        {turn.viaVoice && <Mic className="w-3 h-3" aria-label="asked by voice" />}
        <span>{timeOf(turn.askedAt)}</span>
      </div>
    </div>
  </div>
);

const PendingCard: React.FC<{ statusLine?: string | null }> = ({ statusLine }) => (
  <div className="card px-[1.35rem] py-[1.2rem] max-w-[72rem]" data-testid="turn-pending" role="status" aria-live="polite">
    <div className="flex items-center gap-3 text-label text-[var(--ink-2)]">
      <span className="relative inline-flex w-2.5 h-2.5">
        <span className="absolute inset-0 rounded-full bg-[var(--accent)] opacity-60 animate-ping" />
        <span className="relative w-2.5 h-2.5 rounded-full bg-[var(--accent)]" />
      </span>
      {statusLine || 'Yukti is working on it…'}
    </div>
    <div className="mt-4 space-y-2.5" aria-hidden>
      <div className="h-3 rounded-full yk-shimmer w-[62%]" />
      <div className="h-3 rounded-full yk-shimmer w-[86%]" />
      <div className="h-3 rounded-full yk-shimmer w-[44%]" />
    </div>
  </div>
);

const ErrorCard: React.FC<{ turn: Turn; onRetry?: (q: string, turnId?: string) => void }> = ({ turn, onRetry }) => (
  <div className="card px-[1.35rem] py-[1.1rem] max-w-[72rem] border-[var(--maroon-pale)]" data-testid="turn-error" role="alert">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-center gap-2.5 text-label text-[var(--maroon)]">
        <AlertTriangle className="w-4 h-4 shrink-0" aria-hidden />
        {turn.error || 'Something went wrong.'}
      </div>
      {onRetry && (
        <button type="button" className="chip !py-1.5" onClick={() => onRetry(turn.question, turn.id)} data-testid="turn-retry">
          <RotateCcw className="w-3.5 h-3.5" aria-hidden /> Try again
        </button>
      )}
    </div>
  </div>
);

export const ConversationFeed: React.FC<ConversationFeedProps> = ({
  turns,
  isDark = false,
  persona,
  statusLine,
  onAsk,
  onRetry,
  onNewSession,
  onNavigateToAlternative,
}) => {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const scrollerRef = useRef<HTMLElement | null>(null);
  const [following, setFollowing] = useState(true);
  const followingRef = useRef(true);
  const ignoreUntil = useRef(0); // programmatic smooth scrolls don't count as the user scrolling
  const anchorTop = useRef(0); // scrollTop of the latest card when we last brought it into view
  const rafRef = useRef(0);

  const setFollow = (v: boolean) => {
    followingRef.current = v;
    setFollowing(v);
  };

  const scroller = (): HTMLElement | null => {
    if (!scrollerRef.current) scrollerRef.current = (rootRef.current?.closest('main') as HTMLElement) || null;
    return scrollerRef.current;
  };

  const topOf = (el: HTMLElement, sc: HTMLElement) => el.getBoundingClientRect().top - sc.getBoundingClientRect().top + sc.scrollTop - 16;

  const scrollToTurn = useCallback((id: string, smooth = true) => {
    const sc = scroller();
    const el = rootRef.current?.querySelector<HTMLElement>(`[data-turn-id="${CSS.escape(id)}"]`);
    if (!sc || !el) return;
    const top = Math.max(0, topOf(el, sc));
    anchorTop.current = top;
    ignoreUntil.current = performance.now() + (smooth ? 900 : 120);
    sc.scrollTo({ top, behavior: smooth ? 'smooth' : 'auto' });
  }, []);

  // Auto-scroll: bring the newest card (and its answer when it lands) into view while following.
  const last = turns[turns.length - 1];
  const lastKey = last ? `${last.id}:${last.status}` : '';
  const prevLen = useRef(0);
  useLayoutEffect(() => {
    if (!last) return;
    const appended = turns.length > prevLen.current;
    prevLen.current = turns.length;
    if (appended) setFollow(true); // a new question always resumes following
    if (!followingRef.current) return;
    const id = last.id;
    cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => scrollToTurn(id, turns.length > 1));
  }, [lastKey]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => cancelAnimationFrame(rafRef.current), []);

  // Pause when the user scrolls up more than 100 px above the latest card; resume near the bottom.
  useEffect(() => {
    const sc = scroller();
    if (!sc) return;
    const latestTop = () => {
      // computed live: re-plotting a historic card (e.g. into a long table) moves the latest card (G4 #8)
      const cards = rootRef.current?.querySelectorAll<HTMLElement>('[data-turn-id]');
      const el = cards && cards[cards.length - 1];
      return el ? Math.max(0, topOf(el, sc)) : anchorTop.current;
    };
    const onScrollEnd = () => {
      ignoreUntil.current = 0; // the programmatic scroll finished
    };
    const onScroll = () => {
      if (performance.now() < ignoreUntil.current) return;
      anchorTop.current = latestTop();
      const st = sc.scrollTop;
      const nearBottom = sc.scrollHeight - st - sc.clientHeight < 100;
      if (st < anchorTop.current - 100 && !nearBottom) {
        if (followingRef.current) setFollow(false);
      } else if (!followingRef.current && (nearBottom || st >= anchorTop.current - 10)) {
        setFollow(true);
      }
    };
    sc.addEventListener('scroll', onScroll, { passive: true });
    sc.addEventListener('scrollend', onScrollEnd);
    return () => {
      sc.removeEventListener('scroll', onScroll);
      sc.removeEventListener('scrollend', onScrollEnd);
    };
  }, []);

  // Voice/text navigation: "go back" / "next" / "home" scroll between cards (replaces the history strip).
  useEffect(() => {
    const onNav = (e: Event) => {
      const dir = (e as CustomEvent<string>).detail;
      const sc = scroller();
      const cards = Array.from(rootRef.current?.querySelectorAll<HTMLElement>('[data-turn-id]') || []);
      if (!sc || !cards.length) return;
      const viewTop = sc.getBoundingClientRect().top + 80;
      let cur = cards.findIndex((c) => c.getBoundingClientRect().bottom > viewTop);
      if (cur < 0) cur = cards.length - 1;
      const target = dir === 'top' ? 0 : dir === 'latest' ? cards.length - 1 : dir === 'forward' ? Math.min(cards.length - 1, cur + 1) : Math.max(0, cur - 1);
      const id = cards[target].dataset.turnId!;
      if (target === cards.length - 1) setFollow(true);
      else {
        setFollow(false);
      }
      const top = Math.max(0, topOf(cards[target], sc));
      ignoreUntil.current = performance.now() + 900;
      if (target === cards.length - 1) anchorTop.current = top;
      sc.scrollTo({ top, behavior: 'smooth' });
      void id;
    };
    window.addEventListener('yukti:feed-nav', onNav);
    return () => window.removeEventListener('yukti:feed-nav', onNav);
  }, []);

  const jumpToLatest = () => {
    if (!last) return;
    setFollow(true);
    scrollToTurn(last.id);
  };

  const answered = turns.filter((t) => t.status === 'done').length;

  return (
    <div ref={rootRef} className="flex flex-col" data-testid="conversation-feed" data-following={following}>
      <header className="flex items-center justify-between gap-3 pb-2 mb-1 border-b border-[var(--hairline)]">
        <div className="text-label text-[var(--ink-3)]">
          Conversation · {turns.length} {turns.length === 1 ? 'question' : 'questions'}
          {answered < turns.length ? ` · ${turns.length - answered} in progress` : ''}
        </div>
        {onNewSession && (
          <button type="button" onClick={onNewSession} className="chip !py-1.5 !text-label" data-testid="new-session" title="Start a fresh conversation (clears context)">
            <Plus className="w-3.5 h-3.5" aria-hidden /> New conversation
          </button>
        )}
      </header>

      <div className="flex flex-col gap-[2.75rem] pt-5">
        {turns.map((t, i) => {
          const isLast = i === turns.length - 1;
          return (
            <section
              key={t.id}
              data-turn-id={t.id}
              data-status={t.status}
              data-testid="turn-card"
              aria-label={`Question ${i + 1}: ${cleanText(t.question)}`}
              className="flex flex-col gap-3.5"
            >
              <QuestionBubble turn={t} />
              {t.status === 'pending' && <PendingCard statusLine={isLast ? statusLine : null} />}
              {t.status === 'error' && <ErrorCard turn={t} onRetry={onRetry} />}
              {t.status === 'done' && t.contract && (
                <AnswerCard
                  contract={t.contract}
                  isDark={isDark}
                  persona={persona}
                  fresh={!!t.fresh && isLast}
                  isLatest={isLast}
                  onAsk={onAsk}
                  onNavigateToAlternative={() => onNavigateToAlternative?.(t.contract?.access?.alternative)}
                />
              )}
            </section>
          );
        })}
      </div>

      {!following && turns.length > 0 && (
        <button
          type="button"
          onClick={jumpToLatest}
          data-testid="jump-latest"
          className="fixed left-1/2 -translate-x-1/2 bottom-[7.25rem] z-30 inline-flex items-center gap-1.5 px-4 py-2 rounded-pill bg-[var(--ink)] text-[var(--canvas)] text-label font-medium shadow-[var(--panel-shadow)] hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent)]"
        >
          <ArrowDown className="w-4 h-4" aria-hidden /> Jump to latest
        </button>
      )}
    </div>
  );
};

export default ConversationFeed;
