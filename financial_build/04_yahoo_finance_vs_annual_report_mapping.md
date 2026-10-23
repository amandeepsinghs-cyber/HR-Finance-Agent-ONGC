# Cross-Walk Mapping: Yahoo Finance (`ONGC.NS`) ↔ ONGC Annual Report (Schedule III) ↔ BigQuery SSOT

This document defines the exact mathematical and schema mapping between **Yahoo Finance (`https://finance.yahoo.com/quote/ONGC.NS/financials/`)**, **ONGC’s Official Annual Reports (Ind-AS Schedule III & Notes 24–38)**, and **Yukti’s BigQuery Financial Cube (`hrfin_gold.ssot_corporate_annual_360` & `hrfin_gold.ssot_corporate_pnl_lines`)**.

---

## 1. Critical Distinction: Standalone E&P vs. Consolidated Group (`ONGC.NS`)

When an executive or analyst compares numbers between ONGC’s Annual Report and Yahoo Finance (`ONGC.NS`), the **#1 source of confusion** is **Consolidation Scope**:

| Metric (FY24 / FY25 Benchmark) | ONGC Standalone (Annual Report Primary E&P P&L) | ONGC Consolidated (`ONGC.NS` on Yahoo Finance & Annual Report Consolidated P&L) | Why They Differ (The Exact Reconciliation Bridge) |
|---|---|---|---|
| **Revenue from Operations** | **₹1,38,402 Cr** (`FY24`) / **₹1,37,846 Cr** (`FY25`) | **~₹6,43,037 Cr** (`FY24`) / **~₹6,63,262 Cr** (`FY25`) | Consolidated revenue includes downstream refining & marketing subsidiaries **HPCL** (~₹4.3 Lakh Cr), **MRPL** (~₹0.9 Lakh Cr), international E&P **ONGC Videsh (OVL)** (~₹13,000 Cr), and **OPaL**, minus inter-company crude/gas sales. |
| **EBITDA** | **~₹71,650 Cr** (`FY24`) / **~₹68,940 Cr** (`FY25`) | **~₹1,05,400 Cr** (`FY24`) / **~₹98,200 Cr** (`FY25`) | Adds EBITDA from HPCL refining/marketing margins, MRPL GRMs, and OVL overseas fields. |
| **Profit After Tax (PAT)** | **₹40,526 Cr** (`FY24`) / **₹35,610 Cr** (`FY25`) | **₹57,101 Cr** Total / **₹49,221 Cr** Owners (`FY24`) · **₹38,329 Cr** (`FY25`) | Reflects HPCL & MRPL refining margin cycles and OVL international profit/impairments, net of dividend eliminations. |

**How Yukti Handles Both Seamlessly:**
- By default, E&P operational P&L questions (*"What is ONGC's P&L statement?"*, *"What was our royalty, cess, windfall tax, and exploration write-off?"*) show the **Standalone E&P Schedule III Statement** **and** display the **Consolidated Group (`ONGC.NS`) Revenue & PAT** right alongside it so the user sees both numbers immediately and can switch or bridge between them at will.

---

## 2. Line-by-Line P&L Mapping Table (Schedule III ↔ Yahoo Finance `ONGC.NS` ↔ BigQuery Column)

| Line # | ONGC Annual Report (Ind-AS Schedule III Line & Note) | Yahoo Finance (`ONGC.NS/financials`) Line | BigQuery Column (`ssot_corporate_annual_360`) | Accounting Formula / Sub-Components |
|---|---|---|---|---|
| **1** | **I. Revenue from Operations** *(Note 24)* | `Operating Revenue` / `Total Revenue` | `gross_revenue_inr_cr` | `crude_oil_revenue_inr_cr + natural_gas_revenue_inr_cr + vap_revenue_inr_cr + other_operating_revenue_inr_cr` (Also `= offshore_revenue_inr_cr + onshore_revenue_inr_cr`) |
| **1a** | — *Crude Oil Revenue* *(Note 24.1)* | *(Part of Operating Revenue)* | `crude_oil_revenue_inr_cr` | Nominated blocks + JV blocks crude revenue |
| **1b** | — *Natural Gas Revenue* *(Note 24.1)* | *(Part of Operating Revenue)* | `natural_gas_revenue_inr_cr` | APM gas + New Well / Difficult Field gas revenue |
| **1c** | — *Value-Added Products (VAP) & Other* *(Note 24.1)* | *(Part of Operating Revenue)* | `vap_revenue_inr_cr` | LPG, Naphtha, C2-C3 (Ethane-Propane), SKO, ATF |
| **2** | **II. Other Income** *(Note 25)* | `Other Income Expense` + `Interest Income` | `other_income_inr_cr` | `dividend_income_inr_cr + interest_and_other_income_inr_cr` |
| **3** | **III. Total Income (`I + II`)** | `Total Revenue + Other Income` | `total_income_inr_cr` | `gross_revenue_inr_cr + other_income_inr_cr` |
| **4** | **Statutory Levies** *(Note 28)* | *(Lumped inside `Cost of Revenue`)* | `statutory_levies_total_inr_cr` | `royalty_inr_cr + oidb_cess_inr_cr + saed_windfall_tax_inr_cr + other_levies_inr_cr` |
| **4a** | — *Royalty (Offshore & Onshore)* *(Note 28)* | *(Part of Cost of Revenue)* | `royalty_inr_cr` | Statutory royalty to Central & State Govts |
| **4b** | — *OIDB Cess* *(Note 28)* | *(Part of Cost of Revenue)* | `oidb_cess_inr_cr` | 20% ad-valorem Oil Industry Development Cess |
| **4c** | — *SAED / Windfall Tax & NCCD* *(Note 28)* | *(Part of Cost of Revenue)* | `saed_windfall_tax_inr_cr` | Special Additional Excise Duty on Crude (Jul 2022 – Dec 2024) + NCCD |
| **5** | **Net Realised Revenue (after Statutory Levies)** | *(Derived Gross Margin Base)* | `net_revenue_inr_cr` | `gross_revenue_inr_cr - statutory_levies_total_inr_cr` |
| **6** | **Production, Transportation, Selling & Marketing Exp.** *(Note 29/30)* | *(Part of `Cost of Revenue` & `Operating Expense`)* | `prod_transport_selling_exp_inr_cr` | Workover, water injection, platform O&M, pipeline & marine logistics |
| **7** | **Employee Benefits Expense (Net P&L)** *(Note 31)* | `Selling General And Administration` (partial) | `employee_benefit_net_pnl_inr_cr` | `employee_cost_total_inr_cr (Gross Payroll) - employee_cost_capitalised_inr_cr (Allocated to CWIP/Drilling)` |
| **8** | **Exploration Costs Written Off** *(Note 32)* | *(Lumped inside `Operating Expense` / `DD&A`)* | `exploration_costs_written_off_inr_cr` | `survey_costs_written_off_inr_cr (2D/3D Seismic) + exploratory_wells_written_off_inr_cr (Dry Wells)` |
| **9** | **Other Operating & Provisions Expense** *(Note 35)* | `Other Operating Expenses` | `other_expenses_inr_cr` | Contractual, CSR, provisions, FX & admin expenses |
| **10** | **EBITDA (Operating Profit before Exploration Write-off & DD&A)** | `Normalized EBITDA` | `ebitda_inr_cr` | `gross_revenue_inr_cr - statutory_levies_total_inr_cr - prod_transport_selling_exp_inr_cr - employee_benefit_net_pnl_inr_cr - other_expenses_inr_cr` |
| **11** | **Depreciation, Depletion, Amortisation & Impairment (DD&A)** *(Note 33)* | `Reconciled Depreciation` | `dda_inr_cr` | Oil & gas asset depletion (unit-of-production) + plant depreciation + impairment |
| **12** | **Finance Costs** *(Note 34)* | `Interest Expense Non Operating` | `finance_costs_inr_cr` | Borrowing interest + unwinding of discount on decommissioning liability |
| **13** | **IV. Total Expenses** | `Total Expenses` | `total_expenses_inr_cr` | Sum of Lines `4 + 6 + 7 + 8 + 9 + 11 + 12` |
| **14** | **V. Profit Before Exceptional Items & Tax (`III − IV`)** | `Pretax Income` (ex-unusual) | `profit_before_exceptional_and_tax_inr_cr` | `total_income_inr_cr - total_expenses_inr_cr` |
| **15** | **VI. Exceptional Items** *(Note 36)* | `Total Unusual Items` | `exceptional_items_inr_cr` | Impairment provisions / reversals due to crude/gas price revisions |
| **16** | **VII. Profit Before Tax (PBT) (`V + VI`)** | `Pretax Income` | `pbt_inr_cr` | `profit_before_exceptional_and_tax_inr_cr + exceptional_items_inr_cr` |
| **17** | **VIII. Tax Expense** *(Note 37)* | `Tax Provision` | `tax_expense_total_inr_cr` | `current_tax_inr_cr + deferred_tax_inr_cr + earlier_year_tax_inr_cr` |
| **18** | **IX. Profit After Tax (PAT) (`VII − VIII`)** | `Net Income Common Stockholders` | `pat_inr_cr` | `pbt_inr_cr - tax_expense_total_inr_cr` |
| **19** | **Consolidated Group Revenue & PAT (`ONGC.NS`)** | `Total Revenue` & `Net Income` (`ONGC.NS`) | `consolidated_revenue_inr_cr`, `consolidated_pat_inr_cr` | ONGC Group (Standalone + OVL + HPCL + MRPL + OPaL + JVs) |
