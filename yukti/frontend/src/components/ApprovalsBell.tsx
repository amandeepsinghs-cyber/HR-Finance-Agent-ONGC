'use client';

/**
 * ApprovalsBell (15-Nov): top-bar inbox for access requests.
 * - Director (HR / Finance) and CMD: "Pending approvals" with Approve / Reject and an optional note.
 * - E1–E4 officers: "My access requests" with their status.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Bell, Check, X } from 'lucide-react';
import {
  ACCESS_REQUESTS_EVENT,
  AccessRequest,
  AccessRequestList,
  decideAccessRequest,
  listAccessRequests,
  timeAgo,
} from '@/services/accessRequests';

const STATUS_PILL: Record<string, string> = {
  pending: 'bg-[var(--warning-pale)] text-[var(--warning)]',
  approved: 'bg-[var(--positive-pale)] text-[var(--positive)]',
  rejected: 'bg-[var(--surface-2)] text-[var(--maroon)]',
};

export const ApprovalsBell: React.FC<{ persona: string | null }> = ({ persona }) => {
  const [data, setData] = useState<AccessRequestList | null>(null);
  const [open, setOpen] = useState(false);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const boxRef = useRef<HTMLDivElement | null>(null);

  const refresh = useCallback(async () => {
    if (!persona) return setData(null);
    setData(await listAccessRequests());
  }, [persona]);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), 8000);
    const onChange = () => void refresh();
    window.addEventListener(ACCESS_REQUESTS_EVENT, onChange);
    return () => {
      window.clearInterval(id);
      window.removeEventListener(ACCESS_REQUESTS_EVENT, onChange);
    };
  }, [refresh]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => boxRef.current && !boxRef.current.contains(e.target as Node) && setOpen(false);
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  if (!persona) return null;
  const approver = data?.role === 'approver';
  const pending = data?.pending || 0;
  const items = data?.requests || [];

  const decide = async (r: AccessRequest, d: 'approved' | 'rejected') => {
    setBusy(r.id);
    await decideAccessRequest(r.id, d, notes[r.id] || '');
    setBusy(null);
    void refresh();
  };

  return (
    <div className="relative" ref={boxRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        data-testid="approvals-bell"
        aria-label={approver ? `Pending approvals: ${pending}` : `My access requests: ${pending} pending`}
        title={approver ? 'Pending access approvals' : 'My access requests'}
        className="relative inline-grid place-items-center w-9 h-9 rounded-[var(--radius-md)] text-[var(--ink-2)] hover:bg-[var(--surface-2)] hover:text-[var(--ink)] transition-colors"
      >
        <Bell className="w-[1.1rem] h-[1.1rem]" />
        {pending > 0 && (
          <span data-testid="approvals-count" className="absolute -top-0.5 -right-0.5 min-w-[1.1rem] h-[1.1rem] px-1 rounded-full bg-[var(--critical)] text-[var(--on-accent)] text-[0.65rem] font-bold grid place-items-center">
            {pending}
          </span>
        )}
      </button>

      {open && (
        <div
          data-testid="approvals-panel"
          className="absolute right-0 top-[calc(100%+0.5rem)] z-[60] w-[min(28rem,92vw)] max-h-[70vh] overflow-y-auto rounded-[var(--radius-lg)] border border-[var(--hairline)] bg-[var(--card)] shadow-[var(--panel-shadow)]"
        >
          <div className="px-4 py-3 border-b border-[var(--hairline)]">
            <div className="font-semibold text-[var(--ink)]">{approver ? 'Pending approvals' : 'My access requests'}</div>
            <div className="text-caption text-[var(--ink-2)]">
              {approver ? 'Requests from E1–E4 officers for data withheld at their access level.' : 'Requests you sent for withheld data.'}
            </div>
          </div>
          {items.length === 0 && <div className="px-4 py-6 text-label text-[var(--ink-3)]">No requests yet.</div>}
          <ul className="divide-y divide-[var(--hairline)]">
            {items.map((r) => (
              <li key={r.id} className="px-4 py-3 flex flex-col gap-2" data-testid="approval-item" data-status={r.status}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-label font-semibold text-[var(--ink)]">
                      {approver ? `${r.requester.display_name} · ${r.requester.designation}` : `To ${r.approver_label}`}
                    </div>
                    <div className="text-caption text-[var(--ink-3)]">
                      {r.id} · {timeAgo(r.created_at)} {r.code ? `· ${r.code}` : ''}
                    </div>
                  </div>
                  <span className={`shrink-0 px-2 py-0.5 rounded-pill text-caption font-semibold capitalize ${STATUS_PILL[r.status] || ''}`}>{r.status}</span>
                </div>
                {(r.question || r.subject) && (
                  <div className="text-caption text-[var(--ink-2)] rounded-[var(--radius-sm)] bg-[var(--surface)] px-2.5 py-1.5">
                    “{r.question || r.subject}”
                  </div>
                )}
                {r.status !== 'pending' && <div className="text-caption text-[var(--ink-2)]">{r.outcome}</div>}
                {approver && r.status === 'pending' && (
                  <div className="flex flex-col gap-2">
                    <input
                      value={notes[r.id] || ''}
                      onChange={(e) => setNotes((n) => ({ ...n, [r.id]: e.target.value }))}
                      placeholder="Optional note to the officer"
                      className="w-full px-2.5 py-1.5 rounded-[var(--radius-sm)] border border-[var(--hairline)] bg-[var(--card)] text-caption text-[var(--ink)] placeholder:text-[var(--ink-3)]"
                    />
                    <div className="flex gap-2 justify-end">
                      <button
                        type="button"
                        data-testid="approval-reject"
                        disabled={busy === r.id}
                        onClick={() => void decide(r, 'rejected')}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-pill border border-[var(--hairline)] text-label text-[var(--maroon)] hover:bg-[var(--maroon-pale)] disabled:opacity-60"
                      >
                        <X className="w-3.5 h-3.5" /> Reject
                      </button>
                      <button
                        type="button"
                        data-testid="approval-approve"
                        disabled={busy === r.id}
                        onClick={() => void decide(r, 'approved')}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-pill bg-[var(--positive-fill)] text-[var(--on-accent)] text-label font-semibold hover:opacity-90 disabled:opacity-60"
                      >
                        <Check className="w-3.5 h-3.5" /> Approve
                      </button>
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
