'use client';

import React, { useEffect, useRef, useState } from 'react';
import { VoiceAudioEngine } from '@/services/audioAnalyser';

export type OrbState = 'idle' | 'listening' | 'thinking' | 'speaking';

interface VoiceOrbProps {
  state: OrbState;
  isDark?: boolean;
  size?: number;
  className?: string;
  onClick?: () => void;
  interactive?: boolean;
  audioEngine?: VoiceAudioEngine;
}

interface Point3D {
  x: number;
  y: number;
  z: number;
  baseRadius: number;
  phase: number;
  size: number;
}

export const VoiceOrb: React.FC<VoiceOrbProps> = ({
  state = 'idle',
  isDark = false,
  size = 200,
  className = '',
  onClick,
  interactive = true,
  audioEngine,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const pointsRef = useRef<Point3D[]>([]);
  const rotYRef = useRef<number>(0);
  const rotXRef = useRef<number>(0.2);

  // Initialize Fibonacci sphere points
  useEffect(() => {
    const numPoints = 640;
    const phi = Math.PI * (3 - Math.sqrt(5)); // golden angle ~2.39996 rad
    const points: Point3D[] = [];

    for (let i = 0; i < numPoints; i++) {
      const y = 1 - (i / (numPoints - 1)) * 2; // -1 to 1
      const radiusAtY = Math.sqrt(Math.max(0, 1 - y * y));
      const theta = phi * i;

      const x = Math.cos(theta) * radiusAtY;
      const z = Math.sin(theta) * radiusAtY;

      points.push({
        x,
        y,
        z,
        baseRadius: 1,
        phase: Math.random() * Math.PI * 2,
        size: Math.random() > 0.85 ? 2.8 : Math.random() > 0.4 ? 2.0 : 1.4,
      });
    }

    pointsRef.current = points;
  }, []);

  // Animation rendering loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;

    let localAngleY = rotYRef.current;
    let localAngleX = rotXRef.current;

    const render = () => {
      const dpr = window.devicePixelRatio || 1;
      const width = size * dpr;
      const height = size * dpr;

      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }

      ctx.clearRect(0, 0, width, height);

      // Get real audio amplitude or simulated modulation
      const amplitude = audioEngine ? audioEngine.getAmplitude(state) : 0.2;

      // Adjust rotation speed and style according to state
      let speedY = 0.009;
      let speedX = 0.003;
      let sphereScale = size * 0.38;
      let waveDistortion = 0;

      if (state === 'idle') {
        speedY = 0.007;
        speedX = 0.002;
        sphereScale *= (1 + 0.04 * Math.sin(Date.now() * 0.002));
      } else if (state === 'listening') {
        speedY = 0.014;
        speedX = 0.005;
        sphereScale *= (1 + amplitude * 0.45);
        waveDistortion = amplitude * 0.35;
      } else if (state === 'thinking') {
        speedY = 0.045; // Fast swirl
        speedX = 0.012;
        sphereScale *= (1 + 0.12 * Math.sin(Date.now() * 0.008));
        waveDistortion = 0.15;
      } else if (state === 'speaking') {
        speedY = 0.016;
        speedX = 0.006;
        sphereScale *= (1 + amplitude * 0.35);
        waveDistortion = amplitude * 0.4;
      }

      localAngleY += speedY;
      localAngleX += speedX;
      rotYRef.current = localAngleY;
      rotXRef.current = localAngleX;

      const cosY = Math.cos(localAngleY);
      const sinY = Math.sin(localAngleY);
      const cosX = Math.cos(localAngleX);
      const sinX = Math.sin(localAngleX);

      const centerX = width / 2;
      const centerY = height / 2;

      const points = pointsRef.current;

      // Sort points back-to-front for proper depth blending
      const transformed = points.map((p) => {
        // Dynamic ripple on sphere surface
        const ripple = waveDistortion * Math.sin(p.phase + Date.now() * 0.006 + p.y * 4);
        const r = p.baseRadius * (1 + ripple);

        const x0 = p.x * r;
        const y0 = p.y * r;
        const z0 = p.z * r;

        // Rotate Y
        const x1 = x0 * cosY + z0 * sinY;
        const z1 = -x0 * sinY + z0 * cosY;

        // Rotate X
        const y2 = y0 * cosX - z1 * sinX;
        const z2 = y0 * sinX + z1 * cosX;

        // Perspective projection
        const fov = 3.2;
        const depth = fov / (fov + z2);

        return {
          px: centerX + x1 * sphereScale * depth * dpr,
          py: centerY + y2 * sphereScale * depth * dpr,
          pz: z2,
          depth,
          dotSize: p.size * depth * dpr,
        };
      });

      // Sort by z depth (furthest first)
      transformed.sort((a, b) => a.pz - b.pz);

      // Render dots
      for (let i = 0; i < transformed.length; i++) {
        const pt = transformed[i];
        const normZ = (pt.pz + 1) / 2; // 0 (back) to 1 (front)

        // Palette selection
        let r = 49;
        let g = 134;
        let b = 255;
        let alpha = 0.2 + normZ * 0.75;

        if (state === 'thinking') {
          // Swirl violet/cyan shift
          r = Math.floor(66 + 40 * Math.sin(localAngleY * 2 + normZ));
          g = Math.floor(133 + 70 * normZ);
          b = 255;
          alpha = 0.3 + normZ * 0.7;
        } else if (state === 'listening') {
          // Intense energetic cyan-blue
          r = 49;
          g = Math.floor(160 + 95 * amplitude);
          b = 255;
          alpha = 0.25 + normZ * 0.75 + amplitude * 0.2;
        } else if (state === 'speaking') {
          // Bright ripple
          r = Math.floor(80 + 100 * amplitude);
          g = Math.floor(160 + 70 * normZ);
          b = 255;
        }

        if (isDark) {
          // In dark mode: crisp white/cyan on dark
          if (normZ > 0.7) {
            r = Math.floor(220 + 35 * normZ);
            g = Math.floor(235 + 20 * normZ);
            b = 255;
          }
        }

        ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${Math.min(1.0, alpha)})`;
        ctx.beginPath();
        ctx.arc(pt.px, pt.py, Math.max(0.6 * dpr, pt.dotSize), 0, Math.PI * 2);
        ctx.fill();
      }

      // Center core ambient aura
      const auraGradient = ctx.createRadialGradient(
        centerX,
        centerY,
        0,
        centerX,
        centerY,
        sphereScale * 0.9 * dpr
      );

      if (isDark) {
        auraGradient.addColorStop(0, `rgba(49, 134, 255, ${0.12 + amplitude * 0.15})`);
        auraGradient.addColorStop(0.7, `rgba(118, 187, 255, ${0.05 + amplitude * 0.08})`);
        auraGradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
      } else {
        auraGradient.addColorStop(0, `rgba(49, 134, 255, ${0.08 + amplitude * 0.12})`);
        auraGradient.addColorStop(0.7, `rgba(49, 134, 255, ${0.03 + amplitude * 0.04})`);
        auraGradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
      }

      ctx.fillStyle = auraGradient;
      ctx.beginPath();
      ctx.arc(centerX, centerY, sphereScale * 0.9 * dpr, 0, Math.PI * 2);
      ctx.fill();

      animFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, [state, isDark, size, audioEngine]);

  return (
    <div
      onClick={onClick}
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      aria-label={`Yukti Voice Orb (${state})`}
      style={{ width: size, height: size }}
      className={`relative flex items-center justify-center select-none transition-transform duration-300 ${
        interactive ? 'cursor-pointer hover:scale-105 active:scale-95' : ''
      } ${className}`}
    >
      <canvas
        ref={canvasRef}
        style={{ width: size, height: size }}
        className="block"
      />
      {/* State label badge pill below or centered */}
      {interactive && state !== 'idle' && (
        <div className="absolute -bottom-2 px-2.5 py-0.5 rounded-full text-[11px] font-medium tracking-wide uppercase shadow-sm transition-all duration-300 backdrop-blur-md bg-white/80 dark:bg-zinc-800/80 text-accent border border-accent/20">
          {state}
        </div>
      )}
    </div>
  );
};
