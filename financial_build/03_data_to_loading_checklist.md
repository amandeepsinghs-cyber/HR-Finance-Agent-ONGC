# End-to-End Execution Checklist: From Annual Reports & Yahoo Finance (`ONGC.NS`) to BigQuery Cube & Vector Embeddings

All 5 stages of the **10-Year ONGC Financial Intelligence + Historical Causal Vector RAG** build have been executed and verified end-to-end.

---

## Stage 1: Dual-Source Data Capture (`ONGC Annual Reports` + `Yahoo Finance ONGC.NS`)
- [x] **1.1 Capture Standardized Yahoo Finance (`ONGC.NS`) Series (`financial_build/scripts/build_10yr_financials.py`):**
  - [x] Extracted and verified Consolidated & Standalone Income Statement lines (`Total Revenue`, `Operating Revenue`, `Cost of Revenue`, `Gross Profit`, `Operating Expense`, `Operating Income`, `Net Non-Operating Interest Income/Expense`, `Other Income/Expense`, `Pretax Income [PBT]`, `Tax Provision`, `Net Income Common Stockholders [PAT]`, `Normalized EBITDA`, `Reconciled Depreciation [DD&A]`, `Basic/Diluted EPS`).
  - [x] Extracted and verified Balance Sheet & Cash Flow lines (`Total Debt`, `Net Worth`, `Operating Cash Flow [OCF]`, `Capital Expenditure`, `Free Cash Flow [FCF]`, `Cash Dividends Paid`).
- [x] **1.2 Capture 10-Year ONGC Published Annual Report Schedule III Series (`FY17–FY26`):**
  - [x] **I. Revenue from Operations (`gross_revenue_inr_cr`):**
    - Verified published benchmarks: `FY17` ₹77,908 Cr | `FY18` ₹85,004 Cr | `FY19` ₹1,09,655 Cr | `FY20` ₹96,214 Cr | `FY21` ₹68,141 Cr | `FY22` ₹1,10,345 Cr | `FY23` ₹1,55,517 Cr | `FY24` ₹1,38,402 Cr | `FY25` ₹1,37,846 Cr | `FY26` ₹1,32,508 Cr.
    - Note 24 Product Split: `crude_oil_revenue_inr_cr`, `natural_gas_revenue_inr_cr`, `vap_revenue_inr_cr`, `other_operating_revenue_inr_cr`.
    - Segment Split: `offshore_revenue_inr_cr` + `onshore_revenue_inr_cr`.
  - [x] **II. Other Income (`other_income_inr_cr`, Note 25):** Dividend Income + Interest & Treasury Income.
  - [x] **III. Total Income (`total_income_inr_cr = I + II`).**
  - [x] **IV. Schedule III Expenses & Upstream Oil & Gas Notes (Notes 28–35):**
    - **Statutory Levies (`statutory_levies_total_inr_cr`, Note 28):** `royalty_inr_cr` + `oidb_cess_inr_cr` + `saed_windfall_tax_inr_cr` + `other_levies_inr_cr`.
    - **Production, Transportation, Selling & Marketing Expenses (`prod_transport_selling_exp_inr_cr`).**
    - **Employee Benefits Expense (Note 31):** Both `employee_benefit_net_pnl_inr_cr` (Net charged to P&L) and `employee_cost_total_inr_cr` (Gross employee payroll before CWIP/E&D capitalisation).
    - **Exploration Costs Written Off (`exploration_costs_written_off_inr_cr`, Note 32):** `survey_costs_written_off_inr_cr` + `exploratory_wells_written_off_inr_cr` (Dry Wells).
    - **Depreciation, Depletion, Amortisation & Impairment (`dda_inr_cr`, Note 33).**
    - **Finance Costs (`finance_costs_inr_cr`, Note 34) & Other Expenses (`other_expenses_inr_cr`, Note 35).**
  - [x] **V–IX. Profitability & Tax Bridge:**
    - `ebitda_inr_cr` & `ebitda_margin_pct`
    - `exceptional_items_inr_cr` (Note 36: `FY20` -₹4,899 Cr COVID impairment; `FY22` +₹7,178 Cr reversal)
    - `pbt_inr_cr` & `pbt_margin_pct`
    - `tax_expense_total_inr_cr` (Note 37: `current_tax_inr_cr` + `deferred_tax_inr_cr`, incl. `FY22` Section 115BAA deferred tax credit of -₹8,846 Cr)
    - `pat_inr_cr` & `pat_margin_pct` (`FY17` ₹17,900 Cr .. `FY22` ₹40,306 Cr .. `FY24` ₹40,526 Cr .. `FY25` ₹35,610 Cr .. `FY26` ₹32,894 Cr)
  - [x] **X. Consolidated Group (`ONGC.NS`) & Subsidiary Bridge (`consolidated_revenue_inr_cr`, `consolidated_ebitda_inr_cr`, `consolidated_pbt_inr_cr`, `consolidated_pat_inr_cr`).**
  - [x] **XI. Macro & Physical Realisations (`crude_realisation_usd_bbl`, `gas_realisation_usd_mmbtu`, `fx_inr_per_usd`, `oil_prod_mmt`, `gas_prod_bcm`).**

---

## Stage 2: Deterministic Accounting Identity & Cross-Walk Gate (`verify_pnl_identities.py`)
- [x] **2.1 Verified All 11 Accounting Identities Across All 10 Fiscal Years (`110/110` checks passed, `±₹0.00 Cr`):**
  - [x] `Crude + Gas + VAP + Other Operating Revenue == Revenue from Operations`
  - [x] `Offshore Revenue + Onshore Revenue == Revenue from Operations`
  - [x] `Revenue from Operations + Other Income == Total Income`
  - [x] `Royalty + OIDB Cess + SAED Windfall Tax + Other Levies == Total Statutory Levies`
  - [x] `Revenue from Operations - Total Statutory Levies == Net Realised Revenue`
  - [x] `Survey Costs Written Off + Exploratory Dry Wells Written Off == Total Exploration Costs Written Off`
  - [x] `Prod/Trans/Selling + Net Employee Benefits + Other Opex == Total Operating Expenses`
  - [x] `Net Realised Revenue - Total Operating Expenses == Standalone EBITDA`
  - [x] `EBITDA + Other Income - Exploration Write-Offs - DD&A - Finance Costs + Exceptional Items == Profit Before Tax (PBT)`
  - [x] `Current Tax + Deferred Tax + Earlier Year Tax == Total Tax Expense`
  - [x] `PBT - Total Tax Expense == Standalone Profit After Tax (PAT)`

---

## Stage 3: BigQuery Financial Cube Loading & Top-Down Sub-Table Reconciliation (`load_and_reconcile_bq.py`)
- [x] **3.1 Updated Corporate Wide Tables (`hrfin_silver.corporate_financials` & `hrfin_gold.ssot_corporate_annual_360`):**
  - [x] Loaded all `10` rows (`FY17–FY26`) × `78` columns.
- [x] **3.2 Created Normalized Schedule III Statement Table (`hrfin_gold.ssot_corporate_pnl_lines`):**
  - [x] Loaded `23` ordered Schedule III + Yahoo Finance (`ONGC.NS`) P&L lines × `10` fiscal years (`230` rows).
- [x] **3.3 Reconciled Sub-Tables Top-Down (`agg_field_pnl_summary`, `ssot_field_economics_360`, `subsidiary_financials`):**
  - [x] Reconciled all `530` field-year rows across `53` fields / `15` assets (`FY17–FY26`) so Offshore & Onshore Revenue, Statutory Levies (incl. `FY23–FY25` SAED Windfall Tax), EBITDA, DD&A, and PBT sum to **100.0%** of published corporate numbers.
  - [x] Loaded `50` subsidiary-year rows (`HPCL`, `MRPL`, `OVL`, `OPAL`, `OTPC` × `FY17–FY26`) into `hrfin_silver.subsidiary_financials`.
- [x] **3.4 Refreshed Profiled Semantic Catalog (`yukti/backend/app/semantic/semantic_catalog.json`).**

---

## Stage 4: Line-Item-Anchored Vector Embeddings (`build_and_load_financial_rag.py`)
- [x] **4.1 Built Audited Historical Causal Corpus (`financial_build/data/financial_notes_corpus.jsonl`).**
- [x] **4.2 Generated `768`-d Embeddings with Vertex AI `text-embedding-005` and Loaded into `ongc-hr-finance-agent.hrfin_docs.financial_notes_chunks`.**
- [x] **4.3 Wired Hybrid Causal Retrieval into `insight_context.py`, `pipeline.py`, and `policy_search.py`.**

---

## Stage 5: Planner, Compiler & Live UI Verification
- [x] **5.1 Upgraded `semantic_model.yaml`, `normalize.py`, `planner.py`, `compiler.py`, `presenter.py`, `insights.py`, `drilldowns.py`, and `AnswerCard.tsx`.**
- [x] **5.2 Rebuilt Production Frontend Bundle and Verified Live on `:3200` and `:3300`.**
