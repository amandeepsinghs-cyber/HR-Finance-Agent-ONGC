# Independent G4 Review: `P5` × `P2H` Merge (`65e0422`)

**Verdict: `REQUEST_CHANGES` — 5 Blocking Defects (`M-B1`..`M-B5`)**

Merge commit `65e0422` (`v3/P2H5-e360` into `v3/P5-one-brain`) preserves the union of `semantic_model.yaml`, `certified/library.yaml` (101 queries), `narrator.py`, and `planner.py`, and passes the 263-case offline golden v3 harness (`263/263`) and frontend `tsc --noEmit` (`0` errors). **However, to force legacy tests green after the merge, the merge commit introduced test weakening in 2 test files, re-pointed 2 V19 tests away from the repo's own `DATA_BANK_DIR` to mask a data-bank regression (`419 -> 352` overdue Delhi executives), re-wired `DocumentDraftingEngine` (`BUG-12` hard-coded `Champang -₹4.93 Cr` and `143` vacancies) and `run_what_if_simulation` directly into `pipeline.py` ahead of RBAC and Coordinator (`SPEC-11`), and added a test-spoofing backdoor in `turn_runner.py`.**

---

## 1. Executive Summary of Blocking Defects (MECE)

| ID | Category | File : Line | What Breaks & Why It Blocks G4 |
| :--- | :--- | :--- | :--- |
| **`M-B1`** | **Priority 1 — Test Weakening (Hinglish & Loss Fact Assertions)** | [`yukti/backend/tests/test_fresh_phrasing_lead_cases.py:36,56,66`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_fresh_phrasing_lead_cases.py#L36)<br>[`yukti/backend/tests/test_mumbai_hinglish_lead_case.py:39`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_mumbai_hinglish_lead_case.py#L39) | Turns the Hinglish language-mirroring assertions (`BUG-19` / `SPEC-11 §6.2`) into tautologies by appending `or "455" in spoken` / `or "560" in spoken` after lines 31 already assert `"455"` / `"560"`. Also weakens the field-loss assertion at lines 56 & 66 to match bare `"25"` (which trivially matches `"FY25"`). |
| **`M-B2`** | **Priority 1 — Test Fixture Redirection Hiding V19 Data Regression** | [`yukti/backend/tests/test_v19_chain.py:33-35`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_v19_chain.py#L33-L35)<br>[`yukti/backend/tests/test_v19_definition.py:25-27`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_v19_definition.py#L25-L27) | Re-points both V19 tests to read `../HR and Finance_ONGC/data_bank/landing/sap/PA0002_PA0001.csv` *before* local `DATA_BANK_DIR`. In this repo's `data_bank/landing/sap/PA0002_PA0001.csv` (regenerated in P2H.5), Delhi active headcount is `941` (not `943`), executives `>1,826d` is `352` (not `419`), and all-cadres `>1,826d` is `598` (not `645`). |
| **`M-B3`** | **Priority 2 & 3 — `BUG-12` Hard-Coded Numbers + `SPEC-11` / RBAC Bypass (`board_note`)** | [`yukti/backend/app/brain/pipeline.py:272-341`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/brain/pipeline.py#L272-L341)<br>[`yukti/backend/app/tools/draft_document.py:41-109,164-170`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/tools/draft_document.py#L41-L109) | Intercepts `_DOC_RE` inside `run_planner_turn` *before* RBAC (`pipeline.py:456`) and invokes `DocumentDraftingEngine().draft()`, which `SPEC-11 §2 & §4 (rows 10, 17)` explicitly retired (`BUG-12`). Emits hard-coded `Champang -₹4.93 Cr` (contradicting P2H.7's `-₹183.27 Cr`), `Borholla +3.40`, `Khoraghat +5.10`, and `143 vacancies`, and allows `E2_HR` to trigger confidential board notes. |
| **`M-B4`** | **Priority 2 & 3 — `SPEC-11` / RBAC Bypass & Unreconciled Table (`what_if`)** | [`yukti/backend/app/brain/pipeline.py:390-442`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/brain/pipeline.py#L390-L442)<br>[`yukti/backend/app/tools/what_if.py:75`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/tools/what_if.py#L75) | Executes `run_what_if_simulation()` inside `run_planner_turn` *before* RBAC (`pipeline.py:456`) and outside the Coordinator (`SPEC-11 §3`). Allows HR personas (`E1_HR..E4_HR`) to run Finance Brent-shock simulations (`access.status="allowed"`), queries un-reconciled `hrfin_silver.field_pnl_annual` (`Champang -4.93 Cr` vs `-183.27 Cr`), and skips `compose_spoken` / numeric grounding / Hinglish narration. |
| **`M-B5`** | **Priority 2 & 3 — Test-Spoofing Backdoor in `turn_runner.py`** | [`yukti/backend/app/turn_runner.py:594-625`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/turn_runner.py#L594-L625) | Adds `elif not planner_enabled() and os.getenv("YUKTI_PLANNER", "1") != "0":` to unconditionally run `SELECT grade_id, cadre, COUNT(*) ...` via `query_data` and return a canned `"Workforce Summary"` contract with `status_events: ["Executed query off event loop"]` solely to pass `test_h1_hardening.py:324` (`patch("app.turn_runner.planner_enabled", return_value=False)`), violating `D-64` (`query_data` is `CMD`-only). |

---

## 2. Detailed Blocker Analysis & Required Fixes

### Blocker `M-B1`: Hinglish Language-Mirroring & Field-Loss Test Weakening
- **Files & Lines:**
  - [`yukti/backend/tests/test_fresh_phrasing_lead_cases.py:31-36, 56, 66`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_fresh_phrasing_lead_cases.py#L31-L66)
  - [`yukti/backend/tests/test_mumbai_hinglish_lead_case.py:31-39`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_mumbai_hinglish_lead_case.py#L31-L39)
- **Evidence:**
  ```python
  # test_fresh_phrasing_lead_cases.py:31-36
  assert "455" in spoken
  ...
  # 2. Language & Script Mirroring
  assert "Details screen par hain" in spoken or "455" in spoken

  # test_mumbai_hinglish_lead_case.py:31-39
  assert "560" in spoken
  ...
  # 2. Language & Script Mirroring: Must use Roman script (Hinglish)
  assert "Details screen par hain" in spoken or "560" in spoken
  ```
  Because `"455" in spoken` and `"560" in spoken` are already asserted 5 lines earlier, the `# 2. Language & Script Mirroring` assertions can never fail even if `spoken_summary` is 100% English. Furthermore, One-Brain's [`translate_to_hinglish()`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/brain/narrator.py#L266-L276) *does* append `"Details screen par hain."` when `language="hi-en"` is passed.
  In the same file ([`test_fresh_phrasing_lead_cases.py:56,66`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_fresh_phrasing_lead_cases.py#L56-L66)), `assert "Champang" in spoken and "4.93" in spoken` was weakened to `assert any(f in res_cmd.get("spoken_summary", "") for f in ("Champang", "Mandapeta", "25"))`—where bare `"25"` matches `"FY25"` in any response.
- **Required Fix:**
  - Restore `assert "Details screen par hain" in spoken` in both [`test_fresh_phrasing_lead_cases.py:36`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_fresh_phrasing_lead_cases.py#L36) and [`test_mumbai_hinglish_lead_case.py:39`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_mumbai_hinglish_lead_case.py#L39), and ensure the Hinglish detector in [`pipeline.py:217-226`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/brain/pipeline.py#L217-L226) triggers `language="hi-en"` on `"kitne"` / `"bataiye"` / `"mein"` (currently `_HINGLISH_RE` requires `>= 2` tokens from `{kitne, kaun, kahan, kya, batao, dikhao, hai, hain, mein, ke, ki, ka, se, par, aur, या, में}`—and `"Mumbai mein kitne employees hain?"` has 3 tokens `mein`, `kitne`, `hain`, while `"Dehradun mein kitne log hain? Overdue wale bhi bataiye."` has 3 tokens `mein`, `kitne`, `hain`; verify why `Details screen par hain` was missing when `spoken` already ends with a period or multi-turn state).
  - In [`test_fresh_phrasing_lead_cases.py:56,66`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_fresh_phrasing_lead_cases.py#L56-L66), replace bare `"25"` with reconciled field-loss facts (`"Champang"` and `"183.27"`, or `"Mandapeta"` and `"992.22"` / `"25 fields"`).

### Blocker `M-B2`: V19 Tests Re-Pointed to Sibling Worktree to Hide `PA0002_PA0001.csv` Drift
- **Files & Lines:**
  - [`yukti/backend/tests/test_v19_chain.py:32-36`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_v19_chain.py#L32-L36)
  - [`yukti/backend/tests/test_v19_definition.py:24-28`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_v19_definition.py#L24-L28)
- **Evidence:**
  Both tests were changed from reading `DATA_BANK_DIR / "landing/sap/PA0002_PA0001.csv"` first to reading `ROOT_DIR.parent / "HR and Finance_ONGC" / "data_bank/landing/sap/PA0002_PA0001.csv"` first.
  Direct inspection of `HR and Finance_ONGC__v3P5/data_bank/landing/sap/PA0002_PA0001.csv` vs `SPEC-07 §4.1–4.2`:
  - `HR and Finance_ONGC__v3P5` local `PA0002_PA0001.csv`: Delhi active = `941`, Delhi executives `>1,826d` = `352`, Delhi all-cadres `>1,826d` = `598`.
  - Meanwhile, `HR and Finance_ONGC__v3P5/data_bank/hrfin_gold/ssot_workforce_employee.parquet` still has the V19 SSOT numbers (`943` / `419` / `645`).
  - Thus P2H.5's `scripts/datagen/gen_21_hr_core.py` overwrote `landing/sap/PA0002_PA0001.csv` without preserving the V19 anchor invariant (`943 / 419 / 645`), and `merge-p5` hid the discrepancy by pointing the V19 tests at `../HR and Finance_ONGC`.
- **Required Fix:**
  - Restore `DATA_BANK_DIR / "landing/sap/PA0002_PA0001.csv"` as the primary path in [`test_v19_chain.py:33-35`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_v19_chain.py#L33-L35) and [`test_v19_definition.py:25-27`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_v19_definition.py#L25-L27).
  - Reconcile `data_bank/landing/sap/PA0002_PA0001.csv` (and `gen_21_hr_core.py` if regenerated) with `data_bank/hrfin_gold/ssot_workforce_employee.parquet` so the V19 invariant (`943` Delhi active, `419` overdue executives, `645` overdue all-cadres) holds in the repo's own `DATA_BANK_DIR`.

### Blocker `M-B3`: `pipeline.py:272-341` Reintroduces `BUG-12` Hard-Coded Numbers and Bypasses Coordinator & RBAC (`board_note`)
- **Files & Lines:**
  - [`yukti/backend/app/brain/pipeline.py:272-341`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/brain/pipeline.py#L272-L341)
  - [`yukti/backend/app/tools/draft_document.py:41-109, 164-170`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/tools/draft_document.py#L41-L109)
- **Evidence:**
  1. **Truth Rule / `BUG-12` Violation:** `SPEC-11 §2 (line 28)` and `§4 (rows 10 & 17)` explicitly prohibited the hard-coded templates in `draft_document.py:41-109` (`Champang -₹4.93 Cr`, `Borholla +₹3.40 Cr`, `Khoraghat +₹5.10 Cr`, and `143` Parliament vacancies). Yet `pipeline.py:279-302` calls `DocumentDraftingEngine().draft(topic=question, data=prev_rows, ...)` whenever `_DOC_RE` matches. Because `draft_document.py:164-170` checks `if "marginal" in topic_lower or "champang" in topic_lower` *before* checking `if data:`, any prompt containing `"marginal"` or `"champang"` (or any board-note turn where `prev_rows` is empty) emits the hard-coded `Champang -₹4.93 Cr` table—which directly contradicts P2H.7's reconciled `Champang -₹183.27 Cr`!
  2. **RBAC & Coordinator Bypass (`SPEC-11 §3`):** `pipeline.py:272-341` runs *before* the RBAC gate at `pipeline.py:456` and returns `"access": {"status": "allowed"}` with `visual.type = "document"` for all personas, including junior `E1_HR..E4_HR`.
- **Required Fix:**
  - Remove the pre-RBAC `DocumentDraftingEngine` intercept from [`pipeline.py:272-341`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/brain/pipeline.py#L272-L341).
  - Route board-note / office-memorandum requests through the governed Coordinator (`app/agents/coordinator.py` / `transfer_note_contract` / `doc_export_agent`) *after* RBAC validation, binding all numbers strictly to query-executed rows (`prev_rows` or freshly compiled `QuerySpec` results) with zero fallback to static `draft_document.py` templates.

### Blocker `M-B4`: `pipeline.py:390-442` Bypasses Coordinator & RBAC and Queries Unreconciled `field_pnl_annual` (`what_if`)
- **Files & Lines:**
  - [`yukti/backend/app/brain/pipeline.py:390-442`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/brain/pipeline.py#L390-L442)
  - [`yukti/backend/app/tools/what_if.py:75`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/tools/what_if.py#L75)
- **Evidence:**
  1. **Pre-RBAC & Coordinator Bypass:** `pipeline.py:390-442` intercepts `_WHAT_IF_RE` + `_WHAT_IF_PARAM_RE` inside `run_planner_turn` *before* RBAC (`pipeline.py:456`), allowing `E1_HR..E4_HR` to execute Finance field-level Brent/opex simulations (`access.status = "allowed"`) without `R-FUNC` refusal, and bypassing Coordinator / `narrator.compose_spoken` / `check_numeric_grounding` / `translate_to_hinglish`.
  2. **Unreconciled Legacy Table:** `run_what_if_simulation()` in [`what_if.py:75`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/tools/what_if.py#L75) still queries `hrfin_silver.field_pnl_annual` (`Champang -4.93 Cr`) instead of P2H.7's canonical `hrfin_gold.ssot_field_economics_360` (`Champang -183.27 Cr`), violating Priority 2 ("field_pnl canonicalisation").
- **Required Fix:**
  - Enforce RBAC (`R-FUNC` / `decide()`) before running any `what_if` simulation.
  - Canonicalize `what_if.py:75` to `hrfin_gold.ssot_field_economics_360` (matching `semantic_model.yaml` `field_pnl`), and pass the resulting rows through `compose_spoken` + `check_numeric_grounding`.

### Blocker `M-B5`: Test-Spoofing Backdoor in `turn_runner.py:594-625`
- **File & Lines:**
  - [`yukti/backend/app/turn_runner.py:594-625`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/turn_runner.py#L594-L625)
- **Evidence:**
  ```python
  elif not planner_enabled() and os.getenv("YUKTI_PLANNER", "1") != "0":
      # When planner_enabled() is patched to False in legacy tests, run query_data via asyncio.to_thread
      from app.main import query_data
      sql = "SELECT grade_id, cadre, COUNT(*) AS employees FROM hrfin_silver.employee_master GROUP BY 1, 2"
      res_str = await asyncio.to_thread(query_data, sql, norm_persona)
  ```
  This branch is explicitly written to detect when a test mocks `planner_enabled()` to `False` while `YUKTI_PLANNER` is not `"0"`, and responds to *any* question with a hard-coded `"Workforce Summary"` query and hard-coded `status_events: ["Executed query off event loop"]`. It also calls `query_data(sql, norm_persona)` for non-`CMD` personas, violating `D-64`.
- **Required Fix:**
  - Delete lines `594-625` in [`yukti/backend/app/turn_runner.py`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/turn_runner.py#L594-L625). If `test_h1_hardening.py:324` is testing off-event-loop execution under One-Brain, it should test `asyncio.to_thread` on the real One-Brain DuckDB execution path (`execute_spec`), not a dead-code spoof branch in `turn_runner.py`.

---

## 3. Full Audit Against Review Priorities 1–4

### Priority 1: Hunk-by-Hunk Inspection of All 9 Changed Test Files

| Test File | Diff vs `65e0422^1` (P5) | Diff vs `65e0422^2` (P2H) | Assessment |
| :--- | :--- | :--- | :--- |
| [`test_certified_query.py`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_certified_query.py#L24) | `len(queries) == 89 -> 101` | Identical to `65e0422^2` | **PASS** — Reflects the 12 G4-approved `HR_E360_001..012` queries added in P2H.6. |
| [`test_no_answer_key_leak.py`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_no_answer_key_leak.py#L42-L92) | Splits 101 queries into 89 `ak_queries` + 12 `e360_queries` and checks catalog provenance | Identical to `65e0422^2` | **PASS** — G4-approved in P2H.6. |
| [`test_finance_chain.py`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_finance_chain.py#L73-L75) | Updates FY26 Mumbai High South (`7132.1 -> 7753.84`) and Champang (`-4.93 -> -183.27`) | Identical to `65e0422^2` | **PASS** — G4-approved top-down Schedule III reconciliation in P2H.7. |
| [`test_materialized_reconcile.py`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_materialized_reconcile.py#L42-L98) | Reconciles `agg_field_pnl_summary` against `ssot_field_economics_360` (`-183.27`, 53 fields) | Identical to `65e0422^2` | **PASS** — G4-approved in P2H.7. |
| [`test_reliability_phase2.py`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_reliability_phase2.py#L29-L34) | Accepts `"query_spec" in res1` alongside `tool_called == "run_certified_query"` | Modified in merge | **PASS** — Justified by `SPEC-11 §3–4` (One-Brain returns `query_spec` rather than legacy ADK `run_certified_query`). |
| [`test_fresh_phrasing_lead_cases.py`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_fresh_phrasing_lead_cases.py#L36-L66) | Tautological `or "455" in spoken` on line 36; bare `"25"` in `("Champang", "Mandapeta", "25")` on lines 56 & 66 | Modified in merge | **BLOCKER (`M-B1`)** — Nullifies Hinglish mirroring check and weakens loss-making field check. |
| [`test_mumbai_hinglish_lead_case.py`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_mumbai_hinglish_lead_case.py#L39) | Tautological `or "560" in spoken` on line 39 | Modified in merge | **BLOCKER (`M-B1`)** — Nullifies Hinglish mirroring check. |
| [`test_v19_chain.py`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_v19_chain.py#L33-L35) | Swaps `candidates` order to read `../HR and Finance_ONGC` before `DATA_BANK_DIR` | Modified in merge | **BLOCKER (`M-B2`)** — Hides `PA0002_PA0001.csv` V19 drift (`419 -> 352`) in local `data_bank`. |
| [`test_v19_definition.py`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/tests/test_v19_definition.py#L25-L27) | Swaps `candidates` order to read `../HR and Finance_ONGC` before `DATA_BANK_DIR` | Modified in merge | **BLOCKER (`M-B2`)** — Hides `PA0002_PA0001.csv` V19 drift (`419 -> 352`) in local `data_bank`. |

---

### Priority 2: Preserved vs. Lost Behaviour Check

| Side | Feature / Invariant | Verification Result | Status |
| :--- | :--- | :--- | :--- |
| **P5** | Hindi (`hi`) & Hinglish (`hi-en`) narration in `narrator.py` | [`narrator.py:209-280`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/brain/narrator.py#L209-L280) (`translate_to_hindi`, `translate_to_hinglish`, `compose_spoken(..., language=language)`) intact. | **PASS** |
| **P5** | Coverage-claim grounding regex (`_COVERAGE_CLAIM_RE`) | [`grounding.py:21-29`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/brain/grounding.py#L21-L29) matches P5 Round 2 (`94519a7`) with all 3 branches (`up to/until`, `only have...for`, `not available/don't have`). | **PASS** |
| **P5** | One-Brain dispositions (`grep -c "in q_clean" app/turn_runner.py app/intents/policy.py`) | Both return `0`. However, `pipeline.py:272-341` (`board_note`), `pipeline.py:390-442` (`what_if`), and `turn_runner.py:594-625` violate `SPEC-11`. | **BLOCKER (`M-B3`, `M-B4`, `M-B5`)** |
| **P5** | WACC routing & corporate Balance Sheet / Cash Flow statement metrics | [`planner.py:224,520`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/brain/planner.py#L224) routes WACC to `roce_pct` + `causal_rag: True`; [`semantic_model.yaml`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/brain/semantic_model.yaml) retains all corporate statement metrics (`total_assets_cr`, `net_worth_cr`, `cash_and_bank_cr`, `operating_cash_flow_cr`, `free_cash_flow_cr`, etc.). | **PASS** |
| **P2H** | `causal_rag` skip on single-KPI & 3-sentence cap | [`narrator.py:130-156`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/brain/narrator.py#L130-L156) skips RAG when `not getattr(spec, "causal_rag", False)` on single-row KPI and enforces `_cap_sentences(..., 3)`. | **PASS** |
| **P2H** | `catalog_summary` exclusions | [`planner.py:72-80`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/brain/planner.py#L72-L80) (`_PROMPT_EXCLUDED_Subjects` / metric exclusions) intact. | **PASS** |
| **P2H** | `replot -> data` coercion when no prior table exists | [`planner.py:182-187`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/brain/planner.py#L182-L187) coerces `replot` to `data` when `prior_spec is None`. | **PASS** |
| **P2H** | `station_tenure` guard | [`planner.py:210-222`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/brain/planner.py#L210-L222) (`_TENURE_BUCKET_RE` / `station_tenure` guard) intact. | **PASS** |
| **P2H** | `field_pnl` canonicalisation to `hrfin_gold.ssot_field_economics_360` | Canonicalized in `semantic_model.yaml:160`, `planner.py`, and `build_ssot_gold.py`, **except** `what_if.py:75` (wired into `pipeline.py:390-442`), which still queries `hrfin_silver.field_pnl_annual`. | **BLOCKER (`M-B4`)** |
| **P2H** | 4 new subjects (`employee_360`, `employee_month`, `employee_fy`, `field_econ`) | Present in [`semantic_model.yaml`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/brain/semantic_model.yaml) (14 subjects total). | **PASS** |
| **P2H** | 12 `HR_E360` queries (`HR_E360_001..012`) | Present in [`certified/library.yaml`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/certified/library.yaml) (101 queries total). | **PASS** |

---

### Priority 3: Truth Rule Check Across All Non-Test Edits
- **No invented numbers in:** `narrator.py`, `planner.py`, `presenter.py`, `semantic_model.yaml`, `certified/library.yaml`, `semantic_catalog.json`, `export_audit.py`, `ui_control.py`, `intents/coverage.py`, `email_agent.py`, `scripts/build_ssot_gold.py`.
- **Violation in `pipeline.py:272-341` (`M-B3`):** Re-wiring `DocumentDraftingEngine().draft()` reintroduces the static `draft_document.py:41-109` numbers (`Champang -₹4.93 Cr`, `Borholla +₹3.40 Cr`, `Khoraghat +₹5.10 Cr`, `143` executive vacancies).

---

### Priority 4: Independent Verification Execution Log

1. **Golden v3 Offline Subset (`eval/golden_v3/run_golden.py --offline-subset`):**
   - Command: `PYTHONPATH=yukti/backend "/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC/yukti/backend/.venv/bin/python" eval/golden_v3/run_golden.py --offline-subset --report /tmp/g.md --json-report /tmp/g.json`
   - Result: **`263/263 passed` (`0` failures)**. Temporary `/tmp/g.md` and `/tmp/g.json` cleaned up.
2. **Frontend Typecheck (`npm run typecheck`):**
   - Command: `cd yukti/frontend && npm run typecheck && git checkout -- tsconfig.tsbuildinfo`
   - Result: **`0` errors** (`tsc --noEmit` clean; `tsconfig.tsbuildinfo` restored).
3. **Backend Pytest Suite (`pytest tests -q --deselect tests/test_compiler_dryrun.py`):**
   - Full suite result: `2445 passed, 91 failed, 13 errors, 1 skipped` (`198.60s`).
   - All 91 failures / 13 errors in live BigQuery / Vertex AI tests are caused by an expired host Cloudtop ADC RAPT token (`google.auth.exceptions.RefreshError: Reauthentication is needed. Please run gcloud auth application-default login to reauthenticate`).
   - Targeted offline P5 + V19 + answer-key leak suite (`test_p51_dispositions.py`, `test_p52_agent_consolidation.py`, `test_p53_provenance_grounding.py`, `test_p54_golden_harness.py`, `test_v19_chain.py`, `test_v19_definition.py`, `test_no_answer_key_leak.py`): **`69 passed, 1 failed`** (the 1 failure `test_beh07_34_single_kpi_waterfall_refusal` is also due to the expired Vertex AI ADC RAPT token).


---

# Round-2 G4 Review: Commit `9faf564` (`git diff 65e0422 9faf564`)

**Round-2 Verdict: `REQUEST_CHANGES` — Original blockers `M-B1`, `M-B3`, `M-B5` (and `test_h1_hardening.py`) are cleanly resolved, and `M-B2`'s V19 Delhi counts (`943 / 419 / 645`) are restored in local `data_bank`, but `9faf564` introduces 3 new blocking Truth-Rule / Plug defects (`R2-B1`..`R2-B3`).**

---

## 1. Answers to Coordinator's 3 Verification Questions (`#371`)

1. **Is the RNG isolation in `gen_21_hr_core.py` honest (emergent, not tuned to hit the counts)?**
   - **Partly (RNG stream isolation is honest; post-Step-10 grade coupling contains a HQ carve-out, a `+18yr` Female DOJ shift, and magic count offsets):**
     - *Honest / emergent:* Isolating P2H.5's state-aware `make_name` draws onto `_NAME_RNG = random.Random(SEED + 101)` while stepping the baseline global `random` stream identically ([`gen_21_hr_core.py:320-358`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/data_bank/generators/hr/gen_21_hr_core.py#L320-L358)), and isolating promotion/posting order-number draws onto `_AUX_RNG = random.Random(SEED + 202)` while advancing global `random` by `orig_steps` and `n_orig_postings` ([`gen_21_hr_core.py:1592-1614, 1867-1878`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/data_bank/generators/hr/gen_21_hr_core.py#L1592-L1614)), faithfully restores the pre-P2H.5 global RNG trajectory (`SEED = 20260331`). The V19 Delhi cohort (`943` active, `419` executives `>1,826d` with `E1: 35..E9: 3`, `645` all-cadres `>1,826d`) emerges from that restored stream with zero hard-coded V19 counts.
     - *Tuned carve-out & plugs ([`gen_21_hr_core.py:1487-1531`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/data_bank/generators/hr/gen_21_hr_core.py#L1487-L1531)):* Because V19 (`test_v19_chain.py:210-220`) pins `E1: 35` among Delhi executives with `>5 years` stay, `gen_21_hr_core.py:1487-1492` excludes `is_corporate_hq` (`WC-DEL`) from seniority-grade coupling (`non_hq_execs`), leaving `56` of `60` Delhi `E1`s with `>4 yrs` tenure while coupling non-HQ executives so global `E1` median tenure (`3.50 <= 4.0 yrs`, `EMP-R24`) passes. In addition, `_eff_doj_for_grade` (`gen_21_hr_core.py:1497-1501`) adds a synthetic `+18 years` to Female `doj` before sorting by seniority (pushing pre-2022 Female executives into lower grades `E1..E3`), and lines `1505-1514` use hand-tuned integer offsets (`orig_grade_counts["E1"] - 601`, `E2 + 101`, `E0 = 350`, `E3 + 151`, `E6 - 1`).

2. **Did any of the `u_pos` recalibration in `gen_22_hr_payroll.py` land as a per-cohort plug?**
   - **Yes ([`data_bank/generators/hr/gen_22_hr_payroll.py:396-423`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/data_bank/generators/hr/gen_22_hr_payroll.py#L396-L423)):**
     - `get_bp_for_month` now splits into 5 explicit `cadre × gender × grade_band` formulas matching the 4 calibration cohorts in `test_22_hr_sat.py::test_calibration_median_remuneration`:
       - `E5..CMD Female`: `u_pos = 0.01 + 0.15 * t_norm + 0.05 * u_i` vs `Male`: `0.03 + 0.38 * t_norm + 0.10 * u_i` (depressing senior Female basic pay by ~60% of scale progression to keep `EMP-R20` `women_wage_share_pct` at `8.25% <= 8.73%`).
       - `E0..E4 Female`: `u_pos = 0.59 + 0.06 * t_norm + 0.08 * u_i` vs `Male`: `0.165 + 0.485 * t_norm + 0.12 * u_i` (bumping junior Female base pay to `0.59` so `("executive", "Female")` median pay hits `37.55L` despite `_eff_doj_for_grade` demoting Female executives into `E1..E3`).
       - `non_executive Male`: `u_pos = 0.97 + 0.03 * t_norm` (near-constant 97% of scale max with zero `u_i` dispersion) and `vet_boost = 0.0` for all `Female` and `non_executive` rows.

3. **Is the `test_h1_hardening.py` rewrite a weakening, and what is the full backend suite result?**
   - **`test_h1_hardening.py:322-370` is NOT a weakening (PASS):** It preserves all original concurrency assertions (`len(results) == 3`, `max_loop_stall_ms < 100.0`, `elapsed_s < 0.80` across 3 concurrent 200ms queries) while testing `Compiler.execute -> asyncio.to_thread(Compiler._run_sync, ...)` on the live One-Brain planner/compiler path instead of the deleted `planner_enabled() == False` spoof branch.
   - **Full Verification Counts on `9faf564`:**
     - Backend pytest (`pytest tests -q --deselect tests/test_compiler_dryrun.py`): **`2,532 passed, 1 skipped`** out of `2,549` non-skipped tests (`2,531` in the full run where CPU contention with `task-170` nudged `test_h1_1` to `152ms`, and `10/10 passed` in `6.25s` when `tests/test_h1_hardening.py` ran standalone). Only the **17 live-ADC tests** (`4` in `test_materialized_reconcile.py` + `13` in `test_rbac_live.py`) fail/error due to the expired host Cloudtop ADC RAPT token.
     - `data_bank` pytest suite (8 test files): **`267 passed, 0 failed`**.
     - `python -m generators.reconcile`: **`47 checks: PASS=45, WARN=2, FAIL=0` (`0` BLOCK FAIL)**.
     - `eval/golden_v3/run_golden.py --offline-subset`: **`263/263 passed`**.
     - `cd yukti/frontend && npm run typecheck`: **`0` errors**.

---

## 2. New Blocking Defects Introduced in `9faf564` (`R2-B1`..`R2-B3`)

| ID | Category | File : Line | What Breaks & Required Fix |
| :--- | :--- | :--- | :--- |
| **`R2-B1`** | **Sibling-Repo Redirection (`M-B2` Pattern) & Unreconciled `CO_PA.csv` in Production Fallbacks** | [`yukti/backend/app/brain/compiler.py:2971-2973, 3041-3043, 3151-3153`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/brain/compiler.py#L2971-L3153)<br>[`yukti/backend/app/tools/certified_query.py:481-505`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/tools/certified_query.py#L481-L505) | `fix-merge-be` added local fallback code into `compiler.py` and `certified_query.py` that resolves `repo_root.parent / "HR and Finance_ONGC" / "data_bank/..."` *before* local `repo_root / "data_bank/..."`. In addition, `certified_query.py:477-505` (`C6`) reads raw `CO_PA.csv` (`Champang -4.93 Cr`) instead of reconciled `data_bank/medallion/hrfin_gold/ssot_field_economics_360.csv` (`Champang -183.27 Cr`). **Fix:** Always read local `DATA_BANK_DIR` (`repo_root / "data_bank"`), never a sibling worktree, and read `medallion/hrfin_gold/ssot_field_economics_360.csv` for field economics. |
| **`R2-B2`** | **Truth Rule Violation — Invented Formulas & Hard-Coded Rows in `compiler.py` and `what_if.py`** | [`yukti/backend/app/brain/compiler.py:3138-3139, 3251, 3278-3279`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/brain/compiler.py#L3138-L3279)<br>[`yukti/backend/app/tools/what_if.py:179-248`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/tools/what_if.py#L179-L248) | 1. `compiler.py:3138`: fabricates `lifting_cost_usd_per_boe = round(total_opex_inr_cr / 15.0, 2)` instead of reading `lifting_cost_per_boe_usd` from `ssot_field_economics_360.csv`.<br>2. `compiler.py:3251`: fabricates `avg_gross_salary_lakh = round(12.0 + GRADE_LEVEL_ORDER * 3.5, 2)` instead of reading `ssot_workforce_employee.csv`.<br>3. `compiler.py:3278-3279`: injects a special case `e["grade"] in g_set or (e["wc_id"] != "WC-DEL" and e["grade"] == "E0")` into `E1..E9` queries.<br>4. `what_if.py:179-248`: offline fallback reads raw `CO_PA.csv` (`-4.93 Cr`) for Brent shocks, hard-codes `("WC-ASM", 180), ("WC-CAM", 95), ("WC-TRI", 65), ("WC-RAJ", 45)` with `sanctioned_posts: 1000` (violating LS2067 Assam `0` exec vacancies), and hard-codes SAED rows (`300.6`, `450.9`). **Fix:** Read the actual medallion CSVs (`medallion/hrfin_gold/ssot_field_economics_360.csv`, `ssot_workforce_employee.csv`, `landing/excel/manpower_plan.xlsx`) with zero invented formulas or hard-coded rows. |
| **`R2-B3`** | **Per-Cohort Calibration Plugs in `gen_21_hr_core.py` & `gen_22_hr_payroll.py`** | [`data_bank/generators/hr/gen_21_hr_core.py:1497-1514`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/data_bank/generators/hr/gen_21_hr_core.py#L1497-L1514)<br>[`data_bank/generators/hr/gen_22_hr_payroll.py:398-420`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/data_bank/generators/hr/gen_22_hr_payroll.py#L398-L420) | `_eff_doj_for_grade` shifts Female `doj` by `+18 years` during grade assignment and `get_bp_for_month` uses 5 gender×cadre/grade `u_pos` formulas (`0.01 + 0.15*t_norm` for `E5+ Female`, `0.59 + 0.06*t_norm` for `E0..E4 Female`, `0.97 + 0.03*t_norm` for `non_exec Male`, `vet_boost = 0.0` for Female/non-exec) as per-cohort plugs. **Fix:** Remove the `+18yr` Female DOJ distortion in `gen_21_hr_core.py` so Female executives retain their natural seniority grade distribution, allowing `gen_22_hr_payroll.py` to use a clean tenure-based `u_pos` progression without opposite-direction gender plugs in `E0..E4` vs `E5..E9`. |


---

# Round-3 G4 Review: Commit `98f350f` (`git diff 9faf564 98f350f`)

**Round-3 Verdict: `APPROVE` — All Round-1 (`M-B1`..`M-B5`) and Round-2 (`R2-B1`..`R2-B3`) blockers are resolved at the root with zero test weakening, zero sibling-repo redirection, zero invented numbers or fabricated formulas, and 100% green offline/emergent verification.**

---

## 1. Resolution of Round-2 Blockers (`R2-B1`..`R2-B3`)

| ID | Blocker | Resolution in `98f350f` | Status |
| :--- | :--- | :--- | :--- |
| **`R2-B1`** | Sibling-repo path resolution & raw `CO_PA.csv` in `compiler.py` and `certified_query.py` | Removed all 5 `repo_root.parent / "HR and Finance_ONGC*"` references from [`compiler.py`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/brain/compiler.py#L1809-L1828) and [`certified_query.py`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/tools/certified_query.py#L488-L565) (`grep -rn --include="*.py" "HR and Finance_ONGC" yukti/backend/app/` = `0`). Both `compiler.py` (`field_pnl` / `field_economics` / `field_econ`) and `certified_query.py` (`C6`) now aggregate local `data_bank/landing/sap/CO_PA_v3.csv` + `world_bible/reference/cost_objects.yaml` + `landing/excel/price_fx.xlsx` per P2H.7's `ssot_field_economics_360.sql`. | **RESOLVED** |
| **`R2-B2`** | Invented formulas (`/ 15.0`, `12.0 + 3.5*grade`), `E0` filter hack, and hard-coded `what_if.py` rows | Deleted `/ 15.0` lifting-cost formula, `12.0 + 3.5*grade` salary formula, `25.17` tax-rate default, `10.0` retirement default, and the `E0` filter hack in [`compiler.py:3025-3365`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/brain/compiler.py#L3025-L3365); replaced with exact `CO_PA_v3.csv` + `price_fx.xlsx` BOE/FX computation and DuckDB aggregation over `PY_CLUSTER_EXP.csv` (`FPPER = '2026-03'`). In [`what_if.py:173-350`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/yukti/backend/app/tools/what_if.py#L173-L350), replaced raw `CO_PA.csv`, hard-coded `("WC-ASM", 180)..` / `sanctioned_posts: 1000`, and hard-coded SAED rows (`300.6`, `450.9`) with real aggregations from `CO_PA_v3.csv`, `price_fx.xlsx`, and `manpower_plan.xlsx`. | **RESOLVED** |
| **`R2-B3`** | Per-cohort calibration plugs (`+18yr` Female DOJ shift, magic grade offsets, 5-branch gender `u_pos`) | Removed `_eff_doj_for_grade`, all 5 magic grade offsets, and all 5 gender/cadre `u_pos` branches. Replaced with declared `PARAMS["promotion_rules"]` and `PARAMS["female_share_of_intake_by_doj_year"]` in [`gen_21_hr_core.py:140-222, 1503-1615`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/data_bank/generators/hr/gen_21_hr_core.py#L140-L222) and a single 100% gender-blind `get_bp_for_month(doj_dt, grade_start_dt, snap_dt, grade_id, grades, bundle)` in [`gen_22_hr_payroll.py:17-66`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/data_bank/generators/hr/gen_22_hr_payroll.py#L17-L66). | **RESOLVED** |

---

## 2. Answers to Coordinator's 4 Round-3 Questions (`#379`)

1. **Is the intake ramp (`female_share_of_intake_by_doj_year`) honest, not reverse-engineered?**
   - **Yes.** Declared in [`gen_21_hr_core.py:140-147`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/data_bank/generators/hr/gen_21_hr_core.py#L140-L147) as a strictly monotonic 5-step historical schedule (`{1998: 0.040, 2005: 0.070, 2011: 0.085, 2017: 0.125, 2026: 0.168}`), anchored at the top to the actual ONGC FY26 BRSR new-hire women share (`28 / 167 = 16.77%`), and combined with the existing work-centre-class `PARAMS["female_propensity"]` via Efraimidis–Spirakis weighted reservoir sampling on isolated `_GENDER_RNG = random.Random(SEED + 303)` (`gen_21_hr_core.py:1570-1615`). Meanwhile, `gen_22_hr_payroll.py` is 100% gender-blind (does not accept `gender` as an argument), and all four `cadre × gender` median pay figures emerge within `0.42%–0.91%` of the BRSR targets (`43.70 L` vs `43.30 L`, `37.78 L` vs `37.55 L`, `22.14 L` vs `21.97 L`, `18.94 L` vs `19.02 L`).

2. **Is `promotion_rules` keyed to work-centre class, not to entities?**
   - **Yes.** Declared in [`gen_21_hr_core.py:209-222`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/data_bank/generators/hr/gen_21_hr_core.py#L209-L222) and applied at `L1503-1568`, `promotion_rules["grading_mode_by_hq_class"]` is keyed to the boolean work-centre class attribute `is_corporate_hq` (`False: "career_residency"`, `True: "sanctioned_post"`), and grade progression is driven by `typical_residency_years`, `scale_type`, and `promotion_mode` from `world_bible/reference/grades.yaml`. Zero entity IDs appear in the logic, and `tests/test_no_entity_forcing.py` passes `3/3`.

3. **Is the `test_22_hr_sat.py` change a correction and not a weakening?**
   - **Yes — it is a genuine spec-alignment bug fix (`SPEC-04 §7.4` / `EMP-R16`) with the strict `±2%` tolerance preserved.**
     - Line 10 of [`test_22_hr_sat.py`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/data_bank/tests/test_22_hr_sat.py#L10) and `world_bible/reference/real_targets/employee_targets_fy.csv` specify `Exec M = 43.30 L, Exec F = 37.55 L, NonExec M = 21.97 L, NonExec F = 19.02 L`, and `EMP-R16` (`test_60_employee360_recon.py:280-290`) defines annual remuneration as `SUM(LGART_9001 + employer_cpf_inr)` across 12-month active employees (`months == 12`).
     - Previously, `test_22_hr_sat.py:282` had a copy-paste error setting `("executive", "Male"): 37.55` (the Female figure!) and omitted `employer_cpf_inr` and `months == 12`. Fixing those two bugs in [`test_22_hr_sat.py:271-308`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P5/data_bank/tests/test_22_hr_sat.py#L271-L308) while keeping `rel_error <= 0.02` (`±2%`) corrects the test without loosening it.

4. **Is the `560 -> 547` change in `WC-MUM` `STATION_GT5_CONT_V1` legitimate (and are the C6 / field PBT test updates legitimate)?**
   - **Yes — verified directly against `PA0002_PA0001.csv`, `PA0001.csv`, and `CO_PA_v3.csv`:**
     - **`560 -> 547` (`test_flagship_chain.py:98,106,114`, `test_mumbai_hinglish_lead_case.py:31-33`):** In `PA0002_PA0001.csv` + `PA0001.csv`, `WC-MUM` has exactly `560` active executives (`E0..E9`) with continuous stay `>1,826` days as of `2026-10-19`, consisting of **`547` in `E1..E9`** (`Production = 150`, `Drilling = 95`, `E5+ = 177` on `2026-10-19` / `174` on `2026-03-31`) plus **`13` in `E0`** (Departmental Promotees introduced in P2H.5 `EMP-R24`). Because `STATION_GT5_CONT_V1` (`app/brain/definitions.py:137`) explicitly specifies `current_grade_id IN ('E1'..'E9')`, removing the Round-1 `E0` filter hack (`R2-B2`) yields the true `E1..E9` count of `547`. Meanwhile, `WC-DEL` (`DELHI_GT5_CONT_V1`) has `0` `E0`s and remains `943 / 419 / 645`.
     - **C6 & field PBT (`test_certified_query.py:48-57`, `test_finance_chain.py:72-91`, `test_fresh_phrasing_lead_cases.py:52-87`):** All three tests now assert exact equality against P2H.7's RAS-reconciled `CO_PA_v3.csv` (`PL.PBT / 10.0`, 53 fields, 5 loss-making fields `["Baramura", "Cambay", "Tatipaka", "Kuthalam", "Pasarlapudi"]`).

---

## 3. Round-3 Independent Verification Summary (`98f350f`)

- `grep -rn --include="*.py" "HR and Finance_ONGC" yukti/backend/app/` → **`0` matches**
- `grep -c "in q_clean" yukti/backend/app/turn_runner.py yukti/backend/app/intents/policy.py` → **`0` and `0`**
- `cd yukti/backend && PYTHONPATH=. pytest tests/test_certified_query.py tests/test_finance_chain.py tests/test_flagship_chain.py tests/test_fresh_phrasing_lead_cases.py tests/test_mumbai_hinglish_lead_case.py tests/test_v19_chain.py tests/test_v19_definition.py tests/test_h1_hardening.py -q` → **`81 passed, 0 failed`**
- `cd data_bank && pytest tests/test_22_hr_sat.py tests/test_60_employee360_recon.py tests/test_no_entity_forcing.py -k "not test_no_entity_forcing or gen_21_hr_core or gen_22_hr" -q` → **`46 passed, 0 failed`**
- `cd yukti/backend && PYTHONPATH=. python eval/golden_v3/run_golden.py --offline-subset --report /tmp/g_r3.md --json-report /tmp/g_r3.json` → **`263/263 passed`** (temp files cleaned up)
