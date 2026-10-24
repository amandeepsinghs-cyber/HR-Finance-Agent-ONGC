'use client';

/**
 * AnswerCard (U2.3): one complete Yukti answer — header (eyebrow, title, context chips, export), lead, KPIs,
 * chart switcher, visual, takeaways, follow-up chips and sources. Extracted from the single-answer CanvasView so
 * every turn in the conversation feed is a fully interactive card (tooltips, re-plot, export from any card).
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { AnswerContract, ChartKind, ChartSpec, SourceCitation } from '@/contracts/answerContract';
import { ChartRenderer } from './renderers/ChartRenderer';
import { TableRenderer } from './renderers/TableRenderer';
import { PERSONA_DIRECTORY } from '@/personas';
import { KpiRenderer } from './renderers/KpiRenderer';
import { ClauseRenderer } from './renderers/ClauseRenderer';
import { DocumentRenderer } from './renderers/DocumentRenderer';
import { MapRenderer } from './renderers/MapRenderer';
import { RefusalRenderer } from './renderers/RefusalRenderer';
import { SourceChipsModal } from './SourceChipsModal';
import { RosterTable } from './renderers/RosterTable';
import { CompareRenderer } from './renderers/CompareRenderer';
import { replot, profile, ReplotResult, ReplotKind } from '@/charts/compat';
import { normalizeRows } from '@/charts/normalize';
import type { SpecPatch, VisualContainer } from '@/contracts/answerContract';
import { sourceLabel } from './FloatingConversationPanel';
import { planChart } from '@/charts/plan';
import { cleanText, humanizeKey, toNumber } from '@/charts/format';
import { Card, Chip, ContextChips } from './ui/primitives';
import { Download, ChevronRight, Database, Scale, FileText, Loader2, Volume2, BarChart3, PieChart, Activity, Table as TableIcon, SlidersHorizontal, Sparkles, CornerDownRight } from 'lucide-react';

const NOISE = /^(executed sql|grounding:|query:|sql query|voice turn completed|yukti ai connected|role:|served from|canvas visual|turn complete)/i;

const EXPORT_LABELS: Record<string, string> = {
  sheets: 'Google Sheets',
  docs: 'Google Docs',
  word: 'Word (.docx)',
  pdf: 'PDF',
  xlsx: 'Excel (.xlsx)',
};

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
  { id: 'funnel', label: 'Funnel' },
  { id: 'grouped_bar', label: 'Grouped bar' },
  { id: 'stacked_bar', label: 'Stacked bar' },
  { id: 'bullet', label: 'Bullet (vs target)' },
];
const ROLE_SHORT: Record<string, string> = Object.fromEntries(PERSONA_DIRECTORY.map((p) => [p.id, p.short]));

function eyebrowFor(c: AnswerContract): string {
  const v = c.visual;
  if (c.access?.status === 'refused' || v?.type === 'refusal') return 'Access restricted';
  const m = (c as any).query_spec?.metric;
  if (m && ['pnl_statement', 'balance_sheet', 'cash_flow_statement', 'financial_ratios'].includes(m)) {
    return 'Financial Statement';
  }
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

/** djb2 hash of the plotted rows (test hook: toolbar vs voice/typed re-plot equality) */
function sigOf(data: unknown): number {
  const str = JSON.stringify(data || []);
  let h = 5381;
  for (let i = 0; i < str.length; i++) h = ((h << 5) + h + str.charCodeAt(i)) | 0;
  return h >>> 0;
}

export interface AnswerCardProps {
  contract: AnswerContract;
  isDark?: boolean;
  persona?: string;
  /** arrived live in this view: plays the newest-answer glow once */
  fresh?: boolean;
  /** latest card in the feed: shows follow-up chips */
  isLatest?: boolean;
  onNavigateToAlternative?: () => void;
  /** toolbar re-plot: written into this turn's contract so toolbar, voice and typed commands share one state */
  onReplot?: (visual: VisualContainer) => void;
  /** ask a follow-up question (drill-down / suggestion chips); drill-downs carry a spec_patch (U5.4) */
  onAsk?: (q: string, specPatch?: SpecPatch) => void;
}

/** Spoken-only / conversational answer (no visual): a quiet text card. */
const TextAnswer: React.FC<{ contract: AnswerContract; followUps?: { label: string; q: string; patch?: SpecPatch }[]; onAsk?: (q: string, patch?: SpecPatch) => void }> = ({ contract, followUps = [], onAsk }) => {
  const text = cleanText(contract.display_text || contract.spoken_summary || '');
  return (
    <article className="flex flex-col gap-3" data-testid="answer-card" data-visual-type="none">
      <div className="py-[0.5rem] max-w-[72rem] flex items-start gap-3">
        <Sparkles className="w-4 h-4 mt-[0.3rem] shrink-0 text-[var(--accent-deep)] dark:text-[var(--accent-soft)]" aria-hidden />
        <p className="text-body text-[var(--ink)] leading-relaxed">{text || '…'}</p>
      </div>
      {onAsk && followUps.length > 0 && (
        <nav aria-label="Follow-up questions" className="mt-auto pt-2 flex flex-wrap items-center gap-x-5 gap-y-1.5" data-testid="follow-ups">
          {followUps.map((f) => (
            <button
              key={f.label}
              type="button"
              onClick={() => onAsk(f.q, (f as { patch?: SpecPatch }).patch)}
              className="inline-flex items-center gap-1.5 py-0.5 text-caption font-normal text-[var(--ink-3)] hover:text-[var(--ink-2)] transition-colors"
              data-testid="follow-up-chip"
            >
              <CornerDownRight className="w-3 h-3 text-[var(--ink-3)]" aria-hidden />
              {cleanText(f.label)}
            </button>
          ))}
        </nav>
      )}
    </article>
  );
};

export const AnswerCard: React.FC<AnswerCardProps> = ({ contract, isDark = false, persona, isLatest = false, onNavigateToAlternative, onAsk, onReplot }) => {
  const [selectedSource, setSelectedSource] = useState<SourceCitation | null>(null);
  const [exportOpen, setExportOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  useEffect(() => {
    setMoreOpen(false);
  }, [contract.turn_id]);

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
  const toastTimer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(toastTimer.current), []);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  // Toolbar re-plots go through the same engine as voice/typed commands (U5.7/U5.8): identical output.
  const [override, setOverride] = useState<ReplotResult | null>(null);
  const [metric, setMetric] = useState<string | null>(null);
  const lastKeyRef = useRef<string>('');

  const visual = contract.visual;
  const isGreeting = !visual || visual.type === 'none';
  const refused = contract.access?.status === 'refused' || visual?.type === 'refusal';

  // Reset manual toolbar overrides whenever a new turn or voice/chat re-plot arrives
  useEffect(() => {
    setOverride(null);
    setMetric(null);
  }, [contract.turn_id, visual?.type, visual?.chart?.kind]);

  // Data profile of the answer (original rows, preserved across re-plots in visual.source)
  const prof = useMemo(() => profile(visual), [visual]);
  const effVisual = override?.visual || visual;
  const effectiveVisualType = effVisual?.type;
  const effectiveChartSpec = effVisual?.chart;
  const effectiveTableSpec = useMemo(() => {
    const t = effVisual?.table;
    if (!t?.rows?.length) return t && t.columns ? t : prof.rows.length ? { columns: prof.columns, rows: prof.rows } : undefined;
    return { ...t, rows: normalizeRows(t.columns, t.rows as unknown[]) };
  }, [effVisual, prof]);
  const replotNote = override?.note || visual?.replot_note;

  const canSwitchVisual = !refused && prof.rows.length > 0 && (visual?.type === 'chart' || visual?.type === 'table');
  const activeKindPill: ReplotKind = effectiveVisualType === 'table' ? 'table' : (effectiveChartSpec?.kind as ReplotKind) || 'bar';
  const measures = prof.measures;

  // Named-people tables get the roster component (sort / filter / search / select / actions / masking).
  const t0 = effectiveTableSpec;
  const isRoster =
    effectiveVisualType === 'table' &&
    !!t0 &&
    (!!t0.masking || !!t0.row_actions?.length || (t0.columns || []).some((c) => /^(emp_name|employee_name|emp_id|employee_id)$/i.test(c)));

  // Refine keeps the same key so the chart morphs in place; replace cross-fades.
  const visualKey = useMemo(() => {
    if (visual?.mode === 'refine' && lastKeyRef.current) return lastKeyRef.current;
    lastKeyRef.current = contract.turn_id || String(Date.now());
    return lastKeyRef.current;
  }, [contract.turn_id, visual?.mode]);

  const insightItems: { text: string; kind?: string }[] = (contract.insights_v2?.length
    ? contract.insights_v2.map((i) => ({ text: cleanText(i.text), kind: i.kind }))
    : (contract.insights || []).map((t) => ({ text: cleanText(t) }))
  ).filter((x) => x.text && !NOISE.test(x.text));
  const insights = insightItems.map((x) => x.text);
  const sources = (contract.sources || []).filter((s, i, arr) => arr.findIndex((x) => sourceLabel(x) === sourceLabel(s)) === i);
  // U2.3: every answer card offers Sheets, Docs, Word and PDF (plus anything else the backend lists) — unless the
  // backend deliberately sent an empty list (e.g. restricted content).
  const exportOptions =
    contract.export_options && contract.export_options.length === 0
      ? []
      : Array.from(new Set([...(contract.export_options || []), 'sheets', 'docs', 'word', 'pdf'])).filter((o) => EXPORT_LABELS[o]);
  const summaryBanner = cleanText(contract.display_text || contract.spoken_summary || '');

  const spark = useMemo(() => {
    if (visual?.type !== 'chart' || !visual.chart) return undefined;
    const plan = planChart(visual.chart);
    if (plan.rows.length < 3 || plan.form === 'bullet' || plan.form === 'waterfall') return undefined;
    const vals = plan.rows.map((r) => r.value);
    return { values: vals, kind: plan.timeLike ? ('line' as const) : ('bars' as const), highlight: vals.indexOf(Math.max(...vals)) };
  }, [visual]);

  const handleExport = async (format: string, pick?: { columns: string[]; rows: Record<string, any>[] }) => {
    setExportOpen(false);
    setExporting(format);
    const title = (visual?.title || 'Yukti_Export').replace(/[^a-zA-Z0-9_-]+/g, '_').slice(0, 60);
    // U5.5: export the answer's own rows, normalised (array rows → objects); roster exports pass the selection.
    const columns = pick?.columns || prof.columns;
    const rows = pick?.rows || prof.rows;
    const content = visual?.document?.markdown || visual?.clause?.text || cleanText(contract.display_text);
    try {
      const res = await fetch('/api/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ format, title, content, columns, rows }),
      });
      const j = await res.json();
      if (!res.ok) throw new Error(j?.message || `HTTP ${res.status}`);
      const placeholder = !!j.url && String(j.url).includes('yukti-');
      if (j.url && /docs|sheets/.test(format) && !placeholder) {
        setToast(`Created in ${EXPORT_LABELS[format]}.`);
        window.open(j.url, '_blank', 'noopener');
      } else if (j.export_id) {
        // Workspace sign-in is not configured here: download the local copy (.docx / .xlsx) instead.
        const a = document.createElement('a');
        a.href = `/api/export/${encodeURIComponent(j.export_id)}`;
        a.download = j.filename || `${title}.${j.format || format}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setToast(placeholder ? `Google Workspace isn't connected here, so I downloaded ${j.filename || 'a local copy'} instead.` : `Downloading ${j.filename || EXPORT_LABELS[format]}`);
      }
    } catch (e: any) {
      setToast(`Export failed: ${e?.message || e}`);
    } finally {
      setExporting(null);
      if (toastTimer.current) window.clearTimeout(toastTimer.current);
      toastTimer.current = window.setTimeout(() => setToast(null), 4500);
    }
  };

  const fixedHeight = ((effectiveVisualType === 'chart' && !effVisual?.compare?.items?.length) || effectiveVisualType === 'map');
  const selfFramed = effectiveVisualType === 'clause' || effectiveVisualType === 'document' || effectiveVisualType === 'refusal' || effectiveVisualType === 'table';
  const kpis = (visual?.kpis || []).filter((k) => k && (toNumber(k.value) !== null || typeof k.value === 'string'));

  // Wide tables (> 7 columns) take the full width; takeaways stack below (no horizontal clipping).
  const wideTable = effectiveVisualType === 'table' && (effectiveTableSpec?.columns?.length || 0) > 7;

  const applyReplot = (r: ReplotResult) => {
    if (onReplot) onReplot({ ...r.visual, replot_note: r.note } as VisualContainer);
    else setOverride(r);
  };
  const pickKind = (id: ReplotKind) => applyReplot(replot(effVisual, id, { metric: metric || undefined }));
  const pickMetric = (m: string) => {
    setMetric(m);
    applyReplot(replot(effVisual, activeKindPill, { metric: m }));
  };

  // Context chips (U4.2): role · subject · period · source, derived from the contract.
  const titleText = cleanText(visual?.title || '');
  const fyMatch = (titleText + ' ' + summaryBanner).match(/\bFY\s?\d{2}(?:\d{2})?(?:-\d{2})?\b/i);
  const populationRaw = (visual?.chart?.unit || '').replace(/[₹%$]|\bcr(ore)?s?\b|\/boe\b/gi, '').trim();
  // Only meaningful populations (e.g. "Executives"); generic unit words are not context.
  const population = /^(count|value|number|n|units?|records?|rows?|score|weightage)?$/i.test(populationRaw) ? '' : populationRaw;
  const subject = titleText.includes(':') ? titleText.split(':')[0].trim() : '';
  // v2 contracts carry explicit context chips; v1 answers derive them from the title / unit / period.
  const contextChips = (contract.context_chips?.length
    ? contract.context_chips.filter((c) => c.kind !== 'source').map((c) => c.label)
    : [ROLE_SHORT[persona || contract.persona || 'CMD'] || 'CMD', subject, population, fyMatch ? fyMatch[0].toUpperCase().replace(/\s/, '') : '']
  ).filter((x, i, arr) => x && arr.indexOf(x) === i);
  const firstSource = sources[0];
  // P0.3 (BUG-04, SPEC-11 §7.2): answers served from the local JSON snapshot carry an explicit badge.
  const localSnapshot = contract.provenance?.label === 'local_snapshot' || contract.status?.source === 'local_snapshot';
  const sourceTag = localSnapshot
    ? `Local snapshot${contract.provenance?.snapshot_date ? ` ${contract.provenance.snapshot_date}` : ''}`
    : firstSource ? (firstSource.kind === 'policy' ? 'Policy' : firstSource.kind === 'document' ? 'Document' : 'SSOT') : undefined;

  // Follow-up chips (U2.3 / U5.4): drill-downs first, else the agent's suggestions; latest card only.
  const followUps: { label: string; q: string; patch?: SpecPatch }[] = (contract.drilldowns?.length
    ? contract.drilldowns.map((d) => ({ label: d.label, q: d.question || d.label, patch: d.spec_patch }))
    : (contract.suggestions || []).map((s) => ({ label: s, q: s }))
  ).slice(0, 4);

  if (isGreeting) return <TextAnswer contract={contract} followUps={isLatest && onAsk ? followUps : []} onAsk={onAsk} />;

  return (
    <article className="flex flex-col gap-[1.1rem]" data-testid="answer-card" data-visual-type={effectiveVisualType}>
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
                <h2 data-testid="canvas-title" className="mt-1 font-display text-headline text-[var(--ink)] line-clamp-2">
                  {cleanText(visual?.title || 'Answer')}
                </h2>
                <ContextChips className="mt-2" items={contextChips} source={sourceTag} data-testid="context-chips" />
              </div>
              {exportOptions.length > 0 && !refused && (
                <div className="relative shrink-0">
                  <Chip onClick={() => setExportOpen((o) => !o)} className="!py-2" aria-haspopup="menu" aria-expanded={exportOpen} data-testid="export-button">
                    {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4 text-[var(--accent-deep)] dark:text-[var(--accent-soft)]" />}
                    Export
                  </Chip>
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

          {/* Full-screen Visual + Key Takeaways (borderless canvas, no outer boxes, no plot-type bar) */}
          <div className={`grid gap-[1.75rem] ${insights.length && !refused && !wideTable ? 'xl:grid-cols-[minmax(0,1fr)_minmax(18rem,23rem)]' : ''}`}>
            <section
              className={`min-w-0 self-start w-full ${selfFramed ? '' : 'py-[0.35rem]'} ${fixedHeight ? 'h-[clamp(22rem,calc(100vh-23rem),46rem)]' : ''}`}
              data-testid="visual-card"
              data-visual-type={effectiveVisualType}
              data-chart-kind={effectiveVisualType === 'chart' ? effectiveChartSpec?.kind : effectiveVisualType}
              data-points={effectiveVisualType === 'chart' ? effectiveChartSpec?.data?.length : effectiveTableSpec?.rows?.length}
              data-sig={effectiveVisualType === 'chart' ? sigOf(effectiveChartSpec?.data) : 0}
            >
              {effectiveVisualType === 'chart' && effVisual?.compare?.items?.length ? (
                <CompareRenderer compare={effVisual.compare} isDark={isDark} unit={effVisual.chart?.unit} />
              ) : (
                effectiveVisualType === 'chart' && effectiveChartSpec && <ChartRenderer spec={effectiveChartSpec} isDark={isDark} title={visual?.title} />
              )}
              {effectiveVisualType === 'table' && effectiveTableSpec && isRoster && (
                <RosterTable
                  table={effectiveTableSpec}
                  persona={persona || contract.persona}
                  onRowAction={(actionId, rows) => {
                    const act = effectiveTableSpec.row_actions?.find((a) => a.id === actionId);
                    const clean = (v: unknown) => (v === undefined || v === null || String(v).includes('•') ? '' : String(v));
                    const names = rows.map((r) => [clean(r.emp_name || r.name), clean(r.emp_id) ? `(${clean(r.emp_id)})` : ''].filter(Boolean).join(' ')).slice(0, 25);
                    const who = names.join(', ') + (rows.length > 25 ? ` and ${rows.length - 25} more` : '');
                    const q = act?.question_template && rows.length === 1
                      ? act.question_template.replace(/\{(\w+)\}/g, (_, k) => clean(rows[0][k]))
                      : `${act?.label || 'Draft a transfer note'} for ${rows.length} ${rows.length === 1 ? 'officer' : 'officers'}: ${who}`;
                    // the FULL selection travels as a filter on the roster's query (never truncated)
                    const ids = rows.map((r) => clean(r.emp_id)).filter(Boolean);
                    const nm = rows.map((r) => clean(r.emp_name || r.name)).filter(Boolean);
                    onAsk?.(
                      q,
                      ids.length === rows.length
                        ? { add_filters: [{ field: 'emp_id', op: 'in', value: ids }] }
                        : nm.length
                          ? { add_filters: [{ field: 'emp_name', op: 'in', value: nm }] } // ids masked for this role
                          : undefined,
                    );
                  }}
                  onExport={(columns, rows) => void handleExport('xlsx', { columns, rows })}
                />
              )}
              {effectiveVisualType === 'table' && effectiveTableSpec && !isRoster && <TableRenderer table={effectiveTableSpec} isDark={isDark} />}
              {effectiveVisualType === 'clause' && visual?.clause && <ClauseRenderer clause={visual.clause} isDark={isDark} />}
              {effectiveVisualType === 'document' && visual?.document && <DocumentRenderer document={visual.document} isDark={isDark} />}
              {effectiveVisualType === 'map' && visual?.map && <MapRenderer mapSpec={visual.map} isDark={isDark} />}
              {effectiveVisualType === 'refusal' && <RefusalRenderer access={contract.access} isDark={isDark} onAsk={onAsk ? (q) => onAsk(q) : undefined} onViewAlternative={onNavigateToAlternative} />}
              {effectiveVisualType === 'kpi' && visual?.kpis && <KpiRenderer kpis={visual.kpis} isDark={isDark} hero />}
            </section>

            {insights.length > 0 && !refused && (
              <aside className="pl-[1.25rem] border-l border-[var(--hairline)] self-start" data-testid="insights">
                <div className="text-label text-[var(--ink-2)] mb-3">Key takeaways</div>
                <ul className="space-y-[0.85rem]">
                  {insightItems.slice(0, 5).map((it, i) => (
                    <li key={i} className="flex gap-2.5 text-[0.92rem] leading-[1.55]" data-testid="insight" data-kind={it.kind || ''}>
                      <span
                        className={`mt-[0.55rem] w-1.5 h-1.5 rounded-full shrink-0 ${
                          it.kind === 'risk' ? 'bg-[var(--maroon)]' : i === 0 || it.kind === 'headline' ? 'bg-[var(--accent)]' : 'bg-[var(--ink-3)]'
                        }`}
                      />
                      <span className={i === 0 ? 'font-medium' : 'text-[var(--ink)]/90'}>
                        {it.kind && it.kind !== 'headline' && it.kind !== 'note' && (
                          <span className={`mr-1.5 text-label font-medium capitalize ${it.kind === 'risk' ? 'text-[var(--maroon)]' : 'text-[var(--accent-deep)] dark:text-[var(--accent-soft)]'}`}>{it.kind} · </span>
                        )}
                        {it.text}
                      </span>
                    </li>
                  ))}
                </ul>
              </aside>
            )}
          </div>

          {/* Sources: collapsed, at the end; caveats only inside */}
          {sources.length > 0 && (
            <div className="pt-1" data-testid="canvas-sources">
              <button onClick={() => setSourcesOpen((o) => !o)} className="inline-flex items-center gap-1 text-label text-[var(--ink-2)] hover:text-[var(--ink)]" aria-expanded={sourcesOpen}>
                <ChevronRight className={`w-4 h-4 transition-transform ${sourcesOpen ? 'rotate-90' : ''}`} />
                Sources ({sources.length})
              </button>
              {sourcesOpen && (
                <div className="mt-2 space-y-2.5">
                  <div className="flex flex-wrap gap-2">
                    {sources.map((s, i) => (
                      <Chip key={i} onClick={() => setSelectedSource(s)} className="!text-label">
                        {s.kind === 'policy' ? <Scale className="w-3.5 h-3.5 text-ongc-maroon" /> : s.kind === 'document' ? <FileText className="w-3.5 h-3.5 text-[var(--accent)]" /> : <Database className="w-3.5 h-3.5 text-[var(--accent)]" />}
                        {sourceLabel(s)}
                      </Chip>
                    ))}
                  </div>
                  {contract.caveat && (
                    <div className="max-w-[48rem] p-3 rounded-[0.9rem] bg-warning-pale text-warning text-label font-normal leading-relaxed">
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

      {isLatest && onAsk && followUps.length > 0 && !refused && (
        <nav aria-label="Follow-up questions" className="mt-auto pt-2 flex flex-wrap items-center gap-x-5 gap-y-1.5" data-testid="follow-ups">
          {followUps.map((f) => (
            <button
              key={f.label}
              type="button"
              onClick={() => onAsk(f.q, (f as { patch?: SpecPatch }).patch)}
              className="inline-flex items-center gap-1.5 py-0.5 text-caption font-normal text-[var(--ink-3)] hover:text-[var(--ink-2)] transition-colors"
              data-testid="follow-up-chip"
            >
              <CornerDownRight className="w-3 h-3 text-[var(--ink-3)]" aria-hidden />
              {cleanText(f.label)}
            </button>
          ))}
        </nav>
      )}

      {toast && (
        <div role="status" className="fixed left-1/2 -translate-x-1/2 bottom-28 z-50 px-4 py-2.5 rounded-full bg-[var(--ink)] text-[var(--canvas)] text-label shadow-lg">
          {toast}
        </div>
      )}

      <SourceChipsModal source={selectedSource} onClose={() => setSelectedSource(null)} isDark={isDark} />
    </article>
  );
};

export default AnswerCard;
