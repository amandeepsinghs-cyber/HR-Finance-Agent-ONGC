# Holistic Financial Intelligence Feature List for Yukti AI (`FY17–FY26`)

## Core Design Principles (Non-Negotiable)
1. **Statement-First = Table-First (`visual.type = "table"`):**
   - Whenever a user asks for a **Financial Statement** (**Profit & Loss Statement**, **Balance Sheet**, **Cash Flow Statement**, **Statement of Changes in Equity**, **Ratios Summary**, or **Schedule III Note Schedule**), the **first and primary thing on screen MUST be a clean, structured accounting table** (`Line Item | Note Ref | FY Amount (₹ Cr) | Prior FY (₹ Cr) | YoY Change (₹ Cr) | YoY % | Common-Size %`), accompanied by top-line KPIs and causal takeaways.
   - **Never show a bar chart for a financial statement.**
   - **Waterfall Chart on Demand (`chart_kind = "waterfall"`):** A P&L Bridge, Cash Flow Bridge, or Working Capital Bridge is rendered **as a true Waterfall chart** (`Gross Revenue → −Statutory Levies → =Net Revenue → −Opex → =EBITDA → +Other Income → −Exploration Write-Offs → −DD&A → −Finance Costs → ±Exceptional → =PBT → −Tax → =PAT`) **when requested** (e.g., *"Show P&L bridge / waterfall"* or via the `"Show P&L Waterfall"` follow-up chip).
   - **Multi-Year Trend / Comparison Charts (`line` / `grouped_bar`):** Shown when the user asks for a multi-year trend (*"Show 10-year revenue and PAT trend"*) or component comparison (*"Compare Royalty, OIDB Cess, and SAED over 10 years"*).
2. **Complete 3-Statement + Notes + Ratios Coverage (`FY17–FY26`, Standalone & Consolidated `ONGC.NS`):**
   - Every corporate financial statement published in ONGC’s Annual Report (and on Yahoo Finance `ONGC.NS`) must be available both for **any single year (`FY17` to `FY26`)** with YoY comparison AND **across any multi-year / 10-year window (`FY17–FY26`)**.
3. **Seamless Conversational Follow-Ups on Every Line Item:**
   - After viewing any statement table, the user can ask follow-up questions on **any line item, sub-component, note, ratio, or historical variance** (*"Break down Non-Current Assets"*, *"Why did borrowings increase in FY18?"*, *"Show trade receivables aging"*, *"Compare OCF vs Free Cash Flow over 10 years"*, *"Show this as a waterfall chart"*, *"Show consolidated vs standalone balance sheet"*).

---

## Pillar 1: Complete Three-Statement Financial Model (`FY17–FY26`, Standalone & Consolidated)

### 1.1 Statement of Profit & Loss (`pnl_statement` — Ind-AS Schedule III + Yahoo Finance `ONGC.NS`)
- **Default View:** Structured 23-line Schedule III Statement Table (`visual.type = "table"`) with `Line Item`, `Note Ref`, `Amount (₹ Cr)`, `Prior FY (₹ Cr)`, `YoY Delta (₹ Cr)`, `YoY %`, and `% of Revenue`.
- **On-Demand Visual:** P&L Bridge **Waterfall Chart** (`chart_kind = "waterfall"`).
- **Complete Line Items Covered (`FY17–FY26`):**
  1. **I. Revenue from Operations (Gross) — Note 24:**
     - Crude Oil Revenue (`crude_oil_revenue_cr`)
     - Natural Gas Revenue (`natural_gas_revenue_cr` — APM & New Well Gas)
     - Value-Added Products Revenue (`vap_revenue_cr` — LPG, Naphtha, C2-C3, SKO, ATF)
     - Other Operating Revenue (`other_operating_revenue_cr`)
     - Segment Split: Offshore Revenue (`offshore_revenue_cr`) vs. Onshore Revenue (`onshore_revenue_cr`)
  2. **II. Other Income — Note 25:**
     - Dividend Income from Subsidiaries & JVs (`dividend_income_cr`)
     - Interest, Treasury & Other Non-Operating Income (`interest_and_other_income_cr`)
  3. **III. Total Income (`I + II`, `total_income_cr`)**
  4. **IV. Expenses — Notes 26–35:**
     - Changes in Inventories / Purchases of Stock-in-Trade (Notes 26–27)
     - **Statutory Levies (Note 28):** Royalty (`royalty_cr` — Offshore & Onshore), OIDB Cess (`oidb_cess_cr`), SAED Windfall Tax (`saed_windfall_tax_cr`), Natural Calamity Contingent Duty / Other Levies (`other_levies_cr`)
     - **Net Realised Revenue (after Statutory Levies, `net_revenue_cr`)**
     - **Production, Transportation, Selling & Marketing Expenses (Notes 29–30, `prod_transport_selling_exp_cr`):** Contractual workover, water injection, OSV/rig charter, pipeline transport, insurance
     - **Employee Benefits Expense (Note 31):** Gross Employee Cost (`employee_cost_cr`), Less: Allocated to CWIP/Exploratory Drilling (`employee_cost_capitalised_cr`), Net Employee Benefit Expense in P&L (`employee_benefit_net_pnl_cr`)
     - **Other Operating & Provisions Expense (Note 35, `other_expenses_cr`)**
     - **EBITDA (`ebitda_corporate_cr` & `ebitda_margin_corporate_pct`)**
     - **Exploration Costs Written Off (Note 32, `exploration_costs_written_off_cr`):** Geological & Geophysical Survey Costs Written Off (`survey_costs_written_off_cr`) + Exploratory Dry Wells Written Off (`exploratory_wells_written_off_cr`)
     - **Depreciation, Depletion, Amortisation & Impairment (Note 33, `dda_cr`):** Depletion of Oil & Gas Assets + Depreciation of PPE & ROU Assets + Impairment
     - **Finance Costs (Note 34, `finance_costs_cr`):** Interest on borrowings/bonds + Unwinding of discount on abandonment decommissioning provisions + Lease interest
  5. **V–VI. Profit Before Exceptional Items & Tax → Exceptional Items (Note 36, `exceptional_items_cr`)**
  6. **VII. Profit Before Tax (`pbt_corporate_cr` & `pbt_margin_corporate_pct`)**
  7. **VIII. Tax Expense (Note 37, `tax_expense_cr`):** Current Tax (`current_tax_cr`) + Deferred Tax (`deferred_tax_cr`) + Earlier Years Tax (`earlier_year_tax_cr`) + Effective Tax Rate (`effective_tax_rate_pct`)
  8. **IX. Standalone Profit After Tax (`pat_cr` & `pat_margin_corporate_pct`) & Other Comprehensive Income (OCI) / Total Comprehensive Income**
  9. **X. Consolidated Group P&L (`ONGC.NS`):** Consolidated Revenue (`consolidated_revenue_cr`), Consolidated EBITDA (`consolidated_ebitda_cr`), Consolidated PBT (`consolidated_pbt_cr`), Consolidated PAT (`consolidated_pat_cr`), Non-Controlling Interest (NCI), Share of Profit of Associates/JVs (Petronet LNG, Pawan Hans, Dahej SEZ, Rohini, MSEZ, IGGL).
  10. **XI. Per-Share Metrics:** Basic & Diluted EPS (`eps_basic_inr`), Dividend per Share (`dividend_per_share_inr`), Dividend Payout (`dividend_payout_cr`, `dividend_payout_ratio_pct`).

---

### 1.2 Balance Sheet (`balance_sheet` — Ind-AS Schedule III Statement of Assets, Equity & Liabilities, `FY17–FY26`)
- **Default View:** Structured Ind-AS Schedule III Balance Sheet Table (`visual.type = "table"`) showing `Assets`, `Equity`, and `Liabilities` with `Line Item`, `Note Ref`, `FY Amount (₹ Cr)`, `Prior FY (₹ Cr)`, `YoY Change (₹ Cr)`, `YoY %`, and `% of Total Assets / Equity & Liabilities`.
- **Guaranteed Accounting Identity:** `Total Assets == Total Non-Current Assets + Total Current Assets == Total Equity + Total Non-Current Liabilities + Total Current Liabilities` (`±₹0.00 Cr` across all 10 years `FY17–FY26`).
- **Complete Balance Sheet Line Items Covered (`FY17–FY26`):**
  1. **A. ASSETS**
     - **1. Non-Current Assets (`non_current_assets_cr`):**
       - Oil & Gas Assets (`oil_and_gas_assets_cr` — Producing Properties, Note 5)
       - Other Property, Plant & Equipment (`other_ppe_cr` — Plants, Pipelines, Offshore Platforms, ROU Lease Assets, Note 6)
       - Capital Work-in-Progress (`cwip_cr` — Development Wells-in-Progress & Project CWIP, e.g., KG-DWN-98/2, Daman Upside, Note 7)
       - Intangible Assets & Exploratory/Evaluation Assets (`exploratory_wells_in_progress_cr` — Exploratory Wells-in-Progress under Ind-AS 106, Note 8/9)
       - **Non-Current Financial Assets (`non_current_financial_assets_cr`):**
         - Investments in Subsidiaries, Associates & Joint Ventures (`investments_subsidiaries_jv_cr` — HPCL ₹36,915 Cr stake, OVL, MRPL, OPaL, OTPC, Petronet LNG, IOCL/GAIL listed equity, Note 10)
         - Site Restoration / Abandonment Deposit Fund (`site_restoration_fund_cr` — SBI dedicated escrow corpus under Section 33ABA, Note 11)
         - Long-Term Loans, Deposits & Other Non-Current Assets (`other_non_current_assets_cr`, Notes 11–12)
     - **2. Current Assets (`current_assets_cr`):**
       - Inventories (`inventories_cr` — Crude oil, LPG/Naphtha stock, stores & drilling spares, Note 13)
       - **Current Financial Assets:**
         - Current Investments (`current_investments_cr`, Note 10)
         - Trade Receivables (`trade_receivables_cr` — Billed & unbilled crude/gas receivables + Disputed receivables, Note 14)
         - Cash & Cash Equivalents + Other Bank Balances (`cash_and_bank_cr`, Notes 15–16)
         - Short-Term Loans & Other Current Financial Assets (`other_current_assets_cr`, Notes 17–18)
     - **TOTAL ASSETS (`total_assets_cr`)**
  2. **B. EQUITY AND LIABILITIES**
     - **1. Equity / Net Worth (`net_worth_cr`):**
       - Equity Share Capital (`equity_share_capital_cr` — `1,258.03 crore` shares of `₹5` each = `₹6,290.14 Cr`, Note 19)
       - Other Equity / Reserves & Surplus (`other_equity_reserves_cr` — General Reserve, Retained Earnings, FVOCI Equity Instruments Reserve, Note 20)
       - **Total Standalone Net Worth (`net_worth_cr`) & Consolidated Net Worth (`consolidated_net_worth_cr`)**
     - **2. Non-Current Liabilities (`non_current_liabilities_cr`):**
       - Long-Term Borrowings (`long_term_debt_cr` — Foreign currency bonds, NCDs, term loans, Note 21)
       - Long-Term Lease Liabilities (`lease_liabilities_non_current_cr` — Offshore rigs, OSVs, FPSOs under Ind-AS 116, Note 21A)
       - **Site Restoration & Decommissioning Provision (`abandonment_provision_cr` — Asset Retirement Obligation / ARO for offshore & onshore wells/platforms, Note 22)**
       - Deferred Tax Liabilities (Net) (`deferred_tax_liability_net_cr`, Note 23)
       - Other Non-Current Liabilities & Employee Benefit Obligations (`other_non_current_liabilities_cr`)
     - **3. Current Liabilities (`current_liabilities_cr`):**
       - Short-Term Borrowings & Current Maturities (`short_term_debt_cr`, Note 21)
       - Short-Term Lease Liabilities (`lease_liabilities_current_cr`)
       - Trade Payables (`trade_payables_cr` — MSME & Other O&M/Drilling Vendors, Note 24B)
       - Other Current Financial Liabilities, Provisions & Tax Liabilities (`other_current_liabilities_cr` — Unpaid dividends, capex creditors, statutory dues)
     - **TOTAL EQUITY AND LIABILITIES (`total_equity_and_liabilities_cr`)**
  3. **Derived Balance Sheet Sub-Totals:**
     - **Total Debt (`total_debt_cr = long_term_debt_cr + short_term_debt_cr`)** & **Consolidated Total Debt (`consolidated_debt_cr`)**
     - **Net Debt (`net_debt_cr = total_debt_cr - cash_and_bank_cr`)**
     - **Net Working Capital (`net_working_capital_cr = current_assets_cr - current_liabilities_cr`)**
     - **Capital Employed (`capital_employed_cr = net_worth_cr + total_debt_cr + deferred_tax_liability_net_cr`)**
     - **Book Value per Share (`book_value_per_share_inr`)**

---

### 1.3 Statement of Cash Flows (`cash_flow_statement` — Ind-AS 7 Indirect Method, `FY17–FY26`)
- **Default View:** Structured Ind-AS 7 Cash Flow Statement Table (`visual.type = "table"`) with `Line Item`, `FY Amount (₹ Cr)`, `Prior FY (₹ Cr)`, and `YoY Delta (₹ Cr)`.
- **On-Demand Visual:** Cash Flow Bridge **Waterfall Chart** (`Operating Cash Flow → −Capex → =Free Cash Flow → +Dividends Received → −Dividends Paid → ±Debt Raised/Repaid → =Net Change in Cash`).
- **Complete Cash Flow Line Items Covered (`FY17–FY26`):**
  1. **A. Cash Flow from Operating Activities (`operating_cash_flow_cr`):**
     - Profit Before Tax (`pbt_corporate_cr`)
     - Non-Cash Adjustments: `+ DD&A` (`dda_cr`), `+ Exploration Costs Written Off` (`exploration_costs_written_off_cr`), `+ Finance Costs`, `− Dividend & Interest Income`, `± Exceptional / Impairment Items` (`operating_profit_before_wc_cr`)
     - Working Capital Changes (`working_capital_change_cf_cr`: Trade Receivables, Inventories, Trade Payables & Provisions)
     - Less: Direct Income Taxes Paid (`income_tax_paid_cf_cr`)
     - **Net Cash Generated from Operating Activities (`operating_cash_flow_cr`)**
  2. **B. Cash Flow from Investing Activities (`investing_cash_flow_cr`):**
     - Capital Expenditure on Oil & Gas Assets, PPE & CWIP (`capex_cash_outflow_cr`)
     - Acquisition / Equity Infusion in Subsidiaries & JVs (`subsidiary_investment_cf_cr` — e.g., `₹36,915 Cr` HPCL buyout in `FY18`; `₹18,365 Cr` OPaL debt-to-equity restructuring in `FY25`)
     - Contributions to Site Restoration Fund (`site_restoration_deposit_cf_cr`)
     - Dividends & Interest Received from Subsidiaries/JVs (`dividend_interest_received_cf_cr`)
     - **Net Cash Used in Investing Activities (`investing_cash_flow_cr`)**
  3. **C. Cash Flow from Financing Activities (`financing_cash_flow_cr`):**
     - Proceeds from / (Repayment of) Long-Term & Short-Term Borrowings (`net_borrowings_cf_cr`)
     - Payment of Lease Liabilities (`lease_payments_cf_cr`)
     - Finance Costs / Interest Paid (`interest_paid_cf_cr`)
     - Dividends Paid to Shareholders (incl. GoI & public shareholders, `dividend_paid_cf_cr`)
     - Share Buyback (`share_buyback_cf_cr` — e.g., `FY19` ₹4,022 Cr buyback)
     - **Net Cash Used in Financing Activities (`financing_cash_flow_cr`)**
  4. **D. Net Change in Cash & Free Cash Flow Summary:**
     - Opening Cash & Cash Equivalents (`opening_cash_cr`) → Net Change in Cash (`net_cash_change_cr`) → Closing Cash (`closing_cash_cr`)
     - **Free Cash Flow (`free_cash_flow_cr = operating_cash_flow_cr - total_capex_cr`)**
     - **Cash Conversion Ratio (`ocf_to_ebitda_pct`)**

---

## Pillar 2: Comprehensive Financial Ratios, Valuation & Credit Health (`financial_ratios`, `FY17–FY26`)
- **Default View:** Structured Financial Ratios Scorecard Table (`visual.type = "table"`) grouped by category (`Profitability`, `Return & Efficiency`, `Leverage & Solvency`, `Liquidity & Working Capital`, `Per-Share & Dividend`, `Upstream E&P Unit Economics`).
- **Complete Ratios Covered (`FY17–FY26`):**
  1. **Profitability Margins:** Gross Margin (Net of Levies %), EBITDA Margin (`ebitda_margin_corporate_pct`), Operating / EBIT Margin (`ebit_margin_pct`), PBT Margin (`pbt_margin_corporate_pct`), Net PAT Margin (`pat_margin_corporate_pct`), Effective Tax Rate (`effective_tax_rate_pct`).
  2. **Return Metrics:** Return on Capital Employed (`roce_pct` Standalone & `consolidated_roce_pct` Consolidated), Return on Equity (`roe_pct = PAT / Net Worth`), Return on Assets (`roa_pct = PAT / Total Assets`).
  3. **Leverage & Solvency (SEBI Listing Reg 52(4) Ratios):** Debt-to-Equity Ratio (`debt_to_equity_ratio`), Net Debt-to-EBITDA (`net_debt_to_ebitda_ratio`), Interest Coverage Ratio (`interest_coverage_ratio = EBIT / Finance Costs`), Debt Service Coverage Ratio (`dscr_ratio`).
  4. **Liquidity & Working Capital Efficiency:** Current Ratio (`current_ratio = Current Assets / Current Liabilities`), Quick Ratio (`quick_ratio`), Debtor / Receivable Days (`receivable_days = (Trade Receivables / Gross Revenue) * 365`), Inventory Turnover Days (`inventory_days`), Payable Days (`payable_days`).
  5. **Per-Share & Shareholder Return:** Basic EPS (`eps_basic_inr`), Book Value per Share (`book_value_per_share_inr`), Dividend per Share (`dividend_per_share_inr`), Dividend Payout Ratio (`dividend_payout_ratio_pct`), FCF per Share (`fcf_per_share_inr`).
  6. **Upstream E&P Unit Economics (`$/bbl` & `$/BOE`):**
     - Nominated Crude Realisation (`crude_realisation_usd_bbl`), Net Crude Realisation after SAED (`net_crude_realisation_usd_bbl`), Natural Gas Realisation (`gas_realisation_usd_mmbtu`)
     - Statutory Levies per BOE (`statutory_levies_usd_boe`), Lifting / Operating Cost per BOE (`lifting_cost_average_usd_boe`), DD&A & Depletion Cost per BOE (`dda_cost_usd_boe`), Finding & Development Cost per BOE (`finding_development_cost_usd_boe`), Netback Margin per BOE (`ebitda_netback_usd_boe`), Reserve Replacement Ratio (`rrr_2p`).

---

## Pillar 3: Deep-Dive Sub-Systems (Reconciled Top-Down to Corporate Statements)
1. **Consolidated Group vs. Standalone & 5 Major Subsidiaries (`subsidiaries`, `FY17–FY26`):**
   - Full 10-year breakdown of **HPCL** (Refining & Marketing), **MRPL** (Mangalore Refinery), **OVL** (ONGC Videsh — International E&P across 15 countries), **OPaL** (Dahej Petrochemicals), and **OTPC** (Tripura Gas Power): Revenue, EBITDA, PAT, ROCE, Equity Holding %, Dividend Declared & Received by ONGC, Refining GRM (`$/bbl`), and International Output (`MMTOE`).
2. **Segment, Basin, Asset (15 Assets) & Field (53 Fields) Economics (`field_pnl`, `FY17–FY26`):**
   - Reconciled top-down so Offshore + Onshore and all 53 fields sum to Corporate Schedule III Revenue, Royalty, OIDB Cess, SAED, Net Revenue, Manpower, Opex, EBITDA, DD&A, and PBT.
   - Loss-making fields (`3-year consecutive loss`), PEC/farm-out candidates, lifting cost rankings, and water-cut / downtime drivers.
3. **Capital Expenditure (BE vs. RE vs. Actuals) & Major Projects (`capex`, `FY17–FY27`):**
   - Capex by Asset and Capex Head (`Exploratory Drilling`, `Development Drilling`, `Capital Projects / Offshore Platforms`, `Seismic Survey`, `R&D / Green Energy Transition`), plus Capex vs. 2P Reserves under-investment analysis.
4. **Working Capital, Receivables, Treasury & Governance Trackers:**
   - Trade Receivables & Disputed Receivables (`receivables_outstanding_cr`, `disputed_receivables_cr`)
   - Actuarial Employee Benefit Liabilities (`actuarial_liability_cr`, `net_benefit_liability_cr` — PRBS, Gratuity, PRMS, Leave Encashment)
   - Energy Transition / Green Capex & Renewable Installed MW (`renewable_installed_mw`, `green_capex_cr`)
   - MoU (MoPNG/DPE) Scorecard (`mou_scorecard`) & CSR Spend (`csr_spend_cr`).

---

## Pillar 4: Historical Causal Vector RAG ("Why Did Any Line Item Change?")
- Every major line item across the **P&L**, **Balance Sheet**, **Cash Flow Statement**, and **Ratios** (`FY17–FY26`) is anchored to embedded Schedule III Notes & MD&A explanations (`hrfin_docs.financial_notes_chunks` via Vertex AI `text-embedding-005`), so the agent answers **why** any number moved:
  - *P&L:* Why FY20 PAT fell (`-₹6,685 Cr` COVID Ind-AS 36 impairment); why FY22 Tax dropped (`Section 115BAA` `₹8,919 Cr` deferred tax credit lifting PAT to `₹40,306 Cr`); why FY23 Levies hit `₹49,120 Cr` (SAED windfall tax introduced July 2022); why FY25 Levies dropped (`-₹3,010 Cr`) and FY26 saved `-₹4,606 Cr` (SAED abolished Dec 2, 2024); why FY26 Exploration Write-Offs rose to `₹7,320 Cr` (`3` KG deepwater + `2` Kutch dry wells).
  - *Balance Sheet:* Why Standalone Borrowings jumped from `₹0 Cr` in FY17 to `₹25,592 Cr` in FY18 (`₹36,915 Cr` acquisition of 51.11% stake in HPCL); why Lease Liabilities & ROU Assets appeared in FY20 (adoption of `Ind-AS 116 Leases` for offshore charter rigs/OSVs); why CWIP peaked in FY24–FY25 and transferred to Oil & Gas Producing Properties in FY25–FY26 (commissioning of `KG-DWN-98/2 Cluster-2`); why Non-Current Investments jumped in FY25–FY26 (`₹18,365 Cr` OPaL CCD-to-equity restructuring + `₹3,530 Cr` ONGC Green Ltd infusion); how the `Site Restoration Fund` matches the `₹41,250 Cr` `Abandonment Decommissioning Provision` (Note 18).
  - *Cash Flow:* How ONGC generated `₹54,120 Cr` Operating Cash Flow and `₹18,220 Cr` Free Cash Flow in FY26 while funding `₹35,900 Cr` Capex and `₹15,410 Cr` Dividend Payout.

---

## Pillar 5: Hybrid Line-Item Context Bridge (`ssot_financial_line_context`) & Persisted Context Reports
- **Why Pure BigQuery Numbers Alone Do Not Suffice:** A numbers table stores *what* the figure is (`₹32,894 Cr`), whereas a Finance Director requires *why* it moved and *what happened* in the Annual Report across all 10 years (`FY17–FY26`).
- **Three-Layer Context Persistence:**
  1. **Markdown Context Reports (`financial_build/context_reports/*.md`):**
     - `01_FY17_to_FY26_Chronological_MDA_Dossier.md` (Year-by-year FY17–FY26 audited MD&A chronicle).
     - `02_Schedule_III_Notes_5_to_37_Context_Catalog.md` (Complete Note 5 to Note 37 accounting breakdown).
     - `03_Director_Finance_Action_Playbook.md` (Quantified financial & operational interventions for the Finance Director).
  2. **Deterministic Line-Item Context Ledger (`hrfin_gold.ssot_financial_line_context`):**
     - Keyed by `(fy, statement_type, line_code, note_ref)` across `FY17–FY26` (`100+` structured context records).
     - Stores `what_happened_summary`, `annual_report_context`, `historical_10yr_context`, `director_finance_action`, and `source_citation`.
  3. **Semantic Vector Knowledge Base (`hrfin_docs.financial_notes_chunks`):**
     - `80+` rich narrative chunks embedded with Vertex AI `text-embedding-005` (`768` dimensions), supporting both metadata-filtered lookup (`fy`, `statement_type`, `note_ref`, `line_codes`) and Cosine Distance semantic retrieval.

---

## Pillar 6: Director (Finance) Decision & Action Engine
- Every financial view and variance explanation surfaces concrete, quantified **Director (Finance) Recommended Actions**:
  - **Revenue & Realization (`Note 24`):** Reallocate `₹4,200 Cr` infill capex to New Well Gas (`$7.80/MMBTU`, `+20%` over `$6.50/MMBTU` APM ceiling) in Bassein, Daman, and Tripura (`+₹1,480 Cr/yr` incremental margin).
  - **Mature Field Lifting Cost (`Note 26`):** Transition `12` high-water-cut (`>78%`) marginal clusters in Mehsana/Ankleshwar/Cambay to revenue-sharing PEC contracts (`-₹620 Cr/yr` opex) and shift ESP/SRP artificial lift to `180 MW` captive solar via ONGC Green (`-₹310 Cr/yr` power cost).
  - **Exploration Dry-Hole Governance (`Note 28`):** Mandate `30%–40%` PI technical partner carry on ultra-deepwater wildcat wells (`>₹750 Cr/well`) in Andaman and KG-UDW (`₹1,500–₹2,000 Cr/yr` P&L protection).
  - **Subsidiary Capital Allocation (`Note 8`):** Substitute imported naphtha at OPaL with `100%` captive C2-C3 from Dahej/Hazira and complete SEZ exit (`+₹1,150 Cr/yr` EBITDA uplift to achieve OPaL PAT breakeven).
  - **Treasury & Working Capital (`Notes 12, 16`):** Prepay `₹2,710 Cr` `7.65%` short-term working-capital borrowings using unrestricted treasury cash (`₹205 Cr/yr` Finance Cost saving).
