# G4 Review: `P2F.4` — Variance-Attribution & PBT Bridge Engine (`0551174`)

**Verdict: `CHANGES REQUESTED`** — **All 9 unit tests against the 2-year CSV fixture pass (`test_variance.py`), reproducing the `SPEC-08 §6.5` FY26-vs-FY25 worked example, `M-REV-PV` crude/gas decompositions, `M-POLICY` SAED attribution, missing-quantity degradation, `BridgeDoesNotClose` guard, and determinism. However, testing `variance.py` against the actual `financial_ssot/out/fact_snapshot.parquet` (required by `Packet P2F.4 §2` and `SPEC-08 §8 AC-04`) reveals 3 blocking defects (`P2F4-B1` through `P2F4-B3`) that break quantity lookups (`QTY.*`), `FY18–FY21` PBT bridge closure, and `PL.DDA` / `PL.FIN_COST` / `PL.PAT` decompositions.**

- **Reviewer:** `reviewer-p2h2` (independent G4 review)
- **Worktree:** `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC__v3P2F`
- **Branch / Commit:** `v3/P2F-fin-diag` @ `0551174`
- **Files reviewed:**
  - `yukti/backend/app/agents/__init__.py`
  - `yukti/backend/app/agents/fin_diagnostics/__init__.py`
  - `yukti/backend/app/agents/fin_diagnostics/variance.py`
  - `yukti/backend/tests/agents/fixtures/ten_year_fy25_fy26.csv`
  - `yukti/backend/tests/agents/test_variance.py`

---

## Must-Fix (Blocking)

### 1. `P2F4-B1` (blocking — `yukti/backend/app/agents/fin_diagnostics/variance.py:182-205`): `_lookup_row` fails on `fact_snapshot.parquet` for all non-monetary rows (`QTY.*`, `PROD.*`, `REALISATION.*`, `FX.*`) and does not filter `period_type == "annual"`
- **Defect:**
  1. At `variance.py:202-204`, `_lookup_row` selects the value column via:
     ```python
     val_col = "value_inr_cr" if "value_inr_cr" in row else ("value" if "value" in row else None)
     if val_col and pd.notna(row[val_col]):
         val = float(row[val_col])
     ```
     In `financial_ssot/out/fact_snapshot.parquet` (the DataFrame schema specified in `Packet P2F.4 §2`), the column `"value_inr_cr"` exists on every row (`"value_inr_cr" in row` is always `True`), and is `NaN` for all non-monetary quantity/production/rate lines (`QTY.CRUDE_SOLD`, `QTY.GAS_SOLD`, `QTY.VAP_SOLD`, `PROD.*`), which store their values in `row["value"]` and `row["value_native"]`. Consequently, on `fact_snapshot.parquet`, `attribute(df, "REV.CRUDE", "FY26")` and `attribute(df, "REV.GAS", "FY26")` return `(None, None)` for `QTY.CRUDE_SOLD` / `QTY.GAS_SOLD` and degrade to `other_unexplained` (`coverage='partial'`) instead of `M-REV-PV`!
  2. At `variance.py:182-189`, `_lookup_row` filters `scope`, `verified`, and `is_latest_vintage`, but does not filter `period_type == "annual"`, risking false matches against `opening` or `quarter` rows in `fact_snapshot.parquet`.
- **Fix:**
  - In `_lookup_row` (`variance.py:182-189`), add:
    ```python
    if "period_type" in sub.columns:
        sub = sub[sub["period_type"] == "annual"]
    ```
  - At `variance.py:202-205`, resolve the first non-null numeric column across `("value_inr_cr", "value", "value_native")`:
    ```python
    val = None
    for vc in ("value_inr_cr", "value", "value_native"):
        if vc in row and pd.notna(row[vc]):
            val = float(row[vc])
            break
    if val is not None:
    ```

### 2. `P2F4-B2` (blocking — `yukti/backend/app/agents/fin_diagnostics/variance.py:581-680`): `pbt_bridge` raises `BridgeDoesNotClose` for `FY18`, `FY19`, `FY20`, and `FY21` on `fact_snapshot.parquet` (violating `SPEC-08 §8 AC-04`)
- **Defect:** `SPEC-08 §8 AC-04` requires: *"`M-BRIDGE` closes to ΔPBT within ₹0.1 cr for every FY pair FY18–FY26"*. When run against `financial_ssot/out/fact_snapshot.parquet`, `pbt_bridge(df, fy)` currently raises `BridgeDoesNotClose` on 4 of the 9 required FY pairs:
  - `FY18`: `sum of impacts 3677.2 != delta PBT 3677.0 (error 0.20 > 0.1 ₹ cr)`
  - `FY19`: `sum of impacts 11390.3 != delta PBT 11136.6 (error 253.70 > 0.1 ₹ cr)`
  - `FY20`: `sum of impacts -20400.1 != delta PBT -19641.2 (error 758.90 > 0.1 ₹ cr)`
  - `FY21`: `sum of impacts -3479.9 != delta PBT -3985.1 (error 505.20 > 0.1 ₹ cr)`
- **Root cause:**
  1. In `fact_snapshot.parquet`, `FY19` and `FY20` have `PL.OTHER_INCOME` from an older Schedule III vintage (`7519.008` in `FY19`, `6105.03` in `FY20`), whereas the 10-year summary table (`PL.TOTAL_INCOME - PL.REV_OPS`) equals `PL.DIVIDEND_INCOME_10YR + PL.OTHER_NON_OP_INCOME_10YR` (`3105.4 + 4159.8 = 7265.2` in `FY19`, `2466.4 + 4143.8 = 6610.2` in `FY20`). Because `variance.py:594-608` (and `:244-258`) checks `PL.OTHER_INCOME` first and only sums `PL.DIVIDEND_INCOME_10YR + PL.OTHER_NON_OP_INCOME_10YR` when `PL.OTHER_INCOME` is `None`, it mixes 10-year summary expense lines (`PL.OPEX_10YR`, `PL.EXCHANGE_LOSS_10YR`, `PL.OTHER_EXP_10YR`) with non-10-year `PL.OTHER_INCOME`.
  2. In `fact_snapshot.parquet`, `PL.PBT`, `PL.REV_OPS`, `PL.DDA`, `PL.FIN_COST`, and `PL.PROVISIONS_WRITEOFF` carry 3-dp Schedule III precision while the `*_10YR` lines carry 1-dp (`₹ mn / 10`) precision. Rounding `v_to - v_from` instead of `round(v_to, 1) - round(v_from, 1)` causes cumulative 1-dp rounding drift (`0.20` in `FY18`, `0.10` in `FY26`).
- **Fix:**
  1. In `pbt_bridge` (`variance.py:597-608`) and `attribute` (`variance.py:249-259`), when `canonical_code == "PL.OTHER_INCOME"` (or `norm_code == "PL.OTHER_INCOME"`), prefer `d_to + o_to` and `d_from + o_from` (`PL.DIVIDEND_INCOME_10YR + PL.OTHER_NON_OP_INCOME_10YR`) whenever all four 10-year component values exist, falling back to `PL.OTHER_INCOME` otherwise.
  2. In `pbt_bridge`, normalize `start_pbt = round(float(pbt_from), 1)`, `end_pbt = round(float(pbt_to), 1)`, and `line_delta = round(round(v_to, 1) - round(v_from, 1), 1)`. Verified against `fact_snapshot.parquet`: this makes `pbt_bridge` close with `closure_error == 0.0` on `FY19..FY26` and `0.10` (`<= 0.1`) on `FY18`.
  3. Add a test in `test_variance.py` that loads `financial_ssot/out/fact_snapshot.parquet` (using `pd.read_parquet` if `pyarrow` is installed, or via `sqlite3`/`duckdb`/CSV or `pytest.importorskip` fallback, or testing all `FY18..FY26` rows) and asserts `pbt_bridge` closes for every FY in `FY18..FY26` and `attribute(df, "REV.CRUDE", "FY26")` returns `M-REV-PV`.

### 3. `P2F4-B3` (blocking — `yukti/backend/app/agents/fin_diagnostics/variance.py:239-558`): Missing `PL.DDA` (`Note 37`), `PL.FIN_COST` (`Note 36`), and `PL.PAT` decompositions from `SPEC-08 §6.1`, plus 2-component rounding closure in `M-LEVY` / `M-UNIT` / `M-TAX` / `M-REV-PVF`
- **Defect:**
  1. `SPEC-08 §6.1` defines `M-SUB` decompositions for `PL.DDA` (Note 37: `N37.DEPLETION`, `N37.DEPR_ROU`, `N37.AMORT`, `N37.IMPAIR`) and `PL.FIN_COST` (Note 36: `N36.UNWIND_DECOM`, `N36.UNWIND_LEASE`), as well as full bridge support for `PL.PAT` (`SPEC-08 §6.1` line 76: *"or `PL.PBT`/`PL.PAT` for a full bridge"*). Currently `variance.py:239-241` has `# 1. PBT or PAT full bridge` but only checks `if norm_code == "PL.PBT":`, and `PL.DDA` / `PL.FIN_COST` fall through to `# 12. Default fallback` (`other_unexplained`).
  2. In `M-REV-PVF` (`variance.py:292-294`), `M-LEVY` (`:383-384`), `M-UNIT` (`:500-501`), and `M-TAX` (`:530-531`), each component is independently `round(..., 1)` instead of computing the last component as `round(delta - ..., 1)` (like `M-REV-PV` at line 315), which can violate `Packet P2F.4 §5.2` (*"so Σ components = Δ exactly"*) by `±0.1 ₹ cr`.
- **Fix:**
  1. Add `M-SUB` branches in `attribute()` for `PL.DDA` (checking `N37.DEPLETION`, `N37.DEPR_ROU`, `N37.AMORT`, `N37.IMPAIR`; if none exist in `df`, degrade to `other_unexplained` with `coverage='partial'`; if present with a non-zero residual vs `PL.DDA`, append an `other_unexplained` row with `coverage='partial'`) and `PL.FIN_COST` (checking `N36.UNWIND_DECOM`, `N36.UNWIND_LEASE`, with residual `other_unexplained` if `abs(residual) > 0.05` or degrading to `other_unexplained` when `N36.*` are absent).
  2. Support `norm_code == "PL.PAT"` in `attribute()` by taking the `pbt_bridge` rows plus the `PL.TAX` bridge row (`impact_inr_cr = tax_delta`, `impact_on_pbt_inr_cr = -tax_delta`, `method = "M-BRIDGE"`), sorted by `|impact_on_pbt_inr_cr|` descending.
  3. Set `rate_imp = round(delta - base_imp, 1)` in `M-LEVY` and `M-TAX`, `unit_imp = round(delta - act_imp, 1)` in `M-UNIT`, and `fx_imp = round(delta - vol_imp - price_imp, 1)` in `M-REV-PVF` so `Σ components == delta` identically.
