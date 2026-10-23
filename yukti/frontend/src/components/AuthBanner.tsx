'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { ShieldAlert, X } from 'lucide-react';

/**
 * P0.1 (BUG-01, BEH-07.20): shown when the backend reports `/health.auth_ok === false`
 * (Application Default Credentials cannot mint a token). Polls `/health` every 60 s through the UI origin.
 * Dismissible for the current browser session only. Never shows server error text.
 */
const POLL_MS = 60_000;
const DISMISS_KEY = 'yukti.authBannerDismissed';

export const AuthBanner: React.FC<{ enabled?: boolean }> = ({ enabled = true }) => {
  const [authOk, setAuthOk] = useState<boolean | null>(null);
  const [dismissed, setDismissed] = useState(false);

  const poll = useCallback(async () => {
    try {
      const res = await fetch('/health', { cache: 'no-store', signal: AbortSignal.timeout(5000) });
      if (!res.ok) return; // backend unreachable is covered by the offline banner
      const body = await res.json();
      if (typeof body?.auth_ok === 'boolean') setAuthOk(body.auth_ok);
    } catch {
      /* offline banner handles reachability */
    }
  }, []);

  useEffect(() => {
    try {
      setDismissed(window.sessionStorage.getItem(DISMISS_KEY) === '1');
    } catch {}
  }, []);

  useEffect(() => {
    if (!enabled) return;
    void poll();
    const id = setInterval(poll, POLL_MS);
    return () => clearInterval(id);
  }, [enabled, poll]);

  if (!enabled || authOk !== false || dismissed) return null;

  return (
    <div
      role="alert"
      data-testid="auth-banner"
      className="flex items-center justify-between gap-3 px-6 py-2.5 text-[0.85rem] bg-warning-pale text-warning border-b border-[var(--hairline)]"
    >
      <div className="flex items-center gap-2 font-medium">
        <ShieldAlert className="w-4 h-4 shrink-0" />
        <span>Data service not authorised — answers are limited.</span>
      </div>
      <button
        onClick={() => {
          setDismissed(true);
          try {
            window.sessionStorage.setItem(DISMISS_KEY, '1');
          } catch {}
        }}
        className="icon-btn !w-7 !h-7"
        aria-label="Dismiss"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};
