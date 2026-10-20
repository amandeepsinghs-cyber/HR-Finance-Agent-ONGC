'use client';

import React from 'react';
import { DocumentSpec } from '@/contracts/answerContract';
import { FileText, Download, Share2, FileDown } from 'lucide-react';

interface DocumentRendererProps {
  document: DocumentSpec;
  isDark?: boolean;
}

export const DocumentRenderer: React.FC<DocumentRendererProps> = ({ document, isDark = false }) => {
  const markdownText = document.markdown || '';

  // Parses inline formatting like **bold** into React nodes
  const renderInlineMarkdown = (text: string) => {
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, idx) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={idx} className="font-bold text-zinc-900 dark:text-zinc-100">
            {part.slice(2, -2)}
          </strong>
        );
      }
      return part;
    });
  };

  // Render markdown lines cleanly
  const renderFormattedMarkdown = (md: string) => {
    const lines = md.split('\n');
    const elements: React.ReactNode[] = [];
    let tableLines: string[] = [];
    let inTable = false;

    const flushTable = (key: number) => {
      if (tableLines.length >= 2) {
        const headerCols = tableLines[0].split('|').filter(c => c.trim().length > 0).map(c => c.trim());
        const dataRows = tableLines.slice(2).map(l => l.split('|').filter(c => c.trim().length > 0).map(c => c.trim()));

        elements.push(
          <div key={`table-${key}`} className="my-4 overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-700">
            <table className="w-full text-left text-xs md:text-sm border-collapse">
              <thead className="bg-zinc-100 dark:bg-zinc-800">
                <tr>
                  {headerCols.map((h, i) => (
                    <th key={i} className="py-2.5 px-3 font-semibold text-zinc-700 dark:text-zinc-300 border-b border-zinc-200 dark:border-zinc-700">
                      {renderInlineMarkdown(h)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
                {dataRows.map((r, ri) => (
                  <tr key={ri} className="hover:bg-zinc-50/50 dark:hover:bg-zinc-800/50">
                    {r.map((cell, ci) => (
                      <td key={ci} className="py-2 px-3 text-zinc-800 dark:text-zinc-200">
                        {renderInlineMarkdown(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
      tableLines = [];
      inTable = false;
    };

    lines.forEach((line, idx) => {
      const trimmed = line.trim();

      if (trimmed.startsWith('|')) {
        inTable = true;
        tableLines.push(trimmed);
        return;
      } else if (inTable) {
        flushTable(idx);
      }

      if (trimmed.startsWith('# ')) {
        elements.push(
          <h1 key={idx} className="text-xl md:text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50 mt-4 mb-2">
            {renderInlineMarkdown(trimmed.slice(2))}
          </h1>
        );
      } else if (trimmed.startsWith('## ')) {
        elements.push(
          <h2 key={idx} className="text-lg md:text-xl font-bold tracking-tight text-zinc-800 dark:text-zinc-100 mt-3.5 mb-1.5">
            {renderInlineMarkdown(trimmed.slice(3))}
          </h2>
        );
      } else if (trimmed.startsWith('### ')) {
        elements.push(
          <h3 key={idx} className="text-sm md:text-base font-semibold text-ongc-maroon tracking-wide uppercase mb-3">
            {renderInlineMarkdown(trimmed.slice(4))}
          </h3>
        );
      } else if (trimmed.startsWith('#### ')) {
        elements.push(
          <h4 key={idx} className="text-sm font-bold text-zinc-800 dark:text-zinc-200 mt-3 mb-1">
            {trimmed.slice(5)}
          </h4>
        );
      } else if (trimmed.startsWith('---')) {
        elements.push(<hr key={idx} className="my-4 border-zinc-200 dark:border-zinc-800" />);
      } else if (trimmed.length > 0) {
        elements.push(
          <p key={idx} className="my-1.5 leading-relaxed text-sm md:text-base text-zinc-700 dark:text-zinc-300">
            {renderInlineMarkdown(trimmed)}
          </p>
        );
      }
    });

    if (inTable) {
      flushTable(lines.length);
    }

    return elements;
  };

  return (
    <div
      data-testid="document-renderer"
      className={`rounded-2xl border flex flex-col h-[520px] max-h-[calc(100vh-16rem)] transition-all duration-300 overflow-hidden shadow-lg ${
        isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'
      }`}
    >
      {/* Official ONGC Letterhead Banner */}
      <div className="bg-ongc-maroon text-white px-6 py-3.5 flex flex-wrap items-center justify-between gap-4 shrink-0">
        <div className="flex items-center gap-3">
          <div
            title="Oil and Natural Gas Corporation Limited (Official Logo)"
            className="w-10 h-10 rounded-xl bg-white p-1 flex items-center justify-center shadow-xs shrink-0"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/brand/ongc_logo.png"
              alt="ONGC Logo"
              className="w-full h-full object-contain"
            />
          </div>
          <div>
            <div className="text-xs uppercase tracking-wider text-white/80 font-medium">
              Oil and Natural Gas Corporation Limited
            </div>
            <div className="text-base font-bold text-white">
              {document.title || 'Official Parliamentary Reply'}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-white/20 text-white border border-white/30 backdrop-blur-sm">
            {document.doc_type || 'Parliament Reply'}
          </span>
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/30 text-emerald-200 border border-emerald-400/40">
            Draft v{document.version || 1}
          </span>
        </div>
      </div>

      {/* Document Action Bar */}
      <div className="px-6 py-2 bg-zinc-50 dark:bg-zinc-800/60 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between text-xs text-zinc-600 dark:text-zinc-300 shrink-0">
        <div className="flex items-center gap-2 font-medium">
          <FileText className="w-3.5 h-3.5 text-accent" />
          <span>Official Executive Draft</span>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-1 hover:text-accent transition-colors font-medium">
            <Download className="w-3.5 h-3.5" />
            <span>Download .docx</span>
          </button>
          <button className="flex items-center gap-1 hover:text-accent transition-colors font-medium">
            <Share2 className="w-3.5 h-3.5" />
            <span>Open in Google Docs</span>
          </button>
        </div>
      </div>

      {/* Document Content Canvas - strictly scrolls internally */}
      <div className="p-6 md:p-8 flex-1 overflow-y-auto min-h-0">
        {renderFormattedMarkdown(markdownText)}
      </div>
    </div>
  );
};
