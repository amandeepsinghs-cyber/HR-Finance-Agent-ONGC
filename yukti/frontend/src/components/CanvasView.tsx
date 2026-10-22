'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { AnswerContract, ChartKind, ChartSpec, SourceCitation } from '@/contracts/answerContract';
import { ChartRenderer } from './renderers/ChartRenderer';
import { TableRenderer } from './renderers/TableRenderer';
import { KpiRenderer } from './renderers/KpiRenderer';
import { ClauseRenderer } from './renderers/ClauseRenderer';
import { DocumentRenderer } from './renderers/DocumentRenderer';
import { MapRenderer } from './renderers/MapRenderer';
import { RefusalRenderer } from './renderers/RefusalRenderer';
import { SourceChipsModal } from './SourceChipsModal';
import { VoiceOrb, OrbState } from './VoiceOrb';
import { VoiceAudioEngine } from '@/services/audioAnalyser';
import { LevelMeter } from './TopBar';
import { sourceLabel, ChatMessage } from './FloatingConversationPanel';
import { planChart } from '@/charts/plan';
import { cleanText, humanizeKey, toNumber } from '@/charts/format';
import { ContextChips } from './ui/primitives';
import { Download, ChevronRight, Database, Scale, FileText, Mic, Users, TrendingUp, Target, Check, Loader2, Volume2, BarChart3, PieChart, Activity, Table as TableIcon, SlidersHorizontal } from 'lucide-react';

export interface HistoryItem {
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
  onSelectStarter?: (q: string) => void;
  busy?: boolean;
  statusLine?: string | null;
  onTalk?: () => void;
  isMicActive?: boolean;
  orbState?: OrbState;
  audioEngine?: VoiceAudioEngine;
  messages?: ChatMessage[];
  liveInterimText?: string;
  /** active persona: drives the greeting name and suggestion cards (U4.5) */
  persona?: string;
}

const NOISE = /^(executed sql|grounding:|query:|sql query|voice turn completed|yukti ai connected|role:|served from|canvas visual|turn complete)/i;

const EXPORT_LABELS: Record<string, string> = {
  sheets: 'Google Sheets',
  docs: 'Google Docs',
  word: 'Word (.docx)',
  pdf: 'PDF',
  xlsx: 'Excel (.xlsx)',
};

type Starter = { icon: React.ComponentType<{ className?: string }>; tag: string; title: string; q: string };

// U4.5: persona-specific suggestions (HR · HR · Finance · Policy). E-level personas get aggregate/self-service asks (D-11).
const STARTERS: Record<string, Starter[]> = {
  CMD: [
    { icon: Users, tag: 'People · Transfers', title: 'Delhi HQ: executives posted 5+ years', q: 'How many executives have been posted in Delhi for 5 years or more?' },
    { icon: Activity, tag: 'People · Growth', title: 'Where did headcount grow the most?', q: 'Which areas saw the most headcount increase in the last 5 years, and which saw none?' },
    { icon: TrendingUp, tag: 'Finance · FY26', title: 'Most profitable and loss-making fields', q: 'Which fields or assets were the most profitable and which made losses in FY26?' },
    { icon: Scale, tag: 'Policy', title: 'Station tenure and rotation rules', q: 'What is the minimum tenure at a station, and the maximum cumulative stay in one city?' },
  ],
  DIR_HR: [
    { icon: Users, tag: 'People · Transfers', title: 'Delhi HQ: 5+ year postings', q: 'How many executives have been posted in Delhi for 5 years or more?' },
    { icon: Target, tag: 'People · Succession', title: 'E7+ retiring in 3 years without a successor', q: 'How many E7+ officers retire in the next 3 years, and which roles have no ready successor?' },
    { icon: TrendingUp, tag: 'Finance · People cost', title: 'Payroll and overtime by work centre', q: 'What is the FY26 payroll and overtime cost by work centre?' },
    { icon: Scale, tag: 'Policy', title: 'Transfer policy for long-stay officers', q: 'What does the transfer policy say about officers posted 5 years or more?' },
  ],
  DIR_FIN: [
    { icon: TrendingUp, tag: 'Finance · FY26', title: 'Most profitable and loss-making fields', q: 'Which fields or assets were the most profitable and which made losses in FY26?' },
    { icon: BarChart3, tag: 'Finance · Capex', title: 'Under-invested fields vs reserves', q: 'Where have we invested the most capex in the last 5 years, and which fields are under-invested relative to their reserves?' },
    { icon: Target, tag: 'Performance · DPE', title: 'MoU target scorecard', q: 'How are we tracking against our MoU targets with MoPNG/DPE for this year?' },
    { icon: Scale, tag: 'Receivables', title: 'Receivables ageing by customer', q: 'How old are receivables from oil marketing companies and gas buyers, by customer?' },
  ],
  E2_HR: [
    { icon: Scale, tag: 'Policy', title: 'My leave entitlements', q: 'What leave am I entitled to under the ONGC leave rules?' },
    { icon: Scale, tag: 'Policy', title: 'Station tenure norms', q: 'What is the minimum tenure at a station, and the maximum cumulative stay in one city?' },
    { icon: Users, tag: 'People · Aggregate', title: 'Headcount by work centre', q: 'What is the headcount by work centre?' },
    { icon: TrendingUp, tag: 'Finance · Public', title: 'ONGC FY26 revenue and profit', q: 'What were ONGC revenue and profit in FY26?' },
  ],
};
STARTERS.E3_FIN = STARTERS.E2_HR;

const PRIMARY_KINDS: { id: ChartKind | 'table'; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: 'bar', label: 'Bar', icon: BarChart3 },
  { id: 'hbar', label: 'H-Bar', icon: BarChart3 },
  { id: 'donut', label: 'Donut', icon: PieChart },
  { id: 'line', label: 'Line', icon: Activity },
  { id: 'histogram', label: 'Histogram', icon: BarChart3 },
  { id: 'table', label: 'Table', icon: TableIcon },
];
const MORE_KINDS: { id: ChartKind; label: string }[] = [
  { id: 'pie', label: 'Pie' },
  { id: 'area', label: 'Area' },
  { id: 'scatter', label: 'Scatter' },
  { id: 'treemap', label: 'Treemap' },
  { id: 'waterfall', label: 'Waterfall' },
];
const ROLE_SHORT: Record<string, string> = { CMD: 'CMD', DIR_HR: 'Director HR', DIR_FIN: 'Director Finance', E2_HR: 'E2 · HR', E3_FIN: 'E3 · Finance' };

const ADDRESS: Record<string, string> = { CMD: 'Chairman', DIR_HR: 'Director', DIR_FIN: 'Director', E2_HR: 'Pooja', E3_FIN: 'Rajesh' };

function eyebrowFor(c: AnswerContract): string {
  const v = c.visual;
  if (c.access?.status === 'refused' || v?.type === 'refusal') return 'Access restricted';
  switch (v?.type) {
    case 'clause':
      return 'Policy';
    case 'document':
      return 'Draft document';
    case 'map':
      return 'Across India';
    case 'table':
      return 'Records';
    default:
      return v?.mode === 'refine' ? 'Refined view' : 'Executive Briefing';
  }
}

function greetingWord(): string {
  const h = new Date().getHours();
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
}

const Greeting: React.FC<{
  onSelect?: (q: string) => void;
  onTalk?: () => void;
  isMicActive?: boolean;
  orbState?: OrbState;
  isDark?: boolean;
  audioEngine?: VoiceAudioEngine;
  messages?: ChatMessage[];
  liveInterimText?: string;
  persona?: string;
}> = ({ onSelect, onTalk, isMicActive, orbState = 'idle', isDark = false, audioEngine, messages = [], liveInterimText, persona = 'CMD' }) => {
  const lastTurn = messages[messages.length - 1];
  const starters = STARTERS[persona] || STARTERS.CMD;
  // Time-aware greeting computed on the client after mount (server render may run in UTC).
  const [hello, setHello] = useState('Hello');
  useEffect(() => setHello(greetingWord()), []);
  const name = ADDRESS[persona] || 'Chairman';

  return (
    <div className="relative flex-1 flex flex-col items-center justify-center text-center px-6 pt-6 pb-36 w-full" data-testid="greeting">
      {/* AI aura bloom (D-16): feathery light behind Yukti's presence only */}
      <div className="pointer-events-none absolute -inset-x-16 -top-10 h-[80%] [mask-image:radial-gradient(ellipse_at_center,black_35%,transparent_72%)] [-webkit-mask-image:radial-gradient(ellipse_at_center,black_35%,transparent_72%)]" aria-hidden>
        <div className="yk-aura-bloom" />
      </div>

      <div className="relative flex flex-col items-center max-w-[60rem] w-full">
        <div data-testid="greeting-talk" className="cursor-pointer">
          <VoiceOrb
            state={orbState}
            isDark={isDark}
            size={132}
            onClick={onTalk}
            audioEngine={audioEngine}
            label={isMicActive ? 'Stop listening' : 'Start talking to Yukti'}
          />
        </div>

        <h1 className="mt-6 text-display font-display text-[var(--ink)]">
          {hello}, {name}
        </h1>
        <p className="mt-2 text-body text-[var(--ink-2)]">I&apos;m Yukti, your HR &amp; Finance agent. Ask by voice or type below.</p>

        {liveInterimText ? (
          <p className="mt-5 text-body text-[var(--ink-2)] max-w-[44rem] animate-pulse">&ldquo;{liveInterimText}&rdquo;</p>
        ) : lastTurn ? (
          <p className="mt-5 text-body text-[var(--ink-2)] max-w-[42rem]">{lastTurn.text}</p>
        ) : null}

        <div className="mt-10 grid w-full gap-3 grid-cols-1 sm:grid-cols-2 xl:grid-cols-4" data-testid="starter-cards">
          {starters.map((c) => {
            const Icon = c.icon;
            return (
              <button
                key={c.title}
                onClick={() => onSelect?.(c.q)}
                className="group text-left rounded-card border border-[var(--hairline)] bg-[var(--glass)] backdrop-blur-md shadow-[var(--card-shadow)] px-5 py-4 transition duration-fast hover:-translate-y-0.5 hover:border-[var(--accent-soft)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent)]"
              >
                <span className="flex items-center gap-2 text-caption uppercase tracking-[0.06em] text-[var(--ink-3)]">
                  <Icon className="w-3.5 h-3.5 text-[var(--accent-deep)] dark:text-[var(--accent-soft)]" />
                  {c.tag}
                </span>
                <span className="mt-2 block text-label font-semibold text-[var(--ink)] leading-snug group-hover:text-[var(--accent-deep)] dark:group-hover:text-[var(--accent-soft)]">
                  {c.title}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export const CanvasView: React.FC<CanvasViewProps> = ({
  contract,
  isDark = false,
  history,
  currentHistoryIndex,
  onRestoreHistory,
  onNavigateToAlternative,
  onSelectStarter,
  busy,
  onTalk,
  isMicActive,
  orbState = 'idle',
  audioEngine,
  messages = [],
  persona,
  liveInterimText,
}) => {
  const [selectedSource, setSelectedSource] = useState<SourceCitation | null>(null);
  const [exportOpen, setExportOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [glow, setGlow] = useState<'listening' | 'fade' | 'off'>('off');
  const seenTurns = useRef<Set<string>>(new Set());
  useEffect(() => {
    setMoreOpen(false);
    const tid = contract.turn_id;
    if (!tid || !contract.visual || contract.visual.type === 'none') return;
    if (seenTurns.current.has(tid)) return; // restored from history: not the newest answer
    seenTurns.current.add(tid);
    setGlow('listening');
    const t1 = window.setTimeout(() => setGlow('fade'), 4000);
    const t2 = window.setTimeout(() => setGlow('off'), 5600); // stop the animated layers entirely
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
    };
  }, [contract.turn_id]); // eslint-disable-line react-hooks/exhaustive-deps

  // More menu: outside click / Escape close; focus first item on open
  const moreRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (!moreOpen) return;
    moreRef.current?.querySelector<HTMLButtonElement>('[role="menuitem"]')?.focus();
    const onDoc = (e: MouseEvent) => {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) setMoreOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMoreOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [moreOpen]);
  const [exporting, setExporting] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [overrideMode, setOverrideMode] = useState<'chart' | 'table' | null>(null);
  const [overrideKind, setOverrideKind] = useState<ChartKind | null>(null);
  const [overrideMetric, setOverrideMetric] = useState<string | null>(null);
  const lastKeyRef = useRef<string>('');

  const visual = contract.visual;
  const isGreeting = !visual || visual.type === 'none';
  const refused = contract.access?.status === 'refused' || visual?.type === 'refusal';

  // Reset manual toolbar overrides whenever a new turn or voice/chat re-plot arrives
  useEffect(() => {
    setOverrideMode(null);
    setOverrideKind(null);
    setOverrideMetric(null);
  }, [contract.turn_id, visual?.type, visual?.chart?.kind]);

  // Extract dataset rows + numeric columns for interactive Plotly/Dash switcher
  const activeDataset = useMemo(() => {
    const rawRows: Record<string, any>[] =
      (visual?.chart?.data as Record<string, any>[]) ||
      (visual?.table?.rows as Record<string, any>[]) ||
      [];
    if (!rawRows.length) return { rows: [], columns: [], numericCols: [], dimCol: 'label' };
    const cols = visual?.table?.columns?.length ? visual.table.columns : Object.keys(rawRows[0] || {});
    const numCols = cols.filter((k) => {
      if (/^(lat|lon|lng|id|order|rank)$/i.test(k)) return false;
      let n = 0;
      for (const r of rawRows) if (toNumber(r?.[k]) !== null) n++;
      return n >= Math.max(1, Math.ceil(rawRows.length * 0.7));
    });
    const dimCol =
      visual?.chart?.category ||
      visual?.chart?.x ||
      cols.find((c) => !numCols.includes(c)) ||
      cols[0] ||
      'label';
    return { rows: rawRows, columns: cols, numericCols: numCols, dimCol };
  }, [visual]);

  const effectiveVisualType = overrideMode || visual?.type;
  const effectiveChartSpec = useMemo<ChartSpec | undefined>(() => {
    if (!activeDataset.rows.length) return visual?.chart;
    const baseSpec: ChartSpec = visual?.chart || {
      kind: 'bar',
      x: activeDataset.dimCol,
      y: activeDataset.numericCols[0] || activeDataset.columns[1] || 'value',
      category: activeDataset.dimCol,
      value: activeDataset.numericCols[0] || activeDataset.columns[1] || 'value',
      data: activeDataset.rows,
    };
    const nextKind = overrideKind || baseSpec.kind || 'bar';
    const nextMetric = overrideMetric || baseSpec.value || baseSpec.y || activeDataset.numericCols[0];
    return {
      ...baseSpec,
      kind: nextKind,
      value: nextMetric,
      y: nextMetric,
      x: baseSpec.x || activeDataset.dimCol,
      category: baseSpec.category || activeDataset.dimCol,
      data: activeDataset.rows,
    };
  }, [visual?.chart, activeDataset, overrideKind, overrideMetric]);

  const effectiveTableSpec = useMemo(() => {
    if (visual?.table && visual.table.rows?.length) return visual.table;
    if (!activeDataset.rows.length) return undefined;
    return {
      columns: activeDataset.columns,
      rows: activeDataset.rows,
    };
  }, [visual?.table, activeDataset]);

  const canSwitchVisual = !refused && activeDataset.rows.length > 0 && (visual?.type === 'chart' || visual?.type === 'table');
  const activeKindPill = effectiveVisualType === 'table' ? 'table' : effectiveChartSpec?.kind || 'bar';

  // Refine keeps the same key so the chart morphs in place; replace cross-fades.
  const visualKey = useMemo(() => {
    if (visual?.mode === 'refine' && lastKeyRef.current) return lastKeyRef.current;
    lastKeyRef.current = contract.turn_id || String(Date.now());
    return lastKeyRef.current;
  }, [contract.turn_id, visual?.mode]);

  const insights = (contract.insights || []).map(cleanText).filter((s) => s && !NOISE.test(s));
  const sources = (contract.sources || []).filter((s, i, arr) => arr.findIndex((x) => sourceLabel(x) === sourceLabel(s)) === i);
  const exportOptions = (contract.export_options || []).filter((o) => EXPORT_LABELS[o]);
  const summaryBanner = cleanText(contract.display_text || contract.spoken_summary || '');

  const spark = useMemo(() => {
    if (visual?.type !== 'chart' || !visual.chart) return undefined;
    const plan = planChart(visual.chart);
    if (plan.rows.length < 3 || plan.form === 'bullet' || plan.form === 'waterfall') return undefined;
    const vals = plan.rows.map((r) => r.value);
    return { values: vals, kind: plan.timeLike ? ('line' as const) : ('bars' as const), highlight: vals.indexOf(Math.max(...vals)) };
  }, [visual]);

  const handleExport = async (format: string) => {
    setExportOpen(false);
    setExporting(format);
    const title = (visual?.title || 'Yukti_Export').replace(/[^a-zA-Z0-9_-]+/g, '_').slice(0, 60);
    const table = visual?.table;
    const chartRows = visual?.chart?.data || [];
    const columns = table?.columns || (chartRows[0] ? Object.keys(chartRows[0]) : []);
    const rows = (table?.rows as any[]) || chartRows;
    const content = visual?.document?.markdown || visual?.clause?.text || cleanText(contract.display_text);
    try {
      const res = await fetch('/api/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ format, title, content, columns, rows }),
      });
      const j = await res.json();
      if (!res.ok) throw new Error(j?.message || `HTTP ${res.status}`);
      if (j.url && /docs|sheets/.test(format)) {
        setToast(`Created in ${EXPORT_LABELS[format]}. ${j.url.includes('yukti-') ? 'Workspace sign-in is not configured here, so a local copy was saved instead.' : ''}`);
        if (!j.url.includes('yukti-')) window.open(j.url, '_blank', 'noopener');
      } else if (j.export_id) {
        const a = document.createElement('a');
        a.href = `/api/export/${encodeURIComponent(j.export_id)}`;
        a.download = j.filename || `${title}.${j.format || format}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setToast(`Downloading ${j.filename || EXPORT_LABELS[format]}`);
      }
    } catch (e: any) {
      setToast(`Export failed: ${e?.message || e}`);
    } finally {
      setExporting(null);
      setTimeout(() => setToast(null), 4500);
    }
  };

  const fixedHeight = effectiveVisualType === 'chart' || effectiveVisualType === 'map';
  const selfFramed = effectiveVisualType === 'clause' || effectiveVisualType === 'document' || effectiveVisualType === 'refusal' || effectiveVisualType === 'table';
  const kpis = (visual?.kpis || []).filter((k) => k && (toNumber(k.value) !== null || typeof k.value === 'string'));

  // Wide tables (> 7 columns) take the full width; takeaways stack below (no horizontal clipping).
  const wideTable = effectiveVisualType === 'table' && (effectiveTableSpec?.columns?.length || 0) > 7;

  const pickKind = (id: ChartKind | 'table') => {
    if (id === 'table') {
      setOverrideMode('table');
    } else {
      setOverrideMode('chart');
      setOverrideKind(id as ChartKind);
    }
  };

  // Context chips (U4.2): role · subject · period · source, derived from the contract.
  const titleText = cleanText(visual?.title || '');
  const fyMatch = (titleText + ' ' + summaryBanner).match(/\bFY\s?\d{2}(?:\d{2})?(?:-\d{2})?\b/i);
  const populationRaw = (visual?.chart?.unit || '').replace(/[₹%$]|\bcr(ore)?s?\b|\/boe\b/gi, '').trim();
  // Only meaningful populations (e.g. "Executives"); generic unit words are not context.
  const population = /^(count|value|number|n|units?|records?|rows?|score|weightage)?$/i.test(populationRaw) ? '' : populationRaw;
  const subject = titleText.includes(':') ? titleText.split(':')[0].trim() : '';
  const contextChips = [ROLE_SHORT[persona || contract.persona || 'CMD'] || 'CMD', subject, population, fyMatch ? fyMatch[0].toUpperCase().replace(/\s/, '') : ''].filter(
    (x, i, arr) => x && arr.indexOf(x) === i,
  );
  const firstSource = sources[0];
  const sourceTag = firstSource ? (firstSource.kind === 'policy' ? 'Policy' : firstSource.kind === 'document' ? 'Document' : 'SSOT') : undefined;

  return (
    <div className="min-h-full flex flex-col px-[2.25rem] pt-[1.25rem] pb-[9.5rem] gap-[1.15rem] max-w-[104rem] mx-auto w-full" data-testid="canvas">
      {busy && <div className="fixed left-0 right-0 top-[var(--topbar-h)] h-[2px] yk-shimmer z-20" aria-hidden />}

      {isGreeting ? (
        <Greeting
          onSelect={onSelectStarter}
          onTalk={onTalk}
          isMicActive={isMicActive}
          orbState={orbState}
          isDark={isDark}
          audioEngine={audioEngine}
          messages={messages}
          liveInterimText={liveInterimText}
          persona={persona || contract.persona}
        />
      ) : (
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={visualKey}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.32, ease: [0.2, 0.7, 0.2, 1] }}
            className="flex flex-col gap-[1.1rem]"
          >
            {/* Header (U4.2): eyebrow, title, context chips, actions; quiet lead paragraph */}
            <header className="flex flex-col gap-2.5">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className={`text-label uppercase tracking-[0.08em] ${refused ? 'text-[var(--maroon)]' : 'text-[var(--accent-deep)] dark:text-[var(--accent-soft)]'}`}>
                    {eyebrowFor(contract)}
                  </div>
                  <h1 data-testid="canvas-title" className="mt-1 font-display text-headline text-[var(--ink)] line-clamp-2">
                    {cleanText(visual?.title || 'Answer')}
                  </h1>
                  <ContextChips className="mt-2" items={contextChips} source={sourceTag} data-testid="context-chips" />
                </div>
                {exportOptions.length > 0 && !refused && (
                  <div className="relative shrink-0">
                    <button onClick={() => setExportOpen((o) => !o)} className="chip !py-2" aria-haspopup="menu" aria-expanded={exportOpen} data-testid="export-button">
                      {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4 text-[var(--accent-deep)] dark:text-[var(--accent-soft)]" />}
                      Export
                    </button>
                    {exportOpen && (
                      <div role="menu" className="absolute right-0 top-[calc(100%+0.4rem)] w-[13rem] rounded-[var(--radius-lg)] border border-[var(--hairline)] bg-[var(--card)] shadow-[var(--panel-shadow)] p-1.5 z-40">
                        {exportOptions.map((o) => (
                          <button key={o} role="menuitem" onClick={() => handleExport(o)} className="w-full text-left px-3 py-2 rounded-[var(--radius-sm)] text-label hover:bg-[var(--surface)]">
                            {EXPORT_LABELS[o]}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {summaryBanner && !refused && (
                <p className="flex items-start gap-2.5 max-w-[72rem] text-body text-[var(--ink-2)]" data-testid="answer-lead">
                  <Volume2 className="w-4 h-4 mt-[0.3rem] text-[var(--ink-3)] shrink-0" aria-hidden />
                  <span>{summaryBanner}</span>
                </p>
              )}
            </header>

            {/* KPI hero numerals */}
            {kpis.length > 0 && effectiveVisualType !== 'kpi' && !refused && <KpiRenderer kpis={kpis} isDark={isDark} spark={spark} />}

            {/* Chart switcher (U4.3): compact segmented control, top 6 + "More" */}
            {canSwitchVisual && (
              <div className="flex flex-wrap items-center justify-between gap-3" data-testid="chart-switcher-toolbar">
                <div className="flex items-center gap-2">
                  <div role="group" aria-label="Plot type" className="inline-flex items-center gap-0.5 p-0.5 rounded-pill bg-[var(--surface)] border border-[var(--hairline)]">
                    {PRIMARY_KINDS.map((opt) => {
                      const isActive = activeKindPill === opt.id;
                      return (
                        <button
                          key={opt.id}
                          type="button"
                          aria-pressed={isActive}
                          data-testid={`plot-switch-${opt.id}`}
                          onClick={() => pickKind(opt.id)}
                          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-pill text-label font-medium transition-colors duration-fast focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent)] ${
                            isActive ? 'bg-[var(--card)] text-[var(--ink)] shadow-[var(--card-shadow)]' : 'text-[var(--ink-2)] hover:text-[var(--ink)]'
                          }`}
                        >
                          <opt.icon className="w-3.5 h-3.5" />
                          {opt.label}
                        </button>
                      );
                    })}
                  </div>
                  <div className="relative" ref={moreRef}>
                    <button
                      type="button"
                      onClick={() => setMoreOpen((o) => !o)}
                      aria-haspopup="menu"
                      aria-expanded={moreOpen}
                      data-testid="plot-switch-more"
                      className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-pill text-label font-medium border border-[var(--hairline)] transition-colors ${
                        MORE_KINDS.some((k) => k.id === activeKindPill) ? 'bg-[var(--accent-pale)] text-[var(--accent-deep)] dark:text-[var(--accent-soft)]' : 'text-[var(--ink-2)] hover:bg-[var(--surface)]'
                      }`}
                    >
                      {MORE_KINDS.find((k) => k.id === activeKindPill)?.label || 'More'}
                      <ChevronRight className={`w-3.5 h-3.5 transition-transform ${moreOpen ? '-rotate-90' : 'rotate-90'}`} />
                    </button>
                    {moreOpen && (
                      <div role="menu" className="absolute left-0 top-[calc(100%+0.4rem)] w-[11rem] rounded-[var(--radius-lg)] border border-[var(--hairline)] bg-[var(--card)] shadow-[var(--panel-shadow)] p-1.5 z-40">
                        {MORE_KINDS.map((opt) => (
                          <button
                            key={opt.id}
                            role="menuitem"
                            data-testid={`plot-switch-${opt.id}`}
                            onClick={() => {
                              pickKind(opt.id);
                              setMoreOpen(false);
                            }}
                            className={`w-full text-left px-3 py-2 rounded-[var(--radius-sm)] text-label hover:bg-[var(--surface)] ${activeKindPill === opt.id ? 'font-semibold text-[var(--ink)]' : 'text-[var(--ink-2)]'}`}
                          >
                            {opt.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {activeDataset.numericCols.length > 1 && effectiveVisualType === 'chart' && (
                  <label className="flex items-center gap-2 text-label text-[var(--ink-2)]">
                    <SlidersHorizontal className="w-3.5 h-3.5" aria-hidden />
                    Metric
                    <select
                      aria-label="Select plot metric"
                      data-testid="plot-metric-select"
                      value={effectiveChartSpec?.value || activeDataset.numericCols[0]}
                      onChange={(e) => setOverrideMetric(e.target.value)}
                      className="px-2.5 py-1 rounded-[var(--radius-sm)] bg-[var(--card)] border border-[var(--hairline)] text-[var(--ink)] font-medium focus:outline-none focus:border-[var(--accent)]"
                    >
                      {activeDataset.numericCols.map((col) => (
                        <option key={col} value={col}>
                          {humanizeKey(col)}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </div>
            )}

            {/* Full-screen Visual + Key Takeaways */}
            <div className={`grid gap-[1.25rem] ${insights.length && !refused && !wideTable ? 'xl:grid-cols-[minmax(0,1fr)_minmax(18rem,23rem)]' : ''}`}>
              {/* Newest-answer aura edge (U4.7): glows briefly when a fresh answer lands, then fades */}
              <div data-aura={glow} className="yk-aura-ring rounded-card min-w-0 self-start w-full">
              <section
                className={`yk-aura-surface min-w-0 ${selfFramed ? '' : 'card p-[1.35rem]'} ${fixedHeight ? 'h-[clamp(22rem,calc(100vh-23rem),46rem)]' : ''}`}
                data-testid="visual-card"
                data-visual-type={effectiveVisualType}
              >
                {effectiveVisualType === 'chart' && effectiveChartSpec && <ChartRenderer spec={effectiveChartSpec} isDark={isDark} title={visual?.title} />}
                {effectiveVisualType === 'table' && effectiveTableSpec && <TableRenderer table={effectiveTableSpec} isDark={isDark} />}
                {effectiveVisualType === 'clause' && visual?.clause && <ClauseRenderer clause={visual.clause} isDark={isDark} />}
                {effectiveVisualType === 'document' && visual?.document && <DocumentRenderer document={visual.document} isDark={isDark} />}
                {effectiveVisualType === 'map' && visual?.map && <MapRenderer mapSpec={visual.map} isDark={isDark} />}
                {effectiveVisualType === 'refusal' && <RefusalRenderer access={contract.access} isDark={isDark} onViewAlternative={onNavigateToAlternative} />}
                {effectiveVisualType === 'kpi' && visual?.kpis && <KpiRenderer kpis={visual.kpis} isDark={isDark} hero />}
              </section>
              </div>

              {insights.length > 0 && !refused && (
                <aside className="card p-[1.25rem] self-start" data-testid="insights">
                  <div className="text-[0.82rem] font-medium text-[var(--ink-2)] mb-3">Key takeaways</div>
                  <ul className="space-y-[0.85rem]">
                    {insights.slice(0, 5).map((s, i) => (
                      <li key={i} className="flex gap-2.5 text-[0.92rem] leading-[1.55]">
                        <span className={`mt-[0.55rem] w-1.5 h-1.5 rounded-full shrink-0 ${i === 0 ? 'bg-[var(--accent)]' : 'bg-[var(--ink-3)]'}`} />
                        <span className={i === 0 ? 'font-medium' : 'text-[var(--ink)]/90'}>{s}</span>
                      </li>
                    ))}
                  </ul>
                </aside>
              )}
            </div>

            {/* Sources: collapsed, at the end; caveats only inside */}
            {sources.length > 0 && (
              <div className="pt-1" data-testid="canvas-sources">
                <button onClick={() => setSourcesOpen((o) => !o)} className="inline-flex items-center gap-1 text-[0.82rem] font-medium text-[var(--ink-2)] hover:text-[var(--ink)]" aria-expanded={sourcesOpen}>
                  <ChevronRight className={`w-4 h-4 transition-transform ${sourcesOpen ? 'rotate-90' : ''}`} />
                  Sources ({sources.length})
                </button>
                {sourcesOpen && (
                  <div className="mt-2 space-y-2.5">
                    <div className="flex flex-wrap gap-2">
                      {sources.map((s, i) => (
                        <button key={i} onClick={() => setSelectedSource(s)} className="chip !text-[0.82rem]">
                          {s.kind === 'policy' ? <Scale className="w-3.5 h-3.5 text-ongc-maroon" /> : s.kind === 'document' ? <FileText className="w-3.5 h-3.5 text-[var(--accent)]" /> : <Database className="w-3.5 h-3.5 text-[var(--accent)]" />}
                          {sourceLabel(s)}
                        </button>
                      ))}
                    </div>
                    {contract.caveat && (
                      <div className="max-w-[48rem] p-3 rounded-[0.9rem] bg-warning-pale text-warning text-[0.84rem] leading-relaxed">
                        <span className="font-semibold">Data note · </span>
                        {cleanText(contract.caveat)}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      )}

      {/* History strip */}
      {history.length > 1 && (
        <nav className="mt-auto pt-3 border-t border-[var(--hairline)] flex items-center gap-2 overflow-x-auto" aria-label="Earlier answers" data-testid="history-strip">
          <span className="text-[0.76rem] text-[var(--ink-3)] shrink-0 mr-1">Earlier</span>
          {history.map((h, i) => (
            <button
              key={h.id + i}
              onClick={() => onRestoreHistory(h, i)}
              title={h.question}
              className={`shrink-0 max-w-[15rem] truncate px-3 py-1.5 rounded-full text-[0.8rem] border transition-colors ${
                i === currentHistoryIndex ? 'bg-[var(--accent-pale)] border-transparent text-[var(--accent-deep)] dark:text-[var(--accent-soft)] font-medium' : 'border-[var(--hairline)] text-[var(--ink-2)] hover:bg-[var(--surface)]'
              }`}
            >
              {i === currentHistoryIndex && <Check className="inline w-3 h-3 mr-1 -mt-0.5" />}
              {cleanText(h.contract.visual?.title || h.question)}
            </button>
          ))}
        </nav>
      )}

      {toast && (
        <div role="status" className="fixed left-1/2 -translate-x-1/2 bottom-28 z-50 px-4 py-2.5 rounded-full bg-[var(--ink)] text-[var(--canvas)] text-[0.86rem] shadow-lg">
          {toast}
        </div>
      )}

      <SourceChipsModal source={selectedSource} onClose={() => setSelectedSource(null)} isDark={isDark} />
    </div>
  );
};
