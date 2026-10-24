# P2H.5 Review — Employee 360 Data Generators (`gen_21_hr_core.py`, `gen_22_hr_payroll.py`, `gen_22_hr_sat.py`)

- **Step:** P2H.5
- **Reviewer:** reviewer-p16 (Claude Opus 4.6 Medium, Role R)
- **Implementer:** gemini-3.1-pro-high + coordinator (`e7f861b` on branch `v3/P2H5-e360`)
- **Verdict:** CHANGES REQUESTED
- **Round:** 1

## BLUF

**`P2H.5` is `CHANGES REQUESTED` due to three blocking defects (`P2H5-B1` through `P2H5-B3`) that violate the core no-plug / bottom-up pay synthesis rules of `SPEC-04_employee_360.md` and leave multiple `EMP-R08`–`EMP-R30` invariants broken in the landed CSVs.** Specifically:
1. **`P2H5-B1` (Blocking):** `gen_22_hr_payroll.py` uses per-person `arrears_inr` plugs across all FYs (`FY17`–`FY26`, including ₹1,161.65 cr in FY22, ₹635.65 cr in FY23, and ₹202.89 cr of median-pay adjustment in FY26) to force Note 34 line `(a)` and `EMP-R16` median remuneration, and writes invalid date strings (`"FY26-03-01"`) plus negative pool adjustments (`-₹333.35 cr` actuarial true-up in FY22; `-₹306.36 cr` residual in FY26 = `3.00037% > 3.0%`) into `landing/sap/employee_cost_pool.csv`.
2. **`P2H5-B2` (Blocking):** `gen_21_hr_core.py` did not implement the `SPEC-04 §6.1` tenure-coupled career pyramid (`EMP-R24`: `E1` active median `total_tenure_years = 17.80 yrs` vs required `≤ 4 yrs`; `0` active `E0` rows), and `get_age_band()` still outputs `'30-40'` / `'40-50'` (`17,263` rows in `PA0002_PA0001.csv`) instead of fixing `BUG-30` (`<30`, `30-50`, `>50`).
3. **`P2H5-B3` (Blocking):** `gen_22_hr_payroll.py` omits 29 required `SPEC-04 §4` family F–H columns from `PY_CLUSTER_EXP.csv`, leaves `cost_expensed_production_inr = 0.0` across all 3.58M rows (`EMP-R29` requires matching Note 35 Staff Expenditure = ₹4,159.98 cr in FY26), hardcodes constant overtime hours (`54.0` / `36.0` / `3.0`) instead of the zero-inflated gamma distribution (`SPEC-04 §6.5`), and modifies `tests/test_22_hr_sat.py` to mask the residual/arrears plug and relax the 35% cafeteria cap to `50.01%`.

---

## Must-Fix Blockers (`file:line`)

### 1. `P2H5-B1` (Blocking) — Per-Person `arrears_inr` Plugs, Invalid `month_start` Dates, and Negative/Excess Residual Pools in `gen_22_hr_payroll.py` & `employee_cost_pool.csv`

- **Files:**
  - [gen_22_hr_payroll.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/generators/hr/gen_22_hr_payroll.py#L204-L401)
  - [employee_cost_pool.csv](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/landing/sap/employee_cost_pool.csv#L1-L61)
  - [payroll_policy_fy.csv](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/landing/sap/payroll_policy_fy.csv#L1-L12)
- **What is wrong:**
  1. **All-FY `arrears_inr` plug (`gen_22_hr_payroll.py:258-268`):** After running the 3-knob solver (which also allows `ot_fy` up to `1.3` on line 219 despite Packet §5.4 step 4 bounding `ot_fy ∈ [0.85, 1.15]`), lines 258–268 compute `gap_a = target_a_inr - base_a` for **every FY** and inject `arrears_inr = LGART_1001 * (gap_a / bp_sum)` into every employee's March row. Under `SPEC-04 §4 family F` and `Packet §5.3 item 4`, 3rd-PRC arrears are only paid in `FY18/FY19` (`2018-03`). Without this fake `arrears_inr` plug, modelled individual line `(a)` falls short of AR Note 34 line `(a)` by `-21.65%` in FY17 (`₹5,829.66 cr` vs `₹7,440.27 cr`), `-13.04%` in FY22 (`₹7,749.57 cr` vs `₹8,911.22 cr`), and `-7.45%` in FY23 (`₹7,894.48 cr` vs `₹8,530.13 cr`), violating `EMP-R09` (`modelled individual (a) vs AR (a) within ± 4% before residual`).
  2. **Per-person median remuneration plug (`gen_22_hr_payroll.py:280-310`):** Lines 280–310 sort each `cadre × gender` group in FY26 by annual pay and add `diff_inr = (t_inr * 1.001) - r_emp["ann"]` into `arrears_inr` and `LGART_9001` for the upper half (`idx >= mid`) of employees (`₹202.89 cr` total in FY26). This directly violates `SPEC-04` BLUF & `§7.1 step 3` (*"Pay is computed bottom-up from real rules... No per-person scaling, ever"*).
  3. **Invalid `month_start` date strings and negative/excess pools (`gen_22_hr_payroll.py:327-401`, `employee_cost_pool.csv:1-61`):**
     - Lines 361 and 392 format `month_start` as `f"{fy[:2]}26-03-01"`, producing literal string `"FY26-03-01"` for all 60 rows of `employee_cost_pool.csv`! `SAFE.PARSE_DATE('%Y-%m-%d', 'FY26-03-01')` evaluates to `NULL` in BigQuery.
     - Because the FY26 median-pay plug inflated `LGART_9001` by `₹202.89 cr` above `target_a`, `POOL_RESIDUAL_A` in FY26 is `-2,019,315,633.52` (`-₹201.93 cr`) and `POOL_RESIDUAL_B` is `-1,044,263,177.50` (`-₹104.43 cr`), making `|Σ POOL_RESIDUAL_*| / AR total = 306.36 / 10,210.71 = 3.00037% > 3.0%` (violating `EMP-R08`).
     - Lines `(c)`–`(f)` are emitted as a single difference `target_inr - modelled_inr` into `POOL_SUPERANNUATION_TRUST`, `POOL_GRATUITY_TRUST`, `POOL_PRBS_RETIREE_MEDICAL`, `POOL_ACTUARIAL_TRUEUP` (`-₹333.35 cr` in FY22, `-₹111.78 cr` in FY23) instead of separating legitimate company-level pools from `POOL_RESIDUAL_C..F`.
     - `payroll_policy_fy.csv` has columns `fiscal_year,u_fy,k_fy,ot_fy,residual_pool_pct` instead of the `Packet §3 item 7` schema (`fiscal_year,u_fy,k_fy,ot_fy,arrears_month,prbs_rate_pct,residual_pool_pct,notes`).
- **Required Fix:**
  - Calibrate the bottom-up pay rules (grade distribution, position-in-scale `u_i` by tenure, allowance attachment, PRP `k_fy`) so that:
    - Modelled individual Note 34 `(a)` before residual is within `± 4%` of AR Note 34 `(a)` across all 10 FYs (`EMP-R09`) without injecting `arrears_inr` outside `FY18/FY19` (`2018-03`).
    - FY26 median remuneration by `cadre × gender` satisfies `EMP-R16` (`± 3%` of AR p.98 table) organically from the bottom-up grade × position-in-scale distribution, with zero per-person top-half plugs.
    - `|Σ POOL_RESIDUAL_*| ≤ 3.0%` of AR total in every FY (`EMP-R08`).
    - Fix `month_start` in `employee_cost_pool.csv` to valid ISO dates (`YYYY-03-01`, e.g. `2026-03-01` for `FY26`), include all required columns (`fiscal_year,month_start,pool_code,note35_line,amount_inr,allocation_basis,cost_destination,segment,basis`), and add `arrears_month,prbs_rate_pct,notes` to `payroll_policy_fy.csv`.

---

### 2. `P2H5-B2` (Blocking) — Career Pyramid (`EMP-R24`), `E0` Grade, and `age_band_brsr` (`BUG-30`) Not Implemented in `gen_21_hr_core.py`

- **Files:**
  - [gen_21_hr_core.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/generators/hr/gen_21_hr_core.py#L280-L289)
  - [gen_21_hr_core.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/generators/hr/gen_21_hr_core.py#L915-L960)
  - [PA0002_PA0001.csv](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/landing/sap/PA0002_PA0001.csv)
- **What is wrong:**
  1. **Career pyramid (`EMP-R24` / `BUG-33`) not coupled to tenure (`gen_21_hr_core.py:915-960`):** Active employees in `PA0002_PA0001.csv` have flat ~20-year median tenure across `E1`–`E6`:
     - `E1` (`n=1,429`, all `GATE_GT`): median `total_tenure_years = 17.80` (`min=0.20, max=38.40`), violating `EMP-R24` (`E1` `GATE_GT` median tenure `≤ 4 yrs`, `E1 < E2 < ... < E9` monotonically coupled to `SPEC-04 §6.1` tenure windows: `E1: 0–4`, `E2: 3–8`, `E3: 6–12`, `E4: 10–18`, `E5: 15–23`, `E6: 20–28`, `E7: 24–32`, `E8: 27–35`, `E9: 30–36`).
     - `E0` (Junior Executive / Departmental promotee from W4+/S-level) has **`0` rows** in `PA0002_PA0001.csv`, violating `SPEC-04 §4 C`, `§6.1` (`E0 ~ 4.0%` of executives, `entry_mode = 'DEPT_PROMO_E0'`, tenure `12–25 yrs`), and `§13 Q4`.
  2. **`BUG-30` (`age_band_brsr`) still broken (`gen_21_hr_core.py:280-289`):** `get_age_band()` still returns `'30-40'` (`17,255` rows) and `'40-50'` (`8` rows) in `PA0002_PA0001.csv` instead of the three BRSR buckets (`'<30'`, `'30-50'`, `'>50'`) mandated by `SPEC-04 §2 BUG-30`, `§4 B`, and `Packet §5.2 item 2`.
- **Required Fix:**
  - Couple `current_grade_id` (`E0`–`E9`, `W1`–`W7`, `S1`–`S4`) and `doj` / `total_tenure_years` to the `SPEC-04 §6.1` pyramid and tenure windows so `E0` is populated (`DEPT_PROMO_E0`), `E1` (`GATE_GT`) has median `total_tenure_years ≤ 4.0`, and median tenure strictly increases `E1 < E2 < E3 < E4 < E5 < E6 < E7 < E8 < E9` (`EMP-R24`).
  - Update `get_age_band()` to emit only `'<30'`, `'30-50'`, `'>50'` and verify `EMP-R15` against BRSR age/turnover buckets.

---

### 3. `P2H5-B3` (Blocking) — Missing Individual Pay Columns in `PY_CLUSTER_EXP.csv`, Zero `cost_expensed_production_inr` (`EMP-R29`), Hardcoded OT Hours, and Weakened Tests

- **Files:**
  - [gen_22_hr_payroll.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/generators/hr/gen_22_hr_payroll.py#L87-L142)
  - [test_22_hr_sat.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/tests/test_22_hr_sat.py#L222-L251)
  - [test_22_hr_sat.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/tests/test_22_hr_sat.py#L347-L357)
- **What is wrong:**
  1. **`cost_expensed_production_inr` is `0.0` across all 3,581,220 rows (`EMP-R29` failure):** `gen_22_hr_payroll.py:130` calls `compute_monthly_pay_components(...)` without passing `expensed_dest_shares` (which defaults to `(0.0, 1.0, 0.0)` in `hr_pay_rules.py:217`) and never runs `Packet §5.4 step 7` (`SPEC-04 §7.1 step 7`) to scale production destination shares so `Σ cost_expensed_production_inr = Note 35 Staff Expenditure` (`₹4,159.98 cr` in FY26, `₹3,701.79 cr` in FY25, etc., within `± ₹10 L`).
  2. **29 `SPEC-04 §4` family F–H columns computed by `hr_pay_rules.py` are discarded instead of written to `PY_CLUSTER_EXP.csv` (`gen_22_hr_payroll.py:182-199`):** `PY_CLUSTER_EXP.csv` only writes 21 columns and drops `caf_conveyance_inr`, `caf_children_edu_inr`, `caf_professional_dev_inr`, `caf_other_perks_inr`, `hardship_offshore_inr`, `field_duty_allowance_inr`, `location_comp_allowance_inr`, `hard_station_allowance_inr`, `shift_allowance_inr`, `night_duty_allowance_inr`, `npa_inr`, `special_allowance_inr`, `prp_paid_inr`, `leave_encashment_paid_inr`, `ltc_inr`, `medical_reimbursement_inr`, `ex_gratia_other_inr`, `employee_pf_inr`, `vpf_inr`, `professional_tax_inr`, `hrr_recovery_inr`, `loan_recoveries_inr`, `other_recoveries_inr`, `capitalised_share`, `cost_capitalised_inr`, `cost_expensed_inr`, `cost_expensed_gae_inr`, `cost_expensed_exploration_inr`, and `field_id`.
  3. **Workman overtime hours are hardcoded constants (`gen_22_hr_payroll.py:87`):** `ot_base = 54.0 if r_regime == "OFFSHORE_14_14" else (36.0 if r_regime == "FIELD_SHIFT_28_28" else 3.0)` instead of drawing from a zero-inflated gamma distribution (`P(ot_hours = 0) ≈ 0.55`, mean of positives `≈ 18 h/month`, `p99 ≤ 75 h`, executive/supervisory `= 0`) as required by `SPEC-04 §6.5` and `Packet §5.3 item 7`.
  4. **`tests/test_22_hr_sat.py` weakened (`lines 222-251, 347-357`):** `test_cafeteria_cap` was relaxed to allow `50.01%` in FY17 (`assert ratio <= 0.5001` on line 354 instead of `0.3501` across all FYs), and `test_note35_reconciliation` only sums `payroll + pool` without asserting `EMP-R08` (`|residual| ≤ 3%`) or `EMP-R09` (`individual (a) within ± 4% before residual`).
- **Required Fix:**
  - Persist all `SPEC-04 §4` family F–H pay, deduction, and cost-bridge columns in `PY_CLUSTER_EXP.csv`.
  - Implement `SPEC-04 §7.1 step 7` (`EMP-R29`) so `Σ cost_expensed_production_inr` reconciles to Note 35 Staff Expenditure within `± ₹10 L` for every FY (`FY17`–`FY26`).
  - Use the zero-inflated gamma overtime distribution (`SPEC-04 §6.5`) and enforce the 35% cafeteria cap (`ratio <= 0.3501`) across all FYs including FY17.

---

## Verification Evidence Executed

- `pytest -v tests/test_21_hr_core.py tests/test_22_hr_sat.py tests/test_60_employee360_recon.py` in `data_bank`: 44 passed (passes only because `test_60_employee360_recon.py` omits `EMP-R08`, `EMP-R09`, `EMP-R15`, `EMP-R24`, `EMP-R29` checks on the landed CSVs and `test_22_hr_sat.py` was relaxed).
- `grep -cn "EMP-102451" ../yukti/backend/certified/library.yaml`: `0` (verified).
- Direct inspection of landed CSVs in `data_bank/landing/sap/`:
  - `PA0002_PA0001.csv`: `52,658` rows (`25,729` active); `E0` count = `0`; `E1` active median tenure = `17.80 yrs`; `age_band_brsr` has `'30-40'` (`17,255`) and `'40-50'` (`8`).
  - `PY_CLUSTER_EXP.csv`: `3,581,220` rows; `cost_expensed_production_inr` sum = `0.0` in every FY; `arrears_inr` non-zero in FY17 (`₹1,610.61 cr`), FY21 (`₹0.32 cr`), FY22 (`₹1,161.65 cr`), FY23 (`₹635.65 cr`), FY24 (`₹59.48 cr`), FY25 (`₹37.49 cr`), FY26 (`₹202.89 cr`).
  - `employee_cost_pool.csv`: `60` rows; `month_start = "FY26-03-01"` in all 60 rows; FY26 `|POOL_RESIDUAL_A + POOL_RESIDUAL_B| = ₹306.36 cr = 3.00037%` of AR total (`₹10,210.71 cr`).
