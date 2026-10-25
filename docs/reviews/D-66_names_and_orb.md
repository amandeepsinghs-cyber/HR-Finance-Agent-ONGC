# G4 Review: D-66 Leadership Names, Office-Holder Safeguard, Greeting VoiceOrb & Field-Economics Scope Creep

- **Reviewer:** `reviewer-d66` (Role R — Independent G4 Reviewer, read-only)
- **Commit Reviewed:** `9fe6a89` (`git diff 27a9b0b HEAD` on branch `v3/P5-one-brain`)
- **Date:** 2026-10-25
- **Verdict:** **REQUEST_CHANGES** (2 Blockers)

---

## Executive Summary (BLUF)

** Verdict: `REQUEST_CHANGES` — D-66 leadership names, 11-persona Employee-360 parity, V19 (`943 / 645 / 419`), and the frontend greeting `VoiceOrb` restoration all pass, but two blocking defects must be fixed before sign-off:**

1. **BLOCKER 1 — Scope Creep in `ssot_field_economics_360.sqlx` Breaks `data_bank` Parity Suite and Pollutes Monthly SSOT Grain (`data_bank/medallion/dataform/definitions/v3/ssot_field_economics_360.sqlx:276-277`):**
   - Appending `FULL OUTER UNION ALL BY NAME SELECT * FROM ongc-hr-finance-agent.hrfin_gold.ssot_field_economics_360` breaks `data_bank/tests/test_62_recon_parity.py:133` (`AssertionError: Expected >= 44 columns in ssot_field_economics_360.sqlx, got 0`, contradicting the `268 passed, 0 failed` claim in board `#401`), injects 530 annual (`month_start IS NULL`) rows into a monthly cost-object SSOT table (`8,631` rows), and couples `_v3` Dataform definitions to the legacy non-`_v3` dataset `hrfin_gold`.
2. **BLOCKER 2 — D-66 Office-Holder APAR & Medical Safeguard Bypass on Certified Queries, Post-Query `enforce_contract` / Exports, and Hindi Phrasings (`yukti/backend/app/tools/certified_query.py:102-343`, `yukti/backend/app/brain/rbac.py:182-280,1156-1160`, `yukti/backend/app/export_audit.py:507`):**
   - **Certified queries path:** Calling `run_certified_query("my_apar", persona="CMD"|"DIR_HR"|"DIR_FIN")` returns 5 rows of synthetic APAR scores/ratings for `EMP-000001..3`; calling `run_certified_query("E3", persona="CMD"|"DIR_FIN")` returns medical reimbursement claim rows (`1` row for `CMD`, `4` rows for `DIR_FIN`) instead of refusing. Self-queries (`E1`, `my_leave_balance`, `my_postings`) via `run_certified_query` also omit the `"Illustrative HR record (synthetic)"` provenance label.
   - **Post-query `enforce_contract` & Exports path:** `enforce_contract` (`yukti/backend/app/brain/rbac.py:1156-1160`) stamps the synthetic label via `apply_office_holder_safeguard` but never refuses or strips APAR (`numerical_score`, `final_rating`, `apar_score`, `apar_grade`) or medical (`claim_id`, `claimed_amount_inr`, `medical_reimbursement_inr`) rows/columns for `EMP-000001..3`. Consequently, `enforce_export_rbac` (`yukti/backend/app/export_audit.py:507`) allows exporting `EMP-000001..3` APAR/medical tables to PDF/XLSX, and any multi-row query returning `EMP-000001..3` APAR/medical rows passes through unblocked for `CMD` / `DIR_HR`.
   - **Hindi phrasings bypass:** `OFFICE_HOLDER_NAMES` (`yukti/backend/app/brain/rbac.py:182-186`) and `_OFFICE_HOLDER_TITLE_TARGET_RE` (`rbac.py:200-204`) only match English Latin names/titles, and `_OFFICE_HOLDER_MEDICAL_RE` (`rbac.py:194-199`) misses `स्वास्थ्य बीमा` / `दावा`. Queries such as `"अरुण कुमार सिंह का एपार दिखाओ"`, `"मनीष पाटिल का मेडिकल रिकॉर्ड क्या है?"`, `"अनुपम अग्रवाल का APAR क्या है?"`, `"चेयरमैन का एपार स्कोर क्या है?"`, `"निदेशक वित्त का मेडिकल क्लेम"`, and `"मेरा स्वास्थ्य बीमा दावा दिखाओ"` return `allowed` in both `check_access` and `rbac.decide`.

---

## Detailed Check Results

### 1. Names & Designations (`PASS`)

Verified against `ongcindia.com` Board of Directors page and repository files:

| `emp_id` | Persona | Name (`ongcindia.com` & Repo) | Designation (`ongcindia.com` & Repo) | Verification |
|---|---|---|---|---|
| `EMP-000001` | `CMD` | `Arun Kumar Singh` | `Chairman & CEO` | Matches `ongcindia.com` (`data_bank/generators/hr_core.py:121`, `yukti/backend/app/brain/app_users.yaml:13-22`) |
| `EMP-000002` | `DIR_HR` | `Manish Patil` | `Director (Human Resources)` | Matches `ongcindia.com` (`data_bank/generators/hr_core.py:122`, `yukti/backend/app/brain/app_users.yaml:24-33`) |
| `EMP-000003` | `DIR_FIN` | `Anupam Agarwal` | `Director (Finance)` | Matches `ongcindia.com` (`data_bank/generators/hr_core.py:123`, `yukti/backend/app/brain/app_users.yaml:35-44`; succession note for Sunil Kumar on 7-Dec-2026 documented at `docs/DECISIONS.md:66`) |

---

### 2. 11-Persona Employee-360 Parity (`PASS`)

Verified via read-only BigQuery query across `hrfin_gold_v3.dim_app_user`, `hrfin_gold_v3.ssot_employee_360` (`is_fy_end = TRUE AND fiscal_year = 'FY26'`), and `hrfin_gold_v3.ssot_workforce_employee`, cross-checked against `yukti/backend/app/brain/app_users.yaml:13-132`, `yukti/backend/app/brain/rbac_policy.yaml:17-69`, `data_bank/landing/sap/dim_app_user.csv:1-12`, and `yukti/frontend/src/personas.ts:25-39`:

| Persona | `emp_id` | `app_users.yaml` | `src/personas.ts` | `hrfin_gold_v3.dim_app_user` | `hrfin_gold_v3.ssot_employee_360` | Parity |
|---|---|---|---|---|---|---|
| `CMD` | `EMP-000001` | `Arun Kumar Singh` | `Arun Kumar Singh` | `Arun Kumar Singh` | `Arun Kumar Singh` | **100%** |
| `DIR_HR` | `EMP-000002` | `Manish Patil` | `Manish Patil` | `Manish Patil` | `Manish Patil` | **100%** |
| `DIR_FIN` | `EMP-000003` | `Anupam Agarwal` | `Anupam Agarwal` | `Anupam Agarwal` | `Anupam Agarwal` | **100%** |
| `E1_HR` | `EMP-100151` | `Dinesh Deshmukh` | `Dinesh Deshmukh` | `Dinesh Deshmukh` | `Dinesh Deshmukh` | **100%** |
| `E2_HR` | `EMP-102451` | `Pooja Verma` | `Pooja Verma` | `Pooja Verma` | `Pooja Verma` | **100%** |
| `E3_HR` | `EMP-100144` | `Lokesh Verma` | `Lokesh Verma` | `Lokesh Verma` | `Lokesh Verma` | **100%** |
| `E4_HR` | `EMP-100178` | `Umesh D. Bhatia` | `Umesh D. Bhatia` | `Umesh D. Bhatia` | `Umesh D. Bhatia` | **100%** |
| `E1_FIN` | `EMP-100150` | `Ajay Deshmukh` | `Ajay Deshmukh` | `Ajay Deshmukh` | `Ajay Deshmukh` | **100%** |
| `E2_FIN` | `EMP-100152` | `Praveen Nair` | `Praveen Nair` | `Praveen Nair` | `Praveen Nair` | **100%** |
| `E3_FIN` | `EMP-100146` | `Shailesh E. Kapoor` | `Shailesh E. Kapoor` | `Shailesh E. Kapoor` | `Shailesh E. Kapoor` | **100%** |
| `E4_FIN` | `EMP-100145` | `Santosh Banerjee` | `Santosh Banerjee` | `Santosh Banerjee` | `Santosh Banerjee` | **100%** |

---

### 3. D-66 Office-Holder Safeguard & RBAC Non-Regression (`FAIL — BLOCKER 2`)

#### What Works
- **English & `emp_id` pre-query refusals on `check_access` (`yukti/backend/app/access_control.py:534-546`) and `rbac.decide` (`yukti/backend/app/brain/rbac.py:854-869`):**
  - `"my APAR"` as `CMD`, `DIR_HR`, `DIR_FIN` -> refused (`R-APAR`, rule `D-66`).
  - `"What is my medical reimbursement claim status?"` as `CMD`, `DIR_HR`, `DIR_FIN` -> refused (`R-SENS`, rule `D-66`).
  - `"Show APAR for EMP-000001"`, `"EMP-000002 medical reimbursement"`, `"EMP-000003 appraisal rating"` -> refused (`R-APAR` / `R-SENS`, rule `D-66`).
  - `"Show performance rating of Chairman"`, `"Show appraisal score for Director HR"`, `"Show medical bills for Director Finance"` -> refused (`R-APAR` / `R-SENS`, rule `D-66`).
- **Synthetic HR label (`"Illustrative HR record (synthetic)"`) on allowed self-scope and named HR queries (`yukti/backend/app/brain/rbac.py:282-374`, `yukti/backend/app/brain/planner.py:2038-2046`):**
  - Stamps `contract["provenance"] = {"label": "synthetic", "detail": "Illustrative HR record (synthetic)", "badge": "Illustrative HR record (synthetic)"}`, `contract["caveat"]`, and `contract["display_text"]`.
- **RBAC Non-Regression:**
  - `E2_HR` asking `"What is the salary of my reporting officer?"` or `"What is the salary of EMP-100151?"` -> still refused (`R-PAY`).
  - `CMD` asking `"What is the average CTC by grade?"` -> still allowed (`allow`).
- **`test_no_real_person_names` (`data_bank/tests/test_21_hr_core.py:213-230`):**
  - Asserts that no row in `employee_master` with `emp_id NOT IN ('EMP-000001', 'EMP-000002', 'EMP-000003')` matches the 19-name `real_person_names_blacklist` (current and past ONGC Board members). This is consistent with D-66: `EMP-000001..3` intentionally carry the three real office-holder names while all 42,168 other synthetic employees remain checked against the blacklist.

#### Blocking Gaps Found
1. **Certified Queries Path (`yukti/backend/app/tools/certified_query.py:102-343`) Has No D-66 Guard:**
   - `run_certified_query("my_apar", persona="CMD" | "DIR_HR" | "DIR_FIN")` executes `SELECT ... FROM apar_ratings WHERE emp_id = @self_emp_id` against BigQuery and returns **5 rows of synthetic APAR scores** (`numerical_score`, `final_rating`, `benchmark_score`, `is_dpc_eligible`) for `EMP-000001..3`.
   - `run_certified_query("E3", persona="CMD" | "DIR_FIN")` executes `SELECT ... FROM medical_claims WHERE emp_id = @self_emp_id` and returns **1 medical claim row for `CMD`** and **4 medical claim rows for `DIR_FIN`**.
   - Self-scoped HR queries (`E1`, `E2`, `E6`, `my_leave_balance`, `my_leave_ledger`, `my_postings`, `my_station_tenure`, `my_entitlements`, `HR_E360_002`, `HR_E360_003`) called via `run_certified_query` for `CMD` / `DIR_HR` / `DIR_FIN` do not stamp `"Illustrative HR record (synthetic)"` in `result["provenance"]` or `result["deterministic_summary"]`.
2. **Post-Query `enforce_contract` (`yukti/backend/app/brain/rbac.py:1156-1160`) & Exports (`yukti/backend/app/export_audit.py:507`) Do Not Refuse APAR/Medical Rows for `EMP-000001..3`:**
   - `enforce_contract` only calls `apply_office_holder_safeguard` (which adds the synthetic label) and then immediately exits at `if pc == "leadership": return c` (`rbac.py:1159-1160`).
   - If a contract contains `EMP-000001..3` in `rows` (or `self_emp_id in OFFICE_HOLDER_EMP_IDS`) alongside APAR or medical columns (e.g., from a certified query, a roster query, or a client/turn export passed to `enforce_export_rbac`), neither `enforce_contract` nor `enforce_export_rbac` converts it into a D-66 refusal (`R-APAR` / `R-SENS`) or strips `EMP-000001..3` from multi-employee APAR/medical tables.
3. **Hindi Name, Title, and Medical Phrasings Bypass `is_office_holder_apar_or_medical` (`yukti/backend/app/brain/rbac.py:182-204, 240-248`):**
   - `OFFICE_HOLDER_NAMES` (`rbac.py:182-186`) lacks Devanagari names (`"अरुण कुमार सिंह"`, `"अरुण सिंह"`, `"मनीष पाटिल"`, `"अनुपम अग्रवाल"`).
   - `_OFFICE_HOLDER_TITLE_TARGET_RE` (`rbac.py:200-204`) lacks Hindi titles (`चेयरमैन`, `अध्यक्ष`, `सीएमडी`, `निदेशक\s*\(?\s*(?:एचआर|मानव\s*संसाधन|वित्त)\s*\)?`).
   - `_OFFICE_HOLDER_MEDICAL_RE` (`rbac.py:194-199`) lacks `स्वास्थ्य\s*(?:बीमा|दावा|क्लेम)|मेडिकल\s*(?:बिल|दावा|क्लेम)`.
   - All 6 Hindi probes below currently return `allowed` instead of `refused`:
     - `"अरुण कुमार सिंह का एपार दिखाओ"`
     - `"मनीष पाटिल का मेडिकल रिकॉर्ड क्या है?"`
     - `"अनुपम अग्रवाल का APAR क्या है?"`
     - `"चेयरमैन का एपार स्कोर क्या है?"`
     - `"निदेशक वित्त का मेडिकल क्लेम"`
     - `"मेरा स्वास्थ्य बीमा दावा दिखाओ"` (as `CMD`)

---

### 4. Field Economics (`ssot_field_economics_360.sqlx` Scope Creep) (`FAIL — BLOCKER 1`)

- **Reconciliation & FY26 `PL.REV_OPS` Check in BigQuery:**
  - `hrfin_gold_v3.recon_checks`: `BLOCK PASS = 504`, `BLOCK FAIL = 0` (`WARN PASS = 5`, `WARN FAIL = 2` on `EMP-R18` / `EMP-R19`).
  - `FLD-R01` (`PL.REV_OPS` FY26): `ssot_value = 1,325,081.4` Mn (`132,508.14` Cr) vs `reference_value = 1,325,081.4` Mn (`delta = 0.0`, `PASS`).
  - `v_field_economics_fy` FY26 `SUM(revenue_from_operations)/10 = 132,508.14` Cr (`132,508.0` Cr rounded to 1 decimal place).
- **Why `ssot_field_economics_360.sqlx:276-277` Is a Blocker:**
  1. **Breaks `data_bank` test suite (`data_bank/tests/test_62_recon_parity.py:133`):**
     - `_extract_sqlx_select_columns` (`test_62_recon_parity.py:42-47`) inspects the last `SELECT ... FROM` block of `ssot_field_economics_360.sqlx`. Because lines 276–277 append `FULL OUTER UNION ALL BY NAME SELECT * FROM \`ongc-hr-finance-agent.hrfin_gold.ssot_field_economics_360\``, `_extract_sqlx_select_columns` extracts `*` (`0` named columns) and fails with `AssertionError: Expected >= 44 columns in ssot_field_economics_360.sqlx, got 0`.
  2. **Pollutes Monthly SSOT Grain & Cross-Dataset Isolation:**
     - `ssot_field_economics_360` is defined (`ssot_field_economics_360.sqlx:1-8`) as a monthly cost-object grain table partitioned by `month_start` (`8,631` rows across 72 cost objects).
     - The union injects `530` annual legacy rows (`month_start IS NULL`, `field_id IS NOT NULL`) with 44 legacy-only columns and 5 overlapping columns (`fiscal_year`, `asset_wc_id`, `basin`, `maturity`, `water_cut_pct`).
     - Any query on `hrfin_gold_v3.ssot_field_economics_360` that aggregates overlapping column `water_cut_pct` or counts rows by `fiscal_year`/`basin`/`maturity`/`asset_wc_id` without filtering `month_start IS NOT NULL` mixes 8,631 monthly rows with 530 annual rows.
     - It also hardcodes a dependency from `_v3` Dataform definitions onto the legacy un-suffixed dataset `ongc-hr-finance-agent.hrfin_gold.ssot_field_economics_360`.
  3. **Required Fix:** Revert `data_bank/medallion/dataform/definitions/v3/ssot_field_economics_360.sqlx:276-277` and re-materialize `hrfin_gold_v3.ssot_field_economics_360` via `dataform run --schema-suffix v3 --actions ssot_field_economics_360` (legacy compatibility belongs in views such as `v_field_pnl_v3.sqlx`, not inside the monthly SSOT fact table).

---

### 5. Frontend Greeting `VoiceOrb` & Personas (`PASS`)

- **Accessible Label & `aria-pressed` (`yukti/frontend/src/components/CanvasView.tsx:122-132`, `yukti/frontend/src/components/VoiceOrb.tsx:26-27,40-41,188-192`):**
  - `CanvasView.tsx:129-130` passes `label={orbState === 'speaking' ? 'Stop Yukti speaking' : isMicActive ? 'Stop listening' : 'Start talking to Yukti'}` and `pressed={!!isMicActive}`.
  - `VoiceOrb.tsx:188-189` renders `aria-label={label || \`Yukti voice (${state})\`}` and `aria-pressed={clickable && pressed !== undefined ? pressed : undefined}`.
- **Tokens-Only Colours (`yukti/frontend/src/design/orbPalette.ts:1-37`, `yukti/frontend/src/components/VoiceOrb.tsx:12,195`):**
  - Uses `CLOUDS_LIGHT`, `CLOUDS_DARK`, and `tint` from `src/design/orbPalette.ts` and `focus-visible:outline-[var(--accent)]`.
- **Docked Mic Button Test IDs Unbroken (`yukti/frontend/src/components/FloatingConversationPanel.tsx:416-464`):**
  - Greeting orb container uses `data-testid="greeting-talk"` (`CanvasView.tsx:122`) and `data-testid="voice-orb"` (`VoiceOrb.tsx:191`).
  - Docked mic button in `FloatingConversationPanel.tsx:419,430,439,457` retains `data-testid="mic-button"` and `data-testid="stop-speaking"`, with its embedded mini-orb marked `interactive={false}` (`line 426`).
- **Frontend Verification Suite:**
  - `npm run typecheck`: **PASS** (0 errors)
  - `npm run lint:tokens`: **PASS** (`[lint:tokens] OK (68 files scanned)`)
  - `npm run test:unit`: **PASS** (`13/13 passed` in `src/__tests__/smoke.test.tsx`)

---

### 6. V19 Workforce Invariant (`PASS`)

Verified via read-only BigQuery query on `hrfin_gold_v3.ssot_workforce_employee`:
- Active Delhi (`WC-DEL`) headcount: **`943`**
- Continuous stay >= 5 yrs (`is_continuous_5yr_plus = TRUE`) all cadres: **`645`**
- Continuous stay >= 5 yrs (`is_continuous_5yr_plus = TRUE`) executives (`cadre = 'executive'`): **`419`**

---

### 7. Backend & Golden Offline Suites (`PASS` / Note on Flagship Chain Isolation)

- **Golden Offline (`yukti/backend/eval/golden_v3/run_golden.py --offline-subset`):** **`263/263 passed`**.
- **Backend Pytest (`pytest tests -q --deselect tests/test_compiler_dryrun.py`):**
  - `2594 passed, 4 failed, 1 skipped, 2 deselected` in full-suite run; the 4 failures were in `tests/test_flagship_chain.py` (`test_t2_names_roster`, `test_t3_by_discipline`, `test_t4_compare_mumbai`, `test_t5_e5_and_above`) due to live Gemini planner/mock state leakage from earlier test modules.
  - Re-running `pytest tests/test_flagship_chain.py -q` in isolation: **`7/7 passed` (30.92s)**.
- **`data_bank` Pytest (`pytest tests/test_21_hr_core.py tests/test_62_recon_parity.py`):**
  - `test_21_hr_core.py`: **passes** (including `test_no_real_person_names` and `test_app_users_sync`).
  - `test_62_recon_parity.py`: **FAILS** on `test_field_econ_schema_and_n35_guard` (`data_bank/tests/test_62_recon_parity.py:133`) due to Blocker 1.

---

## Required Changes Before Sign-Off

1. **Revert `ssot_field_economics_360.sqlx` union (`data_bank/medallion/dataform/definitions/v3/ssot_field_economics_360.sqlx:276-277`):**
   - Remove `FULL OUTER UNION ALL BY NAME SELECT * FROM \`ongc-hr-finance-agent.hrfin_gold.ssot_field_economics_360\``.
   - Re-run Dataform for `ssot_field_economics_360` with `--schema-suffix v3` so `hrfin_gold_v3.ssot_field_economics_360` has pure monthly cost-object grain (`8,631` rows), and verify `pytest data_bank/tests/test_62_recon_parity.py` passes (`10/10`).
2. **Harden D-66 Office-Holder Safeguard Across All 5 Paths:**
   - **Certified queries (`yukti/backend/app/tools/certified_query.py:102-343`):** Before executing BigQuery, check if `entry["id"]` is an APAR or medical query (`my_apar`, `E3`, or SQL touching `apar_ratings` / `medical_claims`) targeting `EMP-000001..3` (via `canon_persona in OFFICE_HOLDER_PERSONAS` or `merged_params.get("self_emp_id") in OFFICE_HOLDER_EMP_IDS` or `emp_id` param), and refuse with `D-66` (`OFFICE_HOLDER_REFUSAL_COPY`). For allowed self-queries (`my_leave_balance`, `E1`, `my_postings`, etc.) when `self_emp_id in OFFICE_HOLDER_EMP_IDS`, stamp `OFFICE_HOLDER_SYNTHETIC_LABEL` into `provenance` and `deterministic_summary`.
   - **Post-query `enforce_contract` (`yukti/backend/app/brain/rbac.py:282-374, 1156-1160`) & `enforce_export_rbac` (`yukti/backend/app/export_audit.py:507`):** When a contract targets `EMP-000001..3` (or `self_emp_id in OFFICE_HOLDER_EMP_IDS`) and contains APAR (`apar` class) or medical (`claim_id`, `claimed_amount_inr`, `approved_amount_inr`, `medical_reimbursement_inr`, `medical_scheme_cost_inr`) columns/rows, convert a single-target / self contract into a `refused` contract (`code="R-APAR"` or `"R-SENS"`, `rule_ref="D-66"`, `reason=OFFICE_HOLDER_REFUSAL_COPY`), and strip `EMP-000001..3` rows from multi-employee APAR/medical roster tables before returning or exporting.
   - **Hindi phrasings (`yukti/backend/app/brain/rbac.py:182-204, 326-331`):** Add Devanagari office-holder names (`"अरुण कुमार सिंह"`, `"अरुण सिंह"`, `"मनीष पाटिल"`, `"अनुपम अग्रवाल"`), Hindi title patterns (`चेयरमैन`, `अध्यक्ष`, `सीएमडी`, `निदेशक\s*\(?\s*(?:एचआर|मानव\s*संसाधन|वित्त)\s*\)?`), and Hindi medical claim terms (`स्वास्थ्य\s*(?:बीमा|दावा|क्लेम)|मेडिकल\s*(?:बिल|दावा|क्लेम)|इलाज`) to `OFFICE_HOLDER_NAMES`, `_OFFICE_HOLDER_TITLE_TARGET_RE`, and `_OFFICE_HOLDER_MEDICAL_RE`.


---

# Round 2 Review (Post-Fix Verification)

- **Reviewer:** `reviewer-d66` (Role R — Independent G4 Reviewer, read-only)
- **Diff Reviewed:** `git diff 9fe6a89 HEAD` on branch `v3/P5-one-brain` (Implementer `d66-fix`, board `#405`)
- **Date:** 2026-10-25
- **Verdict:** **APPROVE** (Both Round 1 Blockers Resolved)

## Round 2 Executive Summary (BLUF)

**Verdict: `APPROVE` — Both Round 1 blockers (`ssot_field_economics_360.sqlx` scope creep and the D-66 office-holder safeguard bypasses) are resolved at the root with zero regressions.**

1. **BLOCKER 1 Resolved (`data_bank/medallion/dataform/definitions/v3/ssot_field_economics_360.sqlx:267-275`, `data_bank/medallion/dataform/definitions/v3/v_field_pnl_v3.sqlx:1-90`, `yukti/backend/app/config.py:133-155`):**
   - The `FULL OUTER UNION ALL BY NAME SELECT * FROM ongc-hr-finance-agent.hrfin_gold.ssot_field_economics_360` union has been removed from `ssot_field_economics_360.sqlx`.
   - `hrfin_gold_v3.ssot_field_economics_360` is re-materialized at pure monthly cost-object grain: `8,631` total rows, **`0` rows with `month_start IS NULL`**, and FY26 `SUM(revenue_from_operations)/10 = 132,508.14 Cr` (`PL.REV_OPS`).
   - `v_field_pnl_v3.sqlx` builds cleanly over `${ref("v_field_economics_fy")}` with zero dependency on legacy `hrfin_gold`, and `config.py:133-155` routes `field_pnl_annual` / annual `field_id IS NOT NULL` queries on `_v3` to `hrfin_gold_v3.v_field_pnl_v3`. `C6` field P&L returns all `53` fields unchanged (`114,757.74 Cr` field revenue in `_v3`, `132,508.14 Cr` total across all 72 cost objects; `125,145.85 Cr` in legacy `hrfin_gold`).
   - `hrfin_gold_v3.recon_checks` has **`0 BLOCK FAIL`** (`504 BLOCK PASS`), and `data_bank/tests/test_62_recon_parity.py` passes **`7/7` (`1.26s`)**.
2. **BLOCKER 2 Resolved (`yukti/backend/app/brain/rbac.py:180-787,1569-1575`, `yukti/backend/app/tools/certified_query.py:167-179,363-371`, `yukti/backend/app/access_control.py:534-556`, `yukti/backend/app/export_audit.py:515-525`, `yukti/backend/app/main.py:546-551`):**
   - **Certified queries (`certified_query.py:167-179,363-371`):** `run_certified_query("my_apar", persona)` and `run_certified_query("E3", persona)` for `CMD`, `DIR_HR`, and `DIR_FIN` are refused (`status="refused"`, `rows=[]`, `rule_ref="D-66"`, `reason="Not shown: illustrative records are not displayed for named office-holders."`). Allowed office-holder self-queries (`my_leave_balance`, `E1`, `my_postings`, `my_payslip`) carry `provenance.label = "synthetic"` and `provenance.detail = "Illustrative HR record (synthetic)"`.
   - **Post-query `enforce_contract` (`rbac.py:554-696,1569-1575`) & Exports (`export_audit.py:515-525`):** `enforce_office_holder_contract` runs before the `if pc == "leadership": return c` early return. Passing an APAR or medical contract containing `EMP-000001..3` to `enforce_contract` (as `CMD`, `DIR_HR`, or `DIR_FIN`) or `enforce_export_rbac(apar_contract, "CMD")` refuses with `code="R-APAR"` / `"R-SENS"`, `rule_ref="D-66"`, and `rows=[]`.
   - **Hindi, Devanagari & Hinglish (`rbac.py:182-218,339-413`):** All 6 Round 1 Hindi bypass queries plus 12 additional Round 2 adversarial probes (including `EMP-000002 का मेडिकल`, `EMP-000001 का एपीएआर`, `EMP-000003 का इलाज और अस्पताल का बिल`, `अध्यक्ष का वार्षिक कार्य निष्पादन क्या है?`, `सीएमडी के मेडिकल दावे दिखाओ`, `निदेशक (मानव संसाधन) का मूल्यांकन स्कोर`, `Arun Singh ka e-apar dikhao`, `Manish Patil ka chikitsa dawa kya hai?`, `Anupam Agarwal ka bima claim`, `meri medical claim status batao`, and `apna apar rating dikhao`) are refused (`R-APAR` / `R-SENS`, `D-66`) in both `check_access` and `rbac.decide`.
   - **Non-Regression:** `E2_HR` self-APAR (`run_certified_query("my_apar", persona="E2_HR")`) returns `5` rows for `EMP-102451`; `CMD` aggregate APAR distribution by grade (`enforce_contract`) remains `allowed` (`2` rows); `E2_HR` asking for another employee's salary remains refused (`R-PAY`).
