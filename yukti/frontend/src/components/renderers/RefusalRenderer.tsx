'use client';

/**
 * RefusalRenderer (P2H.2, SPEC-06 §4.6). Polite, policy-correct refusal: the first line is the backend's
 * refusal copy (by code + language, from refusal_copy.yaml), then the permitted alternative(s) as chips that ask
 * the allowed question, and a "Why?" disclosure with the rule reference. Tokens only, light + dark.
 */
import React, { useState } from 'react';
import type { AccessControl, RefusalAlternative } from '@/contracts/answerContract';
import { ShieldAlert, ArrowRight, ChevronDown } from 'lucide-react';

interface RefusalRendererProps {
  access: AccessControl;
  isDark?: boolean;
  /** ask the permitted alternative question (chip click) */
  onAsk?: (question: string) => void;
  /** legacy: navigate to a precomputed alternative visual */
  onViewAlternative?: () => void;
}

function alternativesOf(access: AccessControl): RefusalAlternative[] {
  const list: RefusalAlternative[] = [...(access.alternatives || [])];
  const a = access.alternative;
  if (a && typeof a === 'object' && a.question && !list.some((x) => x.question === a.question)) list.unshift(a);
  if (typeof a === 'string' && a.trim() && !list.some((x) => x.question === a)) list.unshift({ label: a, question: a });
  return list.slice(0, 3);
}

export const RefusalRenderer: React.FC<RefusalRendererProps> = ({ access, onAsk, onViewAlternative }) => {
  const [why, setWhy] = useState(false);
  const alts = alternativesOf(access);
  return (
    <div
      data-testid="refusal-card"
      data-code={access.code || ''}
      className="rounded-[var(--radius-lg)] border border-[var(--hairline)] bg-[var(--card)] p-5 md:p-6 flex flex-col gap-4"
    >
      <div className="flex items-start gap-3.5">
        <div className="p-2.5 rounded-[var(--radius-md)] bg-[var(--maroon-pale)] text-[var(--maroon)] shrink-0">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <div className="min-w-0 space-y-1">
          <div className="text-label uppercase tracking-[0.08em] text-[var(--maroon)]">Not available for your role</div>
          <p className="text-[0.98rem] leading-relaxed text-[var(--ink)]" data-testid="refusal-line">
            {access.reason || 'This information is restricted for your role.'}
          </p>
        </div>
      </div>

      {alts.length > 0 && (
        <div className="flex flex-col gap-2" data-testid="refusal-alternatives">
          <div className="text-label text-[var(--ink-2)]">You can ask instead</div>
          <div className="flex flex-wrap gap-2">
            {alts.map((alt) => (
              <button
                key={alt.question}
                type="button"
                data-testid="refusal-alternative"
                onClick={() => (onAsk ? onAsk(alt.question) : onViewAlternative?.())}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-pill border border-[var(--hairline)] bg-[var(--surface)] text-label text-[var(--ink)] hover:bg-[var(--accent-pale)] transition-colors"
              >
                <span>{alt.label || alt.question}</span>
                <ArrowRight className="w-3.5 h-3.5 text-[var(--accent)]" />
              </button>
            ))}
          </div>
        </div>
      )}

      {access.rule_ref && (
        <div>
          <button
            type="button"
            aria-expanded={why}
            onClick={() => setWhy((w) => !w)}
            className="inline-flex items-center gap-1 text-caption text-[var(--ink-2)] hover:text-[var(--ink)]"
            data-testid="refusal-why"
          >
            Why?
            <ChevronDown className={`w-3.5 h-3.5 transition-transform ${why ? 'rotate-180' : ''}`} />
          </button>
          {why && (
            <div className="mt-1.5 text-caption text-[var(--ink-2)]" data-testid="refusal-rule">
              Policy reference: <span className="font-mono">{access.rule_ref}</span>
              {access.code ? <span> · code {access.code}</span> : null}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
