# P2H.2 (Backend Half) Evidence — Refusal Copy YAML (9 Codes EN/HI), 11-Persona Display Strings & Refusal Contract Shape

**Date:** 2026-10-24  
**Author:** `rbac` (Role A, Gemini 4 Argon)  
**Branch:** `v3/P2H-hr`  
**Worktree:** `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC__v3P2H`  
**Packet:** `docs/delegation/packets/v3/P2H.2.md` (backend half assigned by `@coordinator` in #36) · **Spec:** `docs/specs/SPEC-06_personas_identity_rbac_v3.md` §4.6, §5

---

## 1. Files Changed (Backend Half)

| File | Description |
|---|---|
| `yukti/backend/app/brain/refusal_copy.yaml` | New bilingual (EN + HI) refusal copy catalog for all 9 SPEC-06 §4.6 refusal codes (`R-NAMED`, `R-PAY`, `R-APAR`, `R-SENS`, `R-FUNC`, `R-BOARD`, `R-ROLE`, `R-K5`, `E-AUTH`) with `rule_ref`, `auto_answer` flags, `alternative {label, label_hi, question, question_hi}`, and `alternatives` list. |
| `yukti/backend/app/answer_composer.py` | Loads all 11 persona display strings (`PERSONA_DISPLAY`, `PERSONA_DISPLAY_STRINGS`) from `app_users.yaml`; loads `refusal_copy.yaml` via `load_refusal_copy()`; implements `persona_display_info()`, `render_refusal_copy()`, and `build_refusal_contract()`; repairs `access.code`, `access.rule_ref`, `access.alternative {label, question}`, and `access.alternatives` in `validate_and_repair_contract()`. |
| `yukti/backend/app/brain/pipeline.py` | Routes `_refusal_contract()` and `policy.action == "aggregate"` / `suppressed` (`R-NAMED`, `R-FUNC`, `R-K5`) through `build_refusal_contract()` and `render_refusal_copy()` so every refusal carries `access.code`, `access.rule_ref`, `access.alternative {label, question}` and (where policy allows: `R-NAMED`, `R-FUNC`) an auto-answer aggregate visual with `table.masking` metadata. |
| `yukti/backend/app/turn_runner.py` | Routes `_role_switch_contract()` (`R-ROLE`) through `build_refusal_contract()` using `refusal_copy.yaml` with `{display_name}` and `{designation}` interpolated from the signed principal. |
| `yukti/contracts/answer_contract.schema.json` | Backward-compatibly expands `persona.enum` to all 11 canonical personas and allows `access.alternative` to be either `{label, question}`, `string`, or `null` (plus `access.code`, `access.alternatives`, `access.self_emp_id`, `access.allow_pay_aggregate`). |
| `yukti/backend/tests/test_refusal_copy.py` | 49 unit tests covering all 9 refusal codes × 2 languages (18 exact SPEC-06 §4.6 copy renders), all 11 persona display strings from `app_users.yaml`, 18 `build_refusal_contract()` schema-validated refusal contracts, and `R-NAMED` auto-answer aggregate visual contract shape. |

---

## 2. Acceptance Table (Backend Half)

| Criterion | Target | Actual | Status |
|---|---|---|---|
| All 9 refusal codes (`R-NAMED`, `R-PAY`, `R-APAR`, `R-SENS`, `R-FUNC`, `R-BOARD`, `R-ROLE`, `R-K5`, `E-AUTH`) × 2 languages (`en`, `hi`) render from `refusal_copy.yaml` | 18 / 18 | **18 / 18 passed** | ✅ PASS |
| Placeholders `{display_name}`, `{designation}`, `{grade_num}` interpolated from `app_users.yaml` / signed principal | 11 / 11 personas | **11 / 11 passed** | ✅ PASS |
| Every refusal contract carries `access.code`, `access.rule_ref`, `access.alternative {label, question}` (`None` for `E-AUTH`), and `visual.code` / `visual.rule_ref` / `visual.alternative` | 18 / 18 contracts | **18 / 18 passed** | ✅ PASS |
| Auto-answer aggregate visual supported for `R-NAMED` and `R-FUNC` (`access.status = "partial"`, `table.masking.level = "aggregate"`, `table.masking.code`, `table.masking.reason`, `table.masking.rule_ref`) | Verified | **Passed** | ✅ PASS |
| Regression across RBAC, escalation, auth tokens, persona matrix, degraded copy, catalog consistency | All green | **852 / 852 passed** | ✅ PASS |

---

## 3. Exact TypeScript Field Additions Needed in `yukti/frontend/src/contracts/answerContract.ts` (for `@coordinator`)

Per packet `P2H.2.md` §4 & `@coordinator` #36, `yukti/frontend/src/contracts/answerContract.ts` was **not** modified by `rbac`. The exact TypeScript changes needed for the frontend half of `P2H.2` are:

1. **`PersonaType` (expand from 5 to 11 personas):**
   ```ts
   export type PersonaType =
     | 'CMD'
     | 'DIR_HR'
     | 'DIR_FIN'
     | 'E1_HR'
     | 'E2_HR'
     | 'E3_HR'
     | 'E4_HR'
     | 'E1_FIN'
     | 'E2_FIN'
     | 'E3_FIN'
     | 'E4_FIN';
   ```
2. **`RefusalAlternative` helper type (new):**
   ```ts
   export interface RefusalAlternative {
     label: string;
     question: string;
   }
   ```
3. **`TableMasking` interface (add `code?`):**
   ```ts
   export interface TableMasking {
     level?: 'none' | 'aggregate' | 'refused';
     code?: string;
     reason?: string | null;
     rule_ref?: string | null;
   }
   ```
4. **`VisualContainer` interface (add refusal metadata fields for `type === 'refusal'`):**
   ```ts
   export interface VisualContainer {
     // ... existing fields ...
     code?: string;
     rule_ref?: string;
     alternative?: RefusalAlternative | string | null;
     alternatives?: RefusalAlternative[];
     auto_answer_turn_id?: string | null;
   }
   ```
5. **`AccessControl` interface (add `code?`, `alternatives?`, `self_emp_id?`, `allow_pay_aggregate?`, and widen `alternative?`):**
   ```ts
   export interface AccessControl {
     status: AccessStatus;
     code?: string;
     reason?: string | null;
     rule_ref?: string | null;
     alternative?: RefusalAlternative | string | null;
     alternatives?: RefusalAlternative[];
     self_emp_id?: string | null;
     allow_pay_aggregate?: boolean;
   }
   ```

---

## 4. Self-Check Commands & Output

```bash
cd "/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC__v3P2H/yukti/backend" && \
  "/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC/yukti/backend/.venv/bin/python" -m pytest -q \
  tests/test_refusal_copy.py \
  tests/test_role_escalation.py \
  tests/test_rbac_policy.py \
  tests/test_personas_v3.py \
  tests/test_self_scope.py \
  tests/test_persona_question_matrix.py \
  tests/test_degraded_copy.py \
  tests/test_catalog_consistency.py \
  tests/test_auth_tokens.py
```

Output:
```text
852 passed, 3 warnings in 7.26s
```

Individual suite breakdown:
- `tests/test_refusal_copy.py`: **49 passed** (18 code×lang copy renders + 11 persona display strings + 18 contract schema validations + 1 YAML inventory check + 1 auto-answer aggregate contract check)
- `tests/test_role_escalation.py`: **77 passed**
- `tests/test_rbac_policy.py`: **323 passed**
- `tests/test_personas_v3.py`: **49 passed**
- `tests/test_self_scope.py`: **119 passed**
- `tests/test_persona_question_matrix.py`: **198 passed**
- `tests/test_degraded_copy.py`: **14 passed**
- `tests/test_catalog_consistency.py`: **3 passed**
- `tests/test_auth_tokens.py`: **20 passed**

---

## 5. G4 Round 1 Fixes (Backend — `docs/reviews/P2H.2.md` & Board #113)

| Item | Severity | Fix Implemented | Verification |
|---|---|---|---|
| **M1** | Must-fix | Replaced the legacy refusal block in `turn_runner.py:487-510` (`check_access` hook) with `build_refusal_contract()` so `spoken_summary`, `display_text`, and `access.reason` always render SPEC-06 `refusal_copy.yaml` (EN + HI) and `visual.title` is `"Access restricted"` (no `"Access Restricted (D1)"` or rule IDs in title/spoken/display). Also updated `validate_and_repair_contract()` (`answer_composer.py`) to overwrite legacy refusal prose/titles with SPEC-06 copy while preserving `access.code` and `access.rule_ref` for the `"Why?"` disclosure. | `test_m1_legacy_refusal_contract_repaired_to_spec06_without_rule_id_in_title_or_spoken` (EN + HI) & `test_m1_turn_runner_check_access_hook_emits_spec06_refusal` (EN + HI) — **4 / 4 passed** |
| **M4 (backend)** | Must-fix | Added `question_hi` to every `alternatives[]` item across all 9 codes in `app/brain/refusal_copy.yaml` and `app/semantic/refusal_copy.yaml`. Updated `render_refusal_copy()` (`answer_composer.py`) to select `question_hi` / `label_hi` when `lang == "hi"` and deduplicate `alternatives[]` against primary `alternative` by `(label, question)` so duplicate chips are never emitted. | `test_m4_refusal_copy_yaml_every_alternatives_item_has_question_hi_and_no_duplicates` — **passed** |
| **M5** | Must-fix | Made `"What is the POSH policy and reporting process?"` / `"POSH नीति और शिकायत प्रक्रिया क्या है?"` classify as `policy` (`allow` across all 11 personas) via `is_policy_process_question()` in `rbac.py`, `access_control.py`, and `planner.py` (while keeping case/record/count queries in `sensitive`). Added Hindi aggregate-pay (`"E{n} अधिकारियों का औसत मासिक मूल वेतन क्या है?"`), Hindi possessive `self`-scope (`"मेरा APAR इतिहास दिखाएँ"`, `"सितंबर की मेरी वेतन पर्ची दिखाएँ"`), and Hindi P&L / Annual Report (`"प्रकाशित वार्षिक रिपोर्ट से कंपनी की स्थिति का सारांश दें"`, `"कंपनी-स्तर का आय विवरण दिखाएँ"`) recognition across `rbac.py`, `access_control.py`, and `planner.py`. | `test_m5_every_chip_question_passes_real_gate_for_all_11_personas_and_both_langs` (`11 personas × 8 R-* codes × 2 langs = 176` parametrised test cases covering all primary + extra chips through both `planner.to_plan -> compiler.compile_spec -> rbac.decide` and `check_access`) — **176 / 176 passed** |
| **Should-fix #1** | Should-fix | Removed `"E2_HR"` / `"Pooja Verma"` default for unknown/omitted personas in `persona_display_info()` and `render_refusal_copy()` (`answer_composer.py`), using neutral fallback (`"Signed-in User"`, `"Current Role"`). | `test_should_fix_unknown_persona_uses_neutral_fallback_and_word_boundaries` — **passed** |
| **Should-fix #5** | Should-fix | Documented `R-PAY` `{n}` requester-grade fallback in `answer_composer.py` and `refusal_copy.yaml`. | Verified |
| **Should-fix #6** | Should-fix | Updated `_infer_refusal_code()` (`answer_composer.py`) to use word-boundary regexes (`\bpay\b`, `\bboard\s+note\b`, etc.) so `"display"` never matches `"pay"` and `"dashboard"` never matches `"board"`. | `test_should_fix_unknown_persona_uses_neutral_fallback_and_word_boundaries` — **passed** |
| **Should-fix (`ui_control.py`)** | Should-fix | Updated `UI_ACTIONS["persona"]` and `_ALIASES` in `yukti/backend/app/ui_control.py` to list all 11 canonical personas (including `"asha"` -> `"E3_FIN"`). | `test_should_fix_unknown_persona_uses_neutral_fallback_and_word_boundaries` — **passed** |

### Updated Backend Test Counts (G4 r1)
- `tests/test_refusal_copy.py`: **231 passed** (up from 49)
- Combined P2H.1 + P2H.2 backend suite (`test_refusal_copy.py`, `test_rbac_policy.py`, `test_persona_question_matrix.py`, `test_self_scope.py`, `test_role_escalation.py`, `test_auth_tokens.py`, `test_personas_v3.py`): **1,267 passed** in 4.14s.

