# Task Packet: `P2H.4` V19 turns 4–5: export intent + xlsx link; email agent; delete canned proposal

**Executor:** O→F (O: contract `artifacts[]`/`email_draft` types + RBAC on export; F: intent patterns, xlsx/eml writers, template, tests) · **Author:** O · **Date:** 2026-10-23
**Branch:** `v3/P2H-hr` · **Base SHA:** `<after P2H.3>` · **Max files changed:** 14 · **Budget:** ~80 tool calls · **Features:** FEAT-023, FEAT-027 · **Bugs:** BUG-10, BUG-11, BUG-12 · **Spec:** [SPEC-07 §4.4–4.5, §4.7](../../../specs/SPEC-07_v19_transfer_workflow_email.md), [SPEC-10 §4.1, §4.6, §4.9, §4.10](../../../specs/SPEC-10_export_suite.md) · **Behaviour:** [BEH-02.05–.08, .11–.15, .18–.19, .20–.24, .33–.35](../../../behaviour/BEH-02_v19_hr_transfer_chain.md)
**App root (quote it):** `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC`

## 1. Goal
"Export this as an Excel file… names, designations, ranks, tenure in Delhi" returns a formatted xlsx link with exactly those columns, and "draft an email to the Director HR…" returns an editable draft built from the cohort with the xlsx attached; canned proposal numbers are gone.

## 2. Context you need
- `ui_control.py:289-292` + `frontend/src/services/uiCommands.ts:251` (literal export phrases); `brain/pipeline.py:36` (`_DOC_RE`); `turn_runner.py:1140-1245, 1183-1187` (draft triggers → transfer_proposal); `tools/draft_document.py:54-63, 105-131` (static numbers); `tools/export_tool.py`; `main.py:325-380` (export/download routes); `RosterTable.tsx:338/567`.
- SPEC-07 §4.4 patterns + synonym map; §4.5 template table.

## 3. Files you may change
1. `yukti/contracts/intents/export_intent.json` (new, shared patterns)
2. `yukti/backend/app/ui_control.py` (load shared patterns; column parsing)
3. `yukti/frontend/src/services/uiCommands.ts` (load shared patterns)
4. `yukti/backend/app/brain/pipeline.py` (`_DOC_RE` email/letter/HI)
5. `yukti/backend/app/brain/email_agent.py` (new: build `email_draft` from cohort + artifact)
6. `yukti/backend/app/brain/templates/email_transfer_review.md` (+ `_hi.md`) (new)
7. `yukti/backend/app/tools/export_tool.py` (xlsx formatting subset per SPEC-10 §4.1; `.eml` writer; naming; masked source)
8. `yukti/backend/app/main.py` (`POST /api/export` body + `GET /api/export/{export_id}`; audit row)
9. `yukti/backend/app/tools/draft_document.py` (delete canned `transfer_proposal` numbers/template)
10. `yukti/backend/app/turn_runner.py` (remove "transfer → transfer_proposal" route and BUG-12 literals at `:1541-1550, 1609-1613, 2192-2228` **only where they feed V19/draft answers**; others go to SPEC-11)
11. `yukti/contracts/answer_contract.schema.json` + `yukti/frontend/src/contracts/answerContract.ts` (**O only**: `artifacts[]` (SPEC-10 §5 shape), `ui_action.download`, `email_draft` — added additively as SPEC-03 §5.1 ledger rows, behind flag tokens `artifacts` / `email_draft` in `YUKTI_CONTRACT_V3_FIELDS`; no `contract_version` bump, P3.1 owns it)
12. `yukti/frontend/src/components/renderers/EmailDraftRenderer.tsx` (new: editable fields, .eml/.docx/mailto buttons)
13. `yukti/backend/tests/test_export_intent.py`, `tests/test_email_agent.py`, `tests/test_v19_rbac_matrix.py` (new)
14. `yukti/frontend/src/services/__tests__/exportIntent.test.ts` (new, same fixture)

## 4. Do NOT touch
- RBAC policy decisions, PDF/CSV/PNG (P4.6/P4.7). Contract files only by O. No git/deploy/bq/destructive commands.

## 5. Exact requirements
1. Intent fixture: 40 positive (20 EN, 10 Hinglish, 10 Devanagari) + 10 negative from SPEC-07 AC4; columns parsed per synonym map; unknown words → caveat.
2. Export rows = active cohort, post-`enforce_contract`; xlsx per SPEC-10 §4.1 (title rows, frozen A5, widths, `0.0` tenure, Definition sheet); file name per SPEC-10 §4.9; `_aggregate` suffix when masked; audit row.
3. Email draft fields/template per SPEC-07 §4.5; numbers only from cohort; attachment = latest xlsx (auto-create if absent); `.eml` with `X-Unsent: 1`; `.docx` letter; `mailto:` ≤ 1,800 chars + toast.
4. Junior/DIR_FIN/E*_FIN behaviour per SPEC-07 §4.7 (T4, T5).
5. Delete canned "AGT Proposal FY27" and the 401/146 figures.

## 6. Examples
```
"Can you export this as an Excel file? Their names, their designations, their ranks from E1 to whatever level, and their tenure in Delhi"
→ header: Name | Designation | Level | Tenure in Delhi (yrs); rows = T3 row_count
"excel mein export karo, sirf naam aur Delhi tenure" → Name | Tenure in Delhi (yrs)
"show crude oil exports for FY25" → not an export intent
```

## 7. Acceptance criteria
- [ ] SPEC-07 AC 4–7 (intent 40/40 + 0/10 negatives; header + values match; email checks; 55 RBAC cases).
- [ ] `grep -nE "\b401\b|\b146\b" yukti/backend/app/tools/draft_document.py` → 0; template contains no counts.
- [ ] `.eml` parsed by Python `email`: 1 xlsx attachment; `X-Unsent: 1`.
- [ ] `tsc`, `lint:tokens` clean.

## 8. Self-check commands
```bash
cd "<app root>/yukti/backend" && .venv/bin/python -m pytest -q tests/test_export_intent.py tests/test_email_agent.py tests/test_v19_rbac_matrix.py tests/test_v19_chain.py tests/test_export_security.py
cd "<app root>/yukti/frontend" && npx tsc --noEmit && npx vitest run src/services/__tests__/exportIntent.test.ts && npm run -s lint:tokens && echo SELF_CHECK_OK
```

## 9. Stop-and-ask triggers
- A BUG-12 literal also feeds non-V19 answers (list; leave for SPEC-11/P5).
- `vitest` not installed (report; don't add deps).

## 10. Report format
- **Files changed** · **Self-check output** · **Sample xlsx/eml paths (scratch, not repo)** · **Acceptance criteria** ✅/❌ · **Open questions**
