# Independent G4 Review — P2F.3: WACC Metric, Chart, and 5-Factor Shapley Attribution

**Verdict: APPROVE**  
**Reviewer:** `reviewer-p16` (Independent G4 Reviewer, Role R)  
**Commit Reviewed:** `979b3d1` on branch `v3/P2F-fin-diag` (`HR and Finance_ONGC__v3P2F`)  
**Specs & Packet Referenced:** `SPEC-02` (§3.2, §5.1–§5.3, §11 `AC-02`, `AC-03`), `BEH-03.05`, `BEH-03.06`, `docs/delegation/packets/v3/P2F.3_wacc_metric_chart.md`

---

## 1. Executive Summary (BLUF)

**`P2F.3` (`979b3d1`) is APPROVED with zero blocking issues.**  
All 4 WACC templates (`wacc_pct`, `wacc_components`, `wacc_build_up`, `wacc_change_attribution`), the 5-factor 120-permutation Shapley attribution engine (`wacc_attribution.py`), the `planner.py` `fin_kw` guard fix ensuring `"why is WACC high"` never routes to `pnl_statement`, and the local snapshot execution fallback with `provenance_label = "modelled"` and `verified=FALSE` caveat handling satisfy `SPEC-02 §5.1–§5.3` and `Packet P2F.3`. All 21 unit tests (`18/18` in `tests/test_wacc_metric.py` and `3/3` in `tests/agents/test_wacc_shapley.py`) pass in `2.23s`.

---

## 2. Verification Matrix

| Requirement / Acceptance Criterion | Status | Evidence (`file:line`) |
|---|---|---|
| **Scope discipline (`Packet P2F.3 §3–§4`)**: Only the 6 authorized code/test files modified | **PASS** | `yukti/backend/app/agents/fin_diagnostics/wacc_attribution.py`, `yukti/backend/app/brain/semantic_model.yaml`, `yukti/backend/app/brain/planner.py`, `yukti/backend/app/brain/compiler.py`, `yukti/backend/tests/agents/test_wacc_shapley.py`, `yukti/backend/tests/test_wacc_metric.py` |
| **`SPEC-02 §5.1` / `AC-02` (`BEH-03.05`)**: 5-yr (`FY22–FY26`) and 10-yr (`FY17–FY26`) WACC queries route to `wacc_pct` with `chart_kind="line"`, returning `wacc_pct`, `ke_pct`, `kd_after_tax_pct`, and `provenance_label="modelled"` | **PASS** | `planner.py:504-513`, `compiler.py:592-629, 1710-1745`, `test_wacc_metric.py:26-44, 100-110, 142-165` |
| **`SPEC-02 §5.1`**: `"show the WACC build-up / drivers"` (standalone or follow-up) routes to `wacc_components` with `chart_kind="stacked_bar"` | **PASS** | `planner.py:489-495`, `compiler.py:631-671, 1747-1791`, `test_wacc_metric.py:46-61, 112-121, 167-179` |
| **`SPEC-02 §5.1`**: Single-year `"WACC FY24"` routes to `wacc_build_up` with `chart_kind="table"` and returns all 16 lineage rows from `fact_wacc_input` | **PASS** | `planner.py:496-503`, `compiler.py:673-705, 1793-1836`, `test_wacc_metric.py:63-70, 123-130, 181-193` |
| **`SPEC-02 §5.3` / `AC-03` (`BEH-03.06`)**: `"why was WACC high in FY23"` / follow-up `"Why was it high in FY23?"` routes to `wacc_change_attribution` (`FY22 -> FY23`, `chart_kind="waterfall"`) with 5-factor Shapley decomposition across all $5! = 120$ permutations | **PASS** | `wacc_attribution.py:129-302`, `planner.py:481-488`, `compiler.py:707-747, 1838-1860`, `test_wacc_metric.py:72-90, 195-248` |
| **`Packet P2F.3 §5.3`**: `fin_kw` guard fixed so `"why is WACC high"` never returns `pnl_statement` | **PASS** | `planner.py:516-571`, `test_wacc_metric.py:91-98` |
| **`Packet P2F.3 §6` Shapley fixture**: `WACC_a = 11.20%` -> `WACC_b = 12.604%` ($\Delta = +1.404\text{ pp}$); exact closure $|\sum c_i - \Delta\text{WACC}| < 10^{-9}$; `rf_used` ($+0.4450$), `erp_total` ($+0.4672$), `beta` ($+0.6452$), `kd_after_tax` ($+0.0220$) $> 0$; `weights` ($-0.1753$) $< 0$; top 2 ranked factors (`beta`, `erp_total`) cited with sources in narrative | **PASS** | `wacc_attribution.py:157-250`, `test_wacc_shapley.py:13-108` |
| **`Packet P2F.3 §9` Caveats**: Unverified rows (`verified=FALSE` when RBI G-sec seed is pending) render caveat notes and `provenance_label="modelled"` without crashing or hiding rows | **PASS** | `wacc_attribution.py:282-289`, `compiler.py:1740-1743, 1850-1858` |

---

## 3. Non-Blocking Observation

- **`P2F3-N1` (Non-blocking — BigQuery path for `wacc_change_attribution` once `fact_wacc_annual` is loaded to BQ):**
  - In `compiler.py:707-730`, `_compile_wacc_change_attribution` generates a SQL `SELECT` returning the two annual rows (`FY_from`, `FY_to`) from `hrfin_gold.fact_wacc_annual`, while `_v3__execute_local_financial_fallback` (`compiler.py:1838-1860`) transforms those two rows through `attribute_wacc_change()` into the 7 waterfall bars (`WACC FY_from`, 5 Shapley factor deltas, `WACC FY_to`). If `hrfin_gold.fact_wacc_annual` is later promoted to BigQuery, `compiler.execute()` (`compiler.py:2188`) should also pass the 2 BigQuery rows through `attribute_wacc_change()` so the BigQuery and local-snapshot paths return identical 7-row waterfall structures.
