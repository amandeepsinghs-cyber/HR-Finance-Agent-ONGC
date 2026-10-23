# Task Packet: `P2F.6` Top-5 action generator (lever evaluator + delegation table)

**Executor:** O→F. **O** authors `levers.yaml` (SPEC-08 §7.1; sponsor reviews the assumption %). **O** also adds `visual.type="actions"` + the SPEC-08 §7.3 payload to the contract as SPEC-03 §5.1 ledger row `actions` (additive, flag token `actions`, no `contract_version` bump) before F starts. **F** (`flash`) implements the evaluator and tests from this packet. · **Author:** O · **Date:** 2026-10-23
**Branch:** `v3/P2F-fin-diag` · **Base SHA:** `e7de82f` (+ P1, P2F.4) · **Max files changed:** 4 · **Budget:** ~40 tool calls / stop after 2 failed self-checks · **Features:** FEAT-024 · **Spec:** [SPEC-08](../../../specs/SPEC-08_v20_finance_diagnostics.md) §7 · **Checklist:** row `P2F.6`
**App root (quote it):** `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC`

## 1. Goal (one sentence)
Evaluate the lever library against verified SSOT rows for a given FY and return ≤ 5 ranked, owner-diverse actions with ₹ impact ranges, KPIs and evidence, plus the "five things for others to act on" delegation table, as the `actions` payload of SPEC-08 §7.3.

## 2. Context you need
- SPEC-08 §7.1 (levers L01–L10), §7.2 (selection), §7.3 (payload schema), §7.4 (persona variants).
- `yukti/backend/app/agents/fin_diagnostics/levers.yaml` (authored by O before you start; schema: `id, title, owner, trigger: {expr, inputs[]}, impact: {low_expr, mid_expr, high_expr, kind}, kpi, what_to_do_template, horizon_days, confidence_base, uses_assumption: bool, uses_synthetic: bool`).
- `variance.py` (P2F.4) for context only.

## 3. Files you may change
- `yukti/backend/app/agents/fin_diagnostics/actions.py` (new)
- `yukti/backend/app/agents/fin_diagnostics/expr.py` (new: a **safe** arithmetic evaluator over named inputs; no `eval`/`exec`; supports `+ - * / ( ) min max abs median5 avg5 yoy`)
- `yukti/backend/tests/agents/test_actions.py` (new)
- `yukti/backend/tests/agents/fixtures/levers_fixture.yaml` (new, copy of 3 levers for unit tests)

## 4. Do NOT touch
`levers.yaml` (O owns), contract schema, RBAC, narrator, any other file. No LLM, no BigQuery, no git, no deploys.

## 5. Exact requirements
1. `generate_actions(df, fy, persona, levers_path, ar_evidence_fn=None) -> dict` matching SPEC-08 §7.3 JSON (`fy`, `items[≤5]`, `delegation_table`).
2. Score = `impact_mid × confidence`; confidence = `confidence_base` × 0.7 if `uses_assumption` × 0.5 if `uses_synthetic` (multiplicative). Select by score with ≤ 3 items per owner. If persona = DIR_HR and L07 fires, L07 is included. If persona ∈ E1–E4_FIN or E1–E4_HR (agent callable by all 11; SPEC-03 §4.2, SPEC-08 §7.4), drop the `owner` and `delegation_table.owner` values (set to `"for discussion"`).
3. If fewer than 5 fire, return what fires plus `note = "Only N levers are triggered by <FY> data"`. No filler.
4. `what_to_do` is filled from the template with numbers formatted Indian-style (₹ cr, 1 dp); every number used is added to `evidence` as `{type:"data", ref:"<line_code> <FY> = <value> (<source_doc> p.<page>)"}`.
5. `ar_evidence_fn(lever_id, fy)` (injected; returns `[{ref}]` or `[]`) adds `{type:"ar"}` evidence; tests pass a stub.
6. Deterministic ordering (tie-break by lever id).

## 6. Examples (FY26, from AR FY26 10-yr table)
```
L02 receivables: debtor days FY26 32 vs FY25 29 (RATIO.DEBTOR_DAYS) → fires; release = (32 − 29) × 132,508.1 / 365 = ₹1,089.1 cr one-off; owner DIR_FIN; KPI "Debtor days"
L08 FX: exchange loss 2,698.9 vs 767.2 → fires (> 1,000 and > 2× prior)
L09 provisions: 3,947.6 vs 2,805.2 (+40.7%) → fires
L06 exploration: wells write-off FY26 8,236.0 vs 5-yr average (FY22–FY26 from the 10-yr table) → fires only if > 20% above the average
```

## 7. Acceptance criteria
- [ ] L02/L08/L09 fire on the FY26 fixture with the values above (L02 release ±₹0.1 cr)
- [ ] Owner-diversity, DIR_HR and E-level rules tested
- [ ] `expr.py` rejects attribute access, function calls outside the whitelist, and names not in inputs (tests)
- [ ] Output validates against the SPEC-08 §7.3 schema (jsonschema in the test)
- [ ] Only §3 files changed

## 8. Self-check commands
```bash
cd "<app root>/yukti/backend" && .venv/bin/python -m pytest -q tests/agents/test_actions.py
cd "<app root>" && git status --short
```

## 9. Stop-and-ask triggers
`levers.yaml` uses an input not present in the SSOT; a trigger is ambiguous; need a file outside §3.

## 10. Report format
- **Files changed** · **Self-check output** · **Acceptance criteria** ✅/❌ · **Open questions / deviations**
