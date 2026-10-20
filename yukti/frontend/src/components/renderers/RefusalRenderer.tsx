'use client';

import React from 'react';
import { AccessControl } from '@/contracts/answerContract';
import { ShieldAlert, FileText, ArrowRight, Lock } from 'lucide-react';

interface RefusalRendererProps {
  access: AccessControl;
  isDark?: boolean;
  onViewAlternative?: () => void;
}

export const RefusalRenderer: React.FC<RefusalRendererProps> = ({
  access,
  isDark = false,
  onViewAlternative,
}) => {
  return (
    <div
      data-testid="refusal-card"
      className={`rounded-2xl border p-6 md:p-8 flex flex-col space-y-6 transition-all duration-300 relative overflow-hidden shadow-sm ${
        isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'
      }`}
    >
      {/* Top Banner Alert */}
      <div className="flex items-start gap-4">
        <div className="p-3.5 rounded-2xl bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 shrink-0">
          <ShieldAlert className="w-8 h-8" />
        </div>
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-200 dark:border-rose-900/50">
            <Lock className="w-3 h-3" />
            <span>Access Restricted under Role Policy</span>
          </div>
          <h3 className="text-xl font-bold text-zinc-900 dark:text-zinc-50">
            Confidential Deliberative Record
          </h3>
          <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
            {access.reason ||
              'Unapproved draft transfer proposals and placement notes are non-final deliberative records exempt from disclosure prior to official notification by Director (HR).'}
          </p>
        </div>
      </div>

      {/* Justification Box */}
      <div
        className={`p-4 rounded-xl border flex flex-col space-y-2 text-xs md:text-sm ${
          isDark
            ? 'bg-zinc-800/40 border-zinc-700 text-zinc-300'
            : 'bg-zinc-50 border-zinc-200 text-zinc-700'
        }`}
      >
        <div className="font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
          <FileText className="w-4 h-4 text-ongc-maroon" />
          <span>Policy & Statutory Justification:</span>
        </div>
        <div className="font-mono text-xs bg-zinc-100 dark:bg-zinc-800 p-2.5 rounded-lg text-zinc-800 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-700">
          {access.rule_ref || 'ONGC JRTP Clause 11.0 & RTI Act Section 8(1)(i)'}
        </div>
      </div>

      {/* Permitted Alternative Box */}
      {access.alternative && (
        <div className="p-5 rounded-xl bg-blue-50/70 dark:bg-blue-950/30 border border-blue-200/80 dark:border-blue-900/50 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="text-xs font-bold uppercase tracking-wider text-accent">
              Permitted Alternative Available
            </div>
            <div className="text-sm text-zinc-700 dark:text-zinc-300">
              {access.alternative}
            </div>
          </div>
          <button
            onClick={onViewAlternative}
            className="px-4 py-2 rounded-xl bg-accent text-white text-xs font-semibold hover:bg-accent-dark transition-all flex items-center justify-center gap-1.5 shrink-0 shadow-sm"
          >
            <span>View Station Norms</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
};
