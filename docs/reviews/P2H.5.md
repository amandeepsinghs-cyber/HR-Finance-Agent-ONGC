# P2H.5 Review — Employee 360 Data Generators (`gen_21_hr_core.py`, `gen_22_hr_payroll.py`, `gen_22_hr_sat.py`)

- **Step:** P2H.5
- **Reviewer:** reviewer-p16 (Claude Opus 4.6 Medium, Role R)
- **Implementer:** gemini-3.1-pro-high + p2h5-fix + coordinator (`984e449` on branch `v3/P2H5-e360`)
- **Verdict:** APPROVE
- **Round:** 2

## Round-2 Verdict: `APPROVE` (`984e449`)

**`P2H.5` is `APPROVE` at commit `984e449`. All three Round-1 blocking defects (`P2H5-B1` through `P2H5-B3`) have been resolved and independently verified against the regenerated landing CSVs and the `data_bank` pytest suite (`49 passed in 61.13s`).**

### Round-2 Verification Summary

1. **`P2H5-B1` — RESOLVED (`gen_22_hr_payroll.py:20-58, 230-450`, `employee_cost_pool.csv`, `payroll_policy_fy.csv`):**
   - **No artificial arrears plugs outside `FY18/FY19`:** Verified directly on `landing/sap/PY_CLUSTER_EXP.csv` that `arrears_inr = 0.00` in `FY17` and `FY20`–`FY27`, and is populated only for 3rd-PRC arrears in `FY18` (`₹777.88 cr`, `2018-03`) and `FY19` (`₹497.11 cr`, `2019-03`).
   - **No per-person median remuneration plug:** Removed the top-half `arrears_inr` injection; instead, position-in-scale `u_pos` by tenure/cadre/gender (`gen_22_hr_payroll.py:36-56`) naturally calibrates FY26 median remuneration within `1.40%` (`≤ 2.0%`) of BRSR targets (`37.03 L` vs `37.55 L` exec M `-1.40%`, `37.54 L` vs `37.55 L` exec F `-0.02%`, `21.87 L` vs `21.97 L` non-exec M `-0.47%`, `18.91 L` vs `19.02 L` non-exec F `-0.59%`, `EMP-R16`).
   - **`EMP-R08` & `EMP-R09` satisfied:** Natural individual Note 34/35.1 line `(a)` before residual is within `± 2.27%` (`≤ 4.0%`) across all 10 FYs (`+0.22%` in FY26: `₹7,622.06 cr` vs `₹7,605.51 cr`), and `|POOL_RESIDUAL_A + POOL_RESIDUAL_B| / Total_Employee_Cost ≤ 2.25%` (`≤ 3.0%`, `1.64%` in FY26).
   - **Valid `month_start` and policy schema:** `employee_cost_pool.csv` now uses valid ISO dates (`2017-03-01` .. `2026-03-01`), and `payroll_policy_fy.csv` includes all 16 required columns (`fiscal_year, da_q1_pct, da_q2_pct, da_q3_pct, da_q4_pct, da_fy_avg_pct, prp_pool_factor, Increment_rate_pct, arrears_factor, arrears_month, prbs_rate_pct, u_fy, k_fy, ot_fy, residual_pool_pct, notes`).
2. **`P2H5-B2` — RESOLVED (`gen_21_hr_core.py:924-957, 1029-1115`, `PA0002_PA0001.csv`):**
   - **Tenure-coupled career pyramid (`EMP-R24` / `BUG-33`):** Verified on active rows of `PA0002_PA0001.csv` (`22,845` active): `E0` is populated (`467` active rows, `601` total rows, `Departmental_Promotee`, median tenure `36.20 yrs`), `E1` (`878` active rows) has median `total_tenure_years = 2.60 yrs ≤ 4.0 yrs`, and median tenure strictly increases across `E1` (`2.60`) < `E2` (`6.90`) < `E3` (`13.70`) < `E4` (`20.20`) < `E5` (`25.80`) < `E6` (`30.10`) < `E7` (`33.10`) < `E8` (`34.70`) < `E9` (`35.10`).
   - **`age_band` (`BUG-30`):** `PA0002_PA0001.csv` contains only `'<30'` (`2,795`), `'30-50'` (`17,607`), and `'>50'` (`21,769`), with zero `'30-40'` or `'40-50'` rows.
3. **`P2H5-B3` — RESOLVED (`gen_22_hr_payroll.py:97-191, 342-357`, `PY_CLUSTER_EXP.csv`, `test_22_hr_sat.py`):**
   - `PY_CLUSTER_EXP.csv` emits all 83 columns including all 29 `SPEC-04 §4` family F–H pay, deduction, and cost-bridge columns.
   - `cost_expensed_production_inr` reconciles to Note 35 Staff Expenditure across `FY17`–`FY26` (`₹2,652.12 cr` in FY26, `EMP-R29` within `± ₹10 L`).
   - Workman overtime uses a zero-inflated gamma distribution (`gen_22_hr_payroll.py:97-110`, overall zero-OT share `~0.79`–`0.81`).
   - `test_cafeteria_cap` in `test_22_hr_sat.py` enforces `<= 0.3501` across all FYs, and `pytest tests/test_21_hr_core.py tests/test_22_hr_sat.py tests/test_60_employee360_recon.py tests/test_62_recon_parity.py -q` passes **`49 passed in 61.13s`**.

---

## Round-1 Review History (Resolved at `984e449`)

- **Round 1 Verdict (`e7f861b`):** `CHANGES REQUESTED` (`P2H5-B1`: per-person `arrears_inr` plugs outside `FY18/FY19` and top-half median plugs, `"FY26-03-01"` date strings in `employee_cost_pool.csv`; `P2H5-B2`: uncoupled `E1` tenure `17.80 yrs`, missing `E0` grade, `'30-40'`/`'40-50'` age bands; `P2H5-B3`: 29 missing family F–H columns in `PY_CLUSTER_EXP.csv`, zero `cost_expensed_production_inr`, hardcoded OT hours, relaxed cafeteria cap test). All resolved in Round 2 (`984e449`).
