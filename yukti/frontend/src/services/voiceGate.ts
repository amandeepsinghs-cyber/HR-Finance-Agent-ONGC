/**
 * P0.10 (BUG-17/18): voice half-duplex gate + deliberate barge-in.
 *
 * Yukti's own voice comes back through the laptop microphone. If those frames reach Gemini Live, its server VAD
 * treats them as the user speaking and interrupts the answer. So:
 *  - mic PCM is NOT sent while Yukti's audio is playing, nor for a short tail after playback ends;
 *  - a deliberate interrupt (orb tap, Stop/mic button, Space) stops playback and re-opens the gate at once;
 *  - (stage 2) a voice barge-in needs sustained speech clearly louder than the echo of the playback.
 * Pure logic, no DOM: unit-testable.
 */

export const PLAYBACK_TAIL_MS = 300;

export interface GateInput {
  playing: boolean; // Yukti audio currently playing
  nowMs: number;
  tailUntilMs: number; // playback end time + tail
  bargeOpen: boolean; // a deliberate barge-in re-opened the gate
}

/** True when a mic frame may be sent to the backend. */
export function micGateOpen(g: GateInput): boolean {
  if (g.bargeOpen) return true;
  if (g.playing) return false;
  return g.nowMs >= g.tailUntilMs;
}

/**
 * Voice barge-in detector (stage 2): fires only for ~0.4 s of speech clearly louder than the playback echo.
 * `echoFloor` adapts (slow EMA) to the mic level heard during playback when nobody is talking, so the trigger
 * threshold rises with loud speakers / a quiet room.
 */
export class BargeInDetector {
  private echoFloor = 0.05;
  private loudMs = 0;
  constructor(
    private readonly sustainMs = 400,
    private readonly absMin = 0.3, // never trigger below this raw RMS
    private readonly echoFactor = 2.5, // speech must be this many times the echo floor…
    private readonly margin = 0.08, // …plus this margin
  ) {}

  threshold(): number {
    return Math.max(this.absMin, this.echoFloor * this.echoFactor + this.margin);
  }

  /** Feed one tick. Returns true exactly when a barge-in should fire. */
  update(micLevel: number, playing: boolean, dtMs: number): boolean {
    if (!playing) {
      this.loudMs = 0;
      return false;
    }
    const thr = this.threshold();
    if (micLevel > thr) {
      this.loudMs += dtMs;
    } else {
      // learn the echo floor only from sub-threshold frames (speech never inflates it)
      this.echoFloor = this.echoFloor * 0.95 + micLevel * 0.05;
      this.loudMs = Math.max(0, this.loudMs - dtMs / 2); // leaky: short dips between syllables don't reset
    }
    if (this.loudMs >= this.sustainMs) {
      this.loudMs = 0;
      return true;
    }
    return false;
  }

  reset(): void {
    this.loudMs = 0;
  }

  getEchoFloor(): number {
    return this.echoFloor;
  }
}
