# P2H.6 Review — Employee 360 Dataform, Semantic Model & Certified Queries

- **Step:** P2H.6
- **Reviewer:** reviewer-p16 (Claude Opus 4.6 Medium, Role R)
- **Implementer:** gemini-3.1-pro-high + coordinator (`e7f861b` on branch `v3/P2H5-e360`)
- **Verdict:** CHANGES REQUESTED
- **Round:** 1

## BLUF

**`P2H.6` is `CHANGES REQUESTED` due to four blocking defects (`P2H6-B1` through `P2H6-B4`): the Dataform SQLX models are literal `'val'` / `1.0` stubs that do not join the HR satellite tables or reference dimensions, the Silver/Dataform schema generator and reference-dim loader were not wired up, `semantic_model.yaml` crashes `get_semantic_model()` with a duplicate `employee_cost_cr` metric (breaking 20 backend tests) while omitting 26 of 30 `SPEC-04 §8` KPIs, and `certified/library.yaml` appends 12 broken `SELECT * ... WHERE emp_id = @self_emp_id` stubs (breaking 2 more backend tests).**

---

## Must-Fix Blockers (`file:line`)

### 1. `P2H6-B1` (Blocking) — Dataform SQLX Models (`int_employee_month.sqlx`, `fact_employee_cost_pool.sqlx`, `v_employee_360_fy.sqlx`, `v_employee_pay_component_long.sqlx`, `ssot_workforce_employee_compat.sqlx`, `publish_employee_360.sqlx`) Are Hardcoded Constant Stubs

- **Files:**
  - [int_employee_month.sqlx](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/dataform/definitions/gold/int_employee_month.sqlx#L1-L351)
  - [fact_employee_cost_pool.sqlx](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/dataform/definitions/gold/fact_employee_cost_pool.sqlx#L1-L12)
  - [v_employee_360_fy.sqlx](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/dataform/definitions/gold/v_employee_360_fy.sqlx#L1-L19)
  - [v_employee_pay_component_long.sqlx](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/dataform/definitions/gold/v_employee_pay_component_long.sqlx#L1-L8)
  - [ssot_workforce_employee_compat.sqlx](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/dataform/definitions/gold/ssot_workforce_employee_compat.sqlx#L1-L7)
  - [publish_employee_360.sqlx](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/dataform/definitions/gold/publish_employee_360.sqlx#L1-L8)
- **What is wrong:**
  1. **`int_employee_month.sqlx:1-351`:** Joins only `employee_master` and `payroll_monthly` (`lines 349-350`), never joins `posting_history`, `promotion_history`, `dpc_cases`, `separations`, `apar_ratings`, `training_records`, `leave_ledger`, `medical_claims`, `dim_work_centre`, `dim_grade`, `dim_discipline`, `dim_cost_centre`, `dim_ida_rate`, `dim_hra_rate`, or `dim_app_user` (`Packet §5.1`), and hardcodes ~140 of the 186 columns to literal `'val'`, `1`, `1.0`, `true`, or `CURRENT_DATE()` (`lines 25-347`). Even `is_month_end_active` is hardcoded `true`, `fiscal_year` defaults to `'FY26'`, and `net_pay_inr`, `ctc_monthly_inr`, `cost_total_inr`, `el_balance_days`, `training_hours`, `apar_grade`, `delhi_overdue_flag`, and `is_persona_identity` are literal constants (`1.0`, `'val'`, `true`).
  2. **`fact_employee_cost_pool.sqlx:1-12`:** Targets `schema: "hrfin_stage"` and emits 1 dummy constant row (`SELECT CURRENT_DATE() AS month_start, 'FY26' AS fiscal_year, 'Pool' AS pool_name, 0.0 AS amount_inr`) instead of reading `${ref("sap_employee_cost_pool")}` with `SPEC-04 §7.2` columns (`fiscal_year, month_start, pool_code, note35_line, amount_inr, allocation_basis, cost_destination, segment, basis`).
  3. **`v_employee_360_fy.sqlx:1-19`:** Selects only 5 columns (`emp_id, fiscal_year, gross_fy, ctc_fy, cost_total_fy`), omitting `ot_hours_fy`, last-value attributes in FY (`grade_id`, `wc_id`, `basin_name`, `segment`, `tenure_years`), `months_on_roll`, `separated_in_fy`, `joined_in_fy` (`SPEC-04 §9`, `Packet §5.3`).
  4. **`v_employee_pay_component_long.sqlx:1-8`:** Does not `UNPIVOT` families F–H; returns `SELECT emp_id, month_start, 'basic' AS component_group, basic_pay_inr AS amount_inr` and omits `component_code` (`SPEC-04 §9`, `Packet §5.3`).
  5. **`ssot_workforce_employee_compat.sqlx:1-7`:** Returns only 6 columns (`emp_id, emp_name, current_grade_id, discipline_id, wc_id, employment_status`) instead of preserving the exact column surface of `ssot_workforce_employee` (`continuous_stay_years`, `total_tenure_years`, `age_years`, `years_to_retirement`, `is_retiring_within_3yr`, `fy26_training_hours`, `fy26_gross_salary_lakh`, `fy26_apar_score`, etc. required by `semantic_model.yaml:12-175` and `Packet §5.3`).
  6. **`publish_employee_360.sqlx:1-8`:** Contains `-- TODO: wait for P2H.8` and `SELECT 1;` instead of the `Packet §5.2` atomic `CREATE OR REPLACE TABLE ...hrfin_gold.ssot_employee_360 COPY ...hrfin_stage.ssot_employee_360` and `fact_employee_cost_pool` operations with `dependencies: ["assert_recon_block_pass"]`.
- **Required Fix:**
  - Implement real SQL joins, temporal interval matching (`eff_from <= month_end AND (eff_to IS NULL OR eff_to >= month_start)`), and calculated fields across `int_employee_month.sqlx`, `ssot_employee_360.sqlx`, `fact_employee_cost_pool.sqlx`, `v_employee_360_fy.sqlx`, `v_employee_pay_component_long.sqlx`, `ssot_workforce_employee_compat.sqlx`, and `publish_employee_360.sqlx` per `Packet §5.1–§5.3` and `SPEC-04 §4, §7.2, §9`.

---

### 2. `P2H6-B2` (Blocking) — Medallion Silver Schema, Dataform Generator, Reference Dim Loader, and Upload Manifest Not Updated

- **Files:**
  - [schema_silver.yaml](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/world_bible/schema_silver.yaml#L6622-L6633)
  - [generate_dataform_project.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/generate_dataform_project.py#L51-L96)
  - [load_reference_dims.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/load_reference_dims.py#L1-L366)
  - [upload_manifest.csv](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/upload_manifest.csv#L1604)
- **What is wrong:**
  1. **`schema_silver.yaml:6622-6633`:** Instead of adding the new `SPEC-04 §4` columns to `employee_master`, `posting_history`, `payroll_monthly`, `leave_ledger`, `separations` so `generate_dataform_project.py` emits them into `definitions/silver/*.sqlx` (`Packet §2 & §3 item 1`), it appends a dummy 1-column table `employee_360` (`emp_id`).
  2. **`generate_dataform_project.py:51-96`:** `write_sources_js()` was not updated to declare `sap_employee_cost_pool` or the 5 new reference dims (`dim_grade_pay_scale`, `dim_ida_rate`, `dim_hra_rate`, `dim_allowance_rule`, `dim_payroll_policy_fy`) required by `Packet §3 item 2 & §5.4`.
  3. **`load_reference_dims.py:1-366`:** Was not updated (`0` diff lines) to load `dim_grade_pay_scale`, `dim_ida_rate`, `dim_hra_rate`, `dim_allowance_rule`, `dim_payroll_policy_fy` into `hrfin_ref` (`Packet §3 item 12`, `SPEC-04 §3.2 & §5`).
  4. **`upload_manifest.csv:1604`:** Has placeholder `0,md5` (`sap_employee_cost_pool,landing/sap/employee_cost_pool.csv,0,md5`) and omits `landing/sap/payroll_policy_fy.csv`.
- **Required Fix:**
  - Add all new `SPEC-04 §4` columns to the existing HR tables in `schema_silver.yaml`, update `generate_dataform_project.py` (`write_sources_js()` and Silver SQLX generation) and re-run it, implement the 5 new `hrfin_ref.dim_*` loaders in `load_reference_dims.py`, and record real byte sizes and MD5 checksums in `upload_manifest.csv`.

---

### 3. `P2H6-B3` (Blocking) — `semantic_model.yaml` Crashes Backend with `ValueError: metric name employee_cost_cr defined twice` (20 Failing Pytest Tests) and Omits 26 of 30 `SPEC-04 §8` KPIs

- **Files:**
  - [semantic_model.yaml](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/yukti/backend/app/brain/semantic_model.yaml#L1203-L1250)
  - [semantic_model.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/yukti/backend/app/brain/semantic_model.py#L94)
- **What is wrong:**
  1. **Duplicate metric name crashes `get_semantic_model()` (`semantic_model.yaml:1233`):** `employee_month.metrics.employee_cost_cr` collides with `corporate_financials.metrics.employee_cost_cr` (`line 781`). Because `SemanticModel._index()` enforces globally unique metric names across all subjects (`semantic_model.py:92-94`), loading the semantic model raises `ValueError: metric name employee_cost_cr defined twice`, breaking **20 tests** in `tests/test_semantic_model_and_flag.py` and `tests/test_self_scope.py`.
  2. **26 of 30 `SPEC-04 §8` KPIs and all subject `fields:` are missing (`semantic_model.yaml:1203-1250`):** `employee_360`, `employee_month`, and `employee_fy` have empty `fields: {}`, `employee_month` points to `hrfin_stage.int_employee_month` instead of `hrfin_gold.ssot_employee_360`, and only 4 metrics (`headcount_fy_end`, `avg_headcount`, `employee_cost_cr`, `cost_per_employee_lakh`) were stubbed. All remaining 26 KPIs in `SPEC-04 §8` (`fte`, `ctc_per_grade_avg_lakh`, `revenue_per_employee_cr`, `pat_per_employee_cr`, `employee_cost_pct_revenue`, `overtime_pct_of_pay`, `overtime_hours_per_workman`, `allowance_mix_pct`, `benefits_cost_per_employee_lakh`, `medical_cost_per_employee`, `pay_compression_ratio`, `span_of_control`, `attrition_pct`, `turnover_pct_brsr`, `retirements_next_n`, `transfer_overdue_cohort`, `delhi_overdue_cohort_cost_cr`, `capitalised_share_pct`, `entry_pay_monthly`, `employee_cost_per_boe`, and all 6 `what_if_*` scenario KPIs) are missing.
- **Required Fix:**
  - Populate the dimensions/fields and all 30 `SPEC-04 §8` KPIs in `semantic_model.yaml` using unique metric names (do not collide with `corporate_financials.metrics.employee_cost_cr`), point all gold subjects to `ongc-hr-finance-agent.hrfin_gold.*`, and ensure `pytest tests/test_semantic_model_and_flag.py tests/test_self_scope.py` passes 100%.

---

### 4. `P2H6-B4` (Blocking) — `certified/library.yaml` Appends 12 Identical `SELECT * ... WHERE emp_id = @self_emp_id` Stubs That Break `test_certified_query.py` and `test_catalog_consistency.py`

- **Files:**
  - [library.yaml](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/yukti/backend/certified/library.yaml#L4272-L4319)
- **What is wrong:**
  1. **All 12 entries (`library.yaml:4272-4319`) are identical `SELECT *` stubs:** Every entry (`self_payslip`, `self_leave`, `self_posting`, `entry_pay_by_grade`, `ctc_by_grade`, `pay_component_mix_by_grade`, `cost_per_employee_trend`, `revenue_per_employee_trend`, `overtime_by_wc`, `medical_cost_trend`, `delhi_overdue_cohort_cost`, `employee_cost_recon_fy`) has `parameterized_sql: SELECT * FROM ongc-hr-finance-agent.hrfin_gold.ssot_employee_360 WHERE emp_id = @self_emp_id` — even for company-wide aggregate queries (`entry_pay_by_grade`, `ctc_by_grade`, `revenue_per_employee_trend`, `overtime_by_wc`, `employee_cost_recon_fy`) that must NOT filter by `@self_emp_id` (`Packet §5.6`).
  2. **Missing required certified query metadata & broken tests:** None of the 12 entries define `group`, `intent_keywords`, `params`, `visual_kind`, or `provenance`, and adding them changes the certified query count / table catalog references without updating `tests/test_certified_query.py::test_certified_library_loading` and `tests/test_catalog_consistency.py::test_tables` (both fail).
- **Required Fix:**
  - Write real parameterized SQL, `group`, `intent_keywords`, `params`, `visual_kind`, and `provenance` for each of the 12 certified queries per `Packet §5.6`, register `ssot_employee_360` / `fact_employee_cost_pool` / `v_employee_360_fy` / `v_employee_pay_component_long` in the catalog consistency allowlist/schema, and ensure `pytest tests/test_certified_query.py tests/test_catalog_consistency.py` passes 100%.

---

## Verification Evidence Executed

- `dataform compile --json` in `data_bank/medallion/dataform`: `tables: 82, assertions: 6, operations: 1, errors: []` (compiles only because the SQLX files are constant `SELECT 'val'` / `SELECT 1` stubs).
- `pytest -v tests/test_certified_query.py tests/test_semantic_model_and_flag.py tests/test_catalog_consistency.py tests/test_self_scope.py` in `yukti/backend`: **21 failed, 125 passed** (`ValueError: metric name employee_cost_cr defined twice` in 20 tests; `test_certified_library_loading` and `test_tables` fail on the 12 `library.yaml` stubs).
