# Task Packet: `P2F.2` Multi-year Yahoo-style statement query + presenter emit

**Executor:** O (compiler/presenter); frontend StatementTable is P4.2 (SPEC-09) · **Author:** O · **Date:** 2026-10-23
**Branch:** `v3/P2F-fin-diag` · **Base SHA:** `e7de82f` (+ P1.10a) · **Max files changed:** 5 · **Budget:** ~40 tool calls / stop after 2 failed self-checks · **Features:** FEAT-024, FEAT-025 · **Spec:** [SPEC-08](../../../specs/SPEC-08_v20_finance_diagnostics.md) §4, [SPEC-09](../../../specs/SPEC-09_statement_visual_chart_portfolio.md) §4.1 · **Checklist:** row `P2F.2`
**App root (quote it):** `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC`

## 1. Goal (one sentence)
Return 1/2/5/10-column statements (newest → oldest) from the verified views with hierarchy, restated markers and per-column sources, emitted as `visual.type="statement"`.

## 2. Context you need
- `brain/compiler.py` statement templates (after P1.10a), `brain/presenter.py`
- SPEC-09 §4.1 statement payload; SPEC-01 §7.1 vintage rules

## 3. Files you may change
- `brain/compiler.py`, `brain/presenter.py`, `brain/semantic_model.yaml`
- new `tests/test_multiyear_statement.py`

## 4. Do NOT touch
- Frontend (P4.2), RBAC, contract fields other than using `statement` as defined in SPEC-09
- No `git commit` / `push` / `reset` / `checkout` / `stash`, no deploys, no BigQuery writes, no destructive commands. Leave changes uncommitted. Any file not in §3 → stop and report.

## 5. Exact requirements
1. `fy_range` → `v_fin_trend_latest`; single FY → `v_fin_statement_as_reported` + comparative column.
2. Rows ordered by `dim_financial_line.line_order`; `level`, `line_kind` passed through; lines missing for some FYs render `null` + footnote (no imputation).
3. `is_restated` → `†` footnote text per SPEC-01 §7.1; per-column `source` (doc + printed page).
4. Scope switch (`consolidated`) and Yahoo view (`v_fin_yahoo_view`, badge) supported.

## 6. Examples / reference patterns
```
5-yr P&L: columns [FY26, FY25, FY24, FY23*, FY22]; PL.REV_OPS [132508.1, 137846.3, 138402.1, 155517.3, 110345.4]; PL.OTHER_INCOME FY24 = 10735.5 with † "Restated in AR FY25 p.271; originally ₹10,778.19 cr (AR FY24 p.245)"
```

## 7. Acceptance criteria (copied into the review)
- [ ] SPEC-08 AC-03; BEH-03.02 and 03.03 values
- [ ] 10-yr view: FY17–FY21 show only 10-yr lines, others null + footnote

## 8. Self-check commands
```bash
cd "<app root>/yukti/backend" && .venv/bin/python -m pytest -q tests/test_multiyear_statement.py
cd "<app root>" && git status --short
```

## 9. Stop-and-ask triggers
- SPEC-09 payload field names differ from what the presenter can supply (align with the SPEC-09 author)

## 10. Report format
- **Files changed** · **Self-check output** · **Acceptance criteria** ✅/❌ with evidence · **Open questions / deviations**
