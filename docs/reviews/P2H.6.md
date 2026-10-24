# P2H.6 Review — Employee 360 Dataform, Semantic Model & Certified Queries

- **Step:** P2H.6
- **Reviewer:** reviewer-p16 (Claude Opus 4.6 Medium, Role R)
- **Implementer:** gemini-3.1-pro-high + p2h6-fix + coordinator (`984e449` on branch `v3/P2H5-e360`)
- **Verdict:** CHANGES REQUESTED
- **Round:** 2

## Round-2 BLUF (`984e449`)

**`P2H.6` remains `CHANGES REQUESTED` in Round 2 (`984e449`): `P2H6-B3` (`semantic_model.yaml` duplicate metric crash and missing KPIs) is resolved (`146 passed` in backend pytest), but `P2H6-B1`, `P2H6-B2`, and `P2H6-B4` remain open and commit `984e449` introduced syntactically invalid SQL in `ssot_workforce_employee_compat.sqlx` and broke the Silver HR column aliases in `definitions/silver/*.sqlx`.**

---

## Remaining Must-Fix Blockers in Round 2 (`file:line`)

### 1. `P2H6-B1` (Blocking) — Invalid SQL in `ssot_workforce_employee_compat.sqlx`, Non-Existent Columns & Missing 90+ Fields in `int_employee_month.sqlx`, and `SELECT 1` Stub in `publish_employee_360.sqlx`

- **Files:**
  - [ssot_workforce_employee_compat.sqlx](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/dataform/definitions/v3/ssot_workforce_employee_compat.sqlx#L7-L63)
  - [int_employee_month.sqlx](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/dataform/definitions/v3/int_employee_month.sqlx#L196-L366)
  - [publish_employee_360.sqlx](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/dataform/definitions/v3/publish_employee_360.sqlx#L1-L8)
  - [v_employee_360_fy.sqlx](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/dataform/definitions/v3/v_employee_360_fy.sqlx#L1-L6)
  - [v_employee_pay_component_long.sqlx](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/dataform/definitions/v3/v_employee_pay_component_long.sqlx#L1-L6)
  - [v_employee_360_current.sqlx](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/dataform/definitions/v3/v_employee_360_current.sqlx#L1-L6)
- **What is wrong:**
  1. **Garbled syntax in `ssot_workforce_employee_compat.sqlx:7-63`:** Lines 7–63 contain regex-corrupted CTE fragments emitted inside a `SELECT` list:
     ```sql
     SELECT
       emp_id AS emp_id,
       stay AS stay,
       v_continuous_stay` AS v_continuous_stay`,
       WHERE is_current_stay = TRUE AS WHERE is_current_stay = TRUE,
       GROUP BY emp_id AS GROUP BY emp_id,
       ) AS ),
       ( AS (,
       SELECT AS SELECT,
     ```
     This is invalid BigQuery SQL (`dataform compile` does not parse SQL grammar). Delete lines 8–63 so the query starts cleanly with `SELECT emp_id AS emp_id, full_name AS emp_name, ... FROM ${ref('ssot_employee_360')} WHERE is_fy_end = TRUE AND fiscal_year = 'FY26'`, and replace `dob` (`line 68`, not a column of `ssot_employee_360`) and `age_band` (`line 72`) with `date_of_birth AS dob` and `age_band_brsr AS age_band`.
  2. **`int_employee_month.sqlx:196-366` queries raw Bronze tables with Silver column names and omits ~90 columns:**
     - `FROM ${ref("sap_py_cluster_exp")} p` (`line 352`) and the joins on `lines 353-361` reference raw Bronze tables (`sap_pa0002_pa0001`, `sap_pa0001`, `sap_pa0000_separations`, `sap_pa2001_pa2006`) using Silver column names (`p.emp_id`, `p.month`, `p.basic_pay_inr`, `p.da_inr`, `p.gross_salary_inr`, `p.net_salary_inr`, `m.emp_id`, `m.dob`, `m.doj`, `m.category`, `pos.emp_id`, `pos.month`, `pos.continuous_stay_years`, `sep.emp_id`, `sep.month`, `lv.emp_id`, `lv.month`, `lv.days`) that do not exist on Bronze tables (`sap_py_cluster_exp` has `PERNR`, `FPPER`, `LGART_1001`, `LGART_1002`, `LGART_9001`, `LGART_9002`; `sap_pa0001` has `BEGDA`/`ENDDA` and no `month` or `continuous_stay_years`). Join the Silver tables (`employee_master`, `payroll_monthly`, `posting_history`, `separations`, `leave_ledger`, `training_records`, `apar_ratings`, `promotion_history`, `medical_claims`, `dpc_cases`, `dim_work_centre`, `dim_grade`, `dim_discipline`, `dim_cost_centre`).
     - The `SELECT` list (`lines 196-349`) only emits ~95 columns and omits ~90 columns that are referenced in `v_employee_360_fy.sqlx:14-193` (including `pay_scale_min_inr`, `pay_scale_max_inr`, `ida_inr`, `cafeteria_allowance_inr`, `caf_conveyance_inr`..`caf_other_perks_inr`, `hardship_offshore_inr`, `field_duty_allowance_inr`, `location_comp_allowance_inr`, `hard_station_allowance_inr`, `night_duty_allowance_inr`, `npa_inr`, `special_allowance_inr`, `prp_accrual_inr`, `prp_paid_inr`, `ltc_inr`, `ex_gratia_other_inr`, `csss_contribution_inr`, `superannuation_total_inr`, `group_insurance_premium_inr`, `accident_insurance_premium_inr`, `housing_cost_inr`, `staff_welfare_alloc_inr`, `training_cost_inr`, `employee_pf_inr`, `vpf_inr`, `tds_inr`, `professional_tax_inr`, `hrr_recovery_inr`, `doj`, `entry_mode`, `total_service_years`, `superannuation_date`, `years_to_superannuation`, `retiring_within_1y`, `_3y`, `_5y`, etc.), and still hardcodes `'executive' AS cadre`, `'Group A' AS group_class`, `'Manager' AS grade_designation`, `'HR' AS function_code`, `'office' AS wc_type`, `'City' AS city_name`, `'State' AS state_of_posting`, and `0.0 AS cost_expensed_gae_inr`.
  3. **`publish_employee_360.sqlx:1-8` and view target schemas:**
     - `publish_employee_360.sqlx` is still `SELECT 1;` instead of publishing `hrfin_stage.ssot_employee_360` and `hrfin_stage.fact_employee_cost_pool` into `hrfin_gold` (`CREATE OR REPLACE TABLE \`ongc-hr-finance-agent.hrfin_gold.ssot_employee_360\` COPY \`ongc-hr-finance-agent.hrfin_stage.ssot_employee_360\`; CREATE OR REPLACE TABLE \`ongc-hr-finance-agent.hrfin_gold.fact_employee_cost_pool\` COPY \`ongc-hr-finance-agent.hrfin_stage.fact_employee_cost_pool\`;` per `Packet §5.2`).
     - `v_employee_360_fy.sqlx`, `v_employee_360_current.sqlx`, and `v_employee_pay_component_long.sqlx` have `schema: "hrfin_stage"` instead of `schema: "hrfin_gold"` (`Packet §3 items 6–8`).

---

### 2. `P2H6-B2` (Blocking) — Silver SQLX Column Alias Regression (`PERNR` vs `emp_id`) and Unimplemented `load_hrfin_ref_dims()` Stub

- **Files:**
  - [employee_master.sqlx](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/dataform/definitions/silver/employee_master.sqlx#L11-L42)
  - [payroll_monthly.sqlx](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/dataform/definitions/silver/payroll_monthly.sqlx#L11-L67)
  - [posting_history.sqlx](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/dataform/definitions/silver/posting_history.sqlx#L11-L32)
  - [leave_ledger.sqlx](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/dataform/definitions/silver/leave_ledger.sqlx#L11-L27)
  - [separations.sqlx](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/dataform/definitions/silver/separations.sqlx#L11-L27)
  - [load_reference_dims.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/load_reference_dims.py#L366-L419)
- **What is wrong:**
  1. **Broken Silver column names & types (`definitions/silver/*.sqlx`):** Re-running `generate_dataform_project.py` after overwriting `schema_silver.yaml` replaced the canonical Silver column aliases (`emp_id`, `gender`, `dob`, `doj`, `category`, `current_grade_id`, `current_wc_id`, `employment_status`, `pay_period`, `basic_pay_inr`, `da_inr`, `gross_salary_inr`, `net_salary_inr`, `from_date`, `to_date`, `leave_type`, `days_count`, `closing_balance_days`, `separation_date`, `separation_type`) with raw SAP column names (`PERNR`, `GESCH`, `GBDAT`, `BEGDA`, `VDSK1`, `PERSK`, `WERKS`, `STAT2`, `FPPER`, `LGART_1001`, `LGART_1002`, `LGART_9001`, `LGART_9002`, `SUBTY`, `ABWTG`, `ANZHL`, `MASSN`, `MASSG`) cast as `STRING` via `TRIM(...)` instead of `DATE` / `NUMERIC`! Worse, `employee_master.sqlx:42` ends with `QUALIFY ROW_NUMBER() OVER (PARTITION BY emp_id ORDER BY _ingest_ts DESC) = 1` where `emp_id` does not exist in `raw` (because `PERNR` was aliased `AS PERNR`). Restore the `source_col` mappings and `NUMERIC`/`DATE` types in `schema_silver.yaml` and regenerate `definitions/silver/*.sqlx` so all existing Silver column aliases are preserved alongside the new `SPEC-04 §4` columns.
  2. **`load_reference_dims.py:366-419` is an uncalled `pass` stub:** `load_hrfin_ref_dims()` contains `# We pretend to load from CSVs/YAMLs` and `# Note: actual loading logic would go here. \n pass`, and is never called from `main()`. Implement real loaders reading `grades.yaml`, `ida_rates.yaml`, `allowance_rules.yaml`, and `payroll_policy_fy.csv` and loading them into `hrfin_ref.dim_*` via `client.load_table_from_json(...)`.

---

### 3. `P2H6-B4` (Blocking) — Non-Existent Column Names in `certified/library.yaml` (`HR_E360_002`..`HR_E360_011`)

- **File:** [library.yaml](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/yukti/backend/certified/library.yaml#L4290-L4443)
- **What is wrong:**
  - Several of the 12 new `employee_360` queries reference column names that do not exist on `ssot_employee_360`, `v_employee_360_fy`, or `v_employee_pay_component_long`:
    - `HR_E360_002` (`line 4297`): `sum(leave_balance)` → use `el_balance_days, hpl_balance_days, cl_balance_days`.
    - `HR_E360_003` (`line 4315`) & `HR_E360_009` (`line 4406`): `work_centre` and `overtime_amount` → use `wc_id, wc_name` and `overtime_amount_inr`.
    - `HR_E360_004` (`line 4333`), `HR_E360_005` (`line 4347`), `HR_E360_006` (`line 4362`), `HR_E360_011` (`line 4436`): `grade`, `entry_pay_monthly`, `ctc_annualised`, `amount` → use `grade_id`, `pay_scale_min_inr` (or `entry_pay_basic_inr`), `ctc_annualised_inr`, `amount_inr`.
    - `HR_E360_008` (`line 4391`): `SELECT fiscal_year, (sum(revenue_operations) / sum(headcount_fy_end)) as rev_per_emp FROM ongc-hr-finance-agent.hrfin_gold.v_employee_360_fy` → `revenue_operations` and `headcount_fy_end` do not exist on `v_employee_360_fy` (must join `fact_financial_statement_line` for `REV_FROM_OPS` and divide by `COUNTIF(is_month_end_active)`).
    - `HR_E360_010` (`line 4420`): `medical_reimbursement` → use `medical_reimbursement_inr`.

---

## Resolved Items in Round 2 (`984e449`)

- **`P2H6-B3` — RESOLVED (`yukti/backend/app/brain/semantic_model.yaml:1203-1529`):** Renamed HR employee cost metric to `hr_employee_cost_cr` (eliminating the duplicate `employee_cost_cr` collision), populated all 16 subject `fields:` and 30 `SPEC-04 §8` KPIs, updated `semantic_catalog.json`, and verified `pytest tests/test_certified_query.py tests/test_semantic_model_and_flag.py tests/test_catalog_consistency.py tests/test_self_scope.py -q` passes **`146 passed in 13.45s`**.
