# Task Packet: `P2F.4` Variance-attribution engine (deterministic, pure Python)

**Executor:** F (`flash`) · **Author:** O · **Date:** 2026-10-23
**Branch:** `v3/P2F-fin-diag` · **Base SHA:** `e7de82f` (+ P1 merged: SSOT snapshot available) · **Max files changed:** 5 (all new) · **Budget:** ~45 tool calls / stop after 2 failed self-checks · **Features:** FEAT-024 · **Spec:** [SPEC-08](../../../specs/SPEC-08_v20_finance_diagnostics.md) §6.1, §6.5 · **Checklist:** row `P2F.4`
**App root (quote it):** `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC`

## 1. Goal (one sentence)
Implement `variance.py`, which decomposes the YoY change of any P&L line (and the full PBT bridge) into the components of SPEC-08 §6.1 using only verified SSOT rows, with exact closure and full input lineage.

## 2. Context you need
- SPEC-08 §6.1 (methods M-REV-PVF, M-REV-PV, M-LEVY, M-POLICY, M-UNIT, M-SUB, M-ONEOFF, M-TAX, M-BRIDGE), §6.5 (worked example).
- SSOT columns: SPEC-01 §5.1; line codes SPEC-01 §4.3 table + §5.2 (e.g. `PL.REV_OPS`, `REV.CRUDE`, `QTY.CRUDE_SOLD`, `LEVY.ROYALTY`, `PL.DDA`, `PL.FIN_COST`, `PL.PBT`, `PL.TAX`, `PL.PAT`).
- Input = a pandas DataFrame shaped like `financial_ssot/out/fact_snapshot.parquet` (use `v_fin_trend_latest` semantics: `verified & is_latest_vintage`).

## 3. Files you may change (new)
- `yukti/backend/app/agents/__init__.py` (empty, if absent)
- `yukti/backend/app/agents/fin_diagnostics/__init__.py`
- `yukti/backend/app/agents/fin_diagnostics/variance.py`
- `yukti/backend/tests/agents/test_variance.py`
- `yukti/backend/tests/agents/fixtures/ten_year_fy25_fy26.csv` (the FY25/FY26 rows listed in §6 below, as `line_code,fiscal_year,value_inr_cr,source_doc,source_page_label`)

## 4. Do NOT touch
Planner, compiler, narrator, contract, RBAC, frontend, any existing file. No LLM, no BigQuery, no network, no git, no deploys.

## 5. Exact requirements
1. API: `attribute(df, line_code, fy_to, fy_from=None, scope="standalone") -> list[VarianceRow]` and `pbt_bridge(df, fy_to, fy_from=None, scope="standalone") -> Bridge` (ordered rows + `start`, `end`, `closure_error`). `VarianceRow` fields exactly as SPEC-08 §6.1 table.
2. A method is used only if **all** its inputs exist; otherwise degrade (`M-REV-PVF` → `M-REV-PV` → `sub_line` → `other_unexplained`), and set `coverage='partial'` with an explicit `other_unexplained` row so Σ components = Δ exactly.
3. `impact_on_pbt_inr_cr`: revenue/other income = +Δ; cost lines (levies, opex, exploration, provisions, exchange loss, other expenses, DD&A, finance costs) = −Δ.
4. Bridge closure: `|Σ impacts − ΔPBT| ≤ 0.1 ₹ cr`, else raise `BridgeDoesNotClose` (never plug).
5. Ranking by `|impact_on_pbt|` descending.
6. Deterministic: same input → identical output (order + values).

## 6. Examples (fixture values: AR FY26 10-yr table, ₹ cr = ₹ mn / 10)
```
FY26 / FY25: PL.REV_OPS 132508.1 / 137846.3; PL.OTHER_INCOME (dividend 4806.8 + other 5549.0) / (3460.4 + 7019.0);
LEVY total 26147.6 / 30968.0 (royalty 12965.1/13368.0; OIDB 13033.5/13480.2; NCCD 86.0/87.4; other incl SAED 63.0/4032.4);
opex 28208.5/27478.4; exploration 9728.8/9825.8 (survey 1492.8/2345.8; wells 8236.0/7480.0); provisions 3947.6/2805.2;
exchange loss 2698.9/767.2; other expenses 54.5/764.9; DD&A 25133.8/24352.4; finance 4529.3/4604.0; PBT 42414.9/46759.8; tax 9520.9/11149.5; PAT 32894.0/35610.3;
REV.CRUDE 83810.2/89535.3; REV.GAS 36329.9/33817.8; REV.VAP 11878.5/14007.9; QTY.CRUDE_SOLD 18.79/18.71 MMT; QTY.GAS_SOLD 15.491/15.510 BCM
Expected pbt_bridge(FY26): start 46759.8, end 42414.9, Δ −4344.9; impacts: revenue −5338.2, levies +4820.4, exchange loss −1931.7,
provisions −1142.4, DD&A −781.4, opex −730.1, other expenses +710.4, other income −123.7, exploration +97.0, finance +74.7 (±0.1)
Expected attribute(REV.CRUDE, FY26) with no realisation data: method M-REV-PV, volume +382.8, price_incl_fx −6107.9 (±0.1)
Expected attribute(REV.GAS, FY26): volume −41.4, price_incl_fx +2553.5
Expected attribute(LEVY.OTHER, FY26): M-POLICY, policy_levy −3969.4 (impact on PBT +3969.4)
```

## 7. Acceptance criteria
- [ ] All §6 expectations asserted
- [ ] Degradation test: drop `QTY.CRUDE_SOLD` → crude revenue becomes `sub_line`/`other_unexplained` with `coverage='partial'`, still closes
- [ ] `BridgeDoesNotClose` raised when a cost line is removed from the fixture
- [ ] Determinism test (two runs equal)
- [ ] Only §3 files created

## 8. Self-check commands
```bash
cd "<app root>/yukti/backend" && .venv/bin/python -m pytest -q tests/agents/test_variance.py
cd "<app root>" && git status --short
```

## 9. Stop-and-ask triggers
A line code in §6 is missing from the SSOT dim (report, don't invent); closure fails on real data by > ₹0.1 cr; need a file outside §3.

## 10. Report format
- **Files changed** · **Self-check output** · **Acceptance criteria** ✅/❌ · **Open questions / deviations**
