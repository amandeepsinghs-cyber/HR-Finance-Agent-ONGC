/**
 * Voice audio engine
 * 1. Capture: getUserMedia -> AudioWorklet (16 kHz PCM16, 100 ms frames + RMS level) -> callback
 * 2. Playback: 24 kHz PCM16 chunks -> gapless AudioBufferSource scheduler -> AnalyserNode
 * 3. Orb amplitude: live mic level (listening) / playback analyser (speaking)
 * 4. Barge-in: stopPlayback() halts all scheduled audio immediately and drops in-flight chunks
 * 5. Telemetry: bytes/chunks received, seconds scheduled, first-chunk timestamp
 */

export type MicErrorKind = 'insecure' | 'unsupported' | 'denied' | 'no-device' | 'busy' | 'other';

export interface MicStartResult {
  ok: boolean;
  error?: MicErrorKind;
  message?: string;
  /** true when stopMic() won the race against a pending start: not an error to show the user */
  cancelled?: boolean;
}

export interface PlaybackStats {
  chunks: number;
  bytes: number;
  scheduledSeconds: number;
  firstChunkAt: number | null;
  lastChunkAt: number | null;
}

export interface MicDeviceInfo {
  deviceId: string;
  label: string;
}

export class VoiceAudioEngine {
  // Capture
  private recordCtx: AudioContext | null = null;
  private micStream: MediaStream | null = null;
  private workletNode: AudioWorkletNode | null = null;
  private sinkGain: GainNode | null = null;
  private onPcm16Chunk: ((chunk: ArrayBuffer) => void) | null = null;
  private micLevel = 0; // smoothed 0..1 (display only)
  /** Raw per-frame mic RMS level 0..1 from the worklet: no floor, no synthetic cadence (U3.3). Used for barge-in. */
  private rawMicLevel = 0;
  /** In-flight startMic() promise (U3.5): concurrent calls share it instead of opening a second stream. */
  private startingPromise: Promise<MicStartResult> | null = null;
  private stopRequestedDuringStart = false;
  private recording = false;
  private preferredDeviceId: string | null = null;
  private activeDeviceLabel: string = '';
  private devices: MicDeviceInfo[] = [];
  private recognition: any = null;
  private recognitionWantActive = false;
  private flushRecognitionFn: (() => void) | null = null;
  private cancelRecognitionFn: (() => void) | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private recordedChunks: Blob[] = [];
  private recordedMimeType: string = 'audio/webm';
  private isMuted = false;
  private synthSpeaking = false;
  // P0.10 r2 (S-2): watchdogs so a missing onend/onended can never leave the mic gate closed forever
  private synthDeadlineMs = 0; // performance.now() after which a "speaking" synth is treated as finished
  private playEndWallMs = 0; // wall-clock estimate of when the last scheduled PCM chunk finishes

  // Playback
  private playCtx: AudioContext | null = null;
  private playAnalyser: AnalyserNode | null = null;
  private playFreq: Uint8Array | null = null;
  private nextPlayTime = 0;
  private activeSources: Set<AudioBufferSourceNode> = new Set();
  private onPlaybackEnded: (() => void) | null = null;
  private onPlaybackStarted: (() => void) | null = null;
  private onZeroSignal: ((deviceLabel: string) => void) | null = null;
  private dropIncoming = false;

  private stats: PlaybackStats = { chunks: 0, bytes: 0, scheduledSeconds: 0, firstChunkAt: null, lastChunkAt: null };
  private turnStats: PlaybackStats = { chunks: 0, bytes: 0, scheduledSeconds: 0, firstChunkAt: null, lastChunkAt: null };

  /** Must be called from a user gesture (click / keydown) so Chrome allows audio output. */
  public unlock(): void {
    const ctx = this.getPlayContext();
    if (ctx.state === 'suspended') void ctx.resume();
  }

  private getPlayContext(): AudioContext {
    if (!this.playCtx || this.playCtx.state === 'closed') {
      const Ctx = window.AudioContext || (window as any).webkitAudioContext;
      this.playCtx = new Ctx({ sampleRate: 24000 });
      this.playAnalyser = this.playCtx.createAnalyser();
      this.playAnalyser.fftSize = 256;
      this.playAnalyser.smoothingTimeConstant = 0.75;
      this.playFreq = new Uint8Array(this.playAnalyser.frequencyBinCount);
      this.nextPlayTime = this.playCtx.currentTime;
    }
    return this.playCtx;
  }

  public isRecording(): boolean {
    return this.recording;
  }

  public getMuted(): boolean {
    return this.isMuted;
  }

  public setMuted(m: boolean): void {
    this.isMuted = m;
    if (m) this.stopPlayback(true);
  }

  /** Speaks text immediately via browser SpeechSynthesis (female Indian/English voice) when Leda stream isn't active. */
  public speakBrowserTts(text: string, lang: 'en' | 'hi' | 'hi-en' = 'en'): void {
    if (typeof window === 'undefined' || this.isMuted || !('speechSynthesis' in window)) return;
    if (this.activeSources.size > 0) return; // Leda PCM stream is already playing
    try {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = lang === 'hi' ? 'hi-IN' : 'en-IN';
      u.rate = 1.03;
      u.pitch = 1.05;
      const voices = window.speechSynthesis.getVoices();
      const preferred =
        voices.find((v) => /hi-IN|en-IN/i.test(v.lang) && /female|lekha|veena|google|siri|heera|kalpana|neerja/i.test(v.name)) ||
        voices.find((v) => /en-IN|hi-IN/i.test(v.lang)) ||
        voices.find((v) => /female|samantha|victoria|google uk english female|zoe/i.test(v.name));
      if (preferred) u.voice = preferred;
      u.onstart = () => {
        this.synthSpeaking = true;
        this.synthDeadlineMs = performance.now() + (text.length / 12 + 3) * 1000; // ~12 chars/s + 3 s slack
        this.onPlaybackStarted?.();
      };
      u.onend = () => {
        this.synthSpeaking = false;
        if (this.activeSources.size === 0) this.onPlaybackEnded?.();
      };
      u.onerror = () => {
        this.synthSpeaking = false;
        if (this.activeSources.size === 0) this.onPlaybackEnded?.();
      };
      window.speechSynthesis.speak(u);
    } catch {}
  }

  /** Starts Chrome Web Speech API live speech recognition alongside PCM streaming. */
  public startSpeechRecognition(
    lang: 'en' | 'hi' | 'hi-en',
    onInterim: (text: string) => void,
    onFinalUtterance: (text: string) => void
  ): void {
    if (typeof window === 'undefined') return;
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) return;
    this.stopSpeechRecognition(false);
    this.recognitionWantActive = true;
    const launch = () => {
      if (!this.recognitionWantActive) return;
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return;
      try {
        const rec = new SR();
        rec.continuous = true;
        rec.interimResults = true;
        rec.lang = lang === 'hi' ? 'hi-IN' : 'en-IN';
        let consumedIndex = 0;
        let latestUncommitted = '';
        let silenceDebounce: ReturnType<typeof setTimeout> | null = null;
        let lastResultCount = 0;
        let cancelled = false; // set when this recognizer is stopped without flush (U3.6)
        let fatal = false;

        const commitUtterance = () => {
          if (silenceDebounce) {
            clearTimeout(silenceDebounce);
            silenceDebounce = null;
          }
          const committed = latestUncommitted.trim();
          if (committed && !cancelled) {
            latestUncommitted = '';
            consumedIndex = lastResultCount;
            onFinalUtterance(committed);
          }
        };
        this.flushRecognitionFn = commitUtterance;

        // U3.3: SpeechRecognition events no longer inject synthetic mic levels; the meter shows real RMS only.
        rec.onresult = (event: any) => {
          lastResultCount = event.results.length;
          const parts: string[] = [];
          for (let i = consumedIndex; i < event.results.length; i++) {
            const t = (event.results[i][0]?.transcript || '').trim();
            if (t) parts.push(t);
          }
          const combined = parts.join(' ').replace(/\s+/g, ' ').trim();
          if (combined) {
            latestUncommitted = combined;
            // If WebAudio PCM is near-zero on a virtual/CRD mic while SpeechRecognition hears words,
            // pulse the display-only micLevel (never rawMicLevel) so the orb visibly responds during speech.
            if (this.rawMicLevel < 0.05) {
              this.micLevel = Math.max(this.micLevel, 0.55);
            }
            onInterim(combined);
            if (silenceDebounce) clearTimeout(silenceDebounce);
            silenceDebounce = setTimeout(commitUtterance, 1250);
          }
        };
        rec.onerror = (ev: any) => {
          // Permanent permission/support errors must not relaunch in a loop; transient audio-capture/network hiccups retry.
          if (['not-allowed', 'service-not-allowed', 'language-not-supported'].includes(ev?.error)) fatal = true;
        };
        rec.onend = () => {
          if (silenceDebounce) {
            clearTimeout(silenceDebounce);
            silenceDebounce = null;
          }
          const clean = latestUncommitted.trim();
          if (clean && !cancelled) {
            latestUncommitted = '';
            onFinalUtterance(clean);
          } else if (
            !cancelled &&
            !fatal &&
            this.recognitionWantActive &&
            (typeof document === 'undefined' || document.visibilityState === 'visible')
          ) {
            setTimeout(launch, 250);
          }
        };
        rec.start();
        this.recognition = rec;
        this.cancelRecognitionFn = () => {
          cancelled = true;
          if (silenceDebounce) {
            clearTimeout(silenceDebounce);
            silenceDebounce = null;
          }
        };
      } catch {}
    };
    launch();
  }

  public stopSpeechRecognition(flush = true): void {
    this.recognitionWantActive = false;
    if (flush && this.flushRecognitionFn) {
      try {
        this.flushRecognitionFn();
      } catch {}
    }
    // Without flush, the stopped recognizer must never emit a late utterance (U3.6).
    this.cancelRecognitionFn?.();
    this.cancelRecognitionFn = null;
    this.flushRecognitionFn = null;
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch {}
      this.recognition = null;
    }
  }

  /** Stops MediaRecorder and resolves with a base64 audio string + mimeType. */
  public async getRecordedAudioBase64(): Promise<{ base64: string; mimeType: string } | null> {
    const mr = this.mediaRecorder;
    if (!mr) return null;
    return new Promise((resolve) => {
      const finalize = () => {
        const chunks = this.recordedChunks.slice();
        this.recordedChunks = [];
        this.mediaRecorder = null;
        if (chunks.length === 0) {
          resolve(null);
          return;
        }
        const blob = new Blob(chunks, { type: this.recordedMimeType });
        if (blob.size < 400) {
          resolve(null);
          return;
        }
        const reader = new FileReader();
        reader.onloadend = () => {
          const res = String(reader.result || '');
          const b64 = res.includes(',') ? res.split(',')[1] : '';
          resolve(b64 ? { base64: b64, mimeType: this.recordedMimeType } : null);
        };
        reader.onerror = () => resolve(null);
        reader.readAsDataURL(blob);
      };
      if (mr.state !== 'inactive') {
        mr.onstop = finalize;
        try {
          mr.stop();
        } catch {
          finalize();
        }
      } else {
        finalize();
      }
    });
  }

  public getDevices(): MicDeviceInfo[] {
    return this.devices;
  }

  public getActiveDeviceLabel(): string {
    return this.activeDeviceLabel;
  }

  public setPreferredDeviceId(deviceId: string | null): void {
    this.preferredDeviceId = deviceId;
  }

  public async refreshDevices(): Promise<MicDeviceInfo[]> {
    if (!navigator.mediaDevices?.enumerateDevices) return [];
    const list = await navigator.mediaDevices.enumerateDevices();
    this.devices = list
      .filter((d) => d.kind === 'audioinput')
      .map((d, idx) => ({
        deviceId: d.deviceId,
        label: d.label || `Microphone ${idx + 1}`,
      }));
    return this.devices;
  }

  public async startMic(onPcmChunk: (chunk: ArrayBuffer) => void, deviceIdOverride?: string): Promise<MicStartResult> {
    if (this.recording) return { ok: true };
    if (this.startingPromise) return this.startingPromise; // double-click: share the in-flight start
    this.stopRequestedDuringStart = false;
    this.startingPromise = this.startMicInner(onPcmChunk, deviceIdOverride).finally(() => {
      this.startingPromise = null;
    });
    const res = await this.startingPromise;
    if (res.ok && this.stopRequestedDuringStart) {
      // stopMic() was called while getUserMedia was pending: release everything now.
      // Callers that joined this same in-flight start (double-click) are cancelled too, which is intended:
      // the user's latest intent was "stop".
      this.stopMic();
      return { ok: false, error: 'other', message: 'Microphone start was cancelled.', cancelled: true };
    }
    return res;
  }

  private async startMicInner(onPcmChunk: (chunk: ArrayBuffer) => void, deviceIdOverride?: string): Promise<MicStartResult> {
    if (typeof window === 'undefined') return { ok: false, error: 'unsupported' };
    if (!window.isSecureContext) {
      return {
        ok: false,
        error: 'insecure',
        message: `The browser blocks the microphone on ${window.location.origin}. Open Yukti at http://localhost:3200 (port-forward 3200) or over HTTPS.`,
      };
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      return { ok: false, error: 'unsupported', message: 'This browser does not support microphone capture.' };
    }
    if (this.recording) return { ok: true };

    this.onPcm16Chunk = onPcmChunk;
    const targetDeviceId = deviceIdOverride ?? this.preferredDeviceId;
    try {
      // Exact Urvi (`wellpulse/frontend/src/live/micCapture.ts`) getUserMedia constraints:
      // never auto-override deviceId unless the user explicitly selected one from the dropdown.
      const audioConstraints: MediaTrackConstraints = {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      };
      if (targetDeviceId) {
        audioConstraints.deviceId = { exact: targetDeviceId };
      }
      this.micStream = await navigator.mediaDevices.getUserMedia({
        audio: audioConstraints,
        video: false,
      });
      await this.refreshDevices();
      const track = this.micStream.getAudioTracks()[0];
      if (track) {
        this.activeDeviceLabel = track.label || 'Default Microphone';
      }
    } catch (err: any) {
      const name = err?.name || '';
      if (name === 'NotAllowedError' || name === 'SecurityError') {
        return {
          ok: false,
          error: 'denied',
          message: 'Microphone access is blocked. Click the lock/tune icon in the address bar → Microphone → Allow, then try again.',
        };
      }
      if (name === 'NotFoundError' || name === 'OverconstrainedError') {
        return { ok: false, error: 'no-device', message: 'No microphone was found. Connect a microphone and try again.' };
      }
      if (name === 'NotReadableError' || name === 'AbortError') {
        return { ok: false, error: 'busy', message: 'The microphone is in use by another application.' };
      }
      return { ok: false, error: 'other', message: err?.message || 'Could not start the microphone.' };
    }

    try {
      const Ctx = window.AudioContext || (window as any).webkitAudioContext;
      this.recordCtx = new Ctx();
      if (this.recordCtx.state === 'suspended') await this.recordCtx.resume();
      const source = this.recordCtx.createMediaStreamSource(this.micStream);
      this.sinkGain = this.recordCtx.createGain();
      this.sinkGain.gain.value = 0;
      this.sinkGain.connect(this.recordCtx.destination);
      this.recording = true;

      // Primary path (exact Urvi `micCapture.ts` pattern): single AudioWorklet emitting 30 ms (480 samples) frames
      let workletAttached = false;
      try {
        await this.recordCtx.audioWorklet.addModule('/audio-processor.js');
        const node = new AudioWorkletNode(this.recordCtx, 'pcm16-downsampler', {
          processorOptions: { targetSampleRate: 16000, frameSamples: 480 },
        });
        node.port.onmessage = (e) => {
          if (!this.recording) return;
          const msg = e.data;
          const handleBuf = (buf: ArrayBuffer) => {
            const s16 = new Int16Array(buf);
            let sum = 0;
            for (let i = 0; i < s16.length; i++) {
              const v = s16[i] / 32768;
              sum += v * v;
            }
            const rms = Math.sqrt(sum / Math.max(1, s16.length));
            const lv = Math.min(1, Math.sqrt(rms) * 2.0);
            this.rawMicLevel = lv;
            this.micLevel = this.micLevel * 0.45 + lv * 0.55;
            this.onPcm16Chunk?.(buf);
          };
          if (msg instanceof ArrayBuffer) {
            handleBuf(msg);
          } else if (msg?.type === 'pcm' && msg.buffer) {
            handleBuf(msg.buffer as ArrayBuffer);
          } else if (msg?.type === 'level') {
            const lv = Math.min(1, Math.sqrt((msg.rms as number) || 0) * 2.0);
            this.rawMicLevel = lv;
            this.micLevel = this.micLevel * 0.45 + lv * 0.55;
          }
        };
        source.connect(node);
        node.connect(this.sinkGain);
        node.port.postMessage({ enabled: true });
        this.workletNode = node;
        workletAttached = true;
      } catch {
        workletAttached = false;
      }

      // Fallback path ONLY if AudioWorklet is unavailable
      if (!workletAttached) {
        const sp = this.recordCtx.createScriptProcessor(2048, 1, 1);
        const ratio = this.recordCtx.sampleRate / 16000;
        let pos = 0;
        let prev = 0;
        let out = new Int16Array(480);
        let outIdx = 0;
        sp.onaudioprocess = (ev) => {
          if (!this.recording) return;
          const ch = ev.inputBuffer.getChannelData(0);
          const n = ch.length;
          let sumSq = 0;
          let peakAbs = 0;
          for (let i = 0; i < n; i++) {
            const v = ch[i];
            sumSq += v * v;
            const av = Math.abs(v);
            if (av > peakAbs) peakAbs = av;
          }
          const rms = Math.sqrt(sumSq / Math.max(1, n));
          const lv = Math.min(1, Math.sqrt(rms) * 2.2);
          this.rawMicLevel = lv; // fallback path feeds barge-in too
          this.micLevel = this.micLevel * 0.45 + lv * 0.55;
          const gain = peakAbs > 0.00015 && peakAbs < 0.25 ? Math.min(24.0, 0.35 / peakAbs) : 1.0;
          while (pos < n) {
            const i0 = Math.floor(pos);
            const frac = pos - i0;
            const s0 = i0 - 1 >= 0 ? ch[i0 - 1] : prev;
            const s1 = ch[i0];
            let s = (s0 + (s1 - s0) * frac) * gain;
            if (s > 1) s = 1;
            else if (s < -1) s = -1;
            out[outIdx++] = s < 0 ? s * 0x8000 : s * 0x7fff;
            if (outIdx >= 480) {
              const chunk = out;
              this.onPcm16Chunk?.(chunk.buffer);
              out = new Int16Array(480);
              outIdx = 0;
            }
            pos += ratio;
          }
          pos -= n;
          prev = ch[n - 1];
        };
        source.connect(sp);
        sp.connect(this.sinkGain);
      }

      return { ok: true };
    } catch (err: any) {
      this.stopMic();
      return { ok: false, error: 'other', message: `Audio pipeline failed: ${err?.message || err}` };
    }
  }

  public stopMic(): void {
    if (this.startingPromise) this.stopRequestedDuringStart = true;
    try {
      this.workletNode?.port.postMessage('flush');
    } catch {}
    this.micStream?.getTracks().forEach((t) => t.stop());
    this.micStream = null;
    try {
      this.workletNode?.disconnect();
      this.sinkGain?.disconnect();
    } catch {}
    this.workletNode = null;
    this.sinkGain = null;
    if (this.recordCtx && this.recordCtx.state !== 'closed') void this.recordCtx.close();
    this.recordCtx = null;
    this.micLevel = 0;
    this.rawMicLevel = 0;
    this.recording = false;
  }

  /** Raw (unsmoothed, no floor) mic level 0..1: the honest signal used for barge-in decisions (U3.3). */
  public getRawMicLevel(): number {
    return this.recording ? this.rawMicLevel : 0;
  }

  /** Output (Yukti voice) level 0..1 from the playback analyser; 0 when silent (U3.2 speaking state). */
  public getOutputLevel(): number {
    if (!this.playAnalyser || !this.playFreq || this.activeSources.size === 0) return 0;
    this.playAnalyser.getByteFrequencyData(this.playFreq as any);
    let sum = 0;
    for (let i = 0; i < this.playFreq.length; i++) sum += this.playFreq[i];
    return Math.min(1, sum / this.playFreq.length / 70);
  }

  /** 0..1 smoothed microphone level (0 when not recording). */
  public getMicLevel(): number {
    // Pure read (U3.3): smoothed worklet level for display. No synthetic floor or cadence, so silence reads ~0.
    if (!this.recording) return 0;
    return this.micLevel;
  }

  // ---------- Playback ----------

  public setPlaybackEndHandler(cb: () => void): void {
    this.onPlaybackEnded = cb;
  }

  public setPlaybackStartHandler(cb: () => void): void {
    this.onPlaybackStarted = cb;
  }

  public setZeroSignalHandler(cb: (deviceLabel: string) => void): void {
    this.onZeroSignal = cb;
  }

  public resetTurnStats(): void {
    this.turnStats = { chunks: 0, bytes: 0, scheduledSeconds: 0, firstChunkAt: null, lastChunkAt: null };
  }

  public getStats(): PlaybackStats {
    return { ...this.stats };
  }

  public getTurnStats(): PlaybackStats {
    return { ...this.turnStats };
  }

  /** Accept audio again (call when a new agent turn starts / after server confirms interruption). */
  public acceptIncoming(): void {
    this.dropIncoming = false;
  }

  public enqueue24kAudio(pcmData: string | ArrayBuffer): void {
    if (this.isMuted) return;
    // After a barge-in, the rest of the interrupted reply is discarded until acceptIncoming() (U3.4).
    if (this.dropIncoming) return;
    if (typeof window !== 'undefined' && 'speechSynthesis' in window && this.synthSpeaking) {
      try {
        window.speechSynthesis.cancel();
        this.synthSpeaking = false;
      } catch {}
    }
    let raw: ArrayBuffer;
    if (typeof pcmData === 'string') {
      const bin = atob(pcmData);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      raw = bytes.buffer;
    } else {
      raw = pcmData;
    }
    const usable = raw.byteLength - (raw.byteLength % 2);
    if (usable <= 0) return;
    const int16 = new Int16Array(raw, 0, usable / 2);

    const now = performance.now();
    for (const s of [this.stats, this.turnStats]) {
      s.chunks += 1;
      s.bytes += usable;
      s.scheduledSeconds += int16.length / 24000;
      if (s.firstChunkAt === null) s.firstChunkAt = now;
      s.lastChunkAt = now;
    }

    const ctx = this.getPlayContext();
    if (ctx.state === 'suspended') void ctx.resume();
    const f32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) f32[i] = int16[i] / 32768;
    const buf = ctx.createBuffer(1, f32.length, 24000);
    buf.copyToChannel(f32, 0);
    const src = ctx.createBufferSource();
    src.buffer = buf;
    // Connect directly to ctx.destination (Urvi `audioPlayer.ts` pattern) and in parallel to playAnalyser for orb visual
    src.connect(ctx.destination);
    if (this.playAnalyser) {
      try {
        src.connect(this.playAnalyser);
      } catch {}
    }

    const wasIdle = this.activeSources.size === 0;
    const t = Math.max(this.nextPlayTime, ctx.currentTime + 0.05);
    src.start(t);
    this.nextPlayTime = t + buf.duration;
    this.playEndWallMs = performance.now() + (this.nextPlayTime - ctx.currentTime) * 1000;
    this.activeSources.add(src);
    if (wasIdle) this.onPlaybackStarted?.();
    src.onended = () => {
      this.activeSources.delete(src);
      if (this.activeSources.size === 0) this.onPlaybackEnded?.();
    };
  }

  /** Barge-in: stop all currently scheduled sources (Urvi `audioPlayer.interrupt()` pattern — never permanently mute future chunks). */
  public stopPlayback(_dropInFlight = false): void {
    const had = this.activeSources.size > 0 || this.synthSpeaking;
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
      } catch {}
    }
    this.synthSpeaking = false;
    this.activeSources.forEach((s) => {
      try {
        s.onended = null;
        s.stop();
        s.disconnect();
      } catch {}
    });
    this.activeSources.clear();
    if (this.playCtx) this.nextPlayTime = this.playCtx.currentTime;
    // dropInFlight=true (barge-in): ignore remaining chunks of this reply until a new turn starts.
    this.dropIncoming = _dropInFlight;
    if (had) this.onPlaybackEnded?.();
  }

  public isAudioPlaying(): boolean {
    const now = performance.now();
    if (this.synthSpeaking && this.synthDeadlineMs && now > this.synthDeadlineMs) this.synthSpeaking = false; // S-2
    // S-2: a suspended/stalled context never fires onended; past the scheduled end + 1 s it is not "playing"
    const pcmPlaying = this.activeSources.size > 0 && !(this.playEndWallMs && now > this.playEndWallMs + 1000);
    return pcmPlaying || this.synthSpeaking;
  }

  /** Release every audio resource (U3.5): stop mic + playback and close the 24 kHz playback context. */
  public dispose(): void {
    this.stopSpeechRecognition(false);
    this.stopMic();
    this.stopPlayback(false);
    if (this.playCtx && this.playCtx.state !== 'closed') void this.playCtx.close();
    this.playCtx = null;
    this.playAnalyser = null;
    this.playFreq = null;
  }
}
