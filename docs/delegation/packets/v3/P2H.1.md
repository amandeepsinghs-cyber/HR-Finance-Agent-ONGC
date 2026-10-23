# Task Packet: `P2H.1` 11 personas, `dim_app_user`, function dimension, `self` scope, aggregate pay

**Executor:** O (`inherit`; RBAC core) with F for the test matrix (§5.7, delegated as a sub-packet after O lands the policy) · **Author:** O · **Date:** 2026-10-23
**Branch:** `v3/P2H-hr` · **Base SHA:** `<after P0>` · **Max files changed:** 14 · **Budget:** ~90 tool calls (O) + ~40 (F tests) · **Features:** FEAT-017, FEAT-031 · **Bugs:** BUG-07, BUG-27, BUG-28 · **Spec:** [SPEC-06](../../../specs/SPEC-06_personas_identity_rbac_v3.md) §4.1–4.5, §4.8 · **Behaviour:** [BEH-01](../../../behaviour/BEH-01_persona_matrix.md)
**App root (quote it):** `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC`

## 1. Goal
All 11 personas exist end-to-end with seeded identities, a function-aware policy, a `self` scope bound to `@self_emp_id`, and aggregate pay allowed to juniors.

## 2. Context you need
- `yukti/backend/app/access_control.py:12-33, 239-243, 276-390`; `brain/rbac.py`; `brain/rbac_policy.yaml`; `brain/certified/library.yaml:1617,1649,1673,1743`; `brain/pipeline.py:37` (`_PERSON_RE`); `brain/compiler.py` (param binding).
- diag_B §1, §2 (Delhi pools), §7 item 1.
- P0.4 `auth.py` (`Principal`).

## 3. Files you may change
1. `data_bank/generators/hr/gen_app_users.py` (new; deterministic selection per SPEC-06 §4.1, emits CSV + YAML)
2. `data_bank/landing/sap/dim_app_user.csv` (generated)
3. `yukti/backend/app/brain/app_users.yaml` (generated mirror for offline tests)
4. `dataform/definitions/gold/dim_app_user.sqlx` (new; load from landing; **no `bq` run by the executor**)
5. `yukti/backend/app/access_control.py`
6. `yukti/backend/app/brain/rbac.py`
7. `yukti/backend/app/brain/rbac_policy.yaml` (v2 per SPEC-06 §4.3)
8. `yukti/backend/app/brain/certified/library.yaml` (`@self_emp_id` + 8 self queries)
9. `yukti/backend/app/brain/compiler.py` (bind `self_emp_id`; `self_scope` predicate)
10. `yukti/backend/app/brain/planner.py` / `pipeline.py` (possessive → `self_scope`; `_PERSON_RE` no longer blocks "my")
11. `yukti/backend/app/auth.py` (load 11 personas from `app_users.yaml`/BQ)
12. `yukti/backend/tests/test_personas_v3.py`, `tests/test_self_scope.py` (new)
13. `yukti/backend/tests/test_rbac_policy.py` (extend to 11 × 12)
14. `yukti/backend/tests/test_persona_question_matrix.py` (new, F sub-packet)

## 4. Do NOT touch
- Frontend (P2H.2), V19 logic (P2H.3/4), SPEC-04 regeneration (P2H.5+). No git/deploy/`bq` DDL/DML/destructive commands (O runs the Dataform deploy separately with sponsor OK).

## 5. Exact requirements
1. `gen_app_users.py` selects rows per SPEC-06 §4.1 (keep EMP-102451 for E2_HR; Rajesh Kulkarni rule for E3_FIN; lowest emp_id passing the completeness gate otherwise) from landing CSVs; prints a table persona → emp_id, name, grade, discipline, gate flags.
2. Completeness gate SQL (to run in BQ by O later) and the same check in pandas; both must return 11 rows all TRUE.
3. `VALID_PERSONAS` = 11; `normalize_persona` maps aliases ("E1 HR officer", "e3-fin") to exact ids; unknown → `UnknownPersona`.
4. Policy v2 decisions exactly per SPEC-06 §4.3 table; `unknown_persona: reject`. **Until OD-7 is decided**, implement the function-scoped Director cells behind `rbac_policy.yaml` flag `director_function_scope: true`; setting it to `false` restores D-10 (Directors see everything). Test both flag values. Agents are not gated here except `dcf_agent` (`valuation_run` = CMD, DIR_FIN); everything else is masked by `enforce_contract` per the matrix (SPEC-06 §4.3 authority note).
5. Self scope: compiler injects `emp_id = @self_emp_id` when `spec.self_scope`; all 4 hard-coded `EMP-102451` SQL literals replaced; 8 new certified self queries.
6. Pay guard: aggregate pay specs with n ≥ 5 → `pay_aggregate` (allow); entry pay from `dim_grade.pay_scale_min_inr`.
7. F sub-packet: generate the 198-case matrix (11 × 18, SPEC-06 §6) as QuerySpec fixtures + expected `(decision, refusal_code)`; offline.

## 6. Examples
```
principal=E3_FIN, "What is my leave balance?" → SQL has "emp_id = @self_emp_id", param = E3_FIN's emp_id; 0 rows with EMP-102451
principal=E2_HR, "average salary of E1 officers" → decision allow (pay_aggregate), n_e1 ≥ 5
normalize_persona("E4_FIN") == "E4_FIN"; normalize_persona("E5_HR") raises UnknownPersona
```

## 7. Acceptance criteria
- [ ] SPEC-06 AC 1, 2, 5, 6, 7, 10 met (11 ids; 11 seeded rows; self scope; 198/198; masking; old 77 tests).
- [ ] `grep -nE "emp_id\s*=\s*'EMP-[0-9]+'" yukti/backend/app/brain/certified/library.yaml` → 0.
- [ ] Escalation suite from P0.4 extended to 10 non-CMD × 6 = 60/60.

## 8. Self-check commands
```bash
cd "<app root>/data_bank" && .venv/bin/python generators/hr/gen_app_users.py --check
cd "<app root>/yukti/backend" && .venv/bin/python -m pytest -q tests/test_personas_v3.py tests/test_self_scope.py tests/test_rbac_policy.py tests/test_persona_question_matrix.py tests/test_role_escalation.py tests/test_transfer_note.py tests/test_export_security.py
grep -nE "emp_id\s*=\s*'EMP-[0-9]+'" "<app root>/yukti/backend/app/brain/certified/library.yaml" | wc -l   # expect 0
```

## 9. Stop-and-ask triggers
- Any pool cannot satisfy the completeness gate (likely leave rows until BUG-29 is fixed → report; do not fake rows).
- Director rows EMP-000002/3 function mapping unclear.

## 10. Report format
- **Files changed** · **Persona → emp_id table** · **Self-check output** · **Acceptance criteria** ✅/❌ · **Open questions**
