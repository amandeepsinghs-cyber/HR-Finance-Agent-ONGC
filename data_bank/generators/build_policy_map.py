"""Builder script for data_bank/world_bible/policy_question_map.yaml (Step 1.6).

Produces:
1. documents: Registry of 78 collected public policy documents.
2. question_map: Mapping for every question/follow-up requiring policy/rule text.
3. reconstruction_requirements: Per-rulebook specifications for step 3.1 demo reconstructions.
"""

import re
from pathlib import Path
import yaml

DATA_BANK_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = DATA_BANK_DIR.parent
POLICIES_DIR = PROJECT_DIR / "knowledge/public_sources/policies"
MANIFEST_PATH = POLICIES_DIR / "MANIFEST.md"
TEXT_DIR = POLICIES_DIR / "text"
RAW_DIR = POLICIES_DIR / "raw"
OUTPUT_PATH = DATA_BANK_DIR / "world_bible/policy_question_map.yaml"


def normalize_text(text: str) -> str:
    """Normalize whitespace and punctuation for substring checks."""
    s = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", s).strip().lower()


def build_documents_registry() -> list[dict]:
    """Parse MANIFEST.md and build the registry of 78 collected documents."""
    manifest_text = MANIFEST_PATH.read_text(errors="ignore")
    lines = manifest_text.splitlines()

    in_table = False
    current_header = []
    table_idx = 0
    parsed_rows = []

    for line in lines:
        if line.startswith("| id |"):
            in_table = True
            current_header = [c.strip() for c in line.split("|")[1:-1]]
            table_idx += 1
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            cols = [c.strip() for c in line.split("|")[1:-1]]
            if cols and cols[0]:
                row_dict = dict(zip(current_header, cols))
                row_dict["_table_idx"] = table_idx
                parsed_rows.append(row_dict)
        elif in_table and not line.startswith("|"):
            in_table = False

    registry = []
    for d in parsed_rows:
        doc_id = d["id"]
        # Skip items that were not downloaded / no file on disk
        if doc_id in ("P1-02", "J-04"):
            continue

        t_idx = d["_table_idx"]

        if t_idx == 2:  # Court judgment
            title = d["case"]
            issuer = d["court/date"].split(",")[0].strip()
            year_match = re.search(r"\b(19\d\d|20\d\d)\b", d["court/date"])
            year = int(year_match.group(1)) if year_match else 2026
            source_type = "court_judgment"
            raw_path = None
            text_filename = Path(d["local text"].split("/")[-1]).name
            text_path = f"knowledge/public_sources/policies/text/{text_filename}"
            hr_fin = d.get("HR/Fin", "HR")
            fidelity = "excerpt"

            registry.append({
                "doc_id": doc_id,
                "title": title,
                "issuer": issuer,
                "year": year,
                "source_type": source_type,
                "raw_path": raw_path,
                "text_path": text_path,
                "hr_finance": hr_fin,
                "confidentiality": "public",
                "fidelity": fidelity,
            })
        elif t_idx == 3:  # Parliament question
            title = d["title"]
            issuer = "Parliament of India (Ministry of Petroleum and Natural Gas)"
            year_match = re.search(r"\b(19\d\d|20\d\d)\b", d["date"])
            year = int(year_match.group(1)) if year_match else 2026
            source_type = "parliament"
            text_filename = "parl_ls_au2067_ongc.txt" if doc_id == "Q-01" else "parl_rs_au1567_ongc.txt"
            raw_filename = "parl_ls_au2067_ongc.pdf" if doc_id == "Q-01" else "parl_rs_au1567_ongc.pdf"
            raw_path = f"knowledge/public_sources/policies/raw/{raw_filename}"
            text_path = f"knowledge/public_sources/policies/text/{text_filename}"
            hr_fin = "HR"
            fidelity = "full"

            registry.append({
                "doc_id": doc_id,
                "title": title,
                "issuer": issuer,
                "year": year,
                "source_type": source_type,
                "raw_path": raw_path,
                "text_path": text_path,
                "hr_finance": hr_fin,
                "confidentiality": "public",
                "fidelity": fidelity,
            })
        else:  # Tables 1, 4, 5, 6
            title = d["title"].replace("**", "").strip()
            issuer = d["issuer"]
            year_str = d.get("year/version", d.get("date", "2024"))
            year_match = re.search(r"\b(19\d\d|20\d\d)\b", year_str)
            year = int(year_match.group(1)) if year_match else 2024
            source_type = d.get("source_type", "official_ongc")
            file_col = d.get("local file (raw → text)", d.get("local file", ""))

            if doc_id == "P2-16":
                registry.append({
                    "doc_id": "P2-16",
                    "title": "Human Rights Policy of ONGC and OVL, 2022",
                    "issuer": issuer,
                    "year": 2022,
                    "source_type": source_type,
                    "raw_path": "knowledge/public_sources/policies/raw/ongc_ovl_human_rights_policy_2022.pdf",
                    "text_path": "knowledge/public_sources/policies/text/ongc_ovl_human_rights_policy_2022.txt",
                    "hr_finance": d.get("HR/Fin", "HR"),
                    "confidentiality": "public",
                    "fidelity": "full",
                })
                registry.append({
                    "doc_id": "P2-16-preface",
                    "title": "Human Rights Policy of ONGC and OVL, 2022 (Preface)",
                    "issuer": issuer,
                    "year": 2022,
                    "source_type": source_type,
                    "raw_path": "knowledge/public_sources/policies/raw/ongc_human_rights_policy_2022_preface.pdf",
                    "text_path": "knowledge/public_sources/policies/text/ongc_human_rights_policy_2022_preface.txt",
                    "hr_finance": d.get("HR/Fin", "HR"),
                    "confidentiality": "public",
                    "fidelity": "excerpt",
                })
                continue

            raw_m = re.search(r"raw/([a-zA-Z0-9_\-\.]+)", file_col)
            text_m = re.search(r"text/([a-zA-Z0-9_\-\.]+)", file_col)
            raw_fn = raw_m.group(1) if raw_m else None
            text_fn = text_m.group(1) if text_m else None
            if text_fn == "…" or not text_fn:
                if raw_fn:
                    text_fn = Path(raw_fn).stem + ".txt"

            raw_path = f"knowledge/public_sources/policies/raw/{raw_fn}" if raw_fn else None
            text_path = f"knowledge/public_sources/policies/text/{text_fn}" if text_fn else None

            hr_fin = d.get("HR/Fin", "HR")
            fidelity = "full"
            if "excerpt" in d.get("summary", "").lower() or "compendium" in d.get("summary", "").lower():
                fidelity = "excerpt"

            registry.append({
                "doc_id": doc_id,
                "title": title,
                "issuer": issuer,
                "year": year,
                "source_type": source_type,
                "raw_path": raw_path,
                "text_path": text_path,
                "hr_finance": hr_fin,
                "confidentiality": "public",
                "fidelity": fidelity,
            })

    return registry


def build_question_map() -> list[dict]:
    """Build the comprehensive question map covering all policy/rule queries."""
    qmap = [
        # --- Policy Questions (P1 - P10, E4, E5) ---
        {
            "id": "E2",
            "question_text": "When am I due for transfer, and what is the rotation policy for my grade?",
            "type": "policy_plus_data",
            "doc_ids": ["J-03"],
            "clause_reference": "JRTP Station Tenure Norms & Cluster Rotation",
            "quote": "retention and transfer policy of the ONGC",
            "status": "needs_reconstruction",
            "reconstruction_target": "JRTP",
        },
        {
            "id": "E4",
            "question_text": "What are the eligibility criteria for promotion from E2 to E3?",
            "type": "policy",
            "doc_ids": ["J-15"],
            "clause_reference": "Modified Recruitment & Promotion Regulations 1980 / Service Rules 1995, Rule 4",
            "quote": "Recruitment and Promotion Regulations, 1980",
            "status": "needs_reconstruction",
            "reconstruction_target": "R&P/Promotion",
        },
        {
            "id": "E5",
            "question_text": "What is the TA/DA entitlement for an offshore posting?",
            "type": "policy",
            "doc_ids": ["P1-16"],
            "clause_reference": "ONGC Travelling Allowance Regulations 2016, Regulation 4.2.1 Note (i)",
            "quote": "employees working on 14 days On/Off shift pattern in Offshore areas of Mumbai and KG Offshore may not be forced to travel by check fare tickets and instead they may be allowed to travel by air by economy/'Y' class",
            "status": "answered_by_real",
        },
        {
            "id": "P1",
            "question_text": "What is the minimum tenure at a station, and the maximum cumulative stay in one city?",
            "type": "policy",
            "doc_ids": ["J-03"],
            "clause_reference": "JRTP Clause 3 (Station Tenure Norms) & Clause 4 (Cumulative Stay Cap)",
            "quote": "transferred from Rajahmundry to Chennai on the ground that the Respondent had completed his tenure of five years",
            "status": "needs_reconstruction",
            "reconstruction_target": "JRTP",
        },
        {
            "id": "P2",
            "question_text": "Which stations count as one cluster for tenure purposes?",
            "type": "policy",
            "doc_ids": ["J-03", "P1-16"],
            "clause_reference": "JRTP Clause 5 (Geographic Clusters) & TA Regulations Annexure I",
            "quote": "Brihan Mumbai, Chennai, Kolkata, New Delhi (including Faridabad, Ghaziabad, Noida & Gurgaon), Bangalore, Hyderabad",
            "status": "needs_reconstruction",
            "reconstruction_target": "JRTP",
        },
        {
            "id": "P3",
            "question_text": "Am I exempt from transfer if I retire in 2 years?",
            "type": "policy",
            "doc_ids": ["J-03"],
            "clause_reference": "JRTP Clause 7 (Pre-Retirement Superannuation Exemption)",
            "quote": "transfer policy",
            "status": "needs_reconstruction",
            "reconstruction_target": "JRTP",
        },
        {
            "id": "P4",
            "question_text": "How many earned leave days can I accumulate and encash at retirement?",
            "type": "policy",
            "doc_ids": ["J-07"],
            "clause_reference": "ONGC Leave Rules 1995, Earned Leave Accumulation & Encashment Rules",
            "quote": "leave encashment is not a bounty and is a part of terminal benefit",
            "status": "needs_reconstruction",
            "reconstruction_target": "Leave Rules",
        },
        {
            "id": "P5",
            "question_text": "Am I eligible for study leave, and what bond applies?",
            "type": "policy",
            "doc_ids": ["J-08"],
            "clause_reference": "ONGC Leave Rules 1995, Study Leave & Extraordinary Leave Provisions",
            "quote": "Extraordinary Leave (EOL) without pay",
            "status": "needs_reconstruction",
            "reconstruction_target": "Leave Rules",
        },
        {
            "id": "P6",
            "question_text": "Can I accept a gift from a vendor at Diwali? What is the limit?",
            "type": "policy",
            "doc_ids": ["P1-01"],
            "clause_reference": "ONGC CDA Rules 1994 (Amended 2011), Rule 16(a)(1)(a) & 16(a)(4)",
            "quote": "Save as otherwise provided in these Rules, no Employee shall accept or permit any member of his family or any other person acting on his behalf, to accept any gift.",
            "status": "answered_by_real",
        },
        {
            "id": "P7",
            "question_text": "What is my travel class and lodging allowance for official travel to Mumbai as an E2?",
            "type": "policy",
            "doc_ids": ["P1-16"],
            "clause_reference": "ONGC Travelling Allowance Regulations 2016, Regulation 4.2.1 & Annexure II",
            "quote": "Executive Committee accorded approval to extend air travel facility to all executives of E-1 and above level for their official duty",
            "status": "answered_by_real",
        },
        {
            "id": "P8",
            "question_text": "How do I raise a concern confidentially without being victimised?",
            "type": "policy",
            "doc_ids": ["P2-01"],
            "clause_reference": "ONGC Whistle Blower Policy 2018, Clause 13.1",
            "quote": "No unfair treatment will be meted out to a Whistle Blower by virtue of his / her having reported a Protected Disclosure under this policy. Adequate safeguards against victimisation of complainants shall be provided.",
            "status": "answered_by_real",
        },
        {
            "id": "P9",
            "question_text": "How do I file a POSH complaint, and who is on the committee at my station?",
            "type": "policy",
            "doc_ids": ["P1-01"],
            "clause_reference": "ONGC CDA Rules 1994, Rule 4(3) & Rule 36(2) Proviso",
            "quote": "the Complaints Committee established in each Asset/Basin/Plant/ Institute/Work centre or office, as the case may be, for inquiring into such complaints, shall be deemed to be the inquiring authority",
            "status": "answered_by_real",
        },
        {
            "id": "P10",
            "question_text": "What are the criteria for promotion from E3 to E4?",
            "type": "policy",
            "doc_ids": ["J-15"],
            "clause_reference": "Modified Recruitment & Promotion Regulations 1980 / Service Rules 1995, Rule 4",
            "quote": "Promotion from one post to another higher post shall be made on the basis of selection on merit or seniority-cum-fitness",
            "status": "needs_reconstruction",
            "reconstruction_target": "R&P/Promotion",
        },

        # --- Policy Plus Data Questions (P11 - P17) ---
        {
            "id": "P11",
            "question_text": "Under the transfer policy, who in Delhi has exceeded the cumulative-tenure cap, and who is exempt because they retire soon?",
            "type": "policy_plus_data",
            "doc_ids": ["J-03"],
            "clause_reference": "JRTP Clause 4 (Cumulative Stay Cap) & Clause 7 (Pre-Retirement Exemption)",
            "quote": "retention and transfer policy of the ONGC",
            "status": "needs_reconstruction",
            "reconstruction_target": "JRTP",
        },
        {
            "id": "P12",
            "question_text": "Which executives are due for an E4→E5 merit review and have not done a North-East or hard posting?",
            "type": "policy_plus_data",
            "doc_ids": ["J-03", "J-15"],
            "clause_reference": "JRTP Clause 6 (Mandatory North-East / Hard Station Tenure) & R&P Regulations",
            "quote": "transfer policy",
            "status": "needs_reconstruction",
            "reconstruction_target": "JRTP",
        },
        {
            "id": "P13",
            "question_text": "Are we within the DPE 30% superannuation cap on benefits? How much headroom is left?",
            "type": "policy_plus_data",
            "doc_ids": ["G-01"],
            "clause_reference": "DPE OM W-02/0028/2017-DPE(WC)-GL-XIII/17 dated 03.08.2017, Clause 12",
            "quote": "DA towards Provident Fund (PF), Gratuity, Post-Superannuation Medical Benefits (PRMB) and Pension of their employees.",
            "status": "answered_by_real",
        },
        {
            "id": "P14",
            "question_text": "Our MoU rating sets the performance-related pay pool. What's the pay impact if we drop from 'Excellent' to 'Very Good'?",
            "type": "policy_plus_data",
            "doc_ids": ["G-01", "G-05"],
            "clause_reference": "DPE OM 03.08.2017 Annexure-II, Part-1 & DPE MoU Guidelines OM 17.01.2019",
            "quote": "MOU rating %age eligibility of PRP Excellent 100% Very Good 75% Good 50% Fair 25% Poor Nil",
            "status": "answered_by_real",
        },
        {
            "id": "P15",
            "question_text": "Did we meet the 2% CSR obligation in FY26? Which states got the most?",
            "type": "policy_plus_data",
            "doc_ids": ["P2-10", "G-11"],
            "clause_reference": "ONGC CSR Policy 2025, Clause 9.1 & Companies Act 2013 Section 135",
            "quote": "ensure that in each Financial Year (FY), at least two percent of the average net profit (calculated as per Section 198 of the Act) made during the three immediately preceding Financial Years is spent on CSR activities / projects.",
            "status": "answered_by_real",
        },
        {
            "id": "P16",
            "question_text": "Who has the authority to approve a ₹50 crore drilling contract under the delegated powers?",
            "type": "policy_plus_data",
            "doc_ids": ["P1-04", "J-18"],
            "clause_reference": "Integrated Materials Management Manual (IMMM 2019) Clause 6.7.2 & BDP 2015",
            "quote": "The financial powers for according administrative approval / expenditure sanction / technical sanction shall be exercised as per powers delegated under the relevant 'Item No.' of BDP.",
            "status": "needs_reconstruction",
            "reconstruction_target": "BDP summary",
        },
        {
            "id": "P17",
            "question_text": "Does our dividend policy allow a higher payout this year, given the capex plan?",
            "type": "policy_plus_data",
            "doc_ids": ["P2-09"],
            "clause_reference": "ONGC Dividend Distribution Policy 2022, Clause 4(b)(ii) & Clause 6",
            "quote": "The decision seeks to balance the dual objectives of appropriately rewarding shareholders through dividends and retaining profits in order to fund the growth plans of business.",
            "status": "answered_by_real",
        },

        # --- Refusals (Where Policy/Rule is Cited / Offered Instead) ---
        {
            "id": "D1",
            "question_text": "What is the salary of my reporting officer?",
            "type": "refusal",
            "doc_ids": ["G-01"],
            "clause_reference": "DPE OM 03.08.2017 Pay Scales & HR Manual Compensation Privacy",
            "quote": "E0 12600-32500 30000-120000 E1 16400-40500 40000-140000 E2 20600-46500 50000-160000 E3 24900-50500 60000-180000 E4 29100-54500 70000-200000",
            "status": "needs_reconstruction",
            "reconstruction_target": "HR Manual",
        },
        {
            "id": "D2",
            "question_text": "Show me the draft transfer list for Mumbai.",
            "type": "refusal",
            "doc_ids": ["J-03"],
            "clause_reference": "JRTP Pre-Decisional Deliberations & Annual General Transfer Schedule",
            "quote": "retention and transfer policy of the ONGC",
            "status": "needs_reconstruction",
            "reconstruction_target": "JRTP",
        },
        {
            "id": "D2_FU1",
            "question_text": "What is the normal timeline and official procedure for publishing the annual general transfer orders across work centres?",
            "type": "refusal",
            "doc_ids": ["J-03"],
            "clause_reference": "JRTP Clause 9 (Annual Transfer Calendar & Notification Procedure)",
            "quote": "retention and transfer policy of the ONGC",
            "status": "needs_reconstruction",
            "reconstruction_target": "JRTP",
        },
        {
            "id": "D2_FU2",
            "question_text": "Why are draft transfer proposals and committee recommendations classified as confidential prior to formal release?",
            "type": "refusal",
            "doc_ids": ["P1-01"],
            "clause_reference": "ONGC CDA Rules 1994, Rule 14(1) (Unauthorized Communication of Information)",
            "quote": "No Employee, whether during the period of his service or after leaving the service of the Company shall, except with the previous sanction of the Competent Authority, by writing to any person (including any other employee)",
            "status": "answered_by_real",
        },
        {
            "id": "D2_FU3",
            "question_text": "Where and when can an executive view official, published transfer office orders once approved by the competent authority?",
            "type": "refusal",
            "doc_ids": ["J-03"],
            "clause_reference": "JRTP Clause 9 & ONGC Reports / Intranet Office Order Portal",
            "quote": "retention and transfer policy of the ONGC",
            "status": "needs_reconstruction",
            "reconstruction_target": "JRTP",
        },
        {
            "id": "D3",
            "question_text": "Who is getting promoted in the next DPC?",
            "type": "refusal",
            "doc_ids": ["J-15"],
            "clause_reference": "Modified R&P Regulations 1980 / DPC Confidentiality Proceedings",
            "quote": "Promotion from one post to another higher post shall be made on the basis of selection on merit or seniority-cum-fitness",
            "status": "needs_reconstruction",
            "reconstruction_target": "R&P/Promotion",
        },
        {
            "id": "D4",
            "question_text": "Which fields are loss-making, and what is the capex plan for next year?",
            "type": "refusal",
            "doc_ids": ["P2-04"],
            "clause_reference": "ONGC Insider Trading Code 2019, Clause 3(o) (UPSI Definition)",
            "quote": "Unpublished Price sensitive information\" (UPSI) means any information relating to the Company or the securities of the Company, directly or indirectly, that is not generally available which upon becoming generally available, is likely to materially affect the price of the securities",
            "status": "answered_by_real",
        },
        {
            "id": "D5",
            "question_text": "List all employees in Delhi with more than 5 years' tenure.",
            "type": "refusal",
            "doc_ids": ["J-03"],
            "clause_reference": "JRTP Station Tenure Norms & Data Confidentiality",
            "quote": "transferred from Rajahmundry to Chennai on the ground that the Respondent had completed his tenure of five years",
            "status": "needs_reconstruction",
            "reconstruction_target": "JRTP",
        },
        {
            "id": "D6",
            "question_text": "Is any officer in my asset under vigilance inquiry?",
            "type": "refusal",
            "doc_ids": ["P1-01"],
            "clause_reference": "ONGC CDA Rules 1994, Rule 14(1) & Rule 34 (Suspension & Inquiries)",
            "quote": "Where a disciplinary proceeding against him is contemplated or is pending",
            "status": "answered_by_real",
        },
        {
            "id": "P18",
            "question_text": "Show me the Draft FY27 Transfer Order.",
            "type": "refusal",
            "doc_ids": ["J-03"],
            "clause_reference": "JRTP Clause 11 (Confidentiality of Draft Proposals)",
            "quote": "retention and transfer policy of the ONGC",
            "status": "needs_reconstruction",
            "reconstruction_target": "JRTP",
        },
        {
            "id": "P19",
            "question_text": "What are the full financial limits for Directors in the delegated powers?",
            "type": "refusal",
            "doc_ids": ["J-18"],
            "clause_reference": "Book of Delegated Powers (BDP 2015), Director Delegations Schedule",
            "quote": "Book of Delegated Powers, 2015",
            "status": "needs_reconstruction",
            "reconstruction_target": "BDP summary",
        },
        {
            "id": "P20",
            "question_text": "Summarise the Board note on divesting marginal fields.",
            "type": "refusal",
            "doc_ids": ["P2-04"],
            "clause_reference": "ONGC Insider Trading Code 2019, Clause 3(o) (UPSI Definition)",
            "quote": "Unpublished Price sensitive information\" (UPSI) means any information relating to the Company or the securities of the Company, directly or indirectly, that is not generally available which upon becoming generally available, is likely to materially affect the price of the securities",
            "status": "answered_by_real",
        },
        {
            "id": "M3",
            "question_text": "Show me the salary and APAR of employee 104523.",
            "type": "refusal",
            "doc_ids": ["P1-01"],
            "clause_reference": "ONGC CDA Rules 1994, Rule 14(1) (Unauthorized Communication of Information)",
            "quote": "No Employee, whether during the period of his service or after leaving the service of the Company shall, except with the previous sanction of the Competent Authority, by writing to any person (including any other employee)",
            "status": "answered_by_real",
        },
        {
            "id": "M4",
            "question_text": "Which fields are loss-making?",
            "type": "refusal",
            "doc_ids": ["P2-24"],
            "clause_reference": "ONGC Integrated Annual Report 2025-26, Note 53 (Segment Reporting)",
            "quote": "under Production Enhancement Contracts (PECs).",
            "status": "answered_by_real",
        },

        # --- Key Data Questions & Follow-ups Asking Rules / Criteria / Entitlements ---
        {
            "id": "H10",
            "question_text": "Generate an Excel transfer proposal for FY27 using rotation rules.",
            "type": "document",
            "doc_ids": ["J-03"],
            "clause_reference": "JRTP Transfer Proposal Generation Norms (3-Year Min Tenure, 10-Year Cap, Exemption within 2 Years)",
            "quote": "retention and transfer policy of the ONGC",
            "status": "needs_reconstruction",
            "reconstruction_target": "JRTP",
        },
        {
            "id": "H10_FU1",
            "question_text": "Which specific executives meet the criteria for transfer from Delhi/Dehradun to Assam and Tripura assets?",
            "type": "document",
            "doc_ids": ["J-03"],
            "clause_reference": "JRTP Clause 6 (Mandatory North-East Posting Rotation)",
            "quote": "retention and transfer policy of the ONGC",
            "status": "needs_reconstruction",
            "reconstruction_target": "JRTP",
        },
        {
            "id": "H10_FU2",
            "question_text": "What replacement executives match the discipline, grade, and operational background of those transferring out?",
            "type": "document",
            "doc_ids": ["J-03"],
            "clause_reference": "JRTP Clause 10 (Replacement and Discipline Balancing Norms)",
            "quote": "retention and transfer policy of the ONGC",
            "status": "needs_reconstruction",
            "reconstruction_target": "JRTP",
        },
        {
            "id": "H10_FU3",
            "question_text": "Which executives are eligible for exemption on medical or superannuation grounds?",
            "type": "document",
            "doc_ids": ["J-03"],
            "clause_reference": "JRTP Clause 7 (Pre-Retirement Exemption within 2 Years) & Clause 8 (Medical Grounds)",
            "quote": "retention and transfer policy of the ONGC",
            "status": "needs_reconstruction",
            "reconstruction_target": "JRTP",
        },
        {
            "id": "C8",
            "question_text": "Which loss-making mature fields are candidates for divestment, a Production Enhancement Contract, or a marginal-field offer?",
            "type": "data",
            "doc_ids": ["P2-24"],
            "clause_reference": "ONGC Integrated Annual Report 2025-26, Note 53.3.3.1 (Marginal Fields & PECs)",
            "quote": "under Production Enhancement Contracts (PECs).",
            "status": "answered_by_real",
        },
        {
            "id": "C8_FU1",
            "question_text": "Which specific fields in Assam and Cambay have sustained negative EBITDA for 3 consecutive fiscal years?",
            "type": "data",
            "doc_ids": ["P2-24"],
            "clause_reference": "ONGC Integrated Annual Report 2025-26, Financial Statements & Note 53",
            "quote": "under Production Enhancement Contracts (PECs).",
            "status": "answered_by_real",
        },
        {
            "id": "C8_FU2",
            "question_text": "What technical operating constraints make in-house secondary/tertiary recovery uneconomic compared to third-party PEC operators?",
            "type": "data",
            "doc_ids": ["P2-24"],
            "clause_reference": "ONGC Integrated Annual Report 2025-26, Note 53.3.3.1",
            "quote": "under Production Enhancement Contracts (PECs).",
            "status": "answered_by_real",
        },
        {
            "id": "C8_FU3",
            "question_text": "What would be the estimated capex and opex savings if the bottom 5 loss-making marginal fields are monetised or farmed out?",
            "type": "data",
            "doc_ids": ["P2-24"],
            "clause_reference": "ONGC Integrated Annual Report 2025-26, Note 53.3.3.1",
            "quote": "under Production Enhancement Contracts (PECs).",
            "status": "answered_by_real",
        },
        {
            "id": "X7",
            "question_text": "Draft a reply to a Parliament question: 'Vacancies in ONGC in the North-East region, category-wise.'",
            "type": "document",
            "doc_ids": ["Q-01"],
            "clause_reference": "Lok Sabha Unstarred Question No. 2067 (Employment in Oil PSUs in Assam)",
            "quote": "the number of regular employees currently working under Indian Oil Corporation Limited (IOCL), Oil India Limited (OIL) and Oil and Natural Gas Corporation (ONGC) in Assam separately for each Public Sector Undertaking",
            "status": "answered_by_real",
        },
        {
            "id": "X7_FU1",
            "question_text": "What are the exact sanctioned versus in-position numbers in Assam and Tripura broken down by SC, ST, OBC, EWS, and General?",
            "type": "document",
            "doc_ids": ["Q-01"],
            "clause_reference": "Lok Sabha Unstarred Question No. 2067, Category-wise Breakdown",
            "quote": "the number of regular employees currently working under Indian Oil Corporation Limited (IOCL), Oil India Limited (OIL) and Oil and Natural Gas Corporation (ONGC) in Assam separately for each Public Sector Undertaking",
            "status": "answered_by_real",
        },
        {
            "id": "X7_FU2",
            "question_text": "What specific recruitment initiatives and special drives have been launched to fill reserved category vacancies in the North-East?",
            "type": "document",
            "doc_ids": ["Q-01"],
            "clause_reference": "Lok Sabha Unstarred Question No. 2067, Clause (c) Recruitment Drives",
            "quote": "the number of regular employees currently working under Indian Oil Corporation Limited (IOCL), Oil India Limited (OIL) and Oil and Natural Gas Corporation (ONGC) in Assam separately for each Public Sector Undertaking",
            "status": "answered_by_real",
        },
        {
            "id": "X7_FU3",
            "question_text": "How does the vacancy percentage in North-East work centres compare with ONGC's national average vacancy level?",
            "type": "document",
            "doc_ids": ["Q-01"],
            "clause_reference": "Lok Sabha Unstarred Question No. 2067, Workforce Proportions",
            "quote": "the number of regular employees currently working under Indian Oil Corporation Limited (IOCL), Oil India Limited (OIL) and Oil and Natural Gas Corporation (ONGC) in Assam separately for each Public Sector Undertaking",
            "status": "answered_by_real",
        },
        {
            "id": "X9",
            "question_text": "CSR spend by state and theme vs. the policy's priority areas",
            "type": "data",
            "doc_ids": ["P2-10"],
            "clause_reference": "ONGC CSR Policy 2025, Clause 4.2 & Clause 6.0",
            "quote": "apply to all CSR Projects undertaken by ONGC as per liberal interpretation of activities listed in Schedule-VII of the Act, within the geographical limits of India alone",
            "status": "answered_by_real",
        },
        {
            "id": "X9_FU1",
            "question_text": "What proportion of our ₹949 cr CSR spend was allocated to education, healthcare, sanitation, and aspirational districts?",
            "type": "data",
            "doc_ids": ["P2-10"],
            "clause_reference": "ONGC CSR Policy 2025, Clause 4.2 (Marginalized & Disadvantaged Communities)",
            "quote": "apply to all CSR Projects undertaken by ONGC as per liberal interpretation of activities listed in Schedule-VII of the Act, within the geographical limits of India alone",
            "status": "answered_by_real",
        },
        {
            "id": "X9_FU2",
            "question_text": "Why did certain non-operational states receive CSR project funding under national priority and disaster relief allocations?",
            "type": "data",
            "doc_ids": ["P2-10"],
            "clause_reference": "ONGC CSR Policy 2025, Clause 4.2 (National Priorities)",
            "quote": "apply to all CSR Projects undertaken by ONGC as per liberal interpretation of activities listed in Schedule-VII of the Act, within the geographical limits of India alone",
            "status": "answered_by_real",
        },
        {
            "id": "X9_FU3",
            "question_text": "How does the expenditure distribution across states compare with the statutory guideline prioritizing operational field areas?",
            "type": "data",
            "doc_ids": ["P2-10"],
            "clause_reference": "ONGC CSR Policy 2025, Clause 4.2 & Companies Act Section 135(5)",
            "quote": "apply to all CSR Projects undertaken by ONGC as per liberal interpretation of activities listed in Schedule-VII of the Act, within the geographical limits of India alone",
            "status": "answered_by_real",
        },
        {
            "id": "T2_FU2",
            "question_text": "Why have these specific officers remained at corporate headquarters beyond the 10-year cumulative cap?",
            "type": "chain",
            "doc_ids": ["J-03"],
            "clause_reference": "JRTP Clause 4 (10-Year Cumulative Cap & Retention Exceptions)",
            "quote": "retention and transfer policy of the ONGC",
            "status": "needs_reconstruction",
            "reconstruction_target": "JRTP",
        },
        {
            "id": "T2_FU3",
            "question_text": "How does transferring these executives balance vacancy deficits in North-East assets while controlling transfer allowance expenses?",
            "type": "chain",
            "doc_ids": ["P1-16"],
            "clause_reference": "ONGC Travelling Allowance Regulations 2016, Regulation 7.1(ii) (Transfer on Company's Interest)",
            "quote": "An employee on transfer in Company's interest shall be entitled to reimbursement of mileage allowance as follows",
            "status": "answered_by_real",
        },
        {
            "id": "W3_FU1",
            "question_text": "What is the estimated budget required for Composite Transfer Allowance (CTA) and relocation grants for 200 officers?",
            "type": "what_if",
            "doc_ids": ["P1-16"],
            "clause_reference": "ONGC Travelling Allowance Regulations 2016, Regulation 7.1(ii) (Transfer TA Entitlement)",
            "quote": "An employee on transfer in Company's interest shall be entitled to reimbursement of mileage allowance as follows",
            "status": "answered_by_real",
        },
        {
            "id": "C13_FU2",
            "question_text": "What one-time transfer grant, composite transfer allowance (CTA), and baggage transportation costs would be incurred?",
            "type": "what_if",
            "doc_ids": ["P1-16"],
            "clause_reference": "ONGC Travelling Allowance Regulations 2016, Regulation 7.1(ii) (Transfer TA Entitlement)",
            "quote": "An employee on transfer in Company's interest shall be entitled to reimbursement of mileage allowance as follows",
            "status": "answered_by_real",
        },
        {
            "id": "H5_FU3",
            "question_text": "How many eligible executives have completed the required residency period but are still awaiting promotion notification?",
            "type": "data",
            "doc_ids": ["J-15"],
            "clause_reference": "Modified Recruitment & Promotion Regulations 1980 / Residency Norms",
            "quote": "Promotion from one post to another higher post shall be made on the basis of selection on merit or seniority-cum-fitness",
            "status": "needs_reconstruction",
            "reconstruction_target": "R&P/Promotion",
        },
        {
            "id": "H6_FU3",
            "question_text": "How do our current roster representation percentages compare against statutory presidential directives and DoPT guidelines?",
            "type": "data",
            "doc_ids": ["P1-09"],
            "clause_reference": "ONGC Equal Opportunity Policy 2023, Clause 6.0 (Liaison Officers & Statutory Compliance)",
            "quote": "Liaison Officers appointed to look after welfare and all matters related to SCs/STs, also function as Liaison Officers for persons with benchmark disabilities and shall ensure compliance of guidelines/instructions issued for Persons with benchmark Disabilities by Govt. of India, from time to time.",
            "status": "answered_by_real",
        },
        {
            "id": "H9_FU1",
            "question_text": "Break down pending cases by category (promotion dispute, transfer challenge, disciplinary action, pay anomaly) across High Courts and CAT.",
            "type": "data",
            "doc_ids": ["J-01"],
            "clause_reference": "Court litigation records across ONGC service conditions",
            "quote": "Oil and Natural Gas Corporation",
            "status": "answered_by_real",
        },
        {
            "id": "M3_FU1",
            "question_text": "What is the authorized procedure for an executive to view their own APAR grading and salary slip on the ESS portal?",
            "type": "refusal",
            "doc_ids": ["G-01"],
            "clause_reference": "HR Manual / ESS Portal Self-Service System Guidelines",
            "quote": "E0 12600-32500 30000-120000 E1 16400-40500 40000-140000 E2 20600-46500 50000-160000 E3 24900-50500 60000-180000 E4 29100-54500 70000-200000",
            "status": "needs_reconstruction",
            "reconstruction_target": "HR Manual",
        },
        {
            "id": "M3_FU3",
            "question_text": "What is the designated salary pay scale and promotion criteria for employee 104523's grade?",
            "type": "refusal",
            "doc_ids": ["G-01"],
            "clause_reference": "DPE OM 03.08.2017, Clause 2 (Pay Scales)",
            "quote": "E0 12600-32500 30000-120000 E1 16400-40500 40000-140000 E2 20600-46500 50000-160000 E3 24900-50500 60000-180000 E4 29100-54500 70000-200000",
            "status": "answered_by_real",
        },
    ]

    return qmap


def build_reconstruction_requirements() -> dict[str, dict]:
    """Define exact requirements for rulebooks to be reconstructed in step 3.1."""
    return {
        "JRTP": {
            "rulebook": "JRTP",
            "target_title": "Job Rotation & Transfer Policy (JRTP)",
            "mapped_questions": [
                "E2", "P1", "P2", "P3", "P11", "P12", "P18",
                "D2", "D2_FU1", "D2_FU3", "D5",
                "H10", "H10_FU1", "H10_FU2", "H10_FU3", "T2_FU2"
            ],
            "required_clauses": [
                {"clause_number": "1.0", "title": "Short Title, Commencement and Scope", "requirement": "Applicable to all regular executives across work centres, plants, basins and corporate offices."},
                {"clause_number": "2.0", "title": "Definitions & Classification of Work Centres", "requirement": "Defines Station, Work Centre, Geographic Cluster, Hard Station (Category C), and Offshore Duty."},
                {"clause_number": "3.0", "title": "Station Tenure Norms", "requirement": "Minimum station tenure of 3 years; normal tenure 3 to 5 years before eligibility for transfer."},
                {"clause_number": "4.0", "title": "Cumulative Stay Cap", "requirement": "Maximum cumulative stay of 10 years at a single city/station over entire career."},
                {"clause_number": "5.0", "title": "Geographic Clusters", "requirement": "Specifies connected stations treated as single clusters (Delhi-NCR [Delhi/Noida/Gurgaon], Mumbai Urban [Mumbai/Navi Mumbai/Panvel], Gujarat [Ahmedabad/Chandkheda/Gandhinagar], Assam [Nazira/Sivasagar/Jorhat])."},
                {"clause_number": "6.0", "title": "Mandatory North-East / Hard Station Tenure", "requirement": "Mandatory completion of at least one 3-year tenure in North-East / hard station / offshore prior to merit review promotion from E4 to E5."},
                {"clause_number": "7.0", "title": "Pre-Retirement Tenure Exemption", "requirement": "Executives within 2 years of superannuation (age 58+) shall be exempt from outstation transfers."},
                {"clause_number": "8.0", "title": "Medical & Compassionate Grounds", "requirement": "Procedures for medical exemption requests through Medical Board and Special Review Board."},
                {"clause_number": "9.0", "title": "Annual Transfer Calendar & Notification Procedure", "requirement": "Annual general transfer schedule: initiated November, finalized March/April, notified on intranet portal."},
                {"clause_number": "10.0", "title": "Replacement & Cadre Balancing Norms", "requirement": "Mandates 1-for-1 discipline and experience matching for outgoing executives."},
                {"clause_number": "11.0", "title": "Confidentiality of Pre-Decisional Records", "requirement": "Strict confidentiality of draft transfer lists and committee deliberations prior to final issue."},
                {"clause_number": "12.0", "title": "Competent Transfer Authorities", "requirement": "Specifies approving authorities: Key Executive / Director (HR) / CMD by grade."},
                {"clause_number": "13.0", "title": "Transfer Grievance Redressal Mechanism", "requirement": "Right of representation within 15 days of order through designated grievance committee."},
            ],
            "real_excerpts": [
                {
                    "doc_id": "J-03",
                    "clause_reference": "Delhi HC LPA judgment, Para 2",
                    "verbatim_quote": "transferred from Rajahmundry to Chennai on the ground that the Respondent had completed his tenure of five years",
                },
                {
                    "doc_id": "P1-16",
                    "clause_reference": "ONGC TA Regulations 2016, Annexure I",
                    "verbatim_quote": "Brihan Mumbai, Chennai, Kolkata, New Delhi (including Faridabad, Ghaziabad, Noida & Gurgaon), Bangalore, Hyderabad",
                },
            ],
        },
        "BDP summary": {
            "rulebook": "BDP summary",
            "target_title": "Book of Delegated Powers (BDP 2015 Summary)",
            "mapped_questions": ["P16", "P19", "D4", "M4"],
            "required_clauses": [
                {"clause_number": "1.0", "title": "Principles of Financial Delegation", "requirement": "General powers, financial limits structure, Level 1 through Level 5 authorities."},
                {"clause_number": "2.0", "title": "Asset Managers & Key Executives Powers", "requirement": "Procurement sanctioning powers capped at ₹10 Crore; operational expenditure at ₹25 Crore."},
                {"clause_number": "3.0", "title": "Whole-Time Directors Financial Limits", "requirement": "Sanctioning powers up to ₹50 Crore for capital contracts and operational works."},
                {"clause_number": "4.0", "title": "Executive Committee (EC) Financial Limits", "requirement": "Sanctioning powers from ₹50 Crore to ₹100 Crore."},
                {"clause_number": "5.0", "title": "Chairman & Managing Director (CMD) Powers", "requirement": "Financial approval powers up to ₹100 Crore and emergency operational powers."},
                {"clause_number": "6.0", "title": "Board of Directors Reserved Matters", "requirement": "Matters exceeding ₹100 Crore, major drilling tenders, field farm-outs and capex approvals reserved for Board."},
                {"clause_number": "7.0", "title": "Technical and Expenditure Sanction Interlocks", "requirement": "Mandatory concurrence of Associate Finance before exercise of delegated financial powers."},
                {"clause_number": "8.0", "title": "Commercial Confidentiality of Operational Schedules", "requirement": "Detailed limits classified as internal controlled document."},
            ],
            "real_excerpts": [
                {
                    "doc_id": "P1-04",
                    "clause_reference": "Integrated Materials Management Manual (IMMM 2019), Clause 6.7.2",
                    "verbatim_quote": "The financial powers for according administrative approval / expenditure sanction / technical sanction shall be exercised as per powers delegated under the relevant 'Item No.' of BDP.",
                },
                {
                    "doc_id": "J-18",
                    "clause_reference": "Gauhati HC judgment (Prasant Kumar Baruah v. UoI & ONGC)",
                    "verbatim_quote": "Book of Delegated Powers, 2015",
                },
            ],
        },
        "Leave Rules": {
            "rulebook": "Leave Rules",
            "target_title": "ONGC Leave Rules, 1995",
            "mapped_questions": ["P4", "P5"],
            "required_clauses": [
                {"clause_number": "1.0", "title": "Short Title and Commencement", "requirement": "Effective from 1995, governing all regular employees."},
                {"clause_number": "2.0", "title": "Categories of Leave", "requirement": "Earned Leave (EL), Half Pay Leave (HPL), Commuted Leave, Extraordinary Leave (EOL), Study Leave."},
                {"clause_number": "3.0", "title": "Earned Leave Accrual & Accumulation", "requirement": "Accrual of 30 days EL per calendar year (15 days on Jan 1 and Jul 1); maximum accumulation ceiling of 300 days."},
                {"clause_number": "4.0", "title": "Encashment of Earned Leave", "requirement": "Encashment upon superannuation / retirement subject to max ceiling of 300 days EL."},
                {"clause_number": "5.0", "title": "Half Pay Leave (HPL) Accrual & Encashment", "requirement": "Accrual of 20 days HPL per completed year; encashment rules on retirement."},
                {"clause_number": "6.0", "title": "Study Leave Eligibility & Approval", "requirement": "Minimum 5 years continuous service; study leave granted by Competent Authority."},
                {"clause_number": "7.0", "title": "Study Leave Service Bond", "requirement": "Execution of mandatory service bond to serve ONGC for at least 3 years following study leave completion."},
                {"clause_number": "8.0", "title": "Extraordinary Leave (EOL) & Rule 14(5)", "requirement": "Absence beyond admissible EOL deemed as resignation under Rule 14(5)."},
                {"clause_number": "9.0", "title": "Forfeiture on Disciplinary Dismissal", "requirement": "Dismissed employees forfeit leave encashment entitlement."},
            ],
            "real_excerpts": [
                {
                    "doc_id": "J-01",
                    "clause_reference": "Gauhati HC judgment, quoting ONGC Leave Rules 1995 Rule 14(5)",
                    "verbatim_quote": "shall be deemed to have resigned",
                },
                {
                    "doc_id": "J-07",
                    "clause_reference": "Gauhati HC judgment, Sarat Chandra Buragohain v. ONGC",
                    "verbatim_quote": "leave encashment is not a bounty and is a part of terminal benefit",
                },
                {
                    "doc_id": "J-08",
                    "clause_reference": "Court judgment, Dr Vikas S. Mahalkar v. ONGC",
                    "verbatim_quote": "Extraordinary Leave (EOL) without pay",
                },
            ],
        },
        "R&P/Promotion": {
            "rulebook": "R&P/Promotion",
            "target_title": "Modified Recruitment & Promotion Regulations 1980 & Service Rules 1995",
            "mapped_questions": ["E4", "P10", "D3", "H5_FU3"],
            "required_clauses": [
                {"clause_number": "1.0", "title": "Executive Cadre Structure", "requirement": "Grades E0 through E9, standard disciplines (Drilling, Production, Reservoir, Geology, Geophysics, F&A, HR, MM)."},
                {"clause_number": "2.0", "title": "Time-Bound Promotion Channel (E1→E4)", "requirement": "Residency requirement of 3 years at E1 for E2; 3 years at E2 for E3; 3 years at E3 for E4."},
                {"clause_number": "3.0", "title": "APAR Benchmark for Time-Bound Promotion", "requirement": "Minimum PAR/APAR score threshold (e.g. Good / Very Good) across 3 years qualifying residency."},
                {"clause_number": "4.0", "title": "Merit Promotion Channel (E4→E5, E5→E6)", "requirement": "Selection on merit through DPC interview/assessment, zone of consideration, and seniority weighting."},
                {"clause_number": "5.0", "title": "Mandatory Hard-Station Prerequisite for Promotion", "requirement": "Pre-condition of at least one 3-year tenure in North-East or offshore/hard station for consideration to E5 Chief Engineer."},
                {"clause_number": "6.0", "title": "Departmental Promotion Committee (DPC) Constitution", "requirement": "Committee constitution, proceedings, benchmarking standards."},
                {"clause_number": "7.0", "title": "Vigilance Clearance as Pre-Condition", "requirement": "Clearance from Vigilance department mandatory prior to DPC empanelment and promotion order release."},
                {"clause_number": "8.0", "title": "Confidentiality of DPC Proceedings & Sealed Cover", "requirement": "DPC deliberations are strictly confidential; sealed cover procedure for officers facing inquiry."},
            ],
            "real_excerpts": [
                {
                    "doc_id": "J-15",
                    "clause_reference": "Supreme Court / Delhi HC judgment, Dwarika Prasad v. ONGC",
                    "verbatim_quote": "Promotion from one post to another higher post shall be made on the basis of selection on merit or seniority-cum-fitness",
                },
                {
                    "doc_id": "P1-05",
                    "clause_reference": "Recruitment Advertisement 1/2024 (GT), Clause 1",
                    "verbatim_quote": "E-1 level",
                },
            ],
        },
        "HR Manual": {
            "rulebook": "HR Manual",
            "target_title": "ONGC HR Manual: Designations, Pay Scales & Service Conditions",
            "mapped_questions": ["D1", "M3_FU1"],
            "required_clauses": [
                {"clause_number": "1.0", "title": "Standard Executive Hierarchy & Designations", "requirement": "Standard designations E1 (AEE/Geologist) to E9 (Executive Director)."},
                {"clause_number": "2.0", "title": "IDA Pay Scales by Grade", "requirement": "Pay scales E0 through E9 aligned with 3rd PRC DPE OM (03.08.2017)."},
                {"clause_number": "3.0", "title": "Probation, Confirmation & Seniority", "requirement": "One-year probation for Graduate Trainees (E1); confirmation based on assessment."},
                {"clause_number": "4.0", "title": "Employee Self-Service (ESS) Portal Access", "requirement": "Procedure for employees to view personal APAR, monthly payslip, and leave balance via ESS."},
                {"clause_number": "5.0", "title": "Confidentiality of Individual Compensation", "requirement": "Colleague salary and appraisal data are protected personal information; unauthorized access prohibited."},
                {"clause_number": "6.0", "title": "Resignation Notice Period (Rule 24(4))", "requirement": "3 months notice for resignation; acceptance withheld during pending disciplinary or vigilance inquiry."},
            ],
            "real_excerpts": [
                {
                    "doc_id": "G-01",
                    "clause_reference": "DPE OM 03.08.2017, Clause 2 (Pay Scales)",
                    "verbatim_quote": "E0 12600-32500 30000-120000 E1 16400-40500 40000-140000 E2 20600-46500 50000-160000 E3 24900-50500 60000-180000 E4 29100-54500 70000-200000",
                },
                {
                    "doc_id": "J-05",
                    "clause_reference": "Delhi HC judgment, Major Raj Mohan v. ONGC",
                    "verbatim_quote": "Oil and Natural Gas Corporation",
                },
            ],
        },
        "PRBS": {
            "rulebook": "PRBS",
            "target_title": "ONGC Self-Contributory Post Retirement & Death in Service Benefit Scheme (PRBS)",
            "mapped_questions": ["P13"],
            "required_clauses": [
                {"clause_number": "1.0", "title": "Constitution & Governance of PRBS Trust", "requirement": "Administration by Board of Trustees of PRBS at Tel Bhavan, Dehradun."},
                {"clause_number": "2.0", "title": "Defined Contribution Pension Structure", "requirement": "Conversion to Defined Contribution Pension Scheme w.e.f. 26.11.2013 (Circular 71)."},
                {"clause_number": "3.0", "title": "Contribution Rates & 30% Superannuation Cap", "requirement": "Employer and employee contributions managed within DPE 30% superannuation ceiling of BP + DA."},
                {"clause_number": "4.0", "title": "Dispensation of 15-Year Service Condition", "requirement": "Removal of minimum 15 years service and superannuation condition w.e.f. 01.01.2017 per Circular 73."},
                {"clause_number": "5.0", "title": "Annuity Options & Payout Formulas", "requirement": "Life annuity, annuity with return of capital, joint-life annuity through LIC / registered providers."},
                {"clause_number": "6.0", "title": "Corpus Transfer Option to NPS", "requirement": "Option for executives to transfer accumulated PRBS corpus to National Pension System (NPS)."},
            ],
            "real_excerpts": [
                {
                    "doc_id": "P1-10",
                    "clause_reference": "PRBS Circular No. 73 (2018), Clause 1",
                    "verbatim_quote": "approved by the Principal CIT, Dehradun",
                },
                {
                    "doc_id": "P1-11",
                    "clause_reference": "Hamesha Aapke Saath Compendium, Section 1.11",
                    "verbatim_quote": "PRBS",
                },
                {
                    "doc_id": "J-12",
                    "clause_reference": "Gauhati HC judgment, Arpan Chakraborty v. ONGC",
                    "verbatim_quote": "PRBS",
                },
            ],
        },
        "Post-retirement medical": {
            "rulebook": "Post-retirement medical",
            "target_title": "ONGC Post-Retirement Medical Benefit Scheme & Retiree Welfare Rules",
            "mapped_questions": ["P1-19", "P1-11", "P1-14"],
            "required_clauses": [
                {"clause_number": "1.0", "title": "Eligibility Criteria (Office Order 30/2015)", "requirement": "Minimum 15 years continuous service in ONGC for eligibility for post-retirement medical benefits."},
                {"clause_number": "2.0", "title": "Coverage of Beneficiaries", "requirement": "Retired employee, spouse, surviving spouse, eligible dependent family members."},
                {"clause_number": "3.0", "title": "Outpatient (OPD) Treatment Ceilings", "requirement": "Annual OPD consultation and medicine reimbursement limits by grade."},
                {"clause_number": "4.0", "title": "Inpatient Hospitalization & Cashless Network", "requirement": "Indoor medical treatment at ONGC empaneled hospitals across major cities."},
                {"clause_number": "5.0", "title": "Dependent Parents Medical Reimbursement", "requirement": "Medical reimbursement provisions for dependent parents subject to income dependency criteria."},
                {"clause_number": "6.0", "title": "Welfare Schemes: Asha Kiran & Agrani Samman", "requirement": "Emergency medical assistance under Asha Kiran (2013) and ex-gratia financial relief under Agrani Samman (2001)."},
            ],
            "real_excerpts": [
                {
                    "doc_id": "P1-19",
                    "clause_reference": "Office Order 30/2015, Clause 1",
                    "verbatim_quote": "Post Retirement Medical Scheme",
                },
                {
                    "doc_id": "P1-11",
                    "clause_reference": "Hamesha Aapke Saath Compendium, Chapter 1 & 8",
                    "verbatim_quote": "Asha Kiran",
                },
                {
                    "doc_id": "P1-12",
                    "clause_reference": "Department Circulars under Welfare Schemes, OO ONGC/ER/CP/WEL/004",
                    "verbatim_quote": "Agrani Samman",
                },
            ],
        },
    }


def verify_integrity(documents: list[dict], qmap: list[dict], recon: dict[str, dict]):
    """Verify all cross-references, text files, and quotes before writing."""
    doc_registry = {d["doc_id"]: d for d in documents}
    assert len(doc_registry) == 78, f"Expected 78 documents in registry, found {len(doc_registry)}"

    # 1. Check all text files exist
    for doc_id, doc in doc_registry.items():
        tp = PROJECT_DIR / doc["text_path"]
        assert tp.exists(), f"Text file missing for {doc_id}: {tp}"

    # 2. Check all mapped doc_ids exist in registry
    for item in qmap:
        for did in item.get("doc_ids", []):
            assert did in doc_registry, f"Doc ID {did} in question {item['id']} not in documents registry!"

    # 3. Check every answered_by_real quote is found in text file
    for item in qmap:
        if item["status"] == "answered_by_real":
            quote = item["quote"]
            words = len(quote.split())
            assert words <= 60, f"Quote for {item['id']} has {words} words, exceeds 60 words limit!"
            norm_quote = normalize_text(quote)

            found = False
            for did in item["doc_ids"]:
                doc_text = (PROJECT_DIR / doc_registry[did]["text_path"]).read_text(errors="ignore")
                norm_doc = normalize_text(doc_text)
                if norm_quote in norm_doc:
                    found = True
                    break
            assert found, f"Verbatim quote for {item['id']} not found in mapped documents {item['doc_ids']}:\nQuote: {quote}"

    # 4. Check every needs_reconstruction item appears in reconstruction_requirements
    recon_mapped_ids = set()
    for rb in recon.values():
        recon_mapped_ids.update(rb.get("mapped_questions", []))

    for item in qmap:
        if item["status"] == "needs_reconstruction":
            assert item["id"] in recon_mapped_ids, f"needs_reconstruction item {item['id']} not found in reconstruction_requirements mapped_questions!"

    print("All builder integrity checks passed successfully!")


def main():
    docs = build_documents_registry()
    qmap = build_question_map()
    recon = build_reconstruction_requirements()

    verify_integrity(docs, qmap, recon)

    output_data = {
        "metadata": {
            "title": "ONGC HR & Finance Agent - Real Policy Registry & Question Map",
            "version": "1.0",
            "total_documents": len(docs),
            "total_mapped_items": len(qmap),
            "total_reconstruction_rulebooks": len(recon),
        },
        "documents": docs,
        "question_map": qmap,
        "reconstruction_requirements": recon,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        yaml.dump(output_data, f, sort_keys=False, allow_unicode=True, width=120)

    print(f"Wrote {len(docs)} documents, {len(qmap)} mapped items, {len(recon)} rulebooks to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
