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
  export: ['pdf', 'xlsx', 'docx', 'sheets', 'docs'] as const,
  history: ['back', 'forward'] as const,
} as const;

export type UiAction = keyof typeof UI_ACTIONS;
export type UiCommand = {
  [K in UiAction]: { action: K; value: (typeof UI_ACTIONS)[K][number] | string };
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
    case 'export':
      return `Exported → ${cmd.value.toUpperCase()}`;
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

  // Export
  if (/\b(export\s+(to\s+)?pdf|download\s+pdf|save\s+as\s+pdf)\b/.test(s)) {
    return { action: 'export', value: 'pdf' };
  }
  if (/\b(export\s+(to\s+)?(excel|xlsx|sheets)|download\s+(excel|xlsx))\b/.test(s)) {
    return { action: 'export', value: 'xlsx' };
  }

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
