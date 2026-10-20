'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { PersonaType, AnswerContract, VisualContainer } from '@/contracts/answerContract';
import { TopBar } from '@/components/TopBar';
import { PersonaBanner } from '@/components/PersonaBanner';
import { CanvasView } from '@/components/CanvasView';
import { FloatingConversationPanel, ChatMessage } from '@/components/FloatingConversationPanel';
import { OrbState } from '@/components/VoiceOrb';
import { VoiceAudioEngine } from '@/services/audioAnalyser';
import { FIXTURES, FixtureMeta } from '@/fixtures';
import { routeQueryToFixture } from '@/services/mockRouter';
import { yuktiClient } from '@/services/websocketClient';
import { AlertCircle, RefreshCw, Radio } from 'lucide-react';

interface HistoryItem {
  id: string;
  question: string;
  contract: AnswerContract;
  timestamp: string;
}

const GREETING_CONTRACT: AnswerContract = {
  turn_id: 'turn_greeting',
  language: 'en',
  spoken_summary: 'Hello, I am Yukti, your HR and Finance agent. Please tell me how I can help.',
  display_text: 'Hello, I am Yukti, your HR and Finance agent. Please tell me how I can help.',
  visual: {
    type: 'none',
    mode: 'replace',
    title: 'Executive Intelligence Canvas',
  },
  sources: [],
  suggestions: [
    'How many executives have been posted in Delhi for 5 years or more?',
    'Which fields or assets were the most profitable and which made losses in FY26?',
    'How are we tracking against our MoU targets with MoPNG/DPE for this year?',
  ],
  access: { status: 'allowed' },
};

export default function YuktiApp() {
  // Theme & Language
  const [isDark, setIsDark] = useState<boolean>(false);
  const [language, setLanguage] = useState<'en' | 'hi' | 'hi-en'>('en');

  // Mode: Live ADK backend (default) or Mock Mode (?mock=1)
  const [isLiveMode, setIsLiveMode] = useState<boolean>(true);
  const [backendHealthy, setBackendHealthy] = useState<boolean>(true);
  const [micDeniedNotice, setMicDeniedNotice] = useState<boolean>(false);
  const [isDebugMode, setIsDebugMode] = useState<boolean>(false);
  const [lastVisualLatency, setLastVisualLatency] = useState<number | null>(null);

  // Persona
  const [persona, setPersona] = useState<PersonaType>('CMD');

  // Panel Mode: 'docked' | 'minimised' | 'fullscreen'
  const [panelMode, setPanelMode] = useState<'docked' | 'minimised' | 'fullscreen'>('docked');

  // Audio Engine & Voice State
  const [orbState, setOrbState] = useState<OrbState>('idle');
  const [isMicActive, setIsMicActive] = useState<boolean>(false);
  const audioEngineRef = useRef<VoiceAudioEngine | null>(null);

  // Demo index & active contract
  const [currentFixtureIndex, setCurrentFixtureIndex] = useState<number>(-1);
  const [contract, setContract] = useState<AnswerContract>(GREETING_CONTRACT);

  // Canvas History
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [currentHistoryIndex, setCurrentHistoryIndex] = useState<number>(0);

  // Chat message thread
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'msg_welcome',
      role: 'agent',
      spokenSummary: 'Hello, I am Yukti, your HR and Finance agent. Please tell me how I can help.',
      text: 'Hello, I am Yukti, your HR and Finance agent. Please tell me how I can help.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      suggestions: [
        'How many executives have been posted in Delhi for 5 years or more?',
        'Which fields or assets were the most profitable and which made losses in FY26?',
        'How are we tracking against our MoU targets with MoPNG/DPE for this year?',
      ],
    },
  ]);

  // Check URL parameters for ?mock=1 override
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      if (params.get('mock') === '1') {
        setIsLiveMode(false);
      }
      if (params.get('debug') === '1') {
        setIsDebugMode(true);
      }
    }
  }, []);

  // Initialize Audio Engine
  useEffect(() => {
    const engine = new VoiceAudioEngine();
    audioEngineRef.current = engine;

    engine.setPlaybackEndHandler(() => {
      setOrbState((curr) => (curr === 'speaking' ? 'idle' : curr));
    });

    return () => {
      engine.stopMic();
      engine.stopPlayback();
    };
  }, []);

  // Check backend health and connect WebSocket when in Live mode
  const initBackendConnection = useCallback(async () => {
    const health = await yuktiClient.checkHealth();
    setBackendHealthy(health.healthy);

    if (health.healthy) {
      await yuktiClient.connectWs({ persona, language, voice: 'Leda' });
    }
  }, [persona, language]);

  useEffect(() => {
    if (isLiveMode) {
      initBackendConnection();
    } else {
      yuktiClient.disconnectWs();
    }
  }, [isLiveMode, initBackendConnection]);

  // Wire WebSocket streaming events
  useEffect(() => {
    const handleAudioChunk = (b64Audio: string) => {
      if (audioEngineRef.current) {
        audioEngineRef.current.enqueue24kAudio(b64Audio);
        setOrbState('speaking');
      }
    };

    const handleUserTranscript = ({ text }: { text: string }) => {
      const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      setMessages((prev) => [
        ...prev,
        {
          id: `u_tx_${Date.now()}`,
          role: 'user',
          text,
          timestamp: now,
        },
      ]);
    };

    const handleAgentTranscript = ({ text }: { text: string }) => {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === 'agent' && last.id.startsWith('a_tx_live')) {
          return [
            ...prev.slice(0, -1),
            {
              ...last,
              text: last.text + text,
            },
          ];
        }
        return [
          ...prev,
          {
            id: `a_tx_live_${Date.now()}`,
            role: 'agent',
            text,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ];
      });
    };

    const handleStatusEvent = (step: string) => {
      setOrbState('thinking');
      setMessages((prev) => [
        ...prev,
        {
          id: `status_${Date.now()}`,
          role: 'status',
          text: step,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    };

    const handleContract = (newContract: AnswerContract) => {
      setContract(newContract);
      if (newContract.language) {
        setLanguage(newContract.language);
      }

      setHistory((prev) => [
        ...prev,
        {
          id: newContract.turn_id || `hist_${Date.now()}`,
          question: newContract.visual?.title || 'Live Query',
          contract: newContract,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
      setCurrentHistoryIndex(history.length);
    };

    const handleTurnComplete = () => {
      setTimeout(() => {
        if (!audioEngineRef.current?.isAudioPlaying()) {
          setOrbState((curr) => (curr === 'thinking' || curr === 'speaking' ? 'idle' : curr));
        }
      }, 500);
    };

    yuktiClient.on('audio_chunk', handleAudioChunk);
    yuktiClient.on('user_transcript', handleUserTranscript);
    yuktiClient.on('agent_transcript', handleAgentTranscript);
    yuktiClient.on('status_event', handleStatusEvent);
    yuktiClient.on('contract', handleContract);
    yuktiClient.on('turn_complete', handleTurnComplete);

    return () => {
      yuktiClient.off('audio_chunk', handleAudioChunk);
      yuktiClient.off('user_transcript', handleUserTranscript);
      yuktiClient.off('agent_transcript', handleAgentTranscript);
      yuktiClient.off('status_event', handleStatusEvent);
      yuktiClient.off('contract', handleContract);
      yuktiClient.off('turn_complete', handleTurnComplete);
    };
  }, [history.length]);

  // Update theme class on HTML element
  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  // Load scripted fixture into the active view
  const loadFixture = useCallback(
    async (index: number) => {
      const idx = (index + FIXTURES.length) % FIXTURES.length;
      setCurrentFixtureIndex(idx);
      const target = FIXTURES[idx];

      if (target.data.persona && target.data.persona !== persona) {
        setPersona(target.data.persona);
        if (isLiveMode) {
          yuktiClient.sendConfigWs({ persona: target.data.persona });
        }
      }

      setOrbState('thinking');

      if (isLiveMode && backendHealthy) {
        try {
          const liveContract = await yuktiClient.executeTurnRest(
            target.question,
            target.data.persona || persona,
            language
          );
          setContract(liveContract);
          setOrbState('speaking');

          const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          setHistory((prev) => [
            ...prev,
            {
              id: liveContract.turn_id,
              question: target.question,
              contract: liveContract,
              timestamp: now,
            },
          ]);
          setCurrentHistoryIndex(history.length);

          setMessages((prev) => [
            ...prev,
            { id: `u_${Date.now()}`, role: 'user', text: target.question, timestamp: now },
            {
              id: `a_${Date.now()}`,
              role: 'agent',
              spokenSummary: liveContract.spoken_summary,
              text: liveContract.display_text,
              timestamp: now,
              suggestions: liveContract.suggestions,
              accessStatus: liveContract.access.status,
            },
          ]);

          setTimeout(() => {
            setOrbState('idle');
          }, 2400);
          return;
        } catch (e) {
          console.warn('[LiveMode] Turn fallback to fixture:', e);
        }
      }

      // Mock Mode Fallback
      setTimeout(() => {
        setContract(target.data);
        setOrbState('speaking');

        setHistory((prev) => {
          const exists = prev.findIndex((h) => h.id === target.id);
          if (exists >= 0) {
            setCurrentHistoryIndex(exists);
            return prev;
          }
          const nextHist = [
            ...prev,
            {
              id: target.id,
              question: target.question,
              contract: target.data,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ];
          setCurrentHistoryIndex(nextHist.length - 1);
          return nextHist;
        });

        const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        setMessages((prev) => [
          ...prev,
          { id: `msg_u_${Date.now()}`, role: 'user', text: target.question, timestamp: now },
          {
            id: `msg_a_${Date.now()}`,
            role: 'agent',
            spokenSummary: target.data.spoken_summary,
            text: target.data.display_text,
            timestamp: now,
            suggestions: target.data.suggestions,
            accessStatus: target.data.access.status,
          },
        ]);

        setTimeout(() => {
          setOrbState(isMicActive ? 'listening' : 'idle');
        }, 2200);
      }, 400);
    },
    [persona, isLiveMode, backendHealthy, language, history.length, isMicActive]
  );

  // Handle User Input Submission (typed input or starter chip)
  const handleUserQuery = useCallback(
    async (queryText: string) => {
      // Barge-in: immediately stop playback
      audioEngineRef.current?.stopPlayback();

      const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      setMessages((prev) => [
        ...prev,
        { id: `msg_u_${Date.now()}`, role: 'user', text: queryText, timestamp: now },
      ]);

      setOrbState('thinking');
      const t0 = performance.now();

      // 1. Live ADK Backend Execution
      if (isLiveMode && backendHealthy) {
        try {
          const liveContract = await Promise.race([
            yuktiClient.executeTurnRest(queryText, persona, language),
            new Promise<never>((_, reject) =>
              setTimeout(() => reject(new Error('Turn timeout after 120s')), 120000)
            ),
          ]);
          setLastVisualLatency(Math.round(performance.now() - t0));
          setContract(liveContract);
          setOrbState('speaking');

          if (liveContract.language) {
            setLanguage(liveContract.language);
          }

          setHistory((prev) => [
            ...prev,
            {
              id: liveContract.turn_id,
              question: queryText,
              contract: liveContract,
              timestamp: now,
            },
          ]);
          setCurrentHistoryIndex(history.length);

          setMessages((prev) => [
            ...prev,
            {
              id: liveContract.turn_id || `msg_a_${Date.now()}`,
              role: 'agent',
              spokenSummary: liveContract.spoken_summary,
              text: liveContract.display_text,
              timestamp: now,
              suggestions: liveContract.suggestions,
              accessStatus: liveContract.access?.status,
              sources: liveContract.sources,
            },
          ]);

          setTimeout(() => {
            setOrbState(isMicActive ? 'listening' : 'idle');
          }, 2400);
          return;
        } catch (e: any) {
          console.warn('[LiveTurn] Backend error:', e);
          setOrbState('idle');
          setMessages((prev) => [
            ...prev,
            {
              id: `msg_err_${Date.now()}`,
              role: 'agent',
              text: `Backend communication error (${e?.message || 'timeout'}). Showing closest verified answer.`,
              timestamp: now,
            },
          ]);
        }
      }

      // 2. Mock Router Execution
      const { fixture, contract: resultContract } = routeQueryToFixture(queryText, persona);

      setTimeout(() => {
        setContract(resultContract);
        setOrbState('speaking');

        setHistory((prev) => [
          ...prev,
          {
            id: `hist_${Date.now()}`,
            question: queryText,
            contract: resultContract,
            timestamp: now,
          },
        ]);
        setCurrentHistoryIndex(history.length);

        setMessages((prev) => [
          ...prev,
          {
            id: `msg_a_${Date.now()}`,
            role: 'agent',
            spokenSummary: resultContract.spoken_summary,
            text: resultContract.display_text,
            timestamp: now,
            suggestions: resultContract.suggestions,
            accessStatus: resultContract.access.status,
            sources: resultContract.sources,
          },
        ]);

        setTimeout(() => {
          setOrbState(isMicActive ? 'listening' : 'idle');
        }, 2400);
      }, 500);
    },
    [isLiveMode, backendHealthy, persona, language, history.length, isMicActive]
  );

  // Toggle Microphone (Mic -> AudioWorklet 16 kHz PCM16 -> /ws/live)
  const handleToggleMic = useCallback(async () => {
    if (!audioEngineRef.current) return;

    if (isMicActive) {
      audioEngineRef.current.stopMic();
      if (isLiveMode) {
        yuktiClient.sendAudioStreamEndWs();
      }
      setIsMicActive(false);
      setOrbState('idle');
    } else {
      // Barge-in: stop any running audio playback
      audioEngineRef.current.stopPlayback();

      const ok = await audioEngineRef.current.startMic((chunk) => {
        if (isLiveMode) {
          yuktiClient.sendAudioChunkWs(chunk);
        }
      });

      if (ok) {
        setIsMicActive(true);
        setOrbState('listening');
        setMicDeniedNotice(false);
      } else {
        setMicDeniedNotice(true);
        setIsMicActive(false);
        setOrbState('idle');
      }
    }
  }, [isMicActive, isLiveMode]);

  // Handle Persona Change
  const handlePersonaChange = (p: PersonaType) => {
    setPersona(p);
    if (isLiveMode) {
      yuktiClient.sendConfigWs({ persona: p });
    }
  };

  // Keyboard navigation & shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement).tagName)) {
        return;
      }

      if (e.code === 'Space') {
        e.preventDefault();
        loadFixture(currentFixtureIndex < 0 ? 0 : currentFixtureIndex + 1);
      } else if (e.key === 'm' || e.key === 'M') {
        handleToggleMic();
      } else if (e.key === 't' || e.key === 'T') {
        setIsDark((d) => !d);
      } else if (e.key === 'f' || e.key === 'F') {
        setPanelMode((m) => (m === 'fullscreen' ? 'docked' : 'fullscreen'));
      } else if (e.key === 'Escape') {
        setPanelMode('docked');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentFixtureIndex, loadFixture, handleToggleMic]);

  const handleRestoreHistory = (item: HistoryItem, index: number) => {
    setContract(item.contract);
    setCurrentHistoryIndex(index);
  };

  const handleNavigateToAlternative = () => {
    handleUserQuery('What are the station tenure norms and aggregate due counts?');
  };

  return (
    <div
      className={`min-h-screen flex flex-col ${
        isDark ? 'bg-canvas-dark text-textPrimary-dark' : 'bg-canvas-light text-textPrimary-light'
      } transition-colors duration-200`}
    >
      {/* Top Navigation Bar */}
      <TopBar
        currentPersona={persona}
        onPersonaChange={handlePersonaChange}
        isDark={isDark}
        onThemeToggle={() => setIsDark((d) => !d)}
        language={language}
        onLanguageToggle={() => setLanguage((l) => (l === 'en' ? 'hi' : l === 'hi' ? 'hi-en' : 'en'))}
        state={orbState}
        onPrevDemo={() => loadFixture(currentFixtureIndex <= 0 ? 0 : currentFixtureIndex - 1)}
        onNextDemo={() => loadFixture(currentFixtureIndex < 0 ? 0 : currentFixtureIndex + 1)}
        currentDemoIndex={Math.max(0, currentFixtureIndex)}
        totalDemos={FIXTURES.length}
        isLiveMode={isLiveMode}
        onToggleLiveMode={() => setIsLiveMode((m) => !m)}
        backendHealthy={backendHealthy}
      />

      {/* Backend Offline Banner */}
      {isLiveMode && !backendHealthy && (
        <div className="bg-rose-600 text-white px-6 py-2 text-xs md:text-sm flex items-center justify-between shadow-md z-20">
          <div className="flex items-center gap-2 font-medium">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>
              Backend offline at <code>http://localhost:8095</code>. Running with local mock fallback.
            </span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={initBackendConnection}
              className="flex items-center gap-1 bg-white/20 hover:bg-white/30 px-2.5 py-1 rounded text-xs font-semibold transition-colors"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Retry</span>
            </button>
            <button
              onClick={() => setIsLiveMode(false)}
              className="bg-white text-rose-700 px-2.5 py-1 rounded text-xs font-bold hover:bg-rose-50 transition-colors"
            >
              Switch to Mock Mode
            </button>
          </div>
        </div>
      )}

      {/* Microphone Denied Notice */}
      {micDeniedNotice && (
        <div className="bg-amber-500 text-white px-6 py-1.5 text-xs flex items-center justify-between shadow-xs z-20">
          <div className="flex items-center gap-2 font-medium">
            <Radio className="w-3.5 h-3.5 shrink-0" />
            <span>Microphone permission denied. Switched automatically to typed input mode.</span>
          </div>
          <button onClick={() => setMicDeniedNotice(false)} className="text-xs font-bold underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Role Switching Notification Banner */}
      <PersonaBanner persona={persona} />

      {/* Main Work Area */}
      <div className="flex-1 relative flex overflow-hidden">
        {/* Full-width Canvas Area */}
        <main
          className={`flex-1 h-[calc(100vh-4rem)] transition-all duration-300 ${
            panelMode === 'fullscreen'
              ? 'hidden'
              : panelMode === 'docked'
              ? 'pr-0 lg:pr-[430px] xl:pr-[470px]'
              : 'pr-0'
          }`}
        >
          <CanvasView
            contract={contract}
            isDark={isDark}
            history={history}
            currentHistoryIndex={currentHistoryIndex}
            onRestoreHistory={handleRestoreHistory}
            onNavigateToAlternative={handleNavigateToAlternative}
            panelMode={panelMode}
            onSelectStarter={(q) => handleUserQuery(q)}
          />
        </main>

        {/* Floating Conversation Panel on the Right */}
        <FloatingConversationPanel
          panelMode={panelMode}
          onModeChange={setPanelMode}
          isDark={isDark}
          messages={messages}
          onSendMessage={handleUserQuery}
          orbState={orbState}
          onOrbClick={() => {
            if (panelMode === 'minimised') {
              setPanelMode('docked');
            } else {
              handleToggleMic();
            }
          }}
          isMicActive={isMicActive}
          onToggleMic={handleToggleMic}
          audioEngine={audioEngineRef.current || undefined}
          activeSuggestions={contract.suggestions}
          onSelectSuggestion={handleUserQuery}
        />
      </div>

      {/* Engineering Debug Overlay (?debug=1) */}
      {isDebugMode && (
        <div className="fixed bottom-4 left-4 z-50 bg-black/85 text-emerald-400 p-4 rounded-2xl border border-emerald-500/40 font-mono text-xs shadow-2xl backdrop-blur-md max-w-sm space-y-1 select-none">
          <div className="text-[10px] uppercase font-bold text-emerald-300 tracking-wider pb-1 border-b border-emerald-500/30">
            Yukti Live Telemetry (?debug=1)
          </div>
          <div>Audio TTFB (VAD End → 24k): <span className="font-bold text-white">{audioEngineRef.current?.getMeasuredAudioTtfb() ? `${audioEngineRef.current.getMeasuredAudioTtfb()} ms` : 'Waiting for mic...'}</span></div>
          <div>Visual Latency: <span className="font-bold text-white">{lastVisualLatency ? `${lastVisualLatency} ms` : '—'}</span></div>
          <div>Live Model: <span className="text-white">gemini-3.8-live</span></div>
          <div>Speech Voice: <span className="text-white">Leda (24 kHz PCM)</span></div>
          <div>Active Persona: <span className="text-white">{persona}</span></div>
          <div>Backend Status: <span className={backendHealthy ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>{backendHealthy ? "Connected (port 8095)" : "Offline"}</span></div>
        </div>
      )}
    </div>
  );
}
