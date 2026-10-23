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
 * Voice barge-in detector (P0.10 r2, G4 MF-1). Fires only for NEAR-CONTINUOUS speech clearly louder than the echo
 * of Yukti's own playback:
 *  - a sliding window of the last `windowMs` (0.5 s) of ticks must be full,
 *  - >= `minLoudFrac` (85 %) of the ticks in it are above the threshold,
 *  - no quiet dip inside the window is longer than `maxDipMs` (100 ms),
 *  - duty-cycle guard: the loud stretch that ends now (dips <= `maxDipMs` tolerated) must itself be
 *    >= `minLoudFrac` x `windowMs` long, so an on/off (syllabic echo) pattern whose loud runs are shorter than
 *    that can never fire, whatever its duty cycle,
 *  - echo-correlation guard: if the mic level tracks the playback level (Pearson r >= `maxEchoCorr` over the
 *    window, with real variation in both), it is echo, not a person talking over Yukti.
 * Threshold = max(absMin, learned echo floor + margin, playBase + playGain * playbackLevel). Levels are the
 * engine's raw mic level (sqrt-compressed RMS, 0..1) and the playback analyser level (0..1).
 */
export class BargeInDetector {
  private echoFloor: number;
  private ticks: { mic: number; out: number; loud: boolean }[] = [];
  private loudRunMs = 0;
  constructor(
    private readonly windowMs = 500,
    private readonly minLoudFrac = 0.85,
    private readonly maxDipMs = 100,
    private readonly maxEchoCorr = 0.8,
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

  /** Feed one tick (every `dtMs`). Returns true exactly when a barge-in should fire. */
  update(micLevel: number, outputLevel: number, playing: boolean, dtMs: number): boolean {
    if (!playing) {
      this.reset();
      return false;
    }
    const loud = micLevel > this.threshold(outputLevel);
    if (!loud) this.echoFloor = this.echoFloor * 0.9 + micLevel * 0.1; // learn only from sub-threshold ticks
    const n = Math.max(1, Math.round(this.windowMs / dtMs));
    this.ticks.push({ mic: micLevel, out: outputLevel, loud });
    if (this.ticks.length > n) this.ticks.shift();
    // length of the loud stretch ending now, tolerating dips up to maxDipMs
    let dipMs = 0;
    if (loud) this.loudRunMs += dtMs;
    else {
      // look back: count the current dip
      for (let i = this.ticks.length - 1; i >= 0 && !this.ticks[i].loud; i--) dipMs += dtMs;
      if (dipMs > this.maxDipMs) this.loudRunMs = 0;
    }
    if (this.ticks.length < n) return false;
    const loudN = this.ticks.filter((t) => t.loud).length;
    if (loudN / n < this.minLoudFrac) return false;
    // no dip longer than maxDipMs inside the window
    let run = 0;
    for (const t of this.ticks) {
      run = t.loud ? 0 : run + dtMs;
      if (run > this.maxDipMs) return false;
    }
    if (this.loudRunMs < this.windowMs * this.minLoudFrac) return false; // duty-cycle guard
    if (this.echoCorrelated()) return false;
    this.reset();
    return true;
  }

  /** Pearson correlation of mic vs playback level over the window (only when both actually vary). */
  private echoCorrelated(): boolean {
    const xs = this.ticks.map((t) => t.out);
    const ys = this.ticks.map((t) => t.mic);
    const mean = (a: number[]) => a.reduce((p, c) => p + c, 0) / a.length;
    const mx = mean(xs);
    const my = mean(ys);
    let sxy = 0;
    let sxx = 0;
    let syy = 0;
    for (let i = 0; i < xs.length; i++) {
      sxy += (xs[i] - mx) * (ys[i] - my);
      sxx += (xs[i] - mx) ** 2;
      syy += (ys[i] - my) ** 2;
    }
    if (sxx < 1e-4 || syy < 1e-4) return false; // no variation: correlation undefined, other guards decide
    return sxy / Math.sqrt(sxx * syy) >= this.maxEchoCorr;
  }

  reset(): void {
    this.ticks = [];
    this.loudRunMs = 0;
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

  /** WS closed / errored (P0.10 r2 MF-2): forget any speak; the next user turn starts clean. */
  reset(): void {
    this.active = null;
    this.closed = false;
  }

  acceptAgentTranscript(): boolean {
    return this.active === null && !this.closed;
  }
}
