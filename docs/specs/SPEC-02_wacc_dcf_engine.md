# SPEC-02: WACC Series and DCF Valuation Engine

**Features:** FEAT-024 (WACC 5/10-yr part), FEAT-029 (DCF Valuation agent engine) · **Phase:** P1.9 (WACC inputs), P2F.3 (WACC metric + chart), P3.4 / P3.4b / P3.5 (DCF engine, agent wiring, xlsx) · **Spec owner:** O · **Status:** Draft v3 (23-Oct-2026) · **Depends on:** SPEC-01 (verified lines, market data, anchors) · **Used by:** SPEC-03 (dcf_agent), SPEC-08 (WACC "why"), SPEC-09 (sensitivity_grid / tornado / dcf_model visuals), SPEC-10 (xlsx)

> [!IMPORTANT]
> **BLUF.** WACC does not exist today ("show me the WACC for the last 10 years" errors). DCF does not exist either.
> Build (1) `hrfin_gold.fact_wacc_annual` FY17–FY26. Every input (Rf, beta, ERP/CRP, Kd, tax, weights) gets a lineage row in `fact_wacc_input`. (2) A **deterministic, pure-Python DCF engine**: standalone FCFF from verified lines, an explicit assumptions object, Gordon TV with an exit-multiple cross-check, and an EV→equity bridge that adds listed investments at market value.
> The engine outputs per-share value vs the Yahoo market price, a WACC×g grid, a tornado, and an xlsx with live formulas. It is unit-tested against a hand-computed fixture.
> Every DCF output carries the fixed disclaimer **"Illustrative valuation, not investment advice."** Per V23 decision 5, the DCF runs only on verified SSOT rows, so it is built after P1.

---

## 1. Purpose and verbatim trace
| Verbatim | Requirement | Section |
|---|---|---|
| V20 "what was the weighted average cost of capital for the past five years or 10 years? Then it should plot it" | WACC FY22–FY26 / FY17–FY26, plotted | §3, §5 |
| V20 "why it was high in this particular year" | WACC change attribution | §5.3 |
| V22 "run a discounted cash flow and tell if ONGC is undervalued or overvalued" | DCF with per-share value vs market and a verdict | §6–§8 |
| V22 "the valuation would come with the exact discounted cash flow model" | Full model + downloadable assumptions (xlsx, live formulas) | §9 |
| V22 directives: "sensitivity tables (WACC vs. perpetual growth)" | Grid + tornado | §8 |

## 2. Current state
| Item | Status | Evidence |
|---|---|---|
| WACC data/metric | **Missing** | No `wacc/beta/risk-free/cost of equity` in `yukti/backend/app`, `financial_build`, `data_bank` (diag_A §5); "why was WACC high in FY23" → error (diag_D B18) |
| Ratios table | **Broken** | `ongc_10yr_ratios_lines.json` has 18 ratios, no WACC/Ke/Kd; ROCE wrong (diag_A §5) |
| DCF/valuation code | **Missing** | diag_D §2; `what_if.py` only covers Brent/hiring/CTA/SAED |
| Market data | **Blocked** | Yahoo returns HTTP 429 (rate-limited) on every endpoint; retry script `knowledge/public_sources/market_data/yahoo/_PENDING_fetch_script_yahoo.py`; fallbacks in SPEC-01 §9.1. Damodaran archives FY15–FY24 + current are on disk; RBI G-sec history needs a manual seed (MANIFEST_v3 §1) |

## 3. `fact_wacc_annual` and its inputs

### 3.1 Method (decided)
| Input | Definition | Source | Lineage row |
|---|---|---|---|
| **Rf (raw)** | 10-yr G-sec yield at the end of March of each FY | **Manual seed CSV** `knowledge/public_sources/market_data/rbi/gsec10y_fy_end_seed.csv` (`fiscal_year,as_of_date,yield_pct,source_table,source_url,downloaded_by,downloaded_at,sha256_of_source_file`), keyed from the RBI *Handbook of Statistics on Indian Economy* Table 178 "Month-end Yield of SGL Transactions in Government Dated Securities" (10-yr column, March), with the source XLSX saved next to it. Automated pulls hit an RBI bot challenge and must not be bypassed. FBIL historical par yield is the alternative | `rf_gsec_10y` |
| **India default spread** | Damodaran sovereign default spread for India, January dataset of the FY-end calendar year (FY24 → Jan-2024) | `market_data/damodaran/archives/ctryprem15–24` + current file (= Jan-2026, FY26). **Jan-2025 (FY25) is missing** (`ctryprem25.xlsx` 404): use the Jan-2024 dataset with `notes='erp_vintage_gap'` until a manual download fills it (Open Q5) | `default_spread_india` |
| **Rf (used)** | `rf_used = rf_gsec_10y` — the **raw** INR 10-yr G-sec yield at FY-end (lead decision 2026-10-23, recorded in OD-11's recommendation; INR cash flows, so no USD-style default-spread adjustment). `rf_method='gsec_raw'` is stored. **Sensitivity option only:** `rf_gsec_10y − default_spread_india` (avoids counting country risk twice against the Damodaran total ERP) is computed as the alternative column `wacc_alt_gsec_less_spread_pct` and shown in the drill-down, never as the primary series | derived | `rf_used` |
| **ERP (total, India)** | Damodaran India total equity risk premium (mature-market ERP + CRP), January dataset as above | Damodaran | `erp_total_india`, `erp_mature`, `crp_india` |
| **Beta (primary)** | OLS of 104 weekly log returns of ONGC.NS (adj. close) on `^NSEI`, ending at the FY-end; Blume-adjusted `0.67·β_raw + 0.33` | `fact_market_price_daily` | `beta_2y_weekly_raw`, `beta_2y_weekly_adj` |
| **Beta (cross-check)** | 60 monthly returns over 5 years, same method | same | `beta_5y_monthly_raw/adj` |
| **Beta (fallback)** | When no price series is available (Yahoo 429 and NSE fallback not approved; SPEC-01 §9.1): Damodaran EM "Oil/Gas (Production and Exploration)" unlevered beta (`betaemerg` of that year), re-levered at ONGC's D/E and tax rate. `beta_method='industry_relevered'`, shown in the UI | `market_data/damodaran/archives/betaemerg16–24` | `beta_industry_relevered` |
| **Ke** | `rf_used + β_adj × erp_total_india` | derived | `ke` |
| **Kd (pre-tax)** | `(PL.FIN_COST − N36.UNWIND_DECOM) / avg(opening, closing)(BS.BORROWINGS.TOTAL + BS.LEASE_LIAB.TOTAL)`. ONGC's finance cost is dominated by the unwinding of the decommissioning-provision discount (FY26: ₹30,539.42 mn of ₹45,292.61 mn; AR FY26 PDF p.345 and segment note p.369), which is not a cost of debt | SSOT Note 36 + provisions note + BS | `kd_pretax` |
| **Kd sanity band** | If `kd_pretax ∉ [rf_gsec_10y − 1.0pp, rf_gsec_10y + 3.0pp]`, set `kd_flag='out_of_band'` and use `rf_gsec_10y + rating_spread` (AAA PSU spread from CRISIL/ICRA rationale, lineage `kd_rating_spread`) as `kd_used` | derived | `kd_used`, `kd_method` |
| **Tax rate** | Statutory rate used in the AR tax reconciliation note of that FY | SSOT tax note | `tax_rate` |
| **E (market)** | FY-end close × shares outstanding | `fact_market_price_daily`, `fact_shares_outstanding` (12,580,279,206) | `equity_mv` |
| **D** | `BS.BORROWINGS.TOTAL + BS.LEASE_LIAB.TOTAL` at FY-end (book ≈ market for this low-debt issuer) | SSOT (FY26: 78,234 + 258,218 ₹ mn; AR FY26 10-yr) | `debt_bv` |
| **WACC** | `E/(D+E)·Ke + D/(D+E)·kd_used·(1 − tax_rate)` | derived | `wacc` |

Beta needs prices from Apr-2015 for FY17 (2y weekly) and Apr-2012 for 5y monthly. Yahoo covers both.

### 3.2 `hrfin_gold.fact_wacc_annual`
| Column | Type | Notes |
|---|---|---|
| `fiscal_year` | STRING | FY17…FY26 |
| `as_of_date` | DATE | FY-end trading date used |
| `rf_gsec_10y_pct`, `default_spread_pct`, `rf_used_pct` | NUMERIC | Base case: `rf_used_pct = rf_gsec_10y_pct` (raw INR 10-yr G-sec, OD-11) |
| `rf_method` | STRING | `raw_gsec` (base) or `gsec_less_default_spread` (sensitivity only) |
| `erp_mature_pct`, `crp_pct`, `erp_total_pct` | NUMERIC | |
| `beta_2y_weekly_raw`, `beta_2y_weekly_adj`, `beta_5y_monthly_raw`, `beta_5y_monthly_adj`, `beta_r2_2y` | NUMERIC | |
| `ke_pct` | NUMERIC | |
| `kd_pretax_pct`, `kd_used_pct`, `kd_method`, `kd_flag` | NUMERIC / STRING | |
| `tax_rate_pct` | NUMERIC | |
| `equity_mv_inr_cr`, `debt_bv_inr_cr`, `weight_equity`, `weight_debt` | NUMERIC | |
| `wacc_pct` | NUMERIC | Primary series |
| `wacc_alt_gsec_less_spread_pct`, `wacc_alt_beta5y_pct` | NUMERIC | Alternatives shown in the drill-down (Rf = G-sec − default spread sensitivity; 5-yr monthly beta) |
| `method_version` | STRING | e.g. `wacc-v1` |
| `verified` | BOOL | All inputs present + gates W1–W4 pass |
| `provenance_label` | STRING | Always `modelled` (inputs real, output computed) |

### 3.3 `hrfin_gold.fact_wacc_input` (one lineage row per input)
`fiscal_year, input_code, value, unit, source_system (fbil|rbi|damodaran|yahoo|ar|derived|crisil|icra), source_doc, source_page, source_url, retrieved_at, formula (for derived), depends_on ARRAY<STRING>, notes`. Raw Rf/ERP files are saved to `knowledge/public_sources/market_data/{fbil,damodaran,ratings}/`.

### 3.4 Gates
| ID | Gate |
|---|---|
| W1 | Every FY17–FY26 row has all 12 input codes, each with `source_doc` or `formula` |
| W2 | `0.2 ≤ beta_2y_weekly_raw ≤ 2.0` and `beta_r2_2y ≥ 0.05`; otherwise flag and show the 5y beta |
| W3 | `weight_equity + weight_debt = 1` (±1e-9); `wacc_pct` recomputes from the columns (±0.001pp) |
| W4 | `kd_flag` explained in `notes` whenever `out_of_band` |

## 4. Real numbers available today (for fixtures and eval)
| Item | Value | Source |
|---|---|---|
| Finance costs FY26 / FY25 | ₹45,292.61 / 46,039.70 mn | AR FY26 standalone P&L, PDF p.297 |
| Unwinding of discount on decommissioning provision FY26 / FY25 | ₹30,539.42 / 28,987.14 mn | AR FY26 provisions note, PDF p.345 |
| Unwinding of discount on lease liabilities FY26 / FY25 | ₹15,354.99 / 16,351.36 mn | AR FY26 Note 22.1, PDF p.344 |
| Lease liabilities FY26 / FY25 | ₹258,218.02 / 294,393.02 mn | same |
| Borrowings FY26 / FY25 | 78,234 / 84,077 ₹ mn | AR FY26 10-yr table, PDF p.23 |
| Shares outstanding | 12,580,279,206 | Share capital ₹62,901 mn ÷ ₹5 face value |

Worked check (not a published figure): FY26 `kd_pretax ≈ (45,292.61 − 30,539.42) / avg(84,077 + 294,393.02; 78,234 + 258,218.02) = 14,753.19 / 357,461.0 ≈ 4.13%`. P1.9 confirms it with exact note values.

## 5. WACC answer and chart behaviour (P2F.3)
### 5.1 Intents
| User says | Planner metric / spec | Visual |
|---|---|---|
| "WACC for the past 5 years" | `wacc_pct`, `fy_range = FY22–FY26` | `chart` kind `line` (WACC %), with Ke and Kd(1−t) as dashed secondary lines; data labels on the WACC points |
| "… 10 years" | `FY17–FY26` | same |
| "show the build-up / drivers" | `wacc_components` | `chart` kind `stacked_bar`: `rf_used`, `β_adj×ERP`, weighted to WACC, + table of inputs with sources |
| "WACC FY24" (single year) | `wacc_build_up`, FY24 | `table` (input, value, source) + KPI |
| "why was WACC high in FY23" | `wacc_change_attribution`, FY23 vs FY22 | `chart` kind `waterfall` (signed contributions, ends at FY23 WACC) + narrative (§5.3) |

### 5.2 Rules
- Title: "ONGC WACC (standalone, %) FY17–FY26". Subtitle: "Modelled from real inputs: FBIL/RBI 10-yr G-sec, Damodaran ERP, 2-yr weekly beta vs NIFTY 50 (Yahoo), AR finance cost and debt".
- `sources[]` lists each input family. Provenance badge **Modelled**.
- Y-axis in %, 1 dp; the FY order is ascending left→right; the series is never interpolated: a missing FY renders a gap plus a caveat.
- RBAC: public-derived data, allowed to all personas unless SPEC-06 says otherwise.

### 5.3 WACC change attribution
ΔWACC(FY_a→FY_b) is split into five factors (Rf_used, ERP, β, Kd_after_tax, weights) by **Shapley values**: the average marginal contribution over all 120 orderings. This is order-independent and the contributions sum exactly to ΔWACC. The narrative ranks the factors by |contribution| and states each with its source, e.g. "Rf rose from x% to y% (FBIL 31-Mar)". No free-text causes are generated without a data row.

## 6. DCF engine: architecture
```
yukti/backend/app/finance/dcf/
  assumptions.py    # pydantic DCFAssumptions (frozen) + defaults builder from SSOT
  inputs.py         # reads verified SSOT rows / snapshot; no network
  wacc.py           # build-up (re-uses fact_wacc_annual or overrides)
  fcff.py           # historical FCFF + forecast
  valuation.py      # TV (Gordon + exit multiple), discounting, EV→equity bridge, per share, verdict
  sensitivity.py    # WACC×g grid, tornado
  xlsx_writer.py    # openpyxl workbook with live formulas
  run.py            # run_dcf(assumptions) -> DCFResult (pure, deterministic)
tests/finance/test_dcf_fixture.py, test_dcf_inputs.py, test_xlsx_formulas.py
```
**Determinism rules:** no LLM calls, no network, no clock inside `run_dcf` (the `as_of` date is an input), `Decimal`-free float64 is acceptable with results rounded only at presentation, and the same inputs give byte-identical JSON.

## 7. Model definition
### 7.1 Scope decision: standalone FCFF + sum-of-the-parts (SOTP) for investments
- **Valued by DCF:** ONGC standalone E&P operations (the scope of the verified standalone statements).
- **Valued separately and added in the bridge:** listed investments (e.g. HPCL, MRPL, IOCL, GAIL, Petronet LNG, as listed in the AR FY26 standalone investments note) at **market value** = FY-end or `as_of` close × shares held per the note. Unlisted investments (e.g. OVL, ONGC Petro additions) are added at **book value** from the note.
- **Why:** (1) Consolidated FCFF would be dominated by HPCL/MRPL refining, which has a different risk profile, so one WACC would mis-price it. (2) Standalone FCFF excludes subsidiary cash flows, so we add their value once. To avoid double counting, dividend income is **excluded** from forecast EBIT. (3) Market prices are observable and audit-friendly. Book value understates listed stakes. (4) OVL has no market price and no verified standalone cash flows in P1, so book value is the conservative, sourced choice.
- `holdco_discount_pct` (default **0%**; tornado 0–30%) is applied to listed investments only. See Open Q2.

### 7.2 Historical FCFF (from verified cash-flow lines, FY17–FY26)
`FCFF_hist = CF.CFO + CF.INTEREST_PAID_ON_BORROWINGS × (1 − t) − CF.CAPEX_TOTAL`, where `CF.CAPEX_TOTAL` = purchase of PPE + exploration & development expenditure (cash, from CFI). Lease payments stay in financing because lease liabilities are in D (§3.1). Shown as context rows in the model; not used to fit the forecast.

### 7.3 Forecast (FY27–FY36, 10 explicit years; annual, end-year discounting; `mid_year` flag optional)
| Line | Formula | Default driver (from SSOT, editable) |
|---|---|---|
| Crude volume (MMT) | `vol₀ × (1 − decline_crude)^t` | `vol₀` = FY26 `fact_production_annual` ONGC_standalone crude 19.332; `decline_crude` = −CAGR FY22–FY26 of the same series |
| Gas volume (BCM) | same | FY26 19.533; CAGR FY22–FY26 |
| Brent (USD/bbl) | price deck by year | Flat at FY26 realised crude price (AR/press release, lineage row) |
| Crude realisation | `Brent × (1 − discount_pct)` | discount from FY26 realised vs Brent |
| Gas price (USD/mmbtu) | deck | FY26 realised gas price (AR) |
| INR/USD | deck | FY26 average (RBI reference rate), lineage row |
| Crude revenue | `vol_MMT × 1e6 × bbl_per_tonne × realisation × FX / 1e7` (₹ cr) | `bbl_per_tonne` default 7.33 (documented constant); calibration check: implied FY26 crude revenue vs SSOT `REV.CRUDE` (838,102 ₹ mn) within ±5% |
| Gas revenue | `vol_BCM × 1e9 × gcv_mmbtu_per_scm × price × FX / 1e7` (₹ cr) | `gcv_mmbtu_per_scm` = PPAC conversion factor (lineage row, P1.9); cross-check: implied FY26 gas revenue vs SSOT `REV.GAS` within ±5%, else the factor is recalibrated to FY26 actuals |
| VAP + other operating revenue | `% of crude+gas revenue` | FY22–FY26 average ratio |
| Royalty, OIDB cess, NCCD, other levies | `effective_rate × relevant revenue` | Effective rates = FY26 SSOT levy ÷ sales (no statutory-rate claims) |
| Operating expenses | `opex_per_boe × production_boe × (1+inflation)^t` | FY26 SSOT opex ÷ FY26 boe; inflation 4.0% |
| Exploration write-offs | `% of revenue` | FY22–FY26 average ratio |
| DD&A | `% of opening net block + capex_t × dd&a_on_new` (simple: `% of revenue` fallback) | FY26 ratio |
| EBIT (excl. other income) | Revenue − levies − opex − exploration − DD&A | |
| Tax | `EBIT × t` | statutory rate (FY26 AR tax note) |
| Capex | `capex_t` | FY22–FY26 average of `CAPEX.TOTAL` (verified), real terms + inflation |
| ΔNWC | `nwc_pct × ΔRevenue` | FY26 (receivables + inventories − trade payables) ÷ revenue |
| **FCFF** | `EBIT(1−t) + DD&A − capex − ΔNWC` | |

Every default carries `{value, source (line_code + FY or doc/page), editable: true}`. Defaults are labelled **"Illustrative assumption derived from FY26 actuals"**. They are not ONGC guidance.

### 7.4 Terminal value
- **Gordon (primary):** `TV = FCFF_FY36 × (1 + g) / (WACC − g)`; guard `WACC − g ≥ 1.0pp`, else error `E_TV_GUARD`.
- **Exit-multiple cross-check:** `TV_x = EBITDA_FY36 × exit_ev_ebitda` (default 4.5×, labelled illustrative and editable); report the **implied g** of TV_x and the **implied multiple** of the Gordon TV. Warn if `|TV − TV_x| / TV > 30%`.
- Defaults: `g = 3.0%` nominal INR for a depleting E&P base (editable; grid 1–5%).

### 7.5 EV → equity bridge (standalone, ₹ cr, all from verified SSOT at `bridge_date` = latest FY-end unless overridden)
| Row | Sign | Source |
|---|---|---|
| PV of explicit FCFF | + | engine |
| PV of TV | + | engine |
| **Enterprise value** | = | |
| Cash & cash equivalents + other bank balances | + | `BS.CCE`, `BS.OTHER_BANK_BAL` |
| Listed investments at market × (1 − holdco_discount) | + | investments note × `fact_market_price_daily` |
| Unlisted investments at book | + | investments note |
| Site Restoration Fund deposits (earmarked) | + | `BS.SRF_DEPOSIT` (FY26 327,277 ₹ mn) |
| Decommissioning provision | − | provisions note |
| Borrowings (current + non-current) | − | `BS.BORROWINGS.TOTAL` |
| Lease liabilities | − | `BS.LEASE_LIAB.TOTAL` |
| **Equity value** | = | |
| ÷ shares outstanding | | 12,580,279,206 |
| **Intrinsic value per share (₹)** | | |
| Market price (₹, close on `as_of`) | | `fact_market_price_daily` ONGC.NS |
| Upside / (downside) % | `IV/price − 1` | |
| Verdict | `> +10%` "undervalued", `< −10%` "overvalued", else "fairly valued (within ±10%)" | band editable |
SRF deposits and the decommissioning provision are paired, because the deposit is legally earmarked for the provision. Both are shown so the CMD sees the net figure.

## 8. Sensitivity
- **Grid:** WACC = base −2.0pp … +2.0pp in 0.5pp steps (9) × g = 1.0% … 5.0% in 0.5pp steps (9). Cell = value per share; a cell where `WACC − g < 1pp` = `null` ("n/m"). Base cell highlighted. Visual `sensitivity_grid` (SPEC-09).
- **Tornado** (per-share swing, sorted by |high − low|):

| Driver | Low | High |
|---|---|---|
| Brent | −$10/bbl | +$10/bbl |
| Opex/boe | −15% | +15% |
| Capex | −20% | +20% |
| Production (both products) | −10% | +10% |
| WACC | −1pp | +1pp |
| Terminal g | −1pp | +1pp |
| INR/USD | −5% | +5% |
| Holdco discount | 0% | 30% |

## 9. Outputs
### 9.1 `DCFResult` JSON (also stored in `hrfin_gold.fact_dcf_run.result_json`)
```json
{
  "run_id": "dcf_20261023T0712Z_ab12",
  "engine_version": "dcf-v1.0.0+<git_sha>",
  "as_of": "2026-10-23",
  "scope": "standalone_sotp",
  "assumptions": { "...": "full DCFAssumptions, each field {value, source, edited_by_user}" },
  "wacc_build": {"rf_used_pct": 0, "beta_adj": 0, "erp_total_pct": 0, "ke_pct": 0, "kd_used_pct": 0, "tax_rate_pct": 0, "weight_equity": 0, "wacc_pct": 0},
  "historical": [{"fy": "FY26", "line_code": "CF.CFO", "value_inr_cr": 69272.39, "source": "AR FY26 p.298"}],
  "forecast": {"years": ["FY27", "..."], "lines": {"revenue": [], "ebit": [], "fcff": [], "discount_factor": [], "pv_fcff": []}},
  "terminal": {"method": "gordon", "g_pct": 3.0, "tv_inr_cr": 0, "pv_tv_inr_cr": 0, "exit_multiple": 4.5, "tv_exit_inr_cr": 0, "implied_g_pct": 0, "implied_multiple": 0, "warning": null},
  "bridge": [{"label": "Enterprise value", "value_inr_cr": 0, "source": "engine"}],
  "per_share": {"intrinsic_inr": 0, "market_inr": 0, "market_date": "2026-10-22", "upside_pct": 0, "verdict": "undervalued"},
  "sensitivity": {"wacc_axis_pct": [], "g_axis_pct": [], "values_inr": [[]]},
  "tornado": [{"driver": "brent", "low_input": "-10", "high_input": "+10", "low_inr": 0, "high_inr": 0}],
  "lineage_refs": ["fact_financial_statement_line:run_id", "fact_wacc_annual:FY26"],
  "provenance_label": "illustrative",
  "disclaimer": "Illustrative valuation, not investment advice."
}
```
### 9.2 xlsx (`ONGC_DCF_<run_id>.xlsx`, openpyxl)
| Sheet | Content | Formulas |
|---|---|---|
| Cover | Title, run_id, as_of, disclaimer (bold, top), provenance legend | — |
| Assumptions | One row per assumption: name, value (input cell, yellow fill), unit, source, edited flag. Named ranges (`WACC`, `g`, `ExitMultiple`, `Brent_FY27`…) | inputs |
| WACC | Build-up | `=Rf_used+Beta_adj*ERP` etc. |
| Historical | Verified lines FY17–FY26 with source page column | values |
| Forecast | FY27–FY36 lines | all live formulas referencing Assumptions |
| Valuation | PV, TV (Gordon + exit), bridge, per share, upside, verdict | live formulas |
| Sensitivity | 9×9 grid; each cell `=SUMPRODUCT(Forecast!FCFF/(1+w)^Forecast!t)+Forecast!FCFF_last*(1+g)/(w−g)/(1+w)^10` + bridge adjustments | live formulas |
| Tornado | Engine values (static, labelled "computed by engine run <id>") + bar chart | static |
| Sources | All lineage rows (doc, page, URL) | — |
**Formula parity test:** recalculate with LibreOffice headless (`soffice --headless --convert-to xlsx` recalculation) and compare per-share value and 3 grid cells with `DCFResult` within ₹0.01.

## 10. Unit tests: hand-computed fixture (`tests/finance/fixtures/dcf_fixture.json`)
Synthetic fixture (not ONGC data): FCFF FY1–FY5 = 100, 110, 120, 130, 140 (₹ cr); WACC 10%; g 4%; end-year discounting; net debt 200; investments 300; shares 10 cr; market price ₹150.

| Quantity | Expected (±1e-4) |
|---|---|
| PV of FCFF (each) | 90.9091, 90.9091, 90.1578, 88.7917, 86.9290 |
| Σ PV FCFF | 447.6967 |
| TV (Gordon) | 2,426.6667 |
| PV of TV | 1,506.7691 |
| EV | 1,954.4658 |
| Equity (EV − 200 + 300) | 2,054.4658 |
| Per share | 205.4466 |
| Upside vs ₹150 | +36.96% → verdict "undervalued" |
| Exit TV at 5.0× EBITDA_FY5 = 250 | 1,250; implied g = −1.079% |
| Grid (WACC, g) = (9%, 3%) / (9%, 5%) / (11%, 3%) / (11%, 5%) | 212.2077 / 294.8573 / 160.5526 / 198.9785 |
| WACC fixture: Rf_gsec 7% (raw, = `rf_used`), β_raw 1.2, ERP 7%, Kd 6%, t 25.17%, E 900, D 100 | β_adj 1.134 (Blume); with β = 1.2 raw: Ke 15.40%, Kd after tax 4.4898%, **WACC 14.3090%** |
| WACC sensitivity fixture: same inputs + default spread 2% (Rf = 7% − 2% = 5%) | Ke 13.40%, WACC 12.5090% → `wacc_alt_gsec_less_spread_pct` |
| Guard: WACC 4%, g 4% | raises `E_TV_GUARD` |
| Determinism | two runs → identical JSON hash |

## 11. Acceptance criteria
| ID | Criterion |
|---|---|
| AC-01 | `fact_wacc_annual` has 10 verified rows FY17–FY26; W1–W4 pass; each row has ≥ 12 lineage rows |
| AC-02 | "WACC for the past 10 years" returns a line chart with 10 points equal to `wacc_pct` (±0.01pp) and the "Modelled" badge |
| AC-03 | WACC attribution contributions sum to ΔWACC (±0.001pp) |
| AC-04 | All fixture tests in §10 pass; `run_dcf` is pure (a test with network/LLM mocks raising on call) |
| AC-05 | A DCF run on the real SSOT completes in < 5 s on Cloud Run (1 vCPU) and produces JSON + xlsx |
| AC-06 | xlsx parity test passes (≤ ₹0.01/share); Assumptions edits in Excel change the per-share value |
| AC-07 | Every number in the bridge has a source (SSOT line + FY or engine) |
| AC-08 | The disclaimer appears in the JSON, the result card, the xlsx Cover and the spoken summary |
| AC-09 | Forecast reads only `verified=TRUE` rows (poisoned-row test) |

## 12. Test plan
Unit (fixture, guards, Shapley sum, beta OLS on a synthetic price series with known β = 1.5), input tests on the SSOT snapshot, xlsx formula parity (LibreOffice in CI image or FL step), golden eval items (SPEC-11: WACC FY-series values; DCF per-share value for a pinned `as_of` and pinned assumptions).

## 13. Open questions
1. ERP/Rf: **resolved by the lead (2026-10-23) — Rf = raw INR 10-yr G-sec at FY-end** (§3.1); `G-sec − default spread` is a sensitivity column only. Sponsor confirmation is tracked in OD-11.
2. Holdco discount default 0% (recommended for transparency) vs 20%?
3. OVL at book vs a separate OVL DCF (needs verified OVL statements, out of P3 scope).
4. Forecast horizon: 10 years (default) vs reserve-life-linked (2P / production, from `fact_reserves`)?
5. Manual inputs needed from the sponsor or a human: the RBI Table 178 XLSX (Rf FY17–FY26) and the Damodaran Jan-2025 ctryprem file. Until then FY25 uses the Jan-2024 ERP (flagged).
6. Market prices: Yahoo is HTTP 429. Approve the NSE weekly bhavcopy fallback (SPEC-01 Open Q5)? Without prices, beta falls back to the industry beta and market cap needs the manual seed.

## 14. Status matrix
| Item | Status |
|---|---|
| WACC inputs, table, chart, attribution | Missing |
| DCF engine, sensitivity, tornado | Missing |
| xlsx with live formulas | Missing (`export_tool.export_xlsx` is values-only) |
| Fixture tests | Missing |
