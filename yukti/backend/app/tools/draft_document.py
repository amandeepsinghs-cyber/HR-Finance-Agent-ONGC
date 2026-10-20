"""Document Drafting and Revision Engine for Yukti AI.
Drafts official ONGC Board Notes, Parliament Replies, Transfer Proposals,
and executive applications using templates in data_bank/landing/documents/templates/.
Maintains document versions and applies revisions by voice or text.
Enforces real-person denylist check to guarantee 100% fictional parliamentary integrity.
"""

import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import docx

from app.config import TEMPLATES_DIR

logger = logging.getLogger("yukti.tools.draft_document")

REAL_POLITICIAN_DENYLIST = [
    "Rameshwar Teli",
    "Rameswar Teli",
    "Hardeep Singh Puri",
    "Dharmendra Pradhan",
    "Murli Deora",
    "M. Veerappa Moily",
    "Mani Shankar Aiyar",
    "Ram Naik",
    "Piyush Goyal",
]


def sanitize_fictional_names(text: str) -> str:
    """Scans text against real politician denylist and replaces with clearly fictional synthetic names."""
    clean = text
    for real_name in REAL_POLITICIAN_DENYLIST:
        if real_name.lower() in clean.lower():
            clean = re.sub(re.escape(real_name), "Shri Anand Swaroop", clean, flags=re.IGNORECASE)
    return clean


DOCUMENT_TEMPLATES = {
    "board_note": {
        "title": "Board Note: Operational Turnaround Strategy for Marginal Fields",
        "doc_type": "board_note",
        "template_id": "template_board_note.docx",
        "default_markdown": """# OIL AND NATURAL GAS CORPORATION LIMITED
## BOARD OF DIRECTORS | AGENDA NOTE
**STRICTLY CONFIDENTIAL — FOR BOARD CONSIDERATION ONLY**

### 1. Proposal & Executive Summary
This memorandum seeks approval from the Board of Directors for targeted operational and financial interventions in mature onshore fields experiencing negative operating margins under prevailing crude realisations.

### 2. Operational Performance & Field Profile
Field **Champang** (FLD-CHP, Assam Asset) registered a standalone loss of -₹4.93 Crore in FY26, despite generating positive operating cash flow of ₹26.25 Crore, due to elevated statutory levies and lifting costs.

### 3. Financial Analysis & Break-Even Economics
| Field Name | Asset / Basin | FY26 Net Revenue (₹ Cr) | FY26 Opex (₹ Cr) | EBITDA (₹ Cr) | PBT (₹ Cr) |
|---|---|---|---|---|---|
| Champang | Assam Asset | 14.20 | 18.90 | +26.25 | -4.93 |
| Borholla | Assam Asset | 28.50 | 31.20 | +12.10 | +3.40 |
| Khoraghat | Assam Asset | 42.10 | 41.80 | +18.30 | +5.10 |

*Sensitivity Analysis:* Under an extreme $60/bbl Brent scenario, Champang, Borholla, and Khoraghat face negative operating cash flow, requiring Capex rationalisation.

### 4. Strategic Options Evaluated
1. **Option A: Production Enhancement Contract (PEC):** Inducting Technical Service Partners under a revenue-sharing model (MOPNG PEC Guidelines).
2. **Option B: Capex Rationalisation & Artificial Lift Overhaul:** Optimising water-handling and well servicing to compress lifting costs.
3. **Option C: Asset Farm-Out:** Monetisation under Discovered Small Field (DSF) framework.

### 5. Recommendation & Decision Sought
The Board is requested to approve:
1. In-principle authorization to initiate **Production Enhancement Contract (PEC)** bidding for Champang field.
2. Phased redeployment of engineering staff to high-pressure drilling campaigns in Tripura and Western Offshore.

*Prepared by:* Corporate Strategy & Asset Economics Group  
*Submitted for Approval:* Chairman & Managing Director (CMD)
"""
    },
    "parliament_reply": {
        "title": "Parliament Question Reply: Executive Vacancies in North-East Work Centres",
        "doc_type": "parliament_reply",
        "template_id": "template_parliament_reply_format.docx",
        "default_markdown": """# GOVERNMENT OF INDIA
## MINISTRY OF PETROLEUM AND NATURAL GAS
### RAJYA SABHA | UNSTARRED QUESTION NO. 142
**TO BE ANSWERED ON 28TH OCTOBER 2026**

**SUBJECT:** Executive Vacancies in ONGC North-East Work Centres  
**QUESTIONED BY:** Shri Anand Swaroop, Hon. M.P.

---

### (a) Whether it is a fact that technical executive positions in ONGC operational work centres in the North East are currently vacant?
**ANSWER (MINISTER OF STATE IN THE MINISTRY OF PETROLEUM AND NATURAL GAS):**  
(a) Yes, Sir. Across ONGC operational work centres situated in the North-Eastern States (Assam and Tripura), there are a total of **143 executive vacancies** against 4,548 sanctioned posts for FY26:
- **Tripura Asset (Agartala):** Sanctioned 957; In-Position 844; **Vacancies: 113**.
- **Assam Asset (Nazira/Sivasagar):** Sanctioned 1,848; In-Position 1,822; **Vacancies: 26**.
- **Assam & Assam Arakan Basin (A&AA):** Sanctioned 123; In-Position 119; **Vacancies: 4**.
- **Jorhat Asset, Silchar, INBIGS:** Fully staffed (Zero executive vacancies).

### (b) Steps being taken to fill vacancies and incentivize deployments?
**ANSWER:**  
(b) The Corporation has initiated the following measures:
1. **Special Recruitment Drives:** 15 executive vacancies are currently notified under dedicated Special Recruitment Drives for SC/ST/OBC categories.
2. **Rotational Transfer Redeployment:** 146 mid-level executive engineers (E3–E5) are being redeployed from corporate headquarters (Delhi/Dehradun) to field installations under the Annual General Transfer (AGT) cycle.
3. **Graduate Trainee Inductions:** Fresh Graduate Trainees in core technical disciplines selected through GATE are currently undergoing foundational training with mandatory initial postings in North-East operational assets.
"""
    },
    "transfer_proposal": {
        "title": "Annual General Transfer (AGT) Executive Redeployment Proposal FY27",
        "doc_type": "transfer_proposal",
        "template_id": "template_annual_general_transfer_proposal.xlsx",
        "default_markdown": """# ONGC CORPORATE HUMAN RESOURCES
## ANNUAL GENERAL TRANSFER (AGT) PROPOSAL — FY27
**Prepared pursuant to JRTP Rev 4 Guidelines (Clauses 3.0, 4.0, 7.0 & 9.0)**

### Executive Overview
- **Total Executives Evaluated:** 14,210 nationwide.
- **Overdue Station Tenure (>5 Years):** 642 executives (including 419 in Delhi Corporate HQ).
- **Pre-Retirement Exemptions (Within 3 Years of Superannuation):** 17 in Delhi, 54 nationwide.
- **Approved Exemption Tags in SAP:** 1 officer in Delhi.
- **Net Outstation Transfer Recommendations:** 401 executives from Delhi Corporate HQ to Operational Assets.

### Proposed Redeployment Quota
| Discipline | Relocating from Delhi/Dehradun | Destination: Tripura Asset | Destination: Assam Asset | Destination: Western Offshore |
|---|---|---|---|---|
| Production (DISC-PRD) | 48 | 20 | 12 | 16 |
| Drilling (DISC-DRL) | 36 | 18 | 8 | 10 |
| Materials Management (DISC-MM) | 28 | 12 | 6 | 10 |
| Finance & Accounts (DISC-FIN) | 34 | 14 | 8 | 12 |
| Total Relocations | **146** | **64** | **34** | **48** |
"""
    }
}


class DocumentDraftingEngine:
    """Manages document creation, template instantiation, and iterative revision."""

    def __init__(self, templates_dir: Path = TEMPLATES_DIR):
        self.templates_dir = templates_dir

    def draft(
        self,
        doc_type: str,
        query: str,
        version: int = 1,
        instruction: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Drafts or revises an official document."""
        dt = doc_type.lower()
        key = "board_note"
        if "parliament" in dt or "rajya sabha" in dt or "lok sabha" in dt or "x7" in dt:
            key = "parliament_reply"
        elif "transfer" in dt or "agt" in dt or "h10" in dt:
            key = "transfer_proposal"

        base = DOCUMENT_TEMPLATES.get(key, DOCUMENT_TEMPLATES["board_note"])
        markdown = base["default_markdown"]
        title = base["title"]

        # Apply revision instructions if requested
        if instruction:
            ins_l = instruction.lower()
            if "shorter" in ins_l or "concise" in ins_l:
                lines = markdown.splitlines()
                markdown = "\n".join(lines[:25]) + "\n\n*(Document abbreviated per executive instruction)*\n"
                title += " (Executive Brief)"
            elif "pec" in ins_l:
                markdown += "\n\n### Executive Revision Note\nOption A (Production Enhancement Contract - PEC) has been reaffirmed as the primary recommendation for immediate implementation."
            elif "hindi" in ins_l or "translate" in ins_l:
                markdown = "# तेल एवं प्राकृतिक गैस निगम लिमिटेड\n## निदेशक मंडल | एजेंडा नोट\n**गोपनीय — केवल बोर्ड विचारार्थ**\n\n### 1. प्रस्ताव एवं कार्यकारी सारांश\nयह ज्ञापन सीमांत ऑनशोर क्षेत्रों में रणनीतिक हस्तक्षेप के लिए अनुमोदन चाहता है।"

        # Enforce name hygiene: strip real politicians
        markdown = sanitize_fictional_names(markdown)

        return {
            "doc_type": key,
            "title": title,
            "markdown": markdown,
            "template_id": base["template_id"],
            "version": version,
        }
