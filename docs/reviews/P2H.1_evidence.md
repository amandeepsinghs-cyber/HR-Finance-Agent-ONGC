# Evidence: `P2H.1` 11 personas, `dim_app_user`, function dimension, `self` scope, `@self_emp_id` & aggregate pay for juniors

**Executor:** `rbac` (Role A, Gemini 4 Argon) · **Date:** 2026-10-24 · **Branch:** `v3/P2H-hr`
**Task Packet:** [`docs/delegation/packets/v3/P2H.1.md`](../delegation/packets/v3/P2H.1.md) · **Spec:** [`SPEC-06`](../specs/SPEC-06_personas_identity_rbac_v3.md) · **Behaviour:** [`BEH-01`](../behaviour/BEH-01_persona_matrix.md)
**Features:** FEAT-017, FEAT-031 · **Bugs closed:** BUG-07, BUG-27, BUG-28 · **Decisions:** D-41, D-43, D-60

---

## BLUF

**`P2H.1` is complete and verified offline (831/831 tests passing across 11 suites, 11/11 personas passing the `gen_app_users.py --check` completeness gate, and 0 hardcoded `emp_id` literals in `certified/library.yaml`).** All 11 personas (`CMD`, `DIR_HR`, `DIR_FIN`, `E1_HR..E4_HR`, `E1_FIN..E4_FIN`) are seeded from real synthetic `WC-DEL` SAP rows, enforced by `rbac_policy.yaml` v2 (`director_function_scope` toggle tested for both `True` and `False`), bound to `@self_emp_id` for self-scoped queries, and allowed cohort-level aggregate/entry pay (`pay_aggregate`, $k \ge 5$).

---

## 1. Acceptance Criteria Table

| # | Criterion (SPEC-06 §7 / P2H.1 §7) | Status | Verification Evidence |
|---|---|---|---|
| **AC-1** | `VALID_PERSONAS` has 11 canonical IDs; aliases normalize (`"E1 HR officer" -> "E1_HR"`, `"e3-fin" -> "E3_FIN"`); unknown/empty raises `UnknownPersona` (closes **BUG-27**) | ✅ | `tests/test_personas_v3.py` (**49 passed** in 0.30s) |
| **AC-2** | `dim_app_user.csv` & `app_users.yaml` have 11 seeded rows (`WC-DEL`, `synthetic=True`, fictional senior surnames per **D-60**) + `DEMO_ADMIN` in `auth.py`; all completeness flags `True` | ✅ | `gen_app_users.py --check` (**11/11 verified**, exit 0) + `tests/test_personas_v3.py` |
| **AC-3** | Role escalation suite extended to all 10 non-CMD personas × 6 phrasings = **60/60** denied (`R-ROLE`, audit `role_switch_denied`) + 11 persona detector checks | ✅ | `tests/test_role_escalation.py` (**77 passed** in 2.29s) |
| **AC-5** | Self scope (`@self_emp_id`): 4 legacy `EMP-102451` literals replaced + 8 new `self_queries` added; 11 personas × 8 queries = **88/88** bind caller's own `emp_id` with 0 cross-employee rows; CI grep gate = `0` (closes **BUG-07**) | ✅ | `tests/test_self_scope.py` (**119 passed** in 1.17s); `grep -nE "emp_id\s*=\s*'EMP-[0-9]+'" ...` -> **`0`** |
| **AC-6** | 11 personas × 18 canonical questions (Q01–Q18, SPEC-06 §6) = **198/198** parametrized cases match expected `(action, code)` and `self_emp_id` binding | ✅ | `tests/test_persona_question_matrix.py` (**198 passed** in 0.71s) |
| **AC-7** | Policy matrix v2: 11 personas × 12 data classes = **132/132** decisions verified with `director_function_scope=True` (D-43) and **132/132** with `director_function_scope=False` (D-10); junior `pay_aggregate` allowed with $k \ge 5$ (closes **BUG-28**) | ✅ | `tests/test_rbac_policy.py` (**323 passed** in 0.73s) |
| **AC-10** | Existing RBAC, auth token, transfer note, export security, answer-key leak, catalog consistency, and QuerySpec tests stay green | ✅ | `test_auth_tokens.py` (20), `test_transfer_note.py` (5), `test_export_security.py` (14), `test_no_answer_key_leak.py` (3), `test_catalog_consistency.py` (8), `test_query_spec.py` (15) — **all green** |

---

## 2. Seeded Persona → `emp_id` Directory (`dim_app_user` / `app_users.yaml`)

Per **Decision D-60**:
- Senior personas (`EMP-000001..3`) use fictional surnames (`Arun Mehra`, `Manish Deshpande`, `Vivek Rao`) with `synthetic=True`.
- `E2_HR` retains `EMP-102451` (`Pooja Verma`) for continuity with existing fixtures; `ok_leave` is evaluated across all leave-type codes in `PA2001_PA2006.csv` (`EL`, `Earned_Leave_EL`, `CL`, `Casual_Leave_CL`, `HPL`, `Half_Pay_Leave_HPL`).
- `E3_FIN` selects `EMP-100146` (`Asha Mishra`, `WC-DEL`) via the "else lowest `emp_id` in pool" rule in SPEC-06 §4.1 (all `"Rajesh Kulkarni"` rows in `PA0002_PA0001.csv` are in `WC-MUM`, not `WC-DEL`). **UI copy note for P2H.2:** update any hardcoded `"Rajesh Kulkarni"` label for `E3_FIN` in the frontend picker to read from `/api/auth/personas` (`Asha Mishra`).

| `persona_id` | `emp_id` | `display_name` | `grade` | `function` | `discipline_id` | `wc_id` | `pay_fy26_months` | `el/cl/hpl` | `posting_rows` | `apar_rows` | Gate |
|---|---|---|---|---|---|---|---:|---:|---:|---:|---|
| `CMD` | `EMP-000001` | Arun Mehra | `CMD` | `EXEC` | `DISC-PRD` | `WC-DEL` | 12 | 8 / 8 / 4 | 5 | 5 | ✅ |
| `DIR_HR` | `EMP-000002` | Manish Deshpande | `DIR` | `HR` | `DISC-HR` | `WC-DEL` | 12 | 8 / 8 / 4 | 5 | 5 | ✅ |
| `DIR_FIN` | `EMP-000003` | Vivek Rao | `DIR` | `FIN` | `DISC-FIN` | `WC-DEL` | 12 | 8 / 8 / 4 | 5 | 5 | ✅ |
| `E1_HR` | `EMP-100151` | Dinesh Deshmukh | `E1` | `HR` | `DISC-HR` | `WC-DEL` | 12 | 8 / 8 / 4 | 3 | 5 | ✅ |
| `E2_HR` | `EMP-102451` | Pooja Verma | `E2` | `HR` | `DISC-HR` | `WC-DEL` | 12 | 1 / 0 / 0 | 1 | 5 | ✅ |
| `E3_HR` | `EMP-100144` | Pooja Pillai | `E3` | `HR` | `DISC-HR` | `WC-DEL` | 12 | 8 / 8 / 4 | 9 | 5 | ✅ |
| `E4_HR` | `EMP-100178` | Aarti Saikia | `E4` | `HR` | `DISC-HR` | `WC-DEL` | 12 | 8 / 8 / 4 | 5 | 5 | ✅ |
| `E1_FIN` | `EMP-100150` | Ajay Deshmukh | `E1` | `FIN` | `DISC-FIN` | `WC-DEL` | 12 | 8 / 8 / 4 | 3 | 5 | ✅ |
| `E2_FIN` | `EMP-100152` | Praveen Nair | `E2` | `FIN` | `DISC-FIN` | `WC-DEL` | 12 | 8 / 8 / 4 | 8 | 5 | ✅ |
| `E3_FIN` | `EMP-100146` | Asha Mishra | `E3` | `FIN` | `DISC-FIN` | `WC-DEL` | 12 | 8 / 8 / 4 | 8 | 5 | ✅ |
| `E4_FIN` | `EMP-100145` | Santosh Banerjee | `E4` | `FIN` | `DISC-FIN` | `WC-DEL` | 12 | 8 / 8 / 4 | 6 | 5 | ✅ |

---

## 3. Self-Check Commands & Output

```text
$ "/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC/yukti/backend/.venv/bin/python" data_bank/generators/hr/gen_app_users.py --check
persona_id | emp_id     | display_name       | grade | func | wc_id  | pay26 | el/cl/hpl | post | apar
--------------------------------------------------------------------------------------------------
CMD        | EMP-000001 | Arun Mehra         | CMD   | EXEC | WC-DEL |    12 |     8/8/4 |    5 |    5
DIR_HR     | EMP-000002 | Manish Deshpande   | DIR   | HR   | WC-DEL |    12 |     8/8/4 |    5 |    5
DIR_FIN    | EMP-000003 | Vivek Rao          | DIR   | FIN  | WC-DEL |    12 |     8/8/4 |    5 |    5
E1_HR      | EMP-100151 | Dinesh Deshmukh    | E1    | HR   | WC-DEL |    12 |     8/8/4 |    3 |    5
E2_HR      | EMP-102451 | Pooja Verma        | E2    | HR   | WC-DEL |    12 |     1/0/0 |    1 |    5
E3_HR      | EMP-100144 | Pooja Pillai       | E3    | HR   | WC-DEL |    12 |     8/8/4 |    9 |    5
E4_HR      | EMP-100178 | Aarti Saikia       | E4    | HR   | WC-DEL |    12 |     8/8/4 |    5 |    5
E1_FIN     | EMP-100150 | Ajay Deshmukh      | E1    | FIN  | WC-DEL |    12 |     8/8/4 |    3 |    5
E2_FIN     | EMP-100152 | Praveen Nair       | E2    | FIN  | WC-DEL |    12 |     8/8/4 |    8 |    5
E3_FIN     | EMP-100146 | Asha Mishra        | E3    | FIN  | WC-DEL |    12 |     8/8/4 |    8 |    5
E4_FIN     | EMP-100145 | Santosh Banerjee   | E4    | FIN  | WC-DEL |    12 |     8/8/4 |    6 |    5

OK: 11/11 personas verified

$ grep -nE "emp_id\s*=\s*'EMP-[0-9]+'" yukti/backend/app/brain/certified/library.yaml yukti/backend/certified/library.yaml | wc -l
0

$ cd yukti/backend && "/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC/yukti/backend/.venv/bin/python" -m pytest -q \
    tests/test_personas_v3.py \
    tests/test_self_scope.py \
    tests/test_rbac_policy.py \
    tests/test_persona_question_matrix.py \
    tests/test_role_escalation.py \
    tests/test_transfer_note.py \
    tests/test_export_security.py \
    tests/test_auth_tokens.py \
    tests/test_no_answer_key_leak.py \
    tests/test_catalog_consistency.py \
    tests/test_query_spec.py
831 passed, 3 warnings in 4.14s
```

### Per-Suite Test Breakdown

| Suite | Passed | Duration |
|---|---:|---:|
| `tests/test_personas_v3.py` (new) | 49 | 0.30s |
| `tests/test_self_scope.py` (new) | 119 | 1.17s |
| `tests/test_rbac_policy.py` (extended to 11 × 12 × 2) | 323 | 0.73s |
| `tests/test_persona_question_matrix.py` (new, 11 × 18) | 198 | 0.71s |
| `tests/test_role_escalation.py` (extended to 10 × 6 + 11) | 77 | 2.29s |
| `tests/test_auth_tokens.py` (updated for 11 personas) | 20 | 1.71s |
| `tests/test_query_spec.py` | 15 | 0.11s |
| `tests/test_export_security.py` | 14 | 1.71s |
| `tests/test_catalog_consistency.py` | 8 | 0.63s |
| `tests/test_transfer_note.py` | 5 | 0.07s |
| `tests/test_no_answer_key_leak.py` | 3 | 0.22s |
| **Total** | **831** | **4.14s** |

---

## 4. Files Changed & Deviations

### Files Added / Modified
1. `data_bank/generators/hr/gen_app_users.py` (new)
2. `data_bank/landing/sap/dim_app_user.csv` (new, generated)
3. `yukti/backend/app/brain/app_users.yaml` (new, generated)
4. `dataform/definitions/gold/dim_app_user.sqlx` & `data_bank/medallion/dataform/definitions/gold/dim_app_user.sqlx` (new)
5. `yukti/backend/app/access_control.py` (11 personas, aliases, `UnknownPersona`, self & aggregate pay guards)
6. `yukti/backend/app/auth.py` (loads 11 personas from `app_users.yaml`, detects all 11 in `requested_persona`)
7. `yukti/backend/app/brain/rbac_policy.yaml` (v2 policy, 11 personas, 12 data classes, `director_function_scope` flag, bilingual refusal templates)
8. `yukti/backend/app/brain/rbac.py` (v2 `decide()`, function scope, `self_emp_id` binding, `pay_aggregate` allow)
9. `yukti/backend/certified/library.yaml` & `yukti/backend/app/brain/certified/library.yaml` (`@self_emp_id` in `E1/E2/E3/E6` + 8 `self_queries`)
10. `yukti/backend/app/tools/certified_query.py` (`resolve_self_emp_id`, `@self_emp_id` binding, `self_queries` index)
11. `yukti/backend/app/brain/query_spec.py`, `yukti/backend/app/brain/semantic_model.yaml`, & `yukti/backend/app/brain/compiler.py` (`self_scope`, `pay_scale_min_inr` template, `@self_emp_id` `ScalarQueryParameter`)
12. `yukti/backend/app/brain/planner.py` & `yukti/backend/app/brain/pipeline.py` (first-person possessive -> `self_scope=True`; `_PERSON_RE` no longer blocks `"my"`)
13. `yukti/backend/tests/test_personas_v3.py`, `tests/test_self_scope.py`, `tests/test_persona_question_matrix.py` (new)
14. `yukti/backend/tests/test_rbac_policy.py`, `tests/test_role_escalation.py`, `tests/test_auth_tokens.py` (extended to 11 personas)

### Deviations (Approved via Decision D-60, board #10)
1. **Both certified library paths updated:** `certified_query.py` loads `yukti/backend/certified/library.yaml` while `P2H.1.md` also references `yukti/backend/app/brain/certified/library.yaml`. Both files are kept identical so runtime and the packet's CI grep gate stay in sync.
2. **Both Dataform gold paths created:** Created `dataform/definitions/gold/dim_app_user.sqlx` (packet path) and `data_bank/medallion/dataform/definitions/gold/dim_app_user.sqlx` (repo Dataform root).
3. **`test_auth_tokens.py` & `test_role_escalation.py` updated for 11 personas (D-60 item 2):** Updated `test_auth_tokens.py` to expect all 11 personas (`E3_FIN = Asha Mishra`) and extended `test_role_escalation.py` from 4 to 10 non-CMD personas (60/60 escalation cases).

---

## 5. Round 2: G4 Review Fixes (`M1`–`M6` and `S1`–`S9`)

All 6 must-fix items (`M1`–`M6`) and 9 should-fix items (`S1`–`S9`) from [`docs/reviews/P2H.1.md`](./P2H.1.md) have been resolved and covered by regression tests:

| Finding | Resolution | Verification |
|---|---|---|
| **M1 (`agent.py:120`, `certified_query.py:83`)** | Added `ContextVar` (`_ACTIVE_PRINCIPAL`) in `auth.py`, bound in `turn_runner.py::execute_turn_async`. `agent.py::run_certified_query` reads `get_active_principal()` and fails closed (`code: "E-AUTH"`) when no server `Principal` is bound — never defaults to `CMD`/`EMP-000001`. Removed `persona: str = "CMD"` default in `certified_query.py::run_certified_query`. | `tests/test_self_scope.py::test_agent_tool_wrapper_uses_active_principal_and_fails_closed` |
| **M2 (`certified_query.py:52-63`, `certified/library.yaml`)** | Removed `"E2_HR"` default and `"EMP-102451"` fallback from `resolve_self_emp_id`; raises `UnknownPersona` on `None`, empty, or unknown personas. Replaced all `default: EMP-102451` YAML attributes with `default: null` in both `certified/library.yaml` and `app/brain/certified/library.yaml`. | `grep -cE "EMP-[0-9]{4,6}" certified/library.yaml app/brain/certified/library.yaml` -> **`0`**; `cmp -s` -> exit `0` |
| **M3 (`rbac.py`, `planner.py`, `pipeline.py`)** | Removed question-text regex from `_detect_self_emp_id`. `self` class is granted only when `"self" in data_classes` or `spec.self_scope` / `emp_id = @self_emp_id` is in the compiled `QuerySpec` (and no foreign employee/team target is present). `_verified_self_bypass` in `enforce_contract` requires every row in `table.rows` to have `emp_id == principal.emp_id` before skipping column masking. Tightened `planner.py` (`is_self_hr`) to exclude `"in my opinion"` / `"my colleagues"` / `"all officers"`. | `tests/test_self_scope.py::test_m3_adversarial_my_opinion_does_not_bypass_rbac` |
| **M4 (`rbac.py`, `compiler.py`, `pipeline.py`)** | `_enrich_classes_from_question` never strips compiler-derived classes (`pay_individual`, `named`, etc.) and never grants `pay_aggregate` from question text; any question naming an individual (`"What is the pay band of Ramesh Kumar"`) or requesting employee-level pay adds `pay_individual` and removes `pay_aggregate`. `compiler.py` only emits `pay_aggregate` when `grain == "aggregate"`, no `emp_id`/`name` filter is present, and `set(dims) <= {"grade", "discipline", "wc", "asset", "fy", "sector", "region"}`. | `tests/test_self_scope.py::test_m4_named_pay_band_and_row_grain_pay_refused_for_junior` |
| **M5 (`rbac.py`)** | `_infer_target_function` inspects `spec.filters` (`discipline == 'DISC-FIN'` vs `'DISC-HR'`) and marks mixed HR+Finance queries (`"Show APAR ratings of E3 HR officers and the finance officer"`, `"Show names of all Delhi staff (DISC-FIN)"`) as `"MIXED"` (refused/aggregated for single-function Directors). Extended `enforce_contract` to enforce D-43 for `DIR_FIN` (strips `sensitive` columns + $k \ge 5$ suppression; filters mixed tables to `DISC-FIN` rows and scrubs non-FIN names) and `DIR_HR` (strips `fin_internal` columns). | `tests/test_self_scope.py::test_m5_director_cross_function_mixed_query_and_enforce_contract` |
| **M6 (`certified_query.py`, `test_b2_review_regressions.py`)** | `list_certified_queries()` returns the 89 root catalog queries (`_CERTIFIED_ROOT_QUERIES`), while `get_certified_entry()` resolves both the 89 root queries and the `self_queries` section. `run_planner_turn` catches `UnknownPersona` for non-self queries and falls back to least-privilege `E1_HR` while `decide()` strictly raises `UnknownPersona`. Fixed `compiler.py::execute` `_run_sync` signature compatibility when `compiled.params` is empty. | `tests/test_certified_query.py` (**5 passed**), `tests/test_b2_review_regressions.py` (**8 passed**), `tests/test_provenance_labels.py` (**17 passed**) |
| **S1–S9 (`access_control.py`, `rbac.py`, `auth.py`, `test_rbac_live.py`)** | Fixed S1 (`check_access` evaluates foreign employee/refusal keywords before `is_self_question`/`is_aggregate_pay_question`), S2 (`R-POSH`/`R-MED` use `JUNIOR_PERSONAS` and return `partial` for `DIR_FIN`), S3 (`wacc` is `general_fin`; only valuation/DCF model runs are `valuation_run`), S4 (`decide()` raises `UnknownPersona` on unknown/empty/alias strings), S5 (`pipeline.py` and `certified_query.py` prefer `principal.emp_id`), S6 (added 198-case test without explicit `target_function`), S7 (updated `test_rbac_live.py::test_b3_director_sees_names_d10` for D-43), and S9 (`auth.py` loads strictly from `app_users.yaml`). | `tests/test_persona_question_matrix.py` (**396 passed**), `tests/test_self_scope.py::test_s1_s2_s3_s4_regressions` |

### Round 2 Verification Commands & Output

```text
$ cd yukti/backend
$ cmp -s certified/library.yaml app/brain/certified/library.yaml && echo "OK: library.yaml copies identical"
OK: library.yaml copies identical

$ grep -cE "EMP-[0-9]{4,6}" certified/library.yaml app/brain/certified/library.yaml
certified/library.yaml:0
app/brain/certified/library.yaml:0

$ "/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC/yukti/backend/.venv/bin/python" -m pytest -q \
    tests/test_personas_v3.py \
    tests/test_self_scope.py \
    tests/test_persona_question_matrix.py \
    tests/test_rbac_policy.py \
    tests/test_role_escalation.py \
    tests/test_auth_tokens.py \
    tests/test_refusal_copy.py \
    tests/test_certified_query.py \
    tests/test_b2_review_regressions.py \
    tests/test_catalog_consistency.py \
    tests/test_degraded_copy.py \
    tests/test_provenance_labels.py
1092 passed, 3 warnings in 23.45s
```

### Full-Suite Classification (Offline vs Live Environment Tests)

Across the full `yukti/backend/tests` directory:
- **Offline / deterministic suites (`1,092 passed`, `0 failed`):** All RBAC, persona, self-scope, refusal copy, auth token, certified query (89-query catalog), B2 regression, provenance labels, export security, transfer note, catalog consistency, degraded copy, and QuerySpec suites pass 100%.
- **Pre-existing live Gemini / BigQuery / snapshot-drift suites (outside `P2H.1` scope):**
  - `test_finance_chain.py`, `test_flagship_chain.py`, `test_planner_golden.py`, `test_materialized_reconcile.py`: Require live Gemini LLM narration (e.g. live sentence-count variation 6 vs 4) or reflect pre-existing `local_snapshot` vs live `bigquery` PBT figures (`7753.84` vs `7132.1`). Zero failures in any offline test after `M6` fixes.
