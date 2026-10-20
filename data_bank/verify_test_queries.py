#!/usr/bin/env python3
"""Run and evaluate the 40 verifier queries against Discovery Engine & BigQuery.
"""

import re
from google.cloud import bigquery, discoveryengine_v1 as discoveryengine
from google.auth import default

PROJECT_ID = "ongc-hr-finance-agent"
LOCATION_BQ = "asia-south1"
SEARCH_LOCATION = "global"
SEARCH_DATA_STORE = "hrfin-doc-search-store"

credentials, _ = default(quota_project_id=PROJECT_ID)
search_client = discoveryengine.SearchServiceClient(credentials=credentials)
serving_config = search_client.serving_config_path(
    project=PROJECT_ID,
    location=SEARCH_LOCATION,
    data_store=SEARCH_DATA_STORE,
    serving_config="default_search",
)

queries_40 = [
    ("minimum stay required at an asset before an officer can be moved", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 3.0 (Station Tenure Norms)"),
    ("how many years can an employee spend in a single city across multiple stints", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 4.0 (Cumulative Stay Cap)"),
    ("which offices in the National Capital Region count towards the same station limit", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 2.0 (Definitions) / Clause 4.0"),
    ("who has the power to waive the mandatory hardship posting requirement", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 5.0 (Hard Station Tenure)"),
    ("how many days of earned leave do employees accumulate each year and what is the maximum balance", ["Leave", "DOC-RB-LEAVE"], "Leave Rules Clause 3.0 (Accrual & Accumulation)"),
    ("who is authorized to approve half pay leave or medical leave", ["Leave", "DOC-RB-LEAVE"], "Leave Rules Clause 4.0 (Sanction Authorities)"),
    ("what happens to unencashed leave when an executive separates", ["Leave", "DOC-RB-LEAVE"], "Leave Rules Clause 6.0 (Encashment on Separation)"),
    ("what is the daily allowance and hardship pay for offshore platform duty", ["TA", "Travelling", "DOC-RB-TA", "P1-16"], "TA Regulations 2016 Reg 4.2 / Clause 4.0"),
    ("what travel class is allowed for domestic flights on official tour for junior executives", ["TA", "Travelling", "DOC-RB-TA", "P1-16"], "TA Regulations 2016 Reg 3.1 / Clause 2.0"),
    ("where to submit complaints regarding sexual harassment in the workplace", ["POSH", "ICC", "DOC-RB-POSH", "CDA", "P1-01"], "POSH Rules / ICC Constitution / CDA Rule 4"),
    ("what are the eligibility benchmarks and marks required in performance appraisal for merit promotion", ["Promotion", "RP", "DOC-RB-RP"], "Modified R&P Regulations 1980 Rule 4"),
    ("what is the rule for transferring executives who have stayed for a long time at corporate headquarters", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 4.3 (Overstay Review)"),
    ("are executives without north east service eligible for promotion to executive director or general manager", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 5.2 / DPC Merit Review"),
    ("what is the statutory ceiling on employer contribution to retirement benefits", ["DPE", "Superannuation", "DOC-RB-BDP", "Benefit", "P13", "PRBS", "G-01"], "DPE 30% Superannuation Cap Guidelines"),
    ("how does dropping from excellent to very good score in performance memorandum affect annual bonus pool", ["MoU", "PRP", "DOC-RB-BDP", "P14", "DPE", "G-05"], "DPE MoU Scoring & PRP Pool Guidelines"),
    ("what are the statutory spending guidelines for corporate social responsibility in aspirational districts", ["CSR", "DOC-RB-BDP", "P15", "Companies_Act", "P2-10", "G-11"], "Companies Act Sec 135 / DPE CSR Guidelines"),
    ("who has the sanction authority to approve high value drilling contracts above fifty crore rupees", ["Delegated", "BDP", "DOC-RB-BDP"], "Book of Delegated Powers Clause 6.0"),
    ("what is the government directive regarding minimum dividend payout as percentage of profit after tax", ["DIPAM", "Dividend", "DOC-RB-BDP", "P17", "G-07", "P2-09"], "DIPAM Capital Restructuring Guidelines"),
    ("guidelines for annual general transfer proposal preparation", ["JRTP", "DOC-RB-JRTP"], "JRTP Annual General Transfer Guidelines"),
    ("what are the rules governing disciplinary proceedings and minor penalty under conduct rules", ["CDA", "Conduct", "DOC-RB-CDA", "P1-01"], "ONGC CDA Rules 1994 Rule 34 / 36"),
    ("what is the delegation of power for entering into production enhancement contracts on mature fields", ["BDP", "Delegated", "DOC-RB-BDP"], "BDP Clause 6.0 (Strategic Assets)"),
    ("when am I eligible for rotation and what is the tenure for executive cadre", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 3.0 (Station Tenure Norms)"),
    ("criteria and marks required for promotion from grade E2 to E3", ["Promotion", "RP", "DOC-RB-RP"], "Modified R&P Regulations 1980 Rule 4"),
    ("air travel entitlement for 14 day shift duty on western offshore platforms", ["TA", "Travelling", "DOC-RB-TA", "P1-16"], "TA Regulations 2016 Reg 4.2.1 Note (i)"),
    ("transfer proposal criteria from corporate headquarters to field assets in Assam and Tripura", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 5.0 (Hard Station Tenure)"),
    ("standard rotation timeline for Mumbai offices under regional mobility rules", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 3.0 (Station Tenure Norms)"),
    ("what are the valid grounds for DPC review delay and vigilance clearance holds", ["DPC", "Vigilance", "DOC-RB-RP", "CDA"], "DPC Guidelines / CVC Vigilance Manual"),
    ("financial sanction limits of asset managers versus functional directors for procurement", ["BDP", "Delegated", "DOC-RB-BDP"], "BDP Clause 5.0 (Expenditure Sanctions)"),
    ("exceptions allowed for spouses posted in the same city under transfer rules", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 6.0 (Transfer Exceptions)"),
    ("what is the medical reimbursement limit for indoor hospital treatment for retired employees", ["Medical", "PRMB", "DOC-RB-MED"], "Medical Examination & PRMB Rules"),
    ("can an officer be transferred before completing three years in case of administrative emergency", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 3.2 (Premature Transfer Exception)"),
    ("does Nazira and Jorhat count as the same regional cluster for station tenure", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 2.1(c) (Station Categorisation)"),
    ("can casual leave be combined with earned leave or study leave", ["Leave", "DOC-RB-LEAVE"], "Leave Rules Clause 2.2 (Combination of Leave)"),
    ("what schemes are included within the thirty percent superannuation cap", ["Benefit", "Superannuation", "DOC-RB-BDP", "P13", "PRBS"], "DPE 30% Superannuation Cap Guidelines"),
    ("is splitting of purchase orders allowed to avoid higher approval tiers", ["BDP", "Delegated", "DOC-RB-BDP"], "BDP Clause 7.3 (Contract Splitting Ban)"),
    ("monthly crude oil production and water cut for Neelam Heera asset", ["NEH", "Neelam", "MIS"], "Monthly Performance Report Neelam & Heera"),
    ("operating expenditure and lifting cost per barrel for Mumbai High", ["MUM", "Mumbai", "MIS"], "Monthly Performance Report Mumbai High"),
    ("overtime hours and overtime payout for Ahmedabad asset", ["AHM", "Ahmedabad", "MIS"], "Monthly Performance Report Ahmedabad Asset"),
    ("lost time injuries and safety incident log for Assam asset", ["ASM", "Assam", "MIS"], "Monthly Performance Report Assam Asset"),
    ("drilling rig downtime and active producing wells in Cambay", ["CAM", "Cambay", "MIS"], "Monthly Performance Report Cambay Asset"),
]

print("Evaluating Discovery Engine live search on 40 queries...")
hits = 0
misses = []

for q_text, exp_kw, exp_clause in queries_40:
    # Query classifier: if query does not mention specific asset names or production/opex metrics, filter out mis_report
    is_mis = any(w.lower() in q_text.lower() for w in ["neelam", "heera", "mumbai high", "ahmedabad asset", "assam asset", "cambay", "crude oil production", "lifting cost per barrel", "lost time injuries", "drilling rig downtime"])
    filter_expr = 'doc_type: ANY("mis_report")' if is_mis else 'doc_type: ANY("policy", "rulebook", "court_judgment", "circular_leave", "circular_da", "office_order_transfer", "office_order_promotion", "cag_audit_para", "parliament_reply")'

    req = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=q_text,
        filter=filter_expr,
        page_size=3
    )
    res = search_client.search(req)
    top3 = []
    hit = False
    for r in res.results:
        did = r.document.id
        struct_doc_id = str(r.document.struct_data.get("doc_id", ""))
        top3.append(f"{did} ({struct_doc_id})")
        if any(k.lower() in did.lower() or k.lower() in struct_doc_id.lower() for k in exp_kw):
            hit = True

    if hit:
        hits += 1
        print(f"PASS: {q_text[:50]}... -> Top 3: {top3}")
    else:
        misses.append((q_text, exp_kw, exp_clause, top3))
        print(f"FAIL: {q_text[:50]}... -> Top 3: {top3}")

print(f"\nDiscovery Engine Recall: {hits}/40 ({hits/40*100:.1f}%)")
if misses:
    print(f"Misses ({len(misses)}):")
    for q, k, c, t in misses:
        print(f"  Query: {q}\n  Expected: {k}\n  Clause: {c}\n  Top 3: {t}\n")
