/**
 * Shared UI-command vocabulary + client-side event bus + instant command parser for Yukti AI.
 *
 * Ported directly from Urvi AI Agent (`wellpulse/frontend/src/agent/uiCommands.ts`)
 * and tailored to ONGC's HR & Finance Command Center ("Yukti AI").
 *
 * Dual-layer voice/text platform control:
 *   Layer A — `parseUiCommands(text)`: Instant 0ms browser-side execution for plain
 *             screen commands ("dark mode", "show as a table", "full screen", "go home",
 *             "go back", "export to pdf", "switch to Hindi").
 *   Layer B — Server-side `ui_control(action, value)` voice/text tool emitted over
 *             `/ws/live` (`type: "action", kind: "ui_control"` or `type: "ui_action"`).
 */

import { useEffect } from 'react';
import exportIntentSpec from '../../../contracts/intents/export_intent.json';
import { resolveKind } from '@/charts/kindPrecedence';
import { resolveExportIntent } from './exportIntent';

export const UI_ACTIONS = {
  theme: ['light', 'dark'] as const,
  chart_kind: [
    'table', 'bar', 'hbar', 'stacked_bar', 'grouped_bar', 'pie', 'donut',
    'histogram', 'line', 'area', 'combo', 'scatter', 'waterfall',
    'treemap', 'heatmap', 'bullet', 'gauge', 'funnel', 'kpi', 'map',
  ] as const,
  open_screen: [
    'home',
    'delhi_tenure',
    'field_profitability',
    'mou_scorecard',
    'lifting_cost',
    'ne_vacancies',
    'brent_what_if',
    'recruitment_freeze',
    'jrtp_policy',
    'board_note',
  ] as const,
  focus_location: [
    'Delhi',
    'Mumbai',
    'Dehradun',
    'Ahmedabad',
    'Mehsana',
    'Ankleshwar',
    'Cambay',
    'Assam',
    'Jorhat',
    'Tripura',
    'Rajahmundry',
    'Cauvery',
    'ALL',
  ] as const,
  grade_filter: ['ALL', 'E5_PLUS', 'E7_PLUS'] as const,
  breakdown: ['grade', 'discipline'] as const,
  persona: ['CMD', 'DIR_HR', 'DIR_FIN', 'E1_HR', 'E2_HR', 'E3_HR', 'E4_HR', 'E1_FIN', 'E2_FIN', 'E3_FIN', 'E4_FIN'] as const,
  language: ['en', 'hi', 'hi-en'] as const,
  panel: ['expand', 'dock', 'minimise', 'close', 'open_history'] as const,
  // P4.7 (SPEC-10 §4.8): all formats; 'auto' = pick by the visual on screen. A ':default' suffix (e.g.
  // 'png:default') means no format word was given, so the card states which default it used.
  export: ['xlsx', 'csv', 'pdf', 'png', 'svg', 'docx', 'eml', 'sheets', 'docs', 'auto'] as const,
  history: ['back', 'forward'] as const,
} as const;

export type UiAction = keyof typeof UI_ACTIONS;
export type UiCommand = {
  [K in UiAction]: {
    action: K;
    value: (typeof UI_ACTIONS)[K][number] | string;
    columns?: string[];
  };
}[UiAction];

const EVENT = 'yukti:ui';

export function dispatchUi(cmd: UiCommand): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent<UiCommand>(EVENT, { detail: cmd }));
}

export function useUiCommands(
  handlers: Partial<{ [K in UiAction]: (value: (typeof UI_ACTIONS)[K][number] | string) => void }>,
  deps: readonly unknown[] = [],
): void {
  useEffect(() => {
    const onEvent = (e: Event) => {
      const cmd = (e as CustomEvent<UiCommand>).detail;
      if (!cmd) return;
      const fn = handlers[cmd.action] as ((v: string) => void) | undefined;
      fn?.(cmd.value);
    };
    window.addEventListener(EVENT, onEvent);
    return () => window.removeEventListener(EVENT, onEvent);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}

/** Human-readable label shown in the conversation thread when a UI command executes. */
export function labelOf(cmd: UiCommand): string {
  switch (cmd.action) {
    case 'theme':
      return `Theme → ${cmd.value} mode`;
    case 'chart_kind':
      return `View → ${cmd.value.toUpperCase()}`;
    case 'open_screen':
      return cmd.value === 'home' ? 'Returned to Home Orb' : `Screen → ${cmd.value.replace(/_/g, ' ')}`;
    case 'focus_location':
      return cmd.value === 'ALL' ? 'Cleared location filter' : `Location → ${cmd.value}`;
    case 'grade_filter':
      return `Grade filter → ${cmd.value.replace('_PLUS', '+')}`;
    case 'breakdown':
      return `Breakdown → by ${cmd.value}`;
    case 'persona':
      return `Role → ${cmd.value}`;
    case 'language':
      return `Language → ${cmd.value.toUpperCase()}`;
    case 'panel':
      return cmd.value === 'expand'
        ? 'Full-screen conversation'
        : cmd.value === 'dock'
        ? 'Docked conversation bar'
        : cmd.value === 'minimise'
        ? 'Minimised conversation'
        : `Panel → ${cmd.value}`;
    case 'export': {
      const f = String(cmd.value).split(':')[0];
      return f === 'auto' ? 'Export' : `Export → ${f.toUpperCase()}`;
    }
    case 'history':
      return cmd.value === 'back' ? 'History → Previous visual' : 'History → Next visual';
  }
}

/** True for greetings / small talk so background actions never clobber the user's screen. */
export function isSmallTalk(text: string): boolean {
  const s = (text || '')
    .toLowerCase()
    .replace(/[?!.,;:()"'[\]{}]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  if (!s) return true;
  if (
    /\b(delhi|mumbai|dehradun|assam|mehsana|ankleshwar|cambay|jorhat|tripura|cauvery|rajahmundry|champang|executive|tenure|grade|discipline|profit|loss|mou|target|brent|lifting|vacancy|vacancies|policy|jrtp|leave|board|salary|payroll|csr|capex|retire|superannuat|table|chart|bar|donut|dark|light|export|pdf|excel)\b/.test(
      s,
    )
  ) {
    return false;
  }
  const tokens = s.split(' ');
  const greet = new Set([
    'hi',
    'hello',
    'hey',
    'namaste',
    'namaskar',
    'yukti',
    'good',
    'morning',
    'afternoon',
    'evening',
    'thanks',
    'thank',
    'you',
    'ok',
    'okay',
    'bye',
    'haan',
    'ji',
    'नमस्ते',
    'युक्ति',
    'धन्यवाद',
  ]);
  if (tokens.length <= 5 && tokens.every((t) => greet.has(t))) return true;
  if (/^(how are you|who are you|what can you do|thank you|thanks a lot|kya haal hai|kaise ho)\b/.test(s)) return true;
  return false;
}

const EXPORT_PATTERNS: RegExp[] = ((exportIntentSpec as { patterns?: string[] }).patterns || []).map(
  (p) => new RegExp(p, 'i'),
);
const EXPORT_NEG_PATTERNS: RegExp[] = (
  (exportIntentSpec as { negative_guard_patterns?: string[] }).negative_guard_patterns || []
).map((p) => new RegExp(p, 'i'));
const EXPORT_POS_SET = new Set(
  ((exportIntentSpec as { positive_utterances?: string[] }).positive_utterances || []).map((u) =>
    u.toLowerCase().replace(/[?.!]+$/g, '').trim(),
  ),
);
const EXPORT_COL_SYNONYMS: Record<string, string[]> =
  (exportIntentSpec as { column_synonyms?: Record<string, string[]> }).column_synonyms || {};

const FILE_FORMAT_RE =
  /\b(excel|xlsx|xls|spreadsheet|sheets?|workbook|csv|pdf|word|docx|doc|png|svg)\b|(एक्सेल|स्प्रेडशीट|शीट|पीडीएफ|वर्ड|सीएसवी)/i;

function escapeRegExp(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Shared SPEC-07 §4.4 export intent detector (loads `yukti/contracts/intents/export_intent.json`).
 * Returns `{ action: 'export', value, columns }` when `raw` is an export command, or `null` otherwise.
 */
export function detectExportIntent(
  raw: string,
): { action: 'export'; value: 'pdf' | 'xlsx' | 'docx' | 'sheets' | 'docs'; columns: string[] } | null {
  const q = (raw || '')
    .trim()
    .toLowerCase()
    .replace(/[?.!]+$/g, '')
    .trim();
  if (!q) return null;

  const hasFileFormat = FILE_FORMAT_RE.test(q);
  if (!hasFileFormat) return null;

  const isNeg = EXPORT_NEG_PATTERNS.some((re) => re.test(q)) && !hasFileFormat;
  if (isNeg) return null;

  const matchedPattern = EXPORT_PATTERNS.some((re) => re.test(q)) || EXPORT_POS_SET.has(q);
  if (!matchedPattern) return null;

  const matchedWithPos: Array<{ pos: number; canonical: string }> = [];
  for (const [canonical, synonyms] of Object.entries(EXPORT_COL_SYNONYMS)) {
    let bestPos: number | null = null;
    const sortedSyns = [...synonyms].sort((a, b) => b.length - a.length);
    for (const syn of sortedSyns) {
      const re = new RegExp(`(?<!\\w)${escapeRegExp(syn.toLowerCase())}(?!\\w)`, 'i');
      const m = re.exec(q);
      if (m && (bestPos === null || m.index < bestPos)) {
        bestPos = m.index;
      }
    }
    if (bestPos !== null) {
      matchedWithPos.push({ pos: bestPos, canonical });
    }
  }
  matchedWithPos.sort((a, b) => a.pos - b.pos);
  const columns = matchedWithPos.map((x) => x.canonical);

  let value: 'pdf' | 'xlsx' | 'docx' | 'sheets' | 'docs' = 'xlsx';
  if (/\bpdf\b|पीडीएफ/i.test(q)) value = 'pdf';
  else if (/\b(docx|word)\b|वर्ड/i.test(q)) value = 'docx';

  return { action: 'export', value, columns };
}

const QUESTION_WORDS =
  /\b(why|how\s+many|how\s+much|what\s+is|what\s+are|who\s+is|when\s+did|explain|calculate|compare|predict|forecast|simulate|kitne|kya\s+hai|kyun)\b/i;
const COMMAND_START =
  /^(switch|change|set|turn|enable|disable|use|go|open|close|hide|show|view|display|dock|minimise|minimize|expand|maximize|full\s*screen|dark|light|table|bar|donut|pie|line|export|download|back|previous|home|clear|reset|act\s+as|speak\s+in)\b/i;

function matchClause(raw: string): UiCommand | null {
  const s = raw
    .trim()
    .toLowerCase()
    .replace(/[?.!,]+$/g, '')
    .trim();
  if (!s) return null;
  if (QUESTION_WORDS.test(s) && !COMMAND_START.test(s)) return null;

  // Theme
  if (/\b(dark\s*(mode|theme)?|night\s*mode|डार्क\s*मोड)\b/.test(s) && !/\blight\b/.test(s)) {
    return { action: 'theme', value: 'dark' };
  }
  if (/\b(light\s*(mode|theme)?|day\s*mode|white\s*mode|लाइट\s*मोड)\b/.test(s)) {
    return { action: 'theme', value: 'light' };
  }

  // Home / History
  if (
    /^(go\s+home|home|home\s+screen|clear\s+screen|reset\s+screen|show\s+orb|back\s+to\s+home|back\s+to\s+orb|होम\s*स्क्रीन)$/.test(
      s,
    )
  ) {
    return { action: 'open_screen', value: 'home' };
  }
  if (/^(go\s+back|back|previous\s+(chart|visual|screen|view)|पीछे\s*जाओ)$/.test(s)) {
    return { action: 'history', value: 'back' };
  }
  if (/^(go\s+forward|forward|next\s+(chart|visual|screen|view))$/.test(s)) {
    return { action: 'history', value: 'forward' };
  }

  // Panel mode
  if (/\b(full\s*screen|fullscreen|expand\s+(chat|panel)|maximize\s+(chat|panel)|फुल\s*स्क्रीन)\b/.test(s)) {
    return { action: 'panel', value: 'expand' };
  }
  if (/\b(exit\s+full\s*screen|normal\s+(size|view)|dock\s+(panel|chat)|restore\s+(panel|chat))\b/.test(s)) {
    return { action: 'panel', value: 'dock' };
  }
  if (/\b(minimise|minimize|hide\s+(chat|panel)|close\s+(chat|panel)|collapse\s+(chat|panel))\b/.test(s)) {
    return { action: 'panel', value: 'minimise' };
  }

  // P2H.4 + P4.7 (SPEC-07 §4.4, SPEC-10 §4.8): export intents, all formats, EN + HI. Checked before re-plot so
  // "export the table to excel" is an export, not a table view.
  {
    const exp = detectExportIntent(s);
    if (exp && exp.columns.length > 0) {
      return { action: 'export', value: exp.value, columns: exp.columns };
    }
    const ex = resolveExportIntent(s);
    if (ex) {
      const value = ex.defaulted ? (ex.target ? `${ex.format}:default` : 'auto') : ex.format;
      return { action: 'export', value };
    }
    if (exp) {
      return { action: 'export', value: exp.value };
    }
  }

  // Visual / Chart Kind morphing (ONLY when pure re-plot of current data, anchored ^...$)
  if (/^(show|view|plot|display|switch|make)\s+(this\s+|it\s+|current\s+)?(as\s+|to\s+|in\s+)?(a\s+)?table(\s+view)?$|^टेबल\s*में\s*दिखाओ$/.test(s)) {
    return { action: 'chart_kind', value: 'table' };
  }
  if (/^(show|view|plot|draw|switch|make)\s+(this\s+|it\s+)?(as\s+|to\s+|in\s+)?(a\s+)?(horizontal\s+bar|hbar|ranked\s+bar)(\s+chart|\s+plot)?$/.test(s)) {
    return { action: 'chart_kind', value: 'hbar' };
  }
  if (/^(show|view|plot|draw|switch|make)\s+(this\s+|it\s+)?(as\s+|to\s+|in\s+)?(a\s+)?bar(\s+chart|\s+plot|\s+graph|\s+view)?$|^बार\s*चार्ट$/.test(s)) {
    return { action: 'chart_kind', value: 'bar' };
  }
  if (/^(show|view|plot|draw|switch|make)\s+(this\s+|it\s+)?(as\s+|to\s+|in\s+)?(a\s+)?pie(\s+chart|\s+plot|\s+graph|\s+view)?$/.test(s)) {
    return { action: 'chart_kind', value: 'pie' };
  }
  if (/^(show|view|plot|draw|switch|make)\s+(this\s+|it\s+)?(as\s+|to\s+|in\s+)?(a\s+)?(donut|doughnut)(\s+chart|\s+plot|\s+view)?$|^डोनट\s*चार्ट$/.test(s)) {
    return { action: 'chart_kind', value: 'donut' };
  }
  if (/^(show|view|plot|draw|switch|make)\s+(this\s+|it\s+)?(as\s+|to\s+|in\s+)?(a\s+)?line(\s+chart|\s+plot|\s+graph|\s+view)?$/.test(s)) {
    return { action: 'chart_kind', value: 'line' };
  }
  if (/^(show|view|plot|draw|switch|make)\s+(this\s+|it\s+)?(as\s+|to\s+|in\s+)?(an?\s+)?area(\s+chart|\s+plot|\s+graph|\s+view)?$/.test(s)) {
    return { action: 'chart_kind', value: 'area' };
  }
  if (/^(show|view|plot|draw|switch|make)\s+(this\s+|it\s+)?(as\s+|to\s+|in\s+)?(a\s+)?scatter(\s+chart|\s+plot|\s+graph|\s+view)?$/.test(s)) {
    return { action: 'chart_kind', value: 'scatter' };
  }
  if (/^(show|view|plot|draw|switch|make)\s+(this\s+|it\s+)?(as\s+|to\s+|in\s+)?(a\s+)?treemap(\s+chart|\s+plot|\s+view)?$/.test(s)) {
    return { action: 'chart_kind', value: 'treemap' };
  }
  if (/^(show|view|plot|draw|switch|make)\s+(this\s+|it\s+)?(as\s+|to\s+|in\s+)?(a\s+)?waterfall(\s+chart|\s+plot|\s+view)?$/.test(s)) {
    return { action: 'chart_kind', value: 'waterfall' };
  }

  // P4.1 (BUG-22, SPEC-09 §4.4): generic re-plot of the CURRENT visual — "can you express it as a waterfall",
  // "convert this to a line chart", "इसे वॉटरफॉल में दिखाओ". Requires a pronoun (it/this/that/इसे) so data questions
  // ("show revenue as a line chart for 5 years") still go to the backend. The kind comes from the shared precedence.
  if (
    /^(can\s+you\s+|could\s+you\s+|please\s+)*(show|view|plot|draw|switch|make|express|display|convert|change|turn|present|redraw)\s+(this|it|that)\b/.test(s) ||
    /^(इसे|इसको|यह)\s.*(दिखाओ|दिखाइए|बनाओ)$/.test(s)
  ) {
    const k = resolveKind(s);
    if (k && (UI_ACTIONS.chart_kind as readonly string[]).includes(k)) return { action: 'chart_kind', value: k as (typeof UI_ACTIONS.chart_kind)[number] };
  }

  // Export: handled above by resolveExportIntent (P4.7).

  // Persona: P0.4 (BUG-06, SPEC-06 §4.4) — never switched from typed/spoken text. Such requests go to the
  // backend, which answers R-ROLE (or, for the demo presenter, issues a new signed session).

  // Language
  if (/^(speak\s+in\s+hindi|switch\s+to\s+hindi|hindi\s+mode|हिंदी\s*में\s*बोलो|हिंदी)$/.test(s)) {
    return { action: 'language', value: 'hi' };
  }
  if (/^(speak\s+in\s+english|switch\s+to\s+english|english\s+mode)$/.test(s)) {
    return { action: 'language', value: 'en' };
  }
  if (/^(speak\s+in\s+hinglish|switch\s+to\s+hinglish|hinglish\s+mode)$/.test(s)) {
    return { action: 'language', value: 'hi-en' };
  }

  return null;
}

/**
 * If *every* clause of `text` is a plain UI command (that does not require a new
 * BigQuery query), return the list of commands so the browser can execute them in 0ms.
 * If any clause is a data question or screen navigation requiring backend data,
 * return `null` so it goes through the agent.
 */
export function parseUiCommands(text: string): UiCommand[] | null {
  const cleaned = text.trim().replace(/[?.!]+$/g, '');
  if (!cleaned) return null;
  // Whole-utterance export check first (export requests often list column names separated by commas / "and")
  const wholeExport = detectExportIntent(cleaned);
  if (wholeExport) {
    return [
      wholeExport.columns.length > 0
        ? { action: 'export', value: wholeExport.value, columns: wholeExport.columns }
        : { action: 'export', value: wholeExport.value },
    ];
  }
  const parts = cleaned
    .split(/\s*(?:,|\band\s+then\b|\bthen\b|\band\b|\baur\b|और)\s*/i)
    .map((p) => p.trim())
    .filter(Boolean);
  if (parts.length === 0) return null;
  const cmds: UiCommand[] = [];
  for (const p of parts) {
    const m = matchClause(p);
    if (!m) return null;
    cmds.push(m);
  }
  return cmds;
}
