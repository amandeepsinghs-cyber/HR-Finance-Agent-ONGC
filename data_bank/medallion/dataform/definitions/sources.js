// BigQuery source declarations for Bronze layer
const bronzeTables = [
  "sap_pa0002_pa0001",
  "sap_pa0001",
  "sap_pa0000_promotions",
  "sap_pa0000_separations",
  "sap_py_cluster_exp",
  "sap_eapar_ratings",
  "sap_pa2001_pa2006",
  "sap_co_pa",
  "sap_cosp_coss",
  "sap_ekko_ekpo",
  "sap_fi_ar_invoices",
  "sap_essr_esll",
  "sap_ptrv_head_doc",
  "sap_project_milestones",
  "sap_vigilance_cases_confidential",
  "sap_headcount_monthly_snapshot",
  "db_exports_production_monthly",
  "db_exports_wells_drilled",
  "db_exports_lms_attendance",
  "db_exports_hse_incident_log",
  "db_exports_medical_claims_export",
  "db_exports_access_audit_log",
  "db_exports_rti_applications_export",
  "governance_corporate_financial_summary",
  "governance_subsidiary_group_financials",
  "governance_parliament_questions_index",
  "excel_capex_be_re_actuals",
  "excel_manpower_plan",
  "excel_dpe_mou_scorecard",
  "excel_csr_projects_tracker",
  "excel_succession_planning",
  "excel_legal_cases_tracker",
  "excel_dpc_tracker",
  "excel_training_calendar",
  "excel_icc_committees",
  "excel_reserves_annual",
  "excel_price_fx",
  "excel_treasury_forex_hedges",
  "excel_actuarial_benefit_liabilities",
  "excel_energy_transition_progress",
  "excel_cag_paras_register",
  "excel_board_agenda_index",
  "db_exports_env_incident_log",
  "excel_posh_register",
  "sap_apprentice_ledger",
  "sap_ekko_channel",
  "sap_employee_cost_pool",
  "sap_payroll_policy_fy"
];

bronzeTables.forEach(tableName => {
  declare({
    database: "ongc-hr-finance-agent",
    schema: "hrfin_bronze",
    name: tableName,
  });
});

// Preloaded Reference Dimensions in hrfin_silver
const refDims = [
  "dim_work_centre",
  "dim_grade",
  "dim_discipline",
  "dim_field",
  "dim_project",
  "dim_cost_centre",
  "dim_customer",
  "dim_vendor",
  "dim_geography",
  "dim_calendar",
  "dim_price_fx"
];

refDims.forEach(tableName => {
  declare({
    database: "ongc-hr-finance-agent",
    schema: "hrfin_silver",
    name: tableName,
  });
});

// hrfin_ref dims
const hrfinRefDims = [
  "dim_grade_pay_scale", "dim_ida_rate", "dim_hra_rate", "dim_allowance_rule", "dim_payroll_policy_fy", "dim_benefit_scheme", "dim_insurance_plan"
];

hrfinRefDims.forEach(tableName => {
  declare({
    database: "ongc-hr-finance-agent",
    schema: "hrfin_ref",
    name: tableName,
  });
});
