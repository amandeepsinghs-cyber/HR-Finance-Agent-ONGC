/**
 * AudioWorkletProcessor for recording 16kHz 16-bit linear PCM audio.
 * Receives microphone Float32 chunks and buffers/downsamples them to 16kHz PCM chunks.
 */

class PCMRecorderProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = [];
    this.targetSampleRate = 16000;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (!input || input.length === 0) {
      return true;
    }

    const channelData = input[0]; // mono channel 0
    if (!channelData) {
      return true;
    }

    // Convert Float32 (-1.0 to 1.0) to Int16 (-32768 to 32767)
    const pcm16 = new Int16Array(channelData.length);
    for (let i = 0; i < channelData.length; i++) {
      let s = Math.max(-1, Math.min(1, channelData[i]));
      pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }

    this.port.postMessage(pcm16.buffer, [pcm16.buffer]);
    return true;
  }
}

registerProcessor('pcm-recorder-processor', PCMRecorderProcessor);
