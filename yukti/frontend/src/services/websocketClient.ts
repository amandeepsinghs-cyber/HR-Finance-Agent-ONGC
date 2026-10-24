/**
 * Yukti AI real-time client (single origin).
 * All traffic goes through the UI origin and is proxied by server.js:
 *   WebSocket  /ws/live   (PCM16 16 kHz in -> transcripts, 24 kHz Leda audio, status, contract)
 *   REST       /api/turn  (typed turns)
 *   REST       /api/export, /api/export/{id}
 *   Health     /health
 */

import { AnswerContract } from '@/contracts/answerContract';

export type WsState = 'idle' | 'connecting' | 'open' | 'closed' | 'error';

export interface YuktiStreamingEvents {
  ws_state: (state: WsState) => void;
  connection_status: (status: { ready: boolean; session_id?: string; model?: string; voice?: string; persona?: string; language?: string }) => void;
  user_transcript: (data: { text: string; is_final: boolean }) => void;
  agent_transcript: (data: { text: string; is_final: boolean }) => void;
  status_event: (step: string) => void;
  tool_call_start: (tool: { name: string; args: any; timestamp_ms?: number }) => void;
  tool_call_done: (tool: { name: string; latency_ms?: number; response: any }) => void;
  contract: (contract: AnswerContract) => void;
  ui_action: (action: { action?: string; command: string; value: string }) => void;
  audio_chunk: (base64Pcm24k: string) => void;
  interrupted: (data?: { speak_id?: string | null }) => void;
  turn_complete: (metrics: any) => void;
  error: (err: { message: string; retryable?: boolean }) => void;
}

export interface WsCounters {
  audioChunksSent: number;
  audioBytesSent: number;
  audioChunksReceived: number;
  audioBytesReceived: number;
  messagesReceived: number;
}

const TOOL_LABELS: Record<string, string> = {
  ask_yukti: 'Analyzing ONGC enterprise data',
  ui_control: 'Updating screen view',
  control_screen: 'Updating screen view',
  query_data: 'Querying enterprise data',
  run_certified_query: 'Running certified query',
  search_policy: 'Reading policy documents',
  what_if: 'Running the scenario model',
  draft_document: 'Drafting the document',
  export_document: 'Preparing the export',
};

export function humanToolLabel(name?: string): string {
  if (!name) return 'Working';
  return TOOL_LABELS[name] || name.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
}

export class YuktiApiClient {
  private ws: WebSocket | null = null;
  private state: WsState = 'idle';
  private listeners: Map<keyof YuktiStreamingEvents, Set<Function>> = new Map();
  private sessionId: string;
  private pending: string[] = [];
  // persona is advisory only (the server reads it from the signed session); never default to CMD (P2H.2 G4 M3)
  private opts = { persona: '', language: 'en', voice: 'Leda' };
  private wantOpen = false;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  /** Backend fell back to text-only mode (connection_status: degraded): socket open but voice ignored. */
  private voiceDegraded = false;
  public counters: WsCounters = { audioChunksSent: 0, audioBytesSent: 0, audioChunksReceived: 0, audioBytesReceived: 0, messagesReceived: 0 };

  constructor() {
    this.sessionId = `sess-${Date.now()}`;
  }

  public getSessionId(): string {
    return this.sessionId;
  }

  public getState(): WsState {
    return this.state;
  }

  /** True only when Gemini Live actually owns spoken turns (socket open and not in text fallback). */
  public isLiveVoiceReady(): boolean {
    return this.state === 'open' && !this.voiceDegraded;
  }

  /** "New session" (U2.6): fresh session id so the backend starts with no conversation context. */
  public resetSession(): string {
    const wasWanted = this.wantOpen;
    this.disconnect();
    this.sessionId = `sess-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    this.voiceDegraded = false;
    if (wasWanted) void this.connect();
    return this.sessionId;
  }

  /** Switch to a profile-specific session ID and persona so each profile has an isolated conversation. */
  public switchPersonaSession(sessionId: string, persona: string): string {
    const wasWanted = this.wantOpen;
    this.disconnect();
    this.sessionId = sessionId;
    this.opts = { ...this.opts, persona };
    this.voiceDegraded = false;
    if (wasWanted) void this.connect({ persona });
    return this.sessionId;
  }

  private wsUrl(): string {
    const loc = window.location;
    const proto = loc.protocol === 'https:' ? 'wss:' : 'ws:';
    const q = new URLSearchParams({ session_id: this.sessionId, ...this.opts });
    return `${proto}//${loc.host}/ws/live?${q.toString()}`;
  }

  private setState(s: WsState) {
    this.state = s;
    this.emit('ws_state', s);
  }

  public async checkHealth(timeoutMs = 4000): Promise<{ healthy: boolean; data?: any }> {
    try {
      const res = await fetch('/health', { signal: AbortSignal.timeout(timeoutMs), cache: 'no-store' });
      if (!res.ok) return { healthy: false };
      return { healthy: true, data: await res.json() };
    } catch {
      return { healthy: false };
    }
  }

  /** Open (or reuse) the live socket. Resolves when open or on failure. */
  public connect(options?: Partial<{ persona: string; language: string; voice: string }>): Promise<boolean> {
    if (typeof window === 'undefined') return Promise.resolve(false);
    if (options) this.opts = { ...this.opts, ...options } as any;
    this.wantOpen = true;
    if (this.ws && (this.ws.readyState === WebSocket.OPEN)) return Promise.resolve(true);
    if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
      return new Promise((resolve) => {
        const ws = this.ws!;
        ws.addEventListener('open', () => resolve(true), { once: true });
        ws.addEventListener('close', () => resolve(false), { once: true });
      });
    }
    return new Promise((resolve) => {
      this.setState('connecting');
      let ws: WebSocket;
      try {
        ws = new WebSocket(this.wsUrl());
      } catch {
        this.setState('error');
        resolve(false);
        return;
      }
      this.ws = ws;
      ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.setState('open');
        const q = this.pending;
        this.pending = [];
        q.forEach((m) => ws.send(m));
        resolve(true);
      };
      ws.onmessage = (ev) => {
        if (this.ws !== ws) return; // late frames from a replaced / reset session socket (U2.6)
        this.handleMessage(ev);
      };
      ws.onerror = () => {
        if (this.ws !== ws) return; // stale socket (after reconfigure/disconnect): ignore (U3.6)
        this.setState('error');
      };
      ws.onclose = () => {
        if (this.ws !== ws) {
          resolve(false);
          return; // a late close from a replaced socket must not mark the new one closed or reconnect
        }
        this.ws = null;
        this.voiceDegraded = false;
        this.setState('closed');
        resolve(false);
        if (this.wantOpen) this.scheduleReconnect();
      };
    });
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    const delay = Math.min(10000, 800 * 2 ** this.reconnectAttempts);
    this.reconnectAttempts += 1;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      if (this.wantOpen) void this.connect();
    }, delay);
  }

  /** Close the socket on purpose (no auto-reconnect). */
  public disconnect(): void {
    this.wantOpen = false;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
    this.pending = [];
    this.voiceDegraded = false;
    if (this.ws) {
      try {
        this.ws.close();
      } catch {}
      this.ws = null;
    }
    this.setState('idle');
  }

  /** Re-open with new session parameters (persona / language), keeping the same session id. */
  public async reconfigure(options: Partial<{ persona: string; language: string; voice: string }>): Promise<void> {
    const changed = Object.entries(options).some(([k, v]) => (this.opts as any)[k] !== v);
    this.opts = { ...this.opts, ...options } as any;
    if (!changed) return;
    if (this.ws) {
      const wasWanted = this.wantOpen;
      this.disconnect();
      if (wasWanted) await this.connect();
    }
  }

  private handleMessage(event: MessageEvent) {
    if (typeof event.data !== 'string') return;
    this.counters.messagesReceived += 1;
    let msg: any;
    try {
      msg = JSON.parse(event.data);
    } catch {
      return;
    }
    switch (msg.type) {
      case 'connection_status':
        this.voiceDegraded = msg.status === 'degraded';
        this.emit('connection_status', { ready: msg.status === 'ready', ...msg });
        break;
      case 'contract':
        if (msg.contract) {
          this.emit('contract', msg.contract);
          if ((msg.contract as any).ui_action) {
            this.emit('ui_action', (msg.contract as any).ui_action);
          }
        }
        break;
      case 'ui_action':
        this.emit('ui_action', {
          action: msg.action || '',
          command: msg.command || msg.action || '',
          value: msg.value || '',
        });
        break;
      case 'action':
        // The backend always pairs every {type:'action', kind:'ui_control'} with a legacy
        // {type:'ui_action'} message. Emitting here too made every voice UI command
        // (export, go back, chart switch) fire twice, so 'action' is intentionally ignored.
        break;
      case 'user_transcript':
        this.emit('user_transcript', { text: msg.text || '', is_final: !!msg.is_final });
        break;
      case 'agent_transcript':
        this.emit('agent_transcript', { text: msg.text || '', is_final: !!msg.is_final });
        break;
      case 'audio':
        if (msg.data) {
          this.counters.audioChunksReceived += 1;
          this.counters.audioBytesReceived += Math.floor((msg.data.length * 3) / 4);
          this.emit('audio_chunk', msg.data);
        }
        break;
      case 'status_event':
        // Backend sends tool-level detail; the UI shows a human label via tool_call_start.
        break;
      case 'tool_call_start':
        this.emit('tool_call_start', { name: msg.tool, args: msg.args, timestamp_ms: msg.timestamp_ms });
        this.emit('status_event', `${humanToolLabel(msg.tool)}…`);
        break;
      case 'tool_call_done':
        this.emit('tool_call_done', { name: msg.tool, latency_ms: msg.latency_ms, response: msg.response });
        break;
      case 'interrupted':
        this.emit('interrupted', { speak_id: msg.speak_id ?? null }); // P0.10
        break;
      case 'turn_complete':
        this.emit('turn_complete', { ...(msg.metrics || {}), speak_id: msg.speak_id ?? msg.metrics?.speak_id ?? null }); // P0.10
        break;
      case 'error':
        this.emit('error', { message: msg.message || msg.error || 'Live session error', retryable: msg.retryable });
        break;
      default:
        break;
    }
  }

  private send(obj: any): boolean {
    const data = JSON.stringify(obj);
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(data);
      return true;
    }
    if (this.wantOpen) {
      // Buffer briefly while (re)connecting; cap at ~5 s of audio.
      if (this.pending.length < 60) this.pending.push(data);
      return true;
    }
    return false;
  }

  public sendText(text: string): boolean {
    return this.send({ type: 'text', text });
  }

  /** Voice a REST answer through Gemini Live. P0.10: `speakId` lets the server and UI tie the speak's
   *  turn_complete / interruption to this request (an interrupt never ends a different, still-running speak). */
  public sendSpeak(text: string, speakId?: string): boolean {
    if (!text.trim()) return false;
    return this.send({ type: 'speak', text: text.trim(), ...(speakId ? { speak_id: speakId } : {}) });
  }

  public sendContext(uiState: Record<string, any>): boolean {
    return this.send({ type: 'context', ui_state: uiState });
  }

  public sendAudioChunk(pcm16: ArrayBuffer): boolean {
    const bytes = new Uint8Array(pcm16);
    let bin = '';
    const step = 0x8000;
    for (let i = 0; i < bytes.length; i += step) {
      bin += String.fromCharCode.apply(null, Array.from(bytes.subarray(i, i + step)));
    }
    const ok = this.send({ type: 'audio', data: btoa(bin) });
    if (ok) {
      this.counters.audioChunksSent += 1;
      this.counters.audioBytesSent += bytes.length;
    }
    return ok;
  }

  /** Barge-in (U3.4): ask the server to stop the current reply. */
  public sendInterrupt(): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return false;
    this.ws.send(JSON.stringify({ type: 'interrupt' }));
    return true;
  }

  public sendAudioStreamEnd(): void {
    this.send({ type: 'audio_stream_end' });
  }

  /** Typed turn via REST, with retry on 429/503. */
  public async executeTurnRest(
    query: string,
    persona = '',
    language = 'en',
    maxRetries = 2,
    signal?: AbortSignal,
    history?: { role: string; text: string }[],
    uiContext?: Record<string, any>,
  ): Promise<AnswerContract> {
    let lastErr: any = null;
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const res = await fetch('/api/turn', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query,
            persona,
            language,
            session_id: this.sessionId,
            history: history || [],
            ui_context: uiContext || {},
          }),
          signal,
        });
        if ((res.status === 429 || res.status === 503) && attempt < maxRetries) {
          await new Promise((r) => setTimeout(r, 2500));
          continue;
        }
        if (!res.ok) {
          let message = `HTTP ${res.status}`;
          try {
            const j = await res.json();
            message = j?.message || j?.detail?.message || message;
          } catch {}
          throw new Error(message);
        }
        return (await res.json()) as AnswerContract;
      } catch (err: any) {
        lastErr = err;
        if (signal?.aborted) throw err;
        if (attempt < maxRetries && !/HTTP 4\d\d/.test(String(err?.message))) {
          await new Promise((r) => setTimeout(r, 1500));
          continue;
        }
      }
    }
    throw lastErr || new Error('Turn failed');
  }

  public async exportFile(req: { format: string; title: string; content?: string; columns?: string[]; rows?: any[] }): Promise<any> {
    const res = await fetch('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    if (!res.ok) throw new Error(`Export failed (${res.status})`);
    return res.json();
  }

  public on<K extends keyof YuktiStreamingEvents>(event: K, handler: YuktiStreamingEvents[K]): void {
    if (!this.listeners.has(event)) this.listeners.set(event, new Set());
    this.listeners.get(event)!.add(handler);
  }

  public off<K extends keyof YuktiStreamingEvents>(event: K, handler: YuktiStreamingEvents[K]): void {
    this.listeners.get(event)?.delete(handler);
  }

  private emit<K extends keyof YuktiStreamingEvents>(event: K, ...args: Parameters<YuktiStreamingEvents[K]>): void {
    this.listeners.get(event)?.forEach((h) => {
      try {
        (h as any)(...args);
      } catch (e) {
        console.warn(`[yukti] listener error for ${String(event)}`, e);
      }
    });
  }
}

export const yuktiClient = new YuktiApiClient();
