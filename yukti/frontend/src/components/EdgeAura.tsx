'use client';

/**
 * EdgeAura (P4.9, SPEC-09 §4.9; V16/V21 — low priority): a 6 px inset glow around the viewport, keyed to the
 * voice state, so the AI-aura presence is visible on a big screen. OFF by default; enabled only with `?aura=1`
 * until sponsor review (D-53). Tokens only; `prefers-reduced-motion` → static glow (CSS).
 */
import React, { useEffect, useState } from 'react';
import type { OrbState } from './VoiceOrb';

export function EdgeAura({ state }: { state: OrbState }) {
  const [enabled, setEnabled] = useState(false);
  useEffect(() => {
    try {
      setEnabled(new URLSearchParams(window.location.search).get('aura') === '1');
    } catch {
      setEnabled(false);
    }
  }, []);
  if (!enabled || state === 'idle') return null;
  return <div className="yk-edge-aura" data-state={state} data-testid="edge-aura" aria-hidden />;
}
