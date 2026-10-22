'use client';

/**
 * Yukti voice orb: calm "infinity ribbon" (U3.1/U3.2, FEAT-004, aura per D-16).
 *
 * Four luminous ribbons trace a breathing lemniscate (∞) inside a soft circular halo, drawn on Canvas 2D
 * with gradient strokes (additive 'lighter' blending in dark mode), coloured from the AI-aura tokens. No particles.
 *
 * State dynamics:
 *   idle      slow breathing (~0.5 Hz), thin ribbons, faint halo
 *   listening ribbon amplitude/thickness follow the RAW mic level (no synthetic floor), gentle rotation
 *   thinking  ribbons tighten into a loop while a bright pulse orbits the path
 *   speaking  ribbons resonate with Yukti's output level (playback analyser)
 *
 * DPR-aware; honours prefers-reduced-motion (static frame); pauses when off-screen or the tab is hidden.
 * Public props are unchanged from the previous particle orb, so every caller keeps working.
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
  audioEngine?: VoiceAudioEngine;
  label?: string;
  /** toggle state announced to assistive tech (mic on/off) */
  pressed?: boolean;
}

type ThemeMap = Record<string, string>;

/** Parse a #RRGGBB token value into [r,g,b] channels. */
function toChannels(hex: string): [number, number, number] {
  const h = (hex || TOKENS.themes.light['aura-ring-blue']).replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}
const withAlpha = (c: [number, number, number], a: number) => `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${a})`;

const STATE_PARAMS: Record<OrbState, { amp: number; width: number; speed: number; halo: number; spread: number }> = {
  idle: { amp: 0.08, width: 1.4, speed: 0.35, halo: 0.22, spread: 0.1 },
  listening: { amp: 0.16, width: 2.0, speed: 0.75, halo: 0.42, spread: 0.18 },
  thinking: { amp: 0.06, width: 1.8, speed: 1.6, halo: 0.36, spread: 0.06 },
  speaking: { amp: 0.18, width: 2.2, speed: 0.9, halo: 0.5, spread: 0.2 },
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
  const engineRef = useRef<VoiceAudioEngine | undefined>(audioEngine);
  stateRef.current = state;
  engineRef.current = audioEngine;
  // Reduced motion: the loop draws a single frame, so state changes trigger an explicit redraw.
  const redrawRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const th = (isDark ? TOKENS.themes.dark : TOKENS.themes.light) as unknown as ThemeMap;

    const dpr = Math.min(2, typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1);
    canvas.width = Math.round(size * dpr);
    canvas.height = Math.round(size * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const reduced = typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    let raf = 0;
    let visible = true;
    const t0 = performance.now();
    // eased, per-frame-smoothed parameters (no jumps between states)
    const cur = { ...STATE_PARAMS[stateRef.current], level: 0 };
    const colors = [th['aura-ring-blue'], th['aura-ring-red'], th['aura-ring-yellow'], th['aura-ring-green']].map(toChannels);
    const violet = toChannels(th['aura-ring-violet']);

    const levelFor = (s: OrbState): number => {
      const eng = engineRef.current;
      if (!eng) return 0;
      if (s === 'listening') return eng.getRawMicLevel();
      if (s === 'speaking') return eng.getOutputLevel();
      return 0;
    };

    const draw = (now: number) => {
      const s = stateRef.current;
      const target = STATE_PARAMS[s];
      const k = reduced ? 1 : 0.08; // reduced motion: snap straight to the state's look
      cur.amp += (target.amp - cur.amp) * k;
      cur.width += (target.width - cur.width) * k;
      cur.speed += (target.speed - cur.speed) * k;
      cur.halo += (target.halo - cur.halo) * k;
      cur.spread += (target.spread - cur.spread) * k;
      const lvTarget = levelFor(s);
      cur.level += (lvTarget - cur.level) * (lvTarget > cur.level ? 0.35 : 0.12);

      const t = (now - t0) / 1000;
      const W = size;
      const cx = W / 2;
      const cy = W / 2;
      const R = W * 0.38;
      ctx.clearRect(0, 0, W, W);

      // Soft circular halo behind the ribbons (~0.5 Hz breathing)
      const breathe = 0.5 + 0.5 * Math.sin(t * Math.PI * 2 * 0.5);
      const haloA = cur.halo * (0.75 + 0.25 * breathe) + cur.level * 0.35;
      const g = ctx.createRadialGradient(cx, cy, R * 0.15, cx, cy, W * 0.5);
      g.addColorStop(0, withAlpha(colors[0], haloA * (isDark ? 0.55 : 0.45)));
      g.addColorStop(0.55, withAlpha(violet, haloA * 0.22));
      g.addColorStop(1, withAlpha(colors[0], 0));
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(cx, cy, W * 0.5, 0, Math.PI * 2);
      ctx.fill();

      // Ribbons on a breathing lemniscate (Bernoulli), each with its own phase, tilt and harmonic
      ctx.globalCompositeOperation = isDark ? 'lighter' : 'source-over';
      const amp = cur.amp + cur.level * 0.32;
      const N = 140;
      for (let i = 0; i < 4; i++) {
        const phase = t * cur.speed * (1 + i * 0.13) + i * 1.7;
        const tilt = Math.sin(t * 0.18 + i) * 0.12 + (i - 1.5) * cur.spread * 0.35;
        const harmonic = 2 + (i % 3);
        const c = colors[i];
        const next = colors[(i + 1) % 4];
        const grad = ctx.createLinearGradient(cx - R, cy, cx + R, cy);
        grad.addColorStop(0, withAlpha(c, 0));
        grad.addColorStop(0.25, withAlpha(c, isDark ? 0.85 : 0.9));
        grad.addColorStop(0.5, withAlpha(violet, isDark ? 0.7 : 0.75));
        grad.addColorStop(0.75, withAlpha(next, isDark ? 0.85 : 0.9));
        grad.addColorStop(1, withAlpha(next, 0));
        ctx.strokeStyle = grad;
        ctx.lineWidth = cur.width + cur.level * 2.4;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.shadowColor = withAlpha(c, isDark ? 0.55 : 0.35);
        ctx.shadowBlur = 6 + cur.level * 10;
        ctx.beginPath();
        for (let j = 0; j <= N; j++) {
          const u = (j / N) * Math.PI * 2;
          const den = 1 + Math.sin(u) * Math.sin(u);
          let x = (Math.cos(u) / den) * R;
          let y = ((Math.sin(u) * Math.cos(u)) / den) * R * (1 + cur.spread);
          y += Math.sin(u * harmonic + phase) * amp * R;
          x += Math.cos(u * (harmonic + 1) - phase * 0.7) * amp * R * 0.35;
          const xr = x * Math.cos(tilt) - y * Math.sin(tilt);
          const yr = x * Math.sin(tilt) + y * Math.cos(tilt);
          if (j === 0) ctx.moveTo(cx + xr, cy + yr);
          else ctx.lineTo(cx + xr, cy + yr);
        }
        ctx.stroke();
      }

      // Thinking: a bright pulse orbits the ∞ path
      if (s === 'thinking') {
        const u = (t * 1.6) % (Math.PI * 2);
        const den = 1 + Math.sin(u) * Math.sin(u);
        // follow ribbon 0's path (same spread, harmonic offset and tilt) so the pulse stays on the ribbon
        const ph0 = t * cur.speed + 0;
        const tilt0 = Math.sin(t * 0.18) * 0.12 - 1.5 * cur.spread * 0.35;
        const bx = (Math.cos(u) / den) * R + Math.cos(u * 3 - ph0 * 0.7) * amp * R * 0.35;
        const by = ((Math.sin(u) * Math.cos(u)) / den) * R * (1 + cur.spread) + Math.sin(u * 2 + ph0) * amp * R;
        const px = cx + bx * Math.cos(tilt0) - by * Math.sin(tilt0);
        const py = cy + bx * Math.sin(tilt0) + by * Math.cos(tilt0);
        const pr = W * 0.05;
        const pg = ctx.createRadialGradient(px, py, 0, px, py, pr);
        pg.addColorStop(0, withAlpha(violet, isDark ? 0.75 : 0.6));
        pg.addColorStop(0.4, withAlpha(violet, isDark ? 0.3 : 0.22));
        pg.addColorStop(1, withAlpha(violet, 0));
        ctx.shadowBlur = 0;
        ctx.fillStyle = pg;
        ctx.beginPath();
        ctx.arc(px, py, pr, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalCompositeOperation = 'source-over';
      ctx.shadowBlur = 0;
    };

    redrawRef.current = reduced ? () => draw(performance.now()) : null;
    const frame = (now: number) => {
      raf = 0;
      if (!visible || (typeof document !== 'undefined' && document.visibilityState === 'hidden')) return;
      draw(now);
      if (!reduced) raf = requestAnimationFrame(frame);
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
    </div>
  );
};

export default VoiceOrb;
