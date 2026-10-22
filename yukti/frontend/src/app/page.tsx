'use client';

import React, { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { PersonaType, AnswerContract, SpecPatch } from '@/contracts/answerContract';
import { TopBar } from '@/components/TopBar';
import { PersonaBanner } from '@/components/PersonaBanner';
import { CanvasView } from '@/components/CanvasView';
import { feedReducer, applyChartKind, latestAnswered, isReplotOf, Turn } from '@/state/feed';
import { FloatingConversationPanel, ChatMessage, PanelMode } from '@/components/FloatingConversationPanel';
import { OrbState } from '@/components/VoiceOrb';
import { VoiceAudioEngine } from '@/services/audioAnalyser';
import { FIXTURES } from '@/fixtures';
import { routeQueryToFixture } from '@/services/mockRouter';
import { yuktiClient, WsState } from '@/services/websocketClient';
import { dispatchUi, labelOf, parseUiCommands, UiCommand, useUiCommands } from '@/services/uiCommands';
import { cleanText } from '@/charts/format';
import { AlertTriangle, MicOff, RefreshCw, X } from 'lucide-react';

type Backend = 'checking' | 'online' | 'offline';
type Lang = 'en' | 'hi' | 'hi-en';

const STARTERS = [
  'How many executives have been posted in Delhi for 5 years or more?',
  'Which fields or assets were the most profitable and which made losses in FY26?',
  'How are we tracking against our MoU targets with MoPNG/DPE for this year?',
];

const GREETING: AnswerContract = {
  turn_id: 'turn_greeting',
  language: 'en',
  spoken_summary: 'Hello, I am Yukti, your HR and Finance agent. Please tell me how I can help.',
  display_text: 'Hello, I am Yukti, your HR and Finance agent. Please tell me how I can help.',
  visual: { type: 'none', mode: 'replace' },
  sources: [],
  suggestions: STARTERS,
  access: { status: 'allowed' },
};

const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
const uid = (p: string) => `${p}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;

/** Telemetry exposed for automated tests and the ?debug=1 overlay. */
interface Telemetry {
  lastVoiceAt: number | null;
  firstAudioAt: number | null;
  contractAt: number | null;
  turns: { speechEndToFirstAudioMs: number | null; speechEndToCanvasMs: number | null; audioBytes: number; chunks: number }[];
}

function isGreetingContract(c: AnswerContract): boolean {
  const noVisual = !c.visual || c.visual.type === 'none';
  return noVisual && (/-000$/.test(c.turn_id || '') || /^hello|^namaste|नमस्ते/i.test(c.spoken_summary || ''));
}

export default function YuktiApp() {
  const [isDark, setIsDark] = useState(false);
  const [language, setLanguage] = useState<Lang>('en');
  const [persona, setPersona] = useState<PersonaType>('CMD');
  const [isLiveMode, setIsLiveMode] = useState(true);
  const [backend, setBackend] = useState<Backend>('checking');
  const [isDebug, setIsDebug] = useState(false);
  const [panelMode, setPanelMode] = useState<PanelMode>('docked');

  const [orbState, setOrbState] = useState<OrbState>('idle');
  const [isMicActive, setIsMicActive] = useState(false);
  const [micError, setMicError] = useState<string | null>(null);
  const [wsState, setWsState] = useState<WsState>('idle');
  const [statusLine, setStatusLine] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [slow, setSlow] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [liveInterimText, setLiveInterimText] = useState<string>('');

  // Conversation feed (U2.2): every turn stays on screen; the "current" answer is the latest answered turn.
  const [turns, dispatchFeed] = useReducer(feedReducer, [] as Turn[]);
  const contract: AnswerContract = latestAnswered(turns)?.contract || GREETING;
  const [fixtureIndex, setFixtureIndex] = useState(-1);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const engineRef = useRef<VoiceAudioEngine | null>(null);
  const micActiveRef = useRef(false);
  const liveRef = useRef(true);
  const personaRef = useRef<PersonaType>('CMD');
  const langRef = useRef<Lang>('en');
  const messagesRef = useRef<ChatMessage[]>([]);
  const contractRef = useRef<AnswerContract>(GREETING);
  const turnsRef = useRef<Turn[]>([]);
  // Live voice turn tracking (feed card for the spoken question; agent text if no contract arrives)
  const voiceTurnRef = useRef<string | null>(null);
  const voiceQRef = useRef<string>('');
  const voiceAgentTextRef = useRef<string>('');
  const voiceUiOnlyRef = useRef(false);
  // The voice card whose question the backend is currently answering (set when its tool work starts), so a late
  // contract lands on ITS card even if the user has already asked the next question (U2 G4 R2-1).
  const toolTurnRef = useRef<string | null>(null);
  // Bumped by "New conversation": late answers from the old session must not land in the fresh feed (U2 G4 #4).
  const sessionEpochRef = useRef(0);
  const liveUserMsgRef = useRef<string | null>(null);
  const liveAgentMsgRef = useRef<string | null>(null);
  const lastUserQuestionRef = useRef<string>('');
  const telemetryRef = useRef<Telemetry>({ lastVoiceAt: null, firstAudioAt: null, contractAt: null, turns: [] });
  const abortRef = useRef<AbortController | null>(null);
  const pttRef = useRef<{ down: number; startedByPress: boolean } | null>(null);
  const wsAudioGotFirstChunkRef = useRef(false);
  const runTypedTurnRef = useRef<(q: string) => Promise<void>>(async () => {});
  const stopMicRef = useRef<(sendEnd?: boolean) => Promise<void>>(async () => {});
  const [, forceTick] = useState(0);

  useEffect(() => {
    micActiveRef.current = isMicActive;
  }, [isMicActive]);
  useEffect(() => {
    liveRef.current = isLiveMode;
  }, [isLiveMode]);
  useEffect(() => {
    personaRef.current = persona;
  }, [persona]);
  useEffect(() => {
    langRef.current = language;
  }, [language]);
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);
  useEffect(() => {
    contractRef.current = contract;
    turnsRef.current = turns;
  }, [contract, turns]);

  // URL flags
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    if (q.get('mock') === '1') setIsLiveMode(false);
    if (q.get('debug') === '1') setIsDebug(true);
    if (q.get('theme') === 'dark') setIsDark(true);
  }, []);

  // Theme class
  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark);
  }, [isDark]);

  // Audio engine
  useEffect(() => {
    const engine = new VoiceAudioEngine();
    engineRef.current = engine;
    engine.setPlaybackStartHandler(() => setOrbState('speaking'));
    engine.setPlaybackEndHandler(() => {
      setOrbState((s) => (s === 'speaking' ? (micActiveRef.current ? 'listening' : 'idle') : s));
    });
    (window as any).__yukti = {
      engine,
      client: yuktiClient,
      telemetry: telemetryRef.current,
    };
    forceTick((x) => x + 1);
    return () => {
      engine.dispose();
      if (engineRef.current === engine) engineRef.current = null;
    };
  }, []);

  // Backend health (through the UI origin)
  const checkBackend = useCallback(async () => {
    const h = await yuktiClient.checkHealth();
    setBackend(h.healthy ? 'online' : 'offline');
    return h.healthy;
  }, []);

  useEffect(() => {
    if (!isLiveMode) {
      yuktiClient.disconnect();
      return;
    }
    void checkBackend();
    // Pre-connect /ws/live immediately on page mount (Urvi `VoiceAgentPanel` pattern)
    // so Gemini Live is already warm & connected before the user clicks the mic/orb.
    void yuktiClient.connect({ persona: personaRef.current, language: langRef.current, voice: 'Leda' });
    const id = setInterval(checkBackend, 15000);
    return () => clearInterval(id);
  }, [isLiveMode, checkBackend]);

  // ---------- Conversation helpers ----------
  const pushMessage = useCallback((m: ChatMessage) => setMessages((prev) => [...prev, m]), []);

  // Register global UI-command event bus handlers (Urvi `useUiCommands` pattern)
  useUiCommands(
    {
      theme: (val) => setIsDark(val === 'dark'),
      persona: (val) => {
        if (val) {
          setPersona(val as PersonaType);
          personaRef.current = val as PersonaType;
          void yuktiClient.reconfigure({ persona: val });
        }
      },
      language: (val) => {
        if (val) {
          setLanguage(val as Lang);
          langRef.current = val as Lang;
          void yuktiClient.reconfigure({ language: val });
        }
      },
      open_screen: (val) => {
        if (val === 'home') window.dispatchEvent(new CustomEvent('yukti:feed-nav', { detail: 'top' }));
      },
      panel: (val) => {
        if (val === 'expand') setPanelMode('fullscreen');
        else if (val === 'dock') setPanelMode('docked');
        else if (val === 'minimise' || val === 'close') setPanelMode('minimised');
      },
      history: (val) => {
        // Feed (U2): "go back" / "next" scroll between turn cards instead of swapping one canvas.
        window.dispatchEvent(new CustomEvent('yukti:feed-nav', { detail: val === 'forward' ? 'forward' : 'back' }));
      },
      chart_kind: (val) => {
        if (!val) return;
        // Re-plot updates the CURRENT card in place (U2.5); no backend call, no new card.
        dispatchFeed({ type: 'refine', update: (c) => applyChartKind(c, val) });
      },
      export: (val) => {
        // Backend /api/export returns {export_id, filename, format}; the file is then served
        // from GET /api/export/{export_id}. Read the current contract from the ref (not inside a
        // setState updater, which StrictMode double-invokes and would POST twice).
        const v = (val || 'pdf').toLowerCase();
        const fmt = v === 'xlsx' || v === 'sheets' || v === 'excel'
          ? 'xlsx'
          : v === 'docx' || v === 'word' || v === 'docs'
            ? 'docx'
            : 'pdf';
        const prev = contractRef.current;
        const title = prev?.visual?.title || 'Yukti_AI_Report';
        const tbl = prev?.visual?.table;
        const chartRows = ((prev?.visual?.chart as any)?.data as any[]) || [];
        const rawRows: any[] = (tbl?.rows as any[]) || chartRows;
        const columns: string[] = tbl?.columns || (rawRows[0] && !Array.isArray(rawRows[0]) ? Object.keys(rawRows[0]) : []);
        // Backend expects rows as List[Dict]; zip array-shaped rows into objects.
        const rows = rawRows.map((r) =>
          Array.isArray(r) ? Object.fromEntries(columns.map((c, i) => [c, r[i]])) : r,
        );
        const docMd = prev?.visual?.document?.markdown || prev?.display_text || prev?.spoken_summary || '';
        void yuktiClient
          .exportFile({ format: fmt, title, content: docMd, columns, rows })
          .then((res) => {
            const href = res?.download_url || res?.url || (res?.export_id ? `/api/export/${encodeURIComponent(res.export_id)}` : '');
            if (!href) return;
            const a = document.createElement('a');
            a.href = href;
            a.download = res?.filename || `${title}.${res?.format || fmt}`;
            document.body.appendChild(a);
            a.click();
            a.remove();
          })
          .catch((e) => console.warn('[yukti] export failed', e));
      },
    },
    [],
  );

  const handleUiAction = useCallback((action?: { action?: string; command?: string; value?: string }) => {
    if (!action || (!action.command && !action.action)) return;
    const cmd = (action.command || action.action || '').toLowerCase();
    const val = (action.value || '').trim();
    if (cmd === 'set_theme' || cmd === 'theme') {
      dispatchUi({ action: 'theme', value: val === 'dark' ? 'dark' : 'light' });
    } else if ((cmd === 'set_persona' || cmd === 'persona') && val) {
      dispatchUi({ action: 'persona', value: val });
    } else if ((cmd === 'set_language' || cmd === 'language') && val) {
      dispatchUi({ action: 'language', value: val });
    } else if (cmd === 'go_home' || (cmd === 'open_screen' && val === 'home')) {
      dispatchUi({ action: 'open_screen', value: 'home' });
    } else if (cmd === 'navigate_history' || cmd === 'history') {
      dispatchUi({ action: 'history', value: val === 'forward' ? 'forward' : 'back' });
    } else if (cmd === 'set_panel_mode' || cmd === 'panel') {
      dispatchUi({ action: 'panel', value: val || 'dock' });
    } else if ((cmd === 'set_chart_kind' || cmd === 'chart_kind') && val) {
      dispatchUi({ action: 'chart_kind', value: val.toLowerCase() });
    } else if (cmd === 'export') {
      dispatchUi({ action: 'export', value: val || 'pdf' });
    }
  }, []);

  const applyContract = useCallback((c: AnswerContract, question: string, turnId?: string, epoch?: number) => {
    if (epoch !== undefined && epoch !== sessionEpochRef.current) return; // answer from before "New conversation"
    const current = latestAnswered(turnsRef.current)?.contract;
    if (isReplotOf(c, current)) {
      // Backend re-plot of the current card (e.g. voice "show as pie"): refine in place, drop the command's card.
      dispatchFeed({ type: 'refine', update: (prev) => ({ ...prev, visual: c.visual }) });
      if (turnId) dispatchFeed({ type: 'drop', id: turnId });
    } else {
      dispatchFeed({ type: 'answer', id: turnId, contract: c, question, newId: uid('t') });
    }
    if ((c as any).ui_action) handleUiAction((c as any).ui_action);
    if (c.language && c.language !== langRef.current) setLanguage(c.language);
    if (c.persona && c.persona !== personaRef.current) setPersona(c.persona);
    if (liveRef.current) {
      yuktiClient.sendContext({
        persona: c.persona || personaRef.current,
        language: c.language || langRef.current,
        visual_type: c.visual?.type || 'none',
        visual_title: c.visual?.title || '',
      });
    }
  }, [handleUiAction]);

  // ---------- Live socket events ----------
  useEffect(() => {
    // End the current voice card (U2 G4 #1): keep partial spoken text, drop pure screen commands, or mark failed.
    const settleVoiceTurn = (mode: 'settle' | 'fail', msg?: string, interrupted = false) => {
      const id = voiceTurnRef.current;
      if (!id) return;
      voiceTurnRef.current = null;
      if (mode === 'fail') dispatchFeed({ type: 'fail', id, error: msg || 'The voice turn was interrupted.' });
      else if (voiceUiOnlyRef.current) dispatchFeed({ type: 'drop', id });
      else {
        const text = cleanText(voiceAgentTextRef.current) || (interrupted ? 'You interrupted before Yukti finished answering.' : '');
        dispatchFeed({ type: 'settle', id, text });
      }
    };
    const onState = (s: WsState) => {
      setWsState(s);
      if ((s === 'closed' || s === 'error') && voiceTurnRef.current) settleVoiceTurn('fail', 'The voice connection dropped before Yukti answered. Please ask again.');
    };

    const onUserTranscript = ({ text, is_final }: { text: string; is_final: boolean }) => {
      if (!text) return;
      wsAudioGotFirstChunkRef.current = true;
      engineRef.current?.acceptIncoming(); // a new user turn: its reply audio must play (U3.4)
      setLiveInterimText('');
      telemetryRef.current.firstAudioAt = null;
      telemetryRef.current.contractAt = null;
      engineRef.current?.resetTurnStats();
      const curId = liveUserMsgRef.current;
      if (curId) {
        voiceQRef.current = (voiceQRef.current + text).replace(/\s+/g, ' ');
        lastUserQuestionRef.current = voiceQRef.current.trim();
        // UI commands in Live transcripts are resolved server-side (screen_control) and arrive
        // as 'ui_action' events; parsing them locally as well executed each command twice.
        if (voiceTurnRef.current) dispatchFeed({ type: 'question', id: voiceTurnRef.current, question: voiceQRef.current.trim() });
        const merged = voiceQRef.current;
        setMessages((prev) => prev.map((m) => (m.id === curId ? { ...m, text: merged } : m)));
      } else {
        const nid = uid('u_voice');
        liveUserMsgRef.current = nid;
        liveAgentMsgRef.current = null;
        voiceQRef.current = text.trimStart();
        lastUserQuestionRef.current = text.trim();
        // A spoken question gets its own feed card immediately (pending until the answer lands).
        settleVoiceTurn('settle', undefined, true); // a new question ends any previous voice card (e.g. after barge-in)
        voiceTurnRef.current = nid;
        voiceAgentTextRef.current = '';
        voiceUiOnlyRef.current = false;
        dispatchFeed({ type: 'ask', id: nid, question: text.trim(), viaVoice: true });
        setMessages((prev) => [...prev, { id: nid, role: 'user', text: text.trimStart(), timestamp: now(), viaVoice: true }]);
      }
    };

    const onAgentTranscript = ({ text }: { text: string; is_final: boolean }) => {
      if (!text) return;
      liveUserMsgRef.current = null;
      if (voiceTurnRef.current) voiceAgentTextRef.current += text;
      setMessages((prev) => {
        const id = liveAgentMsgRef.current;
        const idx = id ? prev.findIndex((m) => m.id === id) : -1;
        if (idx >= 0) {
          const copy = [...prev];
          copy[idx] = { ...prev[idx], text: (prev[idx].text + text).replace(/\s+/g, ' ') };
          return copy;
        }
        const nid = uid('a_voice');
        liveAgentMsgRef.current = nid;
        return [...prev, { id: nid, role: 'agent', text: text.trimStart(), timestamp: now(), streaming: true }];
      });
    };

    const onAudio = (b64: string) => {
      wsAudioGotFirstChunkRef.current = true;
      const tel = telemetryRef.current;
      if (tel.firstAudioAt === null) tel.firstAudioAt = performance.now();
      engineRef.current?.enqueue24kAudio(b64);
    };

    const onStatus = (step: string) => {
      if (voiceTurnRef.current) toolTurnRef.current = voiceTurnRef.current; // backend is working on this card
      setStatusLine(step);
      setOrbState((s) => (s === 'speaking' ? s : 'thinking'));
    };

    const onContract = (c: AnswerContract) => {
      if (isGreetingContract(c)) return; // never let the session greeting overwrite the canvas
      telemetryRef.current.contractAt = performance.now();
      const q = lastUserQuestionRef.current || c.visual?.title || 'Voice question';
      // Prefer the card whose tool run produced this contract; a dropped card makes it a no-op (stale), never
      // filling the next question's card.
      const target = toolTurnRef.current || voiceTurnRef.current || undefined;
      applyContract(c, q, target, sessionEpochRef.current);
      if (voiceTurnRef.current === target) voiceTurnRef.current = null;
      toolTurnRef.current = null;
      setStatusLine(null);
      setMessages((prev) => {
        const id = liveAgentMsgRef.current;
        const idx = id ? prev.findIndex((m) => m.id === id) : -1;
        const patch = { sources: c.sources, accessStatus: c.access?.status, streaming: false };
        if (idx >= 0) {
          const copy = [...prev];
          copy[idx] = { ...prev[idx], ...patch, text: prev[idx].text || cleanText(c.display_text || c.spoken_summary) };
          return copy;
        }
        const nid = uid('a_voice');
        liveAgentMsgRef.current = nid;
        return [...prev, { id: nid, role: 'agent', text: cleanText(c.display_text || c.spoken_summary), timestamp: now(), ...patch }];
      });
    };

    const onInterrupted = () => {
      settleVoiceTurn('settle', undefined, true); // keep what Yukti had said so far (or note the interruption)
      engineRef.current?.stopPlayback(false);
      engineRef.current?.acceptIncoming();
      setOrbState(micActiveRef.current ? 'listening' : 'idle');
    };

    const onTurnComplete = () => {
      const tel = telemetryRef.current;
      const st = engineRef.current?.getTurnStats();
      if (tel.lastVoiceAt) {
        tel.turns.push({
          speechEndToFirstAudioMs: tel.firstAudioAt ? Math.round(tel.firstAudioAt - tel.lastVoiceAt) : null,
          speechEndToCanvasMs: tel.contractAt ? Math.round(tel.contractAt - tel.lastVoiceAt) : null,
          audioBytes: st?.bytes || 0,
          chunks: st?.chunks || 0,
        });
      }
      engineRef.current?.acceptIncoming();
      // A voice turn with no contract: keep the spoken reply as a text card; drop pure screen commands.
      settleVoiceTurn('settle');
      liveUserMsgRef.current = null;
      liveAgentMsgRef.current = null;
      setStatusLine(null);
      setMessages((prev) => prev.map((m) => (m.streaming ? { ...m, streaming: false } : m)));
      if (!engineRef.current?.isAudioPlaying()) setOrbState(micActiveRef.current ? 'listening' : 'idle');
    };

    const onError = (e: { message: string }) => {
      settleVoiceTurn('fail', `Voice session problem: ${e.message}`);
      setStatusLine(null);
      pushMessage({ id: uid('err'), role: 'error', text: `Voice session problem: ${e.message}`, timestamp: now() });
      setOrbState(micActiveRef.current ? 'listening' : 'idle');
    };

    yuktiClient.on('ws_state', onState);
    yuktiClient.on('user_transcript', onUserTranscript);
    yuktiClient.on('agent_transcript', onAgentTranscript);
    yuktiClient.on('audio_chunk', onAudio);
    yuktiClient.on('status_event', onStatus);
    yuktiClient.on('contract', onContract);
    const onUiActionLive = (a?: { action?: string; command?: string; value?: string }) => {
      if (voiceTurnRef.current) voiceUiOnlyRef.current = true;
      handleUiAction(a);
    };
    yuktiClient.on('ui_action', onUiActionLive);
    yuktiClient.on('interrupted', onInterrupted);
    yuktiClient.on('turn_complete', onTurnComplete);
    yuktiClient.on('error', onError);
    return () => {
      yuktiClient.off('ws_state', onState);
      yuktiClient.off('user_transcript', onUserTranscript);
      yuktiClient.off('agent_transcript', onAgentTranscript);
      yuktiClient.off('audio_chunk', onAudio);
      yuktiClient.off('status_event', onStatus);
      yuktiClient.off('contract', onContract);
      yuktiClient.off('ui_action', onUiActionLive);
      yuktiClient.off('interrupted', onInterrupted);
      yuktiClient.off('turn_complete', onTurnComplete);
      yuktiClient.off('error', onError);
    };
  }, [applyContract, pushMessage, handleUiAction]);

  // Voice activity tracking (speech-end timestamp) + local barge-in (Urvi pattern: server-side VAD handles turn end)
  useEffect(() => {
    let loud = 0;
    const id = setInterval(() => {
      const eng = engineRef.current;
      if (!eng || !micActiveRef.current) {
        loud = 0;
        return;
      }
      // U3.3/U3.4: decisions use the RAW mic level (no floor/cadence), so room noise or echo can't trigger barge-in.
      const lv = eng.getRawMicLevel();
      if (lv > 0.12) {
        telemetryRef.current.lastVoiceAt = performance.now();
      }
      // Leaky counter: brief dips between syllables don't reset it; ~4 loud ticks (200 ms) trigger (U3.4).
      if (eng.isAudioPlaying() && lv > 0.5) {
        loud += 1;
        if (loud >= 4) {
          eng.stopPlayback(true); // drops the rest of this reply locally
          yuktiClient.sendInterrupt(); // and tells the server to stop generating
          setOrbState('listening');
          loud = 0;
        }
      } else {
        loud = Math.max(0, loud - 1);
      }
    }, 50);
    return () => clearInterval(id);
  }, []);

  // ---------- Microphone (Urvi `VoiceAgentPanel` + `micCapture` pattern) ----------
  const micStartingRef = useRef(false);
  const startMic = useCallback(async (deviceId?: string): Promise<boolean> => {
    const eng = engineRef.current;
    if (!eng) return false;
    if (micStartingRef.current) return false; // U3.5: ignore rapid double-clicks while a start is in flight
    micStartingRef.current = true;
    try {
      return await startMicBody(eng, deviceId);
    } finally {
      micStartingRef.current = false;
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const startMicBody = async (eng: VoiceAudioEngine, deviceId?: string): Promise<boolean> => {
    eng.unlock();
    eng.stopPlayback(false);
    setMicError(null);
    setLiveInterimText('');
    wsAudioGotFirstChunkRef.current = false;

    // Broadcast to any other open Yukti tabs so they release getUserMedia & SpeechRecognition immediately
    try {
      const bc = new BroadcastChannel('yukti_voice_owner');
      bc.postMessage({ type: 'claim_mic', sessionId: yuktiClient.getSessionId() });
      bc.close();
    } catch {}

    // CRITICAL URVI PATTERN: Call getUserMedia(startMic) inside the user gesture FIRST,
    // and start Chrome's built-in SpeechRecognition AFTER getUserMedia settles so getUserMedia never aborts SpeechRecognition.
    const res = await eng.startMic((chunk) => {
      if (liveRef.current) yuktiClient.sendAudioChunk(chunk);
    }, deviceId);
    if (!res.ok) {
      eng.stopSpeechRecognition(false);
      if (!res.cancelled) setMicError(res.message || 'Microphone unavailable.');
      setIsMicActive(false);
      setOrbState('idle');
      return false;
    }

    eng.startSpeechRecognition(
      langRef.current,
      (interim) => setLiveInterimText(interim),
      (finalText) => {
        setLiveInterimText('');
        // Browser SR is a FALLBACK only: when the Live socket is open, Gemini Live owns the turn (no duplicate REST turn).
        if (liveRef.current && yuktiClient.isLiveVoiceReady()) return;
        if (!wsAudioGotFirstChunkRef.current && finalText.trim()) {
          void stopMicRef.current(false);
          void runTypedTurnRef.current(finalText.trim());
        }
      }
    );

    if (liveRef.current) {
      void yuktiClient.connect({ persona: personaRef.current, language: langRef.current, voice: 'Leda' });
    }
    setIsMicActive(true);
    setOrbState('listening');
    return true;
  };

  const stopMic = useCallback(async (sendEnd = true) => {
    const eng = engineRef.current;
    // Flush the browser SR only when it is acting as the fallback (Live closed); otherwise cancel it silently.
    eng?.stopSpeechRecognition(sendEnd && !(liveRef.current && yuktiClient.isLiveVoiceReady()));
    eng?.stopMic();
    setLiveInterimText('');
    if (sendEnd && liveRef.current) {
      yuktiClient.sendAudioStreamEnd();
    }
    setIsMicActive(false);
    setOrbState((s) => (s === 'listening' ? 'idle' : s));
  }, []);

  useEffect(() => {
    stopMicRef.current = stopMic;
  }, [stopMic]);

  // Release mic & speech recognition in background tabs so multiple tabs never fight over Chrome's singleton SpeechRecognition
  useEffect(() => {
    let bc: BroadcastChannel | null = null;
    try {
      bc = new BroadcastChannel('yukti_voice_owner');
      bc.onmessage = (ev) => {
        if (ev.data?.type === 'claim_mic' && ev.data?.sessionId !== yuktiClient.getSessionId()) {
          if (micActiveRef.current) void stopMicRef.current(false);
          yuktiClient.disconnect();
        }
      };
    } catch {}
    const onVisChange = () => {
      if (document.visibilityState === 'hidden' && micActiveRef.current) {
        void stopMicRef.current(false);
      }
    };
    document.addEventListener('visibilitychange', onVisChange);
    return () => {
      document.removeEventListener('visibilitychange', onVisChange);
      try {
        bc?.close();
      } catch {}
    };
  }, []);

  const toggleMic = useCallback(async () => {
    if (micActiveRef.current) await stopMic(true);
    else await startMic();
  }, [startMic, stopMic]);

  const handleToggleMute = useCallback(() => {
    setIsMuted((prev) => {
      const next = !prev;
      engineRef.current?.setMuted(next);
      return next;
    });
  }, []);

  const handleSelectMicDevice = useCallback(async (deviceId: string) => {
    const eng = engineRef.current;
    if (!eng) return;
    eng.setPreferredDeviceId(deviceId);
    if (micActiveRef.current) {
      await stopMic(false);
      await startMic(deviceId);
    }
  }, [startMic, stopMic]);

  // ---------- Typed / chip turns (with Urvi Layer-A 0ms client-side UI command parser) ----------
  const runTypedTurn = useCallback(
    async (queryText: string, specPatch?: SpecPatch) => {
      const text = queryText.trim();
      if (!text) return;
      engineRef.current?.unlock();
      engineRef.current?.stopPlayback(true);
      lastUserQuestionRef.current = text;
      pushMessage({ id: uid('u'), role: 'user', text, timestamp: now() });

      // Layer A (Urvi `runLocalUi` pattern): if every clause is a plain UI command, execute in 0 ms in browser
      const localUiCmds: UiCommand[] | null = parseUiCommands(text);
      if (localUiCmds && localUiCmds.length > 0) {
        engineRef.current?.acceptIncoming();
        localUiCmds.forEach(dispatchUi);
        const summary = `↗ Done on screen: ${localUiCmds.map(labelOf).join(' · ')}.`;
        pushMessage({
          id: uid('a_ui'),
          role: 'agent',
          text: summary,
          timestamp: now(),
        });
        if (!engineRef.current?.getMuted() && !liveRef.current) {
          engineRef.current?.speakBrowserTts(
            localUiCmds.map(labelOf).join(', '),
            langRef.current,
          );
        }
        return;
      }

      // A real question supersedes the one in flight (screen commands above never abort it — U2 G4 #5).
      abortRef.current?.abort();
      const epoch = sessionEpochRef.current;
      const tid = uid('t');
      dispatchFeed({ type: 'ask', id: tid, question: text, specPatch });
      let myAc: AbortController | null = null;
      setBusy(true);
      setSlow(false);
      setStatusLine('Thinking…');
      setOrbState('thinking');
      const slowTimer = setTimeout(() => setSlow(true), 9000);

      try {
        let c: AnswerContract;
        if (liveRef.current) {
          const ac = new AbortController();
          abortRef.current = ac;
          myAc = ac;
          const timeout = setTimeout(() => ac.abort(), 90000);
          try {
            const recentHist = messagesRef.current
              .filter((m) => m.role === 'user' || m.role === 'agent')
              .slice(-8)
              .map((m) => ({ role: m.role, text: m.text }));
            const curVis = contractRef.current?.visual;
            const curSrc = (contractRef.current?.sources || []).find((s) => s.sql);
            const uiCtx = curVis
              ? {
                  title: curVis.title || '',
                  subtitle: (curVis as any).subtitle || '',
                  chart_kind: curVis.chart?.kind || curVis.type,
                  columns: curVis.table?.columns || [],
                  rows: (curVis.table?.rows || curVis.chart?.data || []).slice(0, 50),
                  sql: curSrc?.sql || '',
                }
              : {};
            // U5.4: drill-down chips refine the current question as a patch on its query_spec (also for text answers)
            Object.assign(uiCtx, {
              ...(contractRef.current?.query_spec ? { query_spec: contractRef.current.query_spec } : {}),
              ...(specPatch ? { spec_patch: specPatch } : {}),
            });
            c = await yuktiClient.executeTurnRest(
              text,
              personaRef.current,
              langRef.current,
              2,
              ac.signal,
              recentHist,
              uiCtx,
            );
          } finally {
            clearTimeout(timeout);
          }
          setBackend('online');
        } else {
          await new Promise((r) => setTimeout(r, 450));
          c = routeQueryToFixture(text, personaRef.current).contract;
        }
        if (epoch !== sessionEpochRef.current) return; // "New conversation" happened meanwhile
        applyContract(c, text, tid, epoch);
        const replyText = cleanText(c.display_text || c.spoken_summary);
        pushMessage({
          id: c.turn_id ? `${c.turn_id}_${Date.now()}` : uid('a'),
          role: 'agent',
          text: replyText,
          timestamp: now(),
          sources: c.sources,
          accessStatus: c.access?.status,
        });
        // Speak every reply aloud: in Live mode use ONLY Leda 24 kHz Gemini Live stream (never Linux espeak browser TTS!)
        const spokenText = cleanText(c.spoken_summary || c.display_text);
        if (spokenText && !engineRef.current?.getMuted()) {
          engineRef.current?.acceptIncoming();
          if (liveRef.current) {
            void yuktiClient
              .connect({ persona: personaRef.current, language: langRef.current, voice: 'Leda' })
              .then((ok) => {
                if (ok) yuktiClient.sendSpeak(spokenText);
              });
          } else {
            engineRef.current?.speakBrowserTts(spokenText, c.language || langRef.current);
          }
        }
      } catch (e: any) {
        if (epoch !== sessionEpochRef.current) return;
        if (myAc && abortRef.current !== myAc) {
          // superseded by a newer question: not an error the user needs to see
          dispatchFeed({ type: 'fail', id: tid, error: 'Stopped: you asked a newer question.' });
          return;
        }
        const msg = /abort/i.test(String(e?.name || e?.message))
          ? 'That took too long, so I stopped waiting. Please try again.'
          : /unreachable|Failed to fetch|502|NetworkError/i.test(String(e?.message))
          ? "I can't reach Yukti's server right now."
          : `Something went wrong: ${e?.message || e}`;
        pushMessage({ id: uid('err'), role: 'error', text: msg, timestamp: now(), retryText: text });
        dispatchFeed({ type: 'fail', id: tid, error: msg });
        void checkBackend();
      } finally {
        clearTimeout(slowTimer);
        // a newer turn (or a reset) owns the busy/status state
        if (epoch !== sessionEpochRef.current || (myAc && abortRef.current !== myAc)) return;
        setBusy(false);
        setSlow(false);
        setStatusLine(null);
        setOrbState((s) => (s === 'speaking' ? 'speaking' : micActiveRef.current ? 'listening' : 'idle'));
      }
    },
    [applyContract, pushMessage, checkBackend]
  );

  useEffect(() => {
    runTypedTurnRef.current = runTypedTurn;
  }, [runTypedTurn]);

  // ---------- Demo (mock mode only) ----------
  const loadFixture = useCallback(
    (index: number) => {
      const idx = (index + FIXTURES.length) % FIXTURES.length;
      setFixtureIndex(idx);
      const f = FIXTURES[idx];
      if (f.data.persona && f.data.persona !== personaRef.current) setPersona(f.data.persona);
      pushMessage({ id: uid('u'), role: 'user', text: f.question, timestamp: now() });
      applyContract({ ...f.data, turn_id: `${f.data.turn_id}_${Date.now()}` }, f.question);
      pushMessage({ id: uid('a'), role: 'agent', text: cleanText(f.data.display_text), timestamp: now(), sources: f.data.sources, accessStatus: f.data.access?.status });
    },
    [applyContract, pushMessage]
  );

  // ---------- Persona / language ----------
  const handlePersonaChange = (p: PersonaType) => {
    setPersona(p);
    personaRef.current = p;
    void yuktiClient.reconfigure({ persona: p });
  };

  const handleLanguageToggle = () => {
    const next: Lang = language === 'en' ? 'hi' : language === 'hi' ? 'hi-en' : 'en';
    setLanguage(next);
    langRef.current = next;
    void yuktiClient.reconfigure({ language: next });
  };

  // ---------- Keyboard: Space = clean toggle (immune to X11/CRD key auto-repeat storms) ----------
  useEffect(() => {
    let lastSpaceAt = 0;
    const isTyping = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      return ['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes(el.tagName) || el.isContentEditable;
    };
    const down = (e: KeyboardEvent) => {
      if (isTyping(e)) return;
      if (e.code === 'Space') {
        e.preventDefault();
        if (e.repeat) return;
        const nowTs = performance.now();
        if (nowTs - lastSpaceAt < 450) return;
        lastSpaceAt = nowTs;
        if (micActiveRef.current) void stopMic(true);
        else void startMic();
        return;
      }
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === 't' || e.key === 'T') setIsDark((d) => !d);
      else if (e.key === 'f' || e.key === 'F') setPanelMode((m) => (m === 'fullscreen' ? 'docked' : 'fullscreen'));
      else if (e.key === 'Escape') {
        if (engineRef.current?.isAudioPlaying()) engineRef.current.stopPlayback(true);
        setPanelMode((m) => (m === 'fullscreen' ? 'docked' : m));
      } else if (!liveRef.current && e.key === 'ArrowRight') loadFixture(fixtureIndex + 1);
      else if (!liveRef.current && e.key === 'ArrowLeft') loadFixture(Math.max(0, fixtureIndex - 1));
    };
    window.addEventListener('keydown', down);
    return () => {
      window.removeEventListener('keydown', down);
    };
  }, [startMic, stopMic, loadFixture, fixtureIndex]);

  // "New conversation" (U2.6): clear the feed, the chat and the backend context (fresh session id).
  const handleNewSession = useCallback(() => {
    sessionEpochRef.current += 1;
    abortRef.current?.abort();
    abortRef.current = null;
    engineRef.current?.stopPlayback(true);
    engineRef.current?.acceptIncoming();
    voiceTurnRef.current = null;
    liveUserMsgRef.current = null;
    liveAgentMsgRef.current = null;
    lastUserQuestionRef.current = '';
    toolTurnRef.current = null;
    dispatchFeed({ type: 'reset' });
    setMessages([]);
    setStatusLine(null);
    setBusy(false);
    setSlow(false);
    setLiveInterimText('');
    yuktiClient.resetSession();
    setOrbState(micActiveRef.current ? 'listening' : 'idle');
  }, []);

  const micLevel = useCallback(() => engineRef.current?.getMicLevel() || 0, []);
  const suggestions = (contract.suggestions && contract.suggestions.length ? contract.suggestions : STARTERS).slice(0, 4);
  const offline = isLiveMode && backend === 'offline';

  return (
    <div className="h-screen w-screen overflow-hidden grid grid-cols-[minmax(0,1fr)] grid-rows-[auto_auto_minmax(0,1fr)] bg-[var(--canvas)] text-[var(--ink)] transition-colors duration-300">
      <TopBar
        currentPersona={persona}
        onPersonaChange={handlePersonaChange}
        isDark={isDark}
        onThemeToggle={() => setIsDark((d) => !d)}
        language={language}
        onLanguageToggle={handleLanguageToggle}
        state={orbState}
        statusLine={statusLine}
        isLiveMode={isLiveMode}
        onToggleLiveMode={() => setIsLiveMode((m) => !m)}
        backend={backend}
        demo={!isLiveMode ? { index: Math.max(0, fixtureIndex), total: FIXTURES.length, onPrev: () => loadFixture(Math.max(0, fixtureIndex - 1)), onNext: () => loadFixture(fixtureIndex + 1) } : undefined}
        micLevel={micLevel}
      />

      {/* Banners live in normal flow so nothing ever overlaps them */}
      <div className="relative z-20">
        {offline && (
          <div role="alert" className="flex flex-wrap items-center justify-between gap-3 px-6 py-2.5 text-[0.85rem] bg-[var(--maroon-pale)] text-[var(--maroon)] border-b border-[var(--hairline)]">
            <div className="flex items-center gap-2 font-medium">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>Yukti&apos;s server is not reachable. Voice and live answers are paused; I&apos;ll reconnect automatically.</span>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => void checkBackend()} className="chip !py-1">
                <RefreshCw className="w-3.5 h-3.5" /> Retry now
              </button>
              <button onClick={() => setIsLiveMode(false)} className="chip !py-1">
                Use demo answers
              </button>
            </div>
          </div>
        )}
        {micError && (
          <div role="alert" className="flex items-center justify-between gap-3 px-6 py-2.5 text-[0.85rem] bg-warning-pale text-warning border-b border-[var(--hairline)]">
            <div className="flex items-center gap-2 font-medium">
              <MicOff className="w-4 h-4 shrink-0" />
              <span>{micError} You can keep typing in the panel.</span>
            </div>
            <button onClick={() => setMicError(null)} className="icon-btn !w-7 !h-7" aria-label="Dismiss">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      <div className="relative min-h-0 min-w-0 overflow-hidden">
        <PersonaBanner persona={persona} />
        {/* U2.7: the scroll area ends above the floating ask bar / orb (reserved band), so the bar never covers
            the active card; the band height follows the panel mode. */}
        <main
          style={{ height: turns.length && panelMode !== 'fullscreen' ? `calc(100% - ${panelMode === 'minimised' ? '9.25rem' : '5.75rem'})` : '100%' }}
          className={`min-w-0 overflow-y-auto overflow-x-hidden transition-[height,opacity] duration-300 ${panelMode === 'fullscreen' ? 'opacity-20 pointer-events-none' : ''}`}
        >
          <CanvasView
            turns={turns}
            isDark={isDark}
            onNavigateToAlternative={(alt) => runTypedTurn(alt || 'What are the station tenure norms?')}
            onSelectStarter={runTypedTurn}
            onAsk={(q, patch) => void runTypedTurn(q, patch)}
            onRetry={(q, turnId) => {
              const patch = turnsRef.current.find((t) => t.id === turnId)?.specPatch;
              if (turnId) dispatchFeed({ type: 'drop', id: turnId }); // retry replaces the error card
              void runTypedTurn(q, patch);
            }}
            onNewSession={handleNewSession}
            onReplot={(turnId, visual) => dispatchFeed({ type: 'refine', id: turnId, update: (c) => ({ ...c, visual }) })}
            busy={busy}
            statusLine={statusLine}
            onTalk={toggleMic}
            isMicActive={isMicActive}
            orbState={orbState}
            audioEngine={engineRef.current || undefined}
            messages={messages}
            liveInterimText={liveInterimText}
            persona={persona}
          />
        </main>

        <FloatingConversationPanel
          panelMode={panelMode}
          onModeChange={setPanelMode}
          isDark={isDark}
          messages={messages}
          onSendMessage={runTypedTurn}
          orbState={orbState}
          isMicActive={isMicActive}
          onToggleMic={toggleMic}
          audioEngine={engineRef.current || undefined}
          // Follow-ups now live inside the latest answer card (U2.3); the floating chips overlapped data.
          suggestions={turns.length ? [] : suggestions}
          onSelectSuggestion={runTypedTurn}
          statusLine={statusLine}
          slow={slow}
          wsState={wsState}
          isLiveMode={isLiveMode}
          offline={offline}
          onRetry={runTypedTurn}
          onSelectMicDevice={handleSelectMicDevice}
          isMuted={isMuted}
          onToggleMute={handleToggleMute}
          liveInterimText={liveInterimText}
          isGreeting={turns.length === 0}
        />
      </div>

      {isDebug && (
        <div className="fixed bottom-4 left-4 z-50 bg-black/85 text-emerald-300 p-4 rounded-2xl font-mono text-[0.72rem] space-y-1 max-w-sm">
          <div className="font-bold text-emerald-200">Yukti telemetry (?debug=1)</div>
          <div>WS: {wsState} · sent {yuktiClient.counters.audioChunksSent} chunks / {yuktiClient.counters.audioBytesSent} B</div>
          <div>Received audio: {yuktiClient.counters.audioChunksReceived} chunks / {yuktiClient.counters.audioBytesReceived} B</div>
          <div>Last turn: {JSON.stringify(telemetryRef.current.turns.slice(-1)[0] || {})}</div>
        </div>
      )}
    </div>
  );
}
