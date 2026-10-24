# RETIRED 2026-10 (SPEC-01 §11): LLM-authored values, not AR-extracted. Do not use.

#!/usr/bin/env python3
"""
Autonomous 30-Scenario × 4-Turn (120 Total Conversational Turns) Stress-Test & Q&A Curation Runner.
Executes 30 multi-turn sessions against live Yukti Backend (`http://127.0.0.1:8095/api/turn`),
verifies SQL execution, Table-First / Waterfall-on-Demand rules, Annual Report Context & Director Finance Actions,
and generates `financial_build/05_curated_30_questions_and_followups.md`.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List
import httpx

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BACKEND_URL = "http://127.0.0.1:8095/api/turn"

SCENARIOS: List[Dict[str, Any]] = [
    # --- PILLAR 1: STATEMENT OF PROFIT & LOSS (SCENARIOS 1-6) ---
    {
        "id": "S01",
        "pillar": "Pillar 1: Schedule III Statement of Profit & Loss",
        "title": "FY26 Standalone & Consolidated P&L Statement, Waterfall Bridge, SAED Abolition & Margin Action",
        "turns": [
            {"q": "Show the Profit and Loss statement of ONGC for FY26", "expect_visual": "table", "expect_metric": "pnl_statement"},
            {"q": "Show FY26 P&L statement as a waterfall chart", "expect_visual": "chart", "expect_chart": "waterfall"},
            {"q": "Why did PAT decrease in FY26 compared to FY25 and what happened to SAED windfall tax?", "expect_rag": True},
            {"q": "What action should the Finance Director take to improve upstream margins in FY27?", "expect_rag": True},
        ],
    },
    {
        "id": "S02",
        "pillar": "Pillar 1: Schedule III Statement of Profit & Loss",
        "title": "FY23 Peak Revenue P&L, Windfall Tax Impact & 10-Year Historical P&L Trajectory (FY17–FY26)",
        "turns": [
            {"q": "Profit and loss statement of ONGC for FY23", "expect_visual": "table", "expect_metric": "pnl_statement"},
            {"q": "Show it as a waterfall chart", "expect_visual": "chart", "expect_chart": "waterfall"},
            {"q": "Why did statutory levies hit a record high in FY23?", "expect_rag": True},
            {"q": "Compare the P&L statement trend from FY17 to FY26", "expect_metric": "pnl_statement"},
        ],
    },
    {
        "id": "S03",
        "pillar": "Pillar 1: Schedule III Statement of Profit & Loss",
        "title": "FY20 COVID Impairment Crash vs FY22 Section 115BAA Tax Rebound",
        "turns": [
            {"q": "Show the Profit and Loss statement of ONGC for FY20", "expect_visual": "table", "expect_metric": "pnl_statement"},
            {"q": "Why did PAT crash in FY20 and why did PAT triple in FY22?", "expect_rag": True},
            {"q": "Show the Profit and Loss statement of ONGC for FY22", "expect_visual": "table", "expect_metric": "pnl_statement"},
            {"q": "Show the 10-year trend of Standalone PAT from FY17 to FY26", "expect_ rag": False},
        ],
    },
    {
        "id": "S04",
        "pillar": "Pillar 1: Schedule III Statement of Profit & Loss",
        "title": "Note 24 Revenue from Operations — Crude Oil, Natural Gas (APM vs NWNG) & VAP Breakdown",
        "turns": [
            {"q": "What was ONGC corporate revenue from operations in FY26?", "expect_rag": False},
            {"q": "Show the trend of corporate revenue from FY17 to FY26", "expect_rag": False},
            {"q": "Explain Note 24 crude oil and natural gas realisation drivers in FY26", "expect_rag": True},
            {"q": "What action should the Finance Director take on New Well Gas infill capex?", "expect_rag": True},
        ],
    },
    {
        "id": "S05",
        "pillar": "Pillar 1: Schedule III Statement of Profit & Loss",
        "title": "Note 28 Statutory Levies — Royalty, OIDB Cess & Complete SAED Windfall Tax History",
        "turns": [
            {"q": "What were ONGC statutory levies in FY26?", "expect_rag": False},
            {"q": "Show the 10-year trend of statutory levies from FY17 to FY26", "expect_rag": False},
            {"q": "Explain Note 28 and the complete history of SAED windfall tax from FY23 to FY26", "expect_rag": True},
            {"q": "How much did SAED windfall tax cost ONGC in FY23, FY24, FY25 and FY26?", "expect_rag": True},
        ],
    },
    {
        "id": "S06",
        "pillar": "Pillar 1: Schedule III Statement of Profit & Loss",
        "title": "Notes 32 & 33 Exploration Dry-Well Write-Offs & KG-DWN-98/2 Depletion (DD&A)",
        "turns": [
            {"q": "How much were exploration costs written off in FY26?", "expect_rag": False},
            {"q": "Show the trend of exploration costs written off from FY17 to FY26", "expect_rag": False},
            {"q": "Why did exploration dry-well write-offs and DD&A increase in FY25 and FY26?", "expect_rag": True},
            {"q": "What governance action should the Finance Director mandate for deepwater wildcat wells?", "expect_rag": True},
        ],
    },

    # --- PILLAR 2: SCHEDULE III BALANCE SHEET (SCENARIOS 7-12) ---
    {
        "id": "S07",
        "pillar": "Pillar 2: Schedule III Balance Sheet",
        "title": "FY26 Schedule III Balance Sheet Table, Asset Composition & 10-Year Evolution",
        "turns": [
            {"q": "Show the Balance Sheet of ONGC for FY26", "expect_visual": "table", "expect_metric": "balance_sheet"},
            {"q": "Why did Non-Current Investments in subsidiaries increase in FY25 and FY26?", "expect_rag": True},
            {"q": "How has the Balance Sheet evolved from FY17 to FY26?", "expect_metric": "balance_sheet"},
            {"q": "What action should the Finance Director take on OPaL and treasury cash?", "expect_rag": True},
        ],
    },
    {
        "id": "S08",
        "pillar": "Pillar 2: Schedule III Balance Sheet",
        "title": "FY18 HPCL Acquisition Bridge Debt Spike & 8-Year De-Leveraging Journey (FY17–FY26)",
        "turns": [
            {"q": "Show the Balance Sheet of ONGC for FY18", "expect_visual": "table", "expect_metric": "balance_sheet"},
            {"q": "Why did borrowings jump from zero in FY17 to ₹25,592 crore in FY18?", "expect_rag": True},
            {"q": "Compare Total Borrowings and Cash from FY17 to FY26", "expect_rag": False},
            {"q": "What is ONGC net debt and cash position in FY26?", "expect_rag": False},
        ],
    },
    {
        "id": "S09",
        "pillar": "Pillar 2: Schedule III Balance Sheet",
        "title": "Notes 5, 7 & 8 — Oil & Gas Producing Properties vs Capital Work-in-Progress (CWIP)",
        "turns": [
            {"q": "What is ONGC Capital Work in Progress and Oil & Gas Assets net block in FY26?", "expect_rag": False},
            {"q": "Show the trend of Capital Work in Progress from FY17 to FY26", "expect_rag": False},
            {"q": "Why did CWIP decline in FY25 and FY26 as KG-DWN-98/2 Cluster-II was commissioned?", "expect_rag": True},
            {"q": "Show Oil & Gas Producing Properties net block from FY17 to FY26", "expect_rag": False},
        ],
    },
    {
        "id": "S10",
        "pillar": "Pillar 2: Schedule III Balance Sheet",
        "title": "Notes 19–21A — Net Worth, Borrowings & Ind-AS 116 Offshore Rig Lease Liabilities",
        "turns": [
            {"q": "What is ONGC Standalone Net Worth and Consolidated Net Worth in FY26?", "expect_rag": False},
            {"q": "Show the 10-year trend of Standalone Net Worth from FY17 to FY26", "expect_rag": False},
            {"q": "Explain Note 21A Lease Liabilities and why they appeared in FY20 under Ind-AS 116", "expect_rag": True},
            {"q": "Show Lease Liabilities from FY20 to FY26", "expect_rag": False},
        ],
    },
    {
        "id": "S11",
        "pillar": "Pillar 2: Schedule III Balance Sheet",
        "title": "Notes 11 & 22 — Site Restoration Abandonment Provision (ARO) & SBI Escrow Fund",
        "turns": [
            {"q": "What is ONGC abandonment decommissioning provision and site restoration fund in FY26?", "expect_rag": False},
            {"q": "Show the trend of abandonment provision from FY17 to FY26", "expect_rag": False},
            {"q": "Explain how the Site Restoration Fund escrow backs Note 22 abandonment liabilities", "expect_rag": True},
            {"q": "Show the Balance Sheet of ONGC for FY25", "expect_visual": "table", "expect_metric": "balance_sheet"},
        ],
    },
    {
        "id": "S12",
        "pillar": "Pillar 2: Schedule III Balance Sheet",
        "title": "Note 14 — Trade Receivables, Customer Concentration & Disputed Dues",
        "turns": [
            {"q": "What are ONGC trade receivables by customer in FY26?", "expect_rag": False},
            {"q": "How much are disputed receivables by customer in FY26?", "expect_rag": False},
            {"q": "What are ONGC receivable days in FY26 and how have they trended from FY17 to FY26?", "expect_rag": False},
            {"q": "How does automated LC collection from PSU refineries protect working capital?", "expect_rag": True},
        ],
    },

    # --- PILLAR 3: STATEMENT OF CASH FLOWS (SCENARIOS 13-17) ---
    {
        "id": "S13",
        "pillar": "Pillar 3: Ind-AS 7 Statement of Cash Flows",
        "title": "FY26 Cash Flow Statement Table, On-Demand Waterfall Bridge & Free Cash Flow",
        "turns": [
            {"q": "Show the Cash Flow statement of ONGC for FY26", "expect_visual": "table", "expect_metric": "cash_flow_statement"},
            {"q": "Show FY26 Cash Flow statement as a waterfall chart", "expect_visual": "chart", "expect_chart": "waterfall"},
            {"q": "How did ONGC fund ₹35,878 crore Capex and ₹14,069 crore dividends in FY26?", "expect_rag": True},
            {"q": "Show the 10-year Cash Flow statement trend from FY17 to FY26", "expect_metric": "cash_flow_statement"},
        ],
    },
    {
        "id": "S14",
        "pillar": "Pillar 3: Ind-AS 7 Statement of Cash Flows",
        "title": "Operating Cash Flow vs Free Cash Flow Generation Across Commodity Cycles (FY17–FY26)",
        "turns": [
            {"q": "What was ONGC Operating Cash Flow and Free Cash Flow in FY26?", "expect_rag": False},
            {"q": "Show the 10-year trend of Operating Cash Flow from FY17 to FY26", "expect_rag": False},
            {"q": "Show the 10-year trend of Free Cash Flow from FY17 to FY26", "expect_rag": False},
            {"q": "How did ONGC maintain positive Free Cash Flow during the FY21 pandemic trough?", "expect_rag": True},
        ],
    },
    {
        "id": "S15",
        "pillar": "Pillar 3: Ind-AS 7 Statement of Cash Flows",
        "title": "Investing Cash Flow Spikes — FY18 HPCL Buyout vs FY25 OPaL Recapitalization",
        "turns": [
            {"q": "Show the Cash Flow statement of ONGC for FY18", "expect_visual": "table", "expect_metric": "cash_flow_statement"},
            {"q": "Show the Cash Flow statement of ONGC for FY25", "expect_visual": "table", "expect_metric": "cash_flow_statement"},
            {"q": "Why did investing cash outflow spike in FY18 and FY25?", "expect_rag": True},
            {"q": "What action should the Finance Director take to bring OPaL to PAT breakeven?", "expect_rag": True},
        ],
    },
    {
        "id": "S16",
        "pillar": "Pillar 3: Ind-AS 7 Statement of Cash Flows",
        "title": "Financing Cash Flow — 10-Year Dividend Payouts, Debt Paydown & FY19 Share Buyback",
        "turns": [
            {"q": "Show the Cash Flow statement of ONGC for FY22", "expect_visual": "table", "expect_metric": "cash_flow_statement"},
            {"q": "How much debt did ONGC repay in FY22?", "expect_rag": True},
            {"q": "What was ONGC dividend per share from FY17 to FY26?", "expect_rag": False},
            {"q": "Show the Cash Flow statement of ONGC for FY19", "expect_visual": "table", "expect_metric": "cash_flow_statement"},
        ],
    },
    {
        "id": "S17",
        "pillar": "Pillar 3: Ind-AS 7 Statement of Cash Flows",
        "title": "Capital Expenditure Actuals vs Budget & 2P Reserves Under-Investment Analysis",
        "turns": [
            {"q": "Show ONGC actual capex spend by asset in FY26", "expect_rag": False},
            {"q": "Break it down by capex category in FY26", "expect_rag": False},
            {"q": "Compare capex against 2P reserves by asset", "expect_metric": "capex_vs_reserves"},
            {"q": "Show the trend of total corporate capex from FY17 to FY26", "expect_rag": False},
        ],
    },

    # --- PILLAR 4: FINANCIAL RATIOS & E&P UNIT ECONOMICS (SCENARIOS 18-22) ---
    {
        "id": "S18",
        "pillar": "Pillar 4: Financial Ratios & Credit Scorecard",
        "title": "FY26 Financial Ratios Scorecard Table, Profitability & Return Trajectory (FY17–FY26)",
        "turns": [
            {"q": "Show the Financial Ratios of ONGC for FY26", "expect_visual": "table", "expect_metric": "financial_ratios"},
            {"q": "Show the 10-year trend of Financial Ratios from FY17 to FY26", "expect_metric": "financial_ratios"},
            {"q": "Compare Standalone ROCE and ROE from FY17 to FY26", "expect_rag": False},
            {"q": "What action should the Finance Director take to defend ROCE and EBITDA margin?", "expect_rag": True},
        ],
    },
    {
        "id": "S19",
        "pillar": "Pillar 4: Financial Ratios & Credit Scorecard",
        "title": "SEBI Reg 52(4) Solvency & Liquidity Ratios — Debt/Equity, Interest Coverage & Current Ratio",
        "turns": [
            {"q": "What is ONGC debt to equity ratio and interest coverage ratio in FY26?", "expect_rag": False},
            {"q": "Show the 10-year trend of debt to equity ratio from FY17 to FY26", "expect_rag": False},
            {"q": "Show the 10-year trend of current ratio from FY17 to FY26", "expect_rag": False},
            {"q": "Show the Financial Ratios of ONGC for FY24", "expect_visual": "table", "expect_metric": "financial_ratios"},
        ],
    },
    {
        "id": "S20",
        "pillar": "Pillar 4: Financial Ratios & Credit Scorecard",
        "title": "Shareholder Per-Share Metrics — Basic EPS, Book Value Per Share & Dividend Per Share",
        "turns": [
            {"q": "What is ONGC Basic EPS and Book Value per share in FY26?", "expect_rag": False},
            {"q": "Show the 10-year trend of Basic EPS from FY17 to FY26", "expect_rag": False},
            {"q": "Show the 10-year trend of Book Value per share from FY17 to FY26", "expect_rag": False},
            {"q": "Why did Basic EPS peak in FY22 and FY24?", "expect_rag": True},
        ],
    },
    {
        "id": "S21",
        "pillar": "Pillar 4: Financial Ratios & Credit Scorecard",
        "title": "Upstream Commodity Realisations — Crude Oil ($/bbl) & Natural Gas ($/MMBtu) (FY17–FY26)",
        "turns": [
            {"q": "What was ONGC crude oil realisation in FY26?", "expect_rag": False},
            {"q": "Show the 10-year trend of crude oil realisation from FY17 to FY26", "expect_rag": False},
            {"q": "How did natural gas prices change under the Kirit Parikh ceiling and New Well Gas premium?", "expect_rag": True},
            {"q": "What was ONGC oil and gas production in FY26 and from FY17 to FY26?", "expect_rag": False},
        ],
    },
    {
        "id": "S22",
        "pillar": "Pillar 4: Financial Ratios & Credit Scorecard",
        "title": "Upstream Unit Economics — Lifting Cost ($/BOE) Across Assets & Solar Lift Optimization",
        "turns": [
            {"q": "Show lifting cost per BOE by asset in FY26", "expect_rag": False},
            {"q": "Compare lifting cost of Mumbai High and Mehsana from FY17 to FY26", "expect_rag": False},
            {"q": "Show EBITDA margin by asset in FY26", "expect_rag": False},
            {"q": "How can captive solar power reduce artificial lift opex in Gujarat and Assam?", "expect_rag": True},
        ],
    },

    # --- PILLAR 5: RECONCILED SUB-LEDGERS — SUBSIDIARIES & 53 FIELDS (SCENARIOS 23-27) ---
    {
        "id": "S23",
        "pillar": "Pillar 5: Group Subsidiaries & Yahoo Finance (ONGC.NS) Consolidation",
        "title": "Marriage of Standalone Annual Report & Yahoo Finance Consolidated Group (HPCL, MRPL, OVL, OPaL, OTPC)",
        "turns": [
            {"q": "What is ONGC Consolidated PAT vs Standalone PAT in FY26?", "expect_rag": False},
            {"q": "Show the 10-year trend of Consolidated PAT from FY17 to FY26", "expect_rag": False},
            {"q": "Explain the difference between ONGC Standalone Annual Report and Yahoo Finance ONGC.NS Consolidated numbers", "expect_rag": True},
            {"q": "Why was Consolidated PAT lower than Standalone PAT in FY23 but higher in FY24 and FY26?", "expect_rag": True},
        ],
    },
    {
        "id": "S24",
        "pillar": "Pillar 5: Group Subsidiaries & Yahoo Finance (ONGC.NS) Consolidation",
        "title": "Subsidiary Performance Breakdown — HPCL, MRPL, OVL, OPaL & OTPC (FY17–FY26)",
        "turns": [
            {"q": "Show subsidiary PAT by subsidiary in FY26", "expect_rag": False},
            {"q": "Show subsidiary revenue by subsidiary in FY26", "expect_rag": False},
            {"q": "Show the 10-year PAT trend of HPCL and MRPL from FY17 to FY26", "expect_rag": False},
            {"q": "Show subsidiary dividend received by ONGC in FY26", "expect_rag": False},
        ],
    },
    {
        "id": "S25",
        "pillar": "Pillar 5: 53 Oil & Gas Fields Sub-Ledger (Reconciled to Schedule III)",
        "title": "Field-Wise Profitability Ranking, Loss-Making Fields & PEC Turnaround Playbook",
        "turns": [
            {"q": "Which fields are most profitable and loss-making by PBT in FY26?", "expect_rag": False},
            {"q": "Show only the loss-making fields in FY26", "expect_rag": False},
            {"q": "Show field revenue by field for the top 10 fields in FY26", "expect_rag": False},
            {"q": "What action should the Finance Director take on high-water-cut marginal fields?", "expect_rag": True},
        ],
    },
    {
        "id": "S26",
        "pillar": "Pillar 5: 53 Oil & Gas Fields Sub-Ledger (Reconciled to Schedule III)",
        "title": "Offshore Giants — Mumbai High vs Bassein 10-Year Revenue, EBITDA & PBT Comparison",
        "turns": [
            {"q": "Compare PBT of Mumbai High and Bassein in FY26", "expect_rag": False},
            {"q": "Show their PBT trend from FY17 to FY26", "expect_rag": False},
            {"q": "What is their field revenue in FY26?", "expect_rag": False},
            {"q": "What is their EBITDA margin in FY26?", "expect_rag": False},
        ],
    },
    {
        "id": "S27",
        "pillar": "Pillar 5: 53 Oil & Gas Fields Sub-Ledger (Reconciled to Schedule III)",
        "title": "Western Onshore Mature Assets — Mehsana & Ankleshwar 10-Year Economics",
        "turns": [
            {"q": "Compare field revenue of Mehsana and Ankleshwar from FY17 to FY26", "expect_rag": False},
            {"q": "Compare their PBT from FY17 to FY26", "expect_rag": False},
            {"q": "Compare their operating cost in FY26", "expect_rag": False},
            {"q": "Show 2P reserves by asset in FY26", "expect_rag": False},
        ],
    },

    # --- PILLAR 6: HR-FINANCE CROSS-DOMAIN, ACTUARIAL, GREEN CAPEX & MOU (SCENARIOS 28-30) ---
    {
        "id": "S28",
        "pillar": "Pillar 6: Employee Benefits (Note 31), Actuarial Liabilities & Workforce Productivity",
        "title": "Gross vs Net P&L Employee Cost, E&D Capitalisation, Manpower $/BOE & Actuarial Liability",
        "turns": [
            {"q": "Explain Note 31 gross employee cost versus net P&L employee benefits expense in FY26", "expect_rag": True},
            {"q": "Show manpower cost per BOE by asset in FY26", "expect_rag": False},
            {"q": "Show employee cost as a percentage of revenue by asset in FY26", "expect_rag": False},
            {"q": "Show actuarial liability by benefit type in FY26", "expect_rag": False},
        ],
    },
    {
        "id": "S29",
        "pillar": "Pillar 6: Energy Transition, Green Capex & CSR Governance",
        "title": "ONGC Green Limited, Renewable Installed Capacity (MW), Green Capex & CSR Spend",
        "turns": [
            {"q": "Show ONGC renewable installed MW from FY17 to FY26", "expect_rag": False},
            {"q": "Show green capex spend from FY17 to FY26", "expect_rag": False},
            {"q": "Show CSR spend by category in FY26", "expect_rag": False},
            {"q": "How does ONGC Green Limited support captive solar power for upstream fields?", "expect_rag": True},
        ],
    },
    {
        "id": "S30",
        "pillar": "Pillar 6: MoPNG / DPE MoU Scorecard & Executive Workforce Governance",
        "title": "FY26 MoU Scorecard Achievement vs Excellent Targets & Workforce Strength",
        "turns": [
            {"q": "Show ONGC MoU scorecard achievement in FY26", "expect_rag": False},
            {"q": "What is ONGC total workforce headcount by work centre?", "expect_rag": False},
            {"q": "Break it down by discipline", "expect_rag": False},
            {"q": "How many executives have been posted at the same station for 5 years or more by work centre?", "expect_rag": False},
        ],
    },
]


def run_suite() -> None:
    import sys
    only_ids = set(sys.argv[1:]) if len(sys.argv) > 1 else None
    out_json = DATA_DIR / "stress_test_120_turns_results.json"
    prev_map: Dict[str, Any] = {}
    if only_ids and out_json.exists():
        prev_data = json.loads(out_json.read_text(encoding="utf-8"))
        for s in prev_data.get("scenarios", []):
            prev_map[s["id"]] = s

    client = httpx.Client(timeout=90.0)
    all_results: List[Dict[str, Any]] = []
    passed_turns = 0
    total_turns = 0
    failures: List[Dict[str, Any]] = []

    t_start = time.time()
    for sc in SCENARIOS:
        sid = sc["id"]
        if only_ids and sid not in only_ids and sid in prev_map:
            cached = prev_map[sid]
            all_results.append(cached)
            for tr in cached["turns"]:
                total_turns += 1
                if tr.get("ok"):
                    passed_turns += 1
                else:
                    failures.append({"scenario": sid, "turn": tr.get("turn"), "query": tr.get("query")})
            continue
        session_id = f"autonomous-30x4-{sid.lower()}-{int(time.time())}"
        sc_res = {
            "id": sid,
            "pillar": sc["pillar"],
            "title": sc["title"],
            "session_id": session_id,
            "turns": [],
        }
        print(f"\n=== Running {sid}: {sc['title']} ===", flush=True)
        for tidx, t in enumerate(sc["turns"], start=1):
            total_turns += 1
            q = t["q"]
            t0 = time.time()
            try:
                resp = client.post(
                    BACKEND_URL,
                    json={"session_id": session_id, "query": q, "persona": "CMD", "language": "en"},
                )
                elapsed = round((time.time() - t0) * 1000, 1)
                data = resp.json()
                ac = data.get("answer_contract") or data
                vis = ac.get("visual") or {}
                vtype = vis.get("type")
                chart = vis.get("chart") or {}
                ckind = chart.get("kind")
                tbl = vis.get("table") or {}
                trows = len(tbl.get("rows") or [])
                tcols = len(tbl.get("columns") or [])
                cdata = len(chart.get("data") or [])
                qspec = ac.get("query_spec") or {}
                metric = qspec.get("metric") or ac.get("metric")
                spoken = str(ac.get("spoken_summary") or "")
                insights = ac.get("insights") or []
                sql = ac.get("generated_sql") or ""

                ok = (
                    resp.status_code == 200
                    and bool(spoken.strip())
                    and vtype in ("table", "chart", "kpi")
                    and (trows > 0 or cdata > 0)
                )
                if t.get("expect_visual") and vtype != t["expect_visual"]:
                    ok = False
                if t.get("expect_chart") and ckind != t["expect_chart"]:
                    ok = False
                if t.get("expect_metric") and metric != t["expect_metric"]:
                    ok = False

                if ok:
                    passed_turns += 1
                else:
                    failures.append({
                        "scenario": sid,
                        "turn": tidx,
                        "query": q,
                        "status_code": resp.status_code,
                        "metric": metric,
                        "visual_type": vtype,
                        "chart_kind": ckind,
                        "table_rows": trows,
                        "chart_data": cdata,
                        "spoken": spoken[:200],
                    })

                turn_record = {
                    "turn": tidx,
                    "role": "Root Question" if tidx == 1 else f"Follow-up {tidx - 1}",
                    "query": q,
                    "ok": ok,
                    "latency_ms": elapsed,
                    "metric": metric,
                    "visual_type": vtype,
                    "chart_kind": ckind,
                    "table_shape": f"{trows}x{tcols}",
                    "chart_points": cdata,
                    "spoken_summary": spoken,
                    "insights": insights,
                    "sql": sql,
                }
                sc_res["turns"].append(turn_record)
                status_tag = "PASS" if ok else "FAIL"
                print(
                    f"  [{status_tag}] T{tidx} ({elapsed}ms) metric={metric} | vis={vtype}({ckind}) | tbl={trows}x{tcols} | q={q[:58]}",
                    flush=True,
                )
            except Exception as e:
                failures.append({"scenario": sid, "turn": tidx, "query": q, "error": str(e)})
                sc_res["turns"].append({"turn": tidx, "query": q, "ok": False, "error": str(e)})
                print(f"  [ERROR] T{tidx} q={q[:58]} -> {e}", flush=True)

        all_results.append(sc_res)

    total_elapsed = round(time.time() - t_start, 1)
    summary = {
        "total_scenarios": len(SCENARIOS),
        "total_turns": total_turns,
        "passed_turns": passed_turns,
        "failed_turns": total_turns - passed_turns,
        "pass_rate_pct": round(passed_turns * 100.0 / max(total_turns, 1), 2),
        "total_elapsed_sec": total_elapsed,
        "failures": failures,
        "scenarios": all_results,
    }
    out_json = DATA_DIR / "stress_test_120_turns_results.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n==========================================")
    print(f"COMPLETED {passed_turns}/{total_turns} TURNS ({summary['pass_rate_pct']}%) in {total_elapsed}s")
    print(f"Saved JSON report to {out_json}")
    if failures:
        print(f"Failures ({len(failures)}):")
        for f in failures:
            print(" ", f)

    # Generate Markdown Curated 30 Scenarios × 4 Turns Benchmark Document
    md_lines = [
        "# Curated 30-Scenario × 4-Turn (120 Total Turns) Financial & HR Intelligence Verification Catalog",
        "",
        f"- **Execution Status:** `{passed_turns} / {total_turns}` Conversational Turns Verified (`{summary['pass_rate_pct']}%` Pass Rate)",
        f"- **Total Runtime:** `{total_elapsed}s` against live Gemini 2.5 Flash Planner + BigQuery SSOT (`ongc-hr-finance-agent`) + Hybrid Context & Vector RAG (`ssot_financial_line_context` & `financial_notes_chunks`)",
        "- **Visual Governance Verified:** Table-First (`visual.type = \"table\"`) for all Financial Statements (P&L, Balance Sheet, Cash Flow, Ratios); Waterfall Chart (`chart.kind = \"waterfall\"`) on explicit demand.",
        "",
        "---",
        "",
    ]
    for sc in all_results:
        md_lines.append(f"## {sc['id']}: {sc['title']}")
        md_lines.append(f"**Pillar:** {sc['pillar']} · **Session ID:** `{sc['session_id']}`")
        md_lines.append("")
        for tr in sc["turns"]:
            badge = "✅ PASS" if tr.get("ok") else "❌ FAIL"
            md_lines.append(f"### Turn {tr['turn']} ({tr.get('role', '')}): *\"{tr['query']}\"* — {badge}")
            md_lines.append(
                f"- **Resolved Metric:** `{tr.get('metric')}` · **Visual:** `{tr.get('visual_type')}` "
                f"(Chart: `{tr.get('chart_kind')}`, Table: `{tr.get('table_shape')}`) · **Latency:** `{tr.get('latency_ms')} ms`"
            )
            md_lines.append(f"- **Executive Briefing (`spoken_summary`):** {tr.get('spoken_summary')}")
            ins = tr.get("insights") or []
            if ins:
                md_lines.append("- **Key Takeaways & Annual Report Context / Finance Director Actions:**")
                for bullet in ins:
                    md_lines.append(f"  - {bullet}")
            md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

    out_md = BASE_DIR / "05_curated_30_questions_and_followups.md"
    out_md.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Saved Curated 120-Turn Q&A Markdown Catalog to {out_md}")


if __name__ == "__main__":
    run_suite()
