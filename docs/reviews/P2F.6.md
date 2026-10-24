# P2F.6 Independent G4 Review — Top-5 Action Generator, Safe AST (`expr.py`), and Delegation Table

**Final Verdict (Round 2): `APPROVE`** — **All 3 Round 1 blocking defects (`P2F6-B1`..`P2F6-B3`) have been resolved across `actions.py`, `expr.py`, `fin_diagnostics/__init__.py`, and `test_actions.py`. All 14/14 unit and real-data tests in `test_actions.py` pass (`pytest -v yukti/backend/tests/agents/test_actions.py`), including real `financial_ssot/out/fact_snapshot.parquet` execution (`L02` debtor-days release of ₹1,089.1 cr, `L03` synthesized `40.5` MMBOE, `L05` synthesized `BS.CWIP_TOTAL`), complete multi-year `evidence[]` lineage for `prior`/`yoy`/`avg5`/`median5`, AST call keyword/arity/`_VAR_` guards, and package exports.**

- **Reviewer:** `reviewer-p2h2` (independent G4 reviewer; fresh context)
- **Worktree:** `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC__v3P2F`
- **Branch:** `v3/P2F-fin-diag` (`1d0fffa` + `6d645f2` + Round 2 fixes)
- **Reference Specs:** `docs/delegation/packets/v3/P2F.6_top5_action_generator.md`, `docs/specs/SPEC-08_v20_finance_diagnostics.md` §7
- **Files reviewed:**
  - [levers.yaml](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/agents/fin_diagnostics/levers.yaml)
  - [expr.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/agents/fin_diagnostics/expr.py)
  - [actions.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/agents/fin_diagnostics/actions.py)
  - [`__init__.py`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/agents/fin_diagnostics/__init__.py)
  - [test_actions.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/tests/agents/test_actions.py)

---

## 1. Round 2 Verification Summary (`APPROVE`)

| Blocker ID | Summary | Resolution Verified |
| :--- | :--- | :---: |
| **`P2F6-B1`** | `_lookup_cell` failed on `fact_snapshot.parquet` for `L02` (`RATIO.DEBTOR_DAYS`), `L03` (`PROD.TOTAL_BOE`), and `L05` (`BS.CWIP_TOTAL`), and lacked `period_type == "annual"` filtering | **RESOLVED** (`actions.py:52-162`, `test_actions.py:319-348`): Filters `period_type == "annual"`, resolves first non-null across `("value_inr_cr", "value", "value_native")`, and synthesizes `BS.CWIP_TOTAL` and `PROD.TOTAL_BOE`. Verified on real `fact_snapshot.parquet` (`L02` = ₹1,089.1 cr, `L03` = 40.5 MMBOE). |
| **`P2F6-B2`** | `evidence[]` omitted `yoy(...)`, `avg5(...)`, and `median5(...)` historical window references | **RESOLVED** (`actions.py:310-335`, `test_actions.py:339-348`): Collects all expressions/templates and includes `prior_y` for `"prior"`/`"yoy"` and all `window_fys` (`FY22..FY26`) for `"avg5"`/`"median5"`. |
| **`P2F6-B3`** | Missing keyword-arg, arity, and `_VAR_` guards in `expr.py` + missing exports in `fin_diagnostics/__init__.py` | **RESOLVED** (`expr.py:74-75, 193-221`, `fin_diagnostics/__init__.py:10-27`, `test_actions.py:350-372`): Rejects `_VAR_`, `node.keywords`, and invalid arities on `abs`/`min`/`max`/`prior`/`yoy`/`avg5`/`median5` with `ExprError`, and exports `ExprError`, `evaluate`, `generate_actions`. |

---

## 2. Checklist Verification Summary (`Packet P2F.6 §6`)

| Requirement | Status | Notes |
| :--- | :---: | :--- |
| Safe AST evaluator (`expr.py`): no `eval()`/`exec()`, rejects `Attribute`, non-whitelisted `Call`, `Subscript`, `Lambda`, `Import`, keyword args, invalid arity, `_VAR_` | **PASS** | Verified in `expr.py` and `test_expr_security_rejections` + `test_p2f6_b3_expr_call_and_arity_guards` |
| `levers.yaml`: 10 levers (`L01`..`L10`), valid YAML, only whitelisted `expr.py` syntax | **PASS** | All 10 levers match `SPEC-08 §7.2` and parse cleanly through `expr.py` |
| Triggered levers sorted by `score` (`mid * confidence`) desc, tie-broken by lever ID asc | **PASS** | Verified in `actions.py:371` and `test_actions.py` |
| Owner diversity rule (`<= 3` actions from same `owner`) | **PASS** | Verified in `actions.py:385-393` and `test_owner_diversity_rule` |
| `DIR_HR` persona forces inclusion of `L07` if triggered and orders HR levers first | **PASS** | Verified in `actions.py:379-398` and `test_dir_hr_persona_includes_l07` |
| `E1..E4` personas receive `"for discussion"` owner role (`BEH-01`) | **PASS** | Verified in `actions.py:412-434` and `test_e_level_persona_for_discussion` |
| `ar_evidence_fn` injected as deterministic mock in tests; no network/LLM call | **PASS** | Verified in `actions.py:338-346` and `test_ar_evidence_injection` |
| `< 5` triggered levers emits explicit note (never pads with untriggered levers) | **PASS** | Verified in `actions.py:442-443` and `test_fewer_than_5_note_with_fixture` |
| Output validates against `SPEC-08 §7.3` JSON schema | **PASS** | Verified in `test_jsonschema_validation` |
| Works against real `financial_ssot/out/fact_snapshot.parquet` & full multi-year `evidence[]` | **PASS** | Verified in `test_p2f6_b1_b2_fact_snapshot_real_data` (24/24 tests pass across `test_variance.py` + `test_actions.py`) |
