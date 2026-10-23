# Task Packet: `P2F.1` Year clarification (chips + voice) for statement requests

**Executor:** O (planner + contract `clarify` field = Opus-only); R-O review · **Author:** O · **Date:** 2026-10-23
**Branch:** `v3/P2F-fin-diag` · **Base SHA:** `e7de82f` (+ P1, BUG-20 fixed in P0) · **Max files changed:** 7 · **Budget:** ~50 tool calls / stop after 2 failed self-checks · **Features:** FEAT-024 · **Spec:** [SPEC-08](../../../specs/SPEC-08_v20_finance_diagnostics.md) §3 · **Checklist:** row `P2F.1`
**App root (quote it):** `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC`

## 1. Goal (one sentence)
When a statement is requested with no FY in the utterance or recent context, return a `clarify` contract with coverage-driven options and resolve the reply (chip, text or voice) deterministically.

## 2. Context you need
- `yukti/backend/app/brain/planner.py` (statement regex routes ~400–480), `pipeline.py:211-221` (statement-type clarification), `semantic/normalize.py` (`resolve_fy`, BUG-20)
- `yukti/contracts/answer_contract.schema.json` + frontend `answerContract.ts`
- SPEC-08 §3.1–§3.3; SPEC-11 §5 (coverage manifest supplies options)

## 3. Files you may change
- `brain/planner.py`, `brain/pipeline.py`, `semantic/normalize.py` (only if BUG-20 not yet fixed)
- `yukti/contracts/answer_contract.schema.json` (+ `clarify` only, additively, as SPEC-03 §5.1 ledger row `clarify`; emitted only when flag token `clarify` is in `YUKTI_CONTRACT_V3_FIELDS`; **do not** bump `contract_version` — P3.1 owns the bump), frontend `answerContract.ts` type + chip renderer for `clarify.options` (U5 chips component)
- new `tests/test_year_clarify.py`

## 4. Do NOT touch
- RBAC, compiler templates (P1.10a owns), other contract fields
- No `git commit` / `push` / `reset` / `checkout` / `stash`, no deploys, no BigQuery writes, no destructive commands. Leave changes uncommitted. Any file not in §3 → stop and report.

## 5. Exact requirements
1. Trigger rule exactly as SPEC-08 §3.1 (no FY in the utterance and none in the last 3 QuerySpecs).
2. Options generated from the coverage manifest (latest FY, latest−1, last 5, last 10), never literals.
3. `clarify.pending_spec` holds the statement QuerySpec; the next turn fills `fy`/`fy_range` from the reply via the §3.3 table; any other reply expires the clarify.
4. Voice: the same resolution runs on `ask_yukti` text.

## 6. Examples / reference patterns
```
"Can I see the income statement?" → clarify{slot:fiscal_period, options:[FY26 (latest), FY25 (last year), Last 5 years, Last 10 years]}
"the present year" → FY26 statement; "pichhle saal" → FY25; "2025" → FY25 ("FY2024-25 (year ended 31-Mar-2025)"); "5 saal" → FY22..FY26
```

## 7. Acceptance criteria (copied into the review)
- [ ] SPEC-08 AC-01 and AC-02 (12-row resolution table) pass
- [ ] Context carry-over: after a FY24 BS, "show the income statement" uses FY24 and says so
- [ ] v1/v2 contract fixtures still validate

## 8. Self-check commands
```bash
cd "<app root>/yukti/backend" && .venv/bin/python -m pytest -q tests/test_year_clarify.py tests/test_normalize.py
cd "<app root>/yukti/frontend" && npx tsc --noEmit
cd "<app root>" && git status --short
```

## 9. Stop-and-ask triggers
- Coverage manifest not yet available (use the SSOT `v_fin_coverage` snapshot instead, and record it)

## 10. Report format
- **Files changed** · **Self-check output** · **Acceptance criteria** ✅/❌ with evidence · **Open questions / deviations**
