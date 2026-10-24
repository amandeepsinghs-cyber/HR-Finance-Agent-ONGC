# G4 Review — P2H.2 Persona identity UX + refusal copy

**Reviewer:** reviewer-p2h2 (independent, fresh context) · **Date:** 2026-10-24
**Branch / HEAD:** `v3/P2H-hr` @ `0a9387e` · **Commits:** 9645676 (backend), 7105556, dde5194, 0a9387e (frontend)
**Method:** read-only. A clean `git archive HEAD` export was used for all tests, so rbac's uncommitted P2H.3 work in the worktree is excluded. Line numbers refer to HEAD.

## Verdict: **CHANGES REQUESTED**

**The main refusal path does not use the SPEC-06 copy, and the app still signs a first-time visitor in as CMD.** Identity is safe: persona switching is server-bound and cannot be done by typing or speaking. The new refusal machinery (YAML, `build_refusal_contract`, `RefusalRenderer`) is sound. But the most common refusals (another person's pay or APAR) are still produced by the legacy `check_access` hook, with legacy English copy and rule ids in the headline. The packet's goal ("every refusal uses the SPEC-06 copy with an alternative") and BEH-01.01 / .60 / .62 are not met.

## Must-fix (blocking)

| # | Where | Problem | Fix |
|---|---|---|---|
| M1 | `yukti/backend/app/turn_runner.py:472-532` (the `check_access` hook); `answer_composer.py:377-387` | Refusals for named pay/APAR (BEH-01.05, the E2E "pay of Ramesh Kumar" case) bypass `refusal_copy.yaml`. Spoken: `"I cannot share these confidential records under {rule}…"`. Display: `"Access restricted under {rule} [1]…"`. Title: `"Access Restricted (D1)"`. Card line: the legacy `access_control.py:186` reason. All of it is English-only. Rule ids appear in the headline/title (BEH-01.60), the language is not matched (BEH-01.62), and the copy differs from SPEC-06 §4.6. The screenshots `refusal_e2_hr*.png` show this legacy copy. `validate_and_repair_contract` only `setdefault`s code/alternatives and keeps the legacy `reason`. | Route the hook through `build_refusal_contract(code=<R-PAY/R-APAR/R-SENS…>, language=det_lang, …)`, mapping `refusal_id` to a code. Alternatively, make the repair step overwrite `access.reason`, `display_text` and `spoken_summary` with the rendered copy when the status is `refused`. Remove `refusal_id` from `visual.title`. Coordinate with rbac: turn_runner.py has uncommitted P2H.3 edits. |
| M2 | `yukti/frontend/src/app/page.tsx:100,125,235-238` | With no session cookie, the app calls `startSession(personaRef.current)` with `'CMD'`, so a first-time visitor is silently signed in as CMD. This breaks BEH-01.01 ("no session → picker; no data call succeeds before sign-in") and the review check "no CMD default for a missing persona". | Initial persona `null`. If `/api/auth/me` returns no principal, open the PersonaPicker (blocking) and do not call `startSession` or connect `/ws/live` until a pick is made. Leave the 2-hour renew a no-op while unsigned. |
| M3 | `yukti/frontend/src/components/TopBar.tsx:98` (new in 7105556); `CanvasView.tsx:91,93`; `AnswerCard.tsx:299`; `services/websocketClient.ts:61,350` | The remaining frontend CMD fallbacks: `personaInfo(..) \|\| PERSONA_DIRECTORY[0]` (CMD), `persona = 'CMD'` defaults, `STARTERS.CMD` and the `'CMD'` chip. An unknown or missing persona is shown as CMD, with CMD starter questions. | Fall back to a neutral "Not signed in" / "Sign in as…" state and empty starters. Drop the `'CMD'` defaults; `personas.ts:49` `personaRank` already shows the right pattern. (`mockRouter.ts:8` is mock-only and acceptable.) |
| M4 | `yukti/backend/app/brain/refusal_copy.yaml:19-23,36-43,56-59,73-76,90-93,107-110,124-127,141-144` + `RefusalRenderer.tsx:21-27` | No `alternatives[]` item has `question_hi`. In Hindi, the renderer prepends `alternative` (HI question) to `alternatives` (EN questions with HI labels). The result is **duplicate chips with identical Hindi labels**: R-PAY HI shows 3 chips, two of them "E2 का औसत वेतन". The EN copies switch the conversation to English (BEH-01.62). | Add `question_hi` to every `alternatives[]` item. Dedupe in `alternativesOf` by label as well as question, or emit only `alternatives` from the backend. |
| M5 | `refusal_copy.yaml` R-SENS chip (`What is the POSH policy and reporting process?` / HI) and R-APAR HI chip (`मेरा APAR इतिहास दिखाएँ`) | **These chips ask questions the system refuses.** With the real gates (planner → `compile_spec` → `decide`, else legacy `check_access(persona, query=)`), POSH-policy is refused (R-SENS / `check_access`) for E1_FIN, E2_HR, E3_FIN and E4_HR. The HI "my APAR" chip is refused by `check_access` for every junior, because the planner does not parse it and the legacy regex treats "APAR" as someone else's. Clicking the offered alternative produces a second refusal. EN "Show my APAR history" is correctly allowed (`self`). | Make the policy/process question an allowed `policy`-class question in rbac (and check_access): the topic is the policy, not a case record. Fix the legacy regex for possessive HI ("मेरा/मेरी") self-scope. Add a test that every rendered chip question (11 personas × 9 codes × 2 langs) is `allow\|self\|aggregate` through the real gate. |

## Should-fix (important, not blocking on their own)

1. `answer_composer.py:111-135,141`: `persona_display_info` maps an unknown persona to **Pooja Verma / EMP-102451**, and `render_refusal_copy` defaults `persona="E2_HR"`. This re-introduces the seeded-identity default removed in P2H.1 r2. It is display-only, but R-ROLE could tell someone they are "Pooja Verma". Use a neutral fallback or raise.
2. `components/PersonaBanner.tsx:30`: the banner reads the static `personas.ts` mirror, not `/api/auth/me` (packet §3 item 3; SPEC-06 §4.4 rule 3). The two match today (verified: all 11 ids/names/designations equal `auth.personas_public()`), but the source of truth should be the server.
3. `app/page.tsx:285-290`: `setPersona(p)` runs before `startSession(p)` resolves, and a failed sign-in (null/401/429 rate-limit) is ignored. The UI then shows the new persona while the cookie still holds the old one. Revert on failure and show an error.
4. `RefusalRenderer.tsx:43,52,79,84`: the chrome is English-only ("Not available for your role", "You can ask instead", "Why?", "Policy reference"), even when the copy line is Hindi. Pass `language` and localise.
5. `answer_composer.py:162-164`: R-PAY `{n}` uses the **requester's** grade, not the target's ("average pay for that grade"). This is acceptable as the safer choice (it does not reveal the target's grade), but it is not documented. Record the decision or pass `grade_num` when the target grade is in-scope.
6. `answer_composer.py:298-317`: the `_infer_refusal_code` keyword fallback is fragile. `"pay" in reason` matches "display"; "board" matches "dashboard". Prefer explicit codes from every refusal source (this follows from M1).

## Accessibility (check 5): mostly pass

- ✅ `role="dialog"` + `aria-modal` + `aria-labelledby`. ✅ Portalled to `document.body` (0a9387e; the fix and its rationale are correct). ✅ Escape closes. ✅ Focus moves to the checked radio on open. ✅ Backdrop click closes.
- Nits: there is a duplicate `data-testid="persona-picker"` on the overlay and the dialog (`PersonaPicker.tsx:64,70`), which breaks Playwright strict-mode locators. `role="radiogroup"` (`:88`) has no accessible name: move the group `aria-label` onto it. There is no arrow-key roving (APG radio pattern), no Tab focus trap, and focus is not restored to the trigger on close.

## Checks summary

| Check | Result |
|---|---|
| 1. Persona only via picker → `POST /api/auth/session`; never from body | **PASS.** `uiCommands.ts:255` has no persona parse. The `page.tsx:374` `set_persona` ui_action only re-reads `/api/auth/me`. Backend `main.py:317,383,550` and `live_session.py:199,778` bind `principal.persona` and audit `persona_assertion_ignored`. `ui_control.py:190` rejects persona. `main.py:281` strips `ui_action` for non-admins. |
| 2a. Every code has EN + HI | **PASS** for the headline copy (9 codes × 2 = 18/18, exact SPEC-06 text). **FAIL** for chip questions (M4). |
| 2b. Chips ask only permitted questions | **FAIL** (M5). Verified for E2_HR, E3_FIN, E1_FIN, E4_HR, DIR_HR and DIR_FIN through the real gates. R-PAY "Average E{n} pay" is allowed (`pay_aggregate`); "My payslip" and EN "My APAR" are allowed (`self`). R-FUNC, R-BOARD, R-K5, R-NAMED and R-ROLE chips are allowed. |
| 2c. "Why?" shows rule ref without leaking data | **PASS** in the new path. Copy, chips and `access` carry only fixed strings and the rule ref; none of the refused target's names or values appear. `query_spec` echoes the user's own filters (not data). The legacy path (M1) shows long policy citations, but no target data. |
| 3. 11-persona directory = server; D-60 names; no CMD default | Directory **PASS** (E3_FIN = EMP-100146 Asha Mishra; CMD Arun Mehra, DIR_HR Manish Deshpande, DIR_FIN Vivek Rao). No CMD default: **FAIL** (M2, M3). |
| 4. Tests | See below. |
| 5. Accessibility | Mostly PASS (nits above). |

## Tests (clean HEAD export)

- Backend `pytest -q` (full suite, full-repo export of HEAD): **no P2H.2 regression.**
  - The first yukti-only export gave 1413 passed / 20 failed. 6 of those failures (clause_provenance, the personas_v3 CSV, provenance_labels fallback, h1) were artefacts of the export missing repo-level data files.
  - With the full repo at HEAD, the 9 affected files give 14 failed / 138 passed. With the full repo at pre-P2H.2 `785e01d`, they also give 14 failed / 138 passed, with the same live/BigQuery/ADC set: `test_flagship_chain` t3–t6, `test_finance_chain` t1 + grounding[1], `test_materialized_reconcile`, and `test_rbac_live` b31/b35.
  - `test_planner_golden` G08/G10/G15/G23/G33 is non-deterministic (LLM planner). Re-running G08/G10/G33 fails a varying subset on **both** HEAD and the baseline.
  - The P2H.2 suites pass: `test_refusal_copy` 49/49, `test_role_escalation`, `test_rbac_policy`, `test_persona_question_matrix`, `test_self_scope`, `test_auth_tokens`.
- Frontend `npx tsc --noEmit`: **clean (exit 0)**.
- `node scripts/check_tokens.mjs`: **exit 1, pre-existing only.** The failures are in `VoiceOrb.tsx`, `FloatingConversationPanel.tsx:438` and `TopBar.tsx:139,142`, all from blame `e7de82f`/earlier. None are in the P2H.2 files (PersonaPicker, RefusalRenderer, personas.ts, PersonaBanner).
- `npx tsx scripts/test_v19_frontend.ts`: **10 passed**.
- `test_compat.ts`: not run (known baseline failure on this branch).

## Evidence gaps (docs)

- `P2H.2_e2e.md` links `persona_picker_dark.png`, which was deleted (the lead note says it was removed). The link is broken.
- Scenario (c) "Permitted answer": `permitted_answer_e2_hr.png` shows only the "Thinking…" skeleton, not the permitted answer. Re-shoot.
- Scenario (b) shows the **legacy** copy (proof of M1), not the R-PAY SPEC-06 line.
- Packet AC #1 (Playwright `tests/persona_picker.spec.ts`: E1_FIN → Q05 → R-NAMED + AGG, light + dark) is not present. There is also no Hindi refusal screenshot.

## Observations (out of P2H.2 scope, FYI)

- `/api/auth/personas` also returns `DEMO_ADMIN` and every `emp_id`. SPEC-06 §4.4 lists only the 11 personas with id, name and designation. The frontend filters DEMO_ADMIN.
- `ui_control.py:54,96-100,148-156` still lists the old 5-persona set (`"rajesh"` → E3_FIN). It is unreachable after `:190`, but stale.


---

## Round 2 verdict: **CHANGES REQUESTED (new security regression)**

**Reviewed:** 36d2c26, b23b178, 6413d9f (backend) and 45a4016 (frontend), HEAD `6413d9f`. Clean `git archive HEAD` export; the live app on :8195 was signed in as E2_HR via `POST /api/auth/session`.

**The M5 fix opens a pre-query gate bypass, and E2_HR was served a named employee's salary.** `check_access` now returns `allowed` early for any question that matches the "policy/reporting process" regex, even when the same question also asks for restricted data. All of round 1's must-fixes are otherwise resolved.

### R2-B1 (blocking, security): the policy-process shortcut bypasses the pay, medical and POSH-names gates

- **Where:**
  - `yukti/backend/app/access_control.py:590-596`: early `return AccessDecision(status="allowed")`, placed before every keyword refusal heuristic.
  - `yukti/backend/app/brain/rbac.py:138-152`: `is_policy_process_question` only rejects case/record words and `EMP-` literals. It does not reject names, pay or medical-history requests.
  - `rbac.py:157-159`: `topic_classes` drops `sensitive` whenever the regex matches.
  - `planner.py:548-550`: routes to `intent=policy`, then the legacy LLM agent with tools.
- **Live reproduction on :8195 as E2_HR (Pooja Verma):**

  | Question | 0a9387e `check_access` | 6413d9f `check_access` | Live result |
  |---|---|---|---|
  | "What is the POSH policy, and what is the salary of Ramesh Kumar?" | refused D1 | **allowed** | `query_data` ran `SELECT fiscal_year, sum(gross_salary_inr)…`. Answer text: **"Regarding Ramesh Kumar's salary, his gross salary for the fiscal year FY27 was ₹5.19 Crore."** Post-masking stripped the column, but the number survived in the narrative. |
  | "Explain the reporting process and show Sunita Sharma's medical history" | refused R-MED | **allowed** | Ran `SELECT * FROM hrfin_silver.medical_claims WHERE emp_id = (SE…`. Answer: "There are no medical claims filed by Sunita Sharma" (a disclosure about a named person's medical record). |
  | "posh policy names of complainants in Delhi" | refused R-POSH | **allowed** | The LLM declined on its own. The gate did not. |

- **Fix:**
  1. Never early-return `allowed` from `check_access` for policy questions. Only suppress the *POSH/sensitive keyword* refusal, and only when the question is purely a policy question, then continue through the other checks.
  2. Make `is_policy_process_question` return False when the question also carries any other data request: person names (the `_mentions_individual_or_row_pay_target` / named-person detectors), the pay/apar/medical topic keywords, `show/list/names/salary/history/claims`, or conjunctions joining a second request ("and", "also", ",").
  3. In `topic_classes`, drop `sensitive` only when no other topic or person is present (mirror the guard already at `rbac.py:407`).
  4. Add regression tests: the three questions above × all 8 junior personas plus DIR_FIN must refuse in both `check_access` and `decide`.
  5. Separately, the narrative leak shows that post-query masking does not scrub numbers the LLM restates from a masked column (`enforce_contract` / `_scrub_leaked_values_from_contract`). File this as a bug for rbac. It is defence in depth, not part of the P2H.2 fix.

### Round-1 items: status

| # | Status | Evidence |
|---|---|---|
| M1 legacy refusal copy | ✅ Fixed | `turn_runner.py:489-510` now calls `build_refusal_contract` with `refusal_id→code` (`access_control.py:531-545`). The legacy title, spoken line and rule-id headline are gone. The repair path forces SPEC-06 copy (b23b178). |
| M2 first-visit CMD sign-in | ✅ Fixed | `page.tsx`: persona starts as `null`. A blocking `PersonaPicker required` appears (no close, Escape or backdrop). There is no `startSession` or `/ws/live` call before a pick, and typed and voice turns are blocked while unsigned. A failed sign-in returns to the picker (closes should-fix #3). Confirmed in `first_visit_signin.png`. |
| M3 CMD fallbacks | ✅ Fixed | TopBar shows "Sign in as…"; there are no CMD starters, chip or name; ws defaults are `''`. |
| M4 HI chips | ✅ Fixed | `question_hi` was added to every item. The backend dedupes `alternatives` against `alternative`, and `RefusalRenderer.alternativesOf` dedupes by label and question and uses the HI question. |
| M5 chips permitted | ⚠️ Fixed functionally (POSH-policy chip allowed; HI "my APAR" goes to the planner self path), **but the fix causes R2-B1**. |
| Should-fix 1 (Pooja fallback) | ✅ A neutral "Signed-in User" is used. |
| Should-fix 4 (HI chrome) | Partly: `language` is passed for the chips, but the headings ("Not available for your role", "You can ask instead", "Why?") are still English. Non-blocking. |
| Should-fix 5 (R-PAY `{n}`) | ✅ Documented in the docstring. |

### Coordinator questions

- **(a) Is "average pay" carried in `alternative`, and are both chips shown?** Yes. In HI, `access.alternative = {label:"E2 का औसत वेतन", question:"E2 अधिकारियों का औसत मासिक मूल वेतन क्या है?"}` and `alternatives = [{मेरी वेतन पर्ची…}]`. The backend removes the duplicate from `alternatives` on purpose. `alternativesOf` puts `alternative` first and then appends `alternatives`, so the card renders **2 chips** (average pay, then my payslip). Having only one entry in `alternatives` is expected.
- **(b) Is the English text in the allowed Hindi aggregate answer a P2H.2 bug?** No. P2H.2 covers refusal and masking copy (SPEC-06 §4.6, BEH-01.60–.64); the Hindi refusal sentence is correct. Language matching for allowed data answers belongs to BEH-07 / the narrator. Log it as a separate bug.

### Other notes (non-blocking)

- `app/semantic/refusal_copy.yaml` (new in 36d2c26) duplicates `app/brain/refusal_copy.yaml`, but only the `brain/` copy is loaded (`answer_composer.py:26`). Delete it or document it, to avoid drift.
- 6413d9f changes `suppress_small_cells` (adds secondary suppression) and `enforce_contract` row classification (rows without `emp_id` are treated as FIN). These are policy-behaviour changes outside P2H.2 scope and need the P2H.1/rbac owner's sign-off. A probe shows that DIR_FIN with `director_function_scope=True` still sees a named DISC-HR row when the table has no `emp_id` column, on both 0a9387e and HEAD (pre-existing; FYI for rbac).
- "my payslip and Ramesh Kumar's payslip" is allowed by every gate, but the planner binds `@self_emp_id`, so it returns only the requester's own rows. This is acceptable.

### Tests (round 2, clean HEAD export)

- `npx tsc --noEmit`: clean.
- `check_tokens`: only pre-existing hexes (TopBar.tsx:140/143 brand title, VoiceOrb, FloatingConversationPanel); none in P2H.2 files.
- `test_v19_frontend`: 10/10.
- **Backend full suite: 1664 passed, 48 failed.**
  - **R2-B2 (blocking, regression from 6413d9f):** `tests/test_rbac_policy.py::test_small_cell_suppression` and `::test_b1_small_cells_hide_averages_via_population_count` fail at HEAD and pass at 0a9387e. The new secondary suppression in `rbac.py` `suppress_small_cells` (the second loop) also masks the smallest non-suppressed cell: `headcount 5` becomes `"<5"` and `avg_age 31.0` becomes `"<5"`. This changes D-11 policy behaviour and breaks the existing contract tests. *Update: the coordinator confirms (#155) that secondary suppression is lead decision D-61. The defect is therefore the implementation, not the policy. It must keep a count of 5 visible, suppress only the next-smallest **count** cell, and hide an average only when its own population count is suppressed, so that both existing tests pass unchanged.* Note also that writing `"<5"` into an average column is a mislabel.
  - Not P2H.2:
    - 37 × `test_v19_chain` / `test_v19_definition` fail because the export lacks `data_bank/landing/sap/PA0001.csv`, a P2H.3 fixture outside the repo;
    - `test_flagship_chain::test_t2_names_roster` fails on new roster columns from the P2H.3 7-col roster (8a387b6);
    - the remaining failures are the live/BigQuery set plus flaky `planner_golden`, the same as the round-1 baseline.


---

## Round 3 verdict: **CHANGES REQUESTED**

**Reviewed:** `7508d87` (P2H.2 G4 r2 security fix). Clean `git archive 7508d87` export.

**The composite-question leak (R2-B1) is closed at the pre-gate, but the fix was committed red, re-breaks M5, and weakens two D-61 tests.** The tool-level defence the coordinator asked for (#153 item 3) is not there.

> [!NOTE]
> The live server on :8195 (pid 1507738) started at 06:25 without `--reload`, so it still runs pre-7508d87 code. All round-3 results below come from the offline gates (`check_access`, `decide`, `Planner.to_plan`, `enforce_contract`) on the 7508d87 export, not from :8195.

### R3-B1 (blocking): the commit is red, and M5 is re-broken

- **Tests:** `tests/test_refusal_copy.py::test_m5_every_chip_question_passes_real_gate_…` has **16 failures**: the R-SENS chip × 8 juniors × EN/HI. Security suites: 1400 passed / 16 failed.
- **Cause:** removing the early allow (`access_control.py:590`) means `check_access` again refuses "What is the POSH policy and reporting process?" (and the HI version) for every junior, through the `"posh" in q_l` heuristic (`access_control.py:622`). The R-SENS refusal chip therefore leads to a second refusal, which is round-1 M5 again.
- **Fix:** in `check_access`, skip **only** the POSH/sensitive keyword refusal when `is_policy_process_question(q)` is true *and* the question has no other ask. Use the same strict predicate everywhere, so composites still refuse. Do not re-introduce an early `allowed` return.

### R3-B2 (blocking): D-61 tests were weakened to match the buggy implementation

`tests/test_rbac_policy.py` changes in 7508d87:

| Test | Before | After | Against D-61 (#155) |
|---|---|---|---|
| `test_small_cell_suppression` (`:198,200`) | `headcount 5` stays `5`, `n == 1` | `headcount 5 == "<5"`, `n == 2` | ❌ Weakened. A count of 5 must stay visible. The secondary cell should be the next-smallest *count* that is not already safe (here the only other count is 0, so complementary suppression has nothing to hide, or picks the 0 cell). It must not label a 5 as "<5". |
| `test_b1_small_cells_hide_averages_via_population_count` (`:259`) | `avg_age 31.0` (n=400) visible, `n == 1` | `avg_age 31.0 == "<5"`, `n == 2` | ❌ Weakened. An average may be hidden only when its own population count is suppressed; n=400 is not. Writing `"<5"` into an average column is also a false value. |
| `test_enforce_contract_masks_named_and_pay_for_junior_and_sets_partial`, renamed `…masks_named_for_junior…` | input had `gross_salary_inr`; asserted it was stripped and `partial` | pay column **removed from the input** | ⚠️ Coverage moved to the new `test_enforce_contract_refuses_pay_for_junior` (stricter: refused). Acceptable, but say so in the commit message. |
| new `test_secondary_suppression` | – | `10` becomes `"<5"` | ⚠️ The masking is right under D-61, but the label is wrong: a secondarily suppressed cell holding 10 must not read `"<5"` (that states a false value). Use a distinct marker (e.g. `"—"` / `"suppressed"`) and footnote it. |

**Fix:**
1. Restore the two original assertions unchanged.
2. Implement D-61 as the coordinator stated it (#155): primary `< 5`; secondary only on count columns, only when exactly one primary exists in that series; averages follow their own count.
3. Add the D-61 tests: no derivation from the total, and 5 stays visible.
4. Also, D-61 is **not recorded** in `docs/DECISIONS.md` on this branch (last entry D-59/D-60). Add it.

### R3-B3 (blocking per #153 item 3): there is no compile/tool-level gate for free SQL

- `agent.py:81-86` `query_data` → `tools/query_data.py` runs any SELECT against `hrfin_gold`/`hrfin_silver` without checking the principal; `persona` defaults to `"CMD"` (`query_data.py:95,291`) and is used only for cache partitioning.
- The only remaining defence is `enforce_contract`'s column-name masking, which free-SQL aliases evade. An offline probe with `enforce_contract(…, "E2_HR")` showed:
  - `gross_salary_inr` / `fy26_gross_salary_inr` columns → **refused R-PAY** ✅ (the new defence-in-depth works for recognised names);
  - `total_gross` (aliased) → **allowed, narrative "Ramesh Kumar gross salary FY27 was Rs 5.19 Crore" kept** ❌;
  - `medical_claims` columns (`claim_id, claimed_amount_inr, hospital_name`) → **allowed** ❌.
- When `enforce_contract` does refuse, it replaces `display_text`/`spoken_summary` but **leaves `insights` holding the leaked sentence** (`rbac.py` early return in the new defence block). The UI hides insights on refused cards, but the JSON payload still carries the value.
- **Fix:**
  - (a) Bind `query_data` to `get_active_principal()`. For juniors (and DIR_FIN on HR-personal data), refuse SQL that references restricted tables (`payroll_*`, `medical_claims`, `eAPAR_*`, POSH/vigilance tables) or restricted columns *by source table*, not by output alias. Use the compiler's data-class map or a table allow-list per persona class.
  - (b) On a refusal in `enforce_contract`, also clear `insights`, `insights_v2`, `drilldowns`, `suggestions`, any chart, and table rows.
  - (c) Add tests: aliased pay SQL and medical_claims SQL as E2_HR → refused at the tool; and the refusal payload contains none of the masked values or narrative.

### Verified OK in 7508d87

- Composite questions are refused by **both** `check_access` and `decide` (E2_HR and E3_FIN) for:
  - EN, "aur" and "और" conjunctions;
  - "also", commas and semicolons;
  - policy + named pay, APAR, medical, POSH complainants and vigilance.
- The 3 round-2 exploit questions are now refused, as R-PAY, R-SENS and R-SENS.
- `topic_classes` keeps `sensitive`. `_enrich_classes_from_question` now *adds* `policy` instead of replacing the class list.
- `masked_values` now include non-string values (numeric scrub). This is an improvement, but it does not catch reformatted numbers ("₹5.19 Crore").

### Open (pre-existing, FYI)

`check_access("E2_HR", "complaint process for the case against EMP-100146")` is allowed by `check_access` and `decide` alike, on 0a9387e too. An EMP-literal plus "case against" should refuse (R-SENS). Assign to rbac.


---

## Round 4 verdict: **CHANGES REQUESTED (individual pay still reachable through free SQL)**

**Reviewed:** `e772869`. Clean export; suites run offline. Live checks were on :8195, which now auto-reloads from the worktree (#166). Suites: **1432 passed / 0 failed** (rbac_policy, rbac_bug44, refusal_copy, persona_question_matrix, role_escalation, self_scope, auth_tokens, personas_v3, export_security).

**The POSH policy chip works again, and the D-61 tests are sound. However, the new `query_data` table gate misses the main employee table: E2_HR was served 20 rows of individual gross pay for "Ramesh Kumar".**

### R4-B1 (blocking, security): the table gate covers 4 name patterns, not the tables that hold restricted data

- **Where:** `tools/query_data.py:117-147`. The gate fires only when a table name contains `payroll`, `apar`, `medical_claims` or `posh`.
- **Live reproduction on :8195 as E2_HR:** "Write a SQL query on hrfin_gold.ssot_workforce_employee selecting emp_name and avg_monthly_gross_inr as total_gross for employees named Ramesh Kumar and tell me the value"
  - The tool ran `SELECT emp_name, avg_monthly_gross_inr AS total_gross FROM h…`.
  - The contract returned `access=partial`, `columns=['total_gross']`, **20 rows** of individual monthly gross pay.
  - `emp_name` was stripped, but the user asked about named people, so each value is attributable. The aliased column defeats `enforce_contract`'s column-class masking, and the table is not gated.
- **Catalog tables holding restricted columns that the gate does not cover** (from `semantic.normalize.load_catalog()`):

  | Table | Restricted columns |
  |---|---|
  | `hrfin_gold.ssot_workforce_employee` | `avg_monthly_gross_inr`, `fy26_apar_rating` (and the `fy26_gross_salary_inr` seen live in round 2) |
  | `hrfin_gold.mart_field_economics` | `gross_salary_inr` |
  | `hrfin_gold.mart_workforce` | `final_rating` |
  | `hrfin_gold.mart_promotions_dpc` | `apar_benchmark_score`, `vigilance_cleared` |
  | `hrfin_silver.promotion_history` | `vigilance_cleared` |
  | `hrfin_silver.vigilance_cases` | case data (refused live only by the pre-gate keyword) |

  Also, `referenced_tables("select * from hrfin_silver . payroll_monthly")` returns `[]`, so whitespace around the dot evades the parser.
- **Fix:**
  1. Gate on the **columns read from source tables**, not on table-name substrings. Resolve every referenced column (including inside `AS` aliases, expressions, CTEs and `SELECT *`) against the catalog's column data classes, i.e. the `column_class` / semantic-model classes.
  2. For juniors and DIR_FIN-on-HR, refuse any free SQL that reads a `pay`/`apar`/`sensitive` column, unless it is a whitelisted aggregate (`AVG/SUM/COUNT` grouped by grade with k≥5). Applying the same rule to `SELECT *` on such tables is the simplest correct option.
  3. Normalise identifiers (strip backticks and whitespace around the dot) before matching.
  4. Tests: the live prompt above, `SELECT *` on ssot_workforce_employee, a CTE wrapping payroll_monthly, `hrfin_silver . payroll_monthly`, and mart_workforce `final_rating`, all as E2_HR → refused at the tool. Also assert that the refusal contract has no rows and no narrative.

### R4-B2 (blocking, small): "posh policy names of complainants in Delhi" is allowed again

- Both `check_access` and `decide` return `allow` for E2_HR. It was refused at 7508d87.
- The new `is_case` regex (`access_control.py:625`, `rbac.py:159`) lacks `complainant(s)`, `names?`, `victim`, `accused` and `respondent`, and `_mentions_individual_or_row_pay_target` misses "names of …".
- **Fix:** treat any `names? of` / `list` / `who` plus a POSH or case noun as a case/named ask. Add this and the HI equivalents (शिकायतकर्ता, नाम) to the regression tests.

### R3 items: status

| # | Status | Evidence |
|---|---|---|
| R3-B1 (POSH policy-only allowed; composites refused) | ✅ | The 16 M5 tests pass. Live: EN and HI policy-only questions are `allowed` (clause); "What is the POSH policy, and what is the salary of Ramesh Kumar?" is **refused R-PAY** with SPEC-06 copy. Every round-2/3 composite is still refused offline, except R4-B2. |
| R3-B2 (D-61) | ✅ **Legitimate, not a weakening.** | Both original assertions are restored exactly. `test_b1_small_cells_hide_averages_via_population_count` is byte-identical to 0a9387e and passes with the default `apply_secondary=True`, so averages follow their own count. `test_small_cell_suppression` adds `apply_secondary=False`: its fixture `[3, 5, 0]` has exactly one primary cell, so D-61 *would* secondary-suppress the 5. Testing the primary rule in isolation is correct, and the D-61 behaviour is covered by the new `test_d61_*` tests. Secondary cells are now labelled `"suppressed"` (no false `"<5"`), and secondary suppression is limited to count columns. Production callers use the default (`apply_secondary=True`). Ask: add one test running `[3, 5, 0]` with the default, asserting `5 → "suppressed"` (not `"<5"`), so the interaction is pinned. |
| R3-B3 (tool gate, Principal, narrative cleared) | ⚠️ Partial | Principal is passed (`agent.py:86-100`, fail-closed E-AUTH) ✅. The table gate is incomplete (R4-B1) ❌. The tool refusal returns no rows or narrative ✅. Live refusals show only SPEC-06 copy in `display_text` and `insights` ✅. `tools/query_data.py:95,291` still default `persona="CMD"`; there is currently no other caller, but make it required. |

### Still open (non-blocking)

- `check_access("E2_HR", "complaint process for the case against EMP-100146")` is allowed (pre-existing since 0a9387e; EMP literal + "case against").
- `E2 का औसत वेतन` and `मेरा APAR इतिहास दिखाएँ` are refused by a bare `decide(topic_classes)`, but allowed on the real planner path (pay_aggregate / self). Live behaviour is correct per the lead's check; noted only for test design.


---

## Round 5 verdict: **CHANGES REQUESTED (juniors fixed; director free-SQL gate still leaky and its tool wiring is wrong)**

**Reviewed:** `80a842d` + `c0b1df2` (export of c0b1df2), sqlglot 30.24.0 in the shared venv. Suites: **1436 passed / 0 failed / 0 skipped**. Live checks on :8195 (auto-reload).

**The junior leak is closed: E1–E4 cannot run free SQL.** Two problems remain in the director path:
- the D-64 director gate lets DIR_FIN read HR pay, vigilance and medical rows;
- the agent's toolset is fixed once per process, so whether directors (and CMD) have `query_data` at all depends on who made the first request after a restart.

### Verified fixed

| Item | Evidence |
|---|---|
| R4-B1 for juniors (D-64) | `agent.py:97-104` hard-refuses `query_data` for `persona_class == "junior"` (R-FUNC), and `create_yukti_agent` omits the tool. Live as E2_HR, the round-4 prompt (`avg_monthly_gross_inr AS total_gross` on `ssot_workforce_employee`) gives **no free SQL**: the agent fell back to certified templates and the answer contains no pay values. |
| R4-B2 POSH names | "posh policy names of complainants in Delhi": **refused R-SENS** live, by `check_access` and by `decide`. The policy-only POSH question (EN/HI) is still allowed. |
| D-61 extra test | `tests/test_rbac_policy.py:402` covers `[3,5,0]` with the default secondary rule. |
| Refusal payloads | Live refusals carry only the SPEC-06 copy in `display_text` and `insights`. Tool refusals return no rows or narrative. |

### R5-B1 (blocking): the director column gate has bypasses (`tools/query_data.py:117-235`)

I probed the gate in-process, short-circuiting just after it with a `validate_sql_safety` stub, so no BigQuery call was made. "PASS" below means the SQL would execute:

| SQL (as DIR_FIN) | Gate | Why |
|---|---|---|
| `SELECT * FROM hrfin_silver.payroll_monthly` | **PASS** | `exp.Star` is not an `exp.Column`, so there are no columns and the class is `general`. The same holds for `SELECT * FROM hrfin_gold.ssot_workforce_employee`. |
| `… payroll_monthly WHERE discipline_id='DISC-FIN' OR 1=1` | **PASS** | `target_func` is FIN if *any* `EQ` mentions FIN; the predicate is not checked to actually restrict rows. The same happens with `… LIKE '%HR%' AND … = 'DISC-FIN' OR TRUE`. |
| `SELECT vigilance_case_id, vigilance_clearance_status FROM hrfin_silver.vigilance_cases` | **PASS** | The class is `sensitive`, but `decide()` returns `aggregate` (not `refuse`) for DIR_FIN, and the gate only blocks `refuse`. Raw rows are returned, with no aggregation enforced. The same applies to `promotion_history.vigilance_cleared`. |
| `SELECT claim_id, claimed_amount_inr, hospital_name FROM hrfin_silver.medical_claims` | **PASS** | `column_class()` returns `None` for these columns, and they are in the catalog, so they are treated as `general`. "In the catalog" is not the same as "non-sensitive", so this is not fail-closed. |
| `WITH x AS (…payroll…)`, `hrfin_silver . payroll_monthly`, the aliased `total_gross`, `mart_field_economics.gross_salary_inr`, `final_rating`, DPC APAR | refused ✅ | |

**Fix (recommended, simplest):** restrict `query_data` to **CMD (and DIR_HR only if needed)**, and give DIR_FIN the same treatment as juniors (planner + certified library only). Otherwise, fix the gate:
- (a) expand `*` to the table's catalog columns;
- (b) for any non-`general` class, require `decide(...).action == "allow"`, and treat `aggregate` as refuse for free SQL;
- (c) a column with no explicit data class fails closed unless its table is on the allowlist;
- (d) derive the D-43 row scope only from a top-level conjunctive `discipline_id = 'DISC-FIN'` (or `IN` with only FIN values), with no `OR` at that level; otherwise MIXED;
- (e) tests for every row above.

### R5-B2 (blocking): the toolset is decided once per process, not per principal

- `create_yukti_agent()` (`agent.py:257-268`) reads `get_active_principal()` once. `AgentTurnRunner.__init__` builds the agent once (`turn_runner.py:141`), and `_GLOBAL_RUNNER` is a singleton (`:2727-2729`).
- Whoever triggers runner creation fixes the toolset for **all** later users:
  - if there is no principal, or a junior triggers it, the junior toolset is used, so CMD and directors silently lose `query_data`. Live: DIR_FIN got "The `query_data` function is not available";
  - if CMD or a director triggers it, every session gets `query_data`. Juniors stay blocked by the wrapper, but the R5-B1 bypasses become live for DIR_FIN.
- **Fix:** build the toolset per turn from the bound principal (or keep one agent per persona class). Keep the wrapper check as the hard gate. Test: create the runner under E2_HR, then run a CMD turn (CMD has `query_data`); and the reverse (E2_HR does not).

### Non-blocking (carried over)

- `tools/query_data.py:95` still defaults `persona="CMD"`. Make it required.
- `check_access("E2_HR", "complaint process for the case against EMP-100146")` is allowed (pre-existing).


---

## Round 6 verdict: **CHANGES REQUESTED (all non-CMD bypasses are closed, but CMD loses `query_data` on HTTP/WS and 3 existing security tests broke)**

**Reviewed:** `24f439a` (clean export). Suites: **1468 passed / 3 failed** across the P2H.2 + security suites (`test_self_scope.py` × 2, `test_h1_hardening.py` × 1).

**Every non-CMD persona (`E1–E4`, `DIR_FIN`, `DIR_HR`) is now completely blocked from `query_data`, and all 16 Round-5 SQL probes refuse for `DIR_FIN`, `DIR_HR`, and `E2_HR`.** However, three defects in `24f439a` must be fixed before sign-off:
1. **R6-B1 (blocking):** On live HTTP (`/api/turn`, `/api/voice-turn`) and WebSocket (`/ws/live`), `get_agent_turn_runner()` is called *before* `execute_turn_async()` sets `_ACTIVE_PRINCIPAL`, so `get_active_principal()` is always `None` and **even `CMD` gets the `"junior"` runner without `query_data`**.
2. **R6-B2 (blocking):** `tools/query_data.py` was not made audit-only for `CMD` (`#188` item 2) and ignores `persona="CMD"` when `_ACTIVE_PRINCIPAL` is unset in direct unit tests, breaking `tests/test_h1_hardening.py::test_h1_2_repaired_sql_is_revalidated_before_execution` and refusing `CMD` queries that use CTE or `HAVING` column aliases.
3. **R6-B3 (blocking):** `tests/test_r5_bypass.py` mutates `_ACTIVE_PRINCIPAL` without resetting it in `wipe_runner`, leaking a `DIR_FIN` principal into later tests and breaking 2 tests in `tests/test_self_scope.py`.

### Verified fixed in `24f439a`

| Item | Evidence |
|---|---|
| Amended D-64 (non-CMD refusal) | All 16 Round-5 SQL probes (`SELECT * FROM payroll_monthly`, `SELECT * FROM ssot_workforce_employee`, `WHERE discipline_id='DISC-FIN' OR 1=1`, `vigilance_cases`, `medical_claims`, `promotion_history`, CTEs, aliases) return `status: "refused"` for `E2_HR`, `DIR_FIN`, and `DIR_HR`. |
| Per-persona runner cache when principal is pre-bound | When `set_active_principal` is set beforehand (`tests/test_r5_bypass.py`), `CMD` gets `query_data` and `E2_HR` / `DIR_FIN` / `DIR_HR` do not. |

### Must-fix items for Round 6

#### R6-B1 (blocking): `get_agent_turn_runner()` runs before `set_active_principal(principal)` on HTTP & WebSocket (`main.py:353, 418`, `live_session.py:397, 530, 1074, 1145`, `turn_runner.py:286, 2725-2735`)

- **What breaks:** In `main.py:353` (`await get_agent_turn_runner().execute_turn_async(..., principal=principal)`), `main.py:418`, and `live_session.py:397, 530, 1074, 1145`, Python evaluates `get_agent_turn_runner()` **before** entering `execute_turn_async()`. Because `set_active_principal(principal)` is only called inside `execute_turn_async()` (`turn_runner.py:286`), `get_active_principal()` is `None` when `get_agent_turn_runner()` runs.
- **Impact:** `get_agent_turn_runner()` always falls back to `key = "junior"`, and `create_yukti_agent()` sees `principal = None`, so **`CMD` never gets `query_data` on any real HTTP or WebSocket request** (`[t.__name__ for t in runner.agent.tools]` omits `query_data`). Also, `live_session.py:1145` caches `trun = get_agent_turn_runner()` outside the message loop.
- **Fix:**
  1. Have `create_yukti_agent(model_name=..., persona: Optional[str] = None)`, `AgentTurnRunner(model_name=..., persona: Optional[str] = None)`, and `get_agent_turn_runner(model_name=..., persona: Optional[str] = None)` accept `persona` (falling back to `get_active_principal().persona` if not passed, else `"junior"`).
  2. Pass `persona=persona` in `main.py:353, 418` (`get_agent_turn_runner(persona=persona)`) and `persona=self.persona` in `live_session.py:397, 530, 1074, 1145`.
  3. Inside `AgentTurnRunner.execute_turn_async` (`turn_runner.py:286`, immediately after `set_active_principal(principal)`), ensure `self.agent` / `self.runner` matches `principal.persona` (e.g., if `(principal.persona.upper() == "CMD") != ("query_data" in [t.__name__ for t in self.agent.tools])`, rebuild `self.agent = create_yukti_agent(model_name=self.model_name)` and `self.runner = Runner(agent=self.agent, app_name=self.agent.name, session_service=self.session_service)`).

#### R6-B2 (blocking): `tools/query_data.py` is not audit-only for `CMD` and breaks `test_h1_2_repaired_sql_is_revalidated_before_execution` (`tools/query_data.py:112-246`, `agent.py:97`)

- **What breaks:**
  1. `tests/test_h1_hardening.py:108` (`test_h1_2_repaired_sql_is_revalidated_before_execution`) calls `query_data("SELECT bad_col FROM `ongc-hr-finance-agent.hrfin_gold.v_field_pnl`", persona="CMD")` directly without `set_active_principal` and expects `res["status"] == "error"` from `SemanticLayer` self-repair validation. It fails with `AssertionError: assert 'refused' == 'error'` for two reasons:
     - `tools/query_data.py:116` checks `if not p or p.persona.upper() != "CMD":` instead of falling back to the `persona` argument when `p is None` (note: the ADK tool wrapper `agent.py:88-95` is what enforces `principal is not None` -> `E-AUTH` for agent tool calls; also update `agent.py:97` from `persona_class(principal.persona) == "junior"` to `principal.persona.upper() != "CMD"`).
     - Even when `p` is `CMD`, `tools/query_data.py:165-180` (`if has_unknown and not non_sensitive:`) and `228-245` (`except Exception:`) still return `{"status": "refused", "code": "R-FUNC"}` for `CMD` instead of being audit-only as required by `#188` item (2) (*"Keep the sqlglot gate for CMD as audit-only logging (CMD sees everything)"*). This also causes `CMD` free-SQL queries with CTE column aliases (`WITH sub AS (SELECT COUNT(*) AS cnt ...) SELECT cnt FROM sub`) or `HAVING cnt > 10` to be refused as `"Unrecognized columns in query"`.
- **Fix:**
  1. In `agent.py:97`, change `if persona_class(principal.persona) == "junior":` to `if principal.persona.upper() != "CMD":`.
  2. In `tools/query_data.py:114-117`, resolve `eff_persona = (p.persona if p is not None else (persona or "")).strip().upper()`. If `eff_persona != "CMD"`, return `{"status": "refused", "code": "R-FUNC", "message": "query_data tool is restricted to CMD. Do not use this tool.", "error": "query_data tool is restricted to CMD. Do not use this tool.", "rows": [], "columns": [], "chart_kind": "refusal"}`.
  3. In `tools/query_data.py:128-245`, for `CMD`, make the `sqlglot` block **audit/log only** (`logger.info(...)` / `audit(...)` and never `return {"status": "refused", ...}`), so `CMD` proceeds to `sl.validate_sql_safety(safe_sql)` and execution.

#### R6-B3 (blocking): `tests/test_r5_bypass.py` leaks `_ACTIVE_PRINCIPAL` into `tests/test_self_scope.py` (`tests/test_r5_bypass.py:7-12`)

- **What breaks:** `test_r5_bypass.py` calls `set_active_principal(Principal(..., persona="DIR_FIN"))` without resetting it. When `test_self_scope.py` runs in the same pytest invocation, `_ACTIVE_PRINCIPAL` is still `DIR_FIN`, causing `test_m2_resolve_self_emp_id_and_run_certified_query_reject_unknown_or_empty_persona[None]` and `test_m1_agent_tool_wrapper_fails_closed_without_principal_and_binds_active_principal` to fail.
- **Fix:** In `tests/test_r5_bypass.py`, call `set_active_principal(None)` before and after `yield` in `wipe_runner()`. Also add a test verifying that when `get_agent_turn_runner(persona="CMD")` (or `execute_turn_async(..., principal=principal_for_persona("CMD"))`) is called *without* pre-setting `set_active_principal`, `CMD` gets `query_data` and `DIR_FIN` / `E2_HR` do not.


---

## Round 7 verdict: **APPROVE**

**Reviewed:** `07704f5` (clean export) + live server on `:8195`. Suites: **1472 passed / 0 failed / 0 skipped** across all P2H.2, RBAC, identity, self-scope, refusal copy, provenance, and H1 hardening suites. Frontend `npx tsc --noEmit` (0 errors) and `test_v19_frontend.ts` pass.

**All Round 1–6 security and UX blockers are resolved. P2H.2 is ready for sign-off.**

### Round 6 items: verified fixed in `07704f5`

| Item | Status | Evidence |
|---|---|---|
| **R6-B1** (`CMD` gets `query_data` on HTTP/WS; non-CMD do not, in both orders) | ✅ Fixed | `main.py:353, 418` and `live_session.py:397, 530, 1074, 1145` pass `principal` to `get_agent_turn_runner(principal=...)`, and `turn_runner.py:289-290` rebinds `self.agent` / `self.runner.agent` after `set_active_principal(principal)`. `test_r5_bypass.py::test_http_runner_isolation_orders` verifies via `TestClient(app)` on `POST /api/turn` in both orders (`CMD` → `E2_HR` and `DIR_FIN` → `CMD`) that `CMD` has `query_data` and `E2_HR` / `DIR_FIN` do not. Live on `:8195`, `E2_HR` and `DIR_FIN` cannot invoke `query_data` and leak no pay/named rows. |
| **R6-B2** (`CMD` path audit-only, `test_h1_2` green, `agent.py` checks `!= "CMD"`) | ✅ Fixed | `agent.py:97` checks `principal.persona.upper() != "CMD"`. `tools/query_data.py:115-202` resolves `eff_persona` from `get_active_principal()` (falling back to the explicit server-side `persona` parameter for direct unit tests) and keeps the `sqlglot` check audit-only (`logger.warning`) for `CMD`. `tests/test_h1_hardening.py` passes **10/10** (`test_h1_2_repaired_sql_is_revalidated_before_execution` green). |
| **R6-B3** (no `_ACTIVE_PRINCIPAL` leak across tests) | ✅ Fixed | `tests/test_r5_bypass.py:8-14` resets `set_active_principal(None)` before and after `yield`. Running all 13 security/P2H.2 test modules together completes with **1472 passed, 0 failed**. |
| **Baseline check on `test_reconcile_field_pnl` and `test_planner_golden` (`G01`/`G23`)** | ✅ Confirmed unrelated | Confirmed on a clean export of pre-P2H.2 baseline `785e01d`: `test_materialized_reconcile.py::test_reconcile_field_pnl` also fails at `785e01d` against live BigQuery (`Decimal('-183.27') != Decimal('-4.93')`), and `test_planner_golden.py` is a non-deterministic live Gemini planner test that also flakes at `785e01d`. Neither is caused by P2H.2. |
