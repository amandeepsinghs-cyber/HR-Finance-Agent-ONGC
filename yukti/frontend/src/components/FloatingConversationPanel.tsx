'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import clsx from 'clsx';
import { SourceCitation } from '@/contracts/answerContract';
import { Chip, IconButton } from './ui/primitives';
import { VoiceOrb, OrbState } from './VoiceOrb';
import { VoiceAudioEngine } from '@/services/audioAnalyser';
import { WsState } from '@/services/websocketClient';
import { LevelMeter } from './TopBar';
import {
  Mic,
  Square,
  ArrowUp,
  ChevronRight,
  ShieldAlert,
  RotateCcw,
  AlertCircle,
  Database,
  Scale,
  FileText,
  MessageSquare,
  Volume2,
  VolumeX,
  X,
  Maximize2,
  Minimize2,
} from 'lucide-react';

export type PanelMode = 'docked' | 'minimised' | 'fullscreen';

export interface ChatMessage {
  id: string;
  role: 'user' | 'agent' | 'error';
  text: string;
  timestamp: string;
  accessStatus?: string;
  sources?: SourceCitation[];
  viaVoice?: boolean;
  streaming?: boolean;
  retryText?: string;
}

interface Props {
  panelMode: PanelMode;
  onModeChange: (m: PanelMode) => void;
  isDark: boolean;
  messages: ChatMessage[];
  onSendMessage: (text: string) => void;
  orbState: OrbState;
  isMicActive: boolean;
  onToggleMic: () => void;
  audioEngine?: VoiceAudioEngine;
  suggestions: string[];
  onSelectSuggestion: (s: string) => void;
  statusLine?: string | null;
  slow?: boolean;
  wsState: WsState;
  isLiveMode: boolean;
  offline: boolean;
  onRetry: (text: string) => void;
  onSelectMicDevice?: (deviceId: string) => void;
  isMuted?: boolean;
  onToggleMute?: () => void;
  liveInterimText?: string;
  isGreeting?: boolean;
}

export function sourceLabel(s: SourceCitation): string {
  if (s.kind === 'policy') return [s.title || s.doc_id || 'Policy', s.clause].filter(Boolean).join(' · ');
  if (s.kind === 'document') return s.title || 'Document template';
  const obj = s.title || s.object || 'Enterprise records';
  if (/hrfin|v_|_gold|silver|bronze|\./i.test(obj)) {
    if (/pnl|field|fin|receiv|capex|mou/i.test(obj)) return 'Finance records';
    if (/head|post|employee|grade|tenure|vacan|transfer/i.test(obj)) return 'HR posting records';
    return 'Enterprise records';
  }
  return obj;
}

const SourceIcon: React.FC<{ kind: string }> = ({ kind }) =>
  kind === 'policy' ? <Scale className="w-3.5 h-3.5" /> : kind === 'document' ? <FileText className="w-3.5 h-3.5" /> : <Database className="w-3.5 h-3.5" />;

const Bubble: React.FC<{ m: ChatMessage; onRetry: (t: string) => void }> = ({ m, onRetry }) => {
  const [open, setOpen] = useState(false);
  if (m.role === 'error') {
    return (
      <div data-testid="error-turn" className="flex items-start gap-2 p-3 rounded-[1rem] bg-[var(--maroon-pale)] text-[var(--maroon)] text-[0.88rem]">
        <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
        <div className="flex-1">
          <div>{m.text}</div>
          {m.retryText && (
            <button onClick={() => onRetry(m.retryText!)} className="mt-2 inline-flex items-center gap-1.5 font-semibold underline-offset-2 hover:underline">
              <RotateCcw className="w-3.5 h-3.5" /> Try again
            </button>
          )}
        </div>
      </div>
    );
  }
  const isUser = m.role === 'user';
  const uniqSources = (m.sources || []).filter((s, i, arr) => arr.findIndex((x) => sourceLabel(x) === sourceLabel(s)) === i);
  return (
    <div data-testid={isUser ? 'user-turn' : 'agent-turn'} data-voice={m.viaVoice ? 'true' : undefined} className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} gap-1`}>
      <div
        className={`max-w-[88%] px-[0.95rem] py-[0.65rem] text-[0.9rem] leading-[1.52] ${
          isUser
            ? 'bg-[var(--accent)] text-white rounded-[1.05rem] rounded-br-[0.3rem]'
            : 'bg-[var(--surface)] text-[var(--ink)] rounded-[1.05rem] rounded-bl-[0.3rem] border border-[var(--hairline)]'
        }`}
      >
        <div className="whitespace-pre-wrap">
          {m.text}
          {m.streaming && <span className="inline-block w-[0.45rem] h-[1em] ml-0.5 align-[-0.15em] rounded-sm bg-current opacity-50 animate-pulse" />}
        </div>
        {!isUser && m.accessStatus === 'refused' && (
          <div className="mt-2 inline-flex items-center gap-1.5 text-[0.78rem] font-semibold text-[var(--maroon)]">
            <ShieldAlert className="w-3.5 h-3.5" /> Not permitted for this role
          </div>
        )}
        {!isUser && uniqSources.length > 0 && (
          <div className="mt-2 pt-2 border-t border-[var(--hairline)]">
            <button type="button" onClick={() => setOpen((o) => !o)} className="inline-flex items-center gap-1 text-[0.75rem] font-medium text-[var(--ink-2)] hover:text-[var(--ink)]" aria-expanded={open}>
              <ChevronRight className={`w-3.5 h-3.5 transition-transform ${open ? 'rotate-90' : ''}`} />
              Sources ({uniqSources.length})
            </button>
            {open && (
              <ul className="mt-1.5 space-y-1 text-[0.76rem] text-[var(--ink-2)]">
                {uniqSources.map((s, i) => (
                  <li key={i} className="flex items-center gap-1.5">
                    <SourceIcon kind={s.kind} />
                    <span className="truncate">{sourceLabel(s)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
      <span className="text-[0.66rem] text-[var(--ink-3)] px-1">
        {m.viaVoice ? 'Spoken · ' : ''}
        {m.timestamp}
      </span>
    </div>
  );
};

export const FloatingConversationPanel: React.FC<Props> = ({
  panelMode,
  onModeChange,
  isDark,
  messages,
  onSendMessage,
  orbState,
  isMicActive,
  onToggleMic,
  audioEngine,
  suggestions,
  onSelectSuggestion,
  statusLine,
  slow,
  onRetry,
  onSelectMicDevice,
  isMuted = false,
  onToggleMute,
  liveInterimText,
  isGreeting = false,
}) => {
  const [input, setInput] = useState('');
  const [threadOpen, setThreadOpen] = useState(false);
  const [micDevices, setMicDevices] = useState<{ deviceId: string; label: string }[]>([]);
  const [activeMicLabel, setActiveMicLabel] = useState<string>('');
  const threadRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const micLevel = useCallback(
    () =>
      Math.max(
        audioEngine?.getRawMicLevel ? audioEngine.getRawMicLevel() : 0,
        audioEngine?.getMicLevel ? audioEngine.getMicLevel() : 0,
        audioEngine?.getOutputLevel ? audioEngine.getOutputLevel() : 0,
      ),
    [audioEngine],
  );

  const collapsed =
    !isGreeting &&
    panelMode === 'docked' &&
    !hovered &&
    !focused &&
    orbState === 'idle' &&
    !isMicActive &&
    !input;

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === '/' && !e.metaKey && !e.ctrlKey && !e.altKey && !e.isComposing && !e.defaultPrevented) {
        const target = e.target as HTMLElement | null;
        const tag = target?.tagName?.toLowerCase();
        if (tag === 'input' || tag === 'textarea' || tag === 'select' || target?.isContentEditable) {
          return;
        }
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const expandBar = useCallback(() => {
    setFocused(true);
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!audioEngine) return;
    setMicDevices(audioEngine.getDevices());
    setActiveMicLabel(audioEngine.getActiveDeviceLabel());
  }, [audioEngine, isMicActive]);

  useEffect(() => {
    const el = threadRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  }, [messages, statusLine, threadOpen]);

  const send = (e: React.FormEvent) => {
    e.preventDefault();
    const t = input.trim();
    if (!t) return;
    onSendMessage(t);
    setInput('');
  };

  if (panelMode === 'minimised') {
    return (
      <div className="fixed bottom-[1.5rem] right-[1.5rem] z-40 flex flex-col items-center gap-2" data-testid="minimised-orb">
        <div className="relative rounded-full bg-[var(--card)] shadow-[var(--panel-shadow)] border border-[var(--hairline)]">
          <VoiceOrb state={orbState} isDark={isDark} size={96} onClick={onToggleMic} audioEngine={audioEngine} label={orbState === 'speaking' ? 'Stop Yukti speaking' : isMicActive ? 'Stop listening' : 'Start talking'} pressed={!!isMicActive} />
          <button onClick={() => onModeChange('docked')} className="absolute -top-1 -left-1 w-8 h-8 grid place-items-center rounded-full bg-[var(--card)] border border-[var(--hairline)] shadow-md text-[var(--ink-2)] hover:text-[var(--ink)]" aria-label="Open command bar">
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    );
  }

  const full = panelMode === 'fullscreen';
  const showHistoryDrawer = threadOpen || full;

  return (
    <div
      data-testid="conversation-panel"
      className="fixed bottom-4 left-1/2 -translate-x-1/2 z-30 w-[min(94vw,60rem)] flex flex-col gap-2 pointer-events-none"
    >
      {/* Hidden DOM thread when drawer is closed so E2E tests and screen readers always see user-turn / agent-turn */}
      {!showHistoryDrawer && (
        <div className="sr-only" data-testid="thread">
          {messages.map((m) => (
            <Bubble key={m.id} m={m} onRetry={onRetry} />
          ))}
        </div>
      )}

      {/* Expandable Conversation History Drawer above the bottom bar */}
      {showHistoryDrawer && (
        <div
          className={`pointer-events-auto w-full rounded-[1.35rem] bg-[color-mix(in_srgb,var(--card)_96%,transparent)] backdrop-blur-2xl border border-[var(--hairline)] shadow-[var(--panel-shadow)] flex flex-col overflow-hidden transition-all ${
            full ? 'h-[72vh]' : 'max-h-[42vh]'
          }`}
        >
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-[var(--hairline)]">
            <div className="flex items-center gap-2 text-[0.86rem] font-semibold">
              <MessageSquare className="w-4 h-4 text-[var(--accent)]" />
              <span>Conversation History ({messages.length})</span>
            </div>
            <div className="flex items-center gap-1">
              <IconButton
                onClick={() => onModeChange(full ? 'docked' : 'fullscreen')}
                className="!w-7 !h-7 [&>svg]:!w-3.5 [&>svg]:!h-3.5"
                label={full ? 'Exit full screen' : 'Full screen'}
              >
                {full ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
              </IconButton>
              <IconButton
                onClick={() => {
                  setThreadOpen(false);
                  if (full) onModeChange('docked');
                }}
                className="!w-7 !h-7 [&>svg]:!w-4 [&>svg]:!h-4"
                label="Close transcript"
              >
                <X className="w-4 h-4" />
              </IconButton>
            </div>
          </div>
          <div ref={threadRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3" data-testid="thread">
            {messages.length === 0 ? (
              <div className="text-[0.88rem] text-[var(--ink-2)] py-4 text-center">No turns yet — speak or type below to start.</div>
            ) : (
              messages.map((m) => <Bubble key={m.id} m={m} onRetry={onRetry} />)
            )}
          </div>
        </div>
      )}

      {/* Status or Live Speech Banner */}
      {(statusLine || liveInterimText) && (
        <div
          className="pointer-events-auto self-center px-4 py-1.5 rounded-pill bg-[var(--glass)] backdrop-blur-md border border-[var(--hairline)] shadow-[var(--card-shadow)] flex items-center gap-2.5 text-label text-[var(--ink-2)]"
          data-testid="status-line"
        >
          <span
            data-aura={liveInterimText ? 'listening' : 'thinking'}
            className="yk-aura-ring inline-flex items-center justify-center w-6 h-6 rounded-full shrink-0"
            aria-hidden
          >
            <LevelMeter level={micLevel} active />
          </span>
          <span className="font-normal text-[var(--ink-2)]">
            {liveInterimText ? `Listening: "${liveInterimText}"` : slow ? 'Still analysing, live data can take a few seconds…' : statusLine}
          </span>
        </div>
      )}

      {/* Suggested follow-ups (U4.6): subtle light-gray chips at the bottom, never bolder than body text */}
      {suggestions.length > 0 && !isGreeting && (
        <div
          className={clsx(
            'pointer-events-auto flex flex-wrap items-center justify-center gap-2 px-2',
            collapsed && 'hidden',
          )}
          data-testid="suggestions"
        >
          {suggestions.slice(0, 3).map((s) => (
            <Chip
              key={s}
              size="sm"
              onClick={() => onSelectSuggestion(s)}
              title={s}
              className="!font-normal !text-[var(--ink-3)] !bg-[var(--surface)] !border-[var(--hairline)] hover:!text-[var(--ink-2)] max-w-full"
            >
              <span className="whitespace-normal text-left">{s}</span>
            </Chip>
          ))}
        </div>
      )}

      {/* Bottom Floating Command & Voice Dock */}
      {/* Ask bar with the AI aura ring (D-16): drift when idle, sweep while listening/speaking, fast while thinking */}
      <div
        data-testid="ask-bar"
        data-collapsed={collapsed || undefined}
        data-aura={collapsed ? 'idle' : orbState === 'thinking' ? 'thinking' : orbState === 'listening' || orbState === 'speaking' ? 'listening' : 'idle'}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        onFocusCapture={() => setFocused(true)}
        onBlurCapture={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget as Node)) {
            setFocused(false);
          }
        }}
        className={clsx(
          'yk-aura-box pointer-events-auto rounded-pill self-center transition-[width] duration motion-reduce:transition-none',
          collapsed ? 'w-[15rem] h-12' : 'w-full',
        )}
      >
        <span aria-hidden className="yk-aura-box-halo">
          <span className="yk-aura-box-stretch" />
        </span>
        <span aria-hidden className="yk-aura-box-border">
          <span className="yk-aura-box-stretch" />
        </span>
        <form
          onSubmit={send}
          onClick={collapsed ? expandBar : undefined}
          className={clsx(
            'yk-aura-surface rounded-pill bg-[var(--card)] border border-[var(--hairline)] shadow-[var(--panel-shadow)] flex items-center',
            collapsed
              ? 'h-12 px-2.5 justify-between cursor-pointer select-none'
              : 'gap-2.5 px-3 py-2',
          )}
        >
          {/* Collapsed Aura Pill contents (U4.4) */}
          {collapsed && (
            <>
              <div className="flex items-center gap-2 min-w-0">
                <IconButton
                  label="Talk to Yukti"
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleMic();
                  }}
                  data-testid="mic-button"
                  className="!w-8 !h-8 !rounded-full shrink-0 text-[var(--accent)] hover:text-[var(--accent-deep)] hover:bg-[var(--accent-pale)]"
                >
                  <Mic className="w-4 h-4" />
                </IconButton>
                <span className="text-label text-[var(--ink-2)] truncate">Ask Yukti</span>
              </div>
              <kbd className="px-1.5 py-0.5 text-caption text-[var(--ink-3)] border border-[var(--hairline)] rounded bg-[var(--surface)] font-mono shrink-0">
                /
              </kbd>
            </>
          )}

          {/* Expanded contents */}
          {!collapsed && (
            <>
              {/* Replicate the TopBar Listening aura ring + animated 5-bar LevelMeter at the bottom panel (made bigger: 2.75rem / 44px) */}
              {orbState !== 'idle' ? (
                /* P4.9 (SPEC-09 §4.9, V12/V16): the Siri-like orb is visible in docked + fullscreen whenever Yukti is
                   listening, thinking or speaking — not only when the panel is minimised. Same control + testids as
                   the mic button: tap stops Yukti / toggles the mic (P0.10 Stop control). */
                <button
                  type="button"
                  onClick={onToggleMic}
                  data-testid="mic-button"
                  aria-pressed={isMicActive}
                  aria-label={orbState === 'speaking' ? 'Stop Yukti speaking' : isMicActive ? 'Stop listening' : 'Start talking'}
                  title={orbState === 'speaking' ? 'Stop Yukti and talk (or press Space)' : isMicActive ? 'Listening — click to stop' : 'Talk to Yukti (or press Space)'}
                  data-orb-state={orbState}
                  className="relative shrink-0 w-12 h-12 rounded-full grid place-items-center cursor-pointer transition-transform hover:scale-105 active:scale-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent)]"
                >
                  <VoiceOrb state={orbState} isDark={isDark} size={48} audioEngine={audioEngine} interactive={false} label={`Yukti is ${orbState}`} />
                  {orbState === 'speaking' && (
                    <span className="absolute inset-0 grid place-items-center pointer-events-none" aria-hidden>
                      <span className="w-5 h-5 rounded-full grid place-items-center bg-[var(--card)] border border-[var(--hairline)] shadow-sm text-[var(--ink)]">
                        <Square className="w-2.5 h-2.5 fill-current" data-testid="stop-speaking" />
                      </span>
                    </span>
                  )}
                </button>
              ) : isMicActive ? (
                <button
                  type="button"
                  onClick={onToggleMic}
                  data-testid="mic-button"
                  aria-pressed={isMicActive}
                  aria-label="Stop listening"
                  title="Listening — click to stop"
                  data-aura="listening"
                  className="yk-aura-ring rounded-full w-11 h-11 shrink-0 cursor-pointer transition-transform hover:scale-105 active:scale-95"
                >
                  <span
                    className="yk-aura-surface rounded-full w-full h-full grid place-items-center bg-[var(--card)] border border-[var(--hairline)] shadow-sm text-[var(--accent)]"
                  >
                    {/* mic open but Yukti idle: live input level (the orb branch above covers listening/thinking/speaking) */}
                    <LevelMeter level={micLevel} active size="lg" />
                  </span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={onToggleMic}
                  data-testid="mic-button"
                  aria-pressed={isMicActive}
                  className="shrink-0 w-[2.65rem] h-[2.65rem] rounded-full flex items-center justify-center transition-all font-medium text-[0.84rem] bg-[var(--mic-bg)] text-[var(--brand-red)] border border-[var(--mic-border)] hover:bg-[var(--mic-bg-hover)] shadow-sm"
                  title="Talk to Yukti (or press Space)"
                >
                  <Mic className="w-[1.12rem] h-[1.12rem]" />
                </button>
              )}
            </>
          )}

          {/* Text Prompt Input (mounted in both states) */}
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Escape' && !input) {
                setHovered(false);
                e.currentTarget.blur();
              }
            }}
            placeholder={isMicActive ? (liveInterimText || 'Listening… speak naturally') : 'Ask Yukti anything about HR, Finance, policies, or draft a note…'}
            data-testid="chat-input"
            className={clsx(
              collapsed
                ? 'sr-only'
                : 'flex-1 min-w-0 h-[2.65rem] px-3 rounded-full bg-transparent text-[0.95rem] placeholder:text-[var(--ink-3)] focus:outline-none',
            )}
          />

          {!collapsed && (
            <>
              {/* Speaker / Voice Mute Toggle */}
              <IconButton
                onClick={onToggleMute}
                className={clsx(
                  '!w-9 !h-9 !rounded-full border border-[var(--hairline)] [&>svg]:!w-4 [&>svg]:!h-4',
                  isMuted ? '!text-[var(--maroon)] !bg-[var(--maroon-pale)]' : '!text-[var(--accent)] !bg-[var(--surface)]',
                )}
                label={isMuted ? 'Voice output muted — click to unmute' : 'Voice output active (Leda) — click to mute'}
                aria-label="Toggle voice output"
              >
                {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
              </IconButton>
            </>
          )}

          {/* Transcript History Drawer Toggle */}
          <IconButton
            onClick={() => setThreadOpen((o) => !o)}
            className={clsx(
              collapsed
                ? 'sr-only'
                : '!w-9 !h-9 !rounded-full border border-[var(--hairline)] relative [&>svg]:!w-4 [&>svg]:!h-4',
              !collapsed && (showHistoryDrawer ? '!bg-[var(--accent-pale)] !text-[var(--accent-deep)]' : '!bg-[var(--surface)] !text-[var(--ink-2)]'),
            )}
            label="Toggle conversation transcript"
            aria-label="Toggle conversation transcript"
            data-testid="panel-minimise"
          >
            <MessageSquare className="w-4 h-4" />
            {messages.length > 0 && !collapsed && (
              <span className="absolute -top-1 -right-1 min-w-[1.1rem] h-[1.1rem] px-1 rounded-full bg-[var(--accent)] text-white text-[0.65rem] font-bold grid place-items-center">
                {messages.length}
              </span>
            )}
          </IconButton>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={!input.trim()}
            data-testid="send-button"
            aria-label="Send"
            className={clsx(
              collapsed
                ? 'sr-only'
                : 'shrink-0 w-[2.65rem] h-[2.65rem] rounded-full grid place-items-center bg-[var(--ink)] text-[var(--canvas)] disabled:opacity-25 transition-opacity',
            )}
          >
            <ArrowUp className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
