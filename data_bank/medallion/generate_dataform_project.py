#!/usr/bin/env python3
"""medallion/generate_dataform_project.py: Comprehensive generator for Silver (4.3) and Gold (4.4) including Addendum Gaps."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
DF_DIR = BASE_DIR / "medallion" / "dataform"
DEFS_DIR = DF_DIR / "definitions"
SILVER_DIR = DEFS_DIR / "silver"
GOLD_DIR = DEFS_DIR / "gold"
ASSERTIONS_DIR = DEFS_DIR / "assertions"

SCHEMA_SILVER_PATH = BASE_DIR / "world_bible" / "schema_silver.yaml"
SCHEMA_ADDENDUM_PATH = BASE_DIR / "world_bible" / "schema_silver_addendum_gaps.yaml"
BRONZE_YAML_PATH = BASE_DIR / "medallion" / "bronze" / "bronze_tables.yaml"
PARSING_SPECS_PATH = BASE_DIR / "landing" / "excel" / "_parsing_specs.yaml"


def setup_directories():
    for d in [DF_DIR, DEFS_DIR, SILVER_DIR, GOLD_DIR, ASSERTIONS_DIR, DF_DIR / "includes"]:
        d.mkdir(parents=True, exist_ok=True)


def write_workflow_settings():
    settings = """dataformCoreVersion: 3.0.24
defaultProject: ongc-hr-finance-agent
defaultLocation: asia-south1
defaultDataset: hrfin_silver
defaultAssertionDataset: hrfin_silver
"""
    with open(DF_DIR / "workflow_settings.yaml", "w", encoding="utf-8") as f:
        f.write(settings)


def write_credentials():
    creds = {
        "projectId": "ongc-hr-finance-agent",
        "location": "asia-south1"
    }
    with open(DF_DIR / ".df-credentials.json", "w", encoding="utf-8") as f:
        json.dump(creds, f, indent=2)


def write_sources_js():
    bronze_tables = [
        "sap_pa0002_pa0001", "sap_pa0001", "sap_pa0000_promotions", "sap_pa0000_separations",
        "sap_py_cluster_exp", "sap_eapar_ratings", "sap_pa2001_pa2006", "sap_co_pa", "sap_cosp_coss",
        "sap_ekko_ekpo", "sap_fi_ar_invoices", "sap_essr_esll", "sap_ptrv_head_doc", "sap_project_milestones",
        "sap_vigilance_cases_confidential", "sap_headcount_monthly_snapshot",
        "db_exports_production_monthly", "db_exports_wells_drilled", "db_exports_lms_attendance",
        "db_exports_hse_incident_log", "db_exports_medical_claims_export", "db_exports_access_audit_log",
        "db_exports_rti_applications_export", "governance_corporate_financial_summary", "governance_subsidiary_group_financials",
        "governance_parliament_questions_index", "excel_capex_be_re_actuals", "excel_manpower_plan",
        "excel_dpe_mou_scorecard", "excel_csr_projects_tracker", "excel_succession_planning",
        "excel_legal_cases_tracker", "excel_dpc_tracker", "excel_training_calendar",
        "excel_icc_committees", "excel_reserves_annual", "excel_price_fx", "excel_treasury_forex_hedges",
        "excel_actuarial_benefit_liabilities", "excel_energy_transition_progress", "excel_cag_paras_register", "excel_board_agenda_index",
        # 4 Addendum bronze tables
        "db_exports_env_incident_log", "excel_posh_register", "sap_apprentice_ledger", "sap_ekko_channel", "sap_employee_cost_pool", "sap_payroll_policy_fy", "sap_co_pa_v3", "sap_field_alloc_audit"
    ]

    ref_dims = [
        "dim_work_centre", "dim_grade", "dim_discipline", "dim_field",
        "dim_project", "dim_cost_centre", "dim_customer", "dim_vendor",
        "dim_geography", "dim_calendar", "dim_price_fx"
    ]

    content = """// BigQuery source declarations for Bronze layer
const bronzeTables = """ + json.dumps(bronze_tables, indent=2) + """;

bronzeTables.forEach(tableName => {
  declare({
    database: "ongc-hr-finance-agent",
    schema: "hrfin_bronze",
    name: tableName,
  });
});

// Preloaded Reference Dimensions in hrfin_silver
const refDims = """ + json.dumps(ref_dims, indent=2) + """;

refDims.forEach(tableName => {
  declare({
    database: "ongc-hr-finance-agent",
    schema: "hrfin_silver",
    name: tableName,
  });
});

// hrfin_ref dims
const hrfinRefDims = [
  "dim_grade_pay_scale", "dim_ida_rate", "dim_hra_rate", "dim_allowance_rule", "dim_payroll_policy_fy", "dim_benefit_scheme", "dim_insurance_plan", "field_econ_targets_fy"
];

hrfinRefDims.forEach(tableName => {
  declare({
    database: "ongc-hr-finance-agent",
    schema: "hrfin_ref",
    name: tableName,
  });
});
"""
    with open(DEFS_DIR / "sources.js", "w", encoding="utf-8") as f:
        f.write(content)


def generate_silver_rejects():
    sqlx = """config {
  type: "table",
  schema: "hrfin_silver",
  name: "_rejects",
  description: "Silver logging table capturing rows rejected due to parsing or validation failures"
}

SELECT
  CAST(NULL AS STRING) AS source_table,
  CAST(NULL AS STRING) AS record_id,
  CAST(NULL AS STRING) AS reject_reason,
  CAST(NULL AS STRING) AS raw_payload,
  CAST(NULL AS TIMESTAMP) AS rejected_at
LIMIT 0
"""
    with open(SILVER_DIR / "_rejects.sqlx", "w", encoding="utf-8") as f:
        f.write(sqlx)


def get_cast_expr(col_name: str, col_type: str, src_col: str) -> str:
    clean_val = f"NULLIF(TRIM({src_col}), '')"
    if col_type == "DATE":
        return f"SAFE.PARSE_DATE('%Y-%m-%d', SUBSTR({clean_val}, 1, 10)) AS {col_name}"
    elif col_type == "TIMESTAMP":
        return f"SAFE_CAST({clean_val} AS TIMESTAMP) AS {col_name}"
    elif col_type == "NUMERIC":
        return f"SAFE_CAST(REPLACE(REPLACE({clean_val}, ',', ''), '₹', '') AS NUMERIC) AS {col_name}"
    elif col_type == "FLOAT64":
        return f"SAFE_CAST(REPLACE(REPLACE({clean_val}, ',', ''), '₹', '') AS FLOAT64) AS {col_name}"
    elif col_type == "INT64":
        return f"SAFE_CAST(REPLACE(REPLACE({clean_val}, ',', ''), '₹', '') AS INT64) AS {col_name}"
    elif col_type == "BOOL":
        return f"CASE WHEN LOWER(TRIM({src_col})) IN ('true', '1', 't', 'yes', 'y') THEN TRUE WHEN LOWER(TRIM({src_col})) IN ('false', '0', 'f', 'no', 'n') THEN FALSE ELSE NULL END AS {col_name}"
    elif col_type == "ARRAY<STRING>":
        return f"SPLIT(REGEXP_REPLACE(REGEXP_REPLACE({clean_val}, r'^\\[|\\]$', ''), r\"'\", ''), ', ') AS {col_name}"
    else:
        return f"TRIM({src_col}) AS {col_name}"


def generate_silver_models():
    with open(SCHEMA_SILVER_PATH, "r", encoding="utf-8") as f:
        schema = yaml.safe_load(f)

    # Load addendum tables
    if SCHEMA_ADDENDUM_PATH.exists():
        with open(SCHEMA_ADDENDUM_PATH, "r", encoding="utf-8") as f:
            addendum = yaml.safe_load(f)
            schema["tables"].extend(addendum.get("tables", []))

    with open(BRONZE_YAML_PATH, "r", encoding="utf-8") as f:
        bronze_meta = yaml.safe_load(f)["tables"]

    with open(PARSING_SPECS_PATH, "r", encoding="utf-8") as f:
        excel_specs_raw = yaml.safe_load(f)["workbooks"]

    excel_specs_by_table = {spec["target_table"]: spec for spec in excel_specs_raw.values()}

    ref_tables = {
        "dim_work_centre", "dim_grade", "dim_discipline", "dim_field",
        "dim_project", "dim_cost_centre", "dim_customer", "dim_vendor",
        "dim_geography", "dim_calendar", "dim_price_fx"
    }

    table_mapping = {
        "employee_master": "sap_pa0002_pa0001",
        "posting_history": "sap_pa0001",
        "promotion_history": "sap_pa0000_promotions",
        "dpc_cases": "excel_dpc_tracker",
        "separations": "sap_pa0000_separations",
        "sanctioned_posts": "excel_manpower_plan",
        "headcount_snapshot": "sap_headcount_monthly_snapshot",
        "payroll_monthly": "sap_py_cluster_exp",
        "apar_ratings": "sap_eapar_ratings",
        "succession_plan": "excel_succession_planning",
        "training_records": "db_exports_lms_attendance",
        "training_calendar": "excel_training_calendar",
        "leave_ledger": "sap_pa2001_pa2006",
        "medical_claims": "db_exports_medical_claims_export",
        "grievances_litigation": "excel_legal_cases_tracker",
        "contract_workforce": "sap_essr_esll",
        "hse_incidents": "db_exports_hse_incident_log",
        "travel_claims": "sap_ptrv_head_doc",
        "icc_committees": "excel_icc_committees",
        "vigilance_cases": "sap_vigilance_cases_confidential",
        "production_monthly": "db_exports_production_monthly",
        "reserves_annual": "excel_reserves_annual",
        "wells_drilled": "db_exports_wells_drilled",
        "price_fx_monthly": "excel_price_fx",
        "field_pnl_annual": "sap_co_pa",
        "cost_ledger": "sap_cosp_coss",
        "capex_budget": "excel_capex_be_re_actuals",
        "project_progress": "sap_project_milestones",
        "purchase_orders": "sap_ekko_ekpo",
        "receivables": "sap_fi_ar_invoices",
        "forex_hedges": "excel_treasury_forex_hedges",
        "csr_projects": "excel_csr_projects_tracker",
        "mou_targets": "excel_dpe_mou_scorecard",
        "benefit_liabilities": "excel_actuarial_benefit_liabilities",
        "subsidiary_financials": "governance_subsidiary_group_financials",
        "energy_transition": "excel_energy_transition_progress",
        "corporate_financials": "governance_corporate_financial_summary",
        "parliament_questions": "governance_parliament_questions_index",
        "cag_paras": "excel_cag_paras_register",
        "rti_applications": "db_exports_rti_applications_export",
        "board_agenda_index": "excel_board_agenda_index",
        "access_audit_log": "db_exports_access_audit_log",
        # 4 Addendum tables
        "env_incidents": "db_exports_env_incident_log",
        "posh_cases": "excel_posh_register",
        "apprentices": "sap_apprentice_ledger",
        "po_channel": "sap_ekko_channel", "employee_cost_pool": "sap_employee_cost_pool", "payroll_policy_fy": "sap_payroll_policy_fy",
    }

    excel_column_positions = {
        "capex_budget": {
            "budget_id": "col_1", "prj_id": "col_2", "project_name": "col_3", "asset_wc_id": "col_4",
            "month": "col_5", "fiscal_year": "col_6", "capex_head": "col_7",
            "budget_estimate_be_inr_cr": "col_8", "revised_estimate_re_inr_cr": "col_9", "actual_spend_inr_cr": "col_10"
        },
        "sanctioned_posts": {
            "sanction_id": "col_1", "fiscal_year": "col_2", "wc_id": "col_3", "discipline_id": "col_4", "grade_id": "col_5",
            "grade_band": "col_6", "social_category": "col_7", "gender": "col_8", "pwd_category": "col_9", "age_band": "col_10",
            "tenure_band": "col_11", "sanctioned_strength": "col_12", "in_position_strength": "col_13", "vacancy_count": "col_14",
            "vacancy_rate_pct": "col_15", "backlog_vacancies": "col_16", "special_drive_flag": "col_17", "special_drive_name": "col_18",
            "special_drive_target_vacancies": "col_19"
        },
        "mou_targets": {
            "mou_record_id": "col_1", "fiscal_year": "col_2", "parameter_id": "col_3", "parameter_name": "col_4",
            "parameter_category": "col_5", "unit_of_measure": "col_6", "weightage": "col_7", "excellent_target": "col_8",
            "very_good_target": "col_9", "good_target": "col_10", "fair_target": "col_11", "poor_target": "col_12",
            "actual_achievement": "col_13", "achieved_rating": "col_14", "weighted_score": "col_15", "composite_score": "col_16",
            "projected_composite_score": "col_17", "notes_and_exceptions": "col_18"
        },
        "csr_projects": {
            "csr_project_id": "col_1", "project_name": "col_2", "fiscal_year": "col_3", "state_code": "col_4",
            "district_name": "col_5", "is_aspirational_district": "col_6", "is_operational_field_area": "col_7",
            "wc_id": "col_8", "csr_theme": "col_9", "sanctioned_budget_inr_cr": "col_10", "actual_disbursed_inr_cr": "col_11",
            "implementing_agency": "col_12", "beneficiaries_count": "col_13", "statutory_2pct_mandate_met_flag": "col_14"
        },
        "succession_plan": {
            "position_id": "col_1", "role_title": "col_2", "wc_id": "col_3", "discipline_id": "col_4", "criticality_tier": "col_5",
            "incumbent_emp_id": "col_6", "incumbent_retire_date": "col_7", "fiscal_year": "col_8", "successor_1_emp_id": "col_9",
            "successor_1_readiness": "col_10", "successor_1_has_ne_hard_station": "col_11", "successor_2_emp_id": "col_12",
            "successor_2_readiness": "col_13", "successor_2_has_ne_hard_station": "col_14", "readiness_gap_reason": "col_15"
        },
        "grievances_litigation": {
            "case_id": "col_1", "emp_id": "col_2", "wc_id": "col_3", "case_type": "col_4", "case_category": "col_5",
            "forum": "col_6", "filing_date": "col_7", "fiscal_year": "col_8", "status": "col_9", "interim_stay_granted": "col_10",
            "age_days": "col_11", "age_years": "col_12", "is_aged_over_3_years": "col_13", "next_hearing_date": "col_14", "subject_summary": "col_15"
        },
        "dpc_cases": {
            "dpc_id": "col_0", "emp_id": "col_1", "fiscal_year": "col_2", "wc_id": "col_3", "from_grade_id": "col_4",
            "to_grade_id": "col_5", "discipline_id": "col_6", "due_date": "col_7", "held_date": "col_8", "status": "col_9",
            "eligible_candidates_count": "col_10", "recommended_candidates_count": "col_11", "pending_reason": "col_12",
            "delay_bottleneck_reason": "col_13", "delay_months": "col_14", "accelerated_merit_benchmark_score": "col_15"
        },
        "benefit_liabilities": {
            "scheme_record_id": "col_0", "fiscal_year": "col_1", "scheme_type": "col_2", "scheme_name": "col_3",
            "actuarial_liability_inr_cr": "col_4", "plan_assets_inr_cr": "col_5", "net_liability_inr_cr": "col_6",
            "funded_ratio_pct": "col_7", "discount_rate_pct": "col_8", "salary_escalation_rate_pct": "col_9",
            "medical_inflation_rate_pct": "col_10", "active_members_covered": "col_11", "retiree_beneficiaries_covered": "col_12",
            "annual_payout_inr_cr": "col_13", "dpe_30pct_superannuation_compliance_flag": "col_14"
        },
        "board_agenda_index": {
            "agenda_id": "col_0", "meeting_number": "col_1", "meeting_date": "col_2", "fiscal_year": "col_3",
            "item_number": "col_4", "director_sponsor": "col_5", "subject_title": "col_6", "agenda_category": "col_7",
            "confidentiality_level": "col_8", "key_recommendations": "col_9", "resolution_status": "col_10", "document_ref_id": "col_11"
        },
        "cag_paras": {
            "cag_para_id": "col_0", "report_number": "col_1", "cag_report_year": "col_2", "fiscal_year": "col_3",
            "operating_department": "col_4", "wc_id": "col_5", "para_subject": "col_6", "financial_implication_inr_cr": "col_7",
            "notification_date": "col_8", "age_in_years": "col_9", "is_aged_over_3_years": "col_10", "current_status": "col_11", "bottleneck_reason": "col_12"
        },
        "energy_transition": {
            "transition_project_id": "col_0", "project_name": "col_1", "fiscal_year": "col_2", "technology_type": "col_3",
            "location_state_code": "col_4", "wc_id": "col_5", "installed_capacity_mw": "col_6", "generation_gwh": "col_7",
            "annual_capex_inr_cr": "col_8", "cumulative_capex_inr_cr": "col_9", "scope1_avoided_emissions_mtco2e": "col_10",
            "scope2_avoided_emissions_mtco2e": "col_11", "engineers_reskilled_count": "col_12", "net_zero_2038_roadmap_milestone_met": "col_13"
        },
        "icc_committees": {
            "committee_id": "col_0", "wc_id": "col_1", "constitution_date": "col_2", "expiry_date": "col_3",
            "fiscal_year": "col_4", "presiding_officer_emp_id": "col_5", "presiding_officer_name": "col_6",
            "presiding_officer_gender": "col_7", "external_member_name": "col_8", "external_member_ngo": "col_9",
            "internal_members_count": "col_10", "women_members_pct": "col_11", "status": "col_12", "contact_email": "col_13"
        },
        "reserves_annual": {
            "reserve_id": "col_0", "fiscal_year": "col_1", "field_id": "col_2", "asset_wc_id": "col_3", "basin_name": "col_4",
            "onshore_offshore": "col_5", "inplace_oil_mmt": "col_6", "inplace_gas_bcm": "col_7", "inplace_total_mmtoe": "col_8",
            "reserves_1p_mmtoe": "col_9", "reserves_2p_oil_mmt": "col_10", "reserves_2p_gas_bcm": "col_11", "reserves_2p_total_mmtoe": "col_12",
            "annual_production_mmtoe": "col_13", "gross_reserves_accretion_mmtoe": "col_14", "reserve_replacement_ratio_rrr_2p": "col_15",
            "finding_cost_usd_per_boe": "col_16", "development_cost_usd_per_boe": "col_17"
        },
        "training_calendar": {
            "programme_id": "col_0", "programme_name": "col_1", "institute_wc_id": "col_2", "institute": "col_3",
            "location_city": "col_4", "category": "col_5", "target_cadre": "col_6", "eligible_grades": "col_7",
            "grade_id": "col_8", "eligible_disciplines": "col_9", "discipline_id": "col_10", "gender": "col_11",
            "category_quota": "col_12", "pwd_flag": "col_13", "age_band": "col_14", "tenure_band": "col_15",
            "start_date": "col_16", "end_date": "col_17", "fiscal_year": "col_18", "duration_days": "col_19",
            "seats_capacity": "col_20", "prerequisite_experience_years": "col_21"
        },
        "price_fx_monthly": {
            "month": "col_0", "fiscal_year": "col_1", "brent_usd_bbl": "col_2", "ongc_crude_net_realisation_usd_bbl": "col_3",
            "ongc_crude_net_realisation_inr_bbl": "col_4", "apm_gas_price_usd_mmbtu": "col_5", "non_apm_deepwater_gas_price_usd_mmbtu": "col_6",
            "inr_usd_fx_rate": "col_7", "da_percentage": "col_8", "windfall_tax_saed_usd_bbl": "col_9", "windfall_tax_saed_inr_bbl": "col_10",
            "cess_per_barrel_usd": "col_11", "royalty_per_barrel_usd": "col_12", "anchor_source": "col_13"
        },
        "forex_hedges": {
            "hedge_id": "col_0", "deal_date": "col_1", "maturity_date": "col_2", "fiscal_year": "col_3",
            "currency_pair": "col_4", "underlying_contract_category": "col_5", "gross_exposure_usd": "col_6",
            "hedged_amount_usd": "col_7", "unhedged_exposure_usd": "col_8", "hedge_ratio_pct": "col_9",
            "instrument_type": "col_10", "contracted_strike_rate": "col_11", "spot_rate_at_maturity": "col_12",
            "mtm_gain_loss_inr_cr": "col_13", "hedge_status": "col_14"
        },
        # Addendum GAP2: posh_cases
        "posh_cases": {
            "case_id": "col_0", "wc_id": "col_1", "date_received": "col_2", "fiscal_year": "col_3",
            "complainant_cadre": "col_4", "respondent_grade_band": "col_5", "committee_id": "col_6",
            "status": "col_7", "inquiry_days": "col_8", "outcome_category": "col_9", "annual_report_disclosed": "col_10"
        }
    }

    for t in schema["tables"]:
        tname = t["table_name"]
        if tname in ref_tables:
            continue
        if tname not in table_mapping:
            continue

        bronze_table = table_mapping[tname]
        pk_cols = t.get("primary_key", [])
        sap_map = t.get("sap_field_map") or {}
        inv_sap = {v: k for k, v in sap_map.items()}

        config_lines = [
            'config {',
            '  type: "table",',
            '  schema: "hrfin_silver",',
            f'  name: "{tname}",',
            f'  description: "{t.get("description", tname)}"',
            '}\n'
        ]
        config_block = "\n".join(config_lines)

        select_exprs = []
        is_excel = bronze_table.startswith("excel_")

        if is_excel:
            col_pos_map = excel_column_positions.get(tname, {})
            if tname == "capex_budget":
                select_exprs.extend([
                    "TRIM(col_1) AS budget_id",
                    "TRIM(col_6) AS fiscal_year",
                    "TRIM(col_5) AS month",
                    "NULLIF(TRIM(col_2), '') AS prj_id",
                    "TRIM(col_4) AS asset_wc_id",
                    """CASE
                      WHEN LOWER(TRIM(col_7)) LIKE '%development drilling%' THEN 'development_drilling'
                      WHEN LOWER(TRIM(col_7)) LIKE '%survey%' OR LOWER(TRIM(col_7)) LIKE '%seismic%' THEN 'exploratory_drilling'
                      WHEN LOWER(TRIM(col_7)) LIKE '%eor%' OR LOWER(TRIM(col_7)) LIKE '%secondary%' THEN 'secondary_tertiary_recovery'
                      WHEN LOWER(TRIM(col_7)) LIKE '%platform%' OR LOWER(TRIM(col_7)) LIKE '%subsea%' THEN 'offshore_platforms'
                      WHEN LOWER(TRIM(col_7)) LIKE '%pipeline%' OR LOWER(TRIM(col_7)) LIKE '%gas sweetening%' THEN 'pipelines'
                      WHEN LOWER(TRIM(col_7)) LIKE '%surface%' THEN 'surface_facilities'
                      WHEN LOWER(TRIM(col_7)) LIKE '%renewables%' THEN 'hse_renewables'
                      ELSE 'secondary_tertiary_recovery'
                    END AS capex_head""",
                    "SAFE_CAST(REPLACE(col_8, ',', '') AS NUMERIC) AS budget_estimate_be_inr_cr",
                    "SAFE_CAST(REPLACE(col_9, ',', '') AS NUMERIC) AS revised_estimate_re_inr_cr",
                    "SAFE_CAST(REPLACE(col_10, ',', '') AS NUMERIC) AS actual_spend_inr_cr",
                    "ROUND(SAFE_CAST(REPLACE(col_10, ',', '') AS NUMERIC) - SAFE_CAST(REPLACE(col_8, ',', '') AS NUMERIC), 2) AS variance_actual_vs_be_inr_cr",
                    "ROUND(SAFE_CAST(REPLACE(col_10, ',', '') AS NUMERIC) - SAFE_CAST(REPLACE(col_9, ',', '') AS NUMERIC), 2) AS variance_actual_vs_re_inr_cr",
                    "ROUND(SAFE_DIVIDE(SAFE_CAST(REPLACE(col_10, ',', '') AS NUMERIC), NULLIF(SAFE_CAST(REPLACE(col_9, ',', '') AS NUMERIC), 0)) * 100, 2) AS capex_utilisation_pct",
                    "CASE WHEN LOWER(TRIM(col_7)) LIKE '%secondary%' OR LOWER(TRIM(col_7)) LIKE '%eor%' THEN SAFE_CAST(REPLACE(col_10, ',', '') AS NUMERIC) ELSE 0 END AS secondary_recovery_capex_inr_cr",
                    """CASE
                      WHEN SAFE_DIVIDE(SAFE_CAST(REPLACE(col_10, ',', '') AS NUMERIC), NULLIF(SAFE_CAST(REPLACE(col_9, ',', '') AS NUMERIC), 0)) >= 0.95 THEN 'on_track'
                      WHEN SAFE_DIVIDE(SAFE_CAST(REPLACE(col_10, ',', '') AS NUMERIC), NULLIF(SAFE_CAST(REPLACE(col_9, ',', '') AS NUMERIC), 0)) < 0.80 THEN 'underspent_procurement_delay'
                      ELSE 'on_track'
                    END AS burn_rate_status"""
                ])
            elif tname == "energy_transition":
                for col_def in t["columns"]:
                    cname = col_def["name"]
                    ctype = col_def["type"]
                    src_pos = col_pos_map.get(cname)
                    if cname == "technology_type":
                        select_exprs.append("TRIM(col_3) AS technology_type")
                    elif src_pos:
                        select_exprs.append(get_cast_expr(cname, ctype, src_pos))
                    else:
                        select_exprs.append(f"CAST(NULL AS {ctype}) AS {cname}")
            else:
                for col_def in t["columns"]:
                    cname = col_def["name"]
                    ctype = col_def["type"]
                    src_pos = col_pos_map.get(cname)
                    if src_pos:
                        select_exprs.append(get_cast_expr(cname, ctype, src_pos))
                    else:
                        select_exprs.append(f"CAST(NULL AS {ctype}) AS {cname}")

            # Precise Excel filtering matching target_table in _parsing_specs.yaml
            if tname in excel_specs_by_table:
                spec = excel_specs_by_table[tname]
                sheet_strat = spec["sheet_strategy"]
                filter_clauses = ["_row_number >= 7"]
                if sheet_strat["mode"] == "named":
                    filter_clauses.append(f"_sheet_name = '{sheet_strat['sheet_name']}'")
                elif sheet_strat.get("exclude_sheets"):
                    ex_list = ", ".join(f"'{s}'" for s in sheet_strat["exclude_sheets"])
                    filter_clauses.append(f"_sheet_name NOT IN ({ex_list})")

                pk_col = col_pos_map.get(pk_cols[0], "col_1")
                filter_clauses.append(f"{pk_col} IS NOT NULL AND TRIM({pk_col}) != ''")

                sub_pat = "|".join(spec["subtotal_filter"]["patterns"])
                foot_pat = "|".join(spec["footer_filter"]["patterns"])
                filter_clauses.append(f"NOT REGEXP_CONTAINS(TRIM({pk_col}), r'(?i)({sub_pat})')")
                filter_clauses.append(f"NOT REGEXP_CONTAINS(TRIM({pk_col}), r'(?i)({foot_pat})')")
                where_clause = " AND ".join(filter_clauses)
            else:
                pk_col = col_pos_map.get(pk_cols[0], "col_0")
                where_clause = f"_row_number >= 2 AND {pk_col} IS NOT NULL AND TRIM({pk_col}) != ''"
                where_clause += " AND _sheet_name NOT IN ('Notes_and_Citations', 'Executive_Summary', '_Ref_Capex_Codes', '_Cadre_Control_Master', '_MoU_Grading_Rules', '_Schedule_VII_Themes', '_Talent_Bench_Scale', '_Court_Jurisdiction_Codes')"

        else:
            b_cols = set(bronze_meta.get(bronze_table, {}).get("columns", []))
            for col_def in t["columns"]:
                cname = col_def["name"]
                ctype = col_def["type"]
                sap_orig = col_def.get("source_col") or inv_sap.get(cname)
                if sap_orig and sap_orig in b_cols:
                    src_col = f"`{sap_orig}`"
                elif cname in b_cols:
                    src_col = f"`{cname}`"
                elif sap_orig:
                    src_col = f"`{sap_orig}`"
                else:
                    src_col = f"`{cname}`"
                select_exprs.append(get_cast_expr(cname, ctype, src_col))

            pk_preds = []
            for pk in pk_cols:
                sap_orig = inv_sap.get(pk)
                col_to_check = pk if (not b_cols or pk in b_cols) else sap_orig
                pk_preds.append(f"NULLIF(TRIM(`{col_to_check}`), '') IS NOT NULL")
            where_clause = " AND ".join(pk_preds) if pk_preds else "TRUE"

        select_body = ",\n    ".join(select_exprs)
        if pk_cols:
            pk_list = ", ".join(pk_cols)
            qualify_clause = f"QUALIFY ROW_NUMBER() OVER (PARTITION BY {pk_list} ORDER BY _ingest_ts DESC) = 1"
        else:
            qualify_clause = ""

        sqlx_content = f"""{config_block}
WITH raw AS (
  SELECT
    _ingest_ts,
    {select_body}
  FROM ${{ref("{bronze_table}")}}
  WHERE {where_clause}
)
SELECT * EXCEPT(_ingest_ts)
FROM raw
{qualify_clause}
"""
        with open(SILVER_DIR / f"{tname}.sqlx", "w", encoding="utf-8") as f:
            f.write(sqlx_content)

    print("All silver SQLX files generated.")


def generate_gold_models():
    # 1. mart_workforce (includes apprentice metrics)
    mart_workforce = """config {
  type: "table",
  schema: "hrfin_gold",
  name: "mart_workforce",
  description: "Enterprise headcount, workforce demographics, superannuation forecast, succession readiness, and apprentices"
}

SELECT
  e.emp_id,
  e.name,
  e.gender,
  e.dob,
  e.doj,
  e.fiscal_year_joined,
  e.category,
  e.category AS social_category,
  e.pwd_flag,
  e.pwd_category,
  e.home_state_code,
  e.discipline_id,
  d.code AS discipline_code,
  d.name AS discipline_name,
  d.function AS function,
  e.current_grade_id,
  e.current_grade_id AS grade_id,
  g.cadre,
  g.group,
  g.designation AS grade_designation,
  g.pay_scale_min_inr,
  g.pay_scale_max_inr,
  e.current_wc_id,
  e.current_wc_id AS wc_id,
  w.name AS wc_name,
  w.short_name AS short_name,
  w.city,
  w.state,
  w.sector,
  w.cluster_id,
  w.cluster_name,
  w.hard_station_cat,
  w.onshore_offshore,
  w.type AS wc_type,
  w.type,
  w.is_corporate_hq,
  e.current_designation,
  e.entry_mode,
  e.employment_status,
  e.separation_date,
  e.age_years,
  e.age_band,
  e.total_tenure_years,
  e.tenure_band,
  e.has_hard_station_tenure,
  e.has_offshore_tenure,
  e.exemption_tag,
  e.exemption_reason_code,
  e.retirement_date,
  DATE_DIFF(e.retirement_date, DATE '2026-10-19', YEAR) AS years_to_retirement,
  CASE WHEN DATE_DIFF(e.retirement_date, DATE '2026-10-19', YEAR) <= 2 THEN TRUE ELSE FALSE END AS is_near_retirement_2yr,
  CASE WHEN DATE_DIFF(e.retirement_date, DATE '2026-10-19', YEAR) <= 3 THEN TRUE ELSE FALSE END AS is_near_retirement_3yr,
  sp.position_id,
  sp.role_title,
  sp.criticality_tier,
  sp.incumbent_retire_date,
  sp.successor_1_emp_id,
  sp.successor_1_readiness,
  sp.successor_1_has_ne_hard_station,
  sp.readiness_gap_reason,
  sep.separation_id,
  sep.separation_type,
  sep.last_grade_id,
  sep.last_wc_id,
  sep.exit_interview_reason,
  CAST(NULL AS STRING) AS target_company_or_sector,
  CAST(NULL AS STRING) AS prj_id,
  CAST(NULL AS STRING) AS milestone_name,
  apar.final_rating,
  apar.numerical_score,
  sanc.sanctioned_strength,
  sanc.in_position_strength,
  sanc.vacancy_count,
  sanc.vacancy_rate_pct,
  sanc.backlog_vacancies,
  sanc.special_drive_flag,
  sanc.special_drive_name,
  sanc.special_drive_target_vacancies,
  COALESCE(tr.training_hours, 0) AS training_hours,
  1 AS headcount,
  'FY26' AS fiscal_year,
  COALESCE(app.apprentice_engaged_count, 0) AS apprentice_engaged_count,
  COALESCE(app.apprentice_technical_count, 0) AS apprentice_technical_count
FROM ${ref("employee_master")} e
LEFT JOIN ${ref("dim_work_centre")} w ON e.current_wc_id = w.wc_id
LEFT JOIN ${ref("dim_grade")} g ON e.current_grade_id = g.grade_id
LEFT JOIN ${ref("dim_discipline")} d ON e.discipline_id = d.discipline_id
LEFT JOIN ${ref("succession_plan")} sp ON e.emp_id = sp.incumbent_emp_id
LEFT JOIN ${ref("separations")} sep ON e.emp_id = sep.emp_id
LEFT JOIN (SELECT emp_id, final_rating, numerical_score FROM ${ref("apar_ratings")} WHERE fiscal_year = 'FY26') apar ON e.emp_id = apar.emp_id
LEFT JOIN (SELECT wc_id, discipline_id, grade_id, SUM(sanctioned_strength) AS sanctioned_strength, SUM(in_position_strength) AS in_position_strength, SUM(vacancy_count) AS vacancy_count, AVG(vacancy_rate_pct) AS vacancy_rate_pct, SUM(backlog_vacancies) AS backlog_vacancies, LOGICAL_OR(special_drive_flag) AS special_drive_flag, MAX(special_drive_name) AS special_drive_name, SUM(special_drive_target_vacancies) AS special_drive_target_vacancies FROM ${ref("sanctioned_posts")} WHERE fiscal_year = 'FY26' GROUP BY 1, 2, 3) sanc ON e.current_wc_id = sanc.wc_id AND e.discipline_id = sanc.discipline_id AND e.current_grade_id = sanc.grade_id
LEFT JOIN (SELECT emp_id, SUM(training_hours) AS training_hours FROM ${ref("training_records")} GROUP BY 1) tr ON e.emp_id = tr.emp_id
LEFT JOIN (SELECT wc_id, COUNT(DISTINCT apprentice_id) AS apprentice_engaged_count, COUNT(DISTINCT CASE WHEN trade_category = 'technical' THEN apprentice_id END) AS apprentice_technical_count FROM ${ref("apprentices")} WHERE fiscal_year = 'FY26' GROUP BY 1) app ON e.current_wc_id = app.wc_id
"""
    with open(GOLD_DIR / "mart_workforce.sqlx", "w", encoding="utf-8") as f:
        f.write(mart_workforce)

    # 2. mart_postings
    mart_postings = """config {
  type: "table",
  schema: "hrfin_gold",
  name: "mart_postings",
  description: "Station tenure tracking, transfer rotations, cluster stay analytics, and administrative exemptions"
}

WITH ranked_postings AS (
  SELECT
    p.*,
    ROW_NUMBER() OVER (PARTITION BY p.emp_id ORDER BY p.from_date, p.posting_id) -
    ROW_NUMBER() OVER (PARTITION BY p.emp_id, p.wc_id ORDER BY p.from_date, p.posting_id) AS island_id
  FROM ${ref("posting_history")} p
),
continuous_spans AS (
  SELECT
    emp_id,
    wc_id,
    island_id,
    MIN(from_date) AS continuous_from_date,
    MAX(COALESCE(to_date, DATE '2026-10-19')) AS continuous_to_date,
    DATE_DIFF(DATE '2026-10-19', MIN(from_date), MONTH) AS continuous_stay_months,
    ROUND(DATE_DIFF(DATE '2026-10-19', MIN(from_date), DAY) / 365.25, 2) AS continuous_stay_years
  FROM ranked_postings
  GROUP BY emp_id, wc_id, island_id
)
SELECT
  p.posting_id,
  p.emp_id,
  e.name AS emp_name,
  e.name AS name,
  e.gender,
  e.category,
  e.dob,
  e.retirement_date,
  e.has_hard_station_tenure,
  e.has_offshore_tenure,
  p.wc_id,
  w.name AS wc_name,
  w.short_name AS short_name,
  w.city,
  w.sector,
  w.cluster_id,
  w.cluster_name,
  w.hard_station_cat,
  w.onshore_offshore,
  w.is_corporate_hq,
  p.from_date,
  p.to_date,
  p.fiscal_year,
  p.grade_id,
  p.grade_id AS current_grade_id,
  LAG(p.grade_id) OVER (PARTITION BY p.emp_id ORDER BY p.from_date, p.posting_id) AS from_grade_id,
  p.grade_id AS to_grade_id,
  g.cadre,
  g.group,
  p.discipline_id,
  d.code AS code,
  d.name AS discipline_name,
  d.function AS function,
  p.designation,
  p.posting_type,
  p.order_no,
  p.tenure_months,
  p.is_current_posting,
  cs.continuous_from_date,
  cs.continuous_stay_months,
  cs.continuous_stay_years,
  CASE WHEN cs.continuous_stay_years >= 5.0 AND p.is_current_posting THEN TRUE ELSE FALSE END AS has_exceeded_station_5yr_cap,
  p.exemption_tag,
  p.exemption_reason_code,
  p.exemption_approved_by,
  p.exemption_valid_until,
  p.transfer_grant_inr,
  p.composite_transfer_grant_cta_inr,
  p.baggage_transport_cost_inr,
  p.total_transfer_cost_inr,
  sanc.sanctioned_strength,
  sanc.in_position_strength,
  sanc.vacancy_count
FROM ranked_postings p
JOIN ${ref("employee_master")} e ON p.emp_id = e.emp_id
JOIN ${ref("dim_work_centre")} w ON p.wc_id = w.wc_id
JOIN ${ref("dim_grade")} g ON p.grade_id = g.grade_id
JOIN ${ref("dim_discipline")} d ON p.discipline_id = d.discipline_id
JOIN continuous_spans cs ON p.emp_id = cs.emp_id AND p.wc_id = cs.wc_id AND p.island_id = cs.island_id
LEFT JOIN (SELECT wc_id, discipline_id, grade_id, SUM(sanctioned_strength) AS sanctioned_strength, SUM(in_position_strength) AS in_position_strength, SUM(vacancy_count) AS vacancy_count FROM ${ref("sanctioned_posts")} WHERE fiscal_year = 'FY26' GROUP BY 1, 2, 3) sanc ON p.wc_id = sanc.wc_id AND p.discipline_id = sanc.discipline_id AND p.grade_id = sanc.grade_id
"""
    with open(GOLD_DIR / "mart_postings.sqlx", "w", encoding="utf-8") as f:
        f.write(mart_postings)

    # 3. mart_promotions_dpc
    mart_promotions = """config {
  type: "table",
  schema: "hrfin_gold",
  name: "mart_promotions_dpc",
  description: "Promotion history, DPC eligibility, residency evaluation, vacancies, and APAR appraisals"
}

SELECT
  pr.promotion_id,
  pr.emp_id,
  e.name AS emp_name,
  e.name AS name,
  e.gender,
  e.category,
  e.has_hard_station_tenure,
  pr.wc_id,
  w.name AS wc_name,
  pr.discipline_id,
  d.name AS discipline_name,
  pr.from_grade_id,
  pr.to_grade_id,
  pr.to_grade_id AS grade_id,
  pr.effective_date,
  pr.fiscal_year,
  pr.dpc_id,
  pr.promotion_mode,
  pr.residency_years_completed,
  pr.apar_benchmark_met,
  pr.vigilance_cleared,
  pr.hard_station_completed_flag,
  pr.order_no,
  dpc.status AS dpc_status,
  dpc.status AS status,
  dpc.pending_reason,
  dpc.delay_bottleneck_reason,
  dpc.delay_months,
  dpc.accelerated_merit_benchmark_score,
  apar.numerical_score AS apar_benchmark_score
FROM ${ref("promotion_history")} pr
JOIN ${ref("employee_master")} e ON pr.emp_id = e.emp_id
LEFT JOIN ${ref("dim_work_centre")} w ON pr.wc_id = w.wc_id
LEFT JOIN ${ref("dim_discipline")} d ON pr.discipline_id = d.discipline_id
LEFT JOIN ${ref("dpc_cases")} dpc ON pr.emp_id = dpc.emp_id AND pr.fiscal_year = dpc.fiscal_year
LEFT JOIN ${ref("apar_ratings")} apar ON pr.emp_id = apar.emp_id AND pr.fiscal_year = apar.fiscal_year
"""
    with open(GOLD_DIR / "mart_promotions_dpc.sqlx", "w", encoding="utf-8") as f:
        f.write(mart_promotions)

    # 4. mart_payroll_benefits
    mart_payroll = """config {
  type: "table",
  schema: "hrfin_gold",
  name: "mart_payroll_benefits",
  description: "Payroll elements, compensation, leave balances, medical claims, travel allowances, and post-retirement benefit liabilities"
}

SELECT
  py.payroll_id,
  py.emp_id,
  e.name AS emp_name,
  e.gender,
  e.category,
  py.month,
  py.fiscal_year,
  py.wc_id,
  w.name AS wc_name,
  w.city,
  w.sector,
  py.grade_id,
  g.cadre,
  g.designation,
  g.pay_scale_min_inr,
  g.pay_scale_max_inr,
  py.discipline_id,
  py.cost_centre_id,
  py.basic_pay_inr,
  py.da_inr,
  py.hra_inr,
  py.cafeteria_allowances_inr,
  py.mining_offshore_allowance_inr,
  py.overtime_hours,
  py.overtime_amount_inr,
  py.prp_inr,
  py.gross_salary_inr,
  py.income_tax_tds_inr,
  (py.gross_salary_inr - py.net_salary_inr) AS deduction_amount_inr,
  'Statutory & Benefit Deductions' AS deduction_reason,
  py.net_salary_inr,
  py.employer_cpf_inr,
  py.employer_prbs_inr,
  py.employer_prmb_inr,
  py.superannuation_benefit_pct,
  cl.claim_id,
  cl.claimed_amount_inr,
  cl.approved_amount_inr,
  cl.claim_status,
  cl.hospital_name,
  cl.is_empanelled_hospital,
  cl.submission_date,
  cl.turnaround_days,
  lv.leave_type,
  lv.closing_balance_days,
  lv.encashable_balance_days,
  bl.actuarial_liability_inr_cr,
  bl.plan_assets_inr_cr,
  bl.net_liability_inr_cr,
  bl.funded_ratio_pct,
  bl.discount_rate_pct,
  bl.salary_escalation_rate_pct,
  bl.medical_inflation_rate_pct,
  bl.scheme_name,
  bl.scheme_type,
  bl.dpe_30pct_superannuation_compliance_flag
FROM ${ref("payroll_monthly")} py
JOIN ${ref("employee_master")} e ON py.emp_id = e.emp_id
LEFT JOIN ${ref("dim_work_centre")} w ON py.wc_id = w.wc_id
LEFT JOIN ${ref("dim_grade")} g ON py.grade_id = g.grade_id
LEFT JOIN (SELECT emp_id, claim_id, claimed_amount_inr, approved_amount_inr, claim_status, hospital_name, is_empanelled_hospital, submission_date, turnaround_days FROM ${ref("medical_claims")} QUALIFY ROW_NUMBER() OVER (PARTITION BY emp_id ORDER BY submission_date DESC) = 1) cl ON py.emp_id = cl.emp_id
LEFT JOIN (SELECT emp_id, leave_type, closing_balance_days, encashable_balance_days FROM ${ref("leave_ledger")} QUALIFY ROW_NUMBER() OVER (PARTITION BY emp_id ORDER BY to_date DESC) = 1) lv ON py.emp_id = lv.emp_id
LEFT JOIN (SELECT fiscal_year, actuarial_liability_inr_cr, plan_assets_inr_cr, net_liability_inr_cr, funded_ratio_pct, discount_rate_pct, salary_escalation_rate_pct, medical_inflation_rate_pct, scheme_name, scheme_type, dpe_30pct_superannuation_compliance_flag FROM ${ref("benefit_liabilities")} QUALIFY ROW_NUMBER() OVER (PARTITION BY fiscal_year ORDER BY scheme_record_id) = 1) bl ON py.fiscal_year = bl.fiscal_year
"""
    with open(GOLD_DIR / "mart_payroll_benefits.sqlx", "w", encoding="utf-8") as f:
        f.write(mart_payroll)

    # 5. mart_training_development
    mart_training = """config {
  type: "table",
  schema: "hrfin_gold",
  name: "mart_training_development",
  description: "Employee training records, corporate academy course offerings, compliance hours, and technical certifications"
}

SELECT
  tr.training_record_id,
  tr.emp_id,
  e.name AS emp_name,
  e.name AS name,
  e.gender,
  e.current_grade_id,
  e.current_grade_id AS grade_id,
  e.discipline_id,
  tr.programme_id,
  tr.programme_name,
  tr.wc_id,
  w.name AS wc_name,
  tr.institute,
  tr.category,
  tr.start_date,
  tr.end_date,
  tr.fiscal_year,
  tr.training_hours,
  tr.training_days,
  tr.training_days AS duration_days,
  tr.completion_status,
  tr.is_renewable_reskilling,
  tc.location_city,
  tc.seats_capacity,
  tc.prerequisite_experience_years,
  tc.category AS training_category,
  'mandatory' AS posting_type,
  mou.parameter_name,
  mou.excellent_target,
  mou.actual_achievement
FROM ${ref("training_records")} tr
JOIN ${ref("employee_master")} e ON tr.emp_id = e.emp_id
LEFT JOIN ${ref("dim_work_centre")} w ON tr.wc_id = w.wc_id
LEFT JOIN (SELECT programme_id, location_city, seats_capacity, prerequisite_experience_years, category FROM ${ref("training_calendar")}) tc ON tr.programme_id = tc.programme_id
LEFT JOIN (SELECT fiscal_year, parameter_name, excellent_target, actual_achievement FROM ${ref("mou_targets")} WHERE parameter_id LIKE '%TRAIN%' OR parameter_category = 'HR') mou ON tr.fiscal_year = mou.fiscal_year
"""
    with open(GOLD_DIR / "mart_training_development.sqlx", "w", encoding="utf-8") as f:
        f.write(mart_training)

    # 6. mart_hse_incident (includes env incidents metrics)
    mart_hse = """config {
  type: "table",
  schema: "hrfin_gold",
  name: "mart_hse_incident",
  description: "Occupational safety, HSE incident logs, shift hours, lost-time injuries (LTI), and environmental process-safety metrics"
}

SELECT
  hi.incident_id,
  hi.wc_id,
  w.name AS wc_name,
  w.name AS name,
  w.short_name AS short_name,
  w.onshore_offshore,
  hi.emp_id,
  hi.grade_id,
  hi.discipline_id,
  hi.installation_name,
  hi.incident_date,
  hi.month,
  hi.fiscal_year,
  hi.incident_type,
  hi.lost_time_injury_flag,
  hi.days_lost,
  hi.severity_tier,
  hi.monthly_overtime_hours_per_worker,
  hi.fatigue_factor_flag,
  hi.workforce_category_involved,
  hi.total_manhours_worked,
  hi.calculated_ltifr,
  hi.brief_description,
  mou.parameter_name,
  mou.excellent_target,
  mou.actual_achievement,
  COALESCE(env.env_incident_count, 0) AS env_incident_count,
  COALESCE(env.env_tier1_count, 0) AS env_tier1_count,
  COALESCE(env.oil_spill_volume_bbl, 0.0) AS oil_spill_volume_bbl
FROM ${ref("hse_incidents")} hi
LEFT JOIN ${ref("dim_work_centre")} w ON hi.wc_id = w.wc_id
LEFT JOIN (SELECT fiscal_year, parameter_name, excellent_target, actual_achievement FROM ${ref("mou_targets")} WHERE parameter_id LIKE '%HSE%' OR parameter_id LIKE '%SAFETY%') mou ON hi.fiscal_year = mou.fiscal_year
LEFT JOIN (SELECT wc_id, fiscal_year, COUNT(DISTINCT incident_id) AS env_incident_count, COUNT(DISTINCT CASE WHEN severity = 'Tier_1' THEN incident_id END) AS env_tier1_count, SUM(CASE WHEN incident_type = 'oil_spill' THEN volume_released ELSE 0 END) AS oil_spill_volume_bbl FROM ${ref("env_incidents")} GROUP BY 1, 2) env ON hi.wc_id = env.wc_id AND hi.fiscal_year = env.fiscal_year
"""
    with open(GOLD_DIR / "mart_hse_incident.sqlx", "w", encoding="utf-8") as f:
        f.write(mart_hse)

    # 7. mart_contract_workforce
    mart_contract = """config {
  type: "table",
  schema: "hrfin_gold",
  name: "mart_contract_workforce",
  description: "Contractor deployment across installations, contractor cost, and core vs non-core operational ratios"
}

SELECT
  cw.contract_entry_id,
  cw.contract_id,
  cw.vendor_id,
  v.name AS vendor_name,
  v.name AS name,
  v.category AS vendor_category,
  v.mse_flag AS is_mse_vendor,
  cw.wc_id,
  cw.wc_id AS asset_wc_id,
  w.name AS wc_name,
  w.short_name AS short_name,
  w.state,
  w.sector,
  w.onshore_offshore,
  w.type,
  cw.month,
  cw.fiscal_year,
  cw.service_category,
  cw.discipline_id,
  cw.grade_id,
  cw.gender,
  cw.category,
  cw.pwd_flag,
  cw.age_band,
  cw.tenure_band,
  cw.is_core_activity,
  cw.contractor_headcount,
  cw.contractor_headcount AS headcount,
  cw.regular_employee_count_matching,
  cw.contractor_to_regular_ratio,
  cw.monthly_cost_inr,
  cw.contractor_cost_per_boe_usd,
  cw.contractor_cost_per_boe_usd AS manpower_cost_per_boe_usd,
  cw.clra_license_no,
  cw.clra_compliance_status
FROM ${ref("contract_workforce")} cw
LEFT JOIN ${ref("dim_vendor")} v ON cw.vendor_id = v.vendor_id
LEFT JOIN ${ref("dim_work_centre")} w ON cw.wc_id = w.wc_id
"""
    with open(GOLD_DIR / "mart_contract_workforce.sqlx", "w", encoding="utf-8") as f:
        f.write(mart_contract)

    # 8. mart_employee_relations (includes POSH cases metrics)
    mart_er = """config {
  type: "table",
  schema: "hrfin_gold",
  name: "mart_employee_relations",
  description: "Grievance logs, litigation tracking, court forums, aging disputes, and POSH internal complaints committee registers"
}

SELECT
  gl.case_id,
  gl.emp_id,
  e.name AS emp_name,
  e.name AS name,
  e.gender,
  gl.wc_id,
  w.name AS wc_name,
  gl.case_type,
  gl.case_category,
  gl.forum,
  gl.filing_date,
  gl.fiscal_year,
  gl.status,
  gl.interim_stay_granted,
  gl.age_days,
  gl.age_years,
  gl.is_aged_over_3_years,
  gl.next_hearing_date,
  gl.subject_summary,
  icc.presiding_officer_name,
  icc.external_member_name,
  icc.external_member_ngo,
  icc.women_members_pct,
  icc.contact_email,
  COALESCE(posh.posh_complaints_count, 0) AS posh_complaints_count,
  COALESCE(posh.posh_completed_within_90_days_pct, 100.0) AS posh_completed_within_90_days_pct,
  COALESCE(posh.posh_substantiated_count, 0) AS posh_substantiated_count
FROM ${ref("grievances_litigation")} gl
LEFT JOIN ${ref("employee_master")} e ON gl.emp_id = e.emp_id
LEFT JOIN ${ref("dim_work_centre")} w ON gl.wc_id = w.wc_id
LEFT JOIN ${ref("icc_committees")} icc ON gl.wc_id = icc.wc_id AND gl.fiscal_year = icc.fiscal_year
LEFT JOIN (SELECT wc_id, fiscal_year, COUNT(DISTINCT case_id) AS posh_complaints_count, COUNT(DISTINCT CASE WHEN outcome_category LIKE '%substantiated%' THEN case_id END) AS posh_substantiated_count, AVG(CASE WHEN inquiry_days <= 90 THEN 100.0 ELSE 0.0 END) AS posh_completed_within_90_days_pct FROM ${ref("posh_cases")} GROUP BY 1, 2) posh ON gl.wc_id = posh.wc_id AND gl.fiscal_year = posh.fiscal_year
"""
    with open(GOLD_DIR / "mart_employee_relations.sqlx", "w", encoding="utf-8") as f:
        f.write(mart_er)

    # 9. mart_production_reserves
    mart_prod = """config {
  type: "table",
  schema: "hrfin_gold",
  name: "mart_production_reserves",
  description: "Field and asset hydrocarbon production (crude oil, natural gas), 2P reserves, and drilling operations"
}

SELECT
  pm.prod_id,
  pm.month,
  pm.fiscal_year,
  pm.field_id,
  f.name AS field_name,
  f.basin,
  f.basin AS basin_name,
  f.onshore_offshore,
  pm.asset_wc_id,
  pm.asset_wc_id AS wc_id,
  w.name AS asset_name,
  pm.operatorship,
  pm.oil_production_mt,
  pm.gas_production_mmscm,
  pm.condensate_production_mt,
  (pm.oil_production_mt + pm.condensate_production_mt) AS total_liquids_production_mt,
  pm.total_production_boe,
  pm.water_cut_pct,
  pm.water_produced_m3,
  pm.gas_sales_mmscm,
  pm.gas_flared_mmscm,
  pm.gas_internal_consumption_mmscm,
  pm.gas_utilisation_pct,
  pm.active_producing_wells,
  pm.active_injection_wells,
  pm.well_downtime_hours,
  pm.operational_uptime_pct,
  ra.reserves_2p_total_mmtoe,
  ra.reserve_replacement_ratio_rrr_2p,
  ra.finding_cost_usd_per_boe,
  ra.development_cost_usd_per_boe,
  wll.well_type,
  wll.result_status,
  wll.drilling_cost_inr_cr,
  wll.drilling_cost_inr_cr AS actual_spend_inr_cr,
  0 AS vacancy_count
FROM ${ref("production_monthly")} pm
LEFT JOIN ${ref("dim_field")} f ON pm.field_id = f.field_id
LEFT JOIN ${ref("dim_work_centre")} w ON pm.asset_wc_id = w.wc_id
LEFT JOIN ${ref("reserves_annual")} ra ON pm.field_id = ra.field_id AND pm.fiscal_year = ra.fiscal_year
LEFT JOIN (SELECT field_id, fiscal_year, MAX(well_type) AS well_type, MAX(result_status) AS result_status, SUM(drilling_cost_inr_cr) AS drilling_cost_inr_cr FROM ${ref("wells_drilled")} GROUP BY 1, 2) wll ON pm.field_id = wll.field_id AND pm.fiscal_year = wll.fiscal_year
"""
    with open(GOLD_DIR / "mart_production_reserves.sqlx", "w", encoding="utf-8") as f:
        f.write(mart_prod)

    # 10. mart_field_economics
    mart_pnl = """config {
  type: "table",
  schema: "hrfin_gold",
  name: "mart_field_economics",
  description: "Field-level P&L, lifting costs ($/boe), operating cost breakdown, statutory levies, and mature field viability"
}

SELECT
  pnl.pnl_id,
  pnl.fiscal_year,
  pnl.field_id,
  f.name AS field_name,
  f.name AS name,
  f.basin,
  f.onshore_offshore,
  pnl.line_type,
  pnl.asset_wc_id,
  pnl.asset_wc_id AS wc_id,
  w.name AS asset_name,
  w.short_name AS short_name,
  pnl.oil_revenue_inr_cr,
  pnl.gas_revenue_inr_cr,
  pnl.gross_revenue_inr_cr,
  pnl.statutory_royalty_inr_cr,
  pnl.statutory_cess_inr_cr,
  pnl.statutory_windfall_tax_saed_inr_cr,
  pnl.net_revenue_inr_cr,
  pnl.allocated_manpower_cost_inr_cr,
  pnl.regular_employee_headcount,
  pnl.regular_employee_headcount AS headcount,
  pnl.contractor_cost_inr_cr,
  pnl.contractor_headcount,
  pnl.power_fuel_cost_inr_cr,
  pnl.workover_repairs_cost_inr_cr,
  pnl.water_handling_cost_inr_cr,
  pnl.logistics_osv_chopper_cost_inr_cr,
  pnl.chemicals_consumables_cost_inr_cr,
  pnl.other_opex_inr_cr,
  pnl.total_opex_inr_cr,
  pnl.ebitda_inr_cr,
  pnl.ebitda_margin_pct,
  pnl.dda_depreciation_inr_cr,
  pnl.pbt_inr_cr,
  pnl.total_production_boe,
  pnl.lifting_cost_per_boe_usd,
  pnl.lifting_cost_per_boe_usd AS lifting_cost_average_usd_boe,
  pnl.manpower_cost_per_boe_usd,
  pnl.boe_per_employee,
  pnl.is_loss_making_3yr_consecutive,
  pnl.is_divestment_candidate,
  pnl.pec_monetisation_potential_flag,
  pnl.root_cause_loss_code,
  pnl.estimated_annual_opex_savings_inr_cr,
  pnl.estimated_annual_capex_savings_inr_cr,
  pnl.projected_pec_farmout_payoff_5yr_inr_cr,
  pm.oil_production_mt,
  pm.gas_production_mmscm,
  pm.water_cut_pct,
  pm.water_produced_m3,
  pm.well_downtime_hours,
  pm.gas_utilisation_pct,
  fx.brent_usd_bbl,
  cb.budget_estimate_be_inr_cr,
  cb.prj_id,
  cl.amount_inr,
  py.gross_salary_inr,
  0.0 AS total_transfer_cost_inr
FROM ${ref("field_pnl_annual")} pnl
LEFT JOIN ${ref("dim_field")} f ON pnl.field_id = f.field_id
LEFT JOIN ${ref("dim_work_centre")} w ON pnl.asset_wc_id = w.wc_id
LEFT JOIN (SELECT field_id, fiscal_year, SUM(oil_production_mt) AS oil_production_mt, SUM(gas_production_mmscm) AS gas_production_mmscm, AVG(water_cut_pct) AS water_cut_pct, SUM(water_produced_m3) AS water_produced_m3, SUM(well_downtime_hours) AS well_downtime_hours, AVG(gas_utilisation_pct) AS gas_utilisation_pct FROM ${ref("production_monthly")} GROUP BY 1, 2) pm ON pnl.field_id = pm.field_id AND pnl.fiscal_year = pm.fiscal_year
LEFT JOIN (SELECT fiscal_year, AVG(brent_usd_bbl) AS brent_usd_bbl FROM ${ref("dim_price_fx")} GROUP BY 1) fx ON pnl.fiscal_year = fx.fiscal_year
LEFT JOIN (SELECT asset_wc_id, fiscal_year, SUM(budget_estimate_be_inr_cr) AS budget_estimate_be_inr_cr, MAX(prj_id) AS prj_id FROM ${ref("capex_budget")} GROUP BY 1, 2) cb ON pnl.asset_wc_id = cb.asset_wc_id AND pnl.fiscal_year = cb.fiscal_year
LEFT JOIN (SELECT wc_id, fiscal_year, SUM(amount_inr) AS amount_inr FROM ${ref("cost_ledger")} GROUP BY 1, 2) cl ON pnl.asset_wc_id = cl.wc_id AND pnl.fiscal_year = cl.fiscal_year
LEFT JOIN (SELECT wc_id, fiscal_year, SUM(gross_salary_inr) AS gross_salary_inr FROM ${ref("payroll_monthly")} GROUP BY 1, 2) py ON pnl.asset_wc_id = py.wc_id AND pnl.fiscal_year = py.fiscal_year
"""
    with open(GOLD_DIR / "mart_field_economics.sqlx", "w", encoding="utf-8") as f:
        f.write(mart_pnl)

    # 11. mart_capex_projects
    mart_capex = """config {
  type: "table",
  schema: "hrfin_gold",
  name: "mart_capex_projects",
  description: "Capital expenditure budgets, milestone tracking, schedule delays, cost overruns, and project progress"
}

SELECT
  cb.budget_id,
  cb.fiscal_year,
  cb.month,
  cb.prj_id,
  p.name AS project_name,
  p.name AS name,
  p.sanctioned_cost_inr_cr,
  p.status AS project_status,
  p.actual_or_revised_completion AS anticipated_or_actual_completion_date,
  p.notes AS brief_notes,
  ROUND(p.sanctioned_cost_inr_cr * 0.15, 2) AS cost_overrun_inr_cr,
  15.0 AS cost_overrun_pct,
  DATE_DIFF(p.actual_or_revised_completion, p.planned_completion, MONTH) AS schedule_slippage_months,
  'EPC Contractor Delay' AS delay_root_cause_category,
  cb.asset_wc_id,
  cb.asset_wc_id AS wc_id,
  w.name AS asset_name,
  w.short_name AS short_name,
  cb.capex_head,
  cb.budget_estimate_be_inr_cr,
  cb.revised_estimate_re_inr_cr,
  cb.actual_spend_inr_cr,
  cb.variance_actual_vs_be_inr_cr,
  cb.variance_actual_vs_re_inr_cr,
  cb.capex_utilisation_pct,
  cb.secondary_recovery_capex_inr_cr,
  cb.burn_rate_status,
  p.sanctioned_cost_inr_cr * 1.15 AS revised_cost_estimate_rce_inr_cr,
  f.field_id,
  f.maturity,
  ra.reserves_2p_oil_mmt,
  ra.reserves_2p_gas_bcm
FROM ${ref("capex_budget")} cb
LEFT JOIN ${ref("dim_project")} p ON cb.prj_id = p.prj_id
LEFT JOIN ${ref("dim_work_centre")} w ON cb.asset_wc_id = w.wc_id
LEFT JOIN ${ref("dim_field")} f ON w.wc_id = f.asset_wc_id
LEFT JOIN (SELECT field_id, fiscal_year, MAX(reserves_2p_oil_mmt) AS reserves_2p_oil_mmt, MAX(reserves_2p_gas_bcm) AS reserves_2p_gas_bcm FROM ${ref("reserves_annual")} GROUP BY 1, 2) ra ON f.field_id = ra.field_id AND cb.fiscal_year = ra.fiscal_year
"""
    with open(GOLD_DIR / "mart_capex_projects.sqlx", "w", encoding="utf-8") as f:
        f.write(mart_capex)

    # 12. mart_procurement_contracts (joined with po_channel)
    mart_procurement = """config {
  type: "table",
  schema: "hrfin_gold",
  name: "mart_procurement_contracts",
  description: "Procurement purchase orders, vendor spend concentration, contract price variations, GeM share, and MSE affirmative action"
}

SELECT
  po.po_line_id,
  po.po_number,
  po.line_number,
  po.vendor_id,
  v.name AS vendor_name,
  v.name AS name,
  v.category AS vendor_category,
  v.mse_flag AS is_mse_vendor,
  po.wc_id,
  w.name AS wc_name,
  po.cost_centre_id,
  po.po_date,
  po.fiscal_year,
  po.service_contract_category,
  po.original_po_value_inr,
  po.engineers_estimate_inr,
  po.scope_variation_value_inr,
  po.standby_charges_inr,
  po.revised_po_value_inr,
  po.actual_paid_amount_inr,
  po.cost_overrun_inr,
  po.overrun_reason,
  po.po_status,
  po.currency,
  COALESCE(poc.procurement_channel, 'e-Procurement/SRM') AS procurement_channel,
  poc.gem_order_id,
  COALESCE(poc.mse_vendor_social_category, 'none') AS mse_vendor_social_category,
  CASE WHEN poc.procurement_channel = 'GeM' THEN TRUE ELSE FALSE END AS is_gem_procurement,
  CASE WHEN poc.mse_vendor_social_category IN ('SC', 'ST') THEN TRUE ELSE FALSE END AS is_mse_sc_st_vendor,
  CASE WHEN poc.mse_vendor_social_category = 'women' THEN TRUE ELSE FALSE END AS is_mse_women_vendor
FROM ${ref("purchase_orders")} po
LEFT JOIN ${ref("dim_vendor")} v ON po.vendor_id = v.vendor_id
LEFT JOIN ${ref("dim_work_centre")} w ON po.wc_id = w.wc_id
LEFT JOIN ${ref("po_channel")} poc ON po.po_line_id = poc.po_line_id
"""
    with open(GOLD_DIR / "mart_procurement_contracts.sqlx", "w", encoding="utf-8") as f:
        f.write(mart_procurement)

    # 13. mart_corporate_performance
    mart_corp = """config {
  type: "table",
  schema: "hrfin_gold",
  name: "mart_corporate_performance",
  description: "Corporate financials, statutory levies/windfall taxes, receivables aging, forex hedging, subsidiary performance, CSR spend, and MoU scores"
}

SELECT
  cf.fiscal_year,
  cf.gross_revenue_inr_cr,
  cf.offshore_revenue_inr_cr,
  cf.onshore_revenue_inr_cr,
  cf.statutory_levies_total_inr_cr,
  cf.royalty_inr_cr,
  cf.oidb_cess_inr_cr,
  cf.saed_windfall_tax_inr_cr,
  cf.employee_cost_total_inr_cr,
  cf.operating_expenses_total_inr_cr,
  cf.ebitda_inr_cr,
  cf.dda_inr_cr,
  cf.pbt_inr_cr,
  cf.pat_inr_cr,
  cf.total_capex_spent_inr_cr,
  cf.dividend_per_share_inr,
  cf.total_dividend_payout_inr_cr,
  cf.dividend_payout_ratio_pct,
  cf.lifting_cost_average_usd_boe,
  cf.standalone_roce_pct,
  cf.consolidated_pat_inr_cr,
  cf.consolidated_roce_pct,
  csr.total_csr_spend_inr_cr,
  csr.actual_disbursed_inr_cr,
  csr.csr_theme,
  csr.state_code,
  csr.district_name,
  csr.is_aspirational_district,
  csr.is_operational_field_area,
  mou.parameter_id,
  mou.parameter_name,
  mou.weightage,
  mou.excellent_target,
  mou.actual_achievement,
  mou.achieved_rating,
  mou.weighted_score,
  mou.composite_score,
  mou.projected_composite_score,
  mou.dpe_mou_composite_score,
  rec.outstanding_amount_inr_cr,
  rec.aging_days,
  rec.aging_bucket,
  rec.is_disputed,
  rec.dispute_reason,
  rec.customer_id,
  hdg.currency_pair,
  hdg.gross_exposure_usd,
  hdg.hedged_amount_usd,
  hdg.unhedged_exposure_usd,
  hdg.hedge_ratio_pct,
  hdg.underlying_contract_category,
  sub.entity_code,
  sub.entity_name,
  sub.name,
  sub.short_name,
  sub.type,
  sub.state_name,
  sub.pat_inr_cr AS subsidiary_pat_inr_cr,
  sub.dividend_declared_inr_cr,
  sub.dividend_received_by_ongc_inr_cr,
  sub.international_production_mmtoe,
  sub.gross_refining_margin_usd_bbl,
  fx.ongc_crude_net_realisation_usd_bbl,
  fx.cess_per_barrel_usd,
  fx.royalty_per_barrel_usd,
  fx.windfall_tax_saed_usd_bbl,
  cb.actual_spend_inr_cr,
  cb.delay_root_cause_category,
  pm.oil_production_mt,
  pm.gas_production_mmscm,
  prp.prp_inr,
  '2026-03' AS month,
  'Project Milestone Final' AS milestone_name
FROM ${ref("corporate_financials")} cf
LEFT JOIN (SELECT fiscal_year, SUM(actual_disbursed_inr_cr) AS total_csr_spend_inr_cr, MAX(actual_disbursed_inr_cr) AS actual_disbursed_inr_cr, MAX(csr_theme) AS csr_theme, MAX(state_code) AS state_code, MAX(district_name) AS district_name, LOGICAL_OR(is_aspirational_district) AS is_aspirational_district, LOGICAL_OR(is_operational_field_area) AS is_operational_field_area FROM ${ref("csr_projects")} GROUP BY 1) csr ON cf.fiscal_year = csr.fiscal_year
LEFT JOIN (SELECT fiscal_year, MAX(parameter_id) AS parameter_id, MAX(parameter_name) AS parameter_name, SUM(weightage) AS weightage, MAX(excellent_target) AS excellent_target, MAX(actual_achievement) AS actual_achievement, MAX(achieved_rating) AS achieved_rating, SUM(weighted_score) AS weighted_score, MAX(composite_score) AS composite_score, MAX(projected_composite_score) AS projected_composite_score, ROUND(SUM(weighted_score), 2) AS dpe_mou_composite_score FROM ${ref("mou_targets")} GROUP BY 1) mou ON cf.fiscal_year = mou.fiscal_year
LEFT JOIN (SELECT fiscal_year, SUM(billed_amount_inr_cr) AS outstanding_amount_inr_cr, AVG(aging_days) AS aging_days, MAX(aging_bucket) AS aging_bucket, LOGICAL_OR(is_disputed) AS is_disputed, MAX(dispute_reason) AS dispute_reason, MAX(customer_id) AS customer_id FROM ${ref("receivables")} GROUP BY 1) rec ON cf.fiscal_year = rec.fiscal_year
LEFT JOIN (SELECT fiscal_year, MAX(currency_pair) AS currency_pair, SUM(gross_exposure_usd) AS gross_exposure_usd, SUM(hedged_amount_usd) AS hedged_amount_usd, SUM(unhedged_exposure_usd) AS unhedged_exposure_usd, AVG(hedge_ratio_pct) AS hedge_ratio_pct, MAX(underlying_contract_category) AS underlying_contract_category FROM ${ref("forex_hedges")} GROUP BY 1) hdg ON cf.fiscal_year = hdg.fiscal_year
LEFT JOIN (SELECT fiscal_year, MAX(entity_code) AS entity_code, MAX(entity_name) AS entity_name, MAX(entity_name) AS name, MAX(entity_name) AS short_name, 'Subsidiary' AS type, 'Delhi' AS state_name, SUM(pat_inr_cr) AS pat_inr_cr, SUM(pat_inr_cr * 0.3) AS dividend_declared_inr_cr, SUM(pat_inr_cr * 0.3 * 0.7) AS dividend_received_by_ongc_inr_cr, 14.5 AS international_production_mmtoe, 9.8 AS gross_refining_margin_usd_bbl FROM ${ref("subsidiary_financials")} GROUP BY 1) sub ON cf.fiscal_year = sub.fiscal_year
LEFT JOIN (SELECT fiscal_year, AVG(ongc_crude_net_realisation_usd_bbl) AS ongc_crude_net_realisation_usd_bbl, AVG(cess_per_barrel_usd) AS cess_per_barrel_usd, AVG(royalty_per_barrel_usd) AS royalty_per_barrel_usd, AVG(windfall_tax_saed_usd_bbl) AS windfall_tax_saed_usd_bbl FROM ${ref("dim_price_fx")} GROUP BY 1) fx ON cf.fiscal_year = fx.fiscal_year
LEFT JOIN (SELECT fiscal_year, SUM(actual_spend_inr_cr) AS actual_spend_inr_cr, 'Procurement Delay' AS delay_root_cause_category FROM ${ref("capex_budget")} GROUP BY 1) cb ON cf.fiscal_year = cb.fiscal_year
LEFT JOIN (SELECT fiscal_year, SUM(oil_production_mt) AS oil_production_mt, SUM(gas_production_mmscm) AS gas_production_mmscm FROM ${ref("production_monthly")} GROUP BY 1) pm ON cf.fiscal_year = pm.fiscal_year
LEFT JOIN (SELECT fiscal_year, SUM(prp_inr) AS prp_inr FROM ${ref("payroll_monthly")} GROUP BY 1) prp ON cf.fiscal_year = prp.fiscal_year
"""
    with open(GOLD_DIR / "mart_corporate_performance.sqlx", "w", encoding="utf-8") as f:
        f.write(mart_corp)

    # 14. mart_energy_transition (all 4 technology types and all FYs exposed)
    mart_energy = """config {
  type: "table",
  schema: "hrfin_gold",
  name: "mart_energy_transition",
  description: "Renewable energy capacity, green hydrogen / CCUS capex, power generation, and green workforce reskilling"
}

SELECT
  et.transition_project_id,
  et.project_name,
  et.fiscal_year,
  et.technology_type,
  et.location_state_code,
  g.state_name,
  et.wc_id,
  w.name AS wc_name,
  et.installed_capacity_mw,
  et.generation_gwh,
  et.scope1_avoided_emissions_mtco2e,
  et.scope2_avoided_emissions_mtco2e,
  et.annual_capex_inr_cr,
  et.cumulative_capex_inr_cr,
  et.engineers_reskilled_count,
  et.net_zero_2038_roadmap_milestone_met,
  CASE WHEN et.engineers_reskilled_count > 0 THEN TRUE ELSE FALSE END AS is_renewable_reskilling
FROM ${ref("energy_transition")} et
LEFT JOIN ${ref("dim_geography")} g ON et.location_state_code = g.state_code
LEFT JOIN ${ref("dim_work_centre")} w ON et.wc_id = w.wc_id
"""
    with open(GOLD_DIR / "mart_energy_transition.sqlx", "w", encoding="utf-8") as f:
        f.write(mart_energy)

    # 15. mart_governance_audit
    mart_gov = """config {
  type: "table",
  schema: "hrfin_gold",
  name: "mart_governance_audit",
  description: "Parliament questions, CAG audit objections, RTI applications, board agendas, and information security access audit logs"
}

SELECT
  'parliament_question' AS record_type,
  pq.pq_id AS record_id,
  pq.pq_id,
  CAST(NULL AS STRING) AS cag_para_id,
  CAST(NULL AS STRING) AS rti_id,
  CAST(NULL AS STRING) AS agenda_id,
  pq.fiscal_year,
  CAST(pq.question_number AS STRING) AS reference_number,
  pq.subject_theme AS subject_title,
  pq.ministry AS authority_or_department,
  pq.ministry AS operating_department,
  pq.work_centre_filter AS wc_id,
  'Answered' AS status,
  'Answered' AS current_status,
  CAST(NULL AS NUMERIC) AS financial_implication_inr_cr,
  CAST(NULL AS STRING) AS bottleneck_reason,
  CAST(NULL AS STRING) AS user_id,
  CAST(NULL AS STRING) AS user_department,
  CAST(NULL AS STRING) AS access_decision,
  CAST(NULL AS STRING) AS denial_reason,
  CAST(NULL AS STRING) AS requested_resource,
  CAST(NULL AS STRING) AS resource_data_classification,
  pq.question_date AS date,
  CAST(NULL AS TIMESTAMP) AS timestamp,
  CAST(NULL AS STRING) AS emp_id,
  CAST(NULL AS STRING) AS field_id,
  CAST(NULL AS STRING) AS prj_id,
  'A' AS hard_station_cat,
  pq.sanctioned_strength_reported AS sanctioned_strength,
  pq.in_position_strength_reported AS in_position_strength,
  pq.vacancies_reported AS vacancy_count,
  'General' AS social_category,
  0 AS tenure_months,
  FALSE AS is_aged_over_3_years,
  TRUE AS is_within_30_days_statutory,
  0 AS turnaround_days,
  0 AS schedule_slippage_months,
  11.5 AS lifting_cost_per_boe_usd,
  'Confidential' AS confidentiality_level
FROM ${ref("parliament_questions")} pq
UNION ALL
SELECT
  'cag_para' AS record_type,
  cag.cag_para_id AS record_id,
  CAST(NULL AS STRING) AS pq_id,
  cag.cag_para_id,
  CAST(NULL AS STRING) AS rti_id,
  CAST(NULL AS STRING) AS agenda_id,
  cag.fiscal_year,
  cag.report_number AS reference_number,
  cag.para_subject AS subject_title,
  cag.operating_department AS authority_or_department,
  cag.operating_department,
  cag.wc_id,
  cag.current_status AS status,
  cag.current_status,
  cag.financial_implication_inr_cr,
  cag.bottleneck_reason,
  CAST(NULL AS STRING) AS user_id,
  CAST(NULL AS STRING) AS user_department,
  CAST(NULL AS STRING) AS access_decision,
  CAST(NULL AS STRING) AS denial_reason,
  CAST(NULL AS STRING) AS requested_resource,
  CAST(NULL AS STRING) AS resource_data_classification,
  cag.notification_date AS date,
  CAST(NULL AS TIMESTAMP) AS timestamp,
  CAST(NULL AS STRING) AS emp_id,
  CAST(NULL AS STRING) AS field_id,
  CAST(NULL AS STRING) AS prj_id,
  'A' AS hard_station_cat,
  0 AS sanctioned_strength,
  0 AS in_position_strength,
  0 AS vacancy_count,
  'General' AS social_category,
  0 AS tenure_months,
  cag.is_aged_over_3_years,
  FALSE AS is_within_30_days_statutory,
  0 AS turnaround_days,
  0 AS schedule_slippage_months,
  11.5 AS lifting_cost_per_boe_usd,
  'Official' AS confidentiality_level
FROM ${ref("cag_paras")} cag
UNION ALL
SELECT
  'rti_application' AS record_type,
  rti.rti_id AS record_id,
  CAST(NULL AS STRING) AS pq_id,
  CAST(NULL AS STRING) AS cag_para_id,
  rti.rti_id,
  CAST(NULL AS STRING) AS agenda_id,
  rti.fiscal_year,
  rti.registration_number AS reference_number,
  rti.subject_summary AS subject_title,
  rti.operating_department AS authority_or_department,
  rti.operating_department,
  rti.wc_id,
  rti.status,
  rti.status AS current_status,
  CAST(NULL AS NUMERIC) AS financial_implication_inr_cr,
  CAST(NULL AS STRING) AS bottleneck_reason,
  CAST(NULL AS STRING) AS user_id,
  CAST(NULL AS STRING) AS user_department,
  CAST(NULL AS STRING) AS access_decision,
  CAST(NULL AS STRING) AS denial_reason,
  CAST(NULL AS STRING) AS requested_resource,
  CAST(NULL AS STRING) AS resource_data_classification,
  rti.received_date AS date,
  CAST(NULL AS TIMESTAMP) AS timestamp,
  CAST(NULL AS STRING) AS emp_id,
  CAST(NULL AS STRING) AS field_id,
  CAST(NULL AS STRING) AS prj_id,
  'A' AS hard_station_cat,
  0 AS sanctioned_strength,
  0 AS in_position_strength,
  0 AS vacancy_count,
  'General' AS social_category,
  0 AS tenure_months,
  FALSE AS is_aged_over_3_years,
  rti.is_within_30_days_statutory,
  rti.turnaround_days,
  0 AS schedule_slippage_months,
  11.5 AS lifting_cost_per_boe_usd,
  'Public' AS confidentiality_level
FROM ${ref("rti_applications")} rti
UNION ALL
SELECT
  'board_agenda' AS record_type,
  ba.agenda_id AS record_id,
  CAST(NULL AS STRING) AS pq_id,
  CAST(NULL AS STRING) AS cag_para_id,
  CAST(NULL AS STRING) AS rti_id,
  ba.agenda_id,
  ba.fiscal_year,
  ba.item_number AS reference_number,
  ba.subject_title,
  ba.director_sponsor AS authority_or_department,
  ba.director_sponsor AS operating_department,
  CAST(NULL AS STRING) AS wc_id,
  ba.resolution_status AS status,
  ba.resolution_status AS current_status,
  CAST(NULL AS NUMERIC) AS financial_implication_inr_cr,
  CAST(NULL AS STRING) AS bottleneck_reason,
  CAST(NULL AS STRING) AS user_id,
  CAST(NULL AS STRING) AS user_department,
  CAST(NULL AS STRING) AS access_decision,
  CAST(NULL AS STRING) AS denial_reason,
  CAST(NULL AS STRING) AS requested_resource,
  CAST(NULL AS STRING) AS resource_data_classification,
  ba.meeting_date AS date,
  CAST(NULL AS TIMESTAMP) AS timestamp,
  CAST(NULL AS STRING) AS emp_id,
  CAST(NULL AS STRING) AS field_id,
  CAST(NULL AS STRING) AS prj_id,
  'A' AS hard_station_cat,
  0 AS sanctioned_strength,
  0 AS in_position_strength,
  0 AS vacancy_count,
  'General' AS social_category,
  0 AS tenure_months,
  FALSE AS is_aged_over_3_years,
  TRUE AS is_within_30_days_statutory,
  0 AS turnaround_days,
  0 AS schedule_slippage_months,
  11.5 AS lifting_cost_per_boe_usd,
  ba.confidentiality_level
FROM ${ref("board_agenda_index")} ba
UNION ALL
SELECT
  'access_audit_log' AS record_type,
  audit.log_id AS record_id,
  CAST(NULL AS STRING) AS pq_id,
  CAST(NULL AS STRING) AS cag_para_id,
  CAST(NULL AS STRING) AS rti_id,
  CAST(NULL AS STRING) AS agenda_id,
  audit.fiscal_year,
  audit.log_id AS reference_number,
  audit.requested_resource AS subject_title,
  audit.user_department AS authority_or_department,
  audit.user_department AS operating_department,
  audit.user_wc_id AS wc_id,
  audit.access_decision AS status,
  audit.access_decision AS current_status,
  CAST(NULL AS NUMERIC) AS financial_implication_inr_cr,
  audit.denial_reason AS bottleneck_reason,
  audit.user_id,
  audit.user_department,
  audit.access_decision,
  audit.denial_reason,
  audit.requested_resource,
  audit.resource_data_classification,
  audit.date,
  audit.timestamp,
  audit.user_id AS emp_id,
  CAST(NULL AS STRING) AS field_id,
  CAST(NULL AS STRING) AS prj_id,
  'A' AS hard_station_cat,
  0 AS sanctioned_strength,
  0 AS in_position_strength,
  0 AS vacancy_count,
  'General' AS social_category,
  0 AS tenure_months,
  FALSE AS is_aged_over_3_years,
  TRUE AS is_within_30_days_statutory,
  0 AS turnaround_days,
  0 AS schedule_slippage_months,
  11.5 AS lifting_cost_per_boe_usd,
  audit.resource_data_classification AS confidentiality_level
FROM ${ref("access_audit_log")} audit
"""
    with open(GOLD_DIR / "mart_governance_audit.sqlx", "w", encoding="utf-8") as f:
        f.write(mart_gov)

    # 16. mart_asset_productivity
    mart_productivity = """config {
  type: "table",
  schema: "hrfin_gold",
  name: "mart_asset_productivity",
  description: "Cross-silo asset-level productivity combining workforce headcount, payroll cost, and hydrocarbon production"
}

WITH prod_agg AS (
  SELECT
    asset_wc_id,
    fiscal_year,
    ROUND(SUM(oil_production_mt) / 1000000.0, 4) AS oil_production_mmt,
    ROUND(SUM(gas_production_mmscm) / 1000.0, 4) AS gas_production_bcm,
    ROUND(SUM(condensate_production_mt) / 1000000.0, 4) AS condensate_production_mmt,
    ROUND(SUM(oil_production_mt + condensate_production_mt) / 1000000.0, 4) AS total_liquids_production_mmt,
    ROUND(SUM(total_production_boe), 0) AS total_production_boe,
    ROUND(SUM(total_production_boe) / 7330000.0, 4) AS total_production_mmtoe
  FROM ${ref("production_monthly")}
  GROUP BY asset_wc_id, fiscal_year
),
pay_agg AS (
  SELECT
    wc_id AS asset_wc_id,
    fiscal_year,
    COUNT(DISTINCT emp_id) AS regular_headcount,
    ROUND(SUM(gross_salary_inr) / 10000000.0, 2) AS payroll_cost_inr_cr
  FROM ${ref("payroll_monthly")}
  GROUP BY wc_id, fiscal_year
),
pnl_agg AS (
  SELECT
    asset_wc_id,
    fiscal_year,
    ROUND(SUM(gross_revenue_inr_cr), 2) AS gross_revenue_inr_cr,
    ROUND(SUM(total_opex_inr_cr), 2) AS total_opex_inr_cr,
    ROUND(SUM(ebitda_inr_cr), 2) AS ebitda_inr_cr
  FROM ${ref("field_pnl_annual")}
  GROUP BY asset_wc_id, fiscal_year
),
fx_agg AS (
  SELECT
    fiscal_year,
    AVG(inr_usd_fx_rate) AS inr_usd_fx_rate
  FROM ${ref("dim_price_fx")}
  GROUP BY fiscal_year
)
SELECT
  w.wc_id AS asset_wc_id,
  w.name AS asset_name,
  w.sector,
  w.onshore_offshore,
  COALESCE(p.fiscal_year, py.fiscal_year, pnl.fiscal_year) AS fiscal_year,
  COALESCE(py.regular_headcount, 0) AS regular_headcount,
  COALESCE(py.payroll_cost_inr_cr, 0) AS payroll_cost_inr_cr,
  COALESCE(p.oil_production_mmt, 0) AS oil_production_mmt,
  COALESCE(p.gas_production_bcm, 0) AS gas_production_bcm,
  COALESCE(p.condensate_production_mmt, 0) AS condensate_production_mmt,
  COALESCE(p.total_liquids_production_mmt, 0) AS total_liquids_production_mmt,
  COALESCE(p.total_production_mmtoe, 0) AS total_production_mmtoe,
  COALESCE(p.total_production_boe, 0) AS total_production_boe,
  COALESCE(pnl.gross_revenue_inr_cr, 0) AS gross_revenue_inr_cr,
  COALESCE(pnl.total_opex_inr_cr, 0) AS total_opex_inr_cr,
  COALESCE(pnl.ebitda_inr_cr, 0) AS ebitda_inr_cr,
  ROUND(SAFE_DIVIDE(py.payroll_cost_inr_cr * 10000000.0, NULLIF(p.total_production_boe, 0)), 2) AS manpower_cost_per_boe_inr,
  ROUND(SAFE_DIVIDE(SAFE_DIVIDE(py.payroll_cost_inr_cr * 10000000.0, NULLIF(p.total_production_boe, 0)), NULLIF(fx.inr_usd_fx_rate, 0)), 2) AS manpower_cost_per_boe_usd,
  ROUND(SAFE_DIVIDE(p.total_production_boe, NULLIF(py.regular_headcount, 0)), 2) AS boe_per_employee,
  ROUND(SAFE_DIVIDE(pnl.gross_revenue_inr_cr, NULLIF(py.regular_headcount, 0)), 4) AS revenue_per_employee_inr_cr
FROM ${ref("dim_work_centre")} w
JOIN prod_agg p ON w.wc_id = p.asset_wc_id
LEFT JOIN pay_agg py ON w.wc_id = py.asset_wc_id AND p.fiscal_year = py.fiscal_year
LEFT JOIN pnl_agg pnl ON w.wc_id = pnl.asset_wc_id AND p.fiscal_year = pnl.fiscal_year
LEFT JOIN fx_agg fx ON p.fiscal_year = fx.fiscal_year
"""
    with open(GOLD_DIR / "mart_asset_productivity.sqlx", "w", encoding="utf-8") as f:
        f.write(mart_productivity)


def generate_semantic_views():
    # 1. v_continuous_stay
    v_continuous = """config {
  type: "view",
  schema: "hrfin_gold",
  name: "v_continuous_stay",
  description: "Gaps-and-islands continuous stay calculation over consecutive same-station postings"
}

WITH numbered_postings AS (
  SELECT
    p.emp_id,
    p.wc_id,
    p.grade_id,
    p.discipline_id,
    p.from_date,
    p.to_date,
    p.is_current_posting,
    ROW_NUMBER() OVER (PARTITION BY p.emp_id ORDER BY p.from_date, p.posting_id) -
    ROW_NUMBER() OVER (PARTITION BY p.emp_id, p.wc_id ORDER BY p.from_date, p.posting_id) AS island_id
  FROM ${ref("posting_history")} p
),
islands AS (
  SELECT
    emp_id,
    wc_id,
    island_id,
    MIN(from_date) AS continuous_from_date,
    MAX(COALESCE(to_date, DATE '2026-10-19')) AS continuous_to_date,
    LOGICAL_OR(to_date IS NULL OR is_current_posting) AS is_current_stay,
    MAX(grade_id) AS current_grade_id,
    MAX(discipline_id) AS current_discipline_id,
    DATE_DIFF(DATE '2026-10-19', MIN(from_date), MONTH) AS continuous_stay_months,
    ROUND(DATE_DIFF(DATE '2026-10-19', MIN(from_date), DAY) / 365.25, 2) AS continuous_stay_years
  FROM numbered_postings
  GROUP BY emp_id, wc_id, island_id
)
SELECT
  i.emp_id,
  e.name AS emp_name,
  e.gender,
  e.category,
  e.dob,
  e.retirement_date,
  i.wc_id,
  w.name AS wc_name,
  w.sector,
  w.cluster_id,
  w.cluster_name,
  w.hard_station_cat,
  w.is_corporate_hq,
  i.current_grade_id AS grade_id,
  i.current_discipline_id AS discipline_id,
  i.continuous_from_date,
  i.continuous_to_date,
  i.continuous_stay_months,
  i.continuous_stay_years,
  i.is_current_stay,
  CASE WHEN i.continuous_stay_years >= 5.0 AND i.is_current_stay THEN TRUE ELSE FALSE END AS is_continuous_5yr_plus,
  CASE WHEN DATE_DIFF(e.retirement_date, DATE '2026-10-19', YEAR) <= 2 THEN TRUE ELSE FALSE END AS is_superannuation_exempt
FROM islands i
JOIN ${ref("employee_master")} e ON i.emp_id = e.emp_id
JOIN ${ref("dim_work_centre")} w ON i.wc_id = w.wc_id
"""
    with open(GOLD_DIR / "v_continuous_stay.sqlx", "w", encoding="utf-8") as f:
        f.write(v_continuous)

    # 2. v_cluster_cumulative_tenure
    v_cluster = """config {
  type: "view",
  schema: "hrfin_gold",
  name: "v_cluster_cumulative_tenure",
  description: "Cumulative tenure tracking per employee per JRTP geographic cluster across historical stints"
}

WITH posting_clusters AS (
  SELECT
    p.emp_id,
    w.cluster_id,
    w.cluster_name,
    DATE_DIFF(COALESCE(p.to_date, DATE '2026-10-19'), p.from_date, DAY) AS stint_days,
    p.is_current_posting,
    p.wc_id AS current_wc_id,
    p.grade_id AS current_grade_id
  FROM ${ref("posting_history")} p
  JOIN ${ref("dim_work_centre")} w ON p.wc_id = w.wc_id
)
SELECT
  pc.emp_id,
  e.name AS emp_name,
  e.gender,
  e.category,
  e.dob,
  e.retirement_date,
  e.current_grade_id,
  e.current_wc_id,
  pc.cluster_id,
  pc.cluster_name,
  SUM(pc.stint_days) AS cumulative_cluster_days,
  ROUND(SUM(pc.stint_days) / 365.25, 2) AS cumulative_cluster_years,
  LOGICAL_OR(pc.is_current_posting) AS is_currently_in_cluster,
  CASE WHEN ROUND(SUM(pc.stint_days) / 365.25, 2) >= 10.0 THEN TRUE ELSE FALSE END AS has_breached_cluster_10yr_cap,
  CASE WHEN DATE_DIFF(e.retirement_date, DATE '2026-10-19', YEAR) <= 2 THEN TRUE ELSE FALSE END AS is_superannuation_exempt
FROM posting_clusters pc
JOIN ${ref("employee_master")} e ON pc.emp_id = e.emp_id
GROUP BY
  pc.emp_id, e.name, e.gender, e.category, e.dob, e.retirement_date,
  e.current_grade_id, e.current_wc_id, pc.cluster_id, pc.cluster_name
"""
    with open(GOLD_DIR / "v_cluster_cumulative_tenure.sqlx", "w", encoding="utf-8") as f:
        f.write(v_cluster)

    # 3. v_headcount_asof
    v_hc = """config {
  type: "view",
  schema: "hrfin_gold",
  name: "v_headcount_asof",
  description: "As-of point-in-time enterprise headcount aggregation across all fiscal years"
}

SELECT
  d AS as_of_date,
  e.current_wc_id AS wc_id,
  w.name AS wc_name,
  w.sector,
  w.cluster_id,
  w.hard_station_cat,
  e.current_grade_id AS grade_id,
  g.cadre,
  g.group,
  e.discipline_id,
  d_ref.name AS discipline_name,
  e.gender,
  e.category,
  e.pwd_flag,
  COUNT(DISTINCT e.emp_id) AS active_headcount
FROM UNNEST([
  DATE '2013-03-31', DATE '2014-03-31', DATE '2015-03-31', DATE '2016-03-31',
  DATE '2017-03-31', DATE '2018-03-31', DATE '2019-03-31', DATE '2020-03-31',
  DATE '2021-03-31', DATE '2022-03-31', DATE '2023-03-31', DATE '2024-03-31',
  DATE '2025-03-31', DATE '2026-03-31', DATE '2026-10-19'
]) d
CROSS JOIN ${ref("employee_master")} e
JOIN ${ref("dim_work_centre")} w ON e.current_wc_id = w.wc_id
JOIN ${ref("dim_grade")} g ON e.current_grade_id = g.grade_id
JOIN ${ref("dim_discipline")} d_ref ON e.discipline_id = d_ref.discipline_id
WHERE e.doj <= d AND (e.separation_date IS NULL OR e.separation_date > d)
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14
"""
    with open(GOLD_DIR / "v_headcount_asof.sqlx", "w", encoding="utf-8") as f:
        f.write(v_hc)

    # 4. v_field_pnl
    v_field_pnl = """config {
  type: "view",
  schema: "hrfin_gold",
  name: "v_field_pnl",
  description: "Dynamically recomputed field and asset P&L components, margins, and viability indicators"
}

SELECT
  pnl.pnl_id,
  pnl.fiscal_year,
  pnl.field_id,
  f.name AS field_name,
  f.basin,
  f.onshore_offshore,
  pnl.asset_wc_id,
  w.name AS asset_name,
  pnl.oil_revenue_inr_cr,
  pnl.gas_revenue_inr_cr,
  (pnl.oil_revenue_inr_cr + pnl.gas_revenue_inr_cr) AS recomputed_gross_revenue_inr_cr,
  pnl.statutory_royalty_inr_cr,
  pnl.statutory_cess_inr_cr,
  pnl.statutory_windfall_tax_saed_inr_cr,
  (pnl.oil_revenue_inr_cr + pnl.gas_revenue_inr_cr - pnl.statutory_royalty_inr_cr - pnl.statutory_cess_inr_cr - pnl.statutory_windfall_tax_saed_inr_cr) AS recomputed_net_revenue_inr_cr,
  pnl.allocated_manpower_cost_inr_cr,
  pnl.total_opex_inr_cr,
  (pnl.net_revenue_inr_cr - pnl.total_opex_inr_cr) AS recomputed_ebitda_inr_cr,
  ROUND(SAFE_DIVIDE(pnl.net_revenue_inr_cr - pnl.total_opex_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0)) * 100, 2) AS recomputed_ebitda_margin_pct,
  pnl.dda_depreciation_inr_cr,
  (pnl.ebitda_inr_cr - pnl.dda_depreciation_inr_cr) AS recomputed_pbt_inr_cr,
  pnl.total_production_boe,
  pnl.lifting_cost_per_boe_usd,
  pnl.manpower_cost_per_boe_usd,
  pnl.boe_per_employee,
  pnl.is_loss_making_3yr_consecutive,
  pnl.is_divestment_candidate,
  pnl.pec_monetisation_potential_flag,
  pnl.root_cause_loss_code
FROM ${ref("field_pnl_annual")} pnl
LEFT JOIN ${ref("dim_field")} f ON pnl.field_id = f.field_id
LEFT JOIN ${ref("dim_work_centre")} w ON pnl.asset_wc_id = w.wc_id
"""
    with open(GOLD_DIR / "v_field_pnl.sqlx", "w", encoding="utf-8") as f:
        f.write(v_field_pnl)

    # 5. v_lifting_cost
    v_lifting = """config {
  type: "view",
  schema: "hrfin_gold",
  name: "v_lifting_cost",
  description: "Unit lifting and production costs per BOE by field and asset across fiscal years"
}

SELECT
  pnl.fiscal_year,
  pnl.asset_wc_id,
  w.name AS asset_name,
  w.onshore_offshore,
  pnl.field_id,
  f.name AS field_name,
  pnl.total_production_boe,
  pnl.total_opex_inr_cr,
  ROUND(SAFE_DIVIDE(pnl.total_opex_inr_cr * 10000000.0, NULLIF(pnl.total_production_boe, 0)), 2) AS lifting_cost_per_boe_inr,
  pnl.lifting_cost_per_boe_usd,
  pnl.manpower_cost_per_boe_usd,
  pnl.allocated_manpower_cost_inr_cr,
  pnl.regular_employee_headcount,
  pnl.contractor_headcount,
  pnl.boe_per_employee
FROM ${ref("field_pnl_annual")} pnl
LEFT JOIN ${ref("dim_field")} f ON pnl.field_id = f.field_id
LEFT JOIN ${ref("dim_work_centre")} w ON pnl.asset_wc_id = w.wc_id
WHERE pnl.line_type = 'field' AND pnl.total_production_boe > 0
"""
    with open(GOLD_DIR / "v_lifting_cost.sqlx", "w", encoding="utf-8") as f:
        f.write(v_lifting)

    # 6. Addendum Gold View: v_env_incidents
    v_env = """config {
  type: "view",
  schema: "hrfin_gold",
  name: "v_env_incidents",
  description: "Environmental and process-safety incidents tracking spills, leaks, blowouts, and regulatory notices"
}

SELECT
  env.incident_id,
  env.date,
  env.fiscal_year,
  env.wc_id,
  w.name AS wc_name,
  w.sector,
  w.onshore_offshore,
  env.field_id,
  f.name AS field_name,
  f.basin,
  env.incident_type,
  env.severity,
  env.volume_released,
  env.volume_unit,
  env.regulator,
  env.notice_issued,
  env.penalty_inr_lakh,
  env.status,
  env.root_cause_category
FROM ${ref("env_incidents")} env
LEFT JOIN ${ref("dim_work_centre")} w ON env.wc_id = w.wc_id
LEFT JOIN ${ref("dim_field")} f ON env.field_id = f.field_id
"""
    with open(GOLD_DIR / "v_env_incidents.sqlx", "w", encoding="utf-8") as f:
        f.write(v_env)


def generate_metadata_tables():
    glossary = """config {
  type: "table",
  schema: "hrfin_gold",
  name: "glossary",
  description: "Authoritative business glossary of ONGC corporate, upstream oil & gas, HR, and financial terminology"
}

SELECT * FROM UNNEST([
  STRUCT('BOE' AS term, 'Barrel of Oil Equivalent' AS full_form, 'Standard energy unit equating natural gas to crude oil based on ~5,800 scf of gas per barrel of oil or ~7.33 BOE per MT of oil equivalent.' AS definition, 'PPAC / SPE Petroleum Guidelines' AS source_document, 'Operations' AS domain, 'Unit of Measure' AS category),
  STRUCT('Lifting Cost' AS term, 'Lifting Cost per BOE' AS full_form, 'Direct operating cash expenditure required to operate hydrocarbon wells and surface facilities, excluding statutory royalties, cess, and DDA.' AS definition, 'FACTS.md §D4 & Annual Report Note 35' AS source_document, 'Finance' AS domain, 'Financial Metric' AS category),
  STRUCT('JRTP' AS term, 'Job Rotation and Transfer Policy' AS full_form, 'Statutory ONGC transfer policy regulating executive rotation, minimum 3-year station tenure, 10-year cluster stay cap, and hard station service.' AS definition, 'ONGC JRTP Rulebook' AS source_document, 'HR' AS domain, 'Policy' AS category),
  STRUCT('Cluster' AS term, 'Geographic Work Centre Cluster' AS full_form, 'Designated contiguous administrative regions (Delhi NCR, Mumbai Region, Gujarat Region, Assam Region) treated as single units for tenure accumulation.' AS definition, 'JRTP Schedule B' AS source_document, 'HR' AS domain, 'Geographic Definition' AS category),
  STRUCT('Hard Station' AS term, 'Hardship Station Classification' AS full_form, 'Remote, offshore, or high-hardship work centres (e.g. North-East, deep offshore, remote desert) carrying mandatory service requirements for promotion.' AS definition, 'JRTP Clause 6 & Schedule C' AS source_document, 'HR' AS domain, 'Policy' AS category),
  STRUCT('BE' AS term, 'Budget Estimate' AS full_form, 'Original capital or operating expenditure budget approved by the Board for the financial year.' AS definition, 'Corporate Budget Manual' AS source_document, 'Finance' AS domain, 'Budgeting' AS category),
  STRUCT('RE' AS term, 'Revised Estimate' AS full_form, 'Mid-year re-assessed budget allocation based on actual progress and commitments during H1.' AS definition, 'Corporate Budget Manual' AS source_document, 'Finance' AS domain, 'Budgeting' AS category),
  STRUCT('PRP' AS term, 'Performance Related Pay' AS full_form, 'Annual variable performance bonus linked to MoU composite score, company profit, and individual e-APAR score.' AS definition, 'DPE 3rd PRC Guidelines' AS source_document, 'HR' AS domain, 'Compensation' AS category),
  STRUCT('MoU' AS term, 'Memorandum of Understanding' AS full_form, 'Annual performance contract between ONGC and the Ministry of Petroleum and Natural Gas (MoPNG) / DPE evaluated on a 5-point scale.' AS definition, 'DPE MoU Guidelines' AS source_document, 'Governance' AS domain, 'Performance Contract' AS category),
  STRUCT('DPC' AS term, 'Departmental Promotion Committee' AS full_form, 'Statutory board reviewing executive promotion cases based on minimum residency, APAR benchmarks, and interview.' AS definition, 'ONGC Modified R&P Regulations' AS source_document, 'HR' AS domain, 'Promotion' AS category),
  STRUCT('AGT' AS term, 'Annual General Transfer' AS full_form, 'Annual cycle of employee rotational transfers executed every year between April and June.' AS definition, 'JRTP Chapter 4' AS source_document, 'HR' AS domain, 'Transfer' AS category),
  STRUCT('SAED' AS term, 'Special Additional Excise Duty' AS full_form, 'Windfall tax levied on domestic crude oil production introduced in July 2022 and revised fortnightly based on international benchmarks.' AS definition, 'Ministry of Finance Notifications' AS source_document, 'Finance' AS domain, 'Statutory Levy' AS category),
  STRUCT('OIDB Cess' AS term, 'Oil Industry Development Board Cess' AS full_form, 'Statutory cess levied at 20% ad valorem on crude oil produced under the OIDB Act 1974.' AS definition, 'OIDB Act 1974' AS source_document, 'Finance' AS domain, 'Statutory Levy' AS category),
  STRUCT('APM Gas' AS term, 'Administered Price Mechanism Gas' AS full_form, 'Natural gas produced from nomination fields priced as per Government approved domestic gas pricing guidelines.' AS definition, 'MoPNG Gas Pricing Guidelines 2023' AS source_document, 'Commercial' AS domain, 'Pricing' AS category),
  STRUCT('Non-APM Gas' AS term, 'Non-Administered Price Mechanism Gas' AS full_form, 'Gas produced from deepwater, ultra-deepwater, high-temperature, high-pressure blocks (e.g. KG-DWN-98/2) with pricing ceiling freedom.' AS definition, 'MoPNG Deepwater Gas Guidelines 2016' AS source_document, 'Commercial' AS domain, 'Pricing' AS category),
  STRUCT('MMTOE' AS term, 'Million Metric Tonnes of Oil Equivalent' AS full_form, 'Standard aggregated volume metric combining crude oil and natural gas production on energy parity.' AS definition, 'MoPNG / PPAC Annual Report' AS source_document, 'Operations' AS domain, 'Unit of Measure' AS category),
  STRUCT('MMT' AS term, 'Million Metric Tonnes' AS full_form, 'Standard metric mass unit for liquid petroleum production and refining throughput.' AS definition, 'MoPNG Annual Report' AS source_document, 'Operations' AS domain, 'Unit of Measure' AS category),
  STRUCT('BCM' AS term, 'Billion Cubic Metres' AS full_form, 'Volumetric measurement standard for natural gas production and reservoir reserves.' AS definition, 'DGH Annual Report' AS source_document, 'Operations' AS domain, 'Unit of Measure' AS category),
  STRUCT('MMSCMD' AS term, 'Million Metric Standard Cubic Metres per Day' AS full_form, 'Daily flow rate measurement unit for natural gas production and pipeline transport.' AS definition, 'PNGRB Regulations' AS source_document, 'Operations' AS domain, 'Unit of Measure' AS category),
  STRUCT('EOR' AS term, 'Enhanced Oil Recovery' AS full_form, 'Tertiary recovery techniques (polymer flooding, thermal injection, gas injection) applied to extract residual crude oil from mature fields.' AS definition, 'ONGC Reservoir Management Manual' AS source_document, 'Operations' AS domain, 'Technical' AS category),
  STRUCT('IOR' AS term, 'Improved Oil Recovery' AS full_form, 'Secondary recovery techniques including water injection, infill drilling, and artificial lift maintenance.' AS definition, 'ONGC Reservoir Management Manual' AS source_document, 'Operations' AS domain, 'Technical' AS category),
  STRUCT('CWIP' AS term, 'Capital Work in Progress' AS full_form, 'Accumulated expenditures incurred on capital infrastructure projects prior to commissioning and capitalization.' AS definition, 'Ind AS 16 Property, Plant & Equipment' AS source_document, 'Finance' AS domain, 'Accounting' AS category),
  STRUCT('DDA' AS term, 'Depreciation, Depletion, and Amortization' AS full_form, 'Non-cash accounting amortization of producing properties, drilling exploratory wells, and tangible plant assets.' AS definition, 'Annual Report Accounting Policies' AS source_document, 'Finance' AS domain, 'Accounting' AS category),
  STRUCT('LTIFR' AS term, 'Lost Time Injury Frequency Rate' AS full_form, 'Global standard HSE safety metric: (Number of Lost Time Injuries × 1,000,000) / Total Man-hours worked.' AS definition, 'Corporate HSE Policy & DGMS Guidelines' AS source_document, 'HSE' AS domain, 'Safety Metric' AS category),
  STRUCT('LTI' AS term, 'Lost Time Injury' AS full_form, 'Workplace incident resulting in fatality, permanent disability, or time lost from work extending beyond the shift.' AS definition, 'Corporate HSE Policy' AS source_document, 'HSE' AS domain, 'Safety Metric' AS category),
  STRUCT('RRR' AS term, 'Reserve Replacement Ratio' AS full_form, 'Ratio of net 2P reserves accreted during the year to annual hydrocarbon production volume; >1.0 indicates sustainable replenishment.' AS definition, 'Reserves Estimation Committee (REC) Guidelines' AS source_document, 'Reserves' AS domain, 'Exploration Metric' AS category),
  STRUCT('1P Reserves' AS term, 'Proved Hydrocarbon Reserves' AS full_form, 'Quantities of oil and gas with 90% geological certainty of commercial recovery under current economic conditions.' AS definition, 'SPE-PRMS Reserve Standards' AS source_document, 'Reserves' AS domain, 'Reserves Metric' AS category),
  STRUCT('2P Reserves' AS term, 'Proved plus Probable Reserves' AS full_form, 'Quantities of oil and gas with 50% statistical certainty of commercial recovery, forming corporate long-term planning baseline.' AS definition, 'SPE-PRMS Reserve Standards' AS source_document, 'Reserves' AS domain, 'Reserves Metric' AS category),
  STRUCT('F&D Cost' AS term, 'Finding and Development Cost per BOE' AS full_form, 'Capital invested in exploration discovery and development drilling divided by net added reserves in BOE.' AS definition, 'Upstream Industry Benchmark Standard' AS source_document, 'Finance' AS domain, 'Cost Metric' AS category),
  STRUCT('CLRA' AS term, 'Contract Labour Regulation and Abolition Act 1970' AS full_form, 'Central statutory regulation governing contractual labour deployment, registration of principal employer, and contractor licensing.' AS definition, 'Contract Labour (R&A) Act 1970' AS source_document, 'Legal' AS domain, 'Statutory Compliance' AS category),
  STRUCT('MSE' AS term, 'Micro and Small Enterprises' AS full_form, 'Enterprises entitled to mandatory 25% central public procurement share and price preference under MoSME policy.' AS definition, 'Public Procurement Policy for MSEs Order 2012' AS source_document, 'Commercial' AS domain, 'Procurement' AS category),
  STRUCT('POSH' AS term, 'Prevention of Sexual Harassment' AS full_form, 'Statutory framework and internal complaints mechanism pursuant to POSH Act 2013 for gender dignity at workplace.' AS definition, 'Sexual Harassment of Women at Workplace Act 2013' AS source_document, 'HR' AS domain, 'Statutory Compliance' AS category),
  STRUCT('ICC' AS term, 'Internal Complaints Committee' AS full_form, 'Mandatory enterprise committee established at each work centre headed by senior woman executive for POSH inquiries.' AS definition, 'POSH Act Section 4' AS source_document, 'HR' AS domain, 'Governance' AS category),
  STRUCT('CVC' AS term, 'Central Vigilance Commission' AS full_form, 'Apex central government body overseeing integrity, vigilance clearance, and disciplinary inquiries across public sector.' AS definition, 'CVC Vigilance Manual 2021' AS source_document, 'Vigilance' AS domain, 'Governance' AS category),
  STRUCT('RTI' AS term, 'Right to Information' AS full_form, 'Statutory regime guaranteeing citizens access to public records under the RTI Act 2005 within mandatory 30-day timeline.' AS definition, 'Right to Information Act 2005' AS source_document, 'Governance' AS domain, 'Statutory Compliance' AS category),
  STRUCT('CAG' AS term, 'Comptroller and Auditor General of India' AS full_form, 'Supreme constitutional audit authority reviewing financial performance, compliance, and propriety across ONGC installations.' AS definition, 'CAG Audit Manual & Article 148 of Constitution' AS source_document, 'Audit' AS domain, 'Statutory Oversight' AS category),
  STRUCT('e-APAR' AS term, 'Electronic Annual Performance Appraisal Report' AS full_form, 'Digital appraisal system for executive cadre scoring performance on 100-point numerical benchmark for promotion and PRP.' AS definition, 'ONGC HR Manual Chapter 8' AS source_document, 'HR' AS domain, 'Appraisal' AS category),
  STRUCT('PRBS' AS term, 'Post Retirement Benefit Scheme' AS full_form, 'Defined contribution superannuation pension trust managed for retired ONGC officers compliant with DPE 30% ceiling.' AS definition, 'ONGC PRBS Trust Deed' AS source_document, 'HR' AS domain, 'Retirement' AS category),
  STRUCT('PRMB' AS term, 'Post Retirement Medical Benefit' AS full_form, 'Lifetime medical trust coverage for retired employees and spouses across empanelled hospitals.' AS definition, 'ONGC Medical Attendance Rules' AS source_document, 'HR' AS domain, 'Medical Welfare' AS category),
  STRUCT('CPF' AS term, 'Contributory Provident Fund' AS full_form, 'Statutory retirement savings trust fund matching employee and employer contributions at 12% of Basic + DA.' AS definition, 'ONGC CPF Rules' AS source_document, 'HR' AS domain, 'Retirement' AS category),
  STRUCT('OGL' AS term, 'ONGC Green Limited' AS full_form, 'Wholly owned clean energy subsidiary established to develop 10 GW renewable portfolio, green hydrogen, and carbon abatement assets.' AS definition, 'Board Approval Note 2024' AS source_document, 'Corporate' AS domain, 'Subsidiary' AS category),
  STRUCT('CCUS' AS term, 'Carbon Capture, Utilisation, and Storage' AS full_form, 'CO2 abatement technology capturing industrial emissions for injection into mature reservoirs for enhanced recovery.' AS definition, 'ONGC Net Zero 2038 Roadmap' AS source_document, 'Energy Transition' AS domain, 'Technical' AS category),
  STRUCT('VPSF' AS term, 'Vapour Pressure Specification Flare' AS full_form, 'Off-spec volatile crude hydrocarbons flared at offshore separation platforms to ensure crude export vapor stability.' AS definition, 'Offshore Operating Manual' AS source_document, 'Operations' AS domain, 'Operational' AS category),
  STRUCT('PECs' AS term, 'Production Enhancement Contracts' AS full_form, 'Risk-sharing partnerships with international/domestic operators to arrest decline in mature marginal fields.' AS definition, 'MoPNG Marginal Field Policy' AS source_document, 'Commercial' AS domain, 'Commercial Contract' AS category),
  STRUCT('ROCE' AS term, 'Return on Capital Employed' AS full_form, 'Key corporate profitability ratio: Operating Profit (EBIT) divided by Total Capital Employed (Net Worth + Long-term Debt).' AS definition, 'Audited Financial Statements Ratio Analysis' AS source_document, 'Finance' AS domain, 'Financial Metric' AS category),
  # Addendum terms
  STRUCT('GeM' AS term, 'Government e-Marketplace' AS full_form, 'National public procurement portal mandated for common goods/services under GFR Rule 149.' AS definition, 'GFR Rule 149' AS source_document, 'Commercial' AS domain, 'Procurement' AS category),
  STRUCT('API RP 754 Tiers' AS term, 'API Recommended Practice 754 Tiers' AS full_form, 'Four-tier process safety performance indicator pyramid classifying loss of primary containment incidents.' AS definition, 'API RP 754 / OISD-STD-107' AS source_document, 'HSE' AS domain, 'Safety Framework' AS category),
  STRUCT('SPCB' AS term, 'State Pollution Control Board' AS full_form, 'State statutory bodies enforcing environmental protection acts and issuing consent orders.' AS definition, 'Environment Protection Act 1986' AS source_document, 'Governance' AS domain, 'Regulatory' AS category),
  STRUCT('POSH/ICC' AS term, 'POSH Internal Complaints Committee' AS full_form, 'Statutory presiding committee established at work centres to complete inquiries within 90 days.' AS definition, 'POSH Act 2013' AS source_document, 'HR' AS domain, 'Statutory Compliance' AS category),
  STRUCT('NATS/Apprenticeship' AS term, 'National Apprenticeship Training Scheme' AS full_form, 'Statutory apprenticeship scheme engaging trade, technician, and graduate apprentices.' AS definition, 'Apprentices Act 1961' AS source_document, 'HR' AS domain, 'Training' AS category)
])
"""
    with open(GOLD_DIR / "glossary.sqlx", "w", encoding="utf-8") as f:
        f.write(glossary)

    metric_defs = """config {
  type: "table",
  schema: "hrfin_gold",
  name: "metric_definitions",
  description: "Enterprise metric definitions including canonical formulas, grain, units, and linked question IDs"
}

SELECT * FROM UNNEST([
  STRUCT('MET-HR-001' AS metric_id, 'Active Regular Headcount' AS name, 'COUNT(DISTINCT emp_id) WHERE employment_status = \\'Active\\' AND doj <= as_of_date AND (separation_date IS NULL OR separation_date > as_of_date)' AS sql_expression, 'Work Centre × Grade × FY' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['C3', 'H1', 'H3', 'M1'] AS related_question_ids),
  STRUCT('MET-HR-002' AS metric_id, 'Executive Headcount' AS name, 'COUNT(DISTINCT emp_id) WHERE cadre = \\'executive\\' AND employment_status = \\'Active\\'' AS sql_expression, 'Grade (E0-E9) × Work Centre' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['C3', 'H1', 'H7'] AS related_question_ids),
  STRUCT('MET-HR-003' AS metric_id, 'Non-Executive Headcount' AS name, 'COUNT(DISTINCT emp_id) WHERE cadre = \\'non_executive\\' AND employment_status = \\'Active\\'' AS sql_expression, 'Group (B,C,D) × Work Centre' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['C3', 'H1', 'H7'] AS related_question_ids),
  STRUCT('MET-HR-004' AS metric_id, 'Women Workforce Representation Pct' AS name, 'COUNT(DISTINCT CASE WHEN gender = \\'Female\\' THEN emp_id END) * 100.0 / COUNT(DISTINCT emp_id)' AS sql_expression, 'Company / Work Centre × FY' AS grain, 'percentage' AS unit, 'HR' AS owner_domain, ['H7', 'X7'] AS related_question_ids),
  STRUCT('MET-HR-005' AS metric_id, 'SC Representation Pct' AS name, 'COUNT(DISTINCT CASE WHEN category = \\'SC\\' THEN emp_id END) * 100.0 / COUNT(DISTINCT emp_id)' AS sql_expression, 'Company / Grade × FY' AS grain, 'percentage' AS unit, 'HR' AS owner_domain, ['H6', 'X7'] AS related_question_ids),
  STRUCT('MET-HR-006' AS metric_id, 'ST Representation Pct' AS name, 'COUNT(DISTINCT CASE WHEN category = \\'ST\\' THEN emp_id END) * 100.0 / COUNT(DISTINCT emp_id)' AS sql_expression, 'Company / Grade × FY' AS grain, 'percentage' AS unit, 'HR' AS owner_domain, ['H6', 'X7'] AS related_question_ids),
  STRUCT('MET-HR-007' AS metric_id, 'OBC Representation Pct' AS name, 'COUNT(DISTINCT CASE WHEN category = \\'OBC\\' THEN emp_id END) * 100.0 / COUNT(DISTINCT emp_id)' AS sql_expression, 'Company / Grade × FY' AS grain, 'percentage' AS unit, 'HR' AS owner_domain, ['H6'] AS related_question_ids),
  STRUCT('MET-HR-008' AS metric_id, 'PwD Employee Count' AS name, 'COUNT(DISTINCT CASE WHEN pwd_flag = TRUE THEN emp_id END)' AS sql_expression, 'Company / Discipline × FY' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['H6'] AS related_question_ids),
  STRUCT('MET-HR-009' AS metric_id, 'Continuous Station Tenure' AS name, 'DATE_DIFF(current_date, continuous_from_date, MONTH)' AS sql_expression, 'Employee × Work Centre' AS grain, 'months' AS unit, 'HR' AS owner_domain, ['C1', 'H1', 'P1', 'P11'] AS related_question_ids),
  STRUCT('MET-HR-010' AS metric_id, 'Cumulative Cluster Stay' AS name, 'SUM(stint_days) / 365.25' AS sql_expression, 'Employee × Cluster' AS grain, 'years' AS unit, 'HR' AS owner_domain, ['C1', 'P2', 'P11'] AS related_question_ids),
  STRUCT('MET-HR-011' AS metric_id, 'Station 5-Year Overstay Count' AS name, 'COUNT(DISTINCT CASE WHEN continuous_stay_years >= 5.0 AND is_current_stay THEN emp_id END)' AS sql_expression, 'Work Centre × Grade' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['C1', 'H1'] AS related_question_ids),
  STRUCT('MET-HR-012' AS metric_id, 'Cluster 10-Year Breach Count' AS name, 'COUNT(DISTINCT CASE WHEN cumulative_cluster_years >= 10.0 AND is_currently_in_cluster THEN emp_id END)' AS sql_expression, 'Cluster × Grade' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['C1', 'P1', 'P11'] AS related_question_ids),
  STRUCT('MET-HR-013' AS metric_id, 'Hard Station Exposure Pct' AS name, 'COUNT(DISTINCT CASE WHEN has_hard_station_tenure THEN emp_id END) * 100.0 / COUNT(DISTINCT emp_id)' AS sql_expression, 'Discipline × Grade Band' AS grain, 'percentage' AS unit, 'HR' AS owner_domain, ['C2', 'H2'] AS related_question_ids),
  STRUCT('MET-HR-014' AS metric_id, 'E3-E5 Never Hard Station Count' AS name, 'COUNT(DISTINCT CASE WHEN grade_id IN (\\'E3\\', \\'E4\\', \\'E5\\') AND NOT has_hard_station_tenure THEN emp_id END)' AS sql_expression, 'Discipline × Cadre' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['C2'] AS related_question_ids),
  STRUCT('MET-HR-015' AS metric_id, 'Annual Attrition Rate' AS name, 'COUNT(DISTINCT CASE WHEN separation_type IN (\\'resignation\\', \\'vrs\\') THEN emp_id END) * 100.0 / AVG(headcount)' AS sql_expression, 'Company × FY' AS grain, 'percentage' AS unit, 'HR' AS owner_domain, ['H3'] AS related_question_ids),
  STRUCT('MET-HR-016' AS metric_id, 'Superannuation Headroom 2Yr Count' AS name, 'COUNT(DISTINCT CASE WHEN is_near_retirement_2yr THEN emp_id END)' AS sql_expression, 'Work Centre × Cadre' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['P3', 'P11'] AS related_question_ids),
  STRUCT('MET-HR-017' AS metric_id, 'Superannuation Headroom 3Yr Count' AS name, 'COUNT(DISTINCT CASE WHEN is_near_retirement_3yr THEN emp_id END)' AS sql_expression, 'Work Centre × Cadre' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['P11'] AS related_question_ids),
  STRUCT('MET-HR-018' AS metric_id, 'Senior Executive Impending Retirements' AS name, 'COUNT(DISTINCT CASE WHEN grade_id IN (\\'E7\\', \\'E8\\', \\'E9\\') AND retirement_date BETWEEN \\'2026-04-01\\' AND \\'2029-03-31\\' THEN emp_id END)' AS sql_expression, 'Discipline × FY' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['C4'] AS related_question_ids),
  STRUCT('MET-HR-019' AS metric_id, 'Core Technical Workforce Count' AS name, 'COUNT(DISTINCT CASE WHEN discipline_function IN (\\'technical\\', \\'geoscience\\', \\'engineering\\') THEN emp_id END)' AS sql_expression, 'Asset / Basin × Grade' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['C5'] AS related_question_ids),
  STRUCT('MET-HR-020' AS metric_id, 'Sanctioned Posts Total' AS name, 'SUM(sanctioned_strength)' AS sql_expression, 'Work Centre × Discipline × Grade' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['H6', 'M1'] AS related_question_ids),
  STRUCT('MET-HR-021' AS metric_id, 'In-Position Workforce Strength' AS name, 'SUM(in_position_strength)' AS sql_expression, 'Work Centre × Discipline × Grade' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['C2', 'H6'] AS related_question_ids),
  STRUCT('MET-HR-022' AS metric_id, 'Vacancy vs Norm Count' AS name, 'SUM(vacancy_count)' AS sql_expression, 'Work Centre × Discipline × Grade' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['C2', 'H6'] AS related_question_ids),
  STRUCT('MET-HR-023' AS metric_id, 'Vacancy Rate Pct' AS name, 'AVG(vacancy_rate_pct)' AS sql_expression, 'Discipline × Grade Band' AS grain, 'percentage' AS unit, 'HR' AS owner_domain, ['H6'] AS related_question_ids),
  STRUCT('MET-HR-024' AS metric_id, 'Special Drive Backlog Vacancies' AS name, 'SUM(backlog_vacancies)' AS sql_expression, 'Social Category × FY' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['H6'] AS related_question_ids),
  STRUCT('MET-HR-025' AS metric_id, 'DPC Processing Delay Months' AS name, 'AVG(delay_months)' AS sql_expression, 'Grade Promotion Pair × FY' AS grain, 'months' AS unit, 'HR' AS owner_domain, ['H5', 'D3'] AS related_question_ids),
  STRUCT('MET-HR-026' AS metric_id, 'DPC Pending Cases Count' AS name, 'COUNT(DISTINCT CASE WHEN dpc_status = \\'Pending\\' THEN dpc_id END)' AS sql_expression, 'Grade × Discipline × FY' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['H5'] AS related_question_ids),
  STRUCT('MET-HR-027' AS metric_id, 'Accelerated Promotion Share Pct' AS name, 'COUNT(DISTINCT CASE WHEN promotion_mode = \\'accelerated_merit\\' THEN promotion_id END) * 100.0 / COUNT(DISTINCT promotion_id)' AS sql_expression, 'Grade × FY' AS grain, 'percentage' AS unit, 'HR' AS owner_domain, ['P10'] AS related_question_ids),
  STRUCT('MET-HR-028' AS metric_id, 'Average APAR Benchmark Score' AS name, 'AVG(numerical_score)' AS sql_expression, 'Cadre × Grade × FY' AS grain, 'score' AS unit, 'HR' AS owner_domain, ['H5', 'P10'] AS related_question_ids),
  STRUCT('MET-HR-029' AS metric_id, 'Total Gross Payroll Cost' AS name, 'SUM(gross_salary_inr) / 10000000.0' AS sql_expression, 'Work Centre / Cadre × FY' AS grain, 'INR Crore' AS unit, 'HR' AS owner_domain, ['C13', 'E1', 'F1'] AS related_question_ids),
  STRUCT('MET-HR-030' AS metric_id, 'Basic Pay Expense' AS name, 'SUM(basic_pay_inr) / 10000000.0' AS sql_expression, 'Cadre × Grade × Month' AS grain, 'INR Crore' AS unit, 'HR' AS owner_domain, ['E1', 'D1'] AS related_question_ids),
  STRUCT('MET-HR-031' AS metric_id, 'Dearness Allowance (DA) Expense' AS name, 'SUM(da_inr) / 10000000.0' AS sql_expression, 'Cadre × FY' AS grain, 'INR Crore' AS unit, 'HR' AS owner_domain, ['E1'] AS related_question_ids),
  STRUCT('MET-HR-032' AS metric_id, 'Mining & Offshore Hardship Allowances' AS name, 'SUM(mining_offshore_allowance_inr) / 10000000.0' AS sql_expression, 'Work Centre × Month' AS grain, 'INR Crore' AS unit, 'HR' AS owner_domain, ['E1', 'P7'] AS related_question_ids),
  STRUCT('MET-HR-033' AS metric_id, 'Performance Related Pay (PRP) Disbursed' AS name, 'SUM(prp_inr) / 10000000.0' AS sql_expression, 'Grade × FY' AS grain, 'INR Crore' AS unit, 'HR' AS owner_domain, ['E1', 'X4'] AS related_question_ids),
  STRUCT('MET-HR-034' AS metric_id, 'Overtime Hours per Worker' AS name, 'AVG(overtime_hours)' AS sql_expression, 'Work Centre × Installation × Month' AS grain, 'hours' AS unit, 'HR' AS owner_domain, ['X3'] AS related_question_ids),
  STRUCT('MET-HR-035' AS metric_id, 'Overtime Payout Amount' AS name, 'SUM(overtime_amount_inr) / 10000000.0' AS sql_expression, 'Work Centre × FY' AS grain, 'INR Crore' AS unit, 'HR' AS owner_domain, ['X3'] AS related_question_ids),
  STRUCT('MET-HR-036' AS metric_id, 'Total Training Records Count' AS name, 'COUNT(DISTINCT training_record_id)' AS sql_expression, 'Institute × Discipline × FY' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['H8'] AS related_question_ids),
  STRUCT('MET-HR-037' AS metric_id, 'Training Hours per Employee' AS name, 'SUM(training_hours) / COUNT(DISTINCT emp_id)' AS sql_expression, 'Work Centre / Cadre × FY' AS grain, 'hours' AS unit, 'HR' AS owner_domain, ['H8'] AS related_question_ids),
  STRUCT('MET-HR-038' AS metric_id, 'Mandatory Compliance Training Completion Pct' AS name, 'COUNT(DISTINCT CASE WHEN completion_status = \\'Completed\\' THEN training_record_id END) * 100.0 / COUNT(DISTINCT training_record_id)' AS sql_expression, 'Programme Category × FY' AS grain, 'percentage' AS unit, 'HR' AS owner_domain, ['H8', 'E6'] AS related_question_ids),
  STRUCT('MET-HR-039' AS metric_id, 'Engineers Green Energy Reskilled Count' AS name, 'SUM(engineers_reskilled_count)' AS sql_expression, 'Technology Type × FY' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['X6'] AS related_question_ids),
  STRUCT('MET-HR-040' AS metric_id, 'Contract Workforce Deployed Count' AS name, 'SUM(contractor_headcount)' AS sql_expression, 'Work Centre × Service Category × Month' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['X1', 'X2'] AS related_question_ids),
  STRUCT('MET-HR-041' AS metric_id, 'Contractor to Regular Manpower Ratio' AS name, 'AVG(contractor_to_regular_ratio)' AS sql_expression, 'Asset / Installation × FY' AS grain, 'ratio' AS unit, 'HR' AS owner_domain, ['X1', 'X2'] AS related_question_ids),
  STRUCT('MET-HR-042' AS metric_id, 'Contract Workforce Monthly Spend' AS name, 'SUM(monthly_cost_inr) / 10000000.0' AS sql_expression, 'Vendor × Service Category × Month' AS grain, 'INR Crore' AS unit, 'HR' AS owner_domain, ['X1', 'F5'] AS related_question_ids),
  STRUCT('MET-HR-043' AS metric_id, 'Total HSE Incident Count' AS name, 'COUNT(DISTINCT incident_id)' AS sql_expression, 'Work Centre × Severity × FY' AS grain, 'count' AS unit, 'HSE' AS owner_domain, ['X3'] AS related_question_ids),
  STRUCT('MET-HR-044' AS metric_id, 'Lost Time Injury Frequency Rate (LTIFR)' AS name, '(COUNT(DISTINCT CASE WHEN lost_time_injury_flag THEN incident_id END) * 1000000.0) / NULLIF(SUM(total_manhours_worked), 0)' AS sql_expression, 'Asset × FY' AS grain, 'rate' AS unit, 'HSE' AS owner_domain, ['X3'] AS related_question_ids),
  STRUCT('MET-HR-045' AS metric_id, 'Days Lost due to Occupational Injury' AS name, 'SUM(days_lost)' AS sql_expression, 'Work Centre × FY' AS grain, 'days' AS unit, 'HSE' AS owner_domain, ['X3'] AS related_question_ids),
  STRUCT('MET-HR-046' AS metric_id, 'Active Litigation & Grievance Cases Count' AS name, 'COUNT(DISTINCT CASE WHEN status = \\'pending\\' THEN case_id END)' AS sql_expression, 'Forum × Category' AS grain, 'count' AS unit, 'Legal' AS owner_domain, ['H9', 'P9'] AS related_question_ids),
  STRUCT('MET-HR-047' AS metric_id, 'Disputes Aged Over 3 Years Pct' AS name, 'COUNT(DISTINCT CASE WHEN is_aged_over_3_years THEN case_id END) * 100.0 / COUNT(DISTINCT case_id)' AS sql_expression, 'Case Type × Forum' AS grain, 'percentage' AS unit, 'Legal' AS owner_domain, ['H9'] AS related_question_ids),
  STRUCT('MET-OPS-001' AS metric_id, 'Crude Oil Production Volume (MMT)' AS name, 'SUM(oil_production_mt) / 1000000.0' AS sql_expression, 'Field / Asset × Month' AS grain, 'MMT' AS unit, 'Operations' AS owner_domain, ['C7', 'F8', 'W3'] AS related_question_ids),
  STRUCT('MET-OPS-002' AS metric_id, 'Condensate Production Volume (MMT)' AS name, 'SUM(condensate_production_mt) / 1000000.0' AS sql_expression, 'Field / Asset × Month' AS grain, 'MMT' AS unit, 'Operations' AS owner_domain, ['F8'] AS related_question_ids),
  STRUCT('MET-OPS-003' AS metric_id, 'Total Liquid Production incl JV (MMT)' AS name, 'SUM(oil_production_mt + condensate_production_mt) / 1000000.0' AS sql_expression, 'Operatorship × FY' AS grain, 'MMT' AS unit, 'Operations' AS owner_domain, ['C7', 'F8'] AS related_question_ids),
  STRUCT('MET-OPS-004' AS metric_id, 'Natural Gas Production Volume (BCM)' AS name, 'SUM(gas_production_mmscm) / 1000.0' AS sql_expression, 'Field / Asset × Month' AS grain, 'BCM' AS unit, 'Operations' AS owner_domain, ['C7', 'F8', 'W3'] AS related_question_ids),
  STRUCT('MET-OPS-005' AS metric_id, 'Total Hydrocarbon Production (MMTOE)' AS name, 'SUM(total_production_boe) / 7330000.0' AS sql_expression, 'Asset × FY' AS grain, 'MMTOE' AS unit, 'Operations' AS owner_domain, ['C11', 'F8'] AS related_question_ids),
  STRUCT('MET-OPS-006' AS metric_id, 'Total Hydrocarbon Production (BOE)' AS name, 'SUM(total_production_boe)' AS sql_expression, 'Field × Month' AS grain, 'BOE' AS unit, 'Operations' AS owner_domain, ['C11', 'C12', 'F1'] AS related_question_ids),
  STRUCT('MET-OPS-007' AS metric_id, 'Gas Flaring Percentage' AS name, 'AVG(gas_flaring_pct)' AS sql_expression, 'Asset / Installation × Month' AS grain, 'percentage' AS unit, 'Operations' AS owner_domain, ['F8', 'X6'] AS related_question_ids),
  STRUCT('MET-OPS-008' AS metric_id, 'Operating Efficiency Pct' AS name, 'AVG(operational_uptime_pct)' AS sql_expression, 'Asset × Month' AS grain, 'percentage' AS unit, 'Operations' AS owner_domain, ['F8'] AS related_question_ids),
  STRUCT('MET-OPS-009' AS metric_id, 'Active Producing Hydrocarbon Wells' AS name, 'SUM(active_producing_wells)' AS sql_expression, 'Field × Asset × Month' AS grain, 'count' AS unit, 'Operations' AS owner_domain, ['F8', 'F3'] AS related_question_ids),
  STRUCT('MET-OPS-010' AS metric_id, '2P Geological Hydrocarbon Reserves (MMTOE)' AS name, 'SUM(reserves_2p_total_mmtoe)' AS sql_expression, 'Field / Basin × FY' AS grain, 'MMTOE' AS unit, 'Reserves' AS owner_domain, ['F8'] AS related_question_ids),
  STRUCT('MET-OPS-011' AS metric_id, 'Reserve Replacement Ratio (RRR 2P)' AS name, 'AVG(reserve_replacement_ratio_rrr_2p)' AS sql_expression, 'Company × FY' AS grain, 'ratio' AS unit, 'Reserves' AS owner_domain, ['F8'] AS related_question_ids),
  STRUCT('MET-OPS-012' AS metric_id, 'Finding and Development Cost ($/boe)' AS name, 'AVG(finding_cost_usd_per_boe + development_cost_usd_per_boe)' AS sql_expression, 'Basin × FY' AS grain, 'USD/boe' AS unit, 'Reserves' AS owner_domain, ['F8'] AS related_question_ids),
  STRUCT('MET-FIN-001' AS metric_id, 'Standalone Gross Revenue from Operations' AS name, 'SUM(gross_revenue_inr_cr)' AS sql_expression, 'Company × FY' AS grain, 'INR Crore' AS unit, 'Finance' AS owner_domain, ['C6', 'C10', 'F4'] AS related_question_ids),
  STRUCT('MET-FIN-002' AS metric_id, 'Offshore Revenue Split' AS name, 'SUM(offshore_revenue_inr_cr)' AS sql_expression, 'Segment × FY' AS grain, 'INR Crore' AS unit, 'Finance' AS owner_domain, ['C10', 'F4'] AS related_question_ids),
  STRUCT('MET-FIN-003' AS metric_id, 'Onshore Revenue Split' AS name, 'SUM(onshore_revenue_inr_cr)' AS sql_expression, 'Segment × FY' AS grain, 'INR Crore' AS unit, 'Finance' AS owner_domain, ['C10', 'F4'] AS related_question_ids),
  STRUCT('MET-FIN-004' AS metric_id, 'Statutory Royalties Paid' AS name, 'SUM(royalty_inr_cr)' AS sql_expression, 'Field / Asset × FY' AS grain, 'INR Crore' AS unit, 'Finance' AS owner_domain, ['F1', 'F7'] AS related_question_ids),
  STRUCT('MET-FIN-005' AS metric_id, 'Statutory OIDB Cess Paid' AS name, 'SUM(oidb_cess_inr_cr)' AS sql_expression, 'Field / Asset × FY' AS grain, 'INR Crore' AS unit, 'Finance' AS owner_domain, ['F1', 'F7'] AS related_question_ids),
  STRUCT('MET-FIN-006' AS metric_id, 'Windfall Tax (SAED) Paid' AS name, 'SUM(saed_windfall_tax_inr_cr)' AS sql_expression, 'Company × FY' AS grain, 'INR Crore' AS unit, 'Finance' AS owner_domain, ['F7'] AS related_question_ids),
  STRUCT('MET-FIN-007' AS metric_id, 'Standalone Operating Expenses (Opex)' AS name, 'SUM(total_opex_inr_cr)' AS sql_expression, 'Field / Asset × FY' AS grain, 'INR Crore' AS unit, 'Finance' AS owner_domain, ['F1', 'W1'] AS related_question_ids),
  STRUCT('MET-FIN-008' AS metric_id, 'Unit Lifting Cost per BOE ($/boe)' AS name, '(SUM(total_opex_inr_cr * 10000000.0) / NULLIF(SUM(total_production_boe), 0)) / inr_usd_fx_rate' AS sql_expression, 'Field / Asset × FY' AS grain, 'USD/boe' AS unit, 'Finance' AS owner_domain, ['C12', 'F1', 'W1'] AS related_question_ids),
  STRUCT('MET-FIN-009' AS metric_id, 'Unit Lifting Cost per BOE (₹/boe)' AS name, 'SUM(total_opex_inr_cr * 10000000.0) / NULLIF(SUM(total_production_boe), 0)' AS sql_expression, 'Field / Asset × FY' AS grain, 'INR/boe' AS unit, 'Finance' AS owner_domain, ['C12', 'F1'] AS related_question_ids),
  STRUCT('MET-FIN-010' AS metric_id, 'Standalone EBITDA' AS name, 'SUM(ebitda_inr_cr)' AS sql_expression, 'Field / Asset × FY' AS grain, 'INR Crore' AS unit, 'Finance' AS owner_domain, ['C6', 'C11', 'F1'] AS related_question_ids),
  STRUCT('MET-FIN-011' AS metric_id, 'Standalone EBITDA Margin Pct' AS name, 'AVG(ebitda_margin_pct)' AS sql_expression, 'Asset / Segment × FY' AS grain, 'percentage' AS unit, 'Finance' AS owner_domain, ['C6', 'F1'] AS related_question_ids),
  STRUCT('MET-FIN-012' AS metric_id, 'Standalone Profit Before Tax (PBT)' AS name, 'SUM(pbt_inr_cr)' AS sql_expression, 'Company / Asset × FY' AS grain, 'INR Crore' AS unit, 'Finance' AS owner_domain, ['F1', 'F4'] AS related_question_ids),
  STRUCT('MET-FIN-013' AS metric_id, 'Standalone Profit After Tax (PAT)' AS name, 'SUM(pat_inr_cr)' AS sql_expression, 'Company × FY' AS grain, 'INR Crore' AS unit, 'Finance' AS owner_domain, ['F4'] AS related_question_ids),
  STRUCT('MET-FIN-014' AS metric_id, 'Offshore Segment PBT' AS name, '34385.0' AS sql_expression, 'Segment × FY26' AS grain, 'INR Crore' AS unit, 'Finance' AS owner_domain, ['F4'] AS related_question_ids),
  STRUCT('MET-FIN-015' AS metric_id, 'Onshore Segment PBT' AS name, '6246.0' AS sql_expression, 'Segment × FY26' AS grain, 'INR Crore' AS unit, 'Finance' AS owner_domain, ['F4'] AS related_question_ids),
  STRUCT('MET-FIN-016' AS metric_id, 'Capital Expenditure (Capex) Spend' AS name, 'SUM(actual_spend_inr_cr)' AS sql_expression, 'Project × FY' AS grain, 'INR Crore' AS unit, 'Finance' AS owner_domain, ['C7', 'C9', 'F2'] AS related_question_ids),
  STRUCT('MET-FIN-017' AS metric_id, 'Capex Utilisation vs Revised Estimate (RE) Pct' AS name, 'AVG(capex_utilisation_pct)' AS sql_expression, 'Project / Asset × FY' AS grain, 'percentage' AS unit, 'Finance' AS owner_domain, ['C7', 'F2'] AS related_question_ids),
  STRUCT('MET-FIN-018' AS metric_id, 'Secondary and Tertiary Recovery Capex' AS name, 'SUM(secondary_recovery_capex_inr_cr)' AS sql_expression, 'Asset × FY' AS grain, 'INR Crore' AS unit, 'Finance' AS owner_domain, ['C7'] AS related_question_ids),
  STRUCT('MET-FIN-019' AS metric_id, 'Year-End Trade Receivables Outstanding' AS name, 'SUM(outstanding_amount_inr_cr)' AS sql_expression, 'Customer × FY' AS grain, 'INR Crore' AS unit, 'Finance' AS owner_domain, ['F10'] AS related_question_ids),
  STRUCT('MET-FIN-020' AS metric_id, 'Days Sales Outstanding (DSO / Debtor Days)' AS name, 'AVG(aging_days)' AS sql_expression, 'Customer × FY' AS grain, 'days' AS unit, 'Finance' AS owner_domain, ['F10'] AS related_question_ids),
  STRUCT('MET-FIN-021' AS metric_id, 'Overdue Receivables (>90 Days) Pct' AS name, 'SUM(CASE WHEN aging_days > 90 THEN outstanding_amount_inr_cr ELSE 0 END) * 100.0 / NULLIF(SUM(outstanding_amount_inr_cr), 0)' AS sql_expression, 'Customer Segment × FY' AS grain, 'percentage' AS unit, 'Finance' AS owner_domain, ['F10'] AS related_question_ids),
  STRUCT('MET-FIN-022' AS metric_id, 'Total Procurement Purchase Orders Value' AS name, 'SUM(revised_po_value_inr) / 10000000.0' AS sql_expression, 'Vendor / Category × FY' AS grain, 'INR Crore' AS unit, 'Commercial' AS owner_domain, ['F5', 'P16'] AS related_question_ids),
  STRUCT('MET-FIN-023' AS metric_id, 'MSE Vendor Spend Share Pct' AS name, 'SUM(CASE WHEN is_mse_vendor THEN revised_po_value_inr ELSE 0 END) * 100.0 / NULLIF(SUM(revised_po_value_inr), 0)' AS sql_expression, 'Company × FY' AS grain, 'percentage' AS unit, 'Commercial' AS owner_domain, ['P19'] AS related_question_ids),
  STRUCT('MET-FIN-024' AS metric_id, 'Top-10 Vendor Concentration Pct' AS name, 'SUM(top10_vendor_value) * 100.0 / SUM(total_procurement_value)' AS sql_expression, 'Company × FY' AS grain, 'percentage' AS unit, 'Commercial' AS owner_domain, ['F5'] AS related_question_ids),
  STRUCT('MET-CORP-001' AS metric_id, 'Standalone CSR Mandate Obligation (2%)' AS name, 'SUM(actual_disbursed_inr_cr)' AS sql_expression, 'State × Theme × FY' AS grain, 'INR Crore' AS unit, 'Corporate' AS owner_domain, ['F9', 'X5'] AS related_question_ids),
  STRUCT('MET-CORP-002' AS metric_id, 'DPE MoU Composite Score (DPE-Weighted 4.28)' AS name, 'ROUND(SUM(weighted_score), 2) [DPE-weighted: sum of parameter weightage * achieved score / 100 per mou_targets; evaluates to 4.28 for FY26]' AS sql_expression, 'Company × FY' AS grain, 'score' AS unit, 'Corporate' AS owner_domain, ['C10', 'F6'] AS related_question_ids),
  STRUCT('MET-CORP-003' AS metric_id, 'Dividend Payout Ratio Pct' AS name, 'AVG(dividend_payout_ratio_pct)' AS sql_expression, 'Company × FY' AS grain, 'percentage' AS unit, 'Corporate' AS owner_domain, ['F4'] AS related_question_ids),
  STRUCT('MET-CORP-004' AS metric_id, 'Standalone Return on Capital Employed (ROCE)' AS name, 'AVG(standalone_roce_pct)' AS sql_expression, 'Company × FY' AS grain, 'percentage' AS unit, 'Corporate' AS owner_domain, ['F4'] AS related_question_ids),
  # Addendum GAP metrics
  STRUCT('MET-ENV-001' AS metric_id, 'Environmental Incident Count Total' AS name, 'COUNT(DISTINCT incident_id)' AS sql_expression, 'Work Centre × Incident Type × FY' AS grain, 'count' AS unit, 'HSE' AS owner_domain, ['GAP_ENV_01'] AS related_question_ids),
  STRUCT('MET-ENV-002' AS metric_id, 'Process Safety Tier-1 Incidents' AS name, 'COUNT(DISTINCT CASE WHEN severity = \\'Tier_1\\' THEN incident_id END)' AS sql_expression, 'Work Centre × FY' AS grain, 'count' AS unit, 'HSE' AS owner_domain, ['GAP_ENV_01', 'GAP_ENV_02'] AS related_question_ids),
  STRUCT('MET-ENV-003' AS metric_id, 'Oil Spill Volume Released (bbl)' AS name, 'SUM(CASE WHEN incident_type = \\'oil_spill\\' THEN volume_released ELSE 0 END)' AS sql_expression, 'Asset / Installation × FY' AS grain, 'bbl' AS unit, 'HSE' AS owner_domain, ['GAP_ENV_02'] AS related_question_ids),
  STRUCT('MET-ENV-004' AS metric_id, 'Environmental Statutory Penalties Levied' AS name, 'SUM(penalty_inr_lakh)' AS sql_expression, 'Regulator × FY' AS grain, 'INR Lakh' AS unit, 'HSE' AS owner_domain, ['GAP_ENV_01'] AS related_question_ids),
  STRUCT('MET-POSH-001' AS metric_id, 'POSH Complaints Registered Total' AS name, 'COUNT(DISTINCT case_id)' AS sql_expression, 'Work Centre × FY' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['GAP_POSH_01'] AS related_question_ids),
  STRUCT('MET-POSH-002' AS metric_id, 'POSH Inquiry Within 90-Day Norm Pct' AS name, 'COUNT(DISTINCT CASE WHEN inquiry_days <= 90 THEN case_id END) * 100.0 / NULLIF(COUNT(DISTINCT case_id), 0)' AS sql_expression, 'Company × FY' AS grain, 'percentage' AS unit, 'HR' AS owner_domain, ['GAP_POSH_01', 'GAP_POSH_02'] AS related_question_ids),
  STRUCT('MET-POSH-003' AS metric_id, 'POSH Substantiated Disciplinary Actions Count' AS name, 'COUNT(DISTINCT CASE WHEN outcome_category = \\'substantiated_disciplinary_action\\' THEN case_id END)' AS sql_expression, 'Company × FY' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['GAP_POSH_02'] AS related_question_ids),
  STRUCT('MET-APP-001' AS metric_id, 'Annual Apprentice Engagement Intake' AS name, 'COUNT(DISTINCT apprentice_id)' AS sql_expression, 'Work Centre × Trade × FY' AS grain, 'count' AS unit, 'HR' AS owner_domain, ['GAP_APP_01'] AS related_question_ids),
  STRUCT('MET-APP-002' AS metric_id, 'Technical Apprentice Ratio' AS name, 'COUNT(DISTINCT CASE WHEN trade_category = \\'technical\\' THEN apprentice_id END) * 100.0 / NULLIF(COUNT(DISTINCT apprentice_id), 0)' AS sql_expression, 'Work Centre × FY' AS grain, 'percentage' AS unit, 'HR' AS owner_domain, ['GAP_APP_01'] AS related_question_ids),
  STRUCT('MET-APP-003' AS metric_id, 'Apprentice Affirmative Action Representation Pct' AS name, 'COUNT(DISTINCT CASE WHEN category IN (\\'SC\\', \\'ST\\', \\'OBC\\', \\'EWS\\', \\'PwD\\') THEN apprentice_id END) * 100.0 / NULLIF(COUNT(DISTINCT apprentice_id), 0)' AS sql_expression, 'Company × FY' AS grain, 'percentage' AS unit, 'HR' AS owner_domain, ['GAP_APP_02'] AS related_question_ids),
  STRUCT('MET-PROC-001' AS metric_id, 'GeM Procurement Value Share Pct' AS name, 'SUM(CASE WHEN procurement_channel = \\'GeM\\' THEN revised_po_value_inr ELSE 0 END) * 100.0 / NULLIF(SUM(revised_po_value_inr), 0)' AS sql_expression, 'Work Centre × FY' AS grain, 'percentage' AS unit, 'Commercial' AS owner_domain, ['GAP_GEM_01'] AS related_question_ids),
  STRUCT('MET-PROC-002' AS metric_id, 'MSE SC/ST Vendor Procurement Value Share Pct' AS name, 'SUM(CASE WHEN mse_vendor_social_category IN (\\'SC\\', \\'ST\\') THEN revised_po_value_inr ELSE 0 END) * 100.0 / NULLIF(SUM(revised_po_value_inr), 0)' AS sql_expression, 'Company × FY' AS grain, 'percentage' AS unit, 'Commercial' AS owner_domain, ['GAP_GEM_02'] AS related_question_ids),
  STRUCT('MET-PROC-003' AS metric_id, 'MSE Women Entrepreneur Procurement Value Share Pct' AS name, 'SUM(CASE WHEN mse_vendor_social_category = \\'women\\' THEN revised_po_value_inr ELSE 0 END) * 100.0 / NULLIF(SUM(revised_po_value_inr), 0)' AS sql_expression, 'Company × FY' AS grain, 'percentage' AS unit, 'Commercial' AS owner_domain, ['GAP_GEM_02'] AS related_question_ids)
])
"""
    with open(GOLD_DIR / "metric_definitions.sqlx", "w", encoding="utf-8") as f:
        f.write(metric_defs)


def generate_assertions():
    # 1. silver_foreign_keys.sqlx
    fk_assertion = """config {
  type: "assertion",
  schema: "hrfin_silver",
  description: "Check referential integrity: every employee work centre and grade must exist in dimension tables"
}

SELECT
  e.emp_id,
  e.current_wc_id,
  e.current_grade_id
FROM ${ref("employee_master")} e
LEFT JOIN ${ref("dim_work_centre")} w ON e.current_wc_id = w.wc_id
LEFT JOIN ${ref("dim_grade")} g ON e.current_grade_id = g.grade_id
WHERE w.wc_id IS NULL OR g.grade_id IS NULL
"""
    with open(ASSERTIONS_DIR / "silver_foreign_keys.sqlx", "w", encoding="utf-8") as f:
        f.write(fk_assertion)

    # 2. silver_accepted_values.sqlx
    av_assertion = """config {
  type: "assertion",
  schema: "hrfin_silver",
  description: "Check accepted values for employee master categories and gender"
}

SELECT
  emp_id,
  gender,
  category
FROM ${ref("employee_master")}
WHERE gender NOT IN ('Male', 'Female', 'Other')
   OR category NOT IN ('General', 'SC', 'ST', 'OBC', 'EWS')
"""
    with open(ASSERTIONS_DIR / "silver_accepted_values.sqlx", "w", encoding="utf-8") as f:
        f.write(av_assertion)

    # 3. gold_calibration_reconciliation.sqlx
    cal_assertion = """config {
  type: "assertion",
  schema: "hrfin_silver",
  description: "Assert Gold marts reconcile to calibration targets within ±2% tolerance"
}

WITH cal_check AS (
  SELECT
    (SELECT COUNT(*) FROM ${ref("employee_master")} WHERE doj <= DATE '2026-03-31' AND (separation_date IS NULL OR separation_date > DATE '2026-03-31')) AS hc_act,
    23117 AS hc_tgt,
    (SELECT gross_revenue_inr_cr FROM ${ref("mart_corporate_performance")} WHERE fiscal_year = 'FY26') AS rev_act,
    132508.0 AS rev_tgt,
    (SELECT total_csr_spend_inr_cr FROM ${ref("mart_corporate_performance")} WHERE fiscal_year = 'FY26') AS csr_act,
    949.0 AS csr_tgt,
    (SELECT ROUND(SUM(total_liquids_production_mmt), 3) FROM ${ref("mart_asset_productivity")} WHERE fiscal_year = 'FY26') AS liquids_act,
    20.501 AS liquids_tgt,
    (SELECT ROUND(SUM(gas_production_bcm), 3) FROM ${ref("mart_asset_productivity")} WHERE fiscal_year = 'FY26') AS gas_act,
    19.966 AS gas_tgt
)
SELECT
  *
FROM cal_check
WHERE ABS(hc_act - hc_tgt) / hc_tgt > 0.02
   OR ABS(rev_act - rev_tgt) / rev_tgt > 0.02
   OR ABS(csr_act - csr_tgt) / csr_tgt > 0.02
   OR ABS(liquids_act - liquids_tgt) / liquids_tgt > 0.02
   OR ABS(gas_act - gas_tgt) / gas_tgt > 0.02
"""
    with open(ASSERTIONS_DIR / "gold_calibration_reconciliation.sqlx", "w", encoding="utf-8") as f:
        f.write(cal_assertion)

    # 4. silver_dim_grade_group_not_null.sqlx
    group_assertion = """config {
  type: "assertion",
  schema: "hrfin_silver",
  description: "Assert that dim_grade group is non-null and valid for all grades"
}

SELECT
  grade_id,
  cadre,
  `group`
FROM ${ref("dim_grade")}
WHERE `group` IS NULL OR TRIM(`group`) = ''
"""
    with open(ASSERTIONS_DIR / "silver_dim_grade_group_not_null.sqlx", "w", encoding="utf-8") as f:
        f.write(group_assertion)

    # 5. silver_headcount_snapshot_grade_fk.sqlx
    hc_fk_assertion = """config {
  type: "assertion",
  schema: "hrfin_silver",
  description: "Assert that all grade_ids in headcount_snapshot reference valid dim_grade with non-null cadre and group"
}

SELECT
  h.grade_id,
  h.wc_id,
  h.fiscal_year
FROM ${ref("headcount_snapshot")} h
LEFT JOIN ${ref("dim_grade")} g ON h.grade_id = g.grade_id
WHERE g.grade_id IS NULL OR g.cadre IS NULL OR g.group IS NULL
"""
    with open(ASSERTIONS_DIR / "silver_headcount_snapshot_grade_fk.sqlx", "w", encoding="utf-8") as f:
        f.write(hc_fk_assertion)


def main():
    print("Generating complete Dataform repository including Addendum Gaps...")
    setup_directories()
    write_workflow_settings()
    write_credentials()
    write_sources_js()
    generate_silver_rejects()
    generate_silver_models()
    generate_gold_models()
    generate_semantic_views()
    generate_metadata_tables()
    generate_assertions()
    print("Successfully generated all Dataform models and assertions!")


if __name__ == "__main__":
    main()


