/**
 * Yukti AI Real-Time WebSocket & REST Client
 * Integrates directly with FastAPI backend:
 * - WebSocket: /ws/live (bidi streaming: PCM16 16kHz in -> transcripts, 24kHz Leda audio, status_events, contracts)
 * - REST: /api/turn (fallback / text evaluation)
 * - REST: /api/export (Word, Excel, PDF, Google Docs)
 * - Health: /health
 */

import { AnswerContract } from '@/contracts/answerContract';

export interface YuktiStreamingEvents {
  connection_status: (status: { ready: boolean; session_id?: string; model?: string; voice?: string; persona?: string; language?: string }) => void;
  user_transcript: (data: { text: string; is_final: boolean }) => void;
  agent_transcript: (data: { text: string; is_final: boolean }) => void;
  status_event: (step: string) => void;
  tool_call_start: (tool: { name: string; args: any; timestamp_ms?: number }) => void;
  tool_call_done: (tool: { name: string; latency_ms?: number; response: any }) => void;
  contract: (contract: AnswerContract) => void;
  audio_chunk: (base64Pcm24k: string) => void;
  turn_complete: (metrics: any) => void;
  error: (err: Error) => void;
  close: () => void;
}

export class YuktiApiClient {
  private ws: WebSocket | null = null;
  private isWsConnected: boolean = false;
  private listeners: Map<keyof YuktiStreamingEvents, Set<Function>> = new Map();
  private wsBaseUrl: string;
  private apiBaseUrl: string;
  private currentSessionId: string;
  private reconnectTimer: any = null;

  constructor() {
    const isBrowser = typeof window !== 'undefined';
    const host = isBrowser ? window.location.hostname : 'localhost';

    // Default to port 8095 for local backend instance
    const defaultBackendUrl = `http://${host}:8095`;
    const defaultWsUrl = `ws://${host}:8095/ws/live`;

    this.apiBaseUrl = process.env.NEXT_PUBLIC_BACKEND_URL || defaultBackendUrl;
    this.wsBaseUrl = process.env.NEXT_PUBLIC_WS_URL || defaultWsUrl;
    this.currentSessionId = `sess-${Date.now()}`;
  }

  public getSessionId(): string {
    return this.currentSessionId;
  }

  public setSessionId(id: string): void {
    this.currentSessionId = id;
  }

  public isConnected(): boolean {
    return this.isWsConnected;
  }

  /**
   * Checks backend health
   */
  public async checkHealth(): Promise<{ healthy: boolean; data?: any }> {
    try {
      const res = await fetch(`${this.apiBaseUrl}/health`, { signal: AbortSignal.timeout(3000) });
      if (res.ok) {
        const data = await res.json();
        return { healthy: true, data };
      }
      return { healthy: false };
    } catch (e) {
      return { healthy: false };
    }
  }

  /**
   * Connects to /ws/live
   */
  public async connectWs(options?: { persona?: string; language?: string; voice?: string }): Promise<boolean> {
    if (typeof window === 'undefined') return false;

    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return true;
    }

    return new Promise((resolve) => {
      try {
        const persona = options?.persona || 'CMD';
        const language = options?.language || 'en';
        const voice = options?.voice || 'Leda';
        const url = `${this.wsBaseUrl}?session_id=${this.currentSessionId}&persona=${persona}&language=${language}&voice=${voice}`;

        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
          this.isWsConnected = true;
          this.emit('connection_status', { ready: true, session_id: this.currentSessionId, persona, language, voice });
          resolve(true);
        };

        this.ws.onmessage = (event) => {
          try {
            if (typeof event.data === 'string') {
              const msg = JSON.parse(event.data);
              const type = msg.type;

              if (type === 'connection_status') {
                this.emit('connection_status', { ready: msg.status === 'ready', ...msg });
              } else if (type === 'contract' && msg.contract) {
                this.emit('contract', msg.contract);
              } else if (type === 'user_transcript') {
                this.emit('user_transcript', { text: msg.text, is_final: !!msg.is_final });
              } else if (type === 'agent_transcript') {
                this.emit('agent_transcript', { text: msg.text, is_final: !!msg.is_final });
              } else if (type === 'audio' && msg.data) {
                this.emit('audio_chunk', msg.data);
              } else if (type === 'tool_call_start') {
                this.emit('tool_call_start', { name: msg.tool, args: msg.args, timestamp_ms: msg.timestamp_ms });
                this.emit('status_event', `Querying tool: ${msg.tool}...`);
              } else if (type === 'tool_call_done') {
                this.emit('tool_call_done', { name: msg.tool, latency_ms: msg.latency_ms, response: msg.response });
                // If response contains chart_spec or visual data, synthesize into contract
                if (msg.response && (msg.response.chart_spec || msg.response.document || msg.response.clause)) {
                  this.emit('status_event', `Rendering ${msg.response.chart_kind || 'visual'}...`);
                }
              } else if (type === 'turn_complete') {
                this.emit('turn_complete', msg.metrics || {});
              } else if (type === 'error') {
                this.emit('error', new Error(msg.error || 'Server streaming error'));
              }
            }
          } catch (e) {
            console.warn('[YuktiApiClient] WS message parsing error:', e);
          }
        };

        this.ws.onerror = (err) => {
          this.isWsConnected = false;
          this.emit('error', new Error('WebSocket connection failed'));
          resolve(false);
        };

        this.ws.onclose = () => {
          this.isWsConnected = false;
          this.emit('close');
        };
      } catch (err) {
        this.isWsConnected = false;
        resolve(false);
      }
    });
  }

  public disconnectWs(): void {
    if (this.ws) {
      try {
        this.ws.close();
      } catch (e) {}
      this.ws = null;
      this.isWsConnected = false;
    }
  }

  /**
   * Sends text query over WebSocket
   */
  public sendTextWs(text: string): boolean {
    if (this.ws && this.isWsConnected) {
      this.ws.send(JSON.stringify({ type: 'text', text }));
      return true;
    }
    return false;
  }

  /**
   * Sends PCM16 16 kHz audio chunk from mic over WebSocket
   */
  public sendAudioChunkWs(pcm16Buffer: ArrayBuffer): boolean {
    if (this.ws && this.isWsConnected) {
      const bytes = new Uint8Array(pcm16Buffer);
      let binary = '';
      for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
      }
      const b64 = btoa(binary);
      this.ws.send(JSON.stringify({ type: 'audio', data: b64 }));
      return true;
    }
    return false;
  }

  /**
   * Sends audio stream end event
   */
  public sendAudioStreamEndWs(): void {
    if (this.ws && this.isWsConnected) {
      this.ws.send(JSON.stringify({ type: 'audio_stream_end' }));
    }
  }

  /**
   * Updates session configuration (persona, language, voice)
   */
  public sendConfigWs(config: { persona?: string; language?: string; voice?: string }): void {
    if (this.ws && this.isWsConnected) {
      this.ws.send(JSON.stringify({ type: 'config', ...config }));
    }
  }

  /**
   * Executes a text turn through REST /api/turn with automatic retry on 429 quota exhaustion
   */
  public async executeTurnRest(
    query: string,
    persona: string = 'CMD',
    language: string = 'en',
    maxRetries: number = 3
  ): Promise<AnswerContract> {
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const res = await fetch(`${this.apiBaseUrl}/api/turn`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query,
            persona,
            language,
            session_id: this.currentSessionId,
          }),
        });

        if (res.status === 429 || res.status === 503) {
          if (attempt < maxRetries) {
            console.warn(`[YuktiApiClient] 429 Quota Exhausted on attempt ${attempt + 1}. Retrying in 3s...`);
            await new Promise((r) => setTimeout(r, 3000));
            continue;
          }
        }

        if (!res.ok) {
          const errText = await res.text();
          throw new Error(`Turn execution failed (${res.status}): ${errText}`);
        }

        const contract: AnswerContract = await res.json();
        // If contract is an internal error contract due to 429, retry
        if (
          contract.spoken_summary?.toLowerCase().includes('quota') ||
          contract.spoken_summary?.toLowerCase().includes('resource_exhausted') ||
          contract.spoken_summary?.toLowerCase().includes('rate limit')
        ) {
          if (attempt < maxRetries) {
            console.warn(`[YuktiApiClient] Internal quota error in contract on attempt ${attempt + 1}. Retrying in 3s...`);
            await new Promise((r) => setTimeout(r, 3500));
            continue;
          }
        }

        return contract;
      } catch (err) {
        if (attempt < maxRetries) {
          await new Promise((r) => setTimeout(r, 2500));
          continue;
        }
        throw err;
      }
    }
    throw new Error('Turn failed after retries');
  }

  /**
   * Calls /api/export
   */
  public async exportFile(req: {
    format: string;
    title: string;
    content?: string;
    columns?: string[];
    rows?: any[];
  }): Promise<{ status: string; file?: string; format: string; url?: string; mode?: string }> {
    const res = await fetch(`${this.apiBaseUrl}/api/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Export failed (${res.status}): ${err}`);
    }

    return await res.json();
  }

  public on<K extends keyof YuktiStreamingEvents>(event: K, handler: YuktiStreamingEvents[K]): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(handler);
  }

  public off<K extends keyof YuktiStreamingEvents>(event: K, handler: YuktiStreamingEvents[K]): void {
    if (this.listeners.has(event)) {
      this.listeners.get(event)!.delete(handler);
    }
  }

  private emit<K extends keyof YuktiStreamingEvents>(event: K, ...args: Parameters<YuktiStreamingEvents[K]>): void {
    const handlers = this.listeners.get(event);
    if (handlers) {
      handlers.forEach((h) => {
        try {
          (h as any)(...args);
        } catch (e) {
          console.error(`[YuktiApiClient] Listener error for ${event}:`, e);
        }
      });
    }
  }
}

// Singleton client instance
export const yuktiClient = new YuktiApiClient();
