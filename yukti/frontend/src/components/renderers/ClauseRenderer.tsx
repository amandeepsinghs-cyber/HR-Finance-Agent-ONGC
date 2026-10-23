'use client';

import React, { useState } from 'react';
import { ClauseSpec } from '@/contracts/answerContract';
import { Copy, Check, ShieldCheck, Scale, ChevronDown, ChevronRight, FileText } from 'lucide-react';

interface ClauseRendererProps {
  clause: ClauseSpec;
  isDark?: boolean;
}

export const ClauseRenderer: React.FC<ClauseRendererProps> = ({ clause, isDark = false }) => {
  const [copied, setCopied] = useState(false);
  const [showFullClause, setShowFullClause] = useState(false);

  const handleCopy = () => {
    if (clause.text) {
      navigator.clipboard.writeText(clause.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const fullText = clause.text || '';
  const highlight = clause.highlight || '';

  // Extract highlight or first governing paragraph
  const primaryHighlight = highlight || fullText.slice(0, 220);
  const remainingText = highlight && fullText.includes(highlight)
    ? fullText.replace(highlight, '').trim()
    : fullText;

  return (
    <div
      data-testid="clause-renderer"
      className="card p-[1.6rem] flex flex-col h-[clamp(24rem,calc(100vh-22rem),46rem)] overflow-hidden"
    >
      {/* Top Banner (Fixed) */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-zinc-100 dark:border-zinc-800 pb-4 shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-accent/10 text-accent">
            <Scale className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs uppercase font-bold tracking-wider text-ongc-maroon">
              {clause.doc_id || 'ONGC Policy Manual'}
            </div>
            <h3 className="text-lg md:text-xl font-bold text-zinc-900 dark:text-zinc-100">
              {clause.doc_title || 'Job Rotation & Transfer Policy (JRTP)'}
            </h3>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {clause.clause_ref && (
            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 dark:bg-blue-950/60 text-accent border border-accent/20">
              {clause.clause_ref}
            </span>
          )}
          <button
            onClick={handleCopy}
            className={`p-2 rounded-lg border text-xs font-medium flex items-center gap-1.5 transition-colors ${
              isDark
                ? 'border-zinc-700 hover:border-zinc-500 text-zinc-300'
                : 'border-zinc-200 hover:border-zinc-400 text-zinc-700'
            }`}
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
      </div>

      {/* Scrollable Clause Body (Constrained strictly to card) */}
      <div className="flex-1 overflow-y-auto min-h-0 py-4 space-y-4 pr-1">
        {/* Primary Highlighted Clause Shown First */}
        <div className="p-4 rounded-xl bg-amber-50/90 dark:bg-amber-950/40 border-l-4 border-amber-500 text-amber-950 dark:text-amber-100 font-serif text-base md:text-lg leading-relaxed shadow-xs">
          <div className="text-[10px] font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400 mb-1 flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5" />
            <span>Key Governing Provision</span>
          </div>
          <mark className="bg-amber-200/80 dark:bg-amber-900/60 text-amber-950 dark:text-amber-50 px-1 py-0.5 rounded font-semibold">
            {primaryHighlight}
          </mark>
        </div>

        {/* Collapsible Full Clause Body */}
        {fullText && (
          <div className="space-y-2">
            <button
              type="button"
              onClick={() => setShowFullClause((prev) => !prev)}
              className="flex items-center gap-1 text-xs font-semibold text-accent hover:underline select-none"
            >
              {showFullClause ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
              <span>{showFullClause ? 'Hide full clause text' : 'Show full clause text'}</span>
            </button>

            {showFullClause && (
              <div
                className={`p-5 rounded-xl font-serif text-sm md:text-base leading-relaxed whitespace-pre-line border transition-all ${
                  isDark
                    ? 'bg-zinc-800/50 border-zinc-700/80 text-zinc-200'
                    : 'bg-zinc-50 border-zinc-200 text-zinc-800'
                }`}
              >
                {fullText}
              </div>
            )}
          </div>
        )}

        {/* Statutory Guidance Note */}
        <div className="flex items-start gap-3 p-3.5 rounded-xl bg-blue-50/60 dark:bg-blue-950/30 border border-blue-100 dark:border-blue-900/40 text-xs text-zinc-600 dark:text-zinc-400">
          <ShieldCheck className="w-4 h-4 text-accent shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-zinc-800 dark:text-zinc-200">Legal Authority: </span>
            This clause has statutory force across all ONGC business units and cadres under {clause.doc_id || 'ONGC Corporate Policy'} governance.
          </div>
        </div>
      </div>
    </div>
  );
};
