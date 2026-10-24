# G4 Review: `P2F.4` — Variance-Attribution & PBT Bridge Engine

**Final Verdict (Round 2): `APPROVE`** — **All 3 Round 1 blocking defects (`P2F4-B1`..`P2F4-B3`) have been resolved in `yukti/backend/app/agents/fin_diagnostics/variance.py` and `yukti/backend/tests/agents/test_variance.py`. All 10/10 unit and real-data tests in `test_variance.py` pass (`pytest -v yukti/backend/tests/agents/test_variance.py`), including historical PBT bridge closure (`closure_error <= 0.10`) across all 9 FY pairs (`FY18`..`FY26`) on `financial_ssot/out/fact_snapshot.parquet`, `M-REV-PV` / `M-REV-PVF` / `M-SUB` / `M-POLICY` / `M-LEVY` / `M-UNIT` / `M-TAX` decompositions, `PL.DDA` (Note 37), `PL.FIN_COST` (Note 36), `PL.PAT` full bridge, missing-quantity degradation, `BridgeDoesNotClose` guard, and determinism.**

- **Reviewer:** `reviewer-p2h2` (independent G4 review)
- **Worktree:** `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC__v3P2F`
- **Branch:** `v3/P2F-fin-diag` (`0551174` + Round 2 fixes)
- **Files reviewed:**
  - [variance.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/agents/fin_diagnostics/variance.py)
  - [`__init__.py`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/agents/fin_diagnostics/__init__.py)
  - [test_variance.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/tests/agents/test_variance.py)
  - [ten_year_fy25_fy26.csv](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/tests/agents/fixtures/ten_year_fy25_fy26.csv)

---

## Round 2 Verification Summary (`APPROVE`)

| Blocker ID | Summary | Resolution Verified |
| :--- | :--- | :---: |
| **`P2F4-B1`** | `_lookup_row` failed on non-monetary rows (`QTY.*`, `PROD.*`) in `fact_snapshot.parquet` (`value_inr_cr = NaN`) and lacked `period_type == "annual"` filter | **RESOLVED** (`variance.py:186-210`): Filters `period_type == "annual"` and iterates `("value_inr_cr", "value", "value_native")` for the first non-null numeric value. |
| **`P2F4-B2`** | `pbt_bridge` raised `BridgeDoesNotClose` for `FY18..FY21` on `fact_snapshot.parquet` due to mixed `PL.OTHER_INCOME` vintage and 3-dp vs 1-dp rounding | **RESOLVED** (`variance.py:685-730`, `test_variance.py:225-235`): Prefers 10-year `PL.DIVIDEND_INCOME_10YR + PL.OTHER_NON_OP_INCOME_10YR` when available and rounds line deltas at 1 dp. Verified `closure_error <= 0.10` across all `FY18..FY26` bridges in `test_fact_snapshot_parquet_historical_bridges`. |
| **`P2F4-B3`** | Missing `PL.DDA` (Note 37), `PL.FIN_COST` (Note 36), and `PL.PAT` decompositions + exact `Σ components == delta` telescoping in `M-LEVY` / `M-UNIT` / `M-TAX` / `M-REV-PVF` | **RESOLVED** (`variance.py:250-267, 315-318, 405-406, 502-579, 600-601, 628-629`): Added `PL.PAT` full bridge + `M-TAX`, `PL.DDA` (`N37.*`), `PL.FIN_COST` (`N36.*`), and exact remainder telescoping. |

---

## Round 1 Historical Findings (All Resolved in Round 2)

1. **`P2F4-B1` (Resolved):** `_lookup_row` (`variance.py:186-210`) now filters `period_type == "annual"` and resolves `("value_inr_cr", "value", "value_native")`.
2. **`P2F4-B2` (Resolved):** `pbt_bridge` (`variance.py:685-730`) closes within `<= 0.10 ₹ cr` across all `FY18..FY26` bridges on `financial_ssot/out/fact_snapshot.parquet`.
3. **`P2F4-B3` (Resolved):** `attribute()` (`variance.py:250-640`) supports `PL.PAT`, `PL.DDA` (`N37.*`), `PL.FIN_COST` (`N36.*`), and exact remainder closure on `M-REV-PVF`, `M-LEVY`, `M-UNIT`, and `M-TAX`.
