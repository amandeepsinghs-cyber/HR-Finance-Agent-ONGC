-- =============================================================================
-- Yukti v3 Financial SSOT BigQuery DDL (SPEC-01 §5–§7, Packet P1.6)
-- Project: ongc-hr-finance-agent
-- Datasets: hrfin_bronze, hrfin_gold
-- Additive only: creates new v3 tables and views; never modifies or drops existing
-- ssot_corporate_* tables.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS `ongc-hr-finance-agent.hrfin_bronze`
  OPTIONS(location = "asia-south1", description = "Yukti v3 Financial SSOT Bronze landing tables");

CREATE SCHEMA IF NOT EXISTS `ongc-hr-finance-agent.hrfin_gold`
  OPTIONS(location = "asia-south1", description = "Yukti v3 Financial SSOT Verified Gold tables and views");

-- -----------------------------------------------------------------------------
-- 1. Bronze: raw extractions across AR 10-yr, AR statements/notes, and XBRL
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `ongc-hr-finance-agent.hrfin_bronze.fin_extract_raw` (
  extract_id STRING NOT NULL,
  source_system STRING NOT NULL,
  source_doc STRING NOT NULL,
  source_page INT64,
  source_page_label STRING,
  source_text_line INT64,
  raw_label STRING NOT NULL,
  raw_value_text STRING NOT NULL,
  parsed_value FLOAT64,
  unit STRING NOT NULL,
  column_header STRING,
  scope STRING,
  statement_guess STRING,
  extractor_version STRING NOT NULL,
  extracted_at STRING NOT NULL
)
CLUSTER BY source_system, source_doc;

-- -----------------------------------------------------------------------------
-- 2. Gold: dim_financial_line (SPEC-01 §5.2, 21 columns)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `ongc-hr-finance-agent.hrfin_gold.dim_financial_line` (
  line_code STRING NOT NULL,
  line_name STRING NOT NULL,
  line_name_aliases STRING,
  statement STRING NOT NULL,
  section STRING NOT NULL,
  subsection STRING,
  parent_line_code STRING,
  hierarchy_level INT64 NOT NULL,
  display_order INT64 NOT NULL,
  line_class STRING NOT NULL,
  natural_sign STRING NOT NULL,
  unit_default STRING NOT NULL,
  is_subtotal BOOL NOT NULL,
  is_total BOOL NOT NULL,
  is_kpi BOOL NOT NULL,
  formula STRING,
  ind_as_schedule_iii_ref STRING,
  ar_note_ref_typical STRING,
  xbrl_element_name STRING,
  yahoo_field_name STRING,
  description STRING NOT NULL
)
CLUSTER BY statement, section;

-- -----------------------------------------------------------------------------
-- 3. Gold: fact_financial_statement_line (SPEC-01 §5.1)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `ongc-hr-finance-agent.hrfin_gold.fact_financial_statement_line` (
  fiscal_year STRING NOT NULL,
  period_type STRING NOT NULL,
  period_end DATE NOT NULL,
  scope STRING NOT NULL,
  statement STRING NOT NULL,
  line_code STRING NOT NULL,
  line_name_as_reported STRING NOT NULL,
  value_native FLOAT64,
  unit_native STRING NOT NULL,
  value_inr_cr FLOAT64,
  value FLOAT64,
  unit STRING NOT NULL,
  precision_inr_cr FLOAT64,
  is_restated BOOL NOT NULL,
  raw_is_restated BOOL NOT NULL,
  is_own_vintage BOOL NOT NULL,
  is_latest_vintage BOOL NOT NULL,
  is_nil BOOL NOT NULL,
  sign_convention STRING NOT NULL,
  source_system STRING NOT NULL,
  report_vintage STRING NOT NULL,
  source_doc STRING NOT NULL,
  source_page INT64,
  source_page_label STRING,
  source_table STRING NOT NULL,
  raw_label STRING NOT NULL,
  raw_value_text STRING NOT NULL,
  extraction_method STRING NOT NULL,
  verified BOOL NOT NULL,
  verified_rule_ids ARRAY<STRING>,
  failed_rule_ids ARRAY<STRING>,
  cross_check_source STRING,
  cross_check_value FLOAT64,
  cross_check_delta_inr_cr FLOAT64,
  notes STRING,
  verification_notes STRING,
  v01_subtotal_ok BOOL,
  v02_no_plugs_ok BOOL,
  v03_bs_identity BOOL,
  v04_cash_tie BOOL,
  v05_pnl_chain BOOL,
  v06_note_tie BOOL,
  v07_prior_year_match BOOL,
  v08_ten_year_match BOOL,
  v09_ten_year_editions BOOL,
  v10_xbrl_match BOOL,
  v11_scope_sanity BOOL,
  v12_coverage_ok BOOL
)
PARTITION BY period_end
CLUSTER BY scope, statement, fiscal_year, line_code;

-- -----------------------------------------------------------------------------
-- 4. Gold: Conflict & Restatement Audit Table (SPEC-01 §6.3)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `ongc-hr-finance-agent.hrfin_gold.fact_financial_line_conflict` (
  fiscal_year STRING NOT NULL,
  scope STRING NOT NULL,
  line_code STRING NOT NULL,
  source_a STRING NOT NULL,
  value_a FLOAT64,
  source_b STRING NOT NULL,
  value_b FLOAT64,
  delta_inr_cr FLOAT64,
  rule_id STRING NOT NULL,
  status STRING NOT NULL,
  resolution STRING,
  resolved_by STRING,
  resolved_at STRING
)
CLUSTER BY fiscal_year, scope, line_code;

-- -----------------------------------------------------------------------------
-- 5. Gold: Gate Run Audit Table (Packet P1.6 §4)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `ongc-hr-finance-agent.hrfin_gold.fin_gate_run` (
  run_id STRING NOT NULL,
  run_at STRING NOT NULL,
  gate_id STRING NOT NULL,
  gate_name STRING NOT NULL,
  rows_checked INT64 NOT NULL,
  rows_passed INT64 NOT NULL,
  rows_failed INT64 NOT NULL,
  max_delta_inr_cr FLOAT64,
  examples STRING
);

-- -----------------------------------------------------------------------------
-- 6. Gold: Anchor Tables (P1.7 / SPEC-01 §5.3)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `ongc-hr-finance-agent.hrfin_gold.fact_segment` (
  fiscal_year STRING NOT NULL,
  scope STRING NOT NULL,
  segment_code STRING NOT NULL,
  segment_name STRING NOT NULL,
  metric_code STRING NOT NULL,
  value_inr_cr FLOAT64,
  unit STRING NOT NULL,
  report_vintage STRING NOT NULL,
  source_doc STRING NOT NULL,
  source_page INT64,
  verified BOOL NOT NULL
);

CREATE TABLE IF NOT EXISTS `ongc-hr-finance-agent.hrfin_gold.fact_production_annual` (
  fiscal_year STRING NOT NULL,
  product STRING NOT NULL,
  operator_scope STRING NOT NULL,
  region STRING,
  volume FLOAT64,
  unit STRING NOT NULL,
  report_vintage STRING NOT NULL,
  source_doc STRING NOT NULL,
  source_page INT64,
  verified BOOL NOT NULL
);

CREATE TABLE IF NOT EXISTS `ongc-hr-finance-agent.hrfin_gold.fact_reserves` (
  fiscal_year STRING NOT NULL,
  reserve_category STRING NOT NULL,
  operator_scope STRING NOT NULL,
  product STRING NOT NULL,
  volume FLOAT64,
  unit STRING NOT NULL,
  report_vintage STRING NOT NULL,
  source_doc STRING NOT NULL,
  source_page INT64,
  verified BOOL NOT NULL
);

CREATE TABLE IF NOT EXISTS `ongc-hr-finance-agent.hrfin_gold.fact_hr_aggregates` (
  fiscal_year STRING NOT NULL,
  metric_code STRING NOT NULL,
  category STRING,
  value FLOAT64,
  unit STRING NOT NULL,
  report_vintage STRING NOT NULL,
  source_doc STRING NOT NULL,
  source_page INT64,
  verified BOOL NOT NULL
);

CREATE TABLE IF NOT EXISTS `ongc-hr-finance-agent.hrfin_gold.fact_price_realisation` (
  fiscal_year STRING NOT NULL,
  product STRING NOT NULL,
  regime STRING,
  operator_scope STRING,
  price FLOAT64,
  unit STRING NOT NULL,
  report_vintage STRING NOT NULL,
  source_doc STRING NOT NULL,
  source_page INT64,
  verified BOOL NOT NULL
);

-- -----------------------------------------------------------------------------
-- 7. Serving Views (SPEC-01 §7, Packet P1.6 §4)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW `ongc-hr-finance-agent.hrfin_gold.v_fin_statement_as_reported` AS
SELECT
  f.*,
  d.line_name,
  d.section,
  d.subsection,
  d.parent_line_code,
  d.hierarchy_level,
  d.display_order,
  d.line_class,
  d.natural_sign,
  d.unit_default,
  d.is_subtotal,
  d.is_total,
  d.is_kpi,
  d.formula,
  d.ar_note_ref_typical,
  d.xbrl_element_name,
  d.yahoo_field_name
FROM `ongc-hr-finance-agent.hrfin_gold.fact_financial_statement_line` f
JOIN `ongc-hr-finance-agent.hrfin_gold.dim_financial_line` d
  USING (line_code)
WHERE f.verified = TRUE
  AND f.is_own_vintage = TRUE;

CREATE OR REPLACE VIEW `ongc-hr-finance-agent.hrfin_gold.v_fin_trend_latest` AS
SELECT
  f.*,
  d.line_name,
  d.section,
  d.subsection,
  d.parent_line_code,
  d.hierarchy_level,
  d.display_order,
  d.line_class,
  d.natural_sign,
  d.unit_default,
  d.is_subtotal,
  d.is_total,
  d.is_kpi,
  d.formula,
  d.ar_note_ref_typical,
  d.xbrl_element_name,
  d.yahoo_field_name,
  CASE
    WHEN f.is_restated THEN CONCAT(f.fiscal_year, ' restated in ', f.report_vintage)
    ELSE NULL
  END AS footnote_marker
FROM `ongc-hr-finance-agent.hrfin_gold.fact_financial_statement_line` f
JOIN `ongc-hr-finance-agent.hrfin_gold.dim_financial_line` d
  USING (line_code)
WHERE f.verified = TRUE
  AND f.is_latest_vintage = TRUE;

CREATE OR REPLACE VIEW `ongc-hr-finance-agent.hrfin_gold.v_fin_yahoo_view` AS
SELECT
  f.fiscal_year,
  f.period_type,
  f.period_end,
  f.scope,
  f.statement,
  f.line_code,
  d.line_name,
  d.yahoo_field_name,
  f.value_inr_cr,
  f.value,
  f.unit,
  f.report_vintage,
  f.source_doc,
  f.source_page
FROM `ongc-hr-finance-agent.hrfin_gold.fact_financial_statement_line` f
JOIN `ongc-hr-finance-agent.hrfin_gold.dim_financial_line` d
  USING (line_code)
WHERE f.verified = TRUE
  AND f.is_latest_vintage = TRUE
  AND d.yahoo_field_name IS NOT NULL;

CREATE OR REPLACE VIEW `ongc-hr-finance-agent.hrfin_gold.v_fin_coverage` AS
SELECT
  f.fiscal_year,
  f.scope,
  f.statement,
  f.source_system,
  COUNT(*) AS total_lines,
  COUNTIF(f.verified) AS verified_lines,
  COUNTIF(f.verified AND d.is_kpi) AS verified_kpi_lines,
  COUNTIF(f.is_restated) AS restated_lines,
  MIN(f.report_vintage) AS earliest_vintage,
  MAX(f.report_vintage) AS latest_vintage
FROM `ongc-hr-finance-agent.hrfin_gold.fact_financial_statement_line` f
LEFT JOIN `ongc-hr-finance-agent.hrfin_gold.dim_financial_line` d
  USING (line_code)
GROUP BY 1, 2, 3, 4;
