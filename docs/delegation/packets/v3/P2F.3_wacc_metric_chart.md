# Task Packet: `P2F.3` WACC metric, chart and Shapley attribution

**Executor:** O (semantic model + planner metric); the Shapley function can be delegated to F as a sub-task with the fixture below · **Author:** O · **Date:** 2026-10-23
**Branch:** `v3/P2F-fin-diag` · **Base SHA:** `e7de82f` (+ P1.9 loaded) · **Max files changed:** 6 · **Budget:** ~40 tool calls / stop after 2 failed self-checks · **Features:** FEAT-024 · **Spec:** [SPEC-02](../../../specs/SPEC-02_wacc_dcf_engine.md) §5 · **Checklist:** row `P2F.3`
**App root (quote it):** `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC`

## 1. Goal (one sentence)
Answer WACC 5/10-yr, build-up and "why high/low" questions from `fact_wacc_annual` with the right visuals and a Modelled badge.

## 2. Context you need
- SPEC-02 §3.2 (table), §5.1–§5.3
- `brain/semantic_model.yaml`, `planner.py` (the fin_kw guard at ~466-480 that misroutes "why is WACC high")

## 3. Files you may change
- `brain/semantic_model.yaml`, `brain/planner.py`, `brain/compiler.py`
- new `app/agents/fin_diagnostics/wacc_attribution.py`, new `tests/test_wacc_metric.py`, `tests/agents/test_wacc_shapley.py`

## 4. Do NOT touch
- WACC computation itself (P1.8), RBAC
- No `git commit` / `push` / `reset` / `checkout` / `stash`, no deploys, no BigQuery writes, no destructive commands. Leave changes uncommitted. Any file not in §3 → stop and report.

## 5. Exact requirements
1. Metrics `wacc_pct`, `wacc_components`, `wacc_build_up`, `wacc_change_attribution` per SPEC-02 §5.1.
2. Shapley over 5 factors (rf_used, erp_total, beta_adj, kd_after_tax, weights), all 120 orderings, exact sum.
3. "why is WACC high" never returns the P&L (fix the guard).

## 6. Examples / reference patterns
```
Shapley fixture: WACC_a from (rf 5%, erp 7%, β 1.0, kd_at 4%, wE 0.9) to WACC_b (rf 5.5%, erp 7.5%, β 1.1, kd_at 4.2%, wE 0.88)
→ Σ contributions = WACC_b − WACC_a (±1e-9); rf, erp, β, kd contributions > 0; weights contribution < 0 (equity weight falls while Ke > Kd after tax)
```

## 7. Acceptance criteria (copied into the review)
- [ ] SPEC-02 AC-02, AC-03
- [ ] BEH-03.05 and 03.06 pass

## 8. Self-check commands
```bash
cd "<app root>/yukti/backend" && .venv/bin/python -m pytest -q tests/test_wacc_metric.py tests/agents/test_wacc_shapley.py
cd "<app root>" && git status --short
```

## 9. Stop-and-ask triggers
- `fact_wacc_annual` rows are `verified=FALSE` (render the caveat; do not hide)

## 10. Report format
- **Files changed** · **Self-check output** · **Acceptance criteria** ✅/❌ with evidence · **Open questions / deviations**
