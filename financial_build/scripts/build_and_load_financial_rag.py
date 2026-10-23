#!/usr/bin/env python3
"""
Stage 4: Build & Load Hybrid Financial Context Database (10-Year Historical + Present FY17-FY26):
1. Builds `financial_build/data/ssot_financial_line_context.json` (100 structured line-item context + Director Finance action records across FY17-FY26)
   and loads into `ongc-hr-finance-agent.hrfin_gold.ssot_financial_line_context`.
2. Generates `financial_build/data/financial_notes_corpus.jsonl` (65+ rich causal & action chunks anchored by
   `fiscal_year`, `line_code`, `note_ref`, `section_type`, `causal_tags`, `yahoo_finance_equivalent`).
3. Computes 768-d embeddings using Vertex AI `text-embedding-005` and loads into `ongc-hr-finance-agent.hrfin_docs.financial_notes_chunks`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from google.cloud import bigquery
from google import genai
from google.genai import types

PROJECT_ID = "ongc-hr-finance-agent"
LOCATION = "us-central1"
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

FY_DIRECTOR_ACTIONS: Dict[str, Dict[str, str]] = {
    "FY17": {
        "pnl": "Lock in long-term deepwater rig contracts at trough day-rates for KG-DWN-98/2 Cluster-2 FDP execution while preserving debt-free balance sheet.",
        "bs": "Maintain ₹13,014 Cr treasury liquidity buffer to fund upcoming upstream acquisitions and deepwater subsea capex without diluting equity.",
        "cf": "Deploy ₹28,510 Cr operating cash flow into Western Offshore redevelopment and KG-DWN-98/2 early subsea tree procurement.",
        "ratios": "Advocate with MoPNG for revision of domestic APM gas floor price ($2.50/MMBTU) to restore gas segment ROCE above 14%.",
    },
    "FY18": {
        "pnl": "Accelerate post-merger synergy capture between ONGC upstream crude supply and newly acquired HPCL (51.11% stake) refineries.",
        "bs": "Prioritize retiring the ₹25,592 Cr short-term HPCL acquisition bridge loan out of FY19-FY20 free cash flows to restore debt-to-equity below 0.10x.",
        "cf": "Ring-fence ₹36,915 Cr HPCL equity buyout via short-term commercial paper & bridge facilities at <6.9% cost of debt.",
        "ratios": "Establish consolidated Group capital allocation framework across HPCL, MRPL, OVL, and OPaL following HPCL consolidation.",
    },
    "FY19": {
        "pnl": "Channel higher crude realization ($68.19/bbl) windfall into brownfield EOR/IOR schemes in Mumbai High and Mehsana to arrest natural decline.",
        "bs": "Prepay ₹3,998 Cr of HPCL bridge borrowings and execute ₹4,022 Cr share buyback while growing Net Worth to ₹2,02,990 Cr.",
        "cf": "Utilize ₹42,290 Cr Operating Cash Flow to fund ₹29,450 Cr capex, ₹4,022 Cr buyback, and debt reduction simultaneously.",
        "ratios": "Sustain 17.8% ROCE and 53.2% EBITDA margin through strict offshore logistics and OSV charter cost rationalization.",
    },
    "FY20": {
        "pnl": "Elect Section 115BAA 25.168% corporate tax regime to permanently lower effective tax rate and cushion the ₹6,685 Cr Ind-AS 36 COVID impairment.",
        "bs": "Adopt Ind-AS 116 lease accounting transparently for offshore rigs/FPSOs and stress-test CGU carrying values at $45/bbl Brent.",
        "cf": "Preserve ₹36,920 Cr operating cash generation via emergency working capital release and deferral of discretionary G&A.",
        "ratios": "Protect investment-grade credit metrics (Debt/Equity 0.11x) despite pandemic Q4 crude collapse.",
    },
    "FY21": {
        "pnl": "Enforce pandemic opex austerity and high-grade exploratory drilling to keep EBITDA margin at 48.0% despite $42.78/bbl crude and $1.79/MMBTU gas trough.",
        "bs": "Maintain ₹3,18,452 Cr asset integrity and fund KG-98/2 subsea installation milestones through low-cost working capital lines.",
        "cf": "Keep Free Cash Flow positive (+₹1,540 Cr) at $42.78/bbl crude by prioritizing fast-payback workover wells.",
        "ratios": "Hedge downside gas realization risk by accelerating deepwater HPHT gas commercialization eligible for premium pricing.",
    },
    "FY22": {
        "pnl": "Crystallize ₹8,919 Cr Section 115BAA deferred tax write-back and +₹7,178 Cr impairment reversal to deliver ₹40,306 Cr PAT.",
        "bs": "Pay down ₹14,070 Cr of short-term borrowings in a single year, slashing Total Debt from ₹24,845 Cr to ₹10,775 Cr (Debt/Equity 0.04x).",
        "cf": "Convert ₹55,890 Cr Operating Cash Flow into ₹27,360 Cr Free Cash Flow and restore treasury cash to ₹6,840 Cr.",
        "ratios": "Deliver 17.4% ROE and 55.0% EBITDA margin while increasing dividend payout to ₹10.50/share.",
    },
    "FY23": {
        "pnl": "Engage Ministry of Finance on fortnightly SAED windfall tax calibration (₹10,964 Cr SAED impact) so upstream capex remains self-funded.",
        "bs": "Ring-fence Sakhalin-1 and Mozambique geopolitical exposure via ₹9,235 Cr conservative provision while cutting standalone debt to ₹7,215 Cr.",
        "cf": "Generate record ₹64,350 Cr Operating Cash Flow and ₹34,140 Cr Free Cash Flow to build a ₹22,490 Cr cash cushion.",
        "ratios": "Offset HPCL retail fuel under-recoveries at the Group level with record upstream standalone cash generation.",
    },
    "FY24": {
        "pnl": "Capture Kirit Parikh Committee $6.50/MMBTU APM gas ceiling stability and lower SAED (-₹4,531 Cr) to achieve all-time high ₹40,526 Cr Standalone PAT.",
        "bs": "Build Cash & Bank balances to ₹30,020 Cr (-₹23,391 Cr Net Cash) to prepare for OPaL capital restructuring and KG-98/2 commissioning.",
        "cf": "Deploy ₹37,490 Cr capex into KG-DWN-98/2 Cluster-2 FPSO hookup and Western Offshore pipeline renewal out of ₹62,480 Cr OCF.",
        "ratios": "Maximize Group Consolidated PAT (₹57,101 Cr) and dividend upstreaming from HPCL and MRPL.",
    },
    "FY25": {
        "pnl": "Capitalize on Dec 2, 2024 SAED windfall tax abolition and ramp up KG-DWN-98/2 Cluster-2 M-field oil production to offset mature onshore decline.",
        "bs": "Execute ₹18,365 Cr OPaL CCD-to-equity conversion (95.69% subsidiary) to eliminate high-cost OPaL external debt guarantees.",
        "cf": "Fund ₹37,950 Cr capex and ₹15,890 Cr dividends entirely from ₹58,920 Cr Operating Cash Flow.",
        "ratios": "Require farm-out risk-sharing on frontier deepwater wildcat wells after FY25 dry-well write-offs rose to ₹9,826 Cr.",
    },
    "FY26": {
        "pnl": "Reallocate ₹4,200 Cr FY27 infill capex to New Well Gas ($7.80/MMBTU, +20% premium over APM) in Bassein/Daman/Tripura (+₹1,480 Cr/yr revenue) and transition 12 high-water-cut mature clusters to PEC contracts (-₹620 Cr/yr opex).",
        "bs": "Prepay ₹1,730 Cr short-term working capital debt using ₹33,500 Cr treasury cash (-₹25,650 Cr Net Cash) to save ₹135+ Cr/yr in finance costs, and supply 100% captive C2-C3 feedstock to OPaL (+₹1,150 Cr/yr EBITDA).",
        "cf": "Sustain ₹59,840 Cr Operating Cash Flow and ₹23,962 Cr Free Cash Flow while enforcing 30%-40% PI partner carry on ultra-deepwater wildcat wells (>₹750 Cr/well) to cap Note 32 dry-hole write-offs.",
        "ratios": "Defend 48.2% EBITDA margin and 14.3% ROCE via captive 180 MW solar power for onshore artificial lift (-₹310 Cr/yr power cost) and automated PSU refinery LC collection (31.5 receivable days).",
    },
}


def build_line_context_rows(wide_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for idx, r in enumerate(wide_rows):
        fy = r["fiscal_year"]
        prev = wide_rows[idx - 1] if idx > 0 else None
        act = FY_DIRECTOR_ACTIONS[fy]

        def delta(col: str) -> tuple[float, float, float]:
            cur = float(r.get(col) or 0.0)
            prv = float(prev.get(col) or 0.0) if prev else cur
            d_cr = round(cur - prv, 2) if prev else 0.0
            d_pct = round((d_cr / abs(prv)) * 100.0, 2) if (prev and abs(prv) > 1e-6) else 0.0
            return cur, prv, d_cr, d_pct

        # 1. P&L Headline Context (PAT & Full P&L Statement)
        cur, prv, d_cr, d_pct = delta("pat_inr_cr")
        rows.append({
            "context_id": f"CTX-{fy}-PNL-PAT",
            "fy": fy,
            "statement_type": "PNL",
            "line_code": "pnl_statement",
            "line_name": "Statement of Profit & Loss (PAT & Full Bridge)",
            "note_ref": "Notes 24–37",
            "amount_cr": cur,
            "prev_amount_cr": prv,
            "yoy_delta_cr": d_cr,
            "yoy_delta_pct": d_pct,
            "what_happened_summary": r["primary_driver_note"],
            "annual_report_context": (
                f"In {fy}, Gross Revenue was ₹{r['gross_revenue_inr_cr']:,.0f} Cr (Crude ${r['crude_realisation_usd_bbl']}/bbl, Gas ${r['gas_realisation_usd_mmbtu']}/MMBtu), "
                f"Statutory Levies were ₹{r['statutory_levies_total_inr_cr']:,.0f} Cr (Royalty ₹{r['royalty_inr_cr']:,.0f} Cr, OIDB Cess ₹{r['oidb_cess_inr_cr']:,.0f} Cr, SAED ₹{r['saed_windfall_tax_inr_cr']:,.0f} Cr), "
                f"EBITDA stood at ₹{r['ebitda_inr_cr']:,.0f} Cr ({r['ebitda_margin_pct']}% margin), Exploration Write-Offs were ₹{r['exploration_costs_written_off_inr_cr']:,.0f} Cr, "
                f"DD&A was ₹{r['dda_inr_cr']:,.0f} Cr, Exceptional Items were ₹{r['exceptional_items_inr_cr']:,.0f} Cr, and Standalone PAT reached ₹{r['pat_inr_cr']:,.0f} Cr "
                f"(Consolidated Group PAT: ₹{r['consolidated_pat_inr_cr']:,.0f} Cr on ₹{r['consolidated_revenue_inr_cr']:,.0f} Cr Group Revenue)."
            ),
            "historical_10yr_context": (
                "Across FY17–FY26, Standalone Revenue grew from ₹77,908 Cr (FY17) to a peak of ₹1,55,517 Cr (FY23) and ₹1,32,508 Cr (FY26), "
                "while Standalone PAT nearly doubled from ₹17,900 Cr (FY17) to ₹32,894 Cr (FY26), peaking at ₹40,526 Cr in FY24."
            ),
            "director_finance_action": act["pnl"],
            "source_citation": f"ONGC Audited Annual Report {fy} (Schedule III Statement of Profit & Loss, Notes 24–37 & MD&A)",
        })

        # 2. Balance Sheet Headline Context
        cur, prv, d_cr, d_pct = delta("total_assets_inr_cr")
        rows.append({
            "context_id": f"CTX-{fy}-BS-TOTAL",
            "fy": fy,
            "statement_type": "BALANCE_SHEET",
            "line_code": "balance_sheet",
            "line_name": "Schedule III Balance Sheet (Assets, Equity & Liabilities)",
            "note_ref": "Notes 5–23",
            "amount_cr": cur,
            "prev_amount_cr": prv,
            "yoy_delta_cr": d_cr,
            "yoy_delta_pct": d_pct,
            "what_happened_summary": r["balance_sheet_driver_note"],
            "annual_report_context": (
                f"As of 31 March {fy}, Total Assets stood at ₹{r['total_assets_inr_cr']:,.0f} Cr: Non-Current Assets ₹{r['non_current_assets_inr_cr']:,.0f} Cr "
                f"(Oil & Gas Assets Net Block ₹{r['oil_and_gas_assets_inr_cr']:,.0f} Cr [Note 5], CWIP & Exploratory Wells ₹{r['cwip_inr_cr'] + r['exploratory_wells_in_progress_inr_cr']:,.0f} Cr [Notes 7–8], "
                f"Subsidiary/JV Investments ₹{r['investments_subsidiaries_jv_inr_cr']:,.0f} Cr [Note 10], Site Restoration Fund ₹{r['site_restoration_fund_inr_cr']:,.0f} Cr [Note 11]) "
                f"and Current Assets ₹{r['current_assets_inr_cr']:,.0f} Cr (Cash & Bank ₹{r['cash_and_bank_inr_cr']:,.0f} Cr). "
                f"Funded by Net Worth of ₹{r['net_worth_inr_cr']:,.0f} Cr (Notes 19–20), Total Borrowings of ₹{r['total_debt_inr_cr']:,.0f} Cr (Debt/Equity {r['debt_to_equity_ratio']:.2f}x, Net Debt ₹{r['net_debt_inr_cr']:,.0f} Cr), "
                f"and Abandonment Provision of ₹{r['abandonment_provision_inr_cr']:,.0f} Cr (Note 22)."
            ),
            "historical_10yr_context": (
                "Over FY17–FY26, Standalone Total Assets expanded +91.9% from ₹2,47,240 Cr to ₹4,74,340 Cr and Net Worth grew +72.8% from ₹1,85,540 Cr to ₹3,20,635 Cr, "
                "while the ₹25,592 Cr HPCL acquisition debt in FY18 was pared down to ₹7,850 Cr in FY26 (-₹25,650 Cr Net Cash)."
            ),
            "director_finance_action": act["bs"],
            "source_citation": f"ONGC Audited Annual Report {fy} (Schedule III Balance Sheet, Notes 5–23)",
        })

        # 3. Cash Flow Statement Context
        cur, prv, d_cr, d_pct = delta("operating_cash_flow_inr_cr")
        rows.append({
            "context_id": f"CTX-{fy}-CF-TOTAL",
            "fy": fy,
            "statement_type": "CASH_FLOW",
            "line_code": "cash_flow_statement",
            "line_name": "Statement of Cash Flows (Ind-AS 7 Indirect Method)",
            "note_ref": "Ind-AS 7 Cash Flow",
            "amount_cr": cur,
            "prev_amount_cr": prv,
            "yoy_delta_cr": d_cr,
            "yoy_delta_pct": d_pct,
            "what_happened_summary": (
                f"In {fy}, Operating Cash Flow was ₹{r['operating_cash_flow_inr_cr']:,.0f} Cr, funding ₹{r['total_capex_spent_inr_cr']:,.0f} Cr Capex "
                f"and generating ₹{r['free_cash_flow_inr_cr']:,.0f} Cr Free Cash Flow alongside ₹{abs(r['dividend_paid_cf_inr_cr']):,.0f} Cr Dividend payout."
            ),
            "annual_report_context": (
                f"In {fy}, Net Cash from Operating Activities was ₹{r['operating_cash_flow_inr_cr']:,.0f} Cr ({r['ocf_to_ebitda_pct']}% OCF-to-EBITDA conversion), "
                f"Net Cash Used in Investing Activities was ₹{r['investing_cash_flow_inr_cr']:,.0f} Cr (Capex cash outflow ₹{r['capex_cash_outflow_inr_cr']:,.0f} Cr, "
                f"Subsidiary equity infusions ₹{r['subsidiary_investment_cf_inr_cr']:,.0f} Cr, Dividends/Interest received +₹{r['dividend_interest_received_cf_inr_cr']:,.0f} Cr), "
                f"and Net Cash from Financing Activities was ₹{r['financing_cash_flow_inr_cr']:,.0f} Cr (Net borrowings change ₹{r['net_borrowings_cf_inr_cr']:,.0f} Cr, "
                f"Dividends paid -₹{r['dividend_paid_cf_inr_cr']:,.0f} Cr)."
            ),
            "historical_10yr_context": (
                "Across FY17–FY26, ONGC generated ₹4,58,665 Cr cumulative Operating Cash Flow and ₹1,58,528 Cr cumulative Free Cash Flow after investing ₹3,00,137 Cr in upstream E&P capex."
            ),
            "director_finance_action": act["cf"],
            "source_citation": f"ONGC Audited Annual Report {fy} (Statement of Cash Flows under Ind-AS 7)",
        })

        # 4. Financial Ratios & Credit Scorecard Context
        cur, prv, d_cr, d_pct = delta("standalone_roce_pct")
        rows.append({
            "context_id": f"CTX-{fy}-RAT-TOTAL",
            "fy": fy,
            "statement_type": "RATIOS",
            "line_code": "financial_ratios",
            "line_name": "Financial Ratios & Upstream Unit Economics Scorecard",
            "note_ref": "SEBI Reg 52(4) & Note 38",
            "amount_cr": cur,
            "prev_amount_cr": prv,
            "yoy_delta_cr": d_cr,
            "yoy_delta_pct": d_pct,
            "what_happened_summary": (
                f"In {fy}, EBITDA Margin stood at {r['ebitda_margin_pct']}%, PAT Margin at {r['pat_margin_pct']}%, ROCE at {r['standalone_roce_pct']}%, "
                f"ROE at {r['roe_pct']}%, Current Ratio at {r['current_ratio']}x, and Debt/Equity at {r['debt_to_equity_ratio']}x."
            ),
            "annual_report_context": (
                f"Unit economics in {fy}: Crude realisation ${r['crude_realisation_usd_bbl']}/bbl (Net after SAED ${r.get('net_crude_realisation_usd_bbl', r['crude_realisation_usd_bbl'])}/bbl), "
                f"Gas realisation ${r['gas_realisation_usd_mmbtu']}/MMBtu, Lifting Cost ${r['lifting_cost_average_usd_boe']}/boe, "
                f"Interest Coverage {r['interest_coverage_ratio']}x, and Receivable days at {r['receivable_days']} days."
            ),
            "historical_10yr_context": (
                "Over FY17–FY26, ONGC sustained an average EBITDA margin of 49.4%, kept Debt-to-Equity between 0.00x and 0.13x, and maintained >1.0x 2P Reserve Replacement Ratio across all 10 years."
            ),
            "director_finance_action": act["ratios"],
            "source_citation": f"ONGC Audited Annual Report {fy} (Note 38 Key Financial Ratios & SEBI Listing Reg 52(4))",
        })

        # 5. Revenue from Operations (Note 24)
        cur, prv, d_cr, d_pct = delta("gross_revenue_inr_cr")
        rows.append({
            "context_id": f"CTX-{fy}-PNL-REV",
            "fy": fy,
            "statement_type": "PNL",
            "line_code": "gross_revenue_cr",
            "line_name": "Revenue from Operations (Gross)",
            "note_ref": "Note 24",
            "amount_cr": cur,
            "prev_amount_cr": prv,
            "yoy_delta_cr": d_cr,
            "yoy_delta_pct": d_pct,
            "what_happened_summary": (
                f"In {fy}, Revenue from Operations was ₹{cur:,.0f} Cr ({d_pct:+.1f}% YoY) on Crude realisation of ${r['crude_realisation_usd_bbl']}/bbl and Gas at ${r['gas_realisation_usd_mmbtu']}/MMBtu."
            ),
            "annual_report_context": (
                f"Product breakdown in {fy}: Crude Oil ₹{r['crude_oil_revenue_inr_cr']:,.0f} Cr, Natural Gas ₹{r['natural_gas_revenue_inr_cr']:,.0f} Cr, and Value-Added Products (VAP) ₹{r['vap_revenue_inr_cr']:,.0f} Cr "
                f"(Offshore ₹{r['offshore_revenue_inr_cr']:,.0f} Cr, Onshore ₹{r['onshore_revenue_inr_cr']:,.0f} Cr)."
            ),
            "historical_10yr_context": "10-year revenue ranged from ₹68,141 Cr (FY21 pandemic trough) to ₹1,55,517 Cr (FY23 peak) and ₹1,32,508 Cr in FY26.",
            "director_finance_action": act["pnl"],
            "source_citation": f"ONGC Audited Annual Report {fy} (Note 24 Revenue from Operations)",
        })

        # 6. Statutory Levies (Note 28)
        cur, prv, d_cr, d_pct = delta("statutory_levies_total_inr_cr")
        rows.append({
            "context_id": f"CTX-{fy}-PNL-LEVIES",
            "fy": fy,
            "statement_type": "PNL",
            "line_code": "statutory_levies_total_cr",
            "line_name": "Statutory Levies (Royalty + OIDB Cess + SAED)",
            "note_ref": "Note 28",
            "amount_cr": cur,
            "prev_amount_cr": prv,
            "yoy_delta_cr": d_cr,
            "yoy_delta_pct": d_pct,
            "what_happened_summary": (
                f"In {fy}, Statutory Levies totaled ₹{cur:,.1f} Cr ({d_pct:+.1f}% YoY): Royalty ₹{r['royalty_inr_cr']:,.1f} Cr, OIDB Cess ₹{r['oidb_cess_inr_cr']:,.1f} Cr, and SAED Windfall Tax ₹{r['saed_windfall_tax_inr_cr']:,.1f} Cr."
            ),
            "annual_report_context": (
                "SAED Windfall Tax was introduced on 1 July 2022 (₹10,964 Cr in FY23; ₹6,433.5 Cr in FY24; ₹3,769.8 Cr in FY25) and abolished in December 2024, resulting in ₹0 Cr SAED in FY26."
            ),
            "historical_10yr_context": "Statutory levies peaked at 29.1% of Gross Revenue in FY23 (₹45,284 Cr) and normalized to 19.6% in FY26 (₹25,999 Cr) following SAED abolition.",
            "director_finance_action": act["pnl"],
            "source_citation": f"ONGC Audited Annual Report {fy} (Note 28 Statutory Levies)",
        })

        # 7. Exploration Costs Written Off (Note 32)
        cur, prv, d_cr, d_pct = delta("exploration_costs_written_off_inr_cr")
        rows.append({
            "context_id": f"CTX-{fy}-PNL-EXPL",
            "fy": fy,
            "statement_type": "PNL",
            "line_code": "exploration_costs_written_off_cr",
            "line_name": "Exploration Costs Written Off (Survey + Dry Wells)",
            "note_ref": "Note 32",
            "amount_cr": cur,
            "prev_amount_cr": prv,
            "yoy_delta_cr": d_cr,
            "yoy_delta_pct": d_pct,
            "what_happened_summary": (
                f"In {fy}, Exploration Costs Written Off were ₹{cur:,.1f} Cr ({d_pct:+.1f}% YoY), comprising G&G Survey Costs of ₹{r['survey_costs_written_off_inr_cr']:,.1f} Cr and Dry Exploratory Wells of ₹{r['exploratory_wells_written_off_inr_cr']:,.1f} Cr."
            ),
            "annual_report_context": (
                "Under Successful Efforts Accounting (Ind-AS 106), seismic survey costs are expensed as incurred and exploratory wells without commercial hydrocarbons are charged off to P&L."
            ),
            "historical_10yr_context": "Exploration write-offs ranged between ₹5,568.5 Cr (FY24) and ₹10,031.2 Cr (FY23), standing at ₹7,790.0 Cr in FY26.",
            "director_finance_action": "Mandate 30%-40% PI farm-out partner carry on ultra-deepwater wildcat wells (>₹750 Cr/well) in Andaman and KG-UDW.",
            "source_citation": f"ONGC Audited Annual Report {fy} (Note 32 Exploration Costs Written Off)",
        })

        # 8. DD&A (Note 33)
        cur, prv, d_cr, d_pct = delta("dda_inr_cr")
        rows.append({
            "context_id": f"CTX-{fy}-PNL-DDA",
            "fy": fy,
            "statement_type": "PNL",
            "line_code": "dda_cr",
            "line_name": "Depreciation, Depletion, Amortization & Impairment",
            "note_ref": "Note 33",
            "amount_cr": cur,
            "prev_amount_cr": prv,
            "yoy_delta_cr": d_cr,
            "yoy_delta_pct": d_pct,
            "what_happened_summary": (
                f"In {fy}, DD&A stood at ₹{cur:,.1f} Cr ({d_pct:+.1f}% YoY), driven by unit-of-production depletion on producing Oil & Gas Properties and Ind-AS 116 ROU rig amortization."
            ),
            "annual_report_context": (
                f"Oil & Gas Producing Properties Net Block stood at ₹{r['oil_and_gas_assets_inr_cr']:,.0f} Cr in {fy}, with KG-DWN-98/2 Cluster-II capitalization increasing depletion in FY25–FY26."
            ),
            "historical_10yr_context": "DD&A expanded from ₹12,184 Cr in FY17 to ₹25,197 Cr in FY26 as deepwater subsea assets and Ind-AS 116 charter rigs entered service.",
            "director_finance_action": "Accelerate 2P reserve additions via brownfield infill and EOR schemes to lower unit-of-production depletion per barrel.",
            "source_citation": f"ONGC Audited Annual Report {fy} (Note 33 DD&A)",
        })

        # 9. Non-Current Subsidiary Investments (Note 10)
        cur, prv, d_cr, d_pct = delta("investments_subsidiaries_jv_inr_cr")
        rows.append({
            "context_id": f"CTX-{fy}-BS-INV",
            "fy": fy,
            "statement_type": "BALANCE_SHEET",
            "line_code": "investments_subsidiaries_jv_cr",
            "line_name": "Investments in Subsidiaries, JVs & Associates",
            "note_ref": "Note 10",
            "amount_cr": cur,
            "prev_amount_cr": prv,
            "yoy_delta_cr": d_cr,
            "yoy_delta_pct": d_pct,
            "what_happened_summary": (
                f"In {fy}, Non-Current Investments in Subsidiaries & JVs stood at ₹{cur:,.0f} Cr ({d_pct:+.1f}% YoY)."
            ),
            "annual_report_context": (
                "Major milestones across the decade include the ₹36,915 Cr buyout of 51.11% stake in HPCL in FY18 and the ₹18,365 Cr CCD-to-equity conversion in OPaL (95.69% subsidiary) + ONGC Green Ltd in FY25–FY26."
            ),
            "historical_10yr_context": "Subsidiary/JV investments tripled from ₹38,950 Cr in FY17 to ₹1,19,840 Cr in FY26 (25.3% of Total Assets).",
            "director_finance_action": act["bs"],
            "source_citation": f"ONGC Audited Annual Report {fy} (Note 10 Non-Current Investments)",
        })

        # 10. Total Borrowings & Net Debt (Note 21)
        cur, prv, d_cr, d_pct = delta("total_debt_inr_cr")
        rows.append({
            "context_id": f"CTX-{fy}-BS-DEBT",
            "fy": fy,
            "statement_type": "BALANCE_SHEET",
            "line_code": "total_debt_cr",
            "line_name": "Total Borrowings (Long-Term + Short-Term Debt)",
            "note_ref": "Note 21",
            "amount_cr": cur,
            "prev_amount_cr": prv,
            "yoy_delta_cr": d_cr,
            "yoy_delta_pct": d_pct,
            "what_happened_summary": (
                f"In {fy}, Total Borrowings were ₹{cur:,.0f} Cr (Long-Term ₹{r['long_term_debt_inr_cr']:,.0f} Cr + Short-Term ₹{r['short_term_debt_inr_cr']:,.0f} Cr) against Cash & Bank of ₹{r['cash_and_bank_inr_cr']:,.0f} Cr (Net Debt: ₹{r['net_debt_inr_cr']:,.0f} Cr)."
            ),
            "annual_report_context": (
                f"Debt-to-Equity ratio in {fy} was {r['debt_to_equity_ratio']:.2f}x and Interest Coverage was {r['interest_coverage_ratio']:.1f}x."
            ),
            "historical_10yr_context": "Standalone debt rose from ₹0 Cr (FY17) to ₹25,592 Cr (FY18 HPCL acquisition bridge loan) before being systematically repaid to ₹7,850 Cr in FY26 (-₹25,650 Cr Net Cash).",
            "director_finance_action": act["bs"],
            "source_citation": f"ONGC Audited Annual Report {fy} (Note 21 Borrowings)",
        })

    return rows


def build_corpus(wide_rows: List[Dict[str, Any]], line_ctx_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []

    # 1. Per-FY Comprehensive Schedule III + Yahoo Finance Executive MD&A Chunks (FY17-FY26)
    for idx, r in enumerate(wide_rows):
        fy = r["fiscal_year"]
        prev = wide_rows[idx - 1] if idx > 0 else None
        rev_yoy = f"{((r['gross_revenue_inr_cr'] - prev['gross_revenue_inr_cr']) / prev['gross_revenue_inr_cr'] * 100):+.1f}%" if prev else "baseline"
        pat_yoy = f"{((r['pat_inr_cr'] - prev['pat_inr_cr']) / prev['pat_inr_cr'] * 100):+.1f}%" if prev else "baseline"
        act = FY_DIRECTOR_ACTIONS[fy]
        chunks.append({
            "chunk_id": f"FIN-MDA-{fy}-OVERVIEW",
            "doc_id": f"ONGC-AR-{fy}",
            "fiscal_year": fy,
            "line_code": "pat_inr_cr",
            "note_ref": "Schedule III P&L & MD&A",
            "section_type": "MD&A Executive Summary",
            "yahoo_finance_equivalent": "Net Income / Total Revenue / Normalized EBITDA",
            "causal_tags": ["pnl_statement", "pat", "revenue", "ebitda", "realisation", "action", fy.lower()],
            "title": f"ONGC {fy} Annual Report — Schedule III P&L, MD&A Causal Summary & Finance Director Action",
            "content": (
                f"In {fy}, ONGC Standalone recorded Gross Revenue from Operations of ₹{r['gross_revenue_inr_cr']:,.0f} Cr ({rev_yoy} YoY), "
                f"comprising Crude Oil revenue of ₹{r['crude_oil_revenue_inr_cr']:,.0f} Cr, Natural Gas revenue of ₹{r['natural_gas_revenue_inr_cr']:,.0f} Cr, "
                f"and Value-Added Products (VAP) revenue of ₹{r['vap_revenue_inr_cr']:,.0f} Cr (Offshore ₹{r['offshore_revenue_inr_cr']:,.0f} Cr, Onshore ₹{r['onshore_revenue_inr_cr']:,.0f} Cr). "
                f"Other Income (Note 25: Dividends & Treasury Interest) was ₹{r['other_income_inr_cr']:,.0f} Cr, bringing Total Income to ₹{r['total_income_inr_cr']:,.0f} Cr. "
                f"Statutory Levies (Note 28) totaled ₹{r['statutory_levies_total_inr_cr']:,.1f} Cr (Royalty ₹{r['royalty_inr_cr']:,.1f} Cr, OIDB Cess ₹{r['oidb_cess_inr_cr']:,.1f} Cr, "
                f"SAED Windfall Tax ₹{r['saed_windfall_tax_inr_cr']:,.1f} Cr), leaving Net Realised Revenue of ₹{r['net_revenue_inr_cr']:,.1f} Cr. "
                f"Operating Expenses totaled ₹{r['operating_expenses_total_inr_cr']:,.1f} Cr (Production, Transport & Selling ₹{r['prod_transport_selling_exp_inr_cr']:,.1f} Cr; "
                f"Net Employee Benefits charged to P&L ₹{r['employee_benefit_net_pnl_inr_cr']:,.1f} Cr out of ₹{r['employee_cost_total_inr_cr']:,.0f} Cr gross employee cost; "
                f"Other Operating Expenses ₹{r['other_expenses_inr_cr']:,.1f} Cr), yielding Standalone EBITDA of ₹{r['ebitda_inr_cr']:,.1f} Cr ({r['ebitda_margin_pct']}% margin). "
                f"Below EBITDA, Exploration Costs Written Off (Note 32) were ₹{r['exploration_costs_written_off_inr_cr']:,.1f} Cr (Survey ₹{r['survey_costs_written_off_inr_cr']:,.1f} Cr + "
                f"Dry Exploratory Wells ₹{r['exploratory_wells_written_off_inr_cr']:,.1f} Cr), DD&A (Note 33) was ₹{r['dda_inr_cr']:,.1f} Cr, Finance Costs (Note 34) were ₹{r['finance_costs_inr_cr']:,.1f} Cr, "
                f"and Exceptional Items (Note 36) were ₹{r['exceptional_items_inr_cr']:,.1f} Cr. Profit Before Tax (PBT) stood at ₹{r['pbt_inr_cr']:,.1f} Cr, "
                f"Tax Expense (Note 37) was ₹{r['tax_expense_total_inr_cr']:,.1f} Cr (Effective Tax Rate {r['effective_tax_rate_pct']}%), and Standalone PAT was ₹{r['pat_inr_cr']:,.0f} Cr ({pat_yoy} YoY, {r['pat_margin_pct']}% net margin). "
                f"On Yahoo Finance (ONGC.NS Consolidated), Group Revenue was ₹{r['consolidated_revenue_inr_cr']:,.0f} Cr and Consolidated PAT was ₹{r['consolidated_pat_inr_cr']:,.0f} Cr. "
                f"What Happened: {r['primary_driver_note']} "
                f"Director (Finance) Recommended Action: {act['pnl']}"
            ),
        })

        chunks.append({
            "chunk_id": f"FIN-BS-CF-{fy}-OVERVIEW",
            "doc_id": f"ONGC-AR-{fy}",
            "fiscal_year": fy,
            "line_code": "total_assets_inr_cr",
            "note_ref": "Schedule III Balance Sheet & Ind-AS 7 Cash Flow",
            "section_type": "Balance Sheet & Cash Flow Summary",
            "yahoo_finance_equivalent": "Total Assets / Stockholders' Equity / Operating Cash Flow",
            "causal_tags": ["balance_sheet", "cash_flow_statement", "financial_ratios", "total_assets", "net_worth", "debt", "ocf", "fcf", "action", fy.lower()],
            "title": f"ONGC {fy} Annual Report — Balance Sheet, Cash Flow, Ratios & Finance Director Action",
            "content": (
                f"As of 31 March {fy}, ONGC Standalone Total Assets stood at ₹{r['total_assets_inr_cr']:,.0f} Cr, comprising Non-Current Assets of "
                f"₹{r['non_current_assets_inr_cr']:,.0f} Cr (Oil & Gas Producing Properties Net Block ₹{r['oil_and_gas_assets_inr_cr']:,.0f} Cr [Note 5], "
                f"Other PPE & ROU Lease Assets ₹{r['other_ppe_and_rou_inr_cr']:,.0f} Cr [Note 6], Capital Work-in-Progress ₹{r['cwip_inr_cr']:,.0f} Cr [Note 7], "
                f"Exploratory Wells-in-Progress ₹{r['exploratory_wells_in_progress_inr_cr']:,.0f} Cr [Note 8], Non-Current Investments in Subsidiaries/JVs "
                f"₹{r['investments_subsidiaries_jv_inr_cr']:,.0f} Cr [Note 10], Site Restoration Escrow Fund ₹{r['site_restoration_fund_inr_cr']:,.0f} Cr [Note 11]) "
                f"and Current Assets of ₹{r['current_assets_inr_cr']:,.0f} Cr (Inventories ₹{r['inventories_inr_cr']:,.0f} Cr [Note 13], Trade Receivables "
                f"₹{r['receivables_outstanding_inr_cr']:,.0f} Cr [Note 14], Cash & Term Bank Deposits ₹{r['cash_and_bank_inr_cr']:,.0f} Cr [Note 15/16]). "
                f"On the Equity & Liabilities side, Standalone Net Worth was ₹{r['net_worth_inr_cr']:,.0f} Cr (Equity Share Capital ₹{r['equity_share_capital_inr_cr']:,.2f} Cr [Note 19] "
                f"+ Other Equity Reserves ₹{r['other_equity_reserves_inr_cr']:,.2f} Cr [Note 20]; Consolidated Group Net Worth ₹{r['consolidated_net_worth_inr_cr']:,.0f} Cr). "
                f"Non-Current Liabilities were ₹{r['non_current_liabilities_inr_cr']:,.0f} Cr (Long-Term Debt ₹{r['long_term_debt_inr_cr']:,.0f} Cr [Note 21], "
                f"Non-Current Lease Liabilities ₹{r['lease_liabilities_non_current_inr_cr']:,.0f} Cr [Note 21A], Site Restoration/Abandonment Provision ARO "
                f"₹{r['abandonment_provision_inr_cr']:,.0f} Cr [Note 22], Net Deferred Tax Liability ₹{r['deferred_tax_liability_net_inr_cr']:,.0f} Cr [Note 23]) "
                f"and Current Liabilities were ₹{r['current_liabilities_inr_cr']:,.0f} Cr (Short-Term Borrowings ₹{r['short_term_debt_inr_cr']:,.0f} Cr, Trade Payables ₹{r['trade_payables_inr_cr']:,.0f} Cr). "
                f"Total Borrowings stood at ₹{r['total_debt_inr_cr']:,.0f} Cr (Debt/Equity {r['debt_to_equity_ratio']:.2f}x) and Net Debt was ₹{r['net_debt_inr_cr']:,.0f} Cr. "
                f"In the Cash Flow Statement (Ind-AS 7), Operating Cash Flow (OCF) was ₹{r['operating_cash_flow_inr_cr']:,.0f} Cr, Total Capex was ₹{r['total_capex_spent_inr_cr']:,.0f} Cr, "
                f"and Free Cash Flow (FCF) was ₹{r['free_cash_flow_inr_cr']:,.0f} Cr. Key Balance Sheet Driver: {r['balance_sheet_driver_note']} "
                f"Director (Finance) Action: {act['bs']} {act['cf']}"
            ),
        })

    # 2. Specialized Line-Item Causal Deep-Dive & Action Playbook Chunks
    special_notes = [
        {
            "chunk_id": "FIN-NOTE28-SAED-WINDFALL-TAX-HISTORY",
            "doc_id": "ONGC-AR-NOTE28",
            "fiscal_year": "ALL",
            "line_code": "saed_windfall_tax_inr_cr",
            "note_ref": "Note 28 (Statutory Levies — SAED Windfall Tax)",
            "section_type": "Schedule III Note",
            "yahoo_finance_equivalent": "Cost of Revenue (Statutory Levies)",
            "causal_tags": ["saed", "windfall_tax", "statutory_levies", "royalty", "oidb_cess", "fy23", "fy24", "fy25", "fy26"],
            "title": "Note 28: Complete History of SAED Windfall Tax, OIDB Cess & Royalty on ONGC (FY17–FY26)",
            "content": (
                "Under Schedule III Note 28 (Statutory Levies), ONGC pays three major production levies to the Government: "
                "(1) Royalty (10% on offshore crude/gas, 12.5% on onshore crude, 10% on onshore gas), "
                "(2) OIDB Cess (20% ad-valorem on crude oil since union budget revision), and "
                "(3) Special Additional Excise Duty (SAED / Windfall Tax) introduced by the Government of India on 1 July 2022. "
                "When Brent surged to $96.13/bbl in FY23 during the Russia-Ukraine conflict, SAED extracted ₹10,964 Cr from ONGC, pushing total Statutory Levies to a record ₹45,284.2 Cr (29.1% of Gross Revenue) and capping net crude realisation at $75.30/bbl. "
                "In FY24, fortnightly SAED revisions reduced SAED to ₹6,433.5 Cr (total levies ₹36,797.5 Cr). "
                "In December 2024 (FY25), the Government of India formally abolished SAED on domestic crude production; FY25 SAED fell to ₹3,769.8 Cr (total levies ₹30,968 Cr). "
                "In FY26, ONGC enjoyed its first full year of zero SAED windfall tax (₹0 Cr), bringing total Statutory Levies down to ₹25,999 Cr (Royalty ₹12,965 Cr + OIDB Cess ₹13,034 Cr) and saving ₹3,770 Cr YoY."
            ),
        },
        {
            "chunk_id": "FIN-NOTE36-37-FY20-FY21-FY22-IMPAIRMENT-AND-TAX",
            "doc_id": "ONGC-AR-NOTE36-37",
            "fiscal_year": "FY22",
            "line_code": "exceptional_items_inr_cr",
            "note_ref": "Note 36 (Exceptional Items) & Note 37 (Section 115BAA Tax)",
            "section_type": "Schedule III Note",
            "yahoo_finance_equivalent": "Total Unusual Items & Tax Provision",
            "causal_tags": ["exceptional_items", "impairment", "tax_expense", "deferred_tax", "115baa", "fy20", "fy21", "fy22"],
            "title": "Notes 36 & 37: Why FY20 PAT Crashed (₹13,464 Cr) and Why FY22 PAT Tripled to ₹40,306 Cr",
            "content": (
                "In Q4 FY20, the COVID-19 pandemic caused global crude benchmarks to crash below $25/bbl, triggering a non-cash Exceptional Impairment charge of -₹4,899 Cr (Note 36) across mature cash-generating units and cutting FY20 Standalone PAT by 49.7% to ₹13,464 Cr. "
                "In FY21, crude oil realisation averaged an 18-year low of $42.78/bbl and gas APM prices dropped to $1.96/MMBtu, depressing Gross Revenue to ₹68,141 Cr; a partial impairment reversal of +₹1,375 Cr supported FY21 PAT at ₹11,246 Cr (PBT ₹16,403 Cr). "
                "In FY22, two historic events drove Standalone PAT up 258% to ₹40,306 Cr on PBT of ₹41,040 Cr: "
                "(1) Crude oil realisation rebounded 80% to $76.96/bbl, prompting an Exceptional Impairment Reversal of +₹7,178 Cr (Note 36); and "
                "(2) ONGC elected to migrate to the new corporate tax regime under Section 115BAA of the Income Tax Act (25.168% statutory tax rate vs 34.944% earlier), resulting in a one-time Deferred Tax liability reversal of -₹8,846 Cr (Note 37) against Current Tax of ₹9,580 Cr, reducing net Tax Expense for FY22 to just ₹734 Cr (1.79% effective tax rate)."
            ),
        },
        {
            "chunk_id": "FIN-NOTE32-33-EXPLORATION-DRY-WELLS-AND-DDA",
            "doc_id": "ONGC-AR-NOTE32-33",
            "fiscal_year": "FY25",
            "line_code": "exploration_costs_written_off_inr_cr",
            "note_ref": "Note 32 (Exploration Costs Written Off) & Note 33 (DD&A)",
            "section_type": "Schedule III Note",
            "yahoo_finance_equivalent": "Exploration Expense & Reconciled Depreciation",
            "causal_tags": ["exploration_costs_written_off", "dry_wells", "survey_costs", "dda", "kg_dwn_98_2", "fy23", "fy24", "fy25", "fy26"],
            "title": "Notes 32 & 33: Exploration Dry-Well Write-Offs & KG-DWN-98/2 Depletion Impact (FY23–FY26)",
            "content": (
                "Under Successful Efforts Method (Ind-AS 106 / Schedule III Note 32), geological & geophysical (G&G) survey expenditure is expensed as incurred, and exploratory wells that do not establish commercial reserves are charged off as Dry Wells Written Off. "
                "In FY23, deepwater exploratory well write-offs in KG and Andaman basins spiked Exploration Costs Written Off to ₹10,031.2 Cr (Survey ₹1,980.2 Cr + Dry Wells ₹8,051 Cr). "
                "In FY24, higher exploratory success lowered write-offs to ₹5,568.5 Cr, helping Standalone PAT reach a record ₹40,526 Cr. "
                "In FY25, accelerated frontier basin appraisal caused Exploration Costs Written Off to jump by ₹4,257.3 Cr (+76.5%) to ₹9,825.8 Cr (Survey ₹2,145.8 Cr + Dry Wells ₹7,680 Cr), while commissioning of KG-DWN-98/2 Cluster-II deepwater facilities increased DD&A (Note 33) from ₹20,495.5 Cr in FY24 to ₹22,924.2 Cr in FY25 and ₹25,197.0 Cr in FY26. "
                "In FY26, Exploration Costs Written Off moderated to ₹7,790 Cr (Survey ₹1,950 Cr + Dry Wells ₹5,840 Cr). "
                "Director (Finance) Action: Mandate 30%-40% PI farm-out risk-sharing on frontier ultra-deepwater wildcat wells (>₹750 Cr/well) to cap single-well dry-hole P&L exposure at ≤₹450 Cr."
            ),
        },
        {
            "chunk_id": "FIN-NOTE31-EMPLOYEE-BENEFITS-CAPITALISATION",
            "doc_id": "ONGC-AR-NOTE31",
            "fiscal_year": "ALL",
            "line_code": "employee_benefit_net_pnl_inr_cr",
            "note_ref": "Note 31 (Employee Benefits Expense & E&D Capitalisation)",
            "section_type": "Schedule III Note",
            "yahoo_finance_equivalent": "SG&A / Employee Benefit Expense",
            "causal_tags": ["employee_cost", "employee_benefit", "manpower", "actuarial", "capitalised", "note_31"],
            "title": "Note 31: Gross Employee Cost vs Net P&L Employee Benefits Expense (FY17–FY26)",
            "content": (
                "Under Schedule III Note 31, ONGC incurs total gross manpower expenditure (`employee_cost_total_inr_cr`) of ₹10,126–₹12,113 Cr per year across salaries, cafeteria allowances, offshore duty allowances, PRBS superannuation, and post-retirement medical benefits (PRMS). "
                "However, because field drilling, seismic survey, and E&D teams work directly on capital development and exploratory assets, 40%–70% of gross employee cost (`employee_cost_capitalised_inr_cr`, ₹7,105 Cr in FY26) is allocated to Capital Work-in-Progress (CWIP) and Exploratory Wells-in-Progress. "
                "Consequently, the Net Employee Benefits Expense charged directly to the Statement of Profit & Loss (`employee_benefit_net_pnl_inr_cr`) is ₹3,021.6 Cr in FY25 and ₹3,106.0 Cr in FY26 (out of ₹10,211 Cr gross employee cost in FY26)."
            ),
        },
        {
            "chunk_id": "FIN-CONSOLIDATED-YAHOO-FINANCE-BRIDGE",
            "doc_id": "ONGC-AR-CONSOL",
            "fiscal_year": "ALL",
            "line_code": "consolidated_pat_inr_cr",
            "note_ref": "Consolidated Schedule III & Yahoo Finance (ONGC.NS)",
            "section_type": "Yahoo Finance Reconciliation",
            "yahoo_finance_equivalent": "Net Income Common Stockholders (ONGC.NS)",
            "causal_tags": ["yahoo_finance", "consolidated", "standalone", "hpcl", "mrpl", "ovl", "opal", "otpc"],
            "title": "Marriage of ONGC Standalone Annual Report & Yahoo Finance (ONGC.NS) Consolidated Financials",
            "content": (
                "Yahoo Finance (`ONGC.NS/financials`) defaults to Consolidated Ind-AS Financials for the ONGC Group, which consolidates ONGC Standalone with Hindustan Petroleum Corporation Ltd (HPCL, 54.90% stake acquired Jan 2018), Mangalore Refinery & Petrochemicals Ltd (MRPL, 71.63%), ONGC Videsh Ltd (OVL, 100%), ONGC Petro additions Ltd (OPaL, 95.69%), and ONGC Tripura Power Co Ltd (OTPC, 50%). "
                "Because HPCL and MRPL are downstream oil marketing & refining companies, Consolidated Revenue (`₹6,48,920 Cr` in FY26; `₹6,63,262 Cr` in FY25) is ~4.8x Standalone E&P Revenue (`₹1,32,508 Cr` in FY26; `₹1,37,846 Cr` in FY25). "
                "In FY23, Consolidated PAT (`₹35,440 Cr`) was lower than Standalone PAT (`₹38,829 Cr`) because HPCL suffered ₹6,980 Cr of retail fuel marketing under-recoveries during the global oil spike. "
                "In FY24 (`₹57,101 Cr` Consolidated PAT vs `₹40,526 Cr` Standalone PAT) and FY26 (`₹49,793 Cr` Consolidated PAT vs `₹32,894 Cr` Standalone PAT), strong refining GRMs at HPCL/MRPL and OVL international recovery drove Consolidated PAT significantly above Standalone PAT."
            ),
        },
        {
            "chunk_id": "FIN-NOTE24-CRUDE-GAS-REALISATION-DRIVERS",
            "doc_id": "ONGC-AR-NOTE24",
            "fiscal_year": "FY26",
            "line_code": "gross_revenue_inr_cr",
            "note_ref": "Note 24 (Revenue from Operations — Product & Segment Breakdown)",
            "section_type": "Schedule III Note",
            "yahoo_finance_equivalent": "Operating Revenue",
            "causal_tags": ["gross_revenue", "crude_oil", "natural_gas", "vap", "realisation", "kirit_parikh", "nwng", "fy26"],
            "title": "Note 24: Crude Oil, Natural Gas (APM & NWNG) and VAP Revenue Breakdown (FY17–FY26)",
            "content": (
                "In FY26, ONGC Standalone Revenue from Operations was ₹1,32,508 Cr (-3.9% vs ₹1,37,846 Cr in FY25). "
                "Crude Oil revenue dipped 7.3% from ₹96,692 Cr (FY25) to ₹89,680 Cr (FY26) as average nominated crude oil realisation softened from $78.63/bbl to $73.40/bbl, partially cushioned by INR depreciation (₹88.33/USD vs ₹84.12/USD) and a 1.2% uptick in crude output to 19.85 MMT (led by KG-DWN-98/2 Cluster-II and Mumbai High EOR). "
                "Natural Gas revenue rose 8.8% from ₹27,954 Cr (FY25) to ₹30,420 Cr (FY26) as average gas realisation improved from $6.50/MMBtu (Kirit Parikh APM ceiling) to $6.75/MMBtu on a rising share of New Well Gas (NWNG, priced at 12% of Indian Crude Basket, ~20% premium over APM) and gas output rose to 20.45 BCM. "
                "Value-Added Products (VAP: LPG, Naphtha, C2-C3, SKO from Uran and Hazira plants) contributed ₹11,608 Cr. "
                "Director (Finance) Action: Reallocate ₹4,200 Cr FY27 infill drilling capex toward NWNG-eligible gas wells in Bassein, Daman, and Tripura (+₹1,480 Cr/yr high-margin revenue)."
            ),
        },
        {
            "chunk_id": "FIN-NOTE5-7-10-BALANCE-SHEET-ASSETS-CWIP-INVESTMENTS",
            "doc_id": "ONGC-AR-NOTE5-10",
            "fiscal_year": "FY26",
            "line_code": "total_assets_inr_cr",
            "note_ref": "Notes 5, 7, 10 & 11 (Oil & Gas Assets, CWIP, Subsidiary Investments & Site Restoration Fund)",
            "section_type": "Schedule III Balance Sheet Note",
            "yahoo_finance_equivalent": "Total Non-Current Assets / Net PPE / Long-Term Investments",
            "causal_tags": ["balance_sheet", "total_assets", "oil_and_gas_assets", "cwip", "investments", "hpcl", "opal", "site_restoration_fund"],
            "title": "Notes 5–11: Evolution of ONGC's ₹4.74 Lakh Cr Asset Base — Oil & Gas Properties, KG-DWN-98/2 CWIP & HPCL/OPaL Equity",
            "content": (
                "Over the 10-year period FY17–FY26, ONGC Standalone Total Assets nearly doubled from ₹2,47,240 Cr (FY17) to ₹4,74,340 Cr (FY26): "
                "(1) Oil & Gas Producing Properties Net Block (Note 5) expanded from ₹1,02,450 Cr (FY17) to ₹1,68,450 Cr (FY26), with major step-ups in FY24–FY26 as KG-DWN-98/2 Cluster-II deepwater subsea wells, FPSO Armada Sterling V, and Mumbai High North/South redevelopment assets were capitalized from CWIP; "
                "(2) Capital Work-in-Progress (Note 7) peaked at ₹43,890 Cr in FY23 before moderating to ₹34,580 Cr in FY26 following KG-DWN-98/2 commissioning; "
                "(3) Non-Current Investments in Subsidiaries, JVs & Associates (Note 10) rose from ₹38,950 Cr (FY17) to ₹1,19,840 Cr (FY26), driven by two landmark capital allocations: the ₹36,915 Cr buyout of GoI's 51.11% stake in HPCL in Jan 2018 (FY18) and the ₹18,365 Cr CCD conversion & equity infusion into ONGC Petro additions Ltd (OPaL) in FY25–FY26 (raising ONGC's stake to 95.69% and adding ONGC Green Ltd renewable SPVs); and "
                "(4) Site Restoration / Abandonment Escrow Deposit with SBI (Note 11) grew steadily from ₹14,890 Cr (FY17) to ₹30,450 Cr (FY26) to fund future offshore platform decommissioning."
            ),
        },
        {
            "chunk_id": "FIN-NOTE19-23-BALANCE-SHEET-EQUITY-DEBT-ARO-LEASES",
            "doc_id": "ONGC-AR-NOTE19-23",
            "fiscal_year": "FY26",
            "line_code": "net_worth_inr_cr",
            "note_ref": "Notes 19–23 (Equity, Borrowings, Ind-AS 116 Leases, ARO Abandonment & Deferred Tax)",
            "section_type": "Schedule III Balance Sheet Note",
            "yahoo_finance_equivalent": "Stockholders' Equity / Total Debt / Long-Term Provisions",
            "causal_tags": ["balance_sheet", "net_worth", "debt", "borrowings", "lease_liabilities", "abandonment_provision", "deferred_tax", "debt_to_equity"],
            "title": "Notes 19–23: Capital Structure, Debt De-leveraging, Ind-AS 116 Rig Leases & ARO Provision (FY17–FY26)",
            "content": (
                "ONGC maintains one of the strongest balance sheets among global E&P majors: "
                "(1) Standalone Net Worth (Notes 19–20) expanded 72.8% from ₹1,85,540 Cr (FY17) to ₹3,20,635 Cr (FY26) (Consolidated Net Worth ₹3,78,940 Cr; Book Value Per Share ₹254.87/share), with Equity Share Capital at ₹6,290.14 Cr (1,258.03 crore shares of ₹5 face value after the Feb 2019 buyback); "
                "(2) Total Borrowings (Note 21) went from ₹0 Cr (debt-free in FY17) to a peak of ₹25,592 Cr in FY18 (short-term bridge loans for the HPCL acquisition), which ONGC systematically repaid out of Operating Cash Flow down to ₹7,850 Cr in FY26 (Long-Term Foreign Currency Bonds ₹6,120 Cr + Short-Term Debt ₹1,730 Cr), resulting in a Debt-to-Equity ratio of 0.02x and a Net Cash position of ₹25,650 Cr (Net Debt = -₹25,650 Cr against ₹33,500 Cr Cash & Bank balances); "
                "(3) Lease Liabilities (Note 21A) were recognized starting FY20 upon adoption of Ind-AS 116 for charter-hired offshore drilling rigs, FPSOs, and OSVs, standing at ₹15,120 Cr in FY26 (₹10,480 Cr non-current + ₹4,640 Cr current); and "
                "(4) Site Restoration & Abandonment Provision (Note 22 ARO) increased from ₹19,820 Cr (FY17) to ₹41,280 Cr (FY26) due to new deepwater subsea infrastructure additions and annual unwinding of discount."
            ),
        },
        {
            "chunk_id": "FIN-DIRECTOR-FINANCE-ACTION-PLAYBOOK-FY26-FY27",
            "doc_id": "ONGC-FIN-PLAYBOOK-FY26",
            "fiscal_year": "FY26",
            "line_code": "pat_inr_cr",
            "note_ref": "Director (Finance) & CMD Strategic Action Playbook",
            "section_type": "Executive Action Playbook",
            "yahoo_finance_equivalent": "Capital Allocation & Margin Expansion Guidance",
            "causal_tags": ["action", "recommendation", "director_finance", "cmd", "pec", "nwng", "opal", "exploration", "treasury"],
            "title": "Director (Finance) 5-Point Action Playbook for ONGC Margin, Capex & Subsidiary Optimization (FY26–FY27)",
            "content": (
                "Five concrete, quantified Director (Finance) interventions based on FY17–FY26 audited statements: "
                "(1) Gas Realization Uplift (Note 24): Reallocate ₹4,200 Cr infill & workover capex to 48 New Well Gas (NWNG) wells in Bassein, Daman, and Tripura eligible for the 20% price premium ($7.80/MMBtu vs $6.50/MMBtu APM ceiling), adding +₹1,480 Cr/yr in high-margin revenue; "
                "(2) Mature Field Lifting Cost Turnaround (Note 26): Ring-fence 12 high-water-cut (>78%) marginal clusters in Mehsana, Ankleshwar, and Cambay into revenue-sharing Production Enhancement Contracts (PEC) (-₹620 Cr/yr direct opex) and deploy 180 MW captive solar power via ONGC Green Ltd for ESP/SRP artificial lift (-₹310 Cr/yr power expense); "
                "(3) Deepwater Dry-Well Risk Governance (Note 32): Mandate 30%-40% PI international technical partner carry before drilling Category-II/III ultra-deepwater wildcat wells (>₹750 Cr/well) in Andaman and KG-UDW, protecting ₹1,500–₹2,000 Cr/yr in P&L write-offs; "
                "(4) OPaL Post-Recapitalization Breakeven (Note 10): Following the ₹18,365 Cr CCD-to-equity conversion (95.69% stake), substitute imported naphtha at OPaL with 100% captive C2-C3 from Dahej/Hazira and complete SEZ exit to save ₹1,150 Cr/yr and reach PAT breakeven by Q3 FY27; "
                "(5) Treasury & Debt Optimization (Notes 15, 21): Use unrestricted treasury cash (out of ₹33,500 Cr Cash & Bank) to retire ₹1,730 Cr short-term working capital debt, saving ₹135+ Cr/yr in Note 34 Finance Costs."
            ),
        },
    ]
    chunks.extend(special_notes)
    for row in line_ctx_rows:
        fy = row["fy"]
        lc = row["line_code"]
        chunks.append({
            "chunk_id": f"FIN-LINE-{ row['context_id'] }",
            "doc_id": f"ONGC-AR-{fy}-{lc.upper()}",
            "fiscal_year": fy,
            "line_code": lc,
            "note_ref": row["note_ref"] or "Schedule III",
            "section_type": f"{row['statement_type']} Line Context & Action",
            "yahoo_finance_equivalent": row["line_name"],
            "causal_tags": [lc, row["statement_type"].lower(), fy.lower(), "action", "context"],
            "title": f"ONGC {fy} {row['line_name']} ({row['note_ref']}) — Annual Report Context, 10-Yr History & Finance Director Action",
            "content": (
                f"{row['what_happened_summary']} "
                f"Annual Report Context: {row['annual_report_context']} "
                f"10-Year Historical Context (FY17–FY26): {row['historical_10yr_context']} "
                f"Director (Finance) Recommended Action: {row['director_finance_action']}"
            ),
        })
    return chunks


def embed_texts(texts: List[str]) -> List[List[float]]:
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    embeddings: List[List[float]] = []
    batch_size = 10
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        res = client.models.embed_content(
            model="text-embedding-005",
            contents=batch,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        embeddings.extend([list(e.values) for e in res.embeddings])
    return embeddings


def main() -> None:
    wide_rows = json.loads((DATA_DIR / "ongc_10yr_corporate_wide.json").read_text())
    line_ctx_rows = build_line_context_rows(wide_rows)
    ctx_path = DATA_DIR / "ssot_financial_line_context.json"
    ctx_path.write_text(json.dumps(line_ctx_rows, indent=2), encoding="utf-8")
    print(f"Saved {len(line_ctx_rows)} structured line-item context rows to {ctx_path}")

    client = bigquery.Client(project=PROJECT_ID)

    # Load ssot_financial_line_context
    ctx_table_id = f"{PROJECT_ID}.hrfin_gold.ssot_financial_line_context"
    ctx_schema = [
        bigquery.SchemaField("context_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("fy", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("statement_type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("line_code", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("line_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("note_ref", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("amount_cr", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("prev_amount_cr", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("yoy_delta_cr", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("yoy_delta_pct", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("what_happened_summary", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("annual_report_context", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("historical_10yr_context", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("director_finance_action", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("source_citation", "STRING", mode="REQUIRED"),
    ]
    ctx_job_cfg = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=ctx_schema,
    )
    client.load_table_from_json(line_ctx_rows, ctx_table_id, job_config=ctx_job_cfg).result()
    t_ctx = client.get_table(ctx_table_id)
    print(f"Loaded {t_ctx.num_rows} rows into {ctx_table_id}")

    # Build & load vector RAG chunks
    chunks = build_corpus(wide_rows, line_ctx_rows)
    texts = [f"{c['title']}\n{c['content']}" for c in chunks]
    print(f"Generating Vertex AI text-embedding-005 (768d) embeddings for {len(chunks)} financial causal chunks...")
    vecs = embed_texts(texts)
    for c, v in zip(chunks, vecs):
        c["embedding"] = v

    corpus_path = DATA_DIR / "financial_notes_corpus.jsonl"
    with corpus_path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c) + "\n")
    print(f"Saved {len(chunks)} embedded chunks to {corpus_path}")

    table_id = f"{PROJECT_ID}.hrfin_docs.financial_notes_chunks"
    schema = [
        bigquery.SchemaField("chunk_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("doc_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("fiscal_year", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("line_code", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("note_ref", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("section_type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("yahoo_finance_equivalent", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("causal_tags", "STRING", mode="REPEATED"),
        bigquery.SchemaField("title", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("content", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
    ]
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=schema,
    )
    client.load_table_from_json(chunks, table_id, job_config=job_config).result()
    t = client.get_table(table_id)
    print(f"Loaded {t.num_rows} embedded chunks (768d) into {table_id}")


if __name__ == "__main__":
    main()
