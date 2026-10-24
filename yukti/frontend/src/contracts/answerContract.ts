/**
 * Yukti AI Answer Contract TypeScript Definitions
 * Directly reflects yukti/contracts/answer_contract.schema.json
 */

export type PersonaType =
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

export type VisualType = 'chart' | 'table' | 'kpi' | 'clause' | 'document' | 'map' | 'refusal' | 'none';

export type VisualMode = 'replace' | 'refine' | 'compare' | 'restore';

export type ChartKind =
  | 'pie'
  | 'donut'
  | 'bar'
  | 'hbar'
  | 'column'
  | 'stacked_bar'
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
  min_role?: PersonaType;
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

export interface VisualContainer {
  type: VisualType;
  mode: VisualMode;
  title?: string;
  chart?: ChartSpec;
  table?: TableSpec;
  kpis?: KpiTile[];
  clause?: ClauseSpec;
  document?: DocumentSpec;
  map?: MapSpec;
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
  /** P2H.2 G4 M4: the same permitted question in Hindi (asked when the conversation is in Hindi) */
  question_hi?: string;
  label_hi?: string;
}

export interface AccessControl {
  status: AccessStatus;
  reason?: string;
  rule_ref?: string;
  /** refusal code (R-NAMED, R-PAY, R-ROLE, …) */
  code?: string;
  alternative?: RefusalAlternative | string | null;
  alternatives?: RefusalAlternative[];
  self_emp_id?: string | null;
  allow_pay_aggregate?: boolean;
}

export type ExportOption = 'sheets' | 'docs' | 'word' | 'pdf' | 'xlsx';

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
  /** P0.3 (SPEC-11 §7.1, additive): where the answer's data really came from. */
  provenance?: { label: string; detail?: string; snapshot_date?: string | null };
  /** P0.3: data path of a planner answer; `sql` is null when no SQL ran (local snapshot). */
  status?: { source: 'bigquery' | 'local_snapshot' | string; sql?: string | null };
  /** v2 (U2.1); absent = 1. All v2 fields are optional. */
  contract_version?: 1 | 2;
  insights_v2?: InsightV2[];
  drilldowns?: Drilldown[];
  context_chips?: ContextChip[];
  query_spec?: QuerySpec;
  /** optional screen command bundled with the answer (e.g. chart_kind) */
  ui_action?: { action?: string; command?: string; value?: string };
}
