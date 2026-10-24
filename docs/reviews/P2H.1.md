# G4 Review: `P2H.1` (11 personas, `dim_app_user`, function scope, `self` scope, junior aggregate pay)

**Reviewer:** reviewer-p2h1 (role R, Claude Opus Medium) · **Date:** 2026-10-24 · **Commit:** `785e01d` on `v3/P2H-hr` · **Builder:** rbac (Gemini Argon)

## Verdict: **CHANGES REQUESTED**

**Cross-employee leakage is still possible, so the step must not pass G4.** The main LLM path to certified self-service queries binds `@self_emp_id` to the CMD (`EMP-000001`) for every persona. Separately, `self` and `pay_aggregate` are granted when the question text matches a regex, not when the compiler has actually enforced them. The 831 offline tests pass, and the persona enum, the escalation suite, the library-copy parity and the seeding are all sound. But the tests call `decide()` and `run_certified_query()` directly with the right arguments, so they never reach the paths where the holes are.

Severity: **6 blocking (M1–M6)**, 9 should-fix (S1–S9).

---

## Must-fix (blocking)

| # | Where | Defect | Impact | Fix |
|---|---|---|---|---|
| **M1** | `yukti/backend/app/agent.py:120`; `yukti/backend/app/tools/certified_query.py:83` | The LLM tool `run_certified_query` calls `execute_certified_query(query_id=…, params=…)` with **no persona or self_emp_id**. `run_certified_query` therefore defaults to `persona="CMD"`, and `resolve_self_emp_id("CMD")` returns `EMP-000001`. The cache key at `certified_query.py:145` is also `persona="CMD"`. | **Blocking privacy leak.** On the production turn path, the router tells the LLM to call `run_certified_query('E1'/'my_payslip'…)` (`turn_runner.py:1489`). So every persona asking "my leave balance / my payslip" receives the **CMD's** rows, and they are cached under CMD. BUG-07 is moved, not closed. | Bind the server-side `Principal` into the tool, using a per-turn contextvar or a closure built in `turn_runner`. Remove the `persona="CMD"` default and fail closed (error) when no principal is bound. Add a test that drives the agent tool wrapper for 2 different personas and asserts different bound emp_ids. |
| **M2** | `certified_query.py:52,59-63`; `certified/library.yaml:1625,1658,1685,1763,3583,3603,3625,3643,3661,3680` (same lines in `app/brain/certified/library.yaml`) | `resolve_self_emp_id` defaults to `persona="E2_HR"`, maps an **unknown persona to `E2_HR`**, and falls back to the literal `"EMP-102451"`. The library still carries `default: EMP-102451` on all 10 `self_emp_id` params. | This is the BUG-27 failure mode again: silent mapping to Pooja Verma. The grep gate (`emp_id = 'EMP-…'`) does not catch YAML `default:` literals, so check item 7 is only nominally met. | Raise `UnknownPersona` with no default persona. Delete the `default:` for `self_emp_id`, or set it to `null`. Widen the CI gate to `grep -nE "EMP-[0-9]{6}"` on both library copies, and expect 0. |
| **M3** | `app/brain/rbac.py:467-482`, `:199-209` (`_detect_self_emp_id` branches 2 and 3); `rbac.py:686-699` (`enforce_contract` self bypass) | `decide()` returns `allow / ["self"]` whenever `_FIRST_PERSON_SELF_RE` matches the **question text**, and it **discards the compiler's data classes**. `enforce_contract` then returns the contract **unmasked and without k-suppression** when no row has an `emp_id` key that differs from self. A missing `emp_id` column counts as a pass. | Reproduced offline: E2_HR asking *"In my opinion, list net pay of all E2 HR officers"* gives `allow ['self']`. E3_FIN asking *"my colleagues medical claims"* gives `allow ['self']` (a `sensitive` class turned into self). The planner's self regex differs from this one (no `net pay`/`gross pay`/`hba`/`laptop`/`furniture`). In those cases `spec.self_scope=False`, so no predicate is injected and population rows run with "self" clearance. SPEC-06 §4.2 says `self` must be *"compiler-enforced predicate, not a text match"*. | Grant `self` **only** when the compiled query carries the predicate, i.e. `"self" in compiled.data_classes` / `CompiledQuery.self_emp_id` is set. Drop the regex branches. In `enforce_contract`, require that **every** row has `emp_id == self_id` (missing column = not self), or carry a compiler-signed `self_scoped=True` flag. |
| **M4** | `rbac.py:279-288` (`_enrich_classes_from_question`); `brain/pipeline.py:259`; `rbac.py:702-708` | Any question matching `pay (scale\|band\|range…)`, `starting pay`, etc. is re-classed as `pay_aggregate`, and **compiler-derived `pay_individual` is stripped**. Name exclusion only covers the 11 persona names. `allow_pay_aggregate` then disables pay-column masking in `enforce_contract`. | Reproduced: E2_HR asking *"What is the pay band of Ramesh Kumar"* gives `allow ['pay_aggregate']`. A named individual's pay can be returned unmasked for a junior. SPEC-06 §4.3 requires "no `emp_id` filter, grouping ⊆ {grade, function, WC, FY} **and** every cell n ≥ 5". | Decide `pay_aggregate` from the **compiled spec**: grain = aggregate, no emp/name filter, dimensions ⊆ allowed set, and the cell-count column ≥ 5 per row. Never remove a compiler-derived `pay_individual`. Set `allow_pay_aggregate` only when those conditions hold. |
| **M5** | `rbac.py:214-262` (`_infer_target_function`); `rbac.py:683-684` (`if pc != "junior": return c`) | D-43 function scope depends on **keywords in the question**, and the post-query guard skips **all non-juniors**. | Reproduced: DIR_FIN asking *"Show APAR ratings of E3 HR officers and the finance officer"* gives **allow** (target=FIN), and *"…all Delhi staff (DISC-FIN)"* also gives **allow**. On the legacy/LLM path (`query_data`), DIR_FIN gets HR names/pay/APAR and raw POSH rows unmasked, and DIR_HR gets raw `fin_internal`, because `enforce_contract` never applies D-43 cells. The SPEC-06 §4.3 authority note says agent results "pass through `enforce_contract` with this matrix". | Take the target function from the compiled discipline filter or row `discipline_id`. When it can't be determined, treat it as not-own-function for directors. Extend `enforce_contract` to directors: for DIR_FIN, strip `named/pay/apar` columns (or rows with `discipline_id != 'DISC-FIN'`) and aggregate `sensitive` with k ≥ 5. For DIR_HR, aggregate `fin_internal`. Keep honouring `director_function_scope=false`. |
| **M6** | `yukti/backend/tests/test_certified_query.py:24` | Regression: `test_certified_library_loading` now fails (`Expected 89 queries, found 105`) because the index also loads `self_queries`. The evidence ran only 11 selected suites, so the regression was missed (packet AC-10: "existing tests stay green"). | Full-suite result: 14 failed / 1120 passed. This one is caused by P2H.1. See S7 for the rest. | Update the expectation, or keep `self_queries` out of `list_certified_queries()`. Include the full-suite result in the evidence and classify each failure as either environment or regression. |

---

## Should-fix (important, not blocking on their own)

- **S1** `app/access_control.py:497-515`: `check_access` short-circuits on the self and aggregate-pay regexes **before** the junior topic refusals. *"pay scale and salary of each employee in Delhi"* and *"list my team's APAR ratings"* both return `allowed` for E1_HR and E3_FIN, and the second sets `self_emp_id`. Post-query masking currently limits the damage on the legacy path, but the pre-query guard is defeated. Run the topic refusals first, and let self/agg-pay only *relax* a decision once the compiled spec confirms it.
- **S2** `access_control.py:363,370`: `R-POSH` / `R-MED` `restricted_personas` is still the v2 pair `{"E2_HR","E3_FIN"}`. Use `JUNIOR_PERSONAS`, and model DIR_FIN as aggregate.
- **S3** `rbac.py:307`: `wacc` is classed as `valuation_run`, so E1_HR asking *"What is ONGC's WACC for FY25?"* is refused with R-FUNC. Under SPEC-06, WACC is `general_fin` (A for all), and the WACC series is the *alternative* offered for Q16. Only "run/compute a DCF/valuation" should be `valuation_run`.
- **S4** `rbac.py` `decide()`: an unknown or empty persona (`""`, `None`, `E5_HR`, `DEMO_ADMIN`) is evaluated as `junior`. That fails closed, so it is acceptable for least privilege, but the spec says `unknown_persona: reject`. `decide("chairman")` resolves to `leadership` through the alias map. Make `decide` raise `UnknownPersona`, and assert that callers pass only `Principal.persona`.
- **S5** `brain/pipeline.py:145` and `certified_query.py`: `self_emp_id` comes from `PERSONA_DIRECTORY[persona]`, not from `principal.emp_id` (SPEC-06 §3/§4.5). The two are the same in demo mode but will diverge in `iap` mode.
- **S6** `tests/test_persona_question_matrix.py` (`decide(..., target_function=q_entry["target_function"])`): the 198 cases always pass `target_function` explicitly, so the text-inference path used in production is untested. Add pipeline-level cases without `target_function`, plus the adversarial phrasings from M3, M4 and M5.
- **S7** `tests/test_rbac_live.py::test_b3_director_sees_names_d10` still asserts D-10, which D-43 superseded. Update it. The other live failures (`local_snapshot` vs `bigquery`, roster set mismatch, `planner_golden G15/G23`, `materialized_reconcile`) also fail on the parent tree or are ADC-related (SA-1). Record them in the evidence as environment failures.
- **S8** D-60 (board #10) is not in `docs/DECISIONS.md` (the lead's tracking item). D-60 also covers the relaxed `ok_leave` rule for E2_HR (`gen_app_users.py:299-301`).
- **S9** `app/auth.py:40-150`: the hard-coded `_DEFAULT_PERSONA_DIRECTORY` duplicates `app_users.yaml`, so the two can drift. Prefer failing at startup when the YAML is missing or not exactly 11 personas.

---

## Checklist results (brief items 1–9)

| # | Check | Result | Notes |
|---|---|---|---|
| 1 | No cross-employee leakage in `self`; bound from server principal | ❌ | M1 (agent tool binds CMD), M2 (E2_HR fallback), M3 (text-based self). The compiler path itself is correct: `compiler.py:307-311` adds `emp_id = @self_emp_id` with a `ScalarQueryParameter`, and `certified_query.py:109` pops caller-supplied `self_emp_id`. |
| 2 | Unknown/empty persona fails closed | ⚠️ | `normalize_persona` raises `UnknownPersona` (✅, `access_control.py:400-421`). `resolve_self_emp_id` maps unknown to E2_HR (M2). `decide` maps unknown to junior (S4). |
| 3 | Function split, 11 × classes; ≥ 10 matrix cells spot-checked | ⚠️ | The policy table matches SPEC-06 §4.3. 13 cells spot-checked against §6 all match: Q01 E*_FIN AGG; Q03 DIR_HR AGG/R-FUNC; Q03 E*_HR AGG/R-FUNC; Q05 DIR_FIN AGG; Q06 DIR_FIN A; Q09 DIR_FIN R-PAY; Q11 DIR_FIN AGG/R-SENS (probe); Q13 E3_FIN SELF=EMP-100146; Q15 DIR_HR R-BOARD / DIR_FIN A; Q16 DIR_HR R; Q17 R-ROLE; Q18 E*_FIN R-FUNC. But the target function is spoofable and not enforced post-query for directors (M5). |
| 4 | k ≥ 5 suppression | ⚠️ | `suppress_small_cells` is applied to junior tables and charts (`rbac.py:720-732`). It is bypassed on the self path (M3), and directors' AGG cells are never suppressed (M5). |
| 5 | Junior aggregate pay allowed; others' individual pay refused | ⚠️ | Q07/Q08 allowed and Q09 refused (✅). The text-only `pay_aggregate` lets named pay through (M4). |
| 6 | No escalation via body, WS, voice or text | ✅ | `test_role_escalation.py`: 77 passed (60/60 role-switch phrasings, body persona ignored, WS cannot switch, ui_control rejects persona, admin switch audited). |
| 7 | No hard-coded emp_id literals | ⚠️ | The SQL grep gate returns 0 (✅). 10 `default: EMP-102451` YAML params remain, plus the fallback at `certified_query.py:63` (M2). |
| 8 | Two `certified/library.yaml` copies identical and safe | ⚠️ | `cmp` says identical. The runtime loads only `yukti/backend/certified/library.yaml`, and `app/brain/certified/library.yaml` is a new duplicate. Safe apart from the M2 defaults. |
| 9 | Deterministic identity seeding | ✅ | `gen_app_users.py` uses the lowest `emp_id` in the Active `WC-DEL` discipline × grade pool that passes the full gate (`:364-385`), pins EMP-102451 for E2_HR, and falls back to EMP-100146 for E3_FIN (Rajesh Kulkarni is `WC-MUM`). Senior surnames are fictional per D-60. E2_HR's leave is 1/0/0 (EL only); the coordinator accepted this in D-60 (#10), and it is fixed with P2H.5. |

## Commands run (by reviewer)

```bash
# from worktree yukti/backend, main-copy venv
.venv/bin/python -m pytest -q                       # full: 14 failed, 1120 passed (198 s)
.venv/bin/python -m pytest -q <the 11 evidence suites>   # 831 passed
# parent tree (git archive 785e01d~1 → /tmp) for baseline: planner_golden G15/G23 and materialized_reconcile fail there too
cmp certified/library.yaml app/brain/certified/library.yaml   # identical
grep -nE "EMP-[0-9]{4,6}" certified/library.yaml              # 10 × default: EMP-102451
# offline probes of decide()/check_access()/resolve_self_emp_id() — results quoted in M3–M5, S1–S4
```

## Re-review entry criteria

1. M1–M6 fixed, each with a regression test that fails on `785e01d`: the agent-tool binding for 2 personas, the unknown-persona resolver, the adversarial self/agg-pay/target-function phrasings above, and director post-query masking.
2. Full `pytest -q` result in the evidence, with each remaining failure classified as environment or pre-existing.
3. The widened `EMP-` grep gate returns 0 on both library copies.


---

## Round 2 verdict (commit `0ddbe7f`): **CHANGES REQUESTED** (1 small functional must-fix; no open security defects)

**All six round-1 security must-fixes are fixed, and I verified each one myself.** There is no cross-employee leakage on the agent-tool, certified-query, planner or WebSocket paths, and a missing principal fails closed on every one of them. One functional must-fix remains. Juniors' canonical aggregate-pay question, SPEC-06 Q07 (*"Average monthly basic pay of E1 officers"*), is still **refused** by the pre-query guard on the live turn path. So does the packet §6 example (*"average salary of E1 officers"*). That means BUG-28 is claimed closed but is not closed end-to-end. The fix is a one-line regex alignment.

### R2 must-fix

| # | Where | Defect | Fix |
|---|---|---|---|
| **R2-M1** | `yukti/backend/app/access_control.py:424-435` (`_AGGREGATE_PAY_RE`); guard order is `turn_runner.py:473` (`check_access`) before `:695` (`run_planner_turn`) | `check_access` refuses these for every junior with R-PAY: *"Average monthly basic pay of E1 officers"*, *"average salary of E1 officers"*, *"joining pay of E1"*. `decide()` allows them, but the request never reaches the planner. The defect was already present in `785e01d`; I missed it in round 1. Phrasings that do pass: "average salary by grade", "E1 pay scale", "What does an E1 officer get on joining?", "Average CTC of E3 executives". | Reuse `rbac._V2_AGG_PAY_RE`, or at least add `average (monthly )?(basic )?(salary\|pay) (of\|for) e[1-9]` and `joining (pay\|salary)`. Keep the `_mentions_individual_or_row_pay_target` exclusion. Add a `check_access` test for Q07/Q08 × 8 juniors expecting `allowed`, plus the packet §6 example. |

### Round-1 items re-verified (reviewer probes, offline)

| Item | Result | Evidence |
|---|---|---|
| **M1** agent tool binds the principal | ✅ | `agent.py:120-136` reads `get_active_principal()`, and `turn_runner.py:280-294` sets and resets it around every turn. Probe: no principal → `E-AUTH`. E3_FIN → `persona=E3_FIN, self_emp_id=EMP-100146`; E1_HR → `EMP-100151`, even when the LLM passes `params={"self_emp_id":"EMP-000001"}`, because the param is popped. The cache key is the canonical persona. All `execute_turn_async` callers (`main.py:353,418`, `live_session.py:401,534,1078,1179`) pass `principal`. `/ws/live` closes with 4401 when there is no valid token (`main.py:533-548`). |
| **M2** no fallback, no literals | ✅ | `resolve_self_emp_id()` and `resolve_self_emp_id("bogus")` raise `UnknownPersona`. `run_certified_query("my_payslip")` with no principal raises, so it fails closed. `grep -cE "EMP-[0-9]{4,6}"` returns 0 on both library copies, and `cmp` says they are identical. |
| **M3** self is compiler-enforced | ✅ | E2_HR *"In my opinion, list net pay of all E2 HR officers"* → `refuse R-PAY` (with both `[pay_individual,named]` and `[general]`). E3_FIN *"my colleagues medical claims"* → `refuse R-SENS`. `self` is granted only from `"self"` in the compiled classes or the spec predicate (`rbac.py:227-245`). The `enforce_contract` bypass now needs every row to carry `emp_id == self`: a fake `self_emp_id` with no `emp_id` column has its pay/APAR/name columns stripped. |
| **M4** `pay_aggregate` comes from the compiled spec | ✅ | *"What is the pay band of Ramesh Kumar"* → `refuse R-PAY` (any case, any base class). In `compiler.py:374-387`, `pay_aggregate` requires aggregate grain, no person filter and allowed dims. `allow_pay_aggregate` is gated the same way at `pipeline.py:270-284`. |
| **M5** D-43 | ✅ | DIR_FIN: *"APAR of E3 HR officers and the finance officer"* → `refuse` (MIXED); *"(DISC-FIN)"* → `refuse`; *"Salaries of all Delhi executives, accounts officer view"* → `refuse`. A spec discipline filter decides the target (DISC-HR → refuse; DISC-FIN → allow). Post-query, DIR_FIN mixed tables drop the DISC-HR rows, tables without `discipline_id` get personal columns stripped (fail closed), and the POSH case id is stripped while counts are kept. DIR_HR `fin_internal` loses `vendor_name` and the status becomes `partial`. |
| **M6** test regression | ✅ | `test_certified_query.py` passes, and `list_certified_queries()` returns the 89 root queries. |
| S1 `check_access` short-circuits | ✅ | "pay scale and salary of each employee", "list my team's APAR ratings" and "Show my colleagues' salaries" are now refused for juniors. |
| S3 WACC | ✅ | E1_HR *"What is ONGC's WACC for FY25?"* → `allow` (general_fin). |
| S4 `decide` on unknown persona | ✅ | `""`, `None`, `E5_HR`, `chairman` and `DEMO_ADMIN` all raise `UnknownPersona`. |
| Escalation / library / seeding | ✅ | Unchanged from round 1. |

### Full suite (reviewer run, `0ddbe7f`)

`12 failed, 1381 passed` (180 s). Round 1 was 14 failed. Classification:
- **Environment / pre-existing:** `test_planner_golden` G15/G23 and `test_materialized_reconcile` fail on the parent tree too. `test_flagship_chain` ×4, `test_finance_chain` ×2, and `test_rbac_live` b31/b35 come from `local_snapshot` / ADC (SA-1), with roster sets differing from live BQ.
- **New since round 1, wording only:** `test_rbac_live.py:111` (`test_b34_junior_names_become_aggregate_and_agree`) asserts the word `"restricted"`, but the P2H.2 SPEC-06 §4.6 copy now reads *"I can't share individual names at your access level…"*. Update the assertion to the R-NAMED copy. This is not a security issue.

### Should-fix (non-blocking)

- `brain/pipeline.py:167`: on `UnknownPersona`, the code falls back to `decide("E1_HR", …)` for non-self specs. That is least-privilege, but it is still a silent mapping. Re-raise and return E-AUTH instead, to match `unknown_persona: reject`.
- `turn_runner.py:262,329` (`persona: str = "CMD"`), and the same default in `tools/query_data.py:95,291`, `tools/what_if.py:25`, `tools/policy_search.py:190,267`. Every current caller passes a principal, but a future caller that omits it becomes CMD. Make `principal` required, or default to raising.
- `test_rbac_live.py:111` wording, as above.

### Re-review entry criteria

R2-M1 fixed, with the Q07/Q08 × 8-junior `check_access` test. I will only re-verify that item, plus the evidence suites.


---

## Round 3 verdict (commit `a34a2a0`): **APPROVE**

**R2-M1 is fixed. Junior aggregate pay now gets through the pre-query guard, and individual pay of others is still refused. No blocking items remain for P2H.1.**

### What I checked (offline probes: 8 juniors, both `check_access` and `decide`)

| Probe set | Result |
|---|---|
| Should be allowed: Q07 *"Average monthly basic pay of E1 officers"*, Q08 *"What does an E1 officer get on joining?"*, *"average salary of E1 officers"*, *"joining pay of E1"*, *"average salary by grade"*, *"E1 pay scale"* | ✅ 48/48 allowed by both layers |
| Should be refused: *"pay of Ramesh Kumar"*, *"What is the pay of Ramesh Kumar?"*, *"my colleague's salary"*, *"What is my colleague's salary?"*, *"pay scale and salary of each employee in Delhi"*, *"list salaries of all E1 officers"*, *"average salary of E1 officers in my team"*, *"What is the pay band of Ramesh Kumar"*, *"salary of my reporting officer"* | ✅ refused by both layers for all 8 juniors |
| Own name or own emp_id (*"What is Pooja Verma's salary?"* as E2_HR, *"salary of EMP-100146"* as E3_FIN) | `check_access` returns allowed (own record) and `decide` refuses. Neither leaks. |

### Tests
- 14 RBAC/persona/auth/catalog/planner suites: **1171 passed, 3 failed**. The failures are `planner_golden` G15/G23, which also fail on the parent, and G04, which passed 3/3 when run alone. G04 is the follow-up "Compare with Mumbai" and depends on G03; I treat it as an order-dependent flake. The fix doesn't touch the follow-up/patch path.
- The new 40-case `test_r2_m1_check_access_and_decide_allow_junior_aggregate_pay` passes. The `test_rbac_live.py:111` wording assert was updated to the R-NAMED copy.
- `pipeline.py:177`: `UnknownPersona` is now re-raised instead of being silently downgraded (it closes the round-2 should-fix).

### Remaining should-fix (non-blocking; can go into P2H.2/P2H.3)
1. `rbac.py:161-187` (`_mentions_individual_or_row_pay_target`): a name not preceded by "of/for" or possessive is missed. *"Average monthly basic pay of E1 officer Ramesh Kumar"* passes both text guards as `pay_aggregate`. That is **not a leak** today: on the planner path the compiled spec decides (a name filter → `pay_individual` → refuse, and an unmappable filter → CompileError → legacy). On the legacy path `enforce_contract` masks pay columns for juniors, because `allow_pay_aggregate` is set only by the planner. Still, harden the name detector, e.g. any capitalised two-word token pair not in `_NON_PERSON_PROPER_WORDS`.
2. `turn_runner.py:262,329` and `tools/query_data.py:95,291`, `tools/what_if.py:25`, `tools/policy_search.py:190,267` still default to `persona="CMD"`. Make the principal required (carried over from round 2).
3. Investigate the G04 order-dependent flake.

**Overall P2H.1 status:** security, RBAC, self scope, function scope, k≥5 and seeding are verified. Ready to merge from a G4 standpoint.
