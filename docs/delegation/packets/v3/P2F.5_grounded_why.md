# Task Packet: `P2F.5` Grounded "why" answers: variance rows + AR chunks, non-circular grounding

**Executor:** O (narrator/grounding + retriever integration = Opus-only); R-O review · **Author:** O · **Date:** 2026-10-23
**Branch:** `v3/P2F-fin-diag` · **Base SHA:** `e7de82f` (+ P1.8, P2F.4) · **Max files changed:** 6 · **Budget:** ~50 tool calls / stop after 2 failed self-checks · **Features:** FEAT-024, FEAT-020 · **Spec:** [SPEC-08](../../../specs/SPEC-08_v20_finance_diagnostics.md) §6.2–§6.3 · **Checklist:** row `P2F.5`
**App root (quote it):** `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC`

## 1. Goal (one sentence)
Compose "why" answers from the variance engine's top drivers plus cited AR chunks, and replace the circular grounding whitelist with data-row-only grounding.

## 2. Context you need
- `brain/insight_context.py:138-233` (to delete), `brain/narrator.py` (grounding check), `app/knowledge/ar_retriever.py` (P1.8)
- SPEC-08 §6.2, §6.3; BUG-16

## 3. Files you may change
- `brain/narrator.py`, `brain/insight_context.py` (remove canned corpus paths), new `app/agents/fin_diagnostics/why.py`, `brain/pipeline.py` (route why-intents to `fin_diagnostics_agent` until the coordinator lands)
- new `tests/test_grounding_v3.py`, `tests/agents/test_why.py`

## 4. Do NOT touch
- Variance engine internals (P2F.4), RBAC, contract schema
- No `git commit` / `push` / `reset` / `checkout` / `stash`, no deploys, no BigQuery writes, no destructive commands. Leave changes uncommitted. Any file not in §3 → stop and report.

## 5. Exact requirements
1. Allowed-number set = variance rows + statement rows of the turn; quoted AR excerpts with a page cite are allowed as quotes.
2. Sentences with any other number are dropped and logged; > 1 drop → template-only narrative.
3. Retrieval filters: FY, driver line codes, sections mdna > directors_report > notes; top 2–3; cite `[AR FY26 p.N]`.
4. Unexplained remainder sentence when `coverage='partial'`.
5. Delete runtime reads of `financial_notes_corpus.jsonl`, `ssot_financial_line_context.json`, `FY_DIRECTOR_ACTIONS`.

## 6. Examples / reference patterns
```
Injected narrator output "Royalty rose to ₹15,280 crore" (FY24 value from the old JSON) → dropped (15,280 not in allowed set)
BEH-03.07 lead sentence numbers all ∈ allowed set
```

## 7. Acceptance criteria (copied into the review)
- [ ] SPEC-08 AC-05, AC-06, AC-08
- [ ] 20-question grounding test: 0 disallowed numbers reach the user

## 8. Self-check commands
```bash
cd "<app root>/yukti/backend" && .venv/bin/python -m pytest -q tests/test_grounding_v3.py tests/agents/test_why.py
cd "<app root>" && grep -rn "financial_notes_corpus\|ssot_financial_line_context\|FY_DIRECTOR_ACTIONS" yukti/backend/app
cd "<app root>" && git status --short
```

## 9. Stop-and-ask triggers
- Retrieval quality too low (< 1 relevant chunk in top 5 for 50% of test questions): report with examples

## 10. Report format
- **Files changed** · **Self-check output** · **Acceptance criteria** ✅/❌ with evidence · **Open questions / deviations**
