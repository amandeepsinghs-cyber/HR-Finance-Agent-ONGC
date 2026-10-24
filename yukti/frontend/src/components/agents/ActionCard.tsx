'use client';

/**
 * Permission gate card for proposed agent actions (Packet P3.6a, SPEC-03 §6.1, BEH-05.01 / .02 / .04 / .07).
 * Uses only design tokens (`var(--...)`) — zero hardcoded hex colours.
 */
import React, { useMemo, useState } from 'react';
import type { AnswerContract, EditableInputSpec, JobSpec, ProposedActionSpec } from '@/contracts/answerContract';
import { cancelAction, JobsApiError, startJob } from '@/lib/jobsClient';
import { AssumptionsForm } from './AssumptionsForm';
import { JobCard } from './JobCard';
import { Badge, Card, Chip } from '@/components/ui/primitives';
import { Clock, Play, ShieldCheck, SlidersHorizontal, X } from 'lucide-react';

export interface ActionCardProps {
  proposedAction: ProposedActionSpec;
  sessionId?: string;
  initialJob?: JobSpec | null;
  onJobStarted?: (job: JobSpec, overrides?: Record<string, unknown>) => void;
  onJobCompleted?: (result: AnswerContract, finalJob: JobSpec) => void;
  onCancelled?: (actionId: string) => void;
}

const AGENT_NAMES: Record<string, { name: string; version: string }> = {
  dcf_agent: { name: 'ONGC DCF Valuation Agent', version: 'v1.0' },
  hr_transfer_agent: { name: 'HR Transfer Workflow Agent', version: 'v1.0' },
  fin_diagnostics_agent: { name: 'Finance Diagnostics Agent', version: 'v1.0' },
  doc_export_agent: { name: 'Document Export Agent', version: 'v1.0' },
};

const DEFAULT_EDITABLE_INPUTS: EditableInputSpec[] = [
  {
    key: 'wacc_pct',
    label: 'WACC',
    type: 'percent',
    value: 11.42,
    min: 6,
    max: 16,
    step: 0.25,
    unit: '%',
    source: 'fact_wacc_annual FY26',
  },
  {
    key: 'terminal_g_pct',
    label: 'Terminal growth (g)',
    type: 'percent',
    value: 3.0,
    min: 0,
    max: 6,
    step: 0.25,
    unit: '%',
    source: 'Default (illustrative)',
  },
  {
    key: 'brent_usd',
    label: 'Brent crude',
    type: 'number',
    value: 78.0,
    min: 40,
    max: 120,
    step: 1,
    unit: 'USD/bbl',
    source: 'fact_price_realisation FY26',
  },
];

export const ActionCard: React.FC<ActionCardProps> = ({
  proposedAction,
  sessionId,
  initialJob = null,
  onJobStarted,
  onJobCompleted,
  onCancelled,
}) => {
  const [submitting, setSubmitting] = useState(false);
  const [editing, setEditing] = useState(false);
  const [cancelled, setCancelled] = useState(false);
  const [activeJob, setActiveJob] = useState<JobSpec | null>(initialJob);
  const [appliedOverrides, setAppliedOverrides] = useState<Record<string, unknown>>({});
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const isExpired = useMemo(() => {
    if (!proposedAction.expires_at) return false;
    const t = Date.parse(proposedAction.expires_at);
    return !Number.isNaN(t) && t <= Date.now();
  }, [proposedAction.expires_at]);

  const editableInputs: EditableInputSpec[] = useMemo(() => {
    if (proposedAction.editable_inputs && proposedAction.editable_inputs.length > 0) {
      return proposedAction.editable_inputs;
    }
    const entries = Object.entries(proposedAction.inputs || {});
    if (entries.length === 0) return DEFAULT_EDITABLE_INPUTS;
    return entries.map(([key, val]) => ({
      key,
      label: key.replace(/_/g, ' '),
      type: key.endsWith('_pct') ? 'percent' : typeof val === 'number' ? 'number' : 'enum',
      value: val,
      unit: key.endsWith('_pct') ? '%' : undefined,
      source: 'Verified SSOT',
    }));
  }, [proposedAction.editable_inputs, proposedAction.inputs]);

  const buttons = proposedAction.buttons && proposedAction.buttons.length > 0
    ? proposedAction.buttons
    : (['run', 'edit', 'cancel'] as const);

  const agentMeta = AGENT_NAMES[proposedAction.agent] || { name: proposedAction.agent, version: 'v1.0' };

  const triggerRun = async (overrides?: Record<string, unknown>) => {
    if (submitting || isExpired || activeJob) return;
    setSubmitting(true);
    setErrorMsg(null);
    const effectiveOverrides = overrides ?? appliedOverrides;
    try {
      const job = await startJob({
        proposed_action_id: proposedAction.id,
        session_id: sessionId,
        inputs_override: Object.keys(effectiveOverrides).length > 0 ? effectiveOverrides : undefined,
      });
      setAppliedOverrides(effectiveOverrides);
      setEditing(false);
      setActiveJob(job);
      onJobStarted?.(job, effectiveOverrides);
    } catch (err: unknown) {
      const msg = err instanceof JobsApiError ? err.message : 'Could not start agent job';
      setErrorMsg(msg);
      setSubmitting(false);
    }
  };

  const handleCancel = async () => {
    if (submitting || cancelled) return;
    setSubmitting(true);
    try {
      await cancelAction(proposedAction.id, sessionId);
    } catch {
      // treat as cancelled locally even if proposal already expired on server
    } finally {
      setSubmitting(false);
      setCancelled(true);
      onCancelled?.(proposedAction.id);
    }
  };

  if (cancelled) {
    return (
      <Card className="p-4 max-w-[54rem]" data-testid="action-cancelled" role="status">
        <p className="text-body text-[var(--ink-2)]">Cancelled. No agent was run.</p>
      </Card>
    );
  }

  if (activeJob) {
    return (
      <div className="space-y-2">
        {Object.keys(appliedOverrides).length > 0 && (
          <div className="flex flex-wrap items-center gap-2 text-caption text-[var(--ink-2)]" data-testid="action-edited-summary">
            <Badge tone="warning">edited by you</Badge>
            <span>
              Custom assumptions:{' '}
              {Object.entries(appliedOverrides)
                .map(([k, v]) => `${k}=${String(v)}`)
                .join(', ')}
            </span>
          </div>
        )}
        <JobCard
          initialJob={activeJob}
          sessionId={sessionId}
          onJobCompleted={onJobCompleted}
          onRetry={() => {
            setActiveJob(null);
            setSubmitting(false);
          }}
        />
      </div>
    );
  }

  return (
    <Card
      className={`p-4 max-w-[54rem] space-y-3.5 ${isExpired ? 'opacity-60' : ''}`}
      data-testid="action-card"
      data-action-id={proposedAction.id}
      data-agent={proposedAction.agent}
      data-expired={isExpired ? 'true' : 'false'}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[var(--accent)] shrink-0" aria-hidden />
            <span className="text-label uppercase tracking-[0.06em] text-[var(--accent-deep)] dark:text-[var(--accent-soft)]">
              Permission Required · {agentMeta.name} ({agentMeta.version})
            </span>
          </div>
          <p className="text-body font-medium text-[var(--ink)]" data-testid="action-summary">
            {proposedAction.summary}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Badge tone="neutral" data-testid="action-est-seconds">
            <Clock className="w-3 h-3 mr-1" aria-hidden />~{proposedAction.est_seconds}s
          </Badge>
        </div>
      </div>

      {/* Key assumptions table */}
      {editableInputs.length > 0 && (
        <div className="overflow-x-auto rounded-[var(--radius-md)] border border-[var(--hairline)] bg-[var(--surface)]">
          <table className="w-full text-left border-collapse text-caption" data-testid="action-inputs-table">
            <thead>
              <tr className="border-b border-[var(--hairline)] text-[var(--ink-3)]">
                <th className="py-2 px-3 font-medium">Assumption</th>
                <th className="py-2 px-3 font-medium">Value</th>
                <th className="py-2 px-3 font-medium">Source</th>
              </tr>
            </thead>
            <tbody>
              {editableInputs.map((inp) => {
                const hasOverride = inp.key in appliedOverrides;
                const val = hasOverride ? appliedOverrides[inp.key] : inp.value;
                return (
                  <tr
                    key={inp.key}
                    className="border-b last:border-b-0 border-[var(--hairline)]"
                    data-testid={`action-input-row-${inp.key}`}
                  >
                    <td className="py-2 px-3 font-medium text-[var(--ink)]">{inp.label}</td>
                    <td className="py-2 px-3 font-mono tabular-nums text-[var(--ink)]">
                      {String(val ?? '—')}
                      {inp.unit ? ` ${inp.unit}` : ''}
                      {hasOverride && (
                        <span className="ml-2">
                          <Badge tone="warning">edited by you</Badge>
                        </span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-[var(--ink-2)]">{inp.source || 'Verified SSOT'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {isExpired ? (
        <div
          role="status"
          className="p-2.5 rounded-[var(--radius-sm)] bg-[var(--surface)] text-label text-[var(--ink-2)]"
          data-testid="action-expired"
        >
          This proposal expired. Ask again.
        </div>
      ) : (
        <React.Fragment>
          {editing ? (
            <AssumptionsForm
              inputs={editableInputs}
              initialOverrides={appliedOverrides}
              submitting={submitting}
              serverError={errorMsg}
              onSubmit={(overrides) => void triggerRun(overrides)}
              onCancel={() => {
                setEditing(false);
                setErrorMsg(null);
              }}
            />
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
              <div className="flex flex-wrap items-center gap-2">
                {buttons.includes('run') && (
                  <Chip
                    type="button"
                    selected
                    disabled={submitting}
                    onClick={() => void triggerRun()}
                    data-testid="action-run"
                  >
                    <Play className="w-3.5 h-3.5" aria-hidden />
                    Run
                  </Chip>
                )}
                {buttons.includes('edit') && (
                  <Chip
                    type="button"
                    disabled={submitting}
                    onClick={() => setEditing(true)}
                    data-testid="action-edit"
                  >
                    <SlidersHorizontal className="w-3.5 h-3.5" aria-hidden />
                    Edit assumptions
                  </Chip>
                )}
                {buttons.includes('cancel') && (
                  <Chip
                    type="button"
                    disabled={submitting}
                    onClick={() => void handleCancel()}
                    data-testid="action-cancel"
                  >
                    <X className="w-3.5 h-3.5" aria-hidden />
                    Cancel
                  </Chip>
                )}
              </div>

              {proposedAction.voice_confirm_hint && (
                <span className="text-caption text-[var(--ink-3)]" data-testid="action-voice-hint">
                  {proposedAction.voice_confirm_hint}
                </span>
              )}
            </div>
          )}

          {errorMsg && !editing && (
            <div
              role="alert"
              className="p-2.5 rounded-[var(--radius-sm)] bg-[var(--maroon-pale)] text-[var(--maroon)] text-label"
              data-testid="action-error"
            >
              {errorMsg}
            </div>
          )}
        </React.Fragment>
      )}
    </Card>
  );
};

export default ActionCard;
