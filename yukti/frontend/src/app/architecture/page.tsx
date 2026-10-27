import type { Metadata } from 'next';
import Link from 'next/link';

/**
 * "How Yukti works" — the architecture page linked from the top bar (27-Oct).
 * Static content; keep it in step with docs/ARCHITECTURE.md and public/architecture/*.
 */
export const metadata: Metadata = {
  title: 'How Yukti works — Yukti AI architecture',
  description: 'Architecture of Yukti AI: one voice agent, a deterministic orchestrator, specialist modules and certified data.',
};

const AI_ROLES: { part: string; kind: string; decides: string; numbers: string }[] = [
  { part: 'Gemini Live', kind: 'AI agent — the only one', decides: 'Listens and speaks; decides when to call Yukti’s tools (ask_yukti, ui_control, control_screen)', numbers: 'Never — it reads out what the tools return' },
  { part: 'Turn orchestrator', kind: 'Code', decides: 'Which specialist handles the question, in a fixed order', numbers: 'No' },
  { part: 'Specialist modules', kind: 'Code, listed in an agent registry', decides: 'DCF valuation, finance diagnostics, HR transfers, exports, analyst queries', numbers: 'Yes — computed in code' },
  { part: 'Gemini 2.5 Flash', kind: 'AI, called like a function', decides: 'Turns a question into a structured query plan; writes the explanation', numbers: 'No — every figure it mentions is checked against the data' },
  { part: 'BigQuery', kind: 'Data', decides: 'ONGC HR and finance records, certified v3 datasets', numbers: 'Yes — the source of truth' },
  { part: 'Yahoo Finance', kind: 'External data', decides: 'Brent, WTI and the rupee against the dollar', numbers: 'Yes — cached daily history' },
];

const FLOW: { step: string; detail: string }[] = [
  { step: 'You ask', detail: 'By voice or text. Your signed role travels with every question.' },
  { step: 'Gemini Live hands over', detail: 'It does not answer from memory; it calls ask_yukti with your question.' },
  { step: 'The orchestrator routes', detail: 'In a fixed order: clarify the year or a screen command → DCF follow-up → specialist module → revenue drivers → oil and rupee → data query → small talk.' },
  { step: 'Numbers are computed', detail: 'Gemini 2.5 Flash writes a query plan, code compiles it to certified SQL, BigQuery returns the figures. DCF and market numbers come from their engines.' },
  { step: 'The answer is checked', detail: 'Role-based masking is applied, and any number in the explanation that is not in the data is rejected.' },
  { step: 'You see and hear it', detail: 'Charts, tables and KPI cards appear on screen; Gemini Live reads the grounded answer aloud.' },
];

const GUARDRAILS = [
  'Every number comes from BigQuery, the DCF engine or market data — never from the language model.',
  'The model plans the query; code writes the SQL.',
  'Your role is checked on every turn; restricted fields are masked.',
  'DCF runs only after you confirm the assumptions.',
  'The app sits behind Google sign-in (Identity-Aware Proxy); there is no public access.',
];

function H2({ children }: { children: React.ReactNode }) {
  return <h2 className="font-display text-[1.2rem] font-bold text-[var(--ink)] mt-10 mb-3">{children}</h2>;
}

export default function ArchitecturePage() {
  return (
    <main className="min-h-screen bg-[var(--canvas)] text-[var(--ink-2)]">
      <div className="max-w-[1180px] mx-auto px-6 py-8">
        <div className="flex items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/brand/ongc_logo.png" alt="ONGC" className="w-12 h-12 rounded-[var(--radius-sm)] object-cover" />
            <div>
              <div className="font-display font-bold text-[1.4rem] text-[var(--brand-red)] leading-none">How Yukti works</div>
              <div className="text-[0.85rem] text-[var(--ink-3)] mt-1">Yukti AI Agent · HR and Finance · architecture</div>
            </div>
          </div>
          <Link href="/" className="text-[0.85rem] font-semibold text-[var(--accent-deep)] hover:underline">
            ← Back to Yukti
          </Link>
        </div>

        <p className="text-[1.05rem] text-[var(--ink)] leading-relaxed">
          <strong>Yukti is one voice agent backed by a deterministic, tool-driven engine.</strong> Gemini Live talks with you; code
          decides which specialist answers; every number comes from ONGC’s certified data or a calculation engine, never from the
          language model.
        </p>

        <a href="/architecture/yukti_architecture.svg" target="_blank" rel="noreferrer" className="block mt-6" title="Open full size">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/architecture/yukti_architecture.png"
            alt="Yukti AI architecture: users, Identity-Aware Proxy, Cloud Run with web app, turn orchestrator and specialist modules, Gemini Live, Gemini 2.5 Flash, BigQuery and Yahoo Finance"
            className="w-full rounded-[var(--radius-md)] border border-[var(--hairline)] shadow-[var(--card-shadow)]"
          />
        </a>
        <div className="text-[0.78rem] text-[var(--ink-3)] mt-2">Click the diagram to open it full size.</div>

        <H2>Where AI is used — and where it is not</H2>
        <div className="overflow-x-auto rounded-[var(--radius-md)] border border-[var(--hairline)] bg-[var(--card)]">
          <table className="w-full text-[0.88rem]">
            <thead className="bg-[var(--surface)] text-left text-[var(--ink)]">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Part</th>
                <th className="px-4 py-2.5 font-semibold">What it is</th>
                <th className="px-4 py-2.5 font-semibold">What it decides</th>
                <th className="px-4 py-2.5 font-semibold">Produces numbers?</th>
              </tr>
            </thead>
            <tbody>
              {AI_ROLES.map((r) => (
                <tr key={r.part} className="border-t border-[var(--hairline)] align-top">
                  <td className="px-4 py-2.5 font-semibold text-[var(--ink)] whitespace-nowrap">{r.part}</td>
                  <td className="px-4 py-2.5">{r.kind}</td>
                  <td className="px-4 py-2.5">{r.decides}</td>
                  <td className="px-4 py-2.5">{r.numbers}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <H2>How one question flows</H2>
        <ol className="grid gap-3 md:grid-cols-2">
          {FLOW.map((f, i) => (
            <li key={f.step} className="flex gap-3 rounded-[var(--radius-md)] border border-[var(--hairline)] bg-[var(--card)] p-4">
              <span className="shrink-0 w-7 h-7 rounded-full grid place-items-center bg-[var(--accent-pale)] text-[var(--accent-deep)] font-bold text-[0.85rem]">
                {i + 1}
              </span>
              <div>
                <div className="font-semibold text-[var(--ink)]">{f.step}</div>
                <div className="text-[0.88rem] mt-0.5">{f.detail}</div>
              </div>
            </li>
          ))}
        </ol>

        <H2>Single agent or multi-agent?</H2>
        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-[var(--radius-md)] border border-[var(--hairline)] bg-[var(--card)] p-4">
            <div className="font-semibold text-[var(--ink)]">Today: one agent, specialist modules</div>
            <p className="text-[0.88rem] mt-1">
              The specialists — DCF valuation, finance diagnostics, HR transfers, document export and the analyst — are listed in an
              agent registry with their triggers, allowed roles and confirmation rules. Each one runs code, not its own language
              model. That keeps every answer repeatable and auditable.
            </p>
          </div>
          <div className="rounded-[var(--radius-md)] border border-[var(--hairline)] bg-[var(--card)] p-4">
            <div className="font-semibold text-[var(--ink)]">Ready for: specialist AI agents</div>
            <p className="text-[0.88rem] mt-1">
              A registry entry is just “name → handler, triggers, roles”. A handler can be swapped for a true AI sub-agent — for
              example one that explains an on-screen chart — without changing the orchestrator, the role checks or the data
              guardrails.
            </p>
          </div>
        </div>

        <H2>Guardrails</H2>
        <ul className="list-disc pl-5 space-y-1.5 text-[0.92rem]">
          {GUARDRAILS.map((g) => (
            <li key={g}>{g}</li>
          ))}
        </ul>

        <H2>Platform</H2>
        <p className="text-[0.92rem]">
          Google Cloud project <code>ongc-hr-finance-agent</code>, region asia-south1. One Cloud Run service runs the Next.js web
          app and the FastAPI backend in a single container, behind Identity-Aware Proxy. Releases are built with Cloud Build,
          rolled out with no traffic first, then switched over, with one-step rollback.
        </p>

        <div className="mt-12 pt-4 border-t border-[var(--hairline)] text-[0.78rem] text-[var(--ink-3)]">
          Yukti AI · ONGC HR and Finance · architecture as of 27 October 2026
        </div>
      </div>
    </main>
  );
}
