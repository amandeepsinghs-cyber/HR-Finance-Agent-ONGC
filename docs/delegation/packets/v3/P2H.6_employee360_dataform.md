# Task Packet: `P2H.6` Employee-360 Dataform build, semantic model & certified queries

**Executor:** `O→F` — **O** writes the certified queries (SQL safety: `self_payslip`, `self_leave`, `self_posting`, pay/CTC queries) and the KPI SQL contract; **F** (`flash`) does the Dataform wiring, semantic-model YAML and tests (16 files > DELEGATION's ~5-file F limit, hence the split) · **Author:** O (v3 docs) · **Date:** 2026-10-23
**Branch:** `v3/P2H-hr` · **Base SHA:** after P2H.5 approved (G4) · **Max files changed:** 16 · **Budget:** ~80 tool calls; stop after 2 failed self-checks · **Features:** FEAT-021 · **Spec:** [SPEC-04](../../../specs/SPEC-04_employee_360.md) §3, §4, §8, §9 · **Behaviour:** [BEH-06](../../../behaviour/BEH-06_employee_cost_analytics.md) .03–.15, .25–.40 · **Checklist:** row `P2H.6`
**App root (quote it):** `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC`
**Depends on:** P2H.5 landing CSVs · **Blocks:** P2H.7 (needs `cost_expensed_production_inr` by field), P2H.8

## 1. Goal (one sentence)
Build `hrfin_gold.ssot_employee_360` (employee × month), its three views, the cost-pool fact and the reference dims in Dataform with lineage, then expose them through `semantic_model.yaml` KPIs and parameterised certified queries (no hard-coded `EMP-102451`).

## 2. Context you need (read these first, nothing else)
- `docs/specs/SPEC-04_employee_360.md` §3 (objects, partition/cluster), §4 (exact column names/types), §8 (KPIs), §9 (views).
- `data_bank/medallion/generate_dataform_project.py`: **silver and existing gold `.sqlx` are generated** from `world_bible/schema_silver.yaml` and `medallion/bronze/bronze_tables.yaml`; `run_dataform.sh` regenerates them on every run.
- `data_bank/medallion/dataform/definitions/silver/payroll_monthly.sqlx`, `leave_ledger.sqlx` (`TRIM(SUBTY)` values), `employee_master.sqlx`, `posting_history.sqlx`; `gold/v_continuous_stay.sqlx`, `gold/v_cluster_cumulative_tenure.sqlx`.
- `data_bank/medallion/upload_landing.py` + `upload_manifest.csv` (new landing files must be registered).
- `yukti/backend/scripts/build_ssot_gold.py` (to retire; leave-type bug at :76-78).
- `yukti/backend/app/brain/semantic_model.yaml` (subject `workforce` at :13; pay metric at :49).
- `yukti/backend/certified/library.yaml` (:1617, :1649, :1673, :1743 hard-code `EMP-102451`).
- `docs/specs/SPEC-06_personas_identity_rbac_v3.md` §4.2 (`data_class` names, `@self_emp_id`).

## 3. Files you may change / create
1. `data_bank/world_bible/schema_silver.yaml`: add the new payroll/master columns and the new silver tables `employee_cost_pool`, `payroll_policy_fy`.
2. `data_bank/medallion/bronze/bronze_tables.yaml` + `data_bank/medallion/upload_manifest.csv`: register `employee_cost_pool.csv`, `payroll_policy_fy.csv`.
3. `data_bank/medallion/load_reference_dims.py`: load `ida_rates.yaml`, `hra_rates.yaml`, `allowance_rules.yaml`, `grades.yaml` → `dim_ida_rate`, `dim_hra_rate`, `dim_allowance_rule`, `dim_grade_pay_scale`.
4. **New hand-authored folder** `data_bank/medallion/dataform/definitions/v3/` (not touched by the generator):
   - `int_employee_month.sqlx`: joins silver payroll × master × posting islands × leave × training × APAR × separations at emp × month.
   - `ssot_employee_360.sqlx`: `type: "table"`, `schema: "hrfin_stage"`, `bigquery: {partitionBy: "month_start", clusterBy: ["wc_id","grade_id","function_code","emp_id"], requirePartitionFilter: true}`; every SPEC-04 §4 column, names and types exact.
   - `fact_employee_cost_pool.sqlx`.
   - `v_employee_360_current.sqlx`, `v_employee_360_fy.sqlx`, `v_employee_pay_component_long.sqlx`.
   - `ssot_workforce_employee_compat.sqlx`: view named `ssot_workforce_employee` in `hrfin_gold` projecting the current view to the old column names.
   - `publish_employee_360.sqlx`: `type: "operations"`, copies stage → `hrfin_gold` **with a dependency on** `assert_recon_block_pass` (created in P2H.8; until then a TODO stub that always fails the publish).
5. `yukti/backend/app/brain/semantic_model.yaml`: new subjects `employee_360` (current), `employee_month`, `employee_fy` with the §8 KPIs (each with `expr`, `aggregation`, `unit`, `label`, `data_class` ∈ {`general_hr`, `pay_aggregate`, `pay_individual`, `named`, `apar`, `sensitive`}) and dimension `grade_level_order` as the default sort.
6. `yukti/backend/certified/library.yaml`: replace the 4 hard-coded queries with `@self_emp_id`; add the 12 certified queries listed in SPEC-04 §8.
7. `yukti/backend/scripts/build_ssot_gold.py`: add a deprecation header and exit early with a message pointing to Dataform v3 (do not delete).

## 4. Do NOT touch
- Generated silver/gold `.sqlx` files directly (change the YAML + generator inputs instead); `generate_dataform_project.py` logic (unless the YAML route is impossible; then stop and ask).
- Python app code (`turn_runner.py`, `access_control.py`, planner/compiler): the salary handler fix is a separate P5/P2F step.
- **No** `git commit/push/reset/checkout/stash`; no deploys. **No BigQuery writes**: run `dataform compile` only. Execution of `run_dataform.sh` is done by O after G4.

## 5. Exact requirements
1. Column names, order of families, types and NULL-ability exactly as SPEC-04 §4. Add a column-description map in each `config { columns: {...} }` block from the spec "Description" column, plus `sensitivity` and `basis` tags in descriptions (`[PAY][C]`).
2. Leave mapping: `Earned_Leave_EL` → EL, `Half_Pay_Leave_HPL` → HPL, `Casual_Leave_CL` → CL (BUG-29). Month-end balance = last ledger row ≤ month end.
3. Station tenure via gaps-and-islands over `posting_history` (reuse the `v_continuous_stay` logic, but take the island grade from the latest posting, not `MAX(grade_id)`).
4. `v_employee_360_fy`: sums for money; `ANY_VALUE` at the last month for attributes; `months_on_roll`, `joined_in_fy`, `separated_in_fy`.
5. `v_employee_pay_component_long`: `UNPIVOT` families F–H into (`component_code`, `component_group`, `amount_inr`); `component_group` ∈ {basic, da, hra, perks, allowances, variable, employer_benefits, deductions}.
6. KPI SQL must compute ratios from sums (e.g. `SUM(cost)/AVG_HC`), never average ratios. `avg_headcount` = (open + close)/2 for FY metrics.
7. Certified queries carry `data_class` and `visual_hint` matching BEH-06 (e.g. `entry_pay_by_grade` → `waterfall`).

## 6. Examples / reference patterns
```sql
-- v_employee_360_current (sketch)
SELECT * FROM ${ref("ssot_employee_360")}
WHERE month_start = (SELECT MAX(month_start) FROM ${ref("ssot_employee_360")} WHERE month_start <= DATE_TRUNC(CURRENT_DATE(), MONTH))
  AND is_month_end_active
```
```yaml
# semantic_model.yaml
employee_fy:
  table: hrfin_gold.v_employee_360_fy
  metrics:
    cost_per_employee_lakh: {expr: "SUM(cost_total_fy)/1e5 / NULLIF(@avg_headcount,0)", aggregation: ratio, unit: inr_lakh, label: "Employee cost per employee (₹ lakh)", data_class: general_hr}
```

## 7. Acceptance criteria (copied into the review)
- [ ] `dataform compile` succeeds with 0 errors; the new v3 actions appear in the compiled graph with the stated partition/cluster config.
- [ ] Every SPEC-04 §4 column is present (scripted diff of spec table vs compiled schema = 0 missing, 0 extra except documented helpers).
- [ ] `grep -n "EMP-102451" yukti/backend/certified/library.yaml` returns 0 hits; the new queries use `@self_emp_id`.
- [ ] `semantic_model.yaml` loads (`python -c "import yaml;yaml.safe_load(open(...))"`) and the existing semantic-model tests pass.
- [ ] Offline SQL lint/dry compile of each certified query via the existing compiler test harness (if present) passes.
- [ ] Generated silver files regenerated from the YAML show the new columns (`generate_dataform_project.py` run locally, diff reviewed).

## 8. Self-check commands
```bash
cd "<app root>/data_bank" && uv run python medallion/generate_dataform_project.py && cd medallion/dataform && dataform compile
cd "<app root>/yukti/backend" && .venv/bin/python -m pytest -q -k "semantic or certified or rbac" -p no:cacheprovider
cd "<app root>" && grep -n "EMP-102451" yukti/backend/certified/library.yaml; git status --short
```

## 9. Stop-and-ask triggers
- The generator overwrites `definitions/v3/`, or silver columns cannot be added through YAML.
- A SPEC-04 column cannot be derived from the P2H.5 landing outputs.
- Existing tests that reference `ssot_workforce_employee` columns fail against the compat view.

## 10. Report format
- **Files changed** · **Self-check output** · **Acceptance** ✅/❌ with evidence (compile log excerpt, column-diff result) · **Open questions / deviations**
