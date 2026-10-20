/**
 * AudioWorkletProcessor: Downsamples microphone audio to 16 kHz PCM16
 * Emits raw Int16Array buffers to main thread for streaming to /ws/live
 */
class Pcm16DownsamplerProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.targetSampleRate = 16000;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (!input || !input[0]) return true;

    const channelData = input[0]; // Float32Array
    const sampleRateRatio = sampleRate / this.targetSampleRate;
    const outputLength = Math.floor(channelData.length / sampleRateRatio);

    if (outputLength <= 0) return true;

    const pcm16 = new Int16Array(outputLength);

    for (let i = 0; i < outputLength; i++) {
      const srcIndex = Math.floor(i * sampleRateRatio);
      let s = Math.max(-1, Math.min(1, channelData[srcIndex]));
      pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }

    this.port.postMessage(pcm16.buffer, [pcm16.buffer]);
    return true;
  }
}

registerProcessor('pcm16-downsampler', Pcm16DownsamplerProcessor);
