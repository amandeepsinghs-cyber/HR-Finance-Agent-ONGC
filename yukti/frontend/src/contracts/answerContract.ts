/**
 * Yukti AI Answer Contract TypeScript Definitions
 * Directly reflects yukti/contracts/answer_contract.schema.json (v1, v2, v3)
 */

export type PersonaType = 'CMD' | 'DIR_HR' | 'DIR_FIN' | 'E2_HR' | 'E3_FIN';

export type PersonaV3Type =
  | 'CMD'
  | 'DIR_HR'
  | 'DIR_FIN'
  | 'E1_HR'
  | 'E2_HR'
  | 'E3_HR'
  | 'E4_HR'
  | 'E1_FIN'
  | 'E2_FIN'
  | 'E3_FIN'
  | 'E4_FIN';

export type LanguageType = 'en' | 'hi' | 'hi-en';

export type VisualType =
  | 'chart'
  | 'table'
  | 'statement'
  | 'sensitivity_grid'
  | 'tornado'
  | 'dcf_model'
  | 'actions'
  | 'kpi'
  | 'clause'
  | 'document'
  | 'email_draft'
  | 'map'
  | 'refusal'
  | 'none';

export type VisualMode = 'replace' | 'refine' | 'compare' | 'restore';

export type ChartKind =
  | 'pie'
  | 'donut'
  | 'bar'
  | 'hbar'
  | 'column'
  | 'stacked_bar'
  | 'stacked_100'
  | 'grouped_bar'
  | 'line'
  | 'area'
  | 'combo'
  | 'histogram'
  | 'box'
  | 'treemap'
  | 'heatmap'
  | 'waterfall'
  | 'bullet'
  | 'gauge'
  | 'funnel'
  | 'scatter'
  | 'bubble'
  | 'sunburst'
  | 'sankey'
  | 'kpi'
  | 'table'
  | 'map';

export interface ChartAnnotation {
  x: any;
  label: string;
}

export interface ChartSpec {
  kind: ChartKind;
  data: Record<string, any>[];
  x?: string;
  y?: string;
  series?: string;
  value?: string;
  category?: string;
  unit?: string;
  sort?: 'asc' | 'desc' | 'none';
  top_n?: number;
  annotations?: ChartAnnotation[];
  target?: number;
  /** rows are already buckets/bins: a histogram draws them as-is (U5.7) */
  prebinned?: boolean;
  /** P2H.3 (SPEC-07 §4.1): 'explicit' = rows arrive in their meaningful order (e.g. grade_level_order); never re-sort */
  x_order?: 'explicit' | 'auto';
  /** P2H.3: one-time explanatory note (shown once per session per text) */
  note?: string;
  /** P2H.3: footnote under the chart (e.g. board levels excluded from the axis) */
  footnote?: string;
}

export interface TableMasking {
  level: 'none' | 'partial' | 'aggregate' | 'refused';
  code?: string;
  masked_columns?: string[];
  reason?: string;
  rule_ref?: string;
}

export interface RowAction {
  id: string;
  label: string;
  action?: 'draft_transfer_note' | 'open_profile' | 'add_to_watchlist' | 'ask';
  /** e.g. 'Draft a transfer note for {emp_name}' */
  question_template?: string;
  min_role?: PersonaV3Type;
}

export interface TableSpec {
  columns: string[];
  rows: (Record<string, any> | (string | number | boolean | null)[])[];
  /** v2 (U2.1) */
  masking?: TableMasking;
  total_rows?: number;
  row_actions?: RowAction[];
  /** P2H.3 (SPEC-07 §4.3): header text per column key (falls back to humanizeKey) */
  column_labels?: Record<string, string>;
  /** P2H.3: present in rows but hidden by default; CMD / DIR_HR can reveal them with the column picker */
  hidden_columns?: string[];
  /** P2H.3: initial sort, e.g. { key: 'delhi_tenure_years', dir: 'desc' } */
  default_sort?: { key: string; dir: 'asc' | 'desc' };
  /** P2H.3: data as-of date (ISO), stated under the table */
  as_of?: string;
}

export interface KpiTile {
  label: string;
  value: number | string;
  unit?: string;
  delta?: string;
}

export interface ClauseSpec {
  doc_id?: string;
  doc_title?: string;
  clause_ref?: string;
  text?: string;
  highlight?: string;
  /** P0.7 (D-35): "real" = text from a public document on disk; anything else renders as Illustrative. */
  provenance?: 'real' | 'illustrative';
}

export interface DocumentSpec {
  doc_type?: string;
  title?: string;
  markdown?: string;
  template_id?: string;
  version?: number;
}

export interface EmailRecipient {
  name: string;
  email: string;
  role?: string;
}

export interface ArtifactSpec {
  export_id: string;
  kind: 'xlsx' | 'csv' | 'pdf' | 'png' | 'svg' | 'docx' | 'eml';
  filename: string;
  url: string;
  rows?: number;
  columns?: string[];
  masked?: boolean;
  created_at?: string;
  expires_at?: string;
  sha256?: string;
}

export interface EmailDraftSpec {
  to: EmailRecipient[];
  cc?: EmailRecipient[];
  from?: EmailRecipient;
  subject: string;
  body_md: string;
  attachments?: (string | ArtifactSpec)[];
  citations?: string[];
  editable?: boolean;
  footer?: string;
}

export interface MapPoint {
  wc_id?: string;
  name: string;
  lat: number;
  lon: number;
  value?: number;
  metricLabel?: string;
  status?: string;
}

export interface MapSpec {
  points: MapPoint[];
}

export interface CompareItem {
  label: string;
  chart?: ChartSpec;
  kpis?: KpiTile[];
  filter?: QueryFilter;
}

export interface CompareSpec {
  items: CompareItem[];
  metric?: string;
  shared_axis?: boolean;
}

// ---------- P4.2 (SPEC-09 §4.1, FEAT-025): financial statement visual ----------
export type StatementKind = 'pnl' | 'balance_sheet' | 'cash_flow';

export interface StatementRow {
  line_code?: string;
  label: string;
  /** 0–3; indent = level × 16 px */
  level?: number;
  kind?: 'line' | 'subtotal' | 'total';
  is_total?: boolean;
  is_subtotal?: boolean;
  indent?: number;
  /** period → value or ordered array; null/absent renders "—" (never 0) */
  values?: Record<string, number | null> | (number | null)[];
  amount_cr?: number | null;
  prior_cr?: number | null;
  yoy_pct?: number | null;
  note_ref?: string | null;
  source?: { doc: string; page?: number | null };
  is_restated?: boolean;
}

export interface StatementSection {
  id?: string;
  label?: string;
  title?: string;
  rows?: StatementRow[];
  lines?: StatementRow[];
}

export interface StatementSpec {
  statement: StatementKind;
  scope?: 'standalone' | 'consolidated';
  title?: string;
  unit?: string;
  period?: string;
  prior_period?: string | null;
  /** latest first */
  periods?: string[];
  period_labels?: Record<string, string>;
  show_yoy?: boolean;
  sections: StatementSection[];
  totals_check?: { identity?: string; passed?: boolean; ok?: boolean; max_abs_delta_cr?: number; diff_cr?: number };
  source?: { primary?: string; basis?: string; extraction?: string; verified?: boolean };
  source_footer?: string;
  as_of?: string;
  footnotes?: string[];
  synthetic?: boolean;
}

// ---------- P4.5 B1 (SPEC-09 §5, field names identical to SPEC-02 engine output) ----------
export interface SensitivityAxis {
  name: string;
  unit: string;
  values: number[];
}

export interface SensitivityGridSpec {
  row_input: SensitivityAxis;
  col_input: SensitivityAxis;
  output: { name: string; unit: string };
  /** cells[row][col]; null = not meaningful (SPEC-02 §8: WACC − g < 1pp) → rendered "n/m" */
  cells: (number | null)[][];
  base: { row_idx: number; col_idx: number };
  source?: string;
}

export interface TornadoBarSpec {
  driver: string;
  low_input: string;
  high_input: string;
  low_inr: number;
  high_inr: number;
}

export interface TornadoSpec {
  output: { name: string; unit: string; base: number };
  bars: TornadoBarSpec[];
  source?: string;
}

// ---------- P2F.6 / P4.5 B2: SPEC-08 §7.3 top-5 actions ----------
export interface ActionImpact {
  low?: number;
  mid?: number;
  high?: number;
  unit?: 'INR_cr';
  kind?: 'one_off' | 'annual';
  label?: 'Modelled estimate';
  formula_id?: string;
}

export interface ActionItem {
  rank: number;
  lever_id?: string;
  id?: string;
  title: string;
  what_to_do: string;
  impact?: ActionImpact;
  quantified_impact?: ActionImpact;
  /** absent for E1–E4 personas ("for discussion", SPEC-08 §7.4) */
  owner?: 'CMD' | 'DIR_FIN' | 'DIR_HR' | string | null;
  horizon_days?: 30 | 90 | 180 | number | null;
  kpi: string;
  evidence: ({ type: 'data' | 'ar'; ref: string } | Record<string, any>)[];
  confidence?: 'high' | 'medium' | number;
}

export interface DelegationRow {
  owner?: string;
  ask?: string;
  action?: string;
  by_when?: string;
  horizon?: string;
  kpi?: string;
  evidence?: string;
}

export interface ActionsSpec {
  fy: string;
  items?: ActionItem[];
  actions?: ActionItem[];
  delegation_table: DelegationRow[];
  persona_mode?: 'board_delegation' | 'for_discussion';
}

// ---------- P3.1 / P4.5 (SPEC-02 §9.1, SPEC-09 §5): DCF valuation composite ----------
export interface DcfBridgeRow {
  label: string;
  value_inr_cr: number;
  type?: 'delta' | 'total';
  source?: string;
}

export interface DcfPerShare {
  intrinsic_inr: number;
  market_inr: number;
  market_date?: string;
  upside_pct: number;
  /** Verdict text comes from the contract only — never hardcoded in the UI */
  verdict: string;
}

export interface DcfTerminalSummary {
  method: 'gordon' | 'exit_multiple';
  g_pct: number;
  tv_inr_cr: number;
  pv_tv_inr_cr: number;
  exit_multiple?: number;
  tv_exit_inr_cr?: number;
  implied_g_pct?: number;
  implied_multiple?: number;
  warning?: string | null;
}

export interface DcfWaccBuild {
  rf_used_pct: number;
  beta_adj: number;
  erp_total_pct: number;
  ke_pct: number;
  kd_pretax_pct?: number;
  kd_used_pct: number;
  tax_rate_pct: number;
  weight_equity: number;
  weight_debt?: number;
  wacc_pct: number;
}

export interface DcfForecastSpec {
  years: string[];
  lines: {
    revenue?: number[];
    ebit?: number[];
    fcff: number[];
    discount_factor: number[];
    pv_fcff: number[];
  };
}

export interface DcfModelSpec {
  run_id: string;
  engine_version?: string;
  as_of: string;
  scope?: string;
  per_share: DcfPerShare;
  wacc_build: DcfWaccBuild;
  forecast: DcfForecastSpec;
  terminal: DcfTerminalSummary;
  bridge: DcfBridgeRow[];
  sensitivity_grid: SensitivityGridSpec;
  tornado: TornadoSpec;
  fcff_statement?: StatementSpec;
  wacc_statement?: StatementSpec;
  provenance_label?: string;
  /** Required caption from contract: "Illustrative valuation, not investment advice." */
  disclaimer: string;
}

// ---------- P2F.1: year / slot clarification (SPEC-08 §3.2) ----------
export interface ClarifyOption {
  label: string;
  value: string;
  spoken?: string;
}

export interface ClarifySpec {
  slot?: 'fiscal_period' | 'statement' | 'scope' | 'entity';
  question: string;
  options: ClarifyOption[];
  pending_spec?: Record<string, unknown>;
  pending_intent?: Record<string, unknown>;
  expires_after_turns?: number;
}

// ---------- P3.1 (SPEC-03 §5.2): proposed_action, editable_input, job, provenance ----------
export type AgentKind =
  | 'dcf_agent'
  | 'hr_transfer_agent'
  | 'fin_diagnostics_agent'
  | 'doc_export_agent';

export interface EditableInputSpec {
  key: string;
  label: string;
  type: 'number' | 'percent' | 'enum' | 'fy';
  value: unknown;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  options?: unknown[];
  source?: string;
}

export interface ProposedActionSpec {
  id: string;
  agent: AgentKind;
  summary: string;
  inputs: Record<string, unknown>;
  editable_inputs?: EditableInputSpec[];
  est_seconds: number;
  requires_role: PersonaV3Type[];
  buttons?: ('run' | 'edit' | 'cancel')[];
  voice_confirm_hint?: string;
  expires_at: string;
}

export interface JobStepSpec {
  id: string;
  label: string;
  status: 'pending' | 'running' | 'done' | 'failed' | 'skipped';
  started_at?: string | null;
  ended_at?: string | null;
}

export type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled' | 'expired';

export interface JobSpec {
  id: string;
  agent: string;
  status: JobStatus;
  progress: number;
  steps?: JobStepSpec[];
  result_ref?: string | null;
  artifacts?: ArtifactSpec[];
  error?: { code?: string; message?: string } | null;
  created_at?: string | null;
  finished_at?: string | null;
}

export type ProvenanceLabel =
  | 'verified_ar'
  | 'verified_xbrl'
  | 'yahoo_consolidated'
  | 'derived_ar'
  | 'modelled'
  | 'illustrative'
  | 'synthetic'
  | 'local_snapshot'
  | 'mixed';

export interface ProvenanceSpec {
  label: ProvenanceLabel | string;
  detail?: string;
  snapshot_date?: string | null;
  components?: { label?: string; share_of_rows?: number }[];
}

export interface VisualContainer {
  type: VisualType;
  mode: VisualMode;
  title?: string;
  chart?: ChartSpec;
  table?: TableSpec;
  kpis?: KpiTile[];
  clause?: ClauseSpec;
  document?: DocumentSpec;
  email_draft?: EmailDraftSpec;
  map?: MapSpec;
  /** P4.2: financial statement (type = 'statement') */
  statement?: StatementSpec;
  /** P4.5: typed finance visuals (type = 'sensitivity_grid' | 'tornado') */
  sensitivity_grid?: SensitivityGridSpec;
  tornado?: TornadoSpec;
  /** P2F.6 / P4.5 B2: SPEC-08 §7.3 (type = 'actions') */
  actions?: ActionsSpec;
  /** P3.1 / P4.5: SPEC-02 §9.1 / SPEC-09 §5 (type = 'dcf_model') */
  dcf_model?: DcfModelSpec;
  /** P2H.2: refusal metadata mirrored on the visual */
  code?: string;
  rule_ref?: string;
  alternative?: RefusalAlternative | string | null;
  alternatives?: RefusalAlternative[];
  auto_answer_turn_id?: string | null;
  /** v2 (U2.1): side-by-side comparison when mode = 'compare' */
  compare?: CompareSpec;
  /** UI-only (U5.7): the answer's original rows, kept so repeated re-plots never drift */
  source?: { columns?: string[]; rows?: unknown[] };
  /** UI-only (U5.7): one-line note explaining a re-plot transform or fallback */
  replot_note?: string;
}

// ---------- Contract v2 (U2.1): frozen, versioned query description ----------
export type FilterOp = '=' | '!=' | '>' | '>=' | '<' | '<=' | 'in' | 'not_in' | 'between' | 'like';

export interface QueryFilter {
  field: string;
  op: FilterOp;
  value?: unknown;
}

export interface QueryPeriod {
  fy?: string;
  from?: string;
  to?: string;
  grain?: 'year' | 'quarter' | 'month' | 'day';
}

export interface QuerySpec {
  version: 1;
  domain?: 'hr' | 'finance' | 'policy';
  metric: string;
  aggregation?: 'count' | 'sum' | 'avg' | 'min' | 'max' | 'distinct_count' | 'ratio';
  dimensions?: string[];
  filters?: QueryFilter[];
  period?: QueryPeriod;
  grain?: 'aggregate' | 'row';
  sort?: { by?: string; dir?: 'asc' | 'desc' };
  limit?: number;
}

/** Partial query_spec merged onto the current one (refine in place). */
export interface SpecPatch {
  add_filters?: QueryFilter[];
  remove_filters?: string[];
  dimensions?: string[];
  period?: QueryPeriod;
  grain?: 'aggregate' | 'row';
  sort?: { by?: string; dir?: 'asc' | 'desc' };
  limit?: number;
  chart_kind?: ChartKind;
  metric?: string;
  aggregation?: QuerySpec['aggregation'];
  /** split the current answer into side-by-side entities */
  compare?: { field: string; values: unknown[] };
}

export interface InsightV2 {
  text: string;
  kind?: 'headline' | 'trend' | 'outlier' | 'risk' | 'comparison' | 'note';
  value?: number | string;
  unit?: string;
  /** row/category the insight refers to (for highlight) */
  ref?: string;
}

export interface Drilldown {
  label: string;
  question?: string;
  spec_patch?: SpecPatch;
}

export interface ContextChip {
  label: string;
  kind?: 'role' | 'subject' | 'population' | 'period' | 'source' | 'filter';
}

export type SourceKind = 'data' | 'policy' | 'document';

export interface SourceCitation {
  kind: SourceKind;
  object?: string;
  query_id?: string;
  sql?: string;
  doc_id?: string;
  clause?: string;
  title?: string;
}

export type AccessStatus = 'allowed' | 'partial' | 'refused';

/** P2H.2 (SPEC-06 §4.6): a permitted alternative offered with a refusal. */
export interface RefusalAlternative {
  label: string;
  question: string;
  question_hi?: string;
  label_hi?: string;
}

export interface AccessControl {
  status: AccessStatus;
  reason?: string;
  rule_ref?: string;
  /** refusal code (R-NAMED, R-PAY, R-ROLE, …) */
  code?: string;
  alternative?: string;
  alternatives?: RefusalAlternative[];
  self_emp_id?: string | null;
  allow_pay_aggregate?: boolean;
}

export type ExportOption = 'sheets' | 'docs' | 'word' | 'pdf' | 'xlsx' | 'csv' | 'png' | 'svg' | 'docx' | 'eml';

export interface AnswerContract {
  turn_id: string;
  language: LanguageType;
  persona?: PersonaType;
  spoken_summary: string;
  display_text: string;
  visual?: VisualContainer;
  insights?: string[];
  caveat?: string;
  sources: SourceCitation[];
  suggestions?: string[];
  access: AccessControl;
  export_options?: ExportOption[];
  status_events?: string[];
  /** P0.3 / P3.1 (SPEC-11 §7.1): where the answer's data really came from. */
  provenance?: ProvenanceSpec;
  /** P2F.1 (SPEC-08 §3.2, ledger row `clarify`): ask one question with 2–6 options before answering */
  clarify?: ClarifySpec;
  /** P2F.6 (SPEC-08 §7.3, ledger row `actions`): top-level mirror of visual.actions */
  actions?: ActionsSpec;
  /** P2H.4 / P4.6 (SPEC-10 §5, ledger row `artifacts`): exported files attached to this turn */
  artifacts?: ArtifactSpec[];
  /** P2H.4 (SPEC-07 §4.5, ledger row `email_draft`): top-level mirror of visual.email_draft */
  email_draft?: EmailDraftSpec;
  /** P3.1 (SPEC-03 §5.2, ledger row `proposed_action`): permission gate before running a heavy agent */
  proposed_action?: ProposedActionSpec | null;
  /** P3.1 (SPEC-03 §5.2, ledger row `job`): async agent job handle and progress */
  job?: JobSpec | null;
  /** P0.3: data path of a planner answer; `sql` is null when no SQL ran (local snapshot). */
  status?: { source: 'bigquery' | 'local_snapshot' | string; sql?: string | null };
  /** v3 (P3.1); absent = 1. All v2/v3 fields are optional. */
  contract_version?: 1 | 2 | 3;
  insights_v2?: InsightV2[];
  drilldowns?: Drilldown[];
  context_chips?: ContextChip[];
  query_spec?: QuerySpec;
  definition_id?: string | null;
  /** optional screen command bundled with the answer (e.g. chart_kind, download) */
  ui_action?: {
    type?: 'chart_kind' | 'panel_mode' | 'theme' | 'download' | 'export' | 'set_persona' | string;
    action?: string;
    command?: string;
    value?: string;
    url?: string;
    filename?: string;
    export_id?: string;
    format?: string;
  };
}
