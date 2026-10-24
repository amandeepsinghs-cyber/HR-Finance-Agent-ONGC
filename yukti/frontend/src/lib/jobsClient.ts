/**
 * Jobs API client and SSE subscriber for Yukti v3 background agents (Packet P3.6a, SPEC-03 §7.1).
 */
import type { AnswerContract, JobSpec } from '@/contracts/answerContract';

export interface StartJobParams {
  proposed_action_id: string;
  session_id?: string;
  inputs_override?: Record<string, unknown>;
}

export interface JobWithResult extends JobSpec {
  session_id?: string;
  result?: AnswerContract;
}

export class JobsApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseErrorMessage(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data?.detail === 'string') return data.detail;
    if (typeof data?.message === 'string') return data.message;
    if (data?.error?.message) return String(data.error.message);
  } catch {
    // ignore JSON parse errors
  }
  return `HTTP ${res.status}`;
}

export async function startJob(params: StartJobParams): Promise<JobSpec> {
  const res = await fetch('/api/jobs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    throw new JobsApiError(res.status, await parseErrorMessage(res));
  }
  const data = await res.json();
  return (data.job || data) as JobSpec;
}

export async function cancelAction(actionId: string, sessionId?: string): Promise<void> {
  const qs = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : '';
  const res = await fetch(`/api/actions/${encodeURIComponent(actionId)}/cancel${qs}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(sessionId ? { session_id: sessionId } : {}),
  });
  if (!res.ok && res.status !== 204) {
    throw new JobsApiError(res.status, await parseErrorMessage(res));
  }
}

export async function getJob(jobId: string, sessionId?: string): Promise<JobWithResult> {
  const qs = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : '';
  const res = await fetch(`/api/jobs/${encodeURIComponent(jobId)}${qs}`);
  if (!res.ok) {
    throw new JobsApiError(res.status, await parseErrorMessage(res));
  }
  const data = await res.json();
  return (data.job || data) as JobWithResult;
}

export async function cancelJob(jobId: string): Promise<JobSpec> {
  const res = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/cancel`, {
    method: 'POST',
  });
  if (!res.ok) {
    throw new JobsApiError(res.status, await parseErrorMessage(res));
  }
  const data = await res.json();
  return (data.job || data) as JobSpec;
}

export async function getJobResult(jobId: string): Promise<AnswerContract> {
  const res = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/result`);
  if (!res.ok) {
    throw new JobsApiError(res.status, await parseErrorMessage(res));
  }
  return (await res.json()) as AnswerContract;
}

export async function listJobs(sessionId: string): Promise<JobWithResult[]> {
  if (!sessionId) return [];
  const res = await fetch(`/api/jobs?session_id=${encodeURIComponent(sessionId)}`);
  if (!res.ok) return [];
  const data = await res.json();
  return Array.isArray(data?.jobs) ? (data.jobs as JobWithResult[]) : [];
}

export interface JobEventHandlers {
  onUpdate: (job: JobSpec) => void;
  onCompleted?: (job: JobSpec, result?: AnswerContract) => void;
  onFailed?: (job: JobSpec) => void;
  onCancelled?: (job: JobSpec) => void;
}

/**
 * Subscribe to `/api/jobs/{id}/events` via EventSource, with automatic polling fallback
 * so step/progress updates and completion work across both live SSE and mocked Playwright tests.
 */
export function subscribeJobEvents(
  jobId: string,
  handlers: JobEventHandlers,
  sessionId?: string,
): () => void {
  let closed = false;
  let terminalHandled = false;
  let es: EventSource | null = null;
  let pollTimer: number | undefined;

  const finishTerminal = async (job: JobWithResult) => {
    if (closed || terminalHandled) return;
    if (job.status === 'succeeded') {
      terminalHandled = true;
      stop();
      let result = job.result;
      if (!result) {
        try {
          result = await getJobResult(jobId);
        } catch {
          // result may already be embedded on job
        }
      }
      handlers.onUpdate(job);
      handlers.onCompleted?.(job, result);
    } else if (job.status === 'failed' || job.status === 'expired') {
      terminalHandled = true;
      stop();
      handlers.onUpdate(job);
      handlers.onFailed?.(job);
    } else if (job.status === 'cancelled') {
      terminalHandled = true;
      stop();
      handlers.onUpdate(job);
      handlers.onCancelled?.(job);
    }
  };

  const handlePayload = (raw: string) => {
    if (closed || terminalHandled) return;
    try {
      const parsed = JSON.parse(raw);
      const job = (parsed.job || parsed) as JobWithResult;
      if (!job || !job.id) return;
      handlers.onUpdate(job);
      if (job.status === 'succeeded' || job.status === 'failed' || job.status === 'cancelled' || job.status === 'expired') {
        void finishTerminal(job);
      }
    } catch {
      // ignore malformed SSE frame
    }
  };

  const startPolling = () => {
    if (closed || pollTimer !== undefined) return;
    const tick = async () => {
      if (closed || terminalHandled) return;
      try {
        const job = await getJob(jobId, sessionId);
        if (closed || terminalHandled) return;
        handlers.onUpdate(job);
        if (job.status === 'succeeded' || job.status === 'failed' || job.status === 'cancelled' || job.status === 'expired') {
          await finishTerminal(job);
          return;
        }
      } catch {
        // transient network error during poll
      }
      if (!closed && !terminalHandled) {
        pollTimer = window.setTimeout(tick, 400);
      }
    };
    pollTimer = window.setTimeout(tick, 250);
  };

  if (typeof window !== 'undefined' && typeof window.EventSource !== 'undefined') {
    try {
      es = new window.EventSource(`/api/jobs/${encodeURIComponent(jobId)}/events`);
      const eventTypes = [
        'job.queued',
        'job.step',
        'job.progress',
        'job.completed',
        'job.failed',
        'job.cancelled',
        'message',
      ];
      for (const evt of eventTypes) {
        es.addEventListener(evt, (e: Event) => {
          const me = e as MessageEvent<string>;
          if (me?.data) handlePayload(me.data);
        });
      }
      es.onerror = () => {
        if (es) {
          es.close();
          es = null;
        }
        startPolling();
      };
    } catch {
      startPolling();
    }
  }

  startPolling();

  function stop() {
    closed = true;
    if (es) {
      es.close();
      es = null;
    }
    if (pollTimer !== undefined) {
      window.clearTimeout(pollTimer);
      pollTimer = undefined;
    }
  }

  return stop;
}
