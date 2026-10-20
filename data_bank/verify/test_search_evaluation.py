"""
test_search_evaluation.py — Evaluates Vertex AI Search on:
 1. Old 40 queries under the Lead's approved label policy (real public policy texts count).
 2. Fresh 40 queries (different wording, 25 policy + 8 policy/data context + 7 MIS look-ups).
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from google.cloud import discoveryengine_v1 as discoveryengine

PROJECT_ID = "ongc-hr-finance-agent"
LOCATION = "global"
DATA_STORE = "hrfin-doc-search-store"

search_client = discoveryengine.SearchServiceClient()
serving_config = search_client.serving_config_path(
    project=PROJECT_ID,
    location=LOCATION,
    data_store=DATA_STORE,
    serving_config="default_search",
)

# -----------------------------------------------------------------------------
# 1. Old 40 Queries under Approved Label Policy
# -----------------------------------------------------------------------------
old_queries_40 = [
    ("minimum stay required at an asset before an officer can be moved", ["JRTP", "DOC-RB-JRTP", "J-03"]),
    ("how many years can an employee spend in a single city across multiple stints", ["JRTP", "DOC-RB-JRTP", "J-03"]),
    ("which offices in the National Capital Region count towards the same station limit", ["JRTP", "DOC-RB-JRTP", "J-03"]),
    ("who has the power to waive the mandatory hardship posting requirement", ["JRTP", "DOC-RB-JRTP", "J-03"]),
    ("how many days of earned leave do employees accumulate each year and what is the maximum balance", ["Leave", "DOC-RB-LEAVE", "P1-10", "J-09"]),
    ("who is authorized to approve half pay leave or medical leave", ["Leave", "DOC-RB-LEAVE", "P1-10", "J-09"]),
    ("what happens to unencashed leave when an executive separates", ["Leave", "DOC-RB-LEAVE", "P1-10", "J-09"]),
    ("what is the daily allowance and hardship pay for offshore platform duty", ["TA", "Travelling", "DOC-RB-TA", "P1-16"]),
    ("what travel class is allowed for domestic flights on official tour for junior executives", ["TA", "Travelling", "DOC-RB-TA", "P1-16", "P2-25"]),
    ("where to submit complaints regarding sexual harassment in the workplace", ["POSH", "ICC", "DOC-RB-POSH", "P1-01"]),
    ("what are the eligibility benchmarks and marks required in performance appraisal for merit promotion", ["Promotion", "RP", "DOC-RB-RP", "J-15"]),
    ("what is the rule for transferring executives who have stayed for a long time at corporate headquarters", ["JRTP", "DOC-RB-JRTP", "J-03"]),
    ("are executives without north east service eligible for promotion to executive director or general manager", ["JRTP", "DOC-RB-JRTP", "J-03"]),
    ("what is the statutory ceiling on employer contribution to retirement benefits", ["DPE", "Superannuation", "DOC-RB-BDP", "Benefit", "P13", "PRBS", "G-01"]),
    ("how does dropping from excellent to very good score in performance memorandum affect annual bonus pool", ["MoU", "PRP", "DOC-RB-BDP", "P14", "G-01"]),
    ("what are the statutory spending guidelines for corporate social responsibility in aspirational districts", ["CSR", "DOC-RB-BDP", "P15", "Companies_Act", "P2-25"]),
    ("who has the sanction authority to approve high value drilling contracts above fifty crore rupees", ["Delegated", "BDP", "DOC-RB-BDP", "P1-04"]),
    ("what is the government directive regarding minimum dividend payout as percentage of profit after tax", ["DIPAM", "Dividend", "DOC-RB-BDP", "P17", "G-07"]),
    ("guidelines for annual general transfer proposal preparation", ["JRTP", "DOC-RB-JRTP", "J-03"]),
    ("what are the rules governing disciplinary proceedings and minor penalty under conduct rules", ["CDA", "Conduct", "DOC-RB-CDA", "P1-01"]),
    ("what is the delegation of power for entering into production enhancement contracts on mature fields", ["BDP", "Delegated", "DOC-RB-BDP", "P1-04"]),
    ("when am I eligible for rotation and what is the tenure for executive cadre", ["JRTP", "DOC-RB-JRTP", "J-03"]),
    ("criteria and marks required for promotion from grade E2 to E3", ["Promotion", "RP", "DOC-RB-RP", "J-15"]),
    ("air travel entitlement for 14 day shift duty on western offshore platforms", ["TA", "Travelling", "DOC-RB-TA", "P1-16"]),
    ("transfer proposal criteria from corporate headquarters to field assets in Assam and Tripura", ["JRTP", "DOC-RB-JRTP", "J-03"]),
    ("standard rotation timeline for Mumbai offices under regional mobility rules", ["JRTP", "DOC-RB-JRTP", "J-03"]),
    ("what are the valid grounds for DPC review delay and vigilance clearance holds", ["DPC", "Vigilance", "DOC-RB-RP", "CDA", "P1-01"]),
    ("financial sanction limits of asset managers versus functional directors for procurement", ["BDP", "Delegated", "DOC-RB-BDP", "P1-04"]),
    ("exceptions allowed for spouses posted in the same city under transfer rules", ["JRTP", "DOC-RB-JRTP", "J-03"]),
    ("what is the medical reimbursement limit for indoor hospital treatment for retired employees", ["Medical", "PRMB", "DOC-RB-MED", "P1-03"]),
    ("can an officer be transferred before completing three years in case of administrative emergency", ["JRTP", "DOC-RB-JRTP", "J-03"]),
    ("does Nazira and Jorhat count as the same regional cluster for station tenure", ["JRTP", "DOC-RB-JRTP", "J-03"]),
    ("can casual leave be combined with earned leave or study leave", ["Leave", "DOC-RB-LEAVE", "P1-10", "J-09"]),
    ("what schemes are included within the thirty percent superannuation cap", ["Benefit", "Superannuation", "DOC-RB-BDP", "P13", "PRBS", "G-01"]),
    ("is splitting of purchase orders allowed to avoid higher approval tiers", ["BDP", "Delegated", "DOC-RB-BDP", "P1-04"]),
    ("monthly crude oil production and water cut for Neelam Heera asset", ["NEH", "Neelam", "MIS"]),
    ("operating expenditure and lifting cost per barrel for Mumbai High", ["MUM", "Mumbai", "MIS"]),
    ("overtime hours and overtime payout for Ahmedabad asset", ["AHM", "Ahmedabad", "MIS"]),
    ("lost time injuries and safety incident log for Assam asset", ["ASM", "Assam", "MIS"]),
    ("drilling rig downtime and active producing wells in Cambay", ["CAM", "Cambay", "MIS"]),
]

# -----------------------------------------------------------------------------
# 2. Fresh 40 Queries (25 Policy, 8 Policy+Data, 7 MIS)
# -----------------------------------------------------------------------------
fresh_queries_40 = [
    # 25 Policy questions
    ("mandatory duration an employee must serve at an assigned station before being eligible for displacement", ["JRTP", "DOC-RB-JRTP", "J-03"]),
    ("total maximum lifetime service permitted within a single geographical territory or capital region", ["JRTP", "DOC-RB-JRTP", "J-03"]),
    ("exemption criteria for executives approaching retirement age from mandatory station transfer", ["JRTP", "DOC-RB-JRTP", "J-03"]),
    ("consequences and penalties for officers refusing to proceed on transfer to difficult remote stations", ["JRTP", "DOC-RB-JRTP", "CDA", "P1-01"]),
    ("maximum accumulation limit for privilege leave and rules for advance annual credit", ["Leave", "DOC-RB-LEAVE", "P1-10", "J-09"]),
    ("conditions under which female employees are entitled to maternity leave and adoption leave", ["Leave", "DOC-RB-LEAVE", "P1-10", "J-09"]),
    ("encashment procedure for earned leave balance during active service and upon superannuation", ["Leave", "DOC-RB-LEAVE", "P1-10", "J-09"]),
    ("special disability leave admissibility for work-related accidents sustained during offshore operations", ["Leave", "DOC-RB-LEAVE", "P1-10"]),
    ("lodging allowance and per diem entitlement for senior executives during official tours to tier one cities", ["TA", "Travelling", "DOC-RB-TA", "P1-16"]),
    ("mode of conveyance and baggage transportation reimbursement on permanent transfer", ["TA", "Travelling", "DOC-RB-TA", "P1-16"]),
    ("special offshore compensatory allowance payable for drilling rig operations and production platforms", ["TA", "Travelling", "DOC-RB-TA", "P1-16"]),
    ("procedure for conducting inquiry into allegations of sexual harassment by the internal committee", ["POSH", "ICC", "DOC-RB-POSH", "P1-01"]),
    ("appraisal score weightage and minimum qualifying marks for promotion from assistant executive engineer to executive engineer", ["Promotion", "RP", "DOC-RB-RP", "J-15"]),
    ("circumstances under which an executive can be superseded in promotion board review", ["Promotion", "RP", "DOC-RB-RP", "J-15", "P1-01"]),
    ("statutory ceiling under presidential directives on total employee retirement benefits as percentage of basic pay plus DA", ["DPE", "Superannuation", "PRBS", "G-01", "P13"]),
    ("computation of performance related pay pool based on annual memorandum of understanding achievement score", ["MoU", "PRP", "G-01", "P14"]),
    ("statutory corporate social responsibility obligation of two percent of average net profit under company law", ["CSR", "Companies_Act", "P15", "P2-25"]),
    ("powers of key executives and asset heads to approve capital and revenue procurement tenders", ["Delegated", "BDP", "DOC-RB-BDP", "P1-04"]),
    ("mandatory requirement of associate finance concurrence before issuing purchase orders or work contracts", ["BDP", "Delegated", "DOC-RB-BDP", "P1-04"]),
    ("statutory requirement to pay minimum dividend of thirty percent of net profit to government shareholders", ["DIPAM", "Dividend", "G-07", "P17"]),
    ("conduct rules prohibiting employees from engaging in private commercial trade or business", ["CDA", "Conduct", "DOC-RB-CDA", "P1-01"]),
    ("procedure for imposing minor penalties including censure and recovery from pay under disciplinary rules", ["CDA", "Conduct", "DOC-RB-CDA", "P1-01"]),
    ("competent authority for granting medical treatment approval in private empaneled hospitals", ["Medical", "PRMB", "DOC-RB-MED", "P1-03"]),
    ("post retirement medical scheme eligibility criteria for employees with minimum fifteen years of service", ["Medical", "PRMB", "DOC-RB-MED", "P1-03"]),
    ("cooling off period required between consecutive postings at arduous category C stations", ["JRTP", "DOC-RB-JRTP", "J-03"]),

    # 8 Policy + Data Context questions
    ("transfer eligibility of senior executives currently overstaying past five years in Delhi corporate office", ["JRTP", "DOC-RB-JRTP", "DEL", "DOC-CONF-002"]),
    ("executives awaiting E5 review who have not fulfilled the mandatory service at hard stations", ["JRTP", "DOC-RB-JRTP", "DPC", "DOC-CONF-003"]),
    ("succession preparedness for general managers and group general managers retiring over the next three fiscal years", ["Succession", "DOC-CONF-001", "DOC-RB-RP"]),
    ("disciplinary action and vigilance clearance impact on delayed departmental promotion committee cases", ["DPC", "Vigilance", "CDA", "P1-01"]),
    ("actuarial funding deficit and plan asset valuation across post retirement employee benefit trusts", ["Benefit", "PRBS", "Superannuation", "G-01"]),
    ("corporate social responsibility budget allocation directed towards operational oil and gas field districts", ["CSR", "Companies_Act", "P15"]),
    ("capital expenditure progress variance against budget estimates on major deepwater offshore development projects", ["Capex", "Project", "DOC-CONF-006"]),
    ("board authorization threshold required for entering into production enhancement contracts on loss making fields", ["BDP", "Delegated", "DOC-CONF-004"]),

    # 7 MIS Look-ups
    ("monthly crude oil extraction rate and water cut percentage for Mumbai High North", ["MUM", "Mumbai", "MIS"]),
    ("gas production volume and compressor downtime hours for Bassein offshore asset", ["BAS", "Bassein", "MIS"]),
    ("operating expenditure breakdown by chemical and workover cost heads in Ankleshwar field", ["ANK", "Ankleshwar", "MIS"]),
    ("contractor workforce deployment and monthly labor spend in Hazira processing plant", ["HAZ", "Hazira", "MIS"]),
    ("lost time injury frequency rate and safety incident count for Neelam and Heera asset", ["NEH", "Neelam", "MIS"]),
    ("regular employee headcount and overtime hours worked at Mehsana asset", ["MEH", "Mehsana", "MIS"]),
    ("capex budget utilization and actual spend variance for Eastern Offshore asset", ["EAS", "Eastern", "MIS"]),
]


def evaluate_query_set(query_set: List[Tuple[str, List[str]]], label: str) -> Dict[str, Any]:
    print(f"\nEvaluating {label} ({len(query_set)} queries)...")
    hits = 0
    details = []

    for idx, (q, kws) in enumerate(query_set, start=1):
        req = discoveryengine.SearchRequest(serving_config=serving_config, query=q, page_size=3)
        res = search_client.search(req)
        matched = False
        top3_ids = []
        for r in res.results:
            did = r.document.id
            top3_ids.append(did)
            if any(k.lower() in did.lower() for k in kws):
                matched = True

        if matched:
            hits += 1
        details.append({
            "query_number": idx,
            "query": q,
            "expected_keywords": kws,
            "top3_doc_ids": top3_ids,
            "top3_hit": matched,
        })

    recall_pct = round(hits / len(query_set) * 100.0, 1)
    print(f"{label} Complete: {hits} / {len(query_set)} Top-3 Hits ({recall_pct}%)")
    return {
        "label": label,
        "total_queries": len(query_set),
        "top3_hits": hits,
        "top3_recall_pct": recall_pct,
        "details": details,
    }


def main():
    t0 = time.time()
    res_old = evaluate_query_set(old_queries_40, "Old 40 Queries (Approved Label Policy)")
    res_fresh = evaluate_query_set(fresh_queries_40, "Fresh 40 Queries (Re-Test Benchmark)")

    summary = {
        "evaluation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "duration_seconds": round(time.time() - t0, 2),
        "old_queries_evaluation": res_old,
        "fresh_queries_evaluation": res_fresh,
    }

    out_file = Path(__file__).resolve().parent / "reports" / "G4_search_benchmarks.json"
    out_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nAll evaluations saved to {out_file}")


if __name__ == "__main__":
    main()
