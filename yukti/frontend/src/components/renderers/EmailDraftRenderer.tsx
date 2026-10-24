'use client';

import React, { useState } from 'react';
import { ArtifactSpec, EmailDraftSpec, EmailRecipient } from '@/contracts/answerContract';
import { Mail, Paperclip, Download, FileText, ExternalLink, Edit3, Eye } from 'lucide-react';

export interface EmailDraftRendererProps {
  draft: EmailDraftSpec;
  artifacts?: ArtifactSpec[];
  isDark?: boolean;
}

function formatRecipients(list?: EmailRecipient[]): string {
  if (!list || list.length === 0) return '';
  return list
    .map((r) => (r.name && r.email ? `${r.name} <${r.email}>` : r.email || r.name))
    .filter(Boolean)
    .join(', ');
}

function parseRecipients(raw: string): EmailRecipient[] {
  return raw
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((part) => {
      const m = part.match(/^(.+?)\s*<([^>]+)>$/);
      if (m) return { name: m[1].trim(), email: m[2].trim() };
      return { name: part, email: part };
    });
}

export const EmailDraftRenderer: React.FC<EmailDraftRendererProps> = ({
  draft,
  artifacts = [],
}) => {
  const editable = draft.editable !== false;
  const [isEditing, setIsEditing] = useState(false);
  const [toText, setToText] = useState(() => formatRecipients(draft.to));
  const [ccText, setCcText] = useState(() => formatRecipients(draft.cc));
  const [subject, setSubject] = useState(() => draft.subject || '');
  const [bodyMd, setBodyMd] = useState(() => draft.body_md || '');
  const [busyFormat, setBusyFormat] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast(null), 5000);
  };

  // Resolve attachments against turn artifacts
  const resolvedAttachments: ArtifactSpec[] = (draft.attachments || []).map((att) => {
    if (typeof att === 'object' && att !== null) return att;
    const found = artifacts.find((a) => a.export_id === att || a.filename === att);
    return (
      found || {
        export_id: String(att),
        kind: 'xlsx',
        filename: String(att).endsWith('.xlsx') ? String(att) : `${att}.xlsx`,
        url: `/api/export/${encodeURIComponent(String(att))}`,
      }
    );
  });

  const handleExportDownload = async (format: 'eml' | 'docx') => {
    setBusyFormat(format);
    try {
      const currentDraft: EmailDraftSpec = {
        ...draft,
        to: parseRecipients(toText),
        cc: parseRecipients(ccText),
        subject,
        body_md: bodyMd,
      };
      const res = await fetch('/api/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          format,
          title: subject || 'Transfer_Review_Note',
          content: bodyMd,
          email_draft: currentDraft,
          attachments: resolvedAttachments.map((a) => a.export_id),
        }),
      });
      const j = await res.json();
      if (!res.ok) throw new Error(j?.message || `HTTP ${res.status}`);
      const dlUrl = j.url || (j.export_id ? `/api/export/${encodeURIComponent(j.export_id)}` : '');
      if (dlUrl) {
        const a = document.createElement('a');
        a.href = dlUrl;
        a.download = j.filename || `transfer_review.${format}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast(`Downloaded ${j.filename || format.toUpperCase()}`);
      }
    } catch (err: any) {
      showToast(`Download failed: ${err?.message || err}`);
    } finally {
      setBusyFormat(null);
    }
  };

  const handleMailto = () => {
    const toEmails = parseRecipients(toText)
      .map((r) => r.email)
      .filter(Boolean)
      .join(',');
    const ccEmails = parseRecipients(ccText)
      .map((r) => r.email)
      .filter(Boolean)
      .join(',');
    const note = '\n\n[Note: Please attach the downloaded Excel roster manually — mailto links cannot carry attachments.]';
    const maxBody = Math.max(200, 1800 - note.length - subject.length - toEmails.length - ccEmails.length);
    const truncatedBody = (bodyMd.length > maxBody ? bodyMd.slice(0, maxBody) + '…' : bodyMd) + note;
    const params = new URLSearchParams();
    if (ccEmails) params.set('cc', ccEmails);
    if (subject) params.set('subject', subject);
    params.set('body', truncatedBody);
    const href = `mailto:${encodeURIComponent(toEmails)}?${params.toString().replace(/\+/g, '%20')}`;
    if (typeof window !== 'undefined') {
      window.open(href, '_self');
    }
    showToast('Opened default mail client — attach the downloaded Excel file manually.');
  };

  const renderMarkdownPreview = (md: string) => {
    const lines = md.split('\n');
    const elements: React.ReactNode[] = [];
    let tableLines: string[] = [];
    let inTable = false;

    const renderInline = (text: string) => {
      const parts = text.split(/(\*\*.*?\*\*)/g);
      return parts.map((part, i) =>
        part.startsWith('**') && part.endsWith('**') ? (
          <strong key={i} className="font-semibold text-[var(--ink)]">
            {part.slice(2, -2)}
          </strong>
        ) : (
          part
        ),
      );
    };

    const flushTable = (key: number) => {
      if (tableLines.length >= 2) {
        const headers = tableLines[0]
          .split('|')
          .map((c) => c.trim())
          .filter(Boolean);
        const rows = tableLines
          .slice(2)
          .map((l) =>
            l
              .split('|')
              .map((c) => c.trim())
              .filter(Boolean),
          )
          .filter((r) => r.length > 0);
        elements.push(
          <div key={`tbl-${key}`} className="my-3 overflow-x-auto rounded-[var(--radius-sm)] border border-[var(--hairline)]">
            <table className="w-full text-left text-caption border-collapse" data-testid="email-draft-table">
              <thead className="bg-[var(--surface)]">
                <tr>
                  {headers.map((h, i) => (
                    <th key={i} className="py-2 px-3 font-semibold text-[var(--ink)] border-b border-[var(--hairline)]">
                      {renderInline(h)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r, ri) => (
                  <tr key={ri} className="border-b border-[var(--hairline)] last:border-b-0">
                    {r.map((cell, ci) => (
                      <td key={ci} className="py-1.5 px-3 text-[var(--ink-2)]">
                        {renderInline(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>,
        );
      }
      tableLines = [];
      inTable = false;
    };

    lines.forEach((line, idx) => {
      const t = line.trim();
      if (t.startsWith('|')) {
        inTable = true;
        tableLines.push(t);
        return;
      }
      if (inTable) flushTable(idx);
      if (!t) return;
      elements.push(
        <p key={idx} className="my-1.5 text-body text-[var(--ink)] leading-relaxed">
          {renderInline(t)}
        </p>,
      );
    });
    if (inTable) flushTable(lines.length);
    return elements;
  };

  return (
    <div
      data-testid="email-draft-renderer"
      className="card flex flex-col rounded-[var(--radius-lg)] border border-[var(--hairline)] bg-[var(--card)] overflow-hidden"
    >
      {/* Header bar */}
      <div className="bg-ongc-maroon text-white px-5 py-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <Mail className="w-4 h-4 shrink-0" aria-hidden />
          <div>
            <div className="text-caption uppercase tracking-wider opacity-85">Official Correspondence Draft (Unsent)</div>
            <div className="text-body font-semibold">{subject || 'Transfer Review Memorandum'}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {editable && (
            <button
              type="button"
              onClick={() => setIsEditing((e) => !e)}
              data-testid="email-draft-toggle-edit"
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-caption font-medium bg-white/15 hover:bg-white/25 text-white border border-white/25 transition-colors"
            >
              {isEditing ? <Eye className="w-3.5 h-3.5" /> : <Edit3 className="w-3.5 h-3.5" />}
              {isEditing ? 'Preview' : 'Edit fields'}
            </button>
          )}
        </div>
      </div>

      {/* Envelope metadata */}
      <div className="px-5 py-3.5 border-b border-[var(--hairline)] bg-[var(--surface)] space-y-2 text-caption">
        <div className="grid grid-cols-[4.5rem_1fr] items-center gap-2">
          <label htmlFor="email-draft-to" className="font-semibold text-[var(--ink-2)]">
            To:
          </label>
          {isEditing ? (
            <input
              id="email-draft-to"
              data-testid="email-draft-to-input"
              type="text"
              value={toText}
              onChange={(e) => setToText(e.target.value)}
              placeholder="Recipient name <email@ongc.co.in>"
              className="w-full px-2.5 py-1 rounded-[var(--radius-sm)] border border-[var(--hairline)] bg-[var(--card)] text-[var(--ink)]"
            />
          ) : (
            <span data-testid="email-draft-to" className="text-[var(--ink)] font-medium">
              {toText || '(Select recipient below)'}
            </span>
          )}
        </div>

        <div className="grid grid-cols-[4.5rem_1fr] items-center gap-2">
          <label htmlFor="email-draft-cc" className="font-semibold text-[var(--ink-2)]">
            Cc:
          </label>
          {isEditing ? (
            <input
              id="email-draft-cc"
              data-testid="email-draft-cc-input"
              type="text"
              value={ccText}
              onChange={(e) => setCcText(e.target.value)}
              placeholder="Optional CC addresses"
              className="w-full px-2.5 py-1 rounded-[var(--radius-sm)] border border-[var(--hairline)] bg-[var(--card)] text-[var(--ink)]"
            />
          ) : (
            <span data-testid="email-draft-cc" className="text-[var(--ink-2)]">
              {ccText || '—'}
            </span>
          )}
        </div>

        <div className="grid grid-cols-[4.5rem_1fr] items-center gap-2">
          <label htmlFor="email-draft-subject" className="font-semibold text-[var(--ink-2)]">
            Subject:
          </label>
          {isEditing ? (
            <input
              id="email-draft-subject"
              data-testid="email-draft-subject-input"
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full px-2.5 py-1 rounded-[var(--radius-sm)] border border-[var(--hairline)] bg-[var(--card)] text-[var(--ink)] font-medium"
            />
          ) : (
            <span data-testid="email-draft-subject" className="text-[var(--ink)] font-semibold">
              {subject}
            </span>
          )}
        </div>

        {resolvedAttachments.length > 0 && (
          <div className="grid grid-cols-[4.5rem_1fr] items-center gap-2 pt-1">
            <span className="font-semibold text-[var(--ink-2)]">Attached:</span>
            <div className="flex flex-wrap gap-2">
              {resolvedAttachments.map((att) => (
                <a
                  key={att.export_id}
                  href={att.url || `/api/export/${encodeURIComponent(att.export_id)}`}
                  download={att.filename}
                  data-testid="email-draft-attachment"
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-[var(--hairline)] bg-[var(--card)] text-[var(--accent-deep)] dark:text-[var(--accent-soft)] hover:bg-[var(--surface)] font-medium transition-colors"
                >
                  <Paperclip className="w-3.5 h-3.5" aria-hidden />
                  <span>{att.filename}</span>
                  {typeof att.rows === 'number' && <span className="text-[var(--ink-3)]">({att.rows} rows)</span>}
                </a>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Body */}
      <div className="px-5 py-4 flex-1 overflow-y-auto max-h-[28rem]">
        {isEditing ? (
          <textarea
            data-testid="email-draft-body-input"
            value={bodyMd}
            onChange={(e) => setBodyMd(e.target.value)}
            rows={12}
            className="w-full p-3 rounded-[var(--radius-sm)] border border-[var(--hairline)] bg-[var(--surface)] text-body text-[var(--ink)] font-mono leading-relaxed"
          />
        ) : (
          <div data-testid="email-draft-body">{renderMarkdownPreview(bodyMd)}</div>
        )}
      </div>

      {/* Footer & Action bar */}
      <div className="px-5 py-3 border-t border-[var(--hairline)] bg-[var(--surface)] flex flex-wrap items-center justify-between gap-3">
        <div className="text-caption text-[var(--ink-3)]" data-testid="email-draft-footer">
          {draft.footer || 'Data: synthetic employee records calibrated to ONGC AR FY26 (Illustrative)'}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void handleExportDownload('eml')}
            disabled={busyFormat !== null}
            data-testid="email-draft-download-eml"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-sm)] border border-[var(--hairline)] bg-[var(--card)] hover:bg-[var(--surface)] text-caption font-medium text-[var(--ink)] transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-[var(--accent-deep)] dark:text-[var(--accent-soft)]" aria-hidden />
            {busyFormat === 'eml' ? 'Preparing .eml…' : 'Download .eml'}
          </button>
          <button
            type="button"
            onClick={() => void handleExportDownload('docx')}
            disabled={busyFormat !== null}
            data-testid="email-draft-download-docx"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-sm)] border border-[var(--hairline)] bg-[var(--card)] hover:bg-[var(--surface)] text-caption font-medium text-[var(--ink)] transition-colors"
          >
            <FileText className="w-3.5 h-3.5 text-[var(--accent-deep)] dark:text-[var(--accent-soft)]" aria-hidden />
            {busyFormat === 'docx' ? 'Preparing .docx…' : 'Download .docx'}
          </button>
          <button
            type="button"
            onClick={handleMailto}
            data-testid="email-draft-mailto"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-sm)] border border-[var(--hairline)] bg-[var(--card)] hover:bg-[var(--surface)] text-caption font-medium text-[var(--ink)] transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5 text-[var(--accent-deep)] dark:text-[var(--accent-soft)]" aria-hidden />
            Open in Mail (mailto:)
          </button>
        </div>
      </div>

      {toast && (
        <div role="status" className="px-5 py-2 bg-[var(--ink)] text-[var(--canvas)] text-caption font-medium">
          {toast}
        </div>
      )}
    </div>
  );
};
