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
