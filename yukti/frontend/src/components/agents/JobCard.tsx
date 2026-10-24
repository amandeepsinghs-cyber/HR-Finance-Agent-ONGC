'use client';

/**
 * Live background job progress card driven by SSE + polling fallback (Packet P3.6a, SPEC-03 §7, BEH-05.02 / .07).
 * Uses only design tokens (`var(--...)`) — zero hardcoded hex colours.
 */
import React, { useEffect, useState } from 'react';
import type { AnswerContract, JobSpec, JobStepSpec } from '@/contracts/answerContract';
import { cancelJob, subscribeJobEvents } from '@/lib/jobsClient';
import { Badge, Card, Chip } from '@/components/ui/primitives';
import { AlertTriangle, CheckCircle2, Circle, Clock, Download, Loader2, RotateCcw, Square } from 'lucide-react';

export interface JobCardProps {
  initialJob: JobSpec;
  sessionId?: string;
  onJobCompleted?: (result: AnswerContract, finalJob: JobSpec) => void;
  onRetry?: () => void;
}

const AGENT_LABELS: Record<string, string> = {
  dcf_agent: 'DCF Valuation Agent · v1.0',
  hr_transfer_agent: 'HR Transfer Pack Agent · v1.0',
  fin_diagnostics_agent: 'Finance Diagnostics Agent · v1.0',
  doc_export_agent: 'Document Export Agent · v1.0',
};

const StepIcon: React.FC<{ status: JobStepSpec['status'] }> = ({ status }) => {
  switch (status) {
    case 'done':
      return <CheckCircle2 className="w-4 h-4 text-[var(--accent)] shrink-0" aria-label="completed" />;
    case 'running':
      return <Loader2 className="w-4 h-4 text-[var(--accent-deep)] dark:text-[var(--accent-soft)] animate-spin shrink-0" aria-label="running" />;
    case 'failed':
      return <AlertTriangle className="w-4 h-4 text-[var(--maroon)] shrink-0" aria-label="failed" />;
    default:
      return <Circle className="w-4 h-4 text-[var(--ink-3)] shrink-0" aria-label="pending" />;
  }
};

export const JobCard: React.FC<JobCardProps> = ({
  initialJob,
  sessionId,
  onJobCompleted,
  onRetry,
}) => {
  const [job, setJob] = useState<JobSpec>(initialJob);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    setJob(initialJob);
  }, [initialJob]);

  useEffect(() => {
    if (job.status !== 'queued' && job.status !== 'running') return;
    const unsubscribe = subscribeJobEvents(
      job.id,
      {
        onUpdate: (next) => setJob((prev) => ({ ...prev, ...next })),
        onCompleted: (finalJob, result) => {
          setJob((prev) => ({ ...prev, ...finalJob, status: 'succeeded', progress: 1 }));
          if (result && onJobCompleted) {
            onJobCompleted(result, finalJob);
          }
        },
        onFailed: (finalJob) => setJob((prev) => ({ ...prev, ...finalJob })),
        onCancelled: (finalJob) => setJob((prev) => ({ ...prev, ...finalJob, status: 'cancelled' })),
      },
      sessionId,
    );
    return unsubscribe;
  }, [job.id, job.status, onJobCompleted, sessionId]);

  const handleCancel = async () => {
    if (cancelling || (job.status !== 'queued' && job.status !== 'running')) return;
    setCancelling(true);
    try {
      const updated = await cancelJob(job.id);
      setJob((prev) => ({ ...prev, ...updated, status: 'cancelled', artifacts: [] }));
    } catch {
      setJob((prev) => ({ ...prev, status: 'cancelled', artifacts: [] }));
    } finally {
      setCancelling(false);
    }
  };

  const pct = Math.max(0, Math.min(100, Math.round((job.progress ?? 0) * 100)));
  const isRunning = job.status === 'queued' || job.status === 'running';
  const agentTitle = AGENT_LABELS[job.agent] || job.agent;

  return (
    <Card
      className="p-4 max-w-[54rem] space-y-3.5"
      data-testid="job-card"
      data-job-id={job.id}
      data-job-status={job.status}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          {isRunning ? (
            <Loader2 className="w-4 h-4 text-[var(--accent)] animate-spin shrink-0" aria-hidden />
          ) : job.status === 'succeeded' ? (
            <CheckCircle2 className="w-4 h-4 text-[var(--accent)] shrink-0" aria-hidden />
          ) : (
            <Clock className="w-4 h-4 text-[var(--ink-3)] shrink-0" aria-hidden />
          )}
          <span className="text-label font-semibold text-[var(--ink)]" data-testid="job-agent-title">
            {agentTitle}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Badge
            tone={
              job.status === 'succeeded'
                ? 'positive'
                : job.status === 'failed' || job.status === 'expired'
                  ? 'critical'
                  : job.status === 'cancelled'
                    ? 'neutral'
                    : 'warning'
            }
            data-testid="job-status-badge"
          >
            {job.status} · {pct}%
          </Badge>
          {isRunning && (
            <Chip
              type="button"
              onClick={handleCancel}
              disabled={cancelling}
              className="!py-1"
              data-testid="job-cancel"
            >
              <Square className="w-3 h-3" aria-hidden />
              Cancel
            </Chip>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div
        className="w-full h-2 rounded-full bg-[var(--surface)] overflow-hidden"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        data-testid="job-progress-bar"
      >
        <div
          className="h-full bg-[var(--accent)] transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Ordered step list */}
      {job.steps && job.steps.length > 0 && (
        <ol className="grid gap-1.5 sm:grid-cols-2 pt-1" data-testid="job-steps">
          {job.steps.map((step) => (
            <li
              key={step.id}
              className="flex items-center gap-2 text-caption text-[var(--ink-2)]"
              data-testid={`job-step-${step.id}`}
              data-step-status={step.status}
            >
              <StepIcon status={step.status} />
              <span className={step.status === 'running' ? 'font-medium text-[var(--ink)]' : ''}>
                {step.label}
              </span>
            </li>
          ))}
        </ol>
      )}

      {job.status === 'cancelled' && (
        <div className="text-label text-[var(--ink-2)]" data-testid="job-cancelled">
          Cancelled at step boundary. No artifacts were generated.
        </div>
      )}

      {(job.status === 'failed' || job.status === 'expired') && (
        <div
          role="alert"
          className="p-3 rounded-[var(--radius-md)] bg-[var(--maroon-pale)] text-[var(--maroon)] flex flex-wrap items-center justify-between gap-2 text-label"
          data-testid="job-failed"
        >
          <span>
            {job.error?.code === 'E_INSTANCE_LOST'
              ? 'Background worker restarted before completion. Please run again.'
              : job.error?.message || 'Background job failed. Please run again.'}
          </span>
          {onRetry && (
            <Chip type="button" onClick={onRetry} data-testid="job-retry">
              <RotateCcw className="w-3.5 h-3.5" aria-hidden />
              Run again
            </Chip>
          )}
        </div>
      )}

      {job.status === 'succeeded' && job.artifacts && job.artifacts.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-[var(--hairline)]" data-testid="job-artifacts">
          {job.artifacts.map((art) => (
            <a
              key={art.export_id}
              href={art.url || `/api/export/${encodeURIComponent(art.export_id)}`}
              download={art.filename}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-pill border border-[var(--hairline)] bg-[var(--surface)] text-label font-medium text-[var(--ink)] hover:border-[var(--accent)]"
              data-testid="job-artifact-link"
            >
              <Download className="w-3.5 h-3.5 text-[var(--accent-deep)] dark:text-[var(--accent-soft)]" aria-hidden />
              <span>{art.filename}</span>
            </a>
          ))}
        </div>
      )}
    </Card>
  );
};

export default JobCard;
