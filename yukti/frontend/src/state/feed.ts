/**
 * Conversation feed state (U2.2 + P3.6a): an ordered list of turns (question → answer) that replaces the single
 * `contract` + history strip, plus background job result append and reload rehydration (`SPEC-03 §9`, `BEH-05.10`).
 * Pure reducer so it can be unit-tested without React.
 */
import type { AnswerContract, JobSpec, SpecPatch } from '@/contracts/answerContract';
import { replot, profile, ReplotKind, ALL_KINDS } from '@/charts/compat';
import { getJobResult, JobWithResult, listJobs } from '@/lib/jobsClient';

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
  /** P5.2 (BEH-07.31, BUG-18): speak_id when this turn is being voiced by Leda */
  speakId?: string;
}

export type FeedAction =
  | { type: 'ask'; id: string; question: string; viaVoice?: boolean; at?: number; specPatch?: SpecPatch; speakId?: string }
  | { type: 'question'; id: string; question: string }
  | { type: 'answer'; contract: AnswerContract; id?: string; question?: string; at?: number; newId?: string; speakId?: string }
  | { type: 'fail'; id: string; error: string }
  | { type: 'settle'; id: string; text?: string; at?: number }
  | { type: 'refine'; update: (c: AnswerContract) => AnswerContract; id?: string }
  | { type: 'job_result'; job: JobSpec; result: AnswerContract; at?: number }
  | { type: 'rehydrate_jobs'; jobs: JobWithResult[]; at?: number }
  | { type: 'drop'; id: string }
  | { type: 'reset' }
  | { type: 'restore'; turns: Turn[] };

const textContract = (text: string, id: string): AnswerContract => ({
  turn_id: `${id}_text`,
  language: 'en',
  spoken_summary: text,
  display_text: text,
  visual: { type: 'none', mode: 'replace' },
  sources: [],
  access: { status: 'allowed' },
});

function buildJobProgressContract(job: JobSpec): AnswerContract {
  return {
    contract_version: 3,
    turn_id: `job_progress:${job.id}`,
    language: 'en',
    spoken_summary: `Running ${job.agent} in the background.`,
    display_text: `Running ${job.agent} in the background.`,
    visual: { type: 'none', mode: 'replace', title: `Background Job · ${job.agent}` },
    sources: [],
    access: { status: 'allowed' },
    job,
  };
}

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
      let idx = a.id ? state.findIndex((t) => t.id === a.id) : -1;
      if (a.id && idx < 0) return state;
      if (idx < 0 && a.contract?.turn_id) {
        idx = state.findIndex((t) => t.contract?.turn_id === a.contract.turn_id || t.id === a.contract.turn_id);
      }
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
    case 'job_result': {
      const turnId = a.result.turn_id || `job:${a.job.id}`;
      const enrichedResult: AnswerContract = {
        ...a.result,
        turn_id: turnId,
        job: a.result.job || a.job,
      };
      const existingIdx = state.findIndex(
        (t) => t.id === turnId || t.contract?.turn_id === turnId,
      );
      if (existingIdx >= 0) {
        const copy = [...state];
        copy[existingIdx] = {
          ...copy[existingIdx],
          status: 'done',
          contract: enrichedResult,
          answeredAt: now(a.at),
          fresh: true,
        };
        return copy;
      }
      return [
        ...state,
        {
          id: turnId,
          question: enrichedResult.visual?.title || `Completed ${a.job.agent}`,
          status: 'done',
          contract: enrichedResult,
          askedAt: now(a.at),
          answeredAt: now(a.at),
          fresh: true,
        },
      ];
    }
    case 'rehydrate_jobs': {
      let next = [...state];
      for (const job of a.jobs) {
        const resTurnId = job.result?.turn_id || `job:${job.id}`;
        const hasResultTurn = next.some(
          (t) => t.id === resTurnId || t.contract?.turn_id === resTurnId,
        );
        const hasJobCardTurn = next.some(
          (t) => t.contract?.job?.id === job.id,
        );

        if (job.status === 'succeeded' && job.result) {
          if (!hasResultTurn) {
            const enriched: AnswerContract = {
              ...job.result,
              turn_id: resTurnId,
              job: job.result.job || job,
            };
            next = [
              ...next,
              {
                id: resTurnId,
                question: enriched.visual?.title || `DCF Valuation (${job.id})`,
                status: 'done',
                contract: enriched,
                askedAt: now(a.at),
                answeredAt: now(a.at),
                fresh: false,
              },
            ];
          }
        } else if (!hasJobCardTurn && !hasResultTurn) {
          const progId = `job_progress:${job.id}`;
          next = [
            ...next,
            {
              id: progId,
              question: `Background job · ${job.agent}`,
              status: 'done',
              contract: buildJobProgressContract(job),
              askedAt: now(a.at),
              answeredAt: now(a.at),
              fresh: false,
            },
          ];
        }
      }
      return next;
    }
    case 'fail':
      return state.map((t) => (t.id === a.id ? { ...t, status: 'error', error: a.error } : t));
    case 'settle': {
      if ((a as any).speakId) return state;
      const t = state.find((x) => x.id === a.id);
      if (!t || t.status !== 'pending') return state;
      const text = (a.text || '').trim();
      if (!text) return state.filter((x) => x.id !== a.id);
      return state.map((x) => (x.id === a.id ? { ...x, status: 'done', contract: textContract(text, x.id), answeredAt: now(a.at), fresh: true } : x));
    }
    case 'refine': {
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
    case 'restore':
      return a.turns.map((t) => ({ ...t, fresh: false }));
    default:
      return state;
  }
}

/**
 * Rehydrate running/completed jobs for `sessionId` via `GET /api/jobs?session_id=` (`SPEC-03 §9`, `BEH-05.10`).
 */
export async function rehydrateJobsForSession(
  sessionId: string,
  dispatch: (a: FeedAction) => void,
): Promise<void> {
  if (!sessionId) return;
  try {
    const jobs = await listJobs(sessionId);
    if (!jobs.length) return;
    const hydrated: JobWithResult[] = await Promise.all(
      jobs.map(async (j) => {
        if (j.status === 'succeeded' && !j.result) {
          try {
            const res = await getJobResult(j.id);
            return { ...j, result: res };
          } catch {
            return j;
          }
        }
        return j;
      }),
    );
    dispatch({ type: 'rehydrate_jobs', jobs: hydrated });
  } catch {
    // ignore offline errors during rehydration
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
