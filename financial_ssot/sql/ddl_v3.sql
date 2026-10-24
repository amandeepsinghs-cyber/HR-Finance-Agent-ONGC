-- =============================================================================
-- Yukti v3 Financial SSOT BigQuery DDL (SPEC-01 §5–§7, Packet P1.6)
-- Project: ongc-hr-finance-agent
-- Datasets: hrfin_bronze, hrfin_gold_staging, hrfin_gold
-- Additive only: creates new v3 tables and views; never modifies or drops existing
-- ssot_corporate_* tables.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS `ongc-hr-finance-agent.hrfin_bronze`
  OPTIONS(location = "asia-south1", description = "Yukti v3 Financial SSOT Bronze landing tables");

CREATE SCHEMA IF NOT EXISTS `ongc-hr-finance-agent.hrfin_gold_staging`
  OPTIONS(location = "asia-south1", description = "Yukti v3 Financial SSOT Gold staging dataset for pre-promotion gate verification");

CREATE SCHEMA IF NOT EXISTS `ongc-hr-finance-agent.hrfin_gold`
  OPTIONS(location = "asia-south1", description = "Yukti v3 Financial SSOT Verified Gold tables and views");

-- -----------------------------------------------------------------------------
-- 1. Bronze: raw extractions across AR 10-yr, AR statements/notes, and XBRL (SPEC-01 §5.3)
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
-- 2. Gold: dim_financial_line (SPEC-01 §5.2 columns + backward-compatible aliases)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `ongc-hr-finance-agent.hrfin_gold.dim_financial_line` (
  line_code STRING NOT NULL,
  statement STRING NOT NULL,
  display_name STRING NOT NULL,
  line_name STRING NOT NULL,
  line_name_aliases STRING,
  section STRING NOT NULL,
  subsection STRING,
  parent_line_code STRING,
  level INT64 NOT NULL,
  hierarchy_level INT64 NOT NULL,
  line_order INT64 NOT NULL,
  display_order INT64 NOT NULL,
  line_kind STRING NOT NULL,
  line_class STRING NOT NULL,
  subtotal_formula STRING,
  formula STRING,
  sign_in_parent INT64 NOT NULL,
  natural_sign STRING NOT NULL,
  schedule3_ref STRING,
  ind_as_schedule_iii_ref STRING,
  ar_note_ref_typical STRING,
  ar_labels STRING,
  ten_year_label STRING,
  xbrl_tags STRING,
  xbrl_element_name STRING,
  yahoo_types STRING,
  yahoo_field_name STRING,
  yahoo_equivalence STRING NOT NULL,
  scope_applicability STRING NOT NULL,
  valid_from_fy STRING,
  valid_to_fy STRING,
  unit_default STRING NOT NULL,
  is_subtotal BOOL NOT NULL,
  is_total BOOL NOT NULL,
  is_kpi BOOL NOT NULL,
  description STRING NOT NULL
)
CLUSTER BY statement, section;

-- -----------------------------------------------------------------------------
-- 3. Gold: fact_financial_statement_line (SPEC-01 §5.1)
-- Partitioned by period_end (yearly), clustered by scope, statement, line_code
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `ongc-hr-finance-agent.hrfin_gold.fact_financial_statement_line` (
  fiscal_year STRING NOT NULL,
  period_type STRING NOT NULL,
  period_end DATE NOT NULL,
  scope STRING NOT NULL,
  statement STRING NOT NULL,
  line_code STRING NOT NULL,
  line_name_as_reported STRING NOT NULL,
  parent_line_code STRING,
  line_order INT64 NOT NULL,
  value_native FLOAT64,
  unit_native STRING NOT NULL,
  value_inr_cr FLOAT64,
  value FLOAT64,
  unit STRING NOT NULL,
  precision_inr_cr FLOAT64,
  is_restated BOOL NOT NULL,
  raw_is_restated BOOL NOT NULL,
  is_own_vintage BOOL NOT NULL,
  is_fallback_vintage BOOL NOT NULL,
  is_latest_vintage BOOL NOT NULL,
  is_nil BOOL NOT NULL,
  sign_convention STRING NOT NULL,
  source_system STRING NOT NULL,
  report_vintage STRING NOT NULL,
  source_doc STRING NOT NULL,
  source_page INT64,
  source_page_label STRING,
  source_table STRING NOT NULL,
  source_text_line INT64,
  source_snippet STRING,
  raw_label STRING NOT NULL,
  raw_value_text STRING NOT NULL,
  extraction_method STRING NOT NULL,
  extractor_version STRING NOT NULL,
  extracted_at STRING NOT NULL,
  extract_id STRING,
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
PARTITION BY DATE_TRUNC(period_end, YEAR)
CLUSTER BY scope, statement, line_code;

-- -----------------------------------------------------------------------------
-- 4. Gold: Conflict & Restatement Audit Table (SPEC-01 §5.4 / §6.3)
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
  pct_delta FLOAT64,
  rule_id STRING NOT NULL,
  status STRING NOT NULL,
  resolution_rule STRING,
  resolution STRING,
  resolved_by STRING,
  resolved_at STRING
)
CLUSTER BY fiscal_year, scope, line_code;

-- -----------------------------------------------------------------------------
-- 5. Gold: Gate Run Audit Table (SPEC-01 §6.3, Packet P1.6 §4)
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
-- 6. Gold: Anchor Tables (P1.7 / SPEC-01 §10)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `ongc-hr-finance-agent.hrfin_gold.fact_segment` (
  fiscal_year STRING NOT NULL,
  scope STRING NOT NULL,
  segment_code STRING NOT NULL,
  line_code STRING,
  metric STRING NOT NULL,
  value_inr_mn FLOAT64,
  value_inr_cr FLOAT64,
  source_system STRING NOT NULL,
  source_doc STRING NOT NULL,
  source_page INT64,
  source_page_label STRING,
  source_text_line INT64,
  report_vintage STRING NOT NULL,
  is_own_vintage BOOL NOT NULL,
  is_latest_vintage BOOL NOT NULL,
  is_restated BOOL NOT NULL,
  extraction_method STRING NOT NULL,
  verified BOOL NOT NULL,
  verified_rule_ids ARRAY<STRING>,
  notes STRING
);

CREATE TABLE IF NOT EXISTS `ongc-hr-finance-agent.hrfin_gold.fact_production_annual` (
  fiscal_year STRING NOT NULL,
  product STRING NOT NULL,
  basis STRING NOT NULL,
  region STRING,
  value FLOAT64,
  unit STRING NOT NULL,
  source_system STRING NOT NULL,
  source_doc STRING NOT NULL,
  source_page INT64,
  source_page_label STRING,
  source_text_line INT64,
  report_vintage STRING NOT NULL,
  is_own_vintage BOOL NOT NULL,
  is_latest_vintage BOOL NOT NULL,
  is_restated BOOL NOT NULL,
  extraction_method STRING NOT NULL,
  verified BOOL NOT NULL,
  verified_rule_ids ARRAY<STRING>
);

CREATE TABLE IF NOT EXISTS `ongc-hr-finance-agent.hrfin_gold.fact_reserves` (
  fiscal_year STRING NOT NULL,
  as_of_date STRING,
  category STRING NOT NULL,
  product STRING NOT NULL,
  region STRING,
  value_mmtoe FLOAT64,
  accretion_mmtoe FLOAT64,
  rrr FLOAT64,
  source_system STRING NOT NULL,
  source_doc STRING NOT NULL,
  source_page INT64,
  source_page_label STRING,
  source_text_line INT64,
  report_vintage STRING NOT NULL,
  is_own_vintage BOOL NOT NULL,
  is_latest_vintage BOOL NOT NULL,
  is_restated BOOL NOT NULL,
  extraction_method STRING NOT NULL,
  verified BOOL NOT NULL,
  verified_rule_ids ARRAY<STRING>,
  notes STRING
);

CREATE TABLE IF NOT EXISTS `ongc-hr-finance-agent.hrfin_gold.fact_hr_aggregates` (
  fiscal_year STRING NOT NULL,
  metric STRING NOT NULL,
  dimension STRING,
  dimension_value STRING,
  value FLOAT64,
  unit STRING NOT NULL,
  source_system STRING NOT NULL,
  source_doc STRING NOT NULL,
  source_page INT64,
  source_page_label STRING,
  source_text_line INT64,
  report_vintage STRING NOT NULL,
  is_own_vintage BOOL NOT NULL,
  is_latest_vintage BOOL NOT NULL,
  is_restated BOOL NOT NULL,
  extraction_method STRING NOT NULL,
  verified BOOL NOT NULL,
  verified_rule_ids ARRAY<STRING>,
  notes STRING
);

CREATE TABLE IF NOT EXISTS `ongc-hr-finance-agent.hrfin_gold.fact_price_realisation` (
  fiscal_year STRING NOT NULL,
  product STRING NOT NULL,
  basis STRING,
  realisation_usd_per_bbl FLOAT64,
  realisation_usd_per_mmbtu FLOAT64,
  realisation_inr_per_unit FLOAT64,
  unit STRING NOT NULL,
  source_system STRING NOT NULL,
  source_doc STRING NOT NULL,
  source_page INT64,
  source_page_label STRING,
  source_text_line INT64,
  report_vintage STRING NOT NULL,
  is_own_vintage BOOL NOT NULL,
  is_latest_vintage BOOL NOT NULL,
  is_restated BOOL NOT NULL,
  extraction_method STRING NOT NULL,
  verified BOOL NOT NULL,
  verified_rule_ids ARRAY<STRING>,
  notes STRING
);

-- -----------------------------------------------------------------------------
-- 7. Serving Views (SPEC-01 §5.5 & §7.1, B3 & I1)
-- Guaranteed <= 1 row per (fiscal_year, scope, line_code)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW `ongc-hr-finance-agent.hrfin_gold.v_fin_statement_as_reported` AS
SELECT
  f.*,
  d.display_name,
  d.line_name,
  d.section,
  d.subsection,
  d.level,
  d.hierarchy_level,
  d.display_order,
  d.line_kind,
  d.line_class,
  d.subtotal_formula,
  d.formula,
  d.sign_in_parent,
  d.natural_sign,
  d.schedule3_ref,
  d.ar_note_ref_typical,
  d.xbrl_element_name,
  d.yahoo_field_name,
  d.scope_applicability,
  d.unit_default,
  d.is_subtotal,
  d.is_total,
  d.is_kpi,
  CASE
    WHEN f.is_fallback_vintage THEN CONCAT(f.fiscal_year, ' from ', f.report_vintage, ' comparative/summary (no own-year AR table)')
    WHEN f.source_system = 'xbrl' THEN CONCAT(f.fiscal_year, ' from ', f.report_vintage, ' BSE Reg 33 filing (AR PDF scanned)')
    ELSE NULL
  END AS footnote_marker
FROM `ongc-hr-finance-agent.hrfin_gold.fact_financial_statement_line` f
JOIN `ongc-hr-finance-agent.hrfin_gold.dim_financial_line` d
  USING (line_code)
WHERE f.verified = TRUE
  AND f.period_type = 'annual'
  AND (f.is_own_vintage = TRUE OR f.is_fallback_vintage = TRUE);

CREATE OR REPLACE VIEW `ongc-hr-finance-agent.hrfin_gold.v_fin_trend_latest` AS
SELECT
  f.*,
  d.display_name,
  d.line_name,
  d.section,
  d.subsection,
  d.level,
  d.hierarchy_level,
  d.display_order,
  d.line_kind,
  d.line_class,
  d.subtotal_formula,
  d.formula,
  d.sign_in_parent,
  d.natural_sign,
  d.schedule3_ref,
  d.ar_note_ref_typical,
  d.xbrl_element_name,
  d.yahoo_field_name,
  d.scope_applicability,
  d.unit_default,
  d.is_subtotal,
  d.is_total,
  d.is_kpi,
  CASE
    WHEN f.is_restated THEN CONCAT(f.fiscal_year, ' restated in ', f.report_vintage)
    WHEN f.is_fallback_vintage THEN CONCAT(f.fiscal_year, ' from ', f.report_vintage, ' comparative/summary (no own-year AR table)')
    ELSE NULL
  END AS footnote_marker
FROM `ongc-hr-finance-agent.hrfin_gold.fact_financial_statement_line` f
JOIN `ongc-hr-finance-agent.hrfin_gold.dim_financial_line` d
  USING (line_code)
WHERE f.verified = TRUE
  AND f.period_type = 'annual'
  AND f.is_latest_vintage = TRUE;

CREATE OR REPLACE VIEW `ongc-hr-finance-agent.hrfin_gold.v_fin_quarterly_xbrl` AS
SELECT
  f.*,
  d.display_name,
  d.line_name,
  d.section,
  d.subsection,
  d.level,
  d.line_kind,
  d.unit_default,
  d.is_kpi
FROM `ongc-hr-finance-agent.hrfin_gold.fact_financial_statement_line` f
JOIN `ongc-hr-finance-agent.hrfin_gold.dim_financial_line` d
  USING (line_code)
WHERE f.verified = TRUE
  AND f.period_type = 'quarter';

CREATE OR REPLACE VIEW `ongc-hr-finance-agent.hrfin_gold.v_fin_opening_bs` AS
SELECT
  f.*,
  d.display_name,
  d.line_name,
  d.section,
  d.subsection,
  d.level,
  d.line_kind,
  d.unit_default,
  d.is_kpi
FROM `ongc-hr-finance-agent.hrfin_gold.fact_financial_statement_line` f
JOIN `ongc-hr-finance-agent.hrfin_gold.dim_financial_line` d
  USING (line_code)
WHERE f.verified = TRUE
  AND f.period_type = 'opening';

CREATE OR REPLACE VIEW `ongc-hr-finance-agent.hrfin_gold.v_fin_yahoo_view` AS
SELECT
  f.fiscal_year,
  f.period_type,
  f.period_end,
  f.scope,
  f.statement,
  f.line_code,
  d.display_name,
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
  AND f.source_system = 'yahoo'
  AND f.scope = 'consolidated';

CREATE OR REPLACE VIEW `ongc-hr-finance-agent.hrfin_gold.v_fin_coverage` AS
SELECT
  f.fiscal_year,
  f.scope,
  f.statement,
  f.source_system,
  COUNT(*) AS total_lines,
  COUNT(DISTINCT f.line_code) AS distinct_lines,
  COUNTIF(f.verified) AS verified_lines,
  COUNTIF(f.verified AND d.is_kpi) AS verified_kpi_lines,
  COUNTIF(f.is_restated) AS restated_lines,
  MIN(f.report_vintage) AS earliest_vintage,
  MAX(f.report_vintage) AS latest_vintage
FROM `ongc-hr-finance-agent.hrfin_gold.fact_financial_statement_line` f
LEFT JOIN `ongc-hr-finance-agent.hrfin_gold.dim_financial_line` d
  USING (line_code)
GROUP BY 1, 2, 3, 4;
