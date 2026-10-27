'use client';

/**
 * Yukti voice orb: "Aurora wave" (D-29; replaces the U3.1 infinity ribbon). Borderless, feathered bands of AI-aura
 * light that ripple with the voice — no outlines, no rings, no hard edges (aura per D-16).
 *
 * State dynamics:
 *   idle      calm, slow low ripples and a faint ambient glow
 *   listening band amplitude / thickness follow the RAW mic level (no synthetic floor)
 *   thinking  a travelling shimmer moves through the bands
 *   speaking  bands follow Yukti's output level (playback analyser)
 *
 * Canvas 2D, AI-aura tokens only, DPR-aware. prefers-reduced-motion: no ambient drift (still when silent), but the wave
 * still follows a live voice, since that movement is the feedback that Yukti hears you (26-Oct, sponsor);
 * pauses when off-screen or the tab is hidden. Public props are unchanged, so every caller keeps working.
 */
import React, { useEffect, useRef } from 'react';
import { VoiceAudioEngine } from '@/services/audioAnalyser';
import TOKENS from '@/design/tokens.json';

export type OrbState = 'idle' | 'listening' | 'thinking' | 'speaking';

interface VoiceOrbProps {
  state: OrbState;
  isDark?: boolean;
  size?: number;
  className?: string;
  onClick?: () => void;
  interactive?: boolean;
  /** any source of raw mic + output levels 0..1 (the app's VoiceAudioEngine, or a simulator on showcase pages) */
  audioEngine?: Pick<VoiceAudioEngine, 'getRawMicLevel' | 'getOutputLevel'> & {
    getMicLevel?: () => number;
  };
  label?: string;
  /** toggle state announced to assistive tech (mic on/off) */
  pressed?: boolean;
}

type RGB = [number, number, number];
const ch = (hex: string): RGB => {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
};
const tint = (c: RGB, a: number) => `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${Math.max(0, Math.min(1, a))})`;
const white = (a: number) => tint([255, 255, 255], a);

interface Params {
  energy: number;
  flow: number;
  ripple: number;
}
/** perceptual gain on the 0..1 voice level, so normal speaking volume produces a clearly visible swell */
const VOICE_BOOST = 1.2;
const TARGET: Record<OrbState, Params> = {
  idle: { energy: 0.55, flow: 0.18, ripple: 0.1 },
  listening: { energy: 0.8, flow: 0.38, ripple: 0.35 },
  thinking: { energy: 0.7, flow: 0.55, ripple: 0.15 },
  speaking: { energy: 0.92, flow: 0.45, ripple: 0.6 },
};

export const VoiceOrb: React.FC<VoiceOrbProps> = ({
  state = 'idle',
  isDark = false,
  size = 200,
  className = '',
  onClick,
  interactive = true,
  audioEngine,
  label,
  pressed,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const stateRef = useRef<OrbState>(state);
  const engineRef = useRef(audioEngine);
  stateRef.current = state;
  engineRef.current = audioEngine;
  // Reduced motion: the loop draws a single frame, so state changes trigger an explicit redraw.
  const redrawRef = useRef<(() => void) | null>(null);
  // ?orbdebug=1: live readout of state / voice level / reduced-motion, to diagnose 'not reacting' on a given machine
  const debugRef = useRef<HTMLSpanElement | null>(null);
  const [debug, setDebug] = React.useState(false); // set after mount, so server and client HTML match
  useEffect(() => setDebug(new URLSearchParams(window.location.search).has('orbdebug')), []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;
    const th = (isDark ? TOKENS.themes.dark : TOKENS.themes.light) as unknown as Record<string, string>;
    const pal = { blue: ch(th['aura-ring-blue']), red: ch(th['aura-ring-red']), yellow: ch(th['aura-ring-yellow']), green: ch(th['aura-ring-green']), violet: ch(th['aura-ring-violet']) };
    const dpr = Math.min(2, typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1);
    canvas.width = Math.round(size * dpr);
    canvas.height = Math.round(size * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const reduced = typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    const cur = { ...TARGET[stateRef.current], level: 0, think: stateRef.current === 'thinking' ? 1 : 0 };
    const t0 = performance.now();
    let last = t0;
    // integrated phase: speed changes never scrub the waveform (G4 A1)
    let phase = 0;
    let thinkPhase = 0;
    let clock = 0; // drives the slow amplitude breathing; frozen in reduced motion unless someone speaks
    let raf = 0;
    let visible = true;

    const bands: [RGB, number, number, number][] = [
      [pal.blue, 0.0, 1.0, 1.0],
      [pal.violet, 1.3, 1.25, 0.9],
      [pal.red, 2.6, 0.85, 0.7],
      [pal.green, 3.9, 1.1, 0.65],
      [pal.yellow, 5.2, 0.95, 0.55],
    ];
    const small = size < 80; // ask bar: 3 bands, no halo pass, so it stays a clean wave
    const N = small ? 40 : 90;
    // small orb keeps the clearest Google hues: blue, red, yellow
    const activeBands = small ? [bands[0], bands[2], bands[4]] : bands;
    const span = size * 0.46;
    const cx = size / 2;
    const cy = size / 2;
    // gradients that depend only on palette / size / theme are built once per effect (G4 A4)
    const bandGrad = new Map<string, CanvasGradient>();
    const gradFor = (c: RGB, a: number, alphaMul: number) => {
      const key = `${c.join(',')}|${a}|${alphaMul}`;
      let g = bandGrad.get(key);
      if (!g) {
        g = ctx.createLinearGradient(cx - span, 0, cx + span, 0);
        g.addColorStop(0, tint(c, 0));
        g.addColorStop(0.28, tint(c, a * alphaMul));
        g.addColorStop(0.72, tint(c, a * alphaMul));
        g.addColorStop(1, tint(c, 0));
        bandGrad.set(key, g);
      }
      return g;
    };
    const maskGrad = (() => {
      const g = ctx.createRadialGradient(0, 0, size * 0.12, 0, 0, size * 0.5);
      g.addColorStop(0, white(1));
      g.addColorStop(0.6, white(0.9));
      g.addColorStop(1, white(0));
      return g;
    })();
    const HALO = isDark ? 0.1 : 0.14;
    const CORE = isDark ? 0.36 : 0.46;

    const draw = (now: number) => {
      const s = stateRef.current;
      const tg = TARGET[s];
      // frame-rate independent easing (same feel at 60 and 120 Hz)
      const dt = Math.min(0.1, Math.max(0, (now - last) / 1000));
      last = now;
      const k = 1 - Math.exp(-dt / 0.28);
      cur.energy += (tg.energy - cur.energy) * k;
      cur.flow += (tg.flow - cur.flow) * k;
      cur.ripple += (tg.ripple - cur.ripple) * k;
      const eng = engineRef.current;
      // Siri feel (26-Oct): react to the open mic the moment anyone speaks (idle or listening), with a perceptual
      // boost and a quick attack; Yukti's own voice drives it while speaking. Mic level is 0 whenever the mic is closed.
      const rawLv = !eng ? 0 : s === 'speaking' ? eng.getOutputLevel() : s === 'thinking' ? 0 : eng.getRawMicLevel();
      const lv = Math.min(1, rawLv * VOICE_BOOST);
      cur.level += (lv - cur.level) * (1 - Math.exp(-dt / (lv > cur.level ? 0.03 : 0.12)));
      // reduced motion: time only advances while there is voice, so a silent orb is perfectly still
      const motion = reduced ? Math.min(1, cur.level * 3) : 1;
      cur.think += ((s === 'thinking' ? 1 : 0) - cur.think) * k;
      if (debugRef.current) debugRef.current.textContent = `${s} · raw ${rawLv.toFixed(2)} · level ${cur.level.toFixed(2)}${reduced ? ' · reduced-motion' : ''}`;
      phase += dt * (0.8 + cur.flow * 2 + cur.level * 6) * motion;
      thinkPhase += dt * 3 * (reduced ? 0 : 1);
      clock += dt * motion;

      const t = clock;
      const W = size;
      const baseAmp = W * (0.075 + cur.ripple * 0.08 + cur.level * 0.15);
      ctx.clearRect(0, 0, W, W);

      // ambient glow (no edge)
      const amb = ctx.createRadialGradient(cx, cy, 0, cx, cy, W * 0.5);
      amb.addColorStop(0, tint(pal.violet, (isDark ? 0.2 : 0.12) * cur.energy + cur.level * 0.22));
      amb.addColorStop(1, tint(pal.blue, 0));
      ctx.fillStyle = amb;
      ctx.fillRect(0, 0, W, W);

      ctx.globalCompositeOperation = isDark ? 'screen' : 'source-over';
      const yAt = (u: number, f: number, ph: number, speed: number, amp: number) => {
        const env = Math.pow(Math.sin(Math.PI * u), 1.6);
        const x = (u - 0.5) * 2;
        const wave = Math.sin(x * 2.2 * f + speed + ph) * 0.6 + Math.sin(x * 4.1 - speed * 1.3 + ph * 1.7) * 0.4;
        const think = Math.sin(x * 3 - thinkPhase + ph) * 0.5;
        // thinking blends in smoothly instead of snapping (G4 A2)
        return env * (wave + (think - wave) * cur.think) * amp;
      };
      const band = (c: RGB, a: number, f: number, ph: number, thickness: number, alphaMul: number) => {
        const speed = phase * f;
        const amp = baseAmp * (0.6 + 0.4 * Math.sin(t * 0.9 + ph) + cur.level * 0.18 * Math.sin(t * 9 + ph * 2.3));
        ctx.fillStyle = gradFor(c, a, alphaMul);
        ctx.beginPath();
        for (let i = 0; i <= N; i++) {
          const u = i / N;
          const env = Math.pow(Math.sin(Math.PI * u), 1.2);
          const x = cx - span + u * span * 2;
          const y = cy + yAt(u, f, ph, speed, amp) - thickness * env;
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        for (let i = N; i >= 0; i--) {
          const u = i / N;
          const env = Math.pow(Math.sin(Math.PI * u), 1.2);
          ctx.lineTo(cx - span + u * span * 2, cy + yAt(u, f, ph, speed, amp) + thickness * env);
        }
        ctx.closePath();
        ctx.fill();
      };
      activeBands.forEach(([c, ph, f, a], bi) => {
        const thickness = W * (0.05 + cur.energy * 0.03 + cur.level * 0.05) * (1 - bi * 0.08);
        // feathered halo of each band first (wide + faint), then the band itself — light, not shapes
        if (!small) band(c, a, f, ph, thickness * 2.4, HALO);
        band(c, a, f, ph, thickness, CORE);
      });
      // thinking cue that doesn't depend on voice level: a soft highlight travelling along the wave (G4 A3)
      if (cur.think > 0.02) {
        const u = ((thinkPhase * 0.18) % 1.2) - 0.1;
        const hx = cx - span + u * span * 2;
        const hy = cy + yAt(Math.max(0, Math.min(1, u)), 1, 0, phase, baseAmp * 0.8); // rides the wave
        const edgeFade = Math.sin(Math.PI * Math.max(0, Math.min(1, (u + 0.1) / 1.2))); // no visible wrap
        const hg = ctx.createRadialGradient(hx, hy, 0, hx, hy, W * 0.16);
        hg.addColorStop(0, white((isDark ? 0.35 : 0.6) * cur.think * edgeFade));
        hg.addColorStop(1, white(0));
        ctx.fillStyle = hg;
        ctx.fillRect(hx - W * 0.16, hy - W * 0.16, W * 0.32, W * 0.32);
      }
      ctx.globalCompositeOperation = 'source-over';

      // thin luminous core thread: visible at rest, fades away as soon as someone speaks (26-Oct, sponsor)
      const threadA = (isDark ? 0.3 : 0.7) * Math.max(0, 1 - cur.level * 3);
      if (threadA > 0.01) {
        ctx.strokeStyle = white(threadA);
        ctx.lineWidth = Math.max(0.6, W * 0.0035);
        ctx.beginPath();
        for (let i = 0; i <= N; i++) {
          const u = i / N;
          const x = cx - span + u * span * 2;
          const y = cy + yAt(u, 1, 0, phase, baseAmp * 0.8);
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }

      // borderless: feather everything into the background with an elliptical alpha mask
      ctx.save();
      ctx.globalCompositeOperation = 'destination-in';
      ctx.translate(cx, cy);
      ctx.scale(1, 0.7 + cur.level * 0.15); // the feather opens up as the wave swells, so peaks are not clipped
      ctx.fillStyle = maskGrad;
      ctx.fillRect(-W, -W, W * 2, W * 2);
      ctx.restore();
    };

    redrawRef.current = null;
    const frame = (now: number) => {
      raf = 0;
      if (!visible || (typeof document !== 'undefined' && document.visibilityState === 'hidden')) return;
      draw(now);
      raf = requestAnimationFrame(frame);
    };
    const io =
      typeof IntersectionObserver !== 'undefined'
        ? new IntersectionObserver((entries) => {
            visible = entries[0]?.isIntersecting ?? true;
            if (visible && !raf) raf = requestAnimationFrame(frame);
          })
        : null;
    io?.observe(canvas);
    const onVis = () => {
      if (document.visibilityState === 'visible' && !raf) raf = requestAnimationFrame(frame);
    };
    document.addEventListener('visibilitychange', onVis);
    raf = requestAnimationFrame(frame);
    return () => {
      redrawRef.current = null;
      if (raf) cancelAnimationFrame(raf);
      io?.disconnect();
      document.removeEventListener('visibilitychange', onVis);
    };
  }, [size, isDark]);

  useEffect(() => {
    redrawRef.current?.();
  }, [state]);

  const clickable = interactive && !!onClick;
  return (
    <div
      role={clickable ? 'button' : undefined}
      tabIndex={clickable ? 0 : undefined}
      onClick={clickable ? onClick : undefined}
      onKeyDown={
        clickable
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
      aria-label={label || `Yukti voice (${state})`}
      aria-pressed={clickable && pressed !== undefined ? pressed : undefined}
      title={label}
      data-testid="voice-orb"
      data-state={state}
      className={`relative inline-grid place-items-center rounded-full select-none ${clickable ? 'cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent)]' : ''} ${className}`}
      style={{ width: size, height: size }}
    >
      <canvas ref={canvasRef} style={{ width: size, height: size }} aria-hidden />
      {debug && <span ref={debugRef} className="absolute -bottom-6 left-1/2 -translate-x-1/2 whitespace-nowrap text-caption text-[var(--ink-3)]" />}
    </div>
  );
};

export default VoiceOrb;
