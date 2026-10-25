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
