# Task Packet: `P2H.5` Employee-360 synthetic generator regeneration (realistic + calibrated)

**Executor:** O (Opus) — calibration logic; may hand unit-test writing to F · **Author:** O (v3 docs) · **Date:** 2026-10-23
**Branch:** `v3/P2H-hr` · **Base SHA:** tip of `wip/pre-v3-snapshot` · **Max files changed:** 12 · **Budget:** ~120 tool calls; stop after 2 failed self-checks · **Features:** FEAT-021 · **Spec:** [SPEC-04](../../../specs/SPEC-04_employee_360.md) §5–§7 · **Behaviour:** [BEH-06](../../../behaviour/BEH-06_employee_cost_analytics.md) · **Checklist:** row `P2H.5`
**App root (quote it, the path has spaces and `&`):** `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC`
**Depends on:** P1 real-targets export (if not ready, use the transcribed targets file in §5.1 with `verified=FALSE`) · **Blocks:** P2H.6, P2H.7, P2H.1 re-seed

## 1. Goal (one sentence)
Regenerate the HR landing CSVs so every employee-month carries realistic, rule-based pay and benefits (SPEC-04 §4 families A–N), on a realistic career pyramid with diverse names, and so the population and cost reconcile to the real AR/BRSR targets in SPEC-04 §7.4.

## 2. Context you need (read these first, nothing else)
- `docs/specs/SPEC-04_employee_360.md`: the whole spec; §5 rules, §6 realism, §7 calibration are normative.
- `data_bank/generators/hr/gen_21_hr_core.py`: employee master, postings, promotions, separations (names at :302-330, age band at :280-288).
- `data_bank/generators/hr/gen_22_hr_sat.py`: payroll H8 (:279-487), leave H13 (:986), medical H14 (:1058), training (:832), parameters (:60-125).
- `data_bank/world_bible/reference/grades.yaml`, `work_centres.yaml`, `fields.yaml`, `disciplines.yaml`, `geography.yaml`, `time_window.yaml`.
- `data_bank/GENERATOR_PATTERN_BRIEF.md`, `data_bank/tests/test_21_hr_core.py`, `test_22_hr_sat.py`, `test_no_entity_forcing.py`.
- Real sources (read-only): `knowledge/public_sources/grounding_data/text/ONGC_AR_FY2025-26.txt` lines 1050-1051, 24238-24245, 24210, 4300-4314, 4466-4475, 4493, 9150-9210, 11585-11592; `ONGC_AR_FY2021-22.txt`…`FY2024-25.txt` Note "Employee Benefit Expenses" blocks; `knowledge/public_sources/policies/text/dpe_om_03aug2017_3rd_prc_pay_revision_executives.txt`, `dpe_om_03oct2018_ida_revised_rates_2017_scales.txt`, `dpe_guidelines_compendium_admin_ministries_cpses.txt:18960-19075`, `ongc_recruitment_advt_1_2024_GT.txt`.

## 3. Files you may change / create
1. `data_bank/generators/hr/gen_21_hr_core.py`: pyramid, entry modes, DOB/DOJ consistency, names, functional designations, departments, transfer reasons/exemptions, E0 cadre, BRSR age bands, placeholder names fixed.
2. `data_bank/generators/hr/gen_22_hr_sat.py`: pay engine (scale + increments + fitment + IDA + HRA + allowances + PRP + arrears), employer benefits, deductions, leave fix, medical with dependants, cost destinations, policy-knob fitting, cost pools.
3. `data_bank/generators/hr/pay_rules.py` (new): pure functions for §5–§6 (unit-testable).
4. `data_bank/world_bible/reference/ida_rates.yaml` (new): SPEC-04 §5.2 rows with `status` real/illustrative and `source_doc`.
5. `data_bank/world_bible/reference/hra_rates.yaml` (new): §5.3.
6. `data_bank/world_bible/reference/allowance_rules.yaml` (new): §5.4.
7. `data_bank/world_bible/reference/name_pools.yaml` (new): surnames by state (≥ 25 states × ≥ 20), first names by gender (≥ 400 each).
8. `data_bank/world_bible/reference/real_targets/employee_targets_fy.csv` (new): see §5.1.
9. `data_bank/tests/test_21_hr_core.py`, `data_bank/tests/test_22_hr_sat.py`: extend.
10. `data_bank/tests/test_60_employee360_recon.py` (new): offline EMP-R checks (shared with P2H.8; create the skeleton here).
11. `data_bank/tests/landing_baseline_manifest.sha256`: regenerate **only** via the existing manifest script, after tests pass.

## 4. Do NOT touch
- `yukti/` (any file), Dataform definitions (P2H.6), `financial_build/`, other generators (`ops/`, `finance/`, `documents/`), world-bible files not listed.
- **No** `git commit` / `push` / `reset` / `checkout` / `stash`, no deploys, no `bq` writes, no destructive commands. Leave changes uncommitted.
- Do not invent "real" values: anything not in a cited local file gets `status: illustrative`.

## 5. Exact requirements
### 5.1 Real targets file (`employee_targets_fy.csv`)
Columns: `fiscal_year, metric, value, unit, source_doc, source_page, source_text_line, verified`.
- `employee_cost_total` FY17–FY26 (₹ mn) and `headcount_fy_end` FY16–FY26 from the AR26 10-yr table (lines 1050-1051) and AR22 (FY16 = 33,927). **Latest AR wins** (FY25 = 107,205 / 24,368, not AR25's 107,130 / 24,378).
- Note 35.1 lines a–f FY21–FY26 from AR22–AR26 (current-year column of each AR; for FY25 use the AR26 comparative). Assert Σ a..f = subtotal for each FY.
- `staff_expenditure_note35` FY21–FY26 (Note 35 "Staff Expenditure").
- BRSR FY26: exec/non-exec 13,781/9,336; women 1,377/508; PwD 313/210; age bands 2,300/15,834/5,859 (base 23,993); medians 4,330,341/3,754,822/2,196,587/1,901,919; turnover 7.4/3.1 %; hires 167, <30 86.23 %, women 16.77 %; training 12.12 h; women wage share 7.73 %. Add FY22–FY25 BRSR rows where the same tables exist in the AR texts.
- `verified=FALSE` until P1's `fact_financial_statement_line` cross-check sets it TRUE.

### 5.2 Population
1. FY-end headcount per FY = target **exactly**. Exec/non-exec, women, PwD, SC/ST, age bands within SPEC-04 §7.4 tolerances (iterative proportional fitting on gender × cadre × category × age band).
2. Career pyramid per SPEC-04 §6.1. ≥ 95 % of direct-entry executives inside their service band. E1 median service ≤ 4 yrs. Promotees ≤ 12 % of E0–E2. Grade counts are outputs (do not force today's grade counts).
3. Recruitment per FY = Δheadcount + separations; FY26 hires = 167 (86.23 % < 30, 16.77 % women). Separations by type per BRSR turnover; superannuation at 60 is deterministic.
4. Names: ≥ 15,000 distinct full names; ≤ 3 identical full names per WC; EMP-000001..3 get realistic names; EMP-102451 stays "Pooja Verma"; keep ≥ 1 "Rajesh Kulkarni" in Delhi `DISC-FIN` E3 (SPEC-06 seeding).
5. Delhi active = 943 ± 5 %; Delhi E1–E4 pools in HR and Finance each ≥ 8 (persona seeding).
6. Postings: `transfer_reason`, `requested_flag`, `jrtp_clause`; exemptions 3–5 % of the overdue cohort with `valid_until`.

### 5.3 Pay & cost (per employee-month; Apr-2016 → `time_window.current_month`)
1. Implement SPEC-04 §6.4 exactly (2007 scales to Dec-2016; fitment ×1.15 on 1-Jan-2017; 3 % increments each July; promotion fixation; arrears in an illustrative month).
2. IDA from `ida_rates.yaml`; HRA from class × IDA band; cafeteria ≤ 35 % BP; hardship ≤ 12 % BP on offshore days only; LCA per zone; superannuation ≤ 30 % of BP+DA (cap PRBS to fit); gratuity ceiling per §5.4.
3. Emit every money column in SPEC-04 §4 families F, G, H, I with the same names (`*_inr`), plus `cost_note35_a..f_inr`, `capitalised_share`, `cost_expensed_production_inr`, etc.
4. Fit FY knobs (`k_fy`, `u_fy`, `ot_fy`, arrears month) within bounds; write `data_bank/landing/sap/payroll_policy_fy.csv`.
5. Allocate lines c/d/e/f and compute pools (SPEC-04 §7.1 steps 5–6); write `data_bank/landing/sap/employee_cost_pool.csv` (schema SPEC-04 §7.2).
6. Scale only the production-share destination keys so Σ `cost_expensed_production_inr` = `staff_expenditure_note35` (FY21+).
7. **Never** multiply an individual's pay by a calibration factor.

### 5.4 Outputs (landing)
- `landing/sap/PA0002_PA0001.csv`, `PA0001.csv`, `PA0000_promotions.csv`, `PA0000_separations.csv`: regenerated, with new columns appended (keep existing column names).
- `landing/sap/PY_CLUSTER_EXP.csv`: regenerated, all SPEC-04 money columns; one row per employee-month on roll.
- `landing/sap/PA2001_PA2006.csv`: leave types `Earned_Leave_EL` / `Half_Pay_Leave_HPL` / `Casual_Leave_CL` kept; FY-aligned rows.
- New: `landing/sap/payroll_policy_fy.csv`, `landing/sap/employee_cost_pool.csv`.

## 6. Examples / reference patterns
```
E1 direct entrant, DOJ 2025-07-01, WC-DEL (X), IDA 49.0 % (Apr-2025, illustrative), HRA band 25–50 % → 27 %:
basic 60000.00; ida 29400.00; hra 16200.00; cafeteria 21000.00 (u=1.0); gross 126600.00
employer_cpf = 0.12 × 89400 = 10728.00; superannuation_pct_bp_da ≤ 0.30
July-2026 increment: basic = roundup_10(60000 × 1.03) = 61800.00
```

## 7. Acceptance criteria (copied into the review)
- [ ] EMP-R01 (with pools) and EMP-R10 exact for FY17–FY26; EMP-R02..R07 exact FY21–FY26 (offline, from landing CSVs).
- [ ] EMP-R08 residual ≤ 3.0 %; EMP-R09 modelled (a) within ± 4 % of AR (a) for FY21–FY26.
- [ ] EMP-R11..R18, R22..R26, R28, R29 PASS for FY26 (and for FY22–FY25 where BRSR rows exist).
- [ ] E1 median service ≤ 4.0 yrs; distinct names ≥ 15,000; 0 rows violating caps (superannuation, cafeteria, HRA, scale).
- [ ] Deterministic: two runs with the same seed give identical SHA-256 for every output CSV.
- [ ] `PY_CLUSTER_EXP.csv` rows within ± 3 % of Σ monthly headcount (≈ 3.6 M); runtime ≤ 30 min on cloudtop.
- [ ] All existing `data_bank/tests` still pass, except baseline-hash tests, which are updated via the manifest script.

## 8. Self-check commands (run before reporting)
```bash
cd "<app root>/data_bank" && uv run python generators/hr/gen_21_hr_core.py && uv run python generators/hr/gen_22_hr_sat.py
cd "<app root>/data_bank" && uv run pytest -q tests/test_21_hr_core.py tests/test_22_hr_sat.py tests/test_60_employee360_recon.py tests/test_no_entity_forcing.py
cd "<app root>" && git status --short
```

## 9. Stop-and-ask triggers
- Targets are infeasible within knob bounds (e.g. EMP-R09 > 4 %). Report the gap; do **not** widen bounds or scale pay.
- Downstream generators (`gen_23_ops.py`, `gen_24_fin.py`, documents) break on changed columns.
- A real value is needed that is not in a local file (e.g. IDA quarter): leave it illustrative and list it.
- A self-check fails twice.

## 10. Report format
- **Files changed** (1 line each) · **Self-check output** · **Acceptance** ✅/❌ with numbers (a table of EMP-R checks for FY26 and the worst FY) · **Knob values per FY** · **Illustrative values still open** · **Open questions / deviations**
