'use client';

/**
 * AccessRequestBar (15-Nov): shown on an answer card when an E1–E4 officer's request was refused or reduced to
 * aggregates. States the data exists but is withheld at this access level, and offers "Request access from
 * Director / Executive Director". After a click it tracks the request (pending → approved / rejected).
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Lock, Send, Clock, CheckCircle2, XCircle } from 'lucide-react';
import type { AnswerContract } from '@/contracts/answerContract';
import { isJunior } from '@/personas';
import {
  ACCESS_REQUESTS_EVENT,
  AccessRequest,
  approverLabelFor,
  createAccessRequest,
  listAccessRequests,
} from '@/services/accessRequests';

export function shouldOfferAccessRequest(contract: AnswerContract, persona?: string | null): boolean {
  const st = contract.access?.status;
  const code = (contract.access?.code || '').toUpperCase();
  return isJunior(persona) && (st === 'refused' || st === 'partial') && code !== 'R-ROLE';
}

interface Props {
  contract: AnswerContract;
  persona?: string | null;
  question?: string;
}

export const AccessRequestBar: React.FC<Props> = ({ contract, persona, question }) => {
  const [req, setReq] = useState<AccessRequest | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const turnId = contract.turn_id || '';
  const approver = approverLabelFor(persona);

  const refresh = useCallback(async () => {
    const list = await listAccessRequests();
    const mine = list?.requests.find((r) => r.turn_id === turnId);
    if (mine) setReq(mine);
  }, [turnId]);

  useEffect(() => {
    void refresh();
    const onChange = () => void refresh();
    window.addEventListener(ACCESS_REQUESTS_EVENT, onChange);
    return () => window.removeEventListener(ACCESS_REQUESTS_EVENT, onChange);
  }, [refresh]);

  // poll only while the request is waiting for a decision
  useEffect(() => {
    if (req?.status !== 'pending') return;
    const id = window.setInterval(() => void refresh(), 6000);
    return () => window.clearInterval(id);
  }, [req?.status, refresh]);

  const send = async () => {
    setSending(true);
    setError(null);
    const out = await createAccessRequest({
      turn_id: turnId,
      question: question || contract.display_text || contract.spoken_summary || '',
      subject: contract.visual?.title || '',
      code: contract.access?.code || '',
      rule_ref: contract.access?.rule_ref || '',
      reason: contract.access?.reason || '',
    });
    setSending(false);
    if (out) setReq(out);
    else setError('The request could not be sent. Please try again.');
  };

  const status = req?.status;
  return (
    <div
      data-testid="access-request-bar"
      data-status={status || 'none'}
      className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-md)] border border-[var(--mic-border)] bg-[var(--maroon-pale)] px-4 py-3"
    >
      <div className="flex items-start gap-2.5 min-w-0">
        <Lock className="w-4 h-4 mt-[0.2rem] text-[var(--maroon)] shrink-0" aria-hidden />
        <div className="min-w-0">
          <div className="text-label font-semibold text-[var(--maroon)]">Access restricted for your role</div>
          <div className="text-caption text-[var(--ink-2)]">
            {status === 'approved' || status === 'rejected'
              ? req?.outcome
              : 'The detailed records exist in ONGC’s data, but they are not shown at your access level.'}
          </div>
        </div>
      </div>

      {!req && (
        <button
          type="button"
          data-testid="access-request-button"
          onClick={() => void send()}
          disabled={sending}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-pill bg-[var(--accent-deep)] text-[var(--on-accent)] text-label font-semibold hover:opacity-90 disabled:opacity-60 transition-opacity"
        >
          <Send className="w-3.5 h-3.5" />
          {sending ? 'Sending…' : `Request access from ${approver}`}
        </button>
      )}
      {status === 'pending' && (
        <span data-testid="access-request-pending" className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-pill bg-[var(--warning-pale)] text-[var(--warning)] text-label font-semibold">
          <Clock className="w-3.5 h-3.5" /> Request {req?.id} pending with {req?.approver_label}
        </span>
      )}
      {status === 'approved' && (
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-pill bg-[var(--positive-pale)] text-[var(--positive)] text-label font-semibold">
          <CheckCircle2 className="w-3.5 h-3.5" /> Request {req?.id} approved
        </span>
      )}
      {status === 'rejected' && (
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-pill bg-[var(--surface-2)] text-[var(--maroon)] text-label font-semibold">
          <XCircle className="w-3.5 h-3.5" /> Request {req?.id} rejected
        </span>
      )}
      {error && <div className="w-full text-caption text-[var(--maroon)]">{error}</div>}
    </div>
  );
};
