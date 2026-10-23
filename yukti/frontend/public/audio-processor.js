/**
 * AudioWorkletProcessor: microphone -> 16 kHz mono PCM16 frames for /ws/live.
 *
 * Ported from Urvi AI Agent (`wellpulse/frontend/src/live/pcm-worklet.js`):
 * - Resamples browser audio input to 16,000 Hz mono PCM16 little-endian.
 * - Emits one frame every 30 ms (480 samples = 960 bytes) unconditionally while enabled,
 *   matching Gemini Live API's 20–40 ms real-time audio framing requirement.
 * - Includes soft automatic gain normalization so quiet laptop microphones remain clear.
 */
class Pcm16DownsamplerProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    const opts = (options && options.processorOptions) || {};
    this.targetRate = opts.targetSampleRate || 16000;
    this.frameSamples = opts.frameSamples || 480; // 30 ms @ 16 kHz (960 bytes)
    this.ratio = sampleRate / this.targetRate;
    this.pos = 0;
    this.prev = 0;
    this.out = new Int16Array(this.frameSamples);
    this.outIdx = 0;
    this.levelAcc = 0;
    this.levelN = 0;
    this.enabled = true;
    this.port.onmessage = (e) => {
      if (e.data === 'flush') {
        this.flush();
      } else if (e.data && typeof e.data.enabled === 'boolean') {
        this.enabled = e.data.enabled;
        if (!this.enabled) {
          this.pos = 0;
          this.prev = 0;
          this.outIdx = 0;
        }
      }
    };
  }

  flush() {
    if (this.outIdx > 0) {
      const chunk = this.out.slice(0, this.outIdx);
      this.port.postMessage({ type: 'pcm', buffer: chunk.buffer }, [chunk.buffer]);
      this.out = new Int16Array(this.frameSamples);
      this.outIdx = 0;
    }
  }

  process(inputs, outputs) {
    if (!this.enabled) return true;
    const input = inputs[0];
    if (!input || !input[0] || input[0].length === 0) return true;
    const ch = input[0];
    const n = ch.length;
    if (outputs && outputs[0] && outputs[0][0]) {
      outputs[0][0].set(ch);
    }

    // Level metering + peak detection for soft gain boost on quiet mics
    let peakAbs = 0;
    for (let i = 0; i < n; i++) {
      const av = Math.abs(ch[i]);
      if (av > peakAbs) peakAbs = av;
    }

    const gain = peakAbs > 0.00015 && peakAbs < 0.25 ? Math.min(24.0, 0.35 / peakAbs) : 1.0;

    let sumSq = 0;
    for (let i = 0; i < n; i++) {
      const v = Math.max(-1, Math.min(1, ch[i] * gain));
      sumSq += v * v;
    }
    this.levelAcc += sumSq;
    this.levelN += n;

    // Resample to 16 kHz PCM16
    while (this.pos < n) {
      const i0 = Math.floor(this.pos);
      const frac = this.pos - i0;
      const s0 = i0 - 1 >= 0 ? ch[i0 - 1] : this.prev;
      const s1 = ch[i0];
      let s = (s0 + (s1 - s0) * frac) * gain;
      if (s > 1) s = 1;
      else if (s < -1) s = -1;
      this.out[this.outIdx++] = s < 0 ? s * 0x8000 : s * 0x7fff;
      if (this.outIdx >= this.frameSamples) {
        const chunk = this.out;
        this.port.postMessage({ type: 'pcm', buffer: chunk.buffer }, [chunk.buffer]);
        this.out = new Int16Array(this.frameSamples);
        this.outIdx = 0;
      }
      this.pos += this.ratio;
    }
    this.pos -= n;
    this.prev = ch[n - 1];

    // ~25 level updates per second
    if (this.levelN >= sampleRate / 25) {
      const rms = Math.sqrt(this.levelAcc / this.levelN);
      this.port.postMessage({ type: 'level', rms });
      this.levelAcc = 0;
      this.levelN = 0;
    }
    return true;
  }
}

registerProcessor('pcm16-downsampler', Pcm16DownsamplerProcessor);
