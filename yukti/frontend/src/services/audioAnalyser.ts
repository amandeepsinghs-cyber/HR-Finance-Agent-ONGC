/**
 * Audio Analyser & Real-Time Voice Streaming Engine
 * 1. Recording: Mic -> AudioWorklet (16 kHz PCM16) -> callbacks
 * 2. Playback: 24 kHz PCM chunks -> Gapless AudioBuffer scheduler -> AnalyserNode
 * 3. Orb Amplitude: mic AnalyserNode (listening) & playback AnalyserNode (speaking)
 * 4. Barge-in: immediately stops playback graph on speech/cancel
 */

export class VoiceAudioEngine {
  // Recording
  private recordCtx: AudioContext | null = null;
  private micStream: MediaStream | null = null;
  private micAnalyser: AnalyserNode | null = null;
  private workletNode: AudioWorkletNode | ScriptProcessorNode | null = null;
  private isRecording: boolean = false;
  private onPcm16Chunk: ((chunk: ArrayBuffer) => void) | null = null;

  // Playback
  private playCtx: AudioContext | null = null;
  private playAnalyser: AnalyserNode | null = null;
  private nextPlayTime: number = 0;
  private activeSources: AudioBufferSourceNode[] = [];
  private isPlayingAudio: boolean = false;
  private onPlaybackEnded: (() => void) | null = null;

  // Analyser data buffers
  private micFreqData: Uint8Array | null = null;
  private playFreqData: Uint8Array | null = null;
  private syntheticPhase: number = 0;

  // Telemetry & TTFB instrumentation
  private speechEndTimestamp: number | null = null;
  private firstAudioChunkTimestamp: number | null = null;
  private measuredAudioTtfbMs: number | null = null;

  constructor() {}

  /**
   * Initializes playback audio context (24 kHz).
   */
  public getOrCreatePlayContext(): AudioContext {
    if (!this.playCtx || this.playCtx.state === 'closed') {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      this.playCtx = new AudioCtx({ sampleRate: 24000 });
      this.playAnalyser = this.playCtx.createAnalyser();
      this.playAnalyser.fftSize = 256;
      this.playAnalyser.smoothingTimeConstant = 0.8;
      this.playAnalyser.connect(this.playCtx.destination);
      this.playFreqData = new Uint8Array(this.playAnalyser.frequencyBinCount);
      this.nextPlayTime = this.playCtx.currentTime;
    }
    if (this.playCtx.state === 'suspended') {
      this.playCtx.resume();
    }
    return this.playCtx;
  }

  /**
   * Starts microphone recording, downsampling to 16 kHz PCM16 via AudioWorklet.
   */
  public async startMic(onPcmChunk?: (chunk: ArrayBuffer) => void): Promise<boolean> {
    try {
      if (typeof window === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
        return false;
      }

      this.onPcm16Chunk = onPcmChunk || null;
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      this.recordCtx = new AudioCtx();
      this.micStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });

      const source = this.recordCtx.createMediaStreamSource(this.micStream);
      this.micAnalyser = this.recordCtx.createAnalyser();
      this.micAnalyser.fftSize = 256;
      this.micAnalyser.smoothingTimeConstant = 0.8;
      source.connect(this.micAnalyser);
      this.micFreqData = new Uint8Array(this.micAnalyser.frequencyBinCount);

      // Try AudioWorklet first
      let workletReady = false;
      try {
        await this.recordCtx.audioWorklet.addModule('/audio-processor.js');
        const node = new AudioWorkletNode(this.recordCtx, 'pcm16-downsampler');
        node.port.onmessage = (e) => {
          if (this.onPcm16Chunk && e.data instanceof ArrayBuffer) {
            this.onPcm16Chunk(e.data);
          }
        };
        source.connect(node);
        this.workletNode = node;
        workletReady = true;
      } catch (err) {
        console.warn('[VoiceAudioEngine] AudioWorklet not supported, using ScriptProcessor fallback');
      }

      if (!workletReady) {
        // Fallback: ScriptProcessorNode
        const bufferSize = 4096;
        const spNode = this.recordCtx.createScriptProcessor(bufferSize, 1, 1);
        const sampleRateRatio = this.recordCtx.sampleRate / 16000;

        spNode.onaudioprocess = (e) => {
          const inputData = e.inputBuffer.getChannelData(0);
          const outLength = Math.floor(inputData.length / sampleRateRatio);
          const pcm16 = new Int16Array(outLength);

          for (let i = 0; i < outLength; i++) {
            const idx = Math.floor(i * sampleRateRatio);
            const s = Math.max(-1, Math.min(1, inputData[idx]));
            pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
          }

          if (this.onPcm16Chunk) {
            this.onPcm16Chunk(pcm16.buffer);
          }
        };
        source.connect(spNode);
        spNode.connect(this.recordCtx.destination);
        this.workletNode = spNode;
      }

      this.isRecording = true;
      return true;
    } catch (err) {
      console.warn('[VoiceAudioEngine] Microphone permission denied or unavailable:', err);
      this.isRecording = false;
      return false;
    }
  }

  public stopMic(): void {
    if (this.micStream) {
      this.micStream.getTracks().forEach((t) => t.stop());
      this.micStream = null;
    }
    if (this.workletNode) {
      this.workletNode.disconnect();
      this.workletNode = null;
    }
    if (this.recordCtx && this.recordCtx.state !== 'closed') {
      this.recordCtx.close();
      this.recordCtx = null;
    }
    this.micAnalyser = null;
    this.micFreqData = null;
    this.isRecording = false;
  }

  public markSpeechEnd(): void {
    this.speechEndTimestamp = performance.now();
    this.firstAudioChunkTimestamp = null;
  }

  public getMeasuredAudioTtfb(): number | null {
    return this.measuredAudioTtfbMs;
  }

  /**
   * Enqueues a 24 kHz raw PCM chunk (base64 or ArrayBuffer) for gapless playback.
   */
  public enqueue24kAudio(pcmData: string | ArrayBuffer): void {
    if (this.speechEndTimestamp && this.firstAudioChunkTimestamp === null) {
      this.firstAudioChunkTimestamp = performance.now();
      this.measuredAudioTtfbMs = Math.round(this.firstAudioChunkTimestamp - this.speechEndTimestamp);
    }

    const playCtx = this.getOrCreatePlayContext();

    let rawBuffer: ArrayBuffer;
    if (typeof pcmData === 'string') {
      const binary = atob(pcmData);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
      }
      rawBuffer = bytes.buffer;
    } else {
      rawBuffer = pcmData;
    }

    const int16View = new Int16Array(rawBuffer);
    if (int16View.length === 0) return;

    // Convert Int16 to Float32 [-1.0, 1.0]
    const float32 = new Float32Array(int16View.length);
    for (let i = 0; i < int16View.length; i++) {
      float32[i] = int16View[i] / 32768.0;
    }

    const audioBuf = playCtx.createBuffer(1, float32.length, 24000);
    audioBuf.copyToChannel(float32, 0);

    const source = playCtx.createBufferSource();
    source.buffer = audioBuf;

    if (this.playAnalyser) {
      source.connect(this.playAnalyser);
    } else {
      source.connect(playCtx.destination);
    }

    const now = playCtx.currentTime;
    if (this.nextPlayTime < now) {
      this.nextPlayTime = now;
    }

    source.start(this.nextPlayTime);
    this.isPlayingAudio = true;
    this.activeSources.push(source);

    this.nextPlayTime += audioBuf.duration;

    source.onended = () => {
      const idx = this.activeSources.indexOf(source);
      if (idx !== -1) {
        this.activeSources.splice(idx, 1);
      }
      if (this.activeSources.length === 0) {
        this.isPlayingAudio = false;
        if (this.onPlaybackEnded) {
          this.onPlaybackEnded();
        }
      }
    };
  }

  /**
   * Barge-in interruption: immediately stops playback graph.
   */
  public stopPlayback(): void {
    for (const src of this.activeSources) {
      try {
        src.stop();
        src.disconnect();
      } catch (e) {}
    }
    this.activeSources = [];
    if (this.playCtx) {
      this.nextPlayTime = this.playCtx.currentTime;
    }
    this.isPlayingAudio = false;
  }

  public setPlaybackEndHandler(cb: () => void): void {
    this.onPlaybackEnded = cb;
  }

  public isAudioPlaying(): boolean {
    return this.isPlayingAudio;
  }

  /**
   * Returns current amplitude (0.0 to 1.0) for the 3D particle orb:
   * - listening: real mic AnalyserNode
   * - speaking: real playback AnalyserNode
   * - thinking: animated swirl
   * - idle: breathing drift
   */
  public getAmplitude(mode: 'idle' | 'listening' | 'thinking' | 'speaking'): number {
    this.syntheticPhase += 0.05;

    if (mode === 'listening') {
      if (this.micAnalyser && this.micFreqData) {
        this.micAnalyser.getByteFrequencyData(this.micFreqData);
        let sum = 0;
        for (let i = 0; i < this.micFreqData.length; i++) {
          sum += this.micFreqData[i];
        }
        const avg = sum / this.micFreqData.length;
        return Math.min(1.0, Math.max(0.05, avg / 100.0));
      }
      return 0.2 + 0.15 * Math.sin(this.syntheticPhase * 2.5);
    }

    if (mode === 'speaking') {
      if (this.playAnalyser && this.playFreqData && this.isPlayingAudio) {
        this.playAnalyser.getByteFrequencyData(this.playFreqData);
        let sum = 0;
        for (let i = 0; i < this.playFreqData.length; i++) {
          sum += this.playFreqData[i];
        }
        const avg = sum / this.playFreqData.length;
        return Math.min(1.0, Math.max(0.1, avg / 90.0));
      }
      // If synthetic speaking or before stream connects
      return 0.35 + 0.25 * Math.abs(Math.sin(this.syntheticPhase * 3.5));
    }

    if (mode === 'thinking') {
      return 0.35 + 0.15 * Math.sin(this.syntheticPhase * 4.0);
    }

    // Idle
    return 0.08 + 0.04 * Math.sin(this.syntheticPhase * 0.8);
  }
}
