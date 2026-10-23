# Task Packet: `P2H.2` Persona picker, `/api/auth/me` banner, refusal UX copy (EN/HI)

**Executor:** O→F (O fixes the API shapes and copy table; F builds UI + copy wiring) · **Author:** O · **Date:** 2026-10-23
**Branch:** `v3/P2H-hr` · **Base SHA:** `<after P2H.1>` · **Max files changed:** 8 · **Budget:** ~50 tool calls / stop after 2 failed self-checks · **Features:** FEAT-017 · **Spec:** [SPEC-06 §4.4, §4.6](../../../specs/SPEC-06_personas_identity_rbac_v3.md) · **Behaviour:** [BEH-01.01–.08, .60–.64](../../../behaviour/BEH-01_persona_matrix.md)
**App root (quote it):** `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC`

## 1. Goal
Users sign in by picking one of 11 personas (demo), the banner reflects the signed principal, and every refusal uses the SPEC-06 copy with an alternative.

## 2. Context you need
- `yukti/frontend/src/components/TopBar.tsx:26-31` (persona switcher), `PersonaBanner.tsx:15-34`, `renderers/RefusalRenderer.tsx`, `src/contracts/answerContract.ts` (refusal visual).
- Backend `auth.py` routes from P0.4/P2H.1; `answer_composer.py:31` (persona display strings).

## 3. Files you may change
1. `yukti/frontend/src/components/PersonaPicker.tsx` (new: modal list of 11, grouped Leadership / HR / Finance)
2. `yukti/frontend/src/components/TopBar.tsx` ("Sign in as…" replaces the switcher; hidden when `auth_mode=iap`)
3. `yukti/frontend/src/components/PersonaBanner.tsx` (reads `/api/auth/me`)
4. `yukti/frontend/src/components/renderers/RefusalRenderer.tsx` (copy + alternative chip/auto-answer + "Why?" disclosure)
5. `yukti/backend/app/brain/refusal_copy.yaml` (new: SPEC-06 §4.6 table, EN + HI)
6. `yukti/backend/app/answer_composer.py` (use copy file; 11 display strings from `app_users.yaml`)
7. `yukti/frontend/tests/persona_picker.spec.ts` (Playwright)
8. `yukti/backend/tests/test_refusal_copy.py` (new)

## 4. Do NOT touch
- Policy decisions, auth token code, contract schema (refusal fields already in SPEC-06 §5; if `answerContract.ts` lacks `alternative`, stop and ask O). No git/deploy/bq/destructive commands.

## 5. Exact requirements
1. Picker → `POST /api/auth/session` → reload feed (cleared) → banner shows display name + functional designation + "Illustrative identity" tooltip.
2. No UI path changes persona except the picker; remove any client handling of `ui_action.set_persona` for non-admin.
3. Refusal: first line from `refusal_copy.yaml` by code + language; alternative rendered as chip (click sends the alternative question) or the auto-answer visual below; "Why?" shows `rule_ref`.
4. Copy strings exactly as SPEC-06 §4.6 (EN + HI), placeholders `{display_name}`, `{designation}` filled.

## 6. Examples
```
E2_HR asks Q05 → RefusalRenderer line 1 = R-NAMED EN copy; AGG table rendered beneath; "Why?" → "D-11"
Hindi question → HI copy
```

## 7. Acceptance criteria
- [ ] Playwright: pick E1_FIN → banner "E1_FIN" display name → ask Q05 → R-NAMED copy + AGG table (screenshot light + dark).
- [ ] All 9 refusal codes × 2 languages render from YAML (unit test 18/18).
- [ ] `tsc`, `lint:tokens`, `lint:contrast` clean.

## 8. Self-check commands
```bash
cd "<app root>/yukti/backend" && .venv/bin/python -m pytest -q tests/test_refusal_copy.py
cd "<app root>/yukti/frontend" && npx tsc --noEmit && npm run -s lint:tokens && npm run -s lint:contrast | tail -1 && echo SELF_CHECK_OK
```

## 9. Stop-and-ask triggers
- Contract type changes needed; design tokens missing for the picker.

## 10. Report format
- **Files changed** · **Self-check output** · **Screenshots** · **Acceptance criteria** ✅/❌ · **Open questions**
