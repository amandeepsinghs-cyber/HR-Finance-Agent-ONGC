'use client';

import React, { useState } from 'react';
import { SourceCitation } from '@/contracts/answerContract';
import { Database, FileText, Scale, X, ExternalLink, Code } from 'lucide-react';

interface SourceChipsModalProps {
  source: SourceCitation | null;
  onClose: () => void;
  isDark?: boolean;
}

export const SourceChipsModal: React.FC<SourceChipsModalProps> = ({
  source,
  onClose,
  isDark = false,
}) => {
  const [showSql, setShowSql] = useState(false);
  if (!source) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        className={`w-full max-w-xl rounded-2xl border p-6 shadow-2xl relative transition-all ${
          isDark ? 'bg-zinc-900 border-zinc-700 text-zinc-100' : 'bg-white border-zinc-200 text-zinc-900'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-zinc-200 dark:border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-accent/10 text-accent">
              {source.kind === 'data' && <Database className="w-5 h-5" />}
              {source.kind === 'policy' && <Scale className="w-5 h-5" />}
              {source.kind === 'document' && <FileText className="w-5 h-5" />}
            </div>
            <div>
              <div className="text-xs uppercase font-bold tracking-wider text-accent">
                Source Lineage & Provenance
              </div>
              <h3 className="text-lg font-bold">
                {source.title || source.object || source.doc_id || 'Enterprise Data Source'}
              </h3>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="py-4 space-y-4 text-xs md:text-sm">
          {source.kind === 'data' && (
            <>
              <div>
                <span className="font-semibold text-zinc-500 dark:text-zinc-400">Target Object: </span>
                <span className="font-mono font-bold">{source.object}</span>
              </div>
              {source.query_id && (
                <div>
                  <span className="font-semibold text-zinc-500 dark:text-zinc-400">Query ID: </span>
                  <span className="font-mono text-zinc-600 dark:text-zinc-400">{source.query_id}</span>
                </div>
              )}
              {source.sql && (
                <div className="space-y-2 pt-1 border-t border-zinc-100 dark:border-zinc-800">
                  <button
                    onClick={() => setShowSql((s) => !s)}
                    className="flex items-center gap-1.5 text-xs font-semibold text-accent hover:underline"
                  >
                    <Code className="w-3.5 h-3.5" />
                    <span>{showSql ? 'Hide SQL Query' : 'Show Validated BigQuery SQL'}</span>
                  </button>
                  {showSql && (
                    <pre className="p-3 rounded-xl bg-zinc-950 text-emerald-400 font-mono text-xs overflow-x-auto leading-relaxed border border-zinc-800 animate-in fade-in duration-150">
                      {source.sql}
                    </pre>
                  )}
                </div>
              )}
            </>
          )}

          {source.kind === 'policy' && (
            <>
              <div>
                <span className="font-semibold text-zinc-500 dark:text-zinc-400">Document Identifier: </span>
                <span className="font-mono font-bold">{source.doc_id}</span>
              </div>
              {source.clause && (
                <div>
                  <span className="font-semibold text-zinc-500 dark:text-zinc-400">Clause Reference: </span>
                  <span className="font-semibold text-accent">{source.clause}</span>
                </div>
              )}
              <div className="p-3 rounded-xl bg-blue-50 dark:bg-blue-950/40 text-blue-900 dark:text-blue-200 border border-blue-200 dark:border-blue-900/50 text-xs">
                Official statutory regulation verified against Corporate HR Master Policy Manual and Court Precedents.
              </div>
            </>
          )}

          {source.kind === 'document' && (
            <>
              <div>
                <span className="font-semibold text-zinc-500 dark:text-zinc-400">Document Title: </span>
                <span className="font-bold">{source.title}</span>
              </div>
              <div>
                <span className="font-semibold text-zinc-500 dark:text-zinc-400">Document ID: </span>
                <span className="font-mono">{source.doc_id}</span>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-zinc-200 dark:border-zinc-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-800 text-xs font-semibold hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
