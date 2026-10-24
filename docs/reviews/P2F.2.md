# Independent G4 Review — P2F.2: Multi-Year Yahoo-Style Statement Query + Presenter Emit

**Verdict: APPROVE (Round 2)**  
**Reviewer:** `reviewer-p16` (Independent G4 Reviewer, Role R)  
**Commit Reviewed:** `3089fe2` on branch `v3/P2F-fin-diag` (`HR and Finance_ONGC__v3P2F`)  
**Specs & Packet Referenced:** `SPEC-08` (§4, §10 `AC-03`), `SPEC-09` (§2.2, §4.2, §4.3), `SPEC-01` (§5.5, §7.1), `docs/delegation/packets/v3/P2F.2_multiyear_statement.md`

---

## 1. Executive Summary (BLUF)

**All 3 Round 1 blockers (`P2F2-B1` through `P2F2-B3`) are resolved in commit `3089fe2`, and `tests/test_multiyear_statement.py` passes `4/4` end-to-end against `fact_snapshot.parquet`.**

1. **`P2F2-B1` Resolved (`compiler.py:1006, 1038-1039, 1171, 1203-1216, 1363-1379, 1993-2040`):**
   - `_v3__compile_balance_sheet` and `_v3__compile_cash_flow_statement` now query `STARTS_WITH(line_code, 'BS.')` / `'CF.'` and return `metric="balance_sheet"` / `"cash_flow_statement"`.
   - Multi-year queries against `v_fin_trend_latest` and `_v3__execute_local_financial_fallback` filter by Schedule III `line_code` prefix (`PL.`/`BS.`/`CF.` excluding `*_10YR*`) rather than `source_table = 'standalone_pnl'`, preserving `FY20` (`ten_year_summary` / `xbrl_instance`) and restated `FY19` totals (`PL.PAT = 26,764.6 cr`).
   - `_v3__execute_local_financial_fallback` (`compiler.py:1993-2040`) emits tall Schedule III statement rows with `line_order`, `line_code`, `display_name`, `level`, `line_kind`, `fiscal_year`, `value_inr_cr`, `is_restated`, `source_doc`, and `source_page_label`.
2. **`P2F2-B2` Resolved (`statement_builder.py:620-625`, `presenter.py:569-593`):**
   - `build_statement_spec` keeps all `requested_periods` in `active_periods` (preserving `None` for non-disclosed cells, never `0`) and appends omitted-period footnotes (`statement_builder.py:770-777`).
   - `narrate()` (`presenter.py:569-593`) summarizes multi-year P&L (`PL.REV_OPS` and `PL.PAT`), Balance Sheet (`BS.TOTAL_ASSETS`), and Cash Flow (`CF.CFO`) across `lo`..`hi`.
3. **`P2F2-B3` Resolved (`tests/test_multiyear_statement.py:21-116`):**
   - End-to-end tests run `compiler.compile(spec)` -> `await compiler.execute(compiled)` -> `build_visual(...)` for 5-year P&L (`FY22..FY26`), 10-year P&L (`FY17..FY26`), multi-year Balance Sheet (`FY24..FY26`), and multi-year Cash Flow (`FY24..FY26`), verifying exact SSOT numbers (`PL.REV_OPS = [132508.1, 137846.3, 138402.1, 155517.3, 110345.4]`, restated `FY24 PL.OTHER_INCOME = 10735.5`, restated `FY19 PL.PAT = 26764.6`).

---

## 2. Verification Matrix

| Check | Status | Evidence |
|---|---|---|
| `BEH-03.02` 5-yr P&L (`FY22..FY26`) 5 columns newest-first + exact SSOT values | **PASS** | `tests/test_multiyear_statement.py::test_multiyear_pnl_statement_5_year` (`periods == ["FY26", "FY25", "FY24", "FY23", "FY22"]`) |
| `BEH-03.03` 10-yr P&L (`FY17..FY26`) 10 columns including `FY20` & restated `FY19` PAT (`26,764.6` cr), `None` (never `0`) for non-disclosed lines | **PASS** | `tests/test_multiyear_statement.py::test_multiyear_pnl_statement_10_year` |
| Multi-year Balance Sheet & Cash Flow (`FY24..FY26`) | **PASS** | `test_multiyear_balance_sheet`, `test_multiyear_cash_flow` |
| Multi-year `narrate()` summary | **PASS** | `presenter.py:569-593` |

---

## 3. Non-Blocking Notes

- **`presenter.py:569-619`:** The `if compiled.metric in ("pnl_statement", "balance_sheet", "cash_flow_statement") and "line_code" in (columns or []):` block is duplicated twice consecutively (`569-593` and `595-619`); remove the duplicate second copy when convenient.
- **`statement_builder.py:767-778`:** Consider adding a per-vintage restatement footnote (`† <FY> restated in comparative column / 10-year summary`) when `any(r.get("is_restated") for r in rows)` is True.
