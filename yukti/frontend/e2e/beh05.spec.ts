/**
 * Playwright E2E + integration verification for Packet P3.6a (SPEC-03 §6, §7.1, §9; BEH-05.01, .02, .04, .07, .10).
 * Run with: npx playwright test e2e/beh05.spec.ts
 */
import { test, expect } from 'playwright/test';
import React from 'react';
import ReactDOMServer from 'react-dom/server';
import { ActionCard } from '../src/components/agents/ActionCard';
import { AssumptionsForm } from '../src/components/agents/AssumptionsForm';
import { JobCard } from '../src/components/agents/JobCard';
import { AnswerCard } from '../src/components/AnswerCard';
import { feedReducer, rehydrateJobsForSession, Turn } from '../src/state/feed';
import type { AnswerContract, JobSpec, ProposedActionSpec } from '../src/contracts/answerContract';

// Bridge Playwright's JSX transform ({ __pw_type: 'jsx', type, props, key }) to React elements
const REACT_ELEMENT_TYPE = Symbol.for('react.element');
const REACT_FRAGMENT_TYPE = Symbol.for('react.fragment');
Object.defineProperty(Object.prototype, '$$typeof', {
  configurable: true,
  get() {
    if (this && typeof this === 'object' && (this as Record<string, unknown>).__pw_type === 'jsx') {
      const el = this as Record<string, unknown>;
      if (
        el.type &&
        typeof el.type === 'object' &&
        !Object.prototype.hasOwnProperty.call(el.type, '$$typeof')
      ) {
        el.type = REACT_FRAGMENT_TYPE;
      }
      return REACT_ELEMENT_TYPE;
    }
    return undefined;
  },
  set(v) {
    Object.defineProperty(this, '$$typeof', {
      value: v,
      writable: true,
      configurable: true,
      enumerable: true,
    });
  },
});

const PROPOSAL_FIXTURE: ProposedActionSpec = {
  id: 'pa_beh05_001',
  agent: 'dcf_agent',
  summary:
    "Can I run the DCF valuation agent in the background to estimate ONGC's intrinsic value? It takes about 15 seconds.",
  inputs: {
    wacc_pct: 11.42,
    terminal_g_pct: 3.0,
    brent_usd: 78.0,
    capex_scale_pct: 100,
    production_decline_pct: -1.2,
    holdco_discount_pct: 0,
    as_of: '2026-10-19',
  },
  editable_inputs: [
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
  ],
  est_seconds: 15,
  requires_role: ['CMD', 'DIR_FIN'],
  buttons: ['run', 'edit', 'cancel'],
  voice_confirm_hint: 'Say yes, run it, or cancel.',
  expires_at: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
};

const RUNNING_JOB_FIXTURE: JobSpec = {
  id: 'job_beh05_001',
  agent: 'dcf_agent',
  status: 'running',
  progress: 0.375,
  steps: [
    { id: 'load_inputs', label: 'Load verified SSOT snapshot', status: 'done' },
    { id: 'wacc_build', label: 'Compute CAPM WACC', status: 'done' },
    { id: 'forecast', label: 'Project 10-year FCFF (FY27–FY36)', status: 'running' },
    { id: 'valuation', label: 'Terminal value & EV bridge', status: 'pending' },
    { id: 'sensitivity_grid', label: '9×9 WACC × g sensitivity grid', status: 'pending' },
    { id: 'tornado', label: '8-driver tornado chart', status: 'pending' },
    { id: 'xlsx', label: 'Write 6-sheet Excel workbook', status: 'pending' },
    { id: 'publish', label: 'Publish result turn', status: 'pending' },
  ],
  artifacts: [],
  error: null,
};

const DCF_RESULT_CONTRACT: AnswerContract = {
  contract_version: 3,
  turn_id: 'job:job_beh05_001',
  language: 'en',
  persona: 'DIR_FIN',
  spoken_summary:
    'The DCF valuation is ready. Intrinsic value is ₹312.4 per share against a market price of ₹272.3, so the model suggests ONGC is undervalued by 14.7%. This is an illustrative valuation, not investment advice.',
  display_text:
    'ONGC Standalone DCF valuation complete: intrinsic value ₹312.4/sh vs market price ₹272.3/sh (+14.7% upside). Illustrative valuation, not investment advice.',
  visual: {
    type: 'dcf_model',
    mode: 'replace',
    title: 'ONGC Standalone DCF Valuation (FY27–FY36)',
    dcf_model: {
      run_id: 'dcf_beh05_001',
      engine_version: '3.0.0',
      as_of: '2026-10-19',
      scope: 'standalone',
      per_share: {
        intrinsic_inr: 312.4,
        market_inr: 272.3,
        market_date: '2026-03-31',
        upside_pct: 14.73,
        verdict: 'undervalued (+14.7%)',
      },
      wacc_build: {
        rf_used_pct: 6.82,
        beta_adj: 0.94,
        erp_total_pct: 6.9,
        ke_pct: 13.31,
        kd_used_pct: 5.57,
        tax_rate_pct: 25.17,
        weight_equity: 0.76,
        wacc_pct: 11.42,
      },
      forecast: {
        years: ['FY27', 'FY28', 'FY29', 'FY30', 'FY31', 'FY32', 'FY33', 'FY34', 'FY35', 'FY36'],
        lines: {
          fcff: [28500, 29400, 30300, 31200, 32100, 33000, 33900, 34800, 35700, 36600],
          discount_factor: [0.897, 0.805, 0.723, 0.649, 0.582, 0.523, 0.469, 0.421, 0.378, 0.339],
          pv_fcff: [25578, 23681, 21903, 20242, 18691, 17245, 15899, 14650, 13487, 12411],
        },
      },
      terminal: {
        method: 'gordon',
        g_pct: 3.0,
        tv_inr_cr: 420588.6,
        pv_tv_inr_cr: 142621.6,
      },
      bridge: [
        { label: 'PV of FCFF', value_inr_cr: 183793.1, type: 'total' },
        { label: 'PV of Terminal Value', value_inr_cr: 142621.6, type: 'delta' },
        { label: 'Implied Equity Value', value_inr_cr: 393015.0, type: 'total' },
      ],
      sensitivity_grid: {
        row_input: { name: 'WACC', unit: '%', values: [10.42, 11.42, 12.42] },
        col_input: { name: 'Terminal g', unit: '%', values: [2.0, 3.0, 4.0] },
        output: { name: 'Value per share', unit: 'INR' },
        cells: [
          [338.1, 367.0, 405.6],
          [304.4, 312.4, 354.2],
          [277.8, 294.7, null],
        ],
        base: { row_idx: 1, col_idx: 1 },
      },
      tornado: {
        output: { name: 'Intrinsic value per share', unit: 'INR', base: 312.4 },
        bars: [
          {
            driver: 'Brent crude (±$10/bbl)',
            low_input: '$68/bbl',
            high_input: '$88/bbl',
            low_inr: 268.2,
            high_inr: 356.6,
          },
        ],
      },
      disclaimer: 'Illustrative valuation, not investment advice.',
    },
  },
  sources: [{ kind: 'data', object: 'v_fin_statement_line', title: 'ONGC Audited AR FY17–FY26' }],
  access: { status: 'allowed' },
  export_options: ['xlsx', 'pdf'],
  caveat: 'Illustrative valuation, not investment advice.',
  provenance: { label: 'illustrative', detail: 'Audited AR FY17–FY26 + DCF Engine' },
  job: {
    ...RUNNING_JOB_FIXTURE,
    status: 'succeeded',
    progress: 1.0,
    artifacts: [
      {
        export_id: 'exp_dcf_beh05_001',
        kind: 'xlsx',
        filename: 'ONGC_DCF_dcf_beh05_001.xlsx',
        url: '/api/export/exp_dcf_beh05_001',
      },
    ],
  },
};

test.describe('P3.6a Permission UX (BEH-05.01, .02, .04, .07, .10)', () => {
  test('BEH-05.01: Proposal renders ActionCard with Run, Edit assumptions, Cancel, inputs table, and expiry state', async () => {
    const proposalContract: AnswerContract = {
      contract_version: 3,
      turn_id: 'turn_beh05_01',
      language: 'en',
      persona: 'DIR_FIN',
      spoken_summary: PROPOSAL_FIXTURE.summary,
      display_text: PROPOSAL_FIXTURE.summary,
      visual: { type: 'none', mode: 'replace' },
      sources: [],
      access: { status: 'allowed' },
      proposed_action: PROPOSAL_FIXTURE,
    };

    const html = ReactDOMServer.renderToStaticMarkup(
      React.createElement(AnswerCard, { contract: proposalContract, isLatest: true }),
    );
    expect(html).toContain('data-testid="action-card"');
    expect(html).toContain('data-testid="action-run"');
    expect(html).toContain('data-testid="action-edit"');
    expect(html).toContain('data-testid="action-cancel"');
    expect(html).toContain('fact_wacc_annual FY26');
    expect(html).toContain('~15s');
    expect(html).toContain('Say yes, run it, or cancel.');

    // Expired proposal greys out and displays "This proposal expired. Ask again."
    const expiredHtml = ReactDOMServer.renderToStaticMarkup(
      React.createElement(ActionCard, {
        proposedAction: {
          ...PROPOSAL_FIXTURE,
          expires_at: new Date(Date.now() - 60_000).toISOString(),
        },
      }),
    );
    expect(expiredHtml).toContain('data-testid="action-expired"');
    expect(expiredHtml).toContain('This proposal expired. Ask again.');
    expect(expiredHtml).not.toContain('data-testid="action-run"');
  });

  test('BEH-05.02: Confirming Run shows JobCard with ordered steps, progress bar, and appends result turn with xlsx link', async () => {
    const jobHtml = ReactDOMServer.renderToStaticMarkup(
      React.createElement(JobCard, { initialJob: RUNNING_JOB_FIXTURE }),
    );
    expect(jobHtml).toContain('data-testid="job-card"');
    expect(jobHtml).toContain('data-testid="job-progress-bar"');
    expect(jobHtml).toContain('aria-valuenow="38"');
    expect(jobHtml).toContain('data-testid="job-step-load_inputs"');
    expect(jobHtml).toContain('data-testid="job-step-forecast"');
    expect(jobHtml).toContain('data-testid="job-cancel"');

    // Completed job appends turn_id = job:<id> via feedReducer and renders DCF model + xlsx link
    let turns: Turn[] = [];
    turns = feedReducer(turns, {
      type: 'job_result',
      job: DCF_RESULT_CONTRACT.job!,
      result: DCF_RESULT_CONTRACT,
    });
    expect(turns).toHaveLength(1);
    expect(turns[0].id).toBe('job:job_beh05_001');
    expect(turns[0].contract?.visual?.type).toBe('dcf_model');

    const resultHtml = ReactDOMServer.renderToStaticMarkup(
      React.createElement(AnswerCard, { contract: turns[0].contract!, isLatest: true }),
    );
    expect(resultHtml).toContain('data-testid="dcf-model-view"');
    expect(resultHtml).toContain('₹312.4');
    expect(resultHtml).toContain('₹272.3');
    expect(resultHtml).toContain('+14.7%');
    expect(resultHtml).toContain('ONGC_DCF_dcf_beh05_001.xlsx');
    expect(resultHtml).toContain('Illustrative valuation, not investment advice.');
  });

  test('BEH-05.04: Edit assumptions highlights changed values and validates min/max and WACC - g >= 1pp guard', async () => {
    // Valid override (WACC=11.0%, g=2.5%) highlights both fields as "edited by you"
    const editedHtml = ReactDOMServer.renderToStaticMarkup(
      React.createElement(AssumptionsForm, {
        inputs: PROPOSAL_FIXTURE.editable_inputs!,
        initialOverrides: { wacc_pct: 11.0, terminal_g_pct: 2.5 },
        onSubmit: () => {},
        onCancel: () => {},
      }),
    );
    expect(editedHtml).toContain('data-testid="assumption-edited-badge-wacc_pct"');
    expect(editedHtml).toContain('data-testid="assumption-edited-badge-terminal_g_pct"');
    expect(editedHtml).toContain('edited by you');
    expect(editedHtml).not.toContain('data-testid="assumptions-guard-error"');

    // Out-of-range input (g = 7% > max 6%) shows inline field validation error and disables submit
    const outOfRangeHtml = ReactDOMServer.renderToStaticMarkup(
      React.createElement(AssumptionsForm, {
        inputs: PROPOSAL_FIXTURE.editable_inputs!,
        initialOverrides: { terminal_g_pct: 7.0 },
        onSubmit: () => {},
        onCancel: () => {},
      }),
    );
    expect(outOfRangeHtml).toContain('data-testid="assumption-error-terminal_g_pct"');
    expect(outOfRangeHtml).toContain('must be at most 6 %');

    // Terminal value guard (WACC 6.0%, g 5.5% -> WACC - g < 1pp) shows E_TV_GUARD message
    const tvGuardHtml = ReactDOMServer.renderToStaticMarkup(
      React.createElement(AssumptionsForm, {
        inputs: PROPOSAL_FIXTURE.editable_inputs!,
        initialOverrides: { wacc_pct: 6.0, terminal_g_pct: 5.5 },
        onSubmit: () => {},
        onCancel: () => {},
      }),
    );
    expect(tvGuardHtml).toContain('data-testid="assumptions-guard-error"');
    expect(tvGuardHtml).toContain('WACC must exceed growth by at least 1 point');
  });

  test('BEH-05.07: Cancelled job renders cancelled status with zero artifacts', async () => {
    const cancelledJob: JobSpec = {
      ...RUNNING_JOB_FIXTURE,
      status: 'cancelled',
      artifacts: [],
    };
    const html = ReactDOMServer.renderToStaticMarkup(
      React.createElement(JobCard, { initialJob: cancelledJob }),
    );
    expect(html).toContain('data-job-status="cancelled"');
    expect(html).toContain('data-testid="job-cancelled"');
    expect(html).not.toContain('data-testid="job-artifact-link"');
    expect(html).not.toContain('data-testid="job-cancel"');
  });

  test('BEH-05.10: Feed rehydration via GET /api/jobs?session_id= restores running and completed jobs without duplicates', async () => {
    const origFetch = globalThis.fetch;
    try {
      globalThis.fetch = (async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes('/api/jobs?session_id=sess_rehydrate_01')) {
          return new Response(
            JSON.stringify({
              jobs: [
                {
                  ...RUNNING_JOB_FIXTURE,
                  status: 'succeeded',
                  progress: 1.0,
                  result: DCF_RESULT_CONTRACT,
                },
              ],
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          );
        }
        return new Response('{}', { status: 404 });
      }) as typeof fetch;

      let state: Turn[] = [];
      await rehydrateJobsForSession('sess_rehydrate_01', (action) => {
        state = feedReducer(state, action);
      });
      expect(state).toHaveLength(1);
      expect(state[0].id).toBe('job:job_beh05_001');
      expect(state[0].contract?.visual?.dcf_model?.per_share.intrinsic_inr).toBe(312.4);

      // Second rehydration is idempotent (no duplicate turns)
      await rehydrateJobsForSession('sess_rehydrate_01', (action) => {
        state = feedReducer(state, action);
      });
      expect(state).toHaveLength(1);
    } finally {
      globalThis.fetch = origFetch;
    }
  });
});
