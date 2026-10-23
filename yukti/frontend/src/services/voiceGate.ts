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
 * Voice barge-in detector: fires only for ~0.4 s (cumulative, leaky) of speech clearly louder than the echo of
 * Yukti's own playback. Levels are the engine's raw mic level (sqrt-compressed RMS, 0..1) and the playback
 * analyser level (0..1). The threshold is the highest of:
 *  - an absolute floor (`absMin`, above the old 0.5 trigger that fired on echo),
 *  - the learned echo floor + `margin` (EMA of mic level heard during playback while below the threshold, so the
 *    user's speech never inflates it),
 *  - a playback-correlated term (`playBase + playGain * outputLevel`): louder playback, higher bar.
 */
export class BargeInDetector {
  private echoFloor: number;
  private loudMs = 0;
  constructor(
    private readonly sustainMs = 400,
    private readonly absMin = 0.6,
    private readonly margin = 0.25,
    private readonly playBase = 0.45,
    private readonly playGain = 0.4,
    initialEchoFloor = 0.3,
  ) {
    this.echoFloor = initialEchoFloor;
  }

  threshold(outputLevel = 0): number {
    return Math.min(0.98, Math.max(this.absMin, this.echoFloor + this.margin, this.playBase + this.playGain * outputLevel));
  }

  /** Feed one tick. Returns true exactly when a barge-in should fire. */
  update(micLevel: number, outputLevel: number, playing: boolean, dtMs: number): boolean {
    if (!playing) {
      this.loudMs = 0;
      return false;
    }
    const thr = this.threshold(outputLevel);
    if (micLevel > thr) {
      this.loudMs += dtMs;
    } else {
      this.echoFloor = this.echoFloor * 0.9 + micLevel * 0.1;
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

/**
 * P0.10 (BUG-17/18): per-speak bookkeeping for the Live `speak` turns that voice a REST answer.
 * While a speak is active its Live transcripts are dropped (the REST bubble already shows the text), and after a
 * turn_complete late transcript chunks are dropped until the next user turn starts.
 */
export class SpeakTracker {
  private active: string | null = null;
  private closed = false;
  private seq = 0;

  begin(): string {
    this.seq += 1;
    this.active = `spk-${Date.now().toString(36)}-${this.seq}`;
    return this.active;
  }

  activeId(): string | null {
    return this.active;
  }

  /** A turn_complete (speak or normal). Only the active speak's own completion ends it. */
  complete(speakId?: string | null): void {
    if (speakId && speakId === this.active) this.active = null;
    this.closed = true; // late chunks of the finished turn are dropped until the next user turn
  }

  /** Server-side `interrupted`: the speak (if any) is over. */
  interrupted(speakId?: string | null): void {
    if (!speakId || speakId === this.active) this.active = null;
    this.closed = true;
  }

  /** A new user turn (voice transcript) re-opens agent transcripts. */
  userTurn(): void {
    this.closed = false;
  }

  acceptAgentTranscript(): boolean {
    return this.active === null && !this.closed;
  }
}
