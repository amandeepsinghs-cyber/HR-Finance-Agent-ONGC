'use client';

/**
 * Yukti Voice Orb — Feathery, Light Siri-Style Flowing Aura.
 *
 * Pure borderless, feathery clouds of glowing light (no dots, no hard rings, no pinched lip shape)
 * that continuously drift, breathe, and swirl like Siri's luminous aura, and swell/accelerate
 * dynamically when voice audio is heard or spoken.
 */
import React, { useEffect, useRef } from 'react';
import { VoiceAudioEngine } from '@/services/audioAnalyser';

export type OrbState = 'idle' | 'listening' | 'thinking' | 'speaking';

interface VoiceOrbProps {
  state: OrbState;
  isDark?: boolean;
  size?: number;
  className?: string;
  onClick?: () => void;
  interactive?: boolean;
  audioEngine?: Pick<VoiceAudioEngine, 'getRawMicLevel' | 'getOutputLevel'> & {
    getMicLevel?: () => number;
  };
  label?: string;
  pressed?: boolean;
}

type RGB = [number, number, number];
const rgba = (c: RGB, a: number) => `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${Math.max(0, Math.min(1, a))})`;

interface CloudSpec {
  color: RGB;
  orbitX: number;
  orbitY: number;
  speedX: number;
  speedY: number;
  phase: number;
  radiusMul: number;
  alphaMul: number;
}

// Airy, luminous Siri / Google AI aura hues — positioned around a luminous white core so colors stay pure and never mix into gray
const CLOUDS_LIGHT: CloudSpec[] = [
  { color: [59, 130, 246], orbitX: 0.17, orbitY: 0.16, speedX: 0.75, speedY: 0.92, phase: 0.0, radiusMul: 0.27, alphaMul: 0.52 },   // Sky Cobalt Blue
  { color: [139, 92, 246], orbitX: 0.17, orbitY: 0.17, speedX: -0.82, speedY: 0.68, phase: 1.57, radiusMul: 0.26, alphaMul: 0.48 },  // Feathery Violet
  { color: [244, 63, 94], orbitX: 0.16, orbitY: 0.16, speedX: 0.64, speedY: -0.88, phase: 3.14, radiusMul: 0.26, alphaMul: 0.46 },   // Soft Rose Coral
  { color: [6, 182, 212], orbitX: 0.17, orbitY: 0.15, speedX: -0.7, speedY: -0.78, phase: 4.71, radiusMul: 0.27, alphaMul: 0.48 },   // Luminous Aqua Cyan
  { color: [251, 191, 36], orbitX: 0.14, orbitY: 0.14, speedX: 0.88, speedY: 0.58, phase: 2.35, radiusMul: 0.23, alphaMul: 0.38 },   // Warm Gold Light
];

const CLOUDS_DARK: CloudSpec[] = [
  { color: [96, 165, 250], orbitX: 0.17, orbitY: 0.16, speedX: 0.75, speedY: 0.92, phase: 0.0, radiusMul: 0.27, alphaMul: 0.55 },
  { color: [167, 139, 250], orbitX: 0.17, orbitY: 0.17, speedX: -0.82, speedY: 0.68, phase: 1.57, radiusMul: 0.26, alphaMul: 0.50 },
  { color: [251, 113, 133], orbitX: 0.16, orbitY: 0.16, speedX: 0.64, speedY: -0.88, phase: 3.14, radiusMul: 0.26, alphaMul: 0.48 },
  { color: [34, 211, 238], orbitX: 0.17, orbitY: 0.15, speedX: -0.7, speedY: -0.78, phase: 4.71, radiusMul: 0.27, alphaMul: 0.50 },
  { color: [251, 191, 36], orbitX: 0.14, orbitY: 0.14, speedX: 0.88, speedY: 0.58, phase: 2.35, radiusMul: 0.23, alphaMul: 0.40 },
];

export const VoiceOrb: React.FC<VoiceOrbProps> = ({
  state = 'idle',
  isDark = false,
  size = 220,
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

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;

    const dpr = Math.min(2, typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1);
    canvas.width = Math.round(size * dpr);
    canvas.height = Math.round(size * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    let raf = 0;
    let last = performance.now();
    // Phase continuously advances so the feathery Siri aura is always gently alive and drifting
    let phase = 0;
    let smoothLevel = 0;
    const clouds = isDark ? CLOUDS_DARK : CLOUDS_LIGHT;

    const render = (now: number) => {
      const dt = Math.min(0.1, Math.max(0, (now - last) / 1000));
      last = now;

      const s = stateRef.current;
      const eng = engineRef.current;
      const rawMic = eng?.getRawMicLevel ? eng.getRawMicLevel() : 0;
      const smoothMic = eng?.getMicLevel ? eng.getMicLevel() : 0;
      const outLv = eng?.getOutputLevel ? eng.getOutputLevel() : 0;

      const speakCadence =
        s === 'speaking'
          ? Math.max(outLv, 0.35 + 0.2 * Math.sin(now * 0.008) + 0.12 * Math.cos(now * 0.013))
          : 0;

      const rawLv =
        s === 'listening'
          ? Math.max(rawMic, smoothMic)
          : s === 'speaking'
            ? Math.max(speakCadence, rawMic * 0.4)
            : Math.max(rawMic, smoothMic, outLv);

      const targetLv = Math.min(1, rawLv * 1.65);
      smoothLevel += (targetLv - smoothLevel) * (targetLv > smoothLevel ? 0.25 : 0.1);

      const baseSpeed = s === 'thinking' ? 2.6 : s === 'listening' || s === 'speaking' ? 1.55 : 0.95;
      phase += dt * (baseSpeed + smoothLevel * 3.2);

      const W = size;
      const H = size;
      const cx = W / 2;
      const cy = H / 2;

      ctx.clearRect(0, 0, W, H);

      // 1. Outer ambient feathery aura halo
      const breathe = 0.5 + 0.5 * Math.sin(phase * 0.85);
      const outerR = W * (0.45 + 0.03 * breathe + smoothLevel * 0.04);
      const amb = ctx.createRadialGradient(cx, cy, 0, cx, cy, outerR);
      amb.addColorStop(0, rgba(clouds[0].color, (isDark ? 0.18 : 0.14) + smoothLevel * 0.12));
      amb.addColorStop(0.55, rgba(clouds[1].color, (isDark ? 0.1 : 0.08) + smoothLevel * 0.08));
      amb.addColorStop(1, rgba(clouds[0].color, 0));
      ctx.fillStyle = amb;
      ctx.fillRect(0, 0, W, H);

      // 2. Drifting, feathery Siri light clouds (soft multi-stop radial gradients that blend seamlessly)
      ctx.save();
      ctx.globalCompositeOperation = isDark ? 'screen' : 'source-over';

      clouds.forEach((c, idx) => {
        const tX = phase * c.speedX + c.phase;
        const tY = phase * c.speedY + c.phase * 1.3;
        const orbitScale = 1 + smoothLevel * 0.22 + (s === 'thinking' ? 0.12 : 0);
        const x = cx + Math.cos(tX) * W * c.orbitX * orbitScale;
        const y = cy + Math.sin(tY) * H * c.orbitY * orbitScale;

        const pulse = 1 + 0.1 * Math.sin(phase * 1.4 + idx * 1.1) + smoothLevel * 0.18;
        const r = Math.min(W * 0.31, W * c.radiusMul * pulse);
        const alpha = Math.min(0.82, c.alphaMul * (1 + smoothLevel * 0.35 + (s === 'listening' ? 0.1 : 0)));

        const g = ctx.createRadialGradient(x, y, 0, x, y, r);
        g.addColorStop(0, rgba(c.color, alpha));
        g.addColorStop(0.38, rgba(c.color, alpha * 0.68));
        g.addColorStop(0.72, rgba(c.color, alpha * 0.22));
        g.addColorStop(1, rgba(c.color, 0));

        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      });

      // 3. Bright, airy pearl light core in the center so overlapping inner edges never look gray
      const coreR = W * (0.26 + 0.025 * Math.cos(phase * 1.2) + smoothLevel * 0.05);
      const coreGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, coreR);
      const coreAlpha = isDark ? 0.32 + smoothLevel * 0.18 : 0.78 + smoothLevel * 0.15;
      coreGrad.addColorStop(0, `rgba(255, 255, 255, ${Math.min(0.95, coreAlpha)})`);
      coreGrad.addColorStop(0.48, `rgba(255, 255, 255, ${coreAlpha * 0.55})`);
      coreGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');
      ctx.fillStyle = coreGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, coreR, 0, Math.PI * 2);
      ctx.fill();

      // 4. Circular radial feather mask (destination-in) so the outer edge is 100% circular & feathery (never clips to a square)
      ctx.globalCompositeOperation = 'destination-in';
      const featherMask = ctx.createRadialGradient(cx, cy, W * 0.18, cx, cy, W * 0.48);
      featherMask.addColorStop(0, 'rgba(255, 255, 255, 1)');
      featherMask.addColorStop(0.68, 'rgba(255, 255, 255, 0.92)');
      featherMask.addColorStop(0.88, 'rgba(255, 255, 255, 0.35)');
      featherMask.addColorStop(1, 'rgba(255, 255, 255, 0)');
      ctx.fillStyle = featherMask;
      ctx.fillRect(0, 0, W, H);

      ctx.restore();

      raf = requestAnimationFrame(render);
    };

    raf = requestAnimationFrame(render);
    return () => {
      if (raf) cancelAnimationFrame(raf);
    };
  }, [size, isDark]);

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
      style={{ width: size, height: size }}
      className={`relative inline-flex items-center justify-center select-none rounded-full transition-transform duration-300 ${
        clickable ? 'cursor-pointer hover:scale-[1.03] active:scale-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent)]' : ''
      } ${className}`}
    >
      <canvas ref={canvasRef} style={{ width: size, height: size }} className="block" aria-hidden />
    </div>
  );
};

export default VoiceOrb;
