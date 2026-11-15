/**
 * Access requests (15-Nov, sponsor demo): E1–E4 officers can ask their function's Director / Executive Director
 * for data that was withheld (refused, or reduced to aggregates). Backend: app/access_requests.py.
 * Demo scope: the decision is real and audited, but approval never unlocks names inside Yukti (D-11).
 */
export type AccessRequestStatus = 'pending' | 'approved' | 'rejected';

export interface AccessRequest {
  id: string;
  status: AccessRequestStatus;
  created_at: number;
  decided_at: number | null;
  function: 'HR' | 'FIN' | string;
  approver_label: string;
  requester: { emp_id: string; persona: string; display_name: string; designation: string };
  turn_id: string;
  question: string;
  subject: string;
  code: string;
  rule_ref: string;
  reason: string;
  decided_by: { emp_id: string; persona: string; display_name: string; designation: string } | null;
  note: string;
  outcome: string;
}

export interface AccessRequestList {
  role: 'requester' | 'approver';
  pending: number;
  requests: AccessRequest[];
}

/** Fired after any create / decision so every bell and card refreshes at once. */
export const ACCESS_REQUESTS_EVENT = 'yukti:access-requests-changed';
const notify = () => window.dispatchEvent(new Event(ACCESS_REQUESTS_EVENT));

export function approverLabelFor(persona?: string | null): string {
  return (persona || '').toUpperCase().endsWith('_FIN')
    ? 'Director (Finance) / Executive Director (Finance)'
    : 'Director (HR) / Executive Director (HR)';
}

export async function listAccessRequests(): Promise<AccessRequestList | null> {
  try {
    const r = await fetch('/api/access-requests', { credentials: 'same-origin', cache: 'no-store' });
    return r.ok ? ((await r.json()) as AccessRequestList) : null;
  } catch {
    return null;
  }
}

export async function createAccessRequest(body: {
  turn_id?: string;
  question?: string;
  subject?: string;
  code?: string;
  rule_ref?: string;
  reason?: string;
}): Promise<AccessRequest | null> {
  try {
    const r = await fetch('/api/access-requests', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!r.ok) return null;
    const out = (await r.json()) as AccessRequest;
    notify();
    return out;
  } catch {
    return null;
  }
}

export async function decideAccessRequest(id: string, decision: 'approved' | 'rejected', note = ''): Promise<AccessRequest | null> {
  try {
    const r = await fetch(`/api/access-requests/${encodeURIComponent(id)}/decision`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ decision, note }),
    });
    if (!r.ok) return null;
    const out = (await r.json()) as AccessRequest;
    notify();
    return out;
  } catch {
    return null;
  }
}

export function timeAgo(ts?: number | null): string {
  if (!ts) return '';
  const s = Math.max(0, Math.round(Date.now() / 1000 - ts));
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return `${Math.floor(s / 86400)} d ago`;
}
