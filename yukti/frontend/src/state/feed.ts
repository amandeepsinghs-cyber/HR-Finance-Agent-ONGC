/**
 * Conversation feed state (U2.2): an ordered list of turns (question → answer) that replaces the single
 * `contract` + history strip. Pure reducer so it can be unit-tested without React.
 */
import type { AnswerContract, SpecPatch } from '@/contracts/answerContract';
import { replot, profile, ReplotKind, ALL_KINDS } from '@/charts/compat';

export type TurnStatus = 'pending' | 'done' | 'error';

export interface Turn {
  id: string;
  question: string;
  status: TurnStatus;
  contract?: AnswerContract;
  error?: string;
  askedAt: number;
  answeredAt?: number;
  viaVoice?: boolean;
  /** drill-down patch the question was asked with (kept for Retry) */
  specPatch?: SpecPatch;
  /** true for answers that arrived live in this view (drives the newest-answer glow); false for restores */
  fresh?: boolean;
}

export type FeedAction =
  | { type: 'ask'; id: string; question: string; viaVoice?: boolean; at?: number; specPatch?: SpecPatch }
  | { type: 'question'; id: string; question: string }
  | { type: 'answer'; contract: AnswerContract; id?: string; question?: string; at?: number; newId?: string }
  | { type: 'fail'; id: string; error: string }
  | { type: 'settle'; id: string; text?: string; at?: number }
  | { type: 'refine'; update: (c: AnswerContract) => AnswerContract; id?: string }
  | { type: 'drop'; id: string }
  | { type: 'reset' };

const textContract = (text: string, id: string): AnswerContract => ({
  turn_id: `${id}_text`,
  language: 'en',
  spoken_summary: text,
  display_text: text,
  visual: { type: 'none', mode: 'replace' },
  sources: [],
  access: { status: 'allowed' },
});

export function feedReducer(state: Turn[], a: FeedAction): Turn[] {
  const now = (t?: number) => t ?? Date.now();
  switch (a.type) {
    case 'ask': {
      if (state.some((t) => t.id === a.id)) return state;
      return [...state, { id: a.id, question: a.question, status: 'pending', askedAt: now(a.at), viaVoice: a.viaVoice, specPatch: a.specPatch }];
    }
    case 'question':
      return state.map((t) => (t.id === a.id ? { ...t, question: a.question } : t));
    case 'answer': {
      // Fill the named turn. An explicit id that no longer exists (reset / dropped) is a stale answer: ignore it,
      // never let it fill a different question's card. Id-less answers fill the latest pending turn or append.
      let idx = a.id ? state.findIndex((t) => t.id === a.id) : -1;
      if (a.id && idx < 0) return state;
      if (idx < 0) {
        const last = state[state.length - 1];
        if (last && last.status === 'pending') idx = state.length - 1;
      }
      if (idx >= 0) {
        const copy = [...state];
        copy[idx] = {
          ...copy[idx],
          question: a.question && !copy[idx].question ? a.question : copy[idx].question,
          status: 'done',
          contract: a.contract,
          error: undefined,
          answeredAt: now(a.at),
          fresh: true,
        };
        return copy;
      }
      const id = a.newId || `turn_${state.length}_${now(a.at)}`;
      return [
        ...state,
        { id, question: a.question || a.contract.visual?.title || 'Question', status: 'done', contract: a.contract, askedAt: now(a.at), answeredAt: now(a.at), fresh: true },
      ];
    }
    case 'fail':
      return state.map((t) => (t.id === a.id ? { ...t, status: 'error', error: a.error } : t));
    case 'settle': {
      // A voice turn ended. If it never got a contract: keep it as a text answer, or drop it if empty.
      const t = state.find((x) => x.id === a.id);
      if (!t || t.status !== 'pending') return state;
      const text = (a.text || '').trim();
      if (!text) return state.filter((x) => x.id !== a.id);
      return state.map((x) => (x.id === a.id ? { ...x, status: 'done', contract: textContract(text, x.id), answeredAt: now(a.at), fresh: true } : x));
    }
    case 'refine': {
      // Re-plot / "show as table" updates the CURRENT (latest answered) card in place (U2.5) — or a specific
      // card when the toolbar of a historic card is used.
      for (let i = state.length - 1; i >= 0; i--) {
        const t = state[i];
        if (a.id && t.id !== a.id) continue;
        if (t.status === 'done' && t.contract) {
          const next = a.update(t.contract);
          if (next === t.contract) return state;
          const copy = [...state];
          copy[i] = { ...t, contract: next };
          return copy;
        }
      }
      return state;
    }
    case 'drop':
      return state.filter((t) => t.id !== a.id);
    case 'reset':
      return [];
    default:
      return state;
  }
}

/** Order-independent signature of a visual's data rows (values only; chart kind / column order ignored). */
function rowsSignature(c?: AnswerContract): string {
  const v: any = c?.visual;
  const src = v?.source?.rows || v?.table?.rows || v?.chart?.data || [];
  const cols: string[] = v?.source?.columns || v?.table?.columns || [];
  return (src as any[])
    .map((r) => {
      const o = Array.isArray(r) ? Object.fromEntries(cols.map((k, i) => [k, r[i]])) : r || {};
      return Object.values(o).map((x) => String(x ?? '')).sort().join('|');
    })
    .sort()
    .join('\n');
}

/**
 * A backend re-plot of the current card (e.g. voice "show as pie"): refine in place, don't append.
 * True only for an explicit flag, or mode 'refine' with the SAME title AND identical data rows — a follow-up like
 * "now for FY25" with the same title and row count but different values is a new answer (U2 G4 #2).
 */
export function isReplotOf(c: AnswerContract, current?: AnswerContract): boolean {
  if (!current) return false;
  if ((c as any).replot === true || (c.visual as any)?.replot === true) return true;
  if (c.visual?.mode !== 'refine') return false;
  const a = (c.visual?.title || '').trim().toLowerCase();
  const b = (current.visual?.title || '').trim().toLowerCase();
  if (!a || a !== b) return false;
  const sa = rowsSignature(c);
  return sa.length > 0 && sa === rowsSignature(current);
}

export const latestAnswered = (turns: Turn[]): Turn | undefined => {
  for (let i = turns.length - 1; i >= 0; i--) if (turns[i].status === 'done' && turns[i].contract) return turns[i];
  return undefined;
};

/** "Show this as <kind>" for voice/typed commands: the same engine as the toolbar (U5.7/U5.8), note attached. */
export function applyChartKind(prev: AnswerContract, kindRaw: string): AnswerContract {
  if (!prev?.visual || prev.visual.type === 'none') return prev;
  const kind = kindRaw.toLowerCase() as ReplotKind;
  if (!REPLOT_KINDS.includes(kind)) return prev;
  if (!profile(prev.visual).rows.length) return prev;
  const r = replot(prev.visual, kind);
  if (r.visual === prev.visual) return prev;
  return { ...prev, visual: { ...r.visual, replot_note: r.note } };
}

const REPLOT_KINDS: ReplotKind[] = ALL_KINDS;
