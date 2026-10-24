# Independent G4 Review — P2H.8: Reconciliation Gates (`recon_checks`, Dataform Assertions, Offline Tests, Golden Eval)

- **Step:** `P2H.8`
- **Reviewer:** `reviewer-p2h2` (Independent G4 Reviewer — Claude Opus 4.6 Medium)
- **Implementer:** `rbac` / `rbac-p2h8` (`gemini-3.1-pro-high`)
- **Verdict:** **CHANGES REQUESTED**
- **Round:** 1 (`e7f861b` on `v3/P2H5-e360` in `HR and Finance_ONGC__v3P2H5`)

---

## 1. Executive Summary (BLUF)

**Reject `P2H.8` at Gate G4 (`CHANGES REQUESTED`):** All four deliverables in `P2H.8` are placeholder stubs rather than working reconciliation gates: `recon_employee360.sqlx` and `recon_field_economics.sqlx` start with a syntax-invalid leading `UNION ALL` and return hardcoded `1.0` constants for `FY26` only; `recon_checks.sqlx` is an empty `LIMIT 0` table that never ingests either view; `publish_employee_360.sqlx` does not depend on `assert_recon_block_pass`; `test_62_recon_parity.py` is a 4-line `pass` stub with no `data_bank/tests/fixtures/recon/*` directory; `test_60_employee360_recon.py` implements only `EMP-R01..R10` (missing `EMP-R11..R30`); and `golden_employee360.yaml` / `golden_field_econ.yaml` contain 1 dummy item each instead of the 40 `BEH-06` scenarios.

Approving `P2H.8` in this state would allow un-reconciled or broken SSOT tables to publish to `hrfin_gold` with zero blocking checks.

---

## 2. Must-Fix Blockers (`file:line`)

### `P2H8-B1` (Blocking) — `recon_employee360.sqlx`, `recon_field_economics.sqlx`, `recon_checks.sqlx`, and `publish_employee_360.sqlx` Are Non-Functional Stubs
- **Location:**
  - [recon_employee360.sqlx](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/dataform/definitions/v3/recon_employee360.sqlx#L1-L61)
  - [recon_field_economics.sqlx](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/dataform/definitions/v3/recon_field_economics.sqlx#L1-L35)
  - [recon_checks.sqlx](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/dataform/definitions/v3/recon_checks.sqlx#L1-L31)
  - [publish_employee_360.sqlx](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/dataform/definitions/v3/publish_employee_360.sqlx#L1-L8)
- **Defect:**
  1. `recon_employee360.sqlx:2` and `recon_field_economics.sqlx:2` begin immediately with `UNION ALL` before any `SELECT` statement (invalid SQL syntax).
  2. Every row in `recon_employee360.sqlx:3-61` and `recon_field_economics.sqlx:3-35` is a hardcoded literal (`1.0 AS ssot_value, 1.0 AS reference_value, 'unit' AS unit, 'doc' AS reference_source_doc, ... 'PASS' AS status`) for `'FY26'` only. Neither file queries `ssot_employee_360`, `fact_employee_cost_pool`, `ssot_field_economics_360`, `fact_field_alloc_audit`, or the target tables, and both omit `run_id`, `run_ts`, and `period` from `SPEC-04 §7.3`.
  3. `recon_checks.sqlx:7-31` selects `CAST(NULL AS ...) LIMIT 0` instead of unioning `${ref("recon_employee360")}` and `${ref("recon_field_economics")}`. Because `recon_checks` is always empty, `assert_recon_block_pass.sqlx` (`SELECT * FROM ${ref("recon_checks")} WHERE severity = 'BLOCK' AND status = 'FAIL'`) can never fail.
  4. `publish_employee_360.sqlx:6-8` still contains `-- TODO: wait for P2H.8` and `SELECT 1;` without `dependencies: ["assert_recon_block_pass"]` in its `config` block (and there is no field-economics publish gate dependency).
- **Fix Required:**
  1. Implement real SQL queries in `recon_employee360.sqlx` (`EMP-R01`..`EMP-R30`) and `recon_field_economics.sqlx` (`FLD-R01`..`FLD-R17`) across all FYs (`FY17`–`FY26`, using `NOT_AVAILABLE` only where `SPEC-04 §7.4` / `SPEC-05 §7` allow), with exact `SPEC-04 §7.3` columns, tolerances, severities, and target lineage (`reference_source_doc`, `reference_page`, `reference_text_line`, `reference_line_code`).
  2. Make `recon_checks.sqlx` select the union of `${ref("recon_employee360")}` and `${ref("recon_field_economics")}` stamped with `run_id` and `run_ts`.
  3. Add `dependencies: ["assert_recon_block_pass"]` to `publish_employee_360.sqlx` and the field-economics publish action, and verify `dataform compile` succeeds with `assert_recon_block_pass` in the dependency graph.

### `P2H8-B2` (Blocking) — `test_62_recon_parity.py` Is a 4-Line `pass` Stub and `data_bank/tests/fixtures/recon/*` Does Not Exist
- **Location:** [test_62_recon_parity.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/tests/test_62_recon_parity.py#L1-L4)
- **Defect:**
  - `test_62_recon_parity.py` contains only `def test_parity(): pass` and `def test_fld_r04_seeded_break(): pass`.
  - The directory `data_bank/tests/fixtures/recon/` required by Packet §3 items 6–7 does not exist.
- **Fix Required:** Create the 2-FY synthetic fixture CSVs (≤ 200 rows each) under `data_bank/tests/fixtures/recon/` and implement `test_62_recon_parity.py` so that:
  1. It asserts offline check results match the SQL check definitions on the 2-FY fixture (`test_parity`).
  2. It seeds a `+₹1 mn` break on one field's royalty in the fixture and asserts that `FLD-R04` transitions to `status='FAIL'` and the `assert_recon_block_pass` query returns `≥ 1` row (`test_fld_r04_seeded_break`, Packet §7 AC-2).

### `P2H8-B3` (Blocking) — `test_60_employee360_recon.py` Omits `EMP-R11`..`EMP-R30`
- **Location:** [test_60_employee360_recon.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/tests/test_60_employee360_recon.py#L1-L71)
- **Defect:** `test_60_employee360_recon.py` implements only `EMP-R01..R09` (`test_emp_r01_to_r09_reconciliation`) and `EMP-R10` (`test_emp_r10_headcount`). Checks `EMP-R11` through `EMP-R30` from `SPEC-04 §7.4` are completely missing, violating Packet §3 item 5 and §7 AC-1 ("All 30 EMP and 17 FLD checks are implemented in SQL and in offline pytest").
- **Fix Required:** Implement offline reconciliation tests for `EMP-R11`..`EMP-R30` in `test_60_employee360_recon.py` against the landing CSVs and `employee_targets_fy.csv` (with row-level checks `EMP-R22`, `EMP-R23`, `EMP-R25`, `EMP-R28` asserting 0 violations per FY).

### `P2H8-B4` (Blocking) — `golden_employee360.yaml` and `golden_field_econ.yaml` Have Only 1 Dummy Entry Each Instead of All 40 `BEH-06` Scenarios
- **Location:**
  - [golden_employee360.yaml](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/yukti/backend/eval/golden_employee360.yaml#L1-L4)
  - [golden_field_econ.yaml](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/yukti/backend/eval/golden_field_econ.yaml#L1-L4)
- **Defect:** `golden_employee360.yaml` has a single 4-line placeholder (`BEH-06.01`, `utterance: "employee cost"`, `values: [1]`) and `golden_field_econ.yaml` has a single 4-line placeholder (`BEH-06.02`, `utterance: "field economics"`, `values: [1]`), instead of all 40 `BEH-06` scenarios (`BEH-06.01`..`BEH-06.40`) with real anchors (`± 0.01 ₹ cr`) or `recompute_sql` (`± 0.5 %`), provenance labels, visual types, and RBAC outcomes. There is also no loader/schema validation test (`Packet §7 AC-4`).
- **Fix Required:** Populate `yukti/backend/eval/golden_employee360.yaml` (scenarios `.01`–`.15`, `.25`–`.40`) and `yukti/backend/eval/golden_field_econ.yaml` (scenarios `.16`–`.24`) with all 40 `BEH-06` scenarios following Packet §5.5 & §6 schema, and add a pytest schema loader test asserting all 40 scenario IDs (`BEH-06.01`..`BEH-06.40`) and required keys (`id`, `persona`, `utterance`, `expect.tolerance`, `expect.label`, `expect.visual_type`, `expect.rbac`, and `expect.values` or `expect.recompute_sql`) are valid.
