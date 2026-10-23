# Task Packet: `P2H.7` Field Economics-360: production recalibration, RAS allocation engine, Dataform

**Executor:** O (Opus) — allocation maths; F may implement the Dataform files after the engine is approved · **Author:** O (v3 docs) · **Date:** 2026-10-23
**Branch:** `v3/P2H-hr` · **Base SHA:** after P2H.6 approved · **Max files changed:** 14 · **Budget:** ~110 tool calls; stop after 2 failed self-checks · **Features:** FEAT-022 · **Spec:** [SPEC-05](../../../specs/SPEC-05_field_economics_reconciliation.md) · **Behaviour:** [BEH-06](../../../behaviour/BEH-06_employee_cost_analytics.md) .16–.24 · **Checklist:** row `P2H.7`
**App root (quote it):** `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC`
**Depends on:** P1 `fact_financial_statement_line` with SPEC-05 §5 line codes (fallback: transcribed `field_econ_targets_fy.csv`, `verified=FALSE`), P2H.5 (employee cost by field) · **Blocks:** P2H.8

## 1. Goal (one sentence)
Produce `ssot_field_economics_360` (cost object × month), whose every FY sums **exactly** to the real standalone AR (revenue, Note 35 lines, exploration, DD&A, segment results, PBT, production by basis), using driver seeds and biproportional (RAS) fitting, with an audit trail and "Modelled" labels.

## 2. Context you need (read these first, nothing else)
- `docs/specs/SPEC-05_field_economics_reconciliation.md`: all sections; §4 schema, §5 targets, §6 algorithm, §7 gates are normative.
- `data_bank/generators/ops/gen_23_ops.py` (production_monthly, wells) and `data_bank/generators/finance/gen_24_fin.py` (CO_PA, COSP_COSS).
- `data_bank/world_bible/reference/fields.yaml` (53 fields), `work_centres.yaml`, `prices_fx.yaml`.
- `data_bank/landing/db_exports/production_monthly.csv`, `wells_drilled.csv`; P2H.5 outputs `landing/sap/PY_CLUSTER_EXP.csv` (`field_id`, `cost_expensed_production_inr`).
- AR text (read-only): `knowledge/public_sources/grounding_data/text/ONGC_AR_FY2025-26.txt` lines 953-1062 (10-yr), 3090-3100 (production), 20087-20135 (P&L), 24196-24272 (Notes 35/35.1), 24400-24425 (Note 37), 25120-25200 (Note 44); the same notes in `ONGC_AR_FY2021-22.txt` … `FY2024-25.txt` for FY21–FY24.
- `financial_build/scripts/load_and_reconcile_bq.py:145-258` (the scaling logic being retired; read only).

## 3. Files you may change / create
1. `data_bank/world_bible/reference/real_targets/field_econ_targets_fy.csv` (new): SPEC-05 §5 lines per FY with `source_doc, source_page, source_text_line, verified`.
2. `data_bank/world_bible/reference/cost_objects.yaml` (new): fields + JV + plant + exploration + HQ objects (SPEC-05 §3.1), segment, priors.
3. `data_bank/world_bible/reference/alloc_drivers.yaml` (new): nature → driver → unit-cost prior by segment/maturity (SPEC-05 §4 E); price factors (§6.2); unit conversions (7.33 bbl/t; 1,000 SCM = 1 TOE; flagged "convention, verify").
4. `data_bank/generators/ops/gen_23_ops.py`: add a `prod_basis` column; JV-share rows; scale volumes to AR by FY/basis; sales bridge to AR quantity sold (SPEC-05 §6.1).
5. `data_bank/generators/finance/alloc_field_economics.py` (new): the engine (seed → RAS segment × nature with pinned cells → object → month → largest-remainder rounding) → `landing/sap/CO_PA_v3.csv` (long: fy, month, object_id, line_code, amount_inr_mn, basis) + `landing/sap/field_alloc_audit.csv`.
6. `data_bank/generators/finance/ras.py` (new): pure RAS + largest-remainder helpers with unit tests.
7. `data_bank/tests/test_61_field_alloc.py` (new).
8. `data_bank/world_bible/schema_silver.yaml`, `medallion/bronze/bronze_tables.yaml`, `medallion/upload_manifest.csv`: register `CO_PA_v3.csv`, `field_alloc_audit.csv`.
9. `data_bank/medallion/dataform/definitions/v3/`: `int_fe_targets_fy.sqlx`, `ssot_field_economics_360.sqlx` (pivot long → wide per SPEC-05 §4; partition `month_start`; cluster `segment, object_type, object_id`), `v_field_economics_fy.sqlx`, `v_field_economics_company_bridge.sqlx`, `dim_cost_object.sqlx`, `fact_field_alloc_audit.sqlx`, compat views `mart_field_economics_v3`/`v_field_pnl_v3` (old names are switched by O after review).
10. `yukti/backend/app/brain/semantic_model.yaml`: subject `field_econ` (SPEC-05 §8 KPIs); keep `field_pnl` until cut-over.

## 4. Do NOT touch
- `financial_build/` (read only), `yukti/` Python code, SPEC-04 generator files (P2H.5), any real-source text.
- Never take a target from `financial_build/data/*.json` or `landing/governance/corporate_financial_summary.csv` (wrong; diag_A §1, diag_E bug 2).
- **No** `git commit/push/reset/checkout/stash`; no deploys; no BigQuery writes (`dataform compile` only).

## 5. Exact requirements
1. **Targets:** FY21–FY26 at Note level (2-dp ₹ mn); FY17–FY20 at 10-yr level (whole ₹ mn). Assert the P&L identity per FY in the targets file before allocating (total income − expenses = PBT; segment identity FY21+). Fail fast if not.
2. **Production:** Σ by basis = AR (FY26 crude 19.332 + 1.170 MMT; gas 19.533 + 0.434 BCM); Σ sales = AR quantity sold (18.79 MMT, 15.491 BCM, 2,468 kT VAP). Keep decline shapes (scale per FY, not per month).
3. **Revenue:** RAS on segment × product (rows = segment revenue when available; columns = product revenue); objects ∝ volume × price factor.
4. **Costs:** seeds from drivers; staff expenditure seed = Σ P2H.5 `cost_expensed_production_inr` by field (its RAS factor must be 1.000 ± 1e-9). Pinned cells: segment DD&A, write-offs, impairment (Note 44.4–44.5), staff expenditure. `CO-HQ` total = segment-note "unallocated corporate expense (net)".
5. **Rounding:** largest remainder to ₹0.01 mn at month → FY → segment → company; every published sum is exact.
6. **Labels:** `data_label` on every row; `basis` per value (`R`/`RT`/`M`/`D`).
7. **Audit:** `field_alloc_audit.csv` with seed, factor, final per FY × segment × nature; factors outside [0.5, 2.0] are listed in the report.
8. **Determinism:** fixed seed; identical outputs across runs.

## 6. Examples / reference patterns
```
FY26 identity (₹ mn): Offshore result 343,846.53 + Onshore 62,456.98 + Unallocated −25,438.33
                       + Finance −45,292.61 + Interest/Dividend 88,576.32 = PBT 424,148.89
Segment cost total s = SegRev_s + OtherIncome_s − SegResult_s;  Σ_s (incl. unallocated) = 959,197.48
RAS: X ← diag(r / X·1) X ; X ← X diag(c / 1ᵀX)   until max |row/col error| < 1e-6 ₹ mn (pinned cells excluded from scaling)
```

## 7. Acceptance criteria
- [ ] Offline FLD-R01…R15 PASS for FY21–FY26; FLD-R01/R02/R04 (10-yr level), R06, R09, R11–R14 PASS for FY17–FY20 (from `test_61_field_alloc.py`).
- [ ] Staff RAS factor = 1.000 every FY; ≥ 90 % of other factors in [0.5, 2.0]; none outside [0.33, 3.0].
- [ ] 0 negative production/revenue/opex on objects (except allowed: impairment reversals, `CO-TREASURY`).
- [ ] `dataform compile` OK; `v_field_economics_company_bridge` compiles with delta columns.
- [ ] Two runs → identical SHA-256 of `CO_PA_v3.csv`.

## 8. Self-check commands
```bash
cd "<app root>/data_bank" && uv run python generators/ops/gen_23_ops.py && uv run python generators/finance/alloc_field_economics.py
cd "<app root>/data_bank" && uv run pytest -q tests/test_61_field_alloc.py tests/test_23_ops.py tests/test_24_fin.py
cd "<app root>/data_bank" && uv run python medallion/generate_dataform_project.py && cd medallion/dataform && dataform compile
cd "<app root>" && git status --short
```

## 9. Stop-and-ask triggers
- RAS does not converge, or a factor falls outside [0.33, 3.0] (priors are wrong; do not force).
- A target line is missing for an FY where SPEC-05 says it is available.
- Segment-note identity fails in the AR text (possible extraction error; escalate to the P1 owner).
- A self-check fails twice.

## 10. Report format
- **Files changed** · **Self-check output** · **Acceptance** ✅/❌ with a FY26 bridge table (line, Σ objects, AR, delta) · **RAS factor summary** · **Open questions (SPEC-05 Q1–Q5)**
