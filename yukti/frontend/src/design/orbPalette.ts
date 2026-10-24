/**
 * Voice-orb aura palette (design tokens for the canvas renderer; BUG-35).
 * Canvas gradients need numeric RGB, so the orb's hues live here in src/design/ (the token source folder)
 * rather than as literals inside components. Hues follow the AI-aura family in tokens.json.
 */
export type RGB = [number, number, number];

export interface CloudSpec {
  color: RGB;
  orbitX: number;
  orbitY: number;
  speedX: number;
  speedY: number;
  phase: number;
  radiusMul: number;
  alphaMul: number;
}

/** CSS colour string for an RGB triple at alpha `a` (clamped to 0..1). */
export const tint = (c: RGB, a: number) => `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${Math.max(0, Math.min(1, a))})`;

// Airy, luminous Siri / Google AI aura hues — positioned around a luminous white core so colors stay pure and never mix into gray
export const CLOUDS_LIGHT: CloudSpec[] = [
  { color: [59, 130, 246], orbitX: 0.17, orbitY: 0.16, speedX: 0.75, speedY: 0.92, phase: 0.0, radiusMul: 0.27, alphaMul: 0.52 },   // Sky Cobalt Blue
  { color: [139, 92, 246], orbitX: 0.17, orbitY: 0.17, speedX: -0.82, speedY: 0.68, phase: 1.57, radiusMul: 0.26, alphaMul: 0.48 },  // Feathery Violet
  { color: [244, 63, 94], orbitX: 0.16, orbitY: 0.16, speedX: 0.64, speedY: -0.88, phase: 3.14, radiusMul: 0.26, alphaMul: 0.46 },   // Soft Rose Coral
  { color: [6, 182, 212], orbitX: 0.17, orbitY: 0.15, speedX: -0.7, speedY: -0.78, phase: 4.71, radiusMul: 0.27, alphaMul: 0.48 },   // Luminous Aqua Cyan
  { color: [251, 191, 36], orbitX: 0.14, orbitY: 0.14, speedX: 0.88, speedY: 0.58, phase: 2.35, radiusMul: 0.23, alphaMul: 0.38 },   // Warm Gold Light
];

export const CLOUDS_DARK: CloudSpec[] = [
  { color: [96, 165, 250], orbitX: 0.17, orbitY: 0.16, speedX: 0.75, speedY: 0.92, phase: 0.0, radiusMul: 0.27, alphaMul: 0.55 },
  { color: [167, 139, 250], orbitX: 0.17, orbitY: 0.17, speedX: -0.82, speedY: 0.68, phase: 1.57, radiusMul: 0.26, alphaMul: 0.50 },
  { color: [251, 113, 133], orbitX: 0.16, orbitY: 0.16, speedX: 0.64, speedY: -0.88, phase: 3.14, radiusMul: 0.26, alphaMul: 0.48 },
  { color: [34, 211, 238], orbitX: 0.17, orbitY: 0.15, speedX: -0.7, speedY: -0.78, phase: 4.71, radiusMul: 0.27, alphaMul: 0.50 },
  { color: [251, 191, 36], orbitX: 0.14, orbitY: 0.14, speedX: 0.88, speedY: 0.58, phase: 2.35, radiusMul: 0.23, alphaMul: 0.40 },
];
