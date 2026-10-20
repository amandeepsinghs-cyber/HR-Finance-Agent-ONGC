'use client';

import React, { useState, useRef, useEffect } from 'react';
import { AnswerContract, SourceCitation } from '@/contracts/answerContract';
import { VoiceOrb, OrbState } from './VoiceOrb';
import { VoiceAudioEngine } from '@/services/audioAnalyser';
import {
  Minus,
  Maximize2,
  Minimize2,
  Mic,
  MicOff,
  Send,
  Sparkles,
  Volume2,
  ChevronRight,
  ShieldAlert,
} from 'lucide-react';

export interface ChatMessage {
  id: string;
  role: 'user' | 'agent' | 'status';
  text: string;
  spokenSummary?: string;
  timestamp: string;
  suggestions?: string[];
  accessStatus?: string;
  sources?: SourceCitation[];
}

interface FloatingConversationPanelProps {
  panelMode: 'docked' | 'minimised' | 'fullscreen';
  onModeChange: (mode: 'docked' | 'minimised' | 'fullscreen') => void;
  isDark: boolean;
  messages: ChatMessage[];
  onSendMessage: (text: string) => void;
  orbState: OrbState;
  onOrbClick: () => void;
  isMicActive: boolean;
  onToggleMic: () => void;
  audioEngine?: VoiceAudioEngine;
  activeSuggestions?: string[];
  onSelectSuggestion: (s: string) => void;
}

export const FloatingConversationPanel: React.FC<FloatingConversationPanelProps> = ({
  panelMode,
  onModeChange,
  isDark,
  messages,
  onSendMessage,
  orbState,
  onOrbClick,
  isMicActive,
  onToggleMic,
  audioEngine,
  activeSuggestions = [],
  onSelectSuggestion,
}) => {
  const [inputText, setInputText] = useState('');
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  // When minimised, collapse to the floating Voice Orb in the bottom right corner
  if (panelMode === 'minimised') {
    return (
      <div className="fixed bottom-6 right-6 z-40 flex flex-col items-center select-none animate-in zoom-in-75 duration-200">
        <div className="relative group">
          <VoiceOrb
            state={orbState}
            isDark={isDark}
            size={110}
            onClick={() => onModeChange('docked')}
            interactive={true}
            audioEngine={audioEngine}
            className="shadow-2xl rounded-full bg-white/90 dark:bg-zinc-900/90 backdrop-blur-md border border-accent/30 hover:ring-4 hover:ring-accent/20 transition-all"
          />
          <button
            onClick={() => onModeChange('docked')}
            className="absolute -top-1 -right-1 p-1.5 rounded-full bg-accent text-white shadow-lg hover:scale-110 transition-transform text-xs"
            title="Expand Conversation"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
        </div>
        <span className="text-[11px] font-semibold text-zinc-500 dark:text-zinc-400 mt-2 bg-white/80 dark:bg-zinc-900/80 px-2 py-0.5 rounded-md backdrop-blur-sm shadow-xs">
          Tap orb to expand
        </span>
      </div>
    );
  }

  // Width classes based on docked vs fullscreen
  const panelClasses =
    panelMode === 'fullscreen'
      ? 'w-full h-[calc(100vh-4rem)] max-w-4xl mx-auto rounded-3xl border shadow-2xl'
      : 'w-full lg:w-[420px] xl:w-[460px] h-[calc(100vh-5.5rem)] rounded-3xl border shadow-panel dark:shadow-panel-dark my-3 mr-4';

  return (
    <aside
      className={`fixed top-16 right-0 z-30 flex flex-col transition-all duration-300 backdrop-blur-xl ${
        isDark ? 'bg-zinc-900/95 border-zinc-800' : 'bg-white/95 border-zinc-200/90'
      } ${panelClasses}`}
    >
      {/* Panel Header */}
      <div className="px-5 py-3.5 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-2.5 h-2.5 rounded-full bg-accent animate-pulse" />
          <div>
            <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-1.5">
              <span>Yukti Voice Assistant</span>
              <span className="text-[10px] font-medium text-accent bg-accent/10 px-1.5 py-0.5 rounded">
                Leda Voice
              </span>
            </h3>
            <div className="text-[11px] text-zinc-500 dark:text-zinc-400">
              Spoken dialogue & instant drafting
            </div>
          </div>
        </div>

        {/* Panel Mode Controls (Minimise & Full Screen) */}
        <div className="flex items-center gap-1 text-zinc-500">
          <button
            onClick={() => onModeChange('minimised')}
            className="p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            title="Minimise to Voice Orb only"
          >
            <Minus className="w-4 h-4" />
          </button>
          <button
            onClick={() => onModeChange(panelMode === 'fullscreen' ? 'docked' : 'fullscreen')}
            className="p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            title={panelMode === 'fullscreen' ? 'Restore Docked View' : 'Full Screen View'}
          >
            {panelMode === 'fullscreen' ? (
              <Minimize2 className="w-4 h-4" />
            ) : (
              <Maximize2 className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Center Voice Orb Zone */}
      <div className="flex flex-col items-center justify-center pt-3 pb-2 shrink-0 border-b border-zinc-100 dark:border-zinc-800/80 bg-zinc-50/50 dark:bg-zinc-900/40">
        <VoiceOrb
          state={orbState}
          isDark={isDark}
          size={160}
          onClick={onOrbClick}
          interactive={true}
          audioEngine={audioEngine}
        />
        <div className="text-center mt-1">
          <div className="text-xs font-semibold text-zinc-700 dark:text-zinc-200">
            {orbState === 'listening'
              ? 'Listening to microphone...'
              : orbState === 'thinking'
              ? 'Consulting ONGC Data Lake...'
              : orbState === 'speaking'
              ? 'Leda is speaking...'
              : 'Tap orb or press Space to ask'}
          </div>
          <div className="text-[10px] text-zinc-400">
            Hands-free audio active · Hindi & English
          </div>
        </div>
      </div>

      {/* Running Thread of Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3.5 text-xs md:text-sm">
        {messages.map((msg) => {
          const isUser = msg.role === 'user';
          const isStatus = msg.role === 'status';

          if (isStatus) {
            return (
              <div
                key={msg.id}
                className="flex items-center justify-center gap-2 py-1 text-[11px] text-accent animate-pulse font-medium"
              >
                <Sparkles className="w-3 h-3" />
                <span>{msg.text}</span>
              </div>
            );
          }

          return (
            <div
              key={msg.id}
              data-testid={isUser ? 'user-turn' : 'agent-turn'}
              data-turn-id={msg.id}
              className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} space-y-1`}
            >
              <div
                className={`max-w-[88%] p-3.5 rounded-2xl leading-relaxed ${
                  isUser
                    ? 'bg-accent text-white rounded-br-xs shadow-sm font-medium'
                    : isDark
                    ? 'bg-zinc-800/90 text-zinc-100 rounded-bl-xs border border-zinc-700/60'
                    : 'bg-zinc-100 text-zinc-900 rounded-bl-xs border border-zinc-200/80 shadow-xs'
                }`}
              >
                {/* Spoken Summary highlight (never read source citations) */}
                {!isUser && msg.spokenSummary && (
                  <div className="mb-2 pb-2 border-b border-zinc-200/60 dark:border-zinc-700/60 flex items-start gap-1.5 text-xs font-semibold text-accent dark:text-accent-secondary">
                    <Volume2 className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                    <span>&ldquo;{msg.spokenSummary.replace(/\s*\[\d+\]/g, '')}&rdquo;</span>
                  </div>
                )}

                {/* Display text (citation markers like [1] removed) */}
                <div>{msg.text.replace(/\s*\[\d+\]/g, '')}</div>

                {/* Collapsed Source Row at bottom of agent message */}
                {!isUser && msg.sources && msg.sources.length > 0 && (
                  <div className="mt-2.5 pt-2 border-t border-zinc-200/60 dark:border-zinc-700/60">
                    <button
                      type="button"
                      onClick={() =>
                        setExpandedSources((prev) => ({ ...prev, [msg.id]: !prev[msg.id] }))
                      }
                      className="flex items-center gap-1 text-[11px] font-semibold text-zinc-500 hover:text-accent dark:text-zinc-400 dark:hover:text-accent-secondary transition-colors"
                    >
                      <ChevronRight
                        className={`w-3 h-3 transition-transform duration-150 ${
                          expandedSources[msg.id] ? 'rotate-90' : ''
                        }`}
                      />
                      <span>Sources ({msg.sources.length})</span>
                    </button>
                    {expandedSources[msg.id] && (
                      <div className="mt-1.5 space-y-1 pl-3 border-l-2 border-accent/40 text-[11px] text-zinc-600 dark:text-zinc-300 animate-in fade-in duration-100">
                        {msg.sources.map((s, si) => (
                          <div key={si} className="truncate">
                            • {s.title || s.object || (s.clause ? `Clause ${s.clause}` : 'Source')}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Refusal indicator */}
                {!isUser && msg.accessStatus === 'refused' && (
                  <div className="mt-2 pt-2 border-t border-rose-200 dark:border-rose-900/60 flex items-center gap-1.5 text-rose-600 dark:text-rose-400 font-semibold text-xs">
                    <ShieldAlert className="w-3.5 h-3.5 shrink-0" />
                    <span>Deliberative Record Exemption Applied</span>
                  </div>
                )}
              </div>

              <span className="text-[10px] text-zinc-400 px-1">{msg.timestamp}</span>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Follow-up Suggestion Chips */}
      {activeSuggestions.length > 0 && (
        <div className="px-4 py-2 border-t border-zinc-100 dark:border-zinc-800 flex flex-wrap gap-1.5 shrink-0">
          {activeSuggestions.map((s, idx) => (
            <button
              key={idx}
              onClick={() => onSelectSuggestion(s)}
              className="text-xs font-medium px-2.5 py-1 rounded-full border border-accent/30 bg-blue-50/60 dark:bg-accent/10 hover:bg-accent hover:text-white dark:hover:bg-accent text-accent transition-colors flex items-center gap-1"
            >
              <span>{s}</span>
              <ChevronRight className="w-3 h-3 opacity-60" />
            </button>
          ))}
        </div>
      )}

      {/* Bottom Input & Mic Dock */}
      <div className="p-3.5 border-t border-zinc-200 dark:border-zinc-800 bg-white/60 dark:bg-zinc-900/60 shrink-0">
        <form onSubmit={handleSend} className="flex items-center gap-2">
          {/* Hands-free Mic Button (Shape-morphing Material 3 Expressive) */}
          <button
            type="button"
            onClick={onToggleMic}
            className={`p-2.5 rounded-2xl transition-all duration-300 shadow-md ${
              isMicActive
                ? 'bg-rose-600 text-white animate-pulse ring-4 ring-rose-400/30'
                : 'bg-accent text-white hover:bg-accent-dark ring-2 ring-accent/20'
            }`}
            title={isMicActive ? 'Mute Microphone' : 'Start Voice Input'}
          >
            {isMicActive ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
          </button>

          {/* Text Input */}
          <input
            type="text"
            placeholder="Ask question, instruct, or draft... (or press Space for next demo)"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            className={`flex-1 px-4 py-2.5 text-xs md:text-sm rounded-2xl border transition-all outline-none ${
              isDark
                ? 'bg-zinc-800 border-zinc-700 text-zinc-100 focus:border-accent'
                : 'bg-zinc-50 border-zinc-200 text-zinc-900 focus:border-accent'
            }`}
          />

          {/* Send Button */}
          <button
            type="submit"
            disabled={!inputText.trim()}
            className={`p-2.5 rounded-2xl transition-all ${
              inputText.trim()
                ? 'bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 shadow-md hover:scale-105'
                : 'bg-zinc-200 dark:bg-zinc-800 text-zinc-400 cursor-not-allowed'
            }`}
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </aside>
  );
};
