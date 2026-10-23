# Task Packet: `P2H.8` Reconciliation gates: `recon_checks`, Dataform assertions, offline tests, golden eval

**Executor:** `O→F` — **O** authors the reconciliation rules and SQL (files 1–4: `recon_checks.sqlx`, `recon_employee360.sqlx`, `recon_field_economics.sqlx`, `assert_recon_block_pass.sqlx`; DELEGATION v3: reconciliation logic is O-only); **F** (`flash`) implements the tests (files 5–8: offline parity tests, fixtures, golden YAML) against O's SQL · **Author:** O (v3 docs) · **Date:** 2026-10-23
**Branch:** `v3/P2H-hr` · **Base SHA:** after P2H.7 approved · **Max files changed:** 10 · **Budget:** ~70 tool calls; stop after 2 failed self-checks · **Features:** FEAT-021, FEAT-022, FEAT-030 (numeric golden eval) · **Specs:** [SPEC-04](../../../specs/SPEC-04_employee_360.md) §7.3–7.4, [SPEC-05](../../../specs/SPEC-05_field_economics_reconciliation.md) §7 · **Behaviour:** [BEH-06](../../../behaviour/BEH-06_employee_cost_analytics.md) (test mapping table) · **Checklist:** row `P2H.8`
**App root (quote it):** `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC`

## 1. Goal (one sentence)
Make the reconciliation **block publication**: every EMP-R and FLD-R check writes a row to `hrfin_gold.recon_checks`, a Dataform assertion fails on any `BLOCK` failure, and offline pytest plus a golden numeric eval reproduce the same checks and the BEH-06 numbers.

## 2. Context you need (read these first, nothing else)
- SPEC-04 §7.3 (`recon_checks` schema) and §7.4 (EMP-R01…R30); SPEC-05 §7 (FLD-R01…R17).
- `data_bank/world_bible/reference/real_targets/employee_targets_fy.csv`, `field_econ_targets_fy.csv` (from P2H.5/P2H.7).
- `data_bank/medallion/dataform/definitions/v3/*` (P2H.6/P2H.7), `definitions/assertions/gold_calibration_reconciliation.sqlx` (existing ± 2 % pattern; to be superseded).
- `data_bank/tests/test_60_employee360_recon.py` skeleton (P2H.5), `test_61_field_alloc.py` (P2H.7).
- `docs/behaviour/BEH-06_employee_cost_analytics.md`: golden values in the scenarios and the conventions block.
- `yukti/backend/eval/` (existing gate JSON format, e.g. `eval/gates/B3.json`).

## 3. Files you may change / create
**Owner split:** files 1–4 = **O** (rules/SQL; F must not edit them, only read them); files 5–8 = **F** (tests). F starts after O's SQL compiles (`dataform compile` green).

1. `data_bank/medallion/dataform/definitions/v3/recon_checks.sqlx`: `type: "incremental"`, schema `hrfin_gold`, one row per check × FY × level × key per run (`run_id` = Dataform run id or `GENERATE_UUID()` stamped once per run).
2. `data_bank/medallion/dataform/definitions/v3/recon_employee360.sqlx`: computes EMP-R01…R30 from `hrfin_stage.ssot_employee_360` + pools + `int_fe_targets_fy`/employee targets.
3. `data_bank/medallion/dataform/definitions/v3/recon_field_economics.sqlx`: FLD-R01…R17.
4. `data_bank/medallion/dataform/definitions/v3/assert_recon_block_pass.sqlx`: `type: "assertion"`; returns rows where `severity='BLOCK' AND status='FAIL'` for the current `run_id`; publish actions depend on it (replace the P2H.6 stub).
5. `data_bank/tests/test_60_employee360_recon.py`: complete (offline from landing CSVs).
6. `data_bank/tests/test_62_recon_parity.py` (new): asserts offline check results = the SQL logic expectations on a 2-FY fixture (small synthetic fixture under `data_bank/tests/fixtures/recon/`).
7. `data_bank/tests/fixtures/recon/*` (new; small CSVs ≤ 200 rows each).
8. `yukti/backend/eval/golden_employee360.yaml`, `yukti/backend/eval/golden_field_econ.yaml` (new): BEH-06 questions + expected values/labels/visual/RBAC per persona.

## 4. Do NOT touch
- Generators (P2H.5/P2H.7), SSOT SQL logic other than adding dependencies, `yukti` Python code, RBAC policy.
- **No** `git commit/push/reset/checkout/stash`; no deploys; no BigQuery writes (`dataform compile` only; O runs the pipeline).

## 5. Exact requirements
1. `recon_checks` columns exactly as SPEC-04 §7.3; `reference_*` lineage copied from the targets row; `delta = ssot − reference`; `delta_pct = delta / NULLIF(reference,0)`.
2. Tolerances and severities exactly as in the registers (SPEC-04 §7.4, SPEC-05 §7). `NOT_AVAILABLE` only where the registers allow (FY17–FY20 line/segment checks; BRSR before FY22).
3. Row-level checks (EMP-R22/R23/R25/R28, FLD-R14/R15) write one summary row per FY with `ssot_value` = violation count and `reference_value` = 0.
4. The assertion must make `publish_employee_360` and the field-economics publish fail when any `BLOCK` row fails for a closed FY.
5. Golden YAML: each item = `{id: BEH-06.nn, persona, utterance, expect: {values: [...], tolerance, label, visual_type, rbac}}`. Real anchors use ± 0.01 ₹ cr; synthetic items use `recompute_sql` + ± 0.5 %.
6. Offline tests must not need network or BigQuery.

## 6. Examples / reference patterns
```sql
-- EMP-R01 (sketch)
SELECT 'EMP-R01' check_id, 'SPEC-04' spec, t.fiscal_year, 'company' level, NULL dimension_key,
       'employee_cost_total_inr_mn' metric,
       ROUND((e.cost + p.pool)/1e6, 2) ssot_value, t.value reference_value, 'INR_mn' unit,
       t.source_doc reference_source_doc, t.source_page reference_page, t.source_text_line reference_text_line,
       ROUND((e.cost + p.pool)/1e6 - t.value, 2) delta, 0.1 tolerance_abs, 'BLOCK' severity,
       IF(ABS((e.cost + p.pool)/1e6 - t.value) <= 0.1, 'PASS', 'FAIL') status
FROM targets t JOIN emp_fy e USING (fiscal_year) JOIN pool_fy p USING (fiscal_year)
WHERE t.metric = 'employee_cost_total'
```
```yaml
- id: BEH-06.07
  persona: CMD
  utterance: "Show revenue per employee trend for the last 10 years."
  expect: {values: {FY17: 2.305, FY26: 5.581}, unit: inr_cr, tolerance: 0.001, label: "Derived from AR", visual_type: line, rbac: allow}
```

## 7. Acceptance criteria
- [ ] All 30 EMP and 17 FLD checks are implemented in SQL and in offline pytest; the parity test passes on the fixture.
- [ ] A seeded break (e.g. +₹1 mn on one field's royalty in the fixture) makes FLD-R04 FAIL and the assertion return ≥ 1 row.
- [ ] `dataform compile` OK; the publish actions depend on `assert_recon_block_pass` in the compiled graph.
- [ ] Golden YAMLs contain all 40 BEH-06 scenarios; schema validated by a small loader test.
- [ ] `uv run pytest -q tests/test_60_employee360_recon.py tests/test_61_field_alloc.py tests/test_62_recon_parity.py` green on the real landing data (FY21–FY26 BLOCK checks PASS).

## 8. Self-check commands
```bash
cd "<app root>/data_bank" && uv run pytest -q tests/test_60_employee360_recon.py tests/test_61_field_alloc.py tests/test_62_recon_parity.py
cd "<app root>/data_bank" && uv run python medallion/generate_dataform_project.py && cd medallion/dataform && dataform compile
cd "<app root>" && git status --short
```

## 9. Stop-and-ask triggers
- A BLOCK check fails on the real landing data (report it; do **not** loosen the tolerance; route back to P2H.5/P2H.7).
- Spec registers are ambiguous about a tolerance or the FY availability.
- A self-check fails twice.

## 10. Report format
- **Files changed** · **Self-check output** · **Acceptance** ✅/❌ · **FY26 recon table** (check_id, ssot, reference, delta, status) · **Open questions**
