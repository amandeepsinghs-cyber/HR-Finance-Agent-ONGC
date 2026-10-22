/**
 * Yukti AI Answer Contract TypeScript Definitions
 * Directly reflects yukti/contracts/answer_contract.schema.json
 */

export type PersonaType = 'CMD' | 'DIR_HR' | 'DIR_FIN' | 'E2_HR' | 'E3_FIN';

export type LanguageType = 'en' | 'hi' | 'hi-en';

export type VisualType = 'chart' | 'table' | 'kpi' | 'clause' | 'document' | 'map' | 'refusal' | 'none';

export type VisualMode = 'replace' | 'refine' | 'compare' | 'restore';

export type ChartKind =
  | 'pie'
  | 'donut'
  | 'bar'
  | 'hbar'
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
}

export interface TableSpec {
  columns: string[];
  rows: (Record<string, any> | (string | number | boolean | null)[])[];
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

export interface AccessControl {
  status: AccessStatus;
  reason?: string;
  rule_ref?: string;
  alternative?: string;
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
}
