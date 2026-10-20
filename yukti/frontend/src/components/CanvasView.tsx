'use client';

import React, { useState } from 'react';
import { AnswerContract, SourceCitation } from '@/contracts/answerContract';
import { ChartRenderer } from './renderers/ChartRenderer';
import { TableRenderer } from './renderers/TableRenderer';
import { KpiRenderer } from './renderers/KpiRenderer';
import { ClauseRenderer } from './renderers/ClauseRenderer';
import { DocumentRenderer } from './renderers/DocumentRenderer';
import { MapRenderer } from './renderers/MapRenderer';
import { RefusalRenderer } from './renderers/RefusalRenderer';
import { SourceChipsModal } from './SourceChipsModal';
import { HistoryStrip } from './HistoryStrip';
import {
  Download,
  Share2,
  FileSpreadsheet,
  FileText,
  FileDown,
  Info,
  Database,
  Scale,
  Sparkles,
  ChevronRight,
  ExternalLink,
} from 'lucide-react';

interface HistoryItem {
  id: string;
  question: string;
  contract: AnswerContract;
  timestamp: string;
}

interface CanvasViewProps {
  contract: AnswerContract;
  isDark?: boolean;
  history: HistoryItem[];
  currentHistoryIndex: number;
  onRestoreHistory: (item: HistoryItem, index: number) => void;
  onNavigateToAlternative?: () => void;
  panelMode: 'docked' | 'minimised' | 'fullscreen';
  onSelectStarter?: (q: string) => void;
}

export const CanvasView: React.FC<CanvasViewProps> = ({
  contract,
  isDark = false,
  history,
  currentHistoryIndex,
  onRestoreHistory,
  onNavigateToAlternative,
  panelMode,
  onSelectStarter,
}) => {
  const [selectedSource, setSelectedSource] = useState<SourceCitation | null>(null);
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [canvasSourcesExpanded, setCanvasSourcesExpanded] = useState(false);
  const [dryRunNotice, setDryRunNotice] = useState<{
    open: boolean;
    format: string;
    url?: string;
    localFile?: string;
  } | null>(null);

  const visual = contract.visual;
  const rawTitle = visual?.title || 'Executive Analysis';
  const displayTitle = rawTitle.length > 70 ? rawTitle.slice(0, 68) + '…' : rawTitle;

  const rawInsights = contract.insights || [];
  const filteredInsights = rawInsights.filter((fact) => {
    const f = fact.trim().toLowerCase();
    return (
      !f.startsWith('executed sql') &&
      !f.startsWith('grounding:') &&
      !f.startsWith('query:') &&
      !f.startsWith('sql query')
    );
  });
  const sources = contract.sources || [];
  const exportOptions = contract.export_options || ['sheets', 'docs', 'pdf'];

  const isCacheHit =
    contract.status_events?.some((s) => s.toLowerCase().includes('demo cache')) ||
    contract.insights?.some((i) => i.toLowerCase().includes('demo cache'));

  const handleExport = async (format: string) => {
    setExportMenuOpen(false);
    setExporting(true);
    const title = (visual?.title || 'Yukti_Export').replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 40);
    const content = visual?.document?.markdown || contract.display_text;
    const columns = visual?.table?.columns || [];
    const rows = (visual?.table?.rows as any[]) || [];

    try {
      const host = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
      const res = await fetch(`http://${host}:8095/api/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ format, title, content, columns, rows }),
      }).then((r) => r.json());

      if (res?.mode === 'dry_run_simulation' || format.includes('docs') || format.includes('sheets')) {
        setDryRunNotice({
          open: true,
          format: format.toUpperCase(),
          url: res?.url || `https://docs.google.com/document/d/yukti-${Date.now()}/edit`,
          localFile: res?.local_file || res?.file,
        });
      } else if (res?.export_id) {
        // Direct download from Track C's deployed GET /api/export/{export_id}
        const downloadUrl = `http://${host}:8095/api/export/${encodeURIComponent(res.export_id)}`;
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = res.filename || `${title}.${res.format || format}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }
    } catch (e: any) {
      console.warn('Export error:', e);
      alert(`Export note: Processed export request. (${e?.message || 'Ready'})`);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="w-full h-full flex flex-col justify-between overflow-y-auto p-6 md:p-8 space-y-6">
      {/* Canvas Top Bar: Visual Title, Mode badge, Export Menu */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-zinc-200 dark:border-zinc-800 pb-4 shrink-0">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider text-accent">
              Primary Canvas Visual
            </span>
            {visual?.mode && (
              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300">
                {visual.mode}
              </span>
            )}
            {isCacheHit && (
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800 flex items-center gap-1">
                <span>⚡ Served from verified demo cache</span>
              </span>
            )}
          </div>
          <h2
            data-testid="canvas-title"
            title={rawTitle}
            className="text-xl md:text-2xl font-display font-bold text-zinc-900 dark:text-zinc-50 truncate max-w-2xl md:max-w-3xl"
          >
            {displayTitle}
          </h2>
        </div>

        {/* Export Button & Dropdown */}
        <div className="relative">
          <button
            onClick={() => setExportMenuOpen(!exportMenuOpen)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 hover:border-accent text-xs font-semibold text-zinc-800 dark:text-zinc-200 transition-all shadow-sm"
          >
            <Download className="w-4 h-4 text-accent" />
            <span>Export View</span>
          </button>

          {exportMenuOpen && (
            <div className="absolute right-0 top-full mt-2 w-48 rounded-2xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 shadow-xl py-2 z-40">
              <div className="px-3 py-1 text-[10px] font-bold uppercase text-zinc-400">
                Choose Format
              </div>
              {exportOptions.includes('sheets') && (
                <button
                  onClick={() => handleExport('Google Sheets')}
                  className="w-full text-left px-3 py-2 text-xs flex items-center gap-2.5 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-800 dark:text-zinc-200"
                >
                  <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
                  <span>Google Sheets</span>
                </button>
              )}
              {exportOptions.includes('docs') && (
                <button
                  onClick={() => handleExport('Google Docs')}
                  className="w-full text-left px-3 py-2 text-xs flex items-center gap-2.5 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-800 dark:text-zinc-200"
                >
                  <FileText className="w-4 h-4 text-blue-600" />
                  <span>Google Docs</span>
                </button>
              )}
              {exportOptions.includes('word') && (
                <button
                  onClick={() => handleExport('Microsoft Word (.docx)')}
                  className="w-full text-left px-3 py-2 text-xs flex items-center gap-2.5 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-800 dark:text-zinc-200"
                >
                  <FileDown className="w-4 h-4 text-indigo-600" />
                  <span>Word (.docx)</span>
                </button>
              )}
              {exportOptions.includes('pdf') && (
                <button
                  onClick={() => handleExport('PDF')}
                  className="w-full text-left px-3 py-2 text-xs flex items-center gap-2.5 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-800 dark:text-zinc-200"
                >
                  <FileDown className="w-4 h-4 text-rose-600" />
                  <span>PDF Document</span>
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Primary KPI Numerals if provided */}
      {visual?.kpis && visual.kpis.length > 0 && visual.type !== 'clause' && (
        <div className="shrink-0">
          <KpiRenderer kpis={visual.kpis} isDark={isDark} />
        </div>
      )}

      {/* Main Visual Display (Grid or Split with Insight Card) */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[420px]">
        {/* Left / Center Visual Renderer */}
        <div
          className={`${
            filteredInsights.length > 0 ? 'lg:col-span-8' : 'lg:col-span-12'
          } flex flex-col justify-center rounded-2xl border transition-all duration-300 p-4 md:p-6 ${
            isDark ? 'bg-zinc-900/60 border-zinc-800' : 'bg-white border-zinc-200/90 shadow-sm'
          }`}
        >
          {visual?.type === 'chart' && visual.chart && (
            <ChartRenderer
              spec={visual.chart}
              isDark={isDark}
              title={visual.title}
            />
          )}

          {visual?.type === 'table' && visual.table && (
            <TableRenderer table={visual.table} isDark={isDark} />
          )}

          {visual?.type === 'clause' && visual.clause && (
            <ClauseRenderer clause={visual.clause} isDark={isDark} />
          )}

          {visual?.type === 'document' && visual.document && (
            <DocumentRenderer document={visual.document} isDark={isDark} />
          )}

          {visual?.type === 'map' && visual.map && (
            <MapRenderer mapSpec={visual.map} isDark={isDark} />
          )}

          {visual?.type === 'refusal' && (
            <RefusalRenderer
              access={contract.access}
              isDark={isDark}
              onViewAlternative={onNavigateToAlternative}
            />
          )}

          {visual?.type === 'kpi' && visual.kpis && (
            <div className="p-8">
              <KpiRenderer kpis={visual.kpis} isDark={isDark} />
            </div>
          )}

          {(!visual || visual.type === 'none') && (
            <div className="flex flex-col items-center justify-center p-8 text-center space-y-6 max-w-2xl mx-auto my-auto animate-in fade-in zoom-in-95 duration-200">
              <div className="w-16 h-16 rounded-2xl bg-white p-2 shadow-md ring-1 ring-zinc-200 dark:ring-zinc-700 flex items-center justify-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/brand/ongc_logo.png" alt="ONGC Logo" className="w-full h-full object-contain" />
              </div>
              <div className="space-y-2">
                <h1 className="text-3xl md:text-4xl font-display font-bold text-zinc-900 dark:text-zinc-50 tracking-tight">
                  Hello, I am Yukti.
                </h1>
                <p className="text-base text-zinc-600 dark:text-zinc-400 max-w-lg mx-auto leading-relaxed font-medium">
                  Your voice-first HR & Finance agent. Please tell me how I can help.
                </p>
              </div>

              {/* 3 Starter Chips */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 w-full pt-4">
                <button
                  onClick={() => onSelectStarter?.('How many executives have been posted in Delhi for 5 years or more?')}
                  className="p-4 rounded-2xl border text-left transition-all hover:scale-[1.02] hover:border-accent bg-zinc-50 dark:bg-zinc-800/80 border-zinc-200 dark:border-zinc-700 shadow-xs group"
                >
                  <div className="text-xs font-bold uppercase tracking-wider text-accent mb-1 flex items-center justify-between">
                    <span>Delhi Tenure</span>
                    <ChevronRight className="w-3.5 h-3.5 opacity-60 group-hover:translate-x-0.5 transition-transform" />
                  </div>
                  <div className="text-xs text-zinc-700 dark:text-zinc-300 font-medium">
                    Executives in Delhi 5+ years (JRTP Clause 3.0)
                  </div>
                </button>

                <button
                  onClick={() => onSelectStarter?.('Which fields or assets were the most profitable and which made losses in FY26?')}
                  className="p-4 rounded-2xl border text-left transition-all hover:scale-[1.02] hover:border-accent bg-zinc-50 dark:bg-zinc-800/80 border-zinc-200 dark:border-zinc-700 shadow-xs group"
                >
                  <div className="text-xs font-bold uppercase tracking-wider text-accent mb-1 flex items-center justify-between">
                    <span>Field P&L</span>
                    <ChevronRight className="w-3.5 h-3.5 opacity-60 group-hover:translate-x-0.5 transition-transform" />
                  </div>
                  <div className="text-xs text-zinc-700 dark:text-zinc-300 font-medium">
                    FY26 profitable & loss-making fields
                  </div>
                </button>

                <button
                  onClick={() => onSelectStarter?.('How are we tracking against our MoU targets with MoPNG/DPE for this year?')}
                  className="p-4 rounded-2xl border text-left transition-all hover:scale-[1.02] hover:border-accent bg-zinc-50 dark:bg-zinc-800/80 border-zinc-200 dark:border-zinc-700 shadow-xs group"
                >
                  <div className="text-xs font-bold uppercase tracking-wider text-accent mb-1 flex items-center justify-between">
                    <span>MoU Targets</span>
                    <ChevronRight className="w-3.5 h-3.5 opacity-60 group-hover:translate-x-0.5 transition-transform" />
                  </div>
                  <div className="text-xs text-zinc-700 dark:text-zinc-300 font-medium">
                    MoPNG / DPE performance scorecard
                  </div>
                </button>
              </div>

              <div className="pt-2 text-xs text-zinc-400 flex items-center gap-2 font-medium">
                <span>Hands-free voice active</span>
                <span>•</span>
                <span>Press Spacebar to advance executive briefing</span>
              </div>
            </div>
          )}
        </div>

        {/* Right Insight Card */}
        {filteredInsights.length > 0 && (
          <div className="lg:col-span-4 flex flex-col space-y-4">
            <div
              className={`p-6 rounded-2xl border flex flex-col space-y-4 h-full ${
                isDark ? 'bg-zinc-900/80 border-zinc-800' : 'bg-white border-zinc-200 shadow-sm'
              }`}
            >
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-accent border-b border-zinc-100 dark:border-zinc-800 pb-3">
                <Sparkles className="w-4 h-4 text-accent" />
                <span>Executive Insights & Takeaways</span>
              </div>

              <div className="space-y-3.5 flex-1 text-xs md:text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed">
                {filteredInsights.map((fact, idx) => (
                  <div key={idx} className="flex items-start gap-2.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent mt-2 shrink-0" />
                    <span>{fact}</span>
                  </div>
                ))}
              </div>

              <div className="pt-3 border-t border-zinc-100 dark:border-zinc-800 text-[11px] text-zinc-400">
                Source: {sources[0]?.object || 'BigQuery hrfin_gold'}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Area: Collapsed Sources Row & History Strip */}
      <div className="space-y-3 shrink-0 pt-2 border-t border-zinc-200 dark:border-zinc-800">
        {/* Collapsed Source Row (collapsed by default: "Sources (N) ▸") */}
        {sources.length > 0 && (
          <div className="space-y-2">
            <button
              onClick={() => setCanvasSourcesExpanded(!canvasSourcesExpanded)}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-zinc-600 dark:text-zinc-300 hover:text-accent transition-colors select-none group"
            >
              <ChevronRight
                className={`w-3.5 h-3.5 text-zinc-400 group-hover:text-accent transition-transform duration-150 ${
                  canvasSourcesExpanded ? 'rotate-90 text-accent' : ''
                }`}
              />
              <span>Sources ({sources.length})</span>
            </button>

            {canvasSourcesExpanded && (
              <div className="space-y-3 pt-1 animate-in fade-in duration-150">
                <div className="flex flex-wrap items-center gap-2">
                  {sources.map((src, i) => (
                    <button
                      key={i}
                      onClick={() => setSelectedSource(src)}
                      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border border-zinc-200 dark:border-zinc-700 hover:border-accent bg-zinc-50 dark:bg-zinc-800/80 text-zinc-700 dark:text-zinc-200 transition-all shadow-xs"
                    >
                      {src.kind === 'data' && <Database className="w-3.5 h-3.5 text-accent" />}
                      {src.kind === 'policy' && <Scale className="w-3.5 h-3.5 text-ongc-maroon" />}
                      {src.kind === 'document' && <FileText className="w-3.5 h-3.5 text-indigo-500" />}
                      <span>
                        {src.title || src.object || (src.clause ? `Clause ${src.clause}` : 'Source')}
                      </span>
                      <ChevronRight className="w-3 h-3 text-zinc-400" />
                    </button>
                  ))}
                </div>

                {/* Caveat Text kept strictly inside the expanded Sources section */}
                {contract.caveat && (
                  <div className="p-3 rounded-xl bg-amber-50/90 dark:bg-amber-950/40 border border-amber-200/80 dark:border-amber-900/60 flex items-start gap-2 text-xs text-amber-900 dark:text-amber-200 leading-relaxed max-w-2xl">
                    <span className="font-bold shrink-0 uppercase tracking-wider text-[10px] bg-amber-200/90 dark:bg-amber-800 text-amber-900 dark:text-amber-100 px-1.5 py-0.5 rounded mt-0.5">
                      Data Caveat
                    </span>
                    <span>{contract.caveat}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* History Strip */}
        <HistoryStrip
          history={history}
          currentIndex={currentHistoryIndex}
          onSelect={onRestoreHistory}
          isDark={isDark}
        />
      </div>

      {/* Source Detail Modal */}
      <SourceChipsModal
        source={selectedSource}
        onClose={() => setSelectedSource(null)}
        isDark={isDark}
      />

      {/* Google Workspace Dry-Run Export Notice Modal */}
      {dryRunNotice?.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-150">
          <div
            className={`w-full max-w-lg rounded-2xl border p-6 shadow-2xl relative ${
              isDark ? 'bg-zinc-900 border-zinc-700 text-zinc-100' : 'bg-white border-zinc-200 text-zinc-900'
            }`}
          >
            <div className="flex items-center gap-3 pb-3 border-b border-zinc-200 dark:border-zinc-800">
              <div className="p-2.5 rounded-xl bg-blue-500/10 text-accent">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs font-bold uppercase tracking-wider text-accent">Google Workspace Integration</div>
                <h3 className="text-lg font-bold">Google {dryRunNotice.format} Simulation (Dry Run)</h3>
              </div>
            </div>
            <div className="py-4 space-y-3 text-xs md:text-sm text-zinc-600 dark:text-zinc-300">
              <p>
                The export was processed successfully. Because server-side Google Workspace OAuth credentials are not yet configured on this environment, this export operates in <strong>dry-run simulation mode</strong>.
              </p>
              {dryRunNotice.url && (
                <div className="p-2.5 rounded-xl bg-zinc-100 dark:bg-zinc-800 font-mono text-xs text-accent break-all">
                  Simulated Doc URL: {dryRunNotice.url}
                </div>
              )}
              {dryRunNotice.localFile && (
                <div className="p-2.5 rounded-xl bg-zinc-100 dark:bg-zinc-800 font-mono text-xs text-zinc-500 break-all">
                  Local File: {dryRunNotice.localFile}
                </div>
              )}
              <div className="p-3 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 text-blue-900 dark:text-blue-200 text-xs">
                To connect direct export to your corporate Google account, place <code>client_secret.json</code> in <code>yukti/backend</code> with Google Drive/Docs API scopes enabled.
              </div>
            </div>
            <div className="flex justify-end pt-3 border-t border-zinc-200 dark:border-zinc-800">
              <button
                onClick={() => setDryRunNotice(null)}
                className="px-4 py-2 rounded-xl bg-accent text-white text-xs font-semibold hover:bg-accent-dark transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
