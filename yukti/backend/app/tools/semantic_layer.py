"""Semantic Layer and SQL Safety Engine for Yukti AI.
Contains enterprise table schemas, metric definitions, join paths,
and enforces query-craft rules and SQL safety checks.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from google.cloud import bigquery
from app.config import (
    ALLOWED_DATASETS,
    BQ_LOCATION,
    GCP_PROJECT,
    JOB_LABELS,
    MAX_BYTES_BILLED,
)

logger = logging.getLogger("yukti.semantic_layer")

FORBIDDEN_SQL_PATTERNS = [
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bDROP\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bTRUNCATE\b",
    r"\bRENAME\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bMERGE\b",
    r"\bEXECUTE\b",
    r"\bCALL\b",
]

SEMANTIC_LAYER_PROMPT = f"""
BIGQUERY ENTERPRISE SCHEMAS & EXACT COLUMN CATALOG (Project: {GCP_PROJECT}):

1. PREFERRED PRE-AGGREGATED GOLD SUMMARY TABLES (Use these first for fastest sub-second execution):
   • `hrfin_gold.agg_headcount_tenure_summary` (PREFERRED for executive station stay & transfer queries):
     - Exact Columns: wc_id, wc_name, cluster_id, cluster_name, hard_station_cat, grade_id, discipline_id, continuous_stay_months, continuous_stay_years, total_executives, exempt_retiring_3yr, non_exempt_due_transfer.
     - Clustered by: (wc_id, continuous_stay_months).
     - Example: `SELECT grade_id, discipline_id, SUM(total_executives) as num_executives, SUM(exempt_retiring_3yr) as exempt, SUM(non_exempt_due_transfer) as due_transfer FROM hrfin_gold.agg_headcount_tenure_summary WHERE wc_id = 'WC-DEL' AND continuous_stay_months >= 60 AND grade_id LIKE 'E%' GROUP BY grade_id, discipline_id;`

   • `hrfin_gold.agg_field_pnl_summary` (PREFERRED for field P&L economics & loss-making fields):
     - Exact Columns: pnl_id, fiscal_year, field_id, field_name, basin, onshore_offshore, asset_wc_id, asset_name, oil_revenue_inr_cr, gas_revenue_inr_cr, recomputed_gross_revenue_inr_cr, statutory_royalty_inr_cr, statutory_cess_inr_cr, statutory_windfall_tax_saed_inr_cr, recomputed_net_revenue_inr_cr, allocated_manpower_cost_inr_cr, total_opex_inr_cr, recomputed_ebitda_inr_cr, recomputed_ebitda_margin_pct, dda_depreciation_inr_cr, recomputed_pbt_inr_cr, total_production_boe, lifting_cost_per_boe_usd, manpower_cost_per_boe_usd, is_loss_making_3yr_consecutive, is_divestment_candidate.
     - Clustered by: (field_id, onshore_offshore).
     - Example: `SELECT field_name, recomputed_ebitda_inr_cr, recomputed_pbt_inr_cr FROM hrfin_gold.agg_field_pnl_summary WHERE fiscal_year = 'FY26' AND (recomputed_ebitda_inr_cr < 0 OR recomputed_pbt_inr_cr < 0);`

   • `hrfin_gold.agg_lifting_cost_summary` (PREFERRED for asset lifting & manpower costs per BOE):
     - Exact Columns: fiscal_year, asset_wc_id, asset_name, onshore_offshore, total_opex_inr_cr, allocated_manpower_cost_inr_cr, total_production_boe, total_regular_headcount, total_contractor_headcount, lifting_cost_per_boe_inr, lifting_cost_per_boe_usd, manpower_cost_per_boe_usd.
     - Clustered by: (asset_wc_id, fiscal_year).
     - Example: `SELECT onshore_offshore, ROUND(SUM(total_opex_inr_cr * 10000000.0 / 88.33) / NULLIF(SUM(total_production_boe), 0), 2) as avg_lifting_cost_usd FROM hrfin_gold.agg_lifting_cost_summary WHERE fiscal_year = 'FY26' GROUP BY onshore_offshore;`

   • `hrfin_gold.agg_vacancies_summary` (PREFERRED for vacancies vs sanctioned posts across hard/remote stations):
     - Exact Columns: fiscal_year, wc_id, work_centre_name, hard_station_cat, onshore_offshore, discipline_id, total_sanctioned, total_in_position, total_vacancies, vacancy_rate_pct.
     - Clustered by: (wc_id, fiscal_year).
     - Example: `SELECT work_centre_name, SUM(total_sanctioned) as sanctioned, SUM(total_in_position) as in_position, SUM(total_vacancies) as vacancies FROM hrfin_gold.agg_vacancies_summary WHERE fiscal_year = 'FY26' AND hard_station_cat = 'C' GROUP BY work_centre_name ORDER BY vacancies DESC;`

2. BASE GOLD VIEWS & MARTS (Fallback for un-aggregated row-level details):
   • `hrfin_gold.v_continuous_stay` (Continuous Station Tenure):
     - Exact Columns: emp_id, emp_name, gender, category, dob, retirement_date, wc_id, wc_name, sector, cluster_id, cluster_name, hard_station_cat, is_corporate_hq, grade_id, discipline_id, continuous_from_date, continuous_to_date, continuous_stay_months, continuous_stay_years, is_current_stay, is_continuous_5yr_plus, is_superannuation_exempt.
     - MANDATORY: Always filter `is_current_stay = TRUE` for active postings.
     - Executive cadre: `grade_id LIKE 'E%'` (Grades E0 to E9). (No column named 'cadre').
     - Discipline column: `discipline_id` (e.g. 'DISC-DRL', 'DISC-FIN', 'DISC-HR', 'DISC-PRD', 'DISC-MM').
     - Delhi Corporate HQ: `wc_id = 'WC-DEL'`. Dehradun: `wc_id = 'WC-DDN'`. Mumbai: `wc_id = 'WC-MUM'`.
     - 5-year tenure threshold: `continuous_stay_months >= 60`.
     - Retirement Exemption (JRTP Clause 7.0, 3-year practice): `is_superannuation_exempt = TRUE` or `DATE_DIFF(retirement_date, DATE '2026-10-19', DAY) <= 3 * 365.25`.

   • `hrfin_gold.v_cluster_cumulative_tenure` (Cluster Stay Cap - JRTP Clause 4.0):
     - Exact Columns: emp_id, emp_name, gender, category, dob, retirement_date, current_grade_id, current_wc_id, cluster_id, cluster_name, cumulative_cluster_days, cumulative_cluster_years, is_currently_in_cluster, has_breached_cluster_10yr_cap, is_superannuation_exempt.
     - 10-year lifetime cluster ceiling: `cumulative_cluster_years >= 10.0` or `has_breached_cluster_10yr_cap = TRUE`.
     - Exemption status: `is_superannuation_exempt = TRUE` (within 3 years of superannuation).

   • `hrfin_gold.v_field_pnl` (Standalone Field P&L Economics):
     - Exact Columns: field_id, field_name, basin, onshore_offshore, asset_wc_id, asset_name, fiscal_year, oil_revenue_inr_cr, gas_revenue_inr_cr, recomputed_gross_revenue_inr_cr, statutory_royalty_inr_cr, statutory_cess_inr_cr, statutory_windfall_tax_saed_inr_cr, recomputed_net_revenue_inr_cr, allocated_manpower_cost_inr_cr, total_opex_inr_cr, recomputed_ebitda_inr_cr, recomputed_ebitda_margin_pct, dda_depreciation_inr_cr, recomputed_pbt_inr_cr, total_production_boe, lifting_cost_per_boe_usd, manpower_cost_per_boe_usd, boe_per_employee, is_loss_making_3yr_consecutive, is_divestment_candidate, pec_monetisation_potential_flag, root_cause_loss_code.
     - MANDATORY: Always filter `field_id IS NOT NULL` to exclude non-field corporate reconciling lines (plants/VAP/corporate).
     - In FY26, Champang (`field_id = 'FLD-CHP'`, PBT -₹4.93 Cr) is the only loss-making field.
     - Baseline fiscal year: `fiscal_year IN ('FY26', '2026')`.

   • `hrfin_gold.mart_field_economics` (Field Performance, Water Cut, Lifting Costs):
     - Exact Columns: pnl_id, fiscal_year, field_id, field_name, name, basin, onshore_offshore, line_type, asset_wc_id, wc_id, asset_name, short_name, oil_revenue_inr_cr, gas_revenue_inr_cr, gross_revenue_inr_cr, total_opex_inr_cr, ebitda_inr_cr, pbt_inr_cr, total_production_boe, lifting_cost_per_boe_usd, water_cut_pct, oil_production_mt, gas_production_mmscm.
     - Note: Water cut is `water_cut_pct` and lifting cost is `lifting_cost_per_boe_usd`. Filter `line_type = 'field'`.

   • `hrfin_gold.v_lifting_cost` (Lifting and Manpower Cost Benchmarks):
     - Exact Columns: fiscal_year, asset_wc_id, asset_name, onshore_offshore, field_id, field_name, total_production_boe, total_opex_inr_cr, lifting_cost_per_boe_inr, lifting_cost_per_boe_usd, manpower_cost_per_boe_usd, allocated_manpower_cost_inr_cr, regular_employee_headcount, contractor_headcount, boe_per_employee.
     - Baseline fiscal year: `fiscal_year IN ('FY26', '2026')`.

   • `hrfin_gold.mart_contract_workforce` (Contract Labor vs Regular Manpower & CLRA):
     - Exact Columns: contract_entry_id, contract_id, vendor_id, vendor_name, name, vendor_category, is_mse_vendor, wc_id, asset_wc_id, wc_name, short_name, state, sector, onshore_offshore, type, month, fiscal_year, service_category, discipline_id, grade_id, is_core_activity, contractor_headcount, headcount, regular_employee_count_matching, contractor_to_regular_ratio, monthly_cost_inr, contractor_cost_per_boe_usd, manpower_cost_per_boe_usd, clra_license_no, clra_compliance_status.

   • `hrfin_gold.mart_workforce` (Workforce Cadre, Superannuations, and Demographics):
     - Exact Columns: emp_id, name, gender, dob, doj, fiscal_year_joined, category, social_category, pwd_flag, current_grade_id, grade_id, cadre, group, discipline_id, discipline_name, function, wc_id, wc_name, short_name, city, state, hard_station_cat, onshore_offshore, employment_status, retirement_date, years_to_retirement, is_near_retirement_2yr, is_near_retirement_3yr, sanctioned_strength, in_position_strength, vacancy_count.
     - Note: Active staff: `LOWER(employment_status) = 'active'`. Cadre: `LOWER(cadre) = 'executive'`.

   • `hrfin_gold.mart_capex_projects` (Major Capital Projects & Milestones):
     - Exact Columns: budget_id, fiscal_year, prj_id, project_name, sanctioned_cost_inr_cr, project_status, cost_overrun_inr_cr, schedule_slippage_months, delay_root_cause_category, asset_name, capex_utilisation_pct.

   • `hrfin_gold.mart_hse_incident` (Safety, LTIFR, and Process Safety):
     - Exact Columns: incident_id, wc_id, wc_name, onshore_offshore, incident_date, fiscal_year, incident_type, lost_time_injury_flag, days_lost, severity_tier ('Tier_1', 'Tier_2'), total_manhours_worked, calculated_ltifr, brief_description.

2. SILVER OPERATIONAL TABLES (For granular transactions and foreign key dimensions):
   • `hrfin_silver.employee_master`: emp_id, name, gender, dob, doj, current_grade_id, discipline_id, current_wc_id, employment_status ('Active'), retirement_date. (Note: name is `name`, work centre is `current_wc_id`).
   • `hrfin_silver.dim_work_centre`: wc_id, name, short_name, city, state, hard_station_cat ('A', 'B', 'C'), onshore_offshore.
   • `hrfin_silver.dim_grade`: grade_id, cadre, group, designation, pay_scale_min_inr, pay_scale_max_inr, typical_residency_years, level_order.
   • `hrfin_silver.dim_field`: field_id, name, asset_wc_id, basin_name, onshore_offshore, discovery_year, hydrocarbon_type, maturity.
   • `hrfin_silver.dim_discipline`: discipline_id, code, name, function, applicable_cadres. (Note: column for discipline name is `name`).
   • `hrfin_silver.dim_vendor`: vendor_id, name, vendor_category, is_mse_vendor, mse_social_category, mse_women_owned_flag.
   • `hrfin_silver.sanctioned_posts`: fiscal_year, wc_id, discipline_id, grade_id, sanctioned_strength, in_position_strength, vacancy_count.
   • `hrfin_silver.corporate_financials`: fiscal_year, gross_revenue_inr_cr, total_opex_inr_cr, ebitda_inr_cr, pat_inr_cr, lifting_cost_average_usd_boe.
   • `hrfin_silver.receivables`: invoice_id, customer_id, wc_id, outstanding_amount_inr_cr, aging_days, product_type, fiscal_year.
   • `hrfin_silver.wells_drilled`: well_id, well_name, field_id, asset_wc_id, basin_name, well_type, result_status ('oil_discovery', 'gas_discovery', 'dry_hole'), drilling_cost_inr_cr, fiscal_year.
   • `hrfin_silver.cag_paras`: cag_para_id, report_number, operating_department, para_subject, financial_implication_inr_cr, current_status, age_in_years, is_aged_over_3_years. (Note: column is `report_number`, not reference_number; `para_subject`, not subject_title).

3. THE 5 CRITICAL QUERY-CRAFT RULES:
   Rule 1: Always use LOWER() on categoricals (e.g. `LOWER(onshore_offshore) = 'onshore'`, `LOWER(cadre) = 'executive'`, `LOWER(clra_compliance_status) = 'compliant'`).
   Rule 2: NEVER SUM OR AVG RATIOS OR PER-BARREL METRICS: Pre-computed per-barrel columns (like lifting_cost_per_boe_usd, manpower_cost_per_boe_usd) or ratios (contractor_to_regular_ratio) MUST NEVER be summed or averaged. Always recompute weighted sums:
     `lifting_cost_per_boe = ROUND(SUM(total_opex_inr_cr * 10000000.0 / 88.33) / NULLIF(SUM(total_production_boe), 0), 2)`
     `manpower_cost_per_boe = ROUND(SUM(allocated_manpower_cost_inr_cr * 10000000.0 / 88.33) / NULLIF(SUM(total_production_boe), 0), 2)`
   Rule 3: ASSET & REGIONAL RESOLUTION:
     - Offshore Regions: Western Offshore includes Mumbai High (`WC-MHN`, `WC-MHS`), Neelam & Heera (`WC-N&H`), and Bassein & Satellite (`WC-B&S`). Eastern Offshore includes Eastern Offshore Asset / KG Basin (`WC-EOA`). Do not label Eastern Offshore as Western Offshore.
     - Gujarat Onshore: use `state = 'Gujarat'` or `wc_id IN ('WC-AHM', 'WC-ANK', 'WC-MEH', 'WC-CAM')`. Never invent 'gujarat asset'.
     - Assam Onshore: use `state = 'Assam'` or `wc_id IN ('WC-ASM', 'WC-JOR')`.
     - North-East (NE): strictly means states AS, TR, AR, NL, MZ, MN, ML, SK (`state_code IN ('AS', 'TR', 'AR', 'NL', 'MZ', 'MN', 'ML', 'SK')` or `wc_id IN ('WC-ASM', 'WC-TRI', 'WC-AAB', 'WC-JOR', 'WC-SIL', 'WC-INB')`). DO NOT equate NE with hard_station_cat='C'. Total FY26 NE executive vacancies = 143.
     - Never make unverified causal claims; cite data drivers (such as water cut or mature field age) only when present in query results.
   Rule 4: Multi-Tool Policy + Data Turns: If an inquiry involves both corporate policy rules and quantitative employee numbers (e.g. P11 retention beyond 10-year cluster cap, pre-retirement exemptions, transfer eligibility), call BOTH `search_policy` to retrieve the clause AND `query_data` to fetch exact headcounts.
   Rule 5: Rank not threshold: never use arbitrary hardcoded cutoff filters that risk returning 0 rows; use dynamic quantiles, `ORDER BY ... DESC LIMIT 10`.
"""


class SemanticLayer:
    """Manages enterprise metrics, glossary terms, and query safety."""

    def __init__(self, project_id: str = GCP_PROJECT, location: str = BQ_LOCATION):
        self.project_id = project_id
        self.location = location
        self._bq_client: Optional[bigquery.Client] = None

    @property
    def client(self) -> bigquery.Client:
        if self._bq_client is None:
            self._bq_client = bigquery.Client(
                project=self.project_id,
                location=self.location,
                default_query_job_config=bigquery.QueryJobConfig(labels=JOB_LABELS),
            )
        return self._bq_client

    def apply_query_craft_rules(self, sql: str) -> str:
        """Applies query-craft rules (LOWER on categoricals, project qualification, and row limits)."""
        refined_sql = sql

        # Qualify unadorned datasets with project ID
        pattern = r"(?<![a-zA-Z0-9_\-\.`])(hrfin_gold|hrfin_silver|hrfin_docs)\.([a-zA-Z0-9_]+)"
        refined_sql = re.sub(pattern, f"`{self.project_id}`.\\1.\\2", refined_sql)

        refined_sql = re.sub(
            r"\bonshore_offshore\s*=\s*'([Oo]nshore|[Oo]ffshore)'",
            r"LOWER(onshore_offshore) = '\1'".lower(),
            refined_sql,
            flags=re.IGNORECASE,
        )
        refined_sql = re.sub(
            r"\bcadre\s*=\s*'([Ee]xecutive|[Nn]on-[Ee]xecutive)'",
            r"LOWER(cadre) = '\1'".lower(),
            refined_sql,
            flags=re.IGNORECASE,
        )
        if "LIMIT" not in refined_sql.upper() and not re.search(r"^\s*SELECT\s+COUNT\(", refined_sql, flags=re.IGNORECASE):
            refined_sql = refined_sql.rstrip(";") + " LIMIT 100;"
        return refined_sql

    def validate_sql_safety(self, sql: str) -> Tuple[bool, Optional[str]]:
        """Enforces SELECT-only queries, dataset allow-listing, and absence of forbidden statements."""
        sql_stripped = sql.strip().rstrip(";")
        sql_upper = sql_stripped.upper()

        if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
            return False, "Query must start with SELECT or WITH (read-only queries only)."

        for pattern in FORBIDDEN_SQL_PATTERNS:
            if re.search(pattern, sql_upper):
                return False, f"Forbidden SQL operation detected matching: {pattern}"

        matches = re.findall(r"[`]?([a-zA-Z0-9_\-]+)\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)[`]?", sql)
        for proj, dataset, table in matches:
            if dataset not in ALLOWED_DATASETS:
                return False, f"Dataset '{dataset}' is not in the allowed list: {ALLOWED_DATASETS}"

        two_part = re.findall(r"(?:FROM|JOIN)\s+[`]?([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)[`]?", sql, flags=re.IGNORECASE)
        for dataset, table in two_part:
            if dataset not in ALLOWED_DATASETS and dataset != self.project_id:
                return False, f"Dataset '{dataset}' is not in the allowed list: {ALLOWED_DATASETS}"

        return True, None

    def dry_run_check(self, sql: str) -> Tuple[bool, int, Optional[str]]:
        """Executes a dry-run to validate syntax and estimate bytes processed without incurring cost."""
        try:
            dry_job_config = bigquery.QueryJobConfig(
                dry_run=True,
                use_query_cache=False,
                labels=JOB_LABELS,
            )
            job = self.client.query(sql, job_config=dry_job_config)
            bytes_scanned = job.total_bytes_processed or 0
            if bytes_scanned > MAX_BYTES_BILLED:
                return False, bytes_scanned, f"Query would scan {bytes_scanned} bytes, exceeding cap of {MAX_BYTES_BILLED} bytes."
            return True, bytes_scanned, None
        except Exception as e:
            return False, 0, f"Dry-run syntax validation failed: {str(e)}"
