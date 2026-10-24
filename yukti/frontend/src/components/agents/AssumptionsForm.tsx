'use client';

/**
 * Inline assumptions editor for a proposed agent action (Packet P3.6a, SPEC-03 §6.1 / §6.3, BEH-05.04 / BEH-05.09).
 * Uses only design tokens (`var(--...)`) — zero hardcoded hex colours.
 */
import React, { useMemo, useState } from 'react';
import type { EditableInputSpec } from '@/contracts/answerContract';
import { Badge, Chip } from '@/components/ui/primitives';
import { AlertCircle, Check, RotateCcw, X } from 'lucide-react';

export interface AssumptionsFormProps {
  inputs: EditableInputSpec[];
  initialOverrides?: Record<string, unknown>;
  submitting?: boolean;
  serverError?: string | null;
  onSubmit: (overrides: Record<string, unknown>) => void;
  onCancel: () => void;
}

export const AssumptionsForm: React.FC<AssumptionsFormProps> = ({
  inputs,
  initialOverrides,
  submitting = false,
  serverError,
  onSubmit,
  onCancel,
}) => {
  const [values, setValues] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const item of inputs) {
      const v = initialOverrides && item.key in initialOverrides ? initialOverrides[item.key] : item.value;
      init[item.key] = v === undefined || v === null ? '' : String(v);
    }
    return init;
  });

  const { errors, changedKeys, parsedOverrides } = useMemo(() => {
    const errs: Record<string, string> = {};
    const changed = new Set<string>();
    const overrides: Record<string, unknown> = {};

    for (const item of inputs) {
      const raw = (values[item.key] ?? '').trim();
      const baseStr = item.value === undefined || item.value === null ? '' : String(item.value);

      if (item.type === 'number' || item.type === 'percent') {
        const num = Number(raw);
        if (raw === '' || Number.isNaN(num)) {
          errs[item.key] = `${item.label} must be a valid number`;
          continue;
        }
        if (item.min !== undefined && num < item.min) {
          errs[item.key] = `${item.label} must be at least ${item.min}${item.unit ? ` ${item.unit}` : ''}`;
        } else if (item.max !== undefined && num > item.max) {
          errs[item.key] = `${item.label} must be at most ${item.max}${item.unit ? ` ${item.unit}` : ''}`;
        }
        if (Number(baseStr) !== num) {
          changed.add(item.key);
          overrides[item.key] = num;
        }
      } else if (item.type === 'enum' && item.options?.length) {
        const opts = item.options.map((o) => String(o));
        if (!opts.includes(raw)) {
          errs[item.key] = `${item.label} must be one of: ${opts.join(', ')}`;
        } else if (raw !== baseStr) {
          changed.add(item.key);
          overrides[item.key] = raw;
        }
      } else {
        if (!raw) {
          errs[item.key] = `${item.label} is required`;
        } else if (raw !== baseStr) {
          changed.add(item.key);
          overrides[item.key] = raw;
        }
      }
    }

    // SPEC-02 §8 / BEH-05.09 E_TV_GUARD: WACC must exceed terminal growth by at least 1 percentage point
    const waccRaw = values.wacc_pct;
    const gRaw = values.terminal_g_pct;
    if (waccRaw !== undefined && gRaw !== undefined) {
      const waccNum = Number(waccRaw);
      const gNum = Number(gRaw);
      if (!Number.isNaN(waccNum) && !Number.isNaN(gNum) && waccNum - gNum < 1.0) {
        errs._tv_guard = 'WACC must exceed growth by at least 1 point';
      }
    }

    return { errors: errs, changedKeys: changed, parsedOverrides: overrides };
  }, [inputs, values]);

  const hasErrors = Object.keys(errors).length > 0;

  const handleReset = () => {
    const reset: Record<string, string> = {};
    for (const item of inputs) {
      reset[item.key] = item.value === undefined || item.value === null ? '' : String(item.value);
    }
    setValues(reset);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (hasErrors || submitting) return;
    onSubmit(parsedOverrides);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="mt-3 p-4 rounded-[var(--radius-lg)] border border-[var(--hairline)] bg-[var(--surface)] space-y-3.5"
      data-testid="assumptions-form"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="text-label font-semibold text-[var(--ink)]">
          Edit Valuation Assumptions
        </div>
        {changedKeys.size > 0 && (
          <button
            type="button"
            onClick={handleReset}
            className="inline-flex items-center gap-1 text-caption text-[var(--ink-2)] hover:text-[var(--ink)]"
            data-testid="assumptions-reset"
          >
            <RotateCcw className="w-3.5 h-3.5" aria-hidden /> Reset to SSOT defaults
          </button>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {inputs.map((item) => {
          const isEdited = changedKeys.has(item.key);
          const fieldErr = errors[item.key];
          const inputId = `assumption-input-${item.key}`;
          return (
            <div
              key={item.key}
              className={`p-3 rounded-[var(--radius-md)] border transition-colors ${
                fieldErr
                  ? 'border-[var(--maroon)] bg-[var(--maroon-pale)]/20'
                  : isEdited
                    ? 'border-[var(--accent)] bg-[var(--card)]'
                    : 'border-[var(--hairline)] bg-[var(--card)]'
              }`}
              data-testid={`assumption-field-${item.key}`}
              data-edited={isEdited ? 'true' : 'false'}
            >
              <div className="flex items-center justify-between gap-2 mb-1">
                <label htmlFor={inputId} className="text-label font-medium text-[var(--ink)]">
                  {item.label}
                  {item.unit ? <span className="ml-1 text-caption text-[var(--ink-3)]">({item.unit})</span> : null}
                </label>
                {isEdited && (
                  <Badge tone="warning" data-testid={`assumption-edited-badge-${item.key}`}>
                    edited by you
                  </Badge>
                )}
              </div>

              {item.type === 'enum' && item.options?.length ? (
                <select
                  id={inputId}
                  value={values[item.key] ?? ''}
                  onChange={(e) => setValues((prev) => ({ ...prev, [item.key]: e.target.value }))}
                  className="w-full px-2.5 py-1.5 rounded-[var(--radius-sm)] border border-[var(--hairline)] bg-[var(--surface)] text-body text-[var(--ink)]"
                  data-testid={`assumption-input-${item.key}`}
                >
                  {item.options.map((opt) => (
                    <option key={String(opt)} value={String(opt)}>
                      {String(opt)}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  id={inputId}
                  type={item.type === 'number' || item.type === 'percent' ? 'number' : 'text'}
                  step={item.step ?? 'any'}
                  value={values[item.key] ?? ''}
                  onChange={(e) => setValues((prev) => ({ ...prev, [item.key]: e.target.value }))}
                  className="w-full px-2.5 py-1.5 rounded-[var(--radius-sm)] border border-[var(--hairline)] bg-[var(--surface)] text-body font-mono tabular-nums text-[var(--ink)]"
                  data-testid={`assumption-input-${item.key}`}
                />
              )}

              <div className="mt-1 flex items-center justify-between gap-2 text-caption text-[var(--ink-3)]">
                <span>
                  {item.min !== undefined && item.max !== undefined
                    ? `Range: ${item.min}–${item.max}${item.unit ? ` ${item.unit}` : ''}`
                    : 'Default'}
                </span>
                {item.source && <span className="truncate">{item.source}</span>}
              </div>

              {fieldErr && (
                <div
                  role="alert"
                  className="mt-1.5 flex items-center gap-1 text-caption text-[var(--maroon)] font-medium"
                  data-testid={`assumption-error-${item.key}`}
                >
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" aria-hidden />
                  <span>{fieldErr}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {(errors._tv_guard || serverError) && (
        <div
          role="alert"
          className="p-2.5 rounded-[var(--radius-sm)] bg-[var(--maroon-pale)] text-[var(--maroon)] text-label flex items-center gap-2"
          data-testid="assumptions-guard-error"
        >
          <AlertCircle className="w-4 h-4 shrink-0" aria-hidden />
          <span>{errors._tv_guard || serverError}</span>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2.5 pt-1">
        <Chip
          type="submit"
          selected
          disabled={hasErrors || submitting}
          data-testid="assumptions-submit"
        >
          <Check className="w-3.5 h-3.5" aria-hidden />
          Run with these
        </Chip>
        <Chip type="button" onClick={onCancel} disabled={submitting} data-testid="assumptions-cancel">
          <X className="w-3.5 h-3.5" aria-hidden />
          Back
        </Chip>
      </div>
    </form>
  );
};

export default AssumptionsForm;
