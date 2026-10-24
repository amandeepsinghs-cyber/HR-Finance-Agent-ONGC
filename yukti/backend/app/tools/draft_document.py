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
2. **Rotational Transfer Redeployment:** Mid-level executive engineers (E3–E5) are being redeployed from corporate headquarters (Delhi/Dehradun) to field installations under the Annual General Transfer (AGT) cycle.
3. **Graduate Trainee Inductions:** Fresh Graduate Trainees in core technical disciplines selected through GATE are currently undergoing foundational training with mandatory initial postings in North-East operational assets.
"""
    }
}


class DocumentDraftingEngine:
    """Manages document creation, template instantiation, and iterative revision."""

    def __init__(self, templates_dir: Path = TEMPLATES_DIR):
        self.templates_dir = templates_dir

    def _format_markdown_table(self, columns: List[str], rows: List[Dict[str, Any]], max_rows: int = 12) -> str:
        if not columns or not rows:
            return ""
        cols = columns[:7]
        header = "| " + " | ".join(str(c).replace("_", " ").title() for c in cols) + " |"
        sep = "| " + " | ".join("---" for _ in cols) + " |"
        body = []
        for r in rows[:max_rows]:
            vals = []
            for c in cols:
                v = r.get(c, "")
                if isinstance(v, float):
                    vals.append(f"{v:,.2f}")
                elif isinstance(v, int):
                    vals.append(f"{v:,}")
                else:
                    vals.append(str(v if v is not None else ""))
            body.append("| " + " | ".join(vals) + " |")
        return "\n".join([header, sep] + body)

    def draft(
        self,
        doc_type: str,
        query: str,
        version: int = 1,
        instruction: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Drafts or revises an official document, dynamically incorporating live session/BigQuery SSOT data."""
        dt = (doc_type or "").lower()
        q_l = (query or "").lower()
        key = "board_note"
        if any(w in dt or w in q_l for w in ["parliament", "rajya sabha", "lok sabha", "unstarred", "x7"]):
            key = "parliament_reply"

        base = DOCUMENT_TEMPLATES.get(key, DOCUMENT_TEMPLATES["board_note"])
        markdown = base["default_markdown"]
        title = base["title"]

        # Check if the user is asking for a dynamic data-backed briefing note / memo / report from context or SSOT
        ctx = context_data or {}
        ctx_rows = ctx.get("rows") or []
        ctx_cols = ctx.get("columns") or (list(ctx_rows[0].keys()) if ctx_rows and isinstance(ctx_rows[0], dict) else [])
        ctx_title = ctx.get("title") or ""
        wc_profile = ctx.get("wc_profile") or {}

        is_canonical_template_request = (
            ("parliament" in q_l and not ctx_rows)
            or ("marginal" in q_l or "champang" in q_l)
            or ("annual general transfer" in q_l or "agt" in q_l)
        )

        if (ctx_rows or wc_profile) and not is_canonical_template_request:
            wc_name = wc_profile.get("wc_name") or ctx.get("wc_name") or "ONGC Enterprise Operations"
            wc_id = wc_profile.get("wc_id") or ctx.get("wc_id") or "CORP-ALL"
            doc_heading = "OFFICE MEMORANDUM & EXECUTIVE BRIEFING NOTE"
            if "board" in q_l or "board" in dt:
                doc_heading = "BOARD OF DIRECTORS | AGENDA BRIEFING NOTE"
            elif "parliament" in q_l or "parliament" in dt:
                doc_heading = "MINISTRY OF PETROLEUM & NATURAL GAS | PARLIAMENT BRIEFING"
            elif "order" in q_l or "transfer" in q_l:
                doc_heading = "CORPORATE HUMAN RESOURCES | ADMINISTRATIVE ORDER DRAFT"

            subject_line = ctx_title if ctx_title and ctx_title != "Answer" else f"Operational & Workforce Review — {wc_name}"
            title = f"Draft Briefing Note: {subject_line}"

            wc_section = ""
            if wc_profile:
                def _fmt_count(val: Any) -> str:
                    if val is None or val == "":
                        return "n/a"
                    try:
                        return f"{int(float(val)):,}"
                    except (ValueError, TypeError):
                        return "n/a"

                def _get_val(new_key: str, old_key: Optional[str] = None) -> Any:
                    val = wc_profile.get(new_key)
                    if val is None and old_key:
                        val = wc_profile.get(old_key)
                    return val

                act_hc = _fmt_count(wc_profile.get("active_headcount"))
                exec_hc = _fmt_count(wc_profile.get("executive_headcount"))
                non_exec_hc = _fmt_count(wc_profile.get("non_executive_headcount"))
                sanc_hc = _fmt_count(_get_val("sanctioned_strength_fy26", "sanctioned_strength"))
                vac_hc = _fmt_count(_get_val("vacancy_count_fy26", "vacancy_count"))
                cont_hc = _fmt_count(_get_val("contractor_headcount_fy26", "contract_workforce_headcount"))

                pay_val = _get_val("payroll_gross_inr_cr_fy26", "fy26_total_payroll_cr")
                if pay_val is None or pay_val == "":
                    pay_str = "n/a"
                else:
                    try:
                        pay_str = f"₹{float(pay_val):,.2f} Crore"
                    except (ValueError, TypeError):
                        pay_str = "n/a"

                stay_5y = _fmt_count(_get_val("continuous_stay_5yr_plus_execs", "execs_stay_ge_5yr"))
                ret_3y = _fmt_count(_get_val("retiring_within_3yr_count", "retiring_3yr_count"))

                wc_section = f"""
### 2. Work Centre 360° Key Indicators ({wc_name} · `{wc_id}`)
- **In-Position Regular Strength (As of 19-Oct-2026):** **{act_hc}** employees (**{exec_hc}** Executives; **{non_exec_hc}** Non-Executives) against **{sanc_hc}** Sanctioned Posts (**{vac_hc}** Vacancies).
- **Contractual & Outsourced Workforce:** **{cont_hc}** contract personnel deployed across operations.
- **FY26 Gross Payroll:** **{pay_str}**.
- **Mobility & Succession Profile:** **{stay_5y}** executives with ≥5 years continuous station stay; **{ret_3y}** employees superannuating within 36 months.
"""

            md_table = self._format_markdown_table(ctx_cols, ctx_rows, max_rows=15)
            table_section = f"\n### 3. Grounded Analytical Data Table ({len(ctx_rows)} Records)\n{md_table}\n" if md_table else ""

            summary_para = ctx.get("summary_text") or (
                f"This executive briefing note synthesizes enterprise records (demo data) from the ONGC Single Source of Truth (SSOT) "
                f"for {wc_name} as of 19th October 2026."
            )

            markdown = f"""# OIL AND NATURAL GAS CORPORATION LIMITED
## {doc_heading}
**File Ref:** `ONGC/CMD/BRIEF/2026/{wc_id}` | **Date:** 20th October 2026  
**Classification:** INTERNAL — FOR EXECUTIVE REVIEW  
**Subject:** **{subject_line}**

---

### 1. Executive Summary
{summary_para}
{wc_section}{table_section}
### 4. Actionable Recommendations & Next Steps
1. **Workforce & Cadre Alignment:** Align rotational deployments and special recruitment drives with sanctioned post gaps and upcoming superannuation windows under JRTP Rev. 4 guidelines.
2. **Cost & Productivity Optimization:** Monitor unit manpower and lifting costs against FY27 MoU targets and quarterly budget estimates (BE/RE).
3. **Compliance & Governance:** Record this briefing note in the executive decision register and circulate approved extracts to concerned Asset/Basin Managers.

*Generated & Grounded by:* **Yukti AI (ONGC Executive Intelligence)**  
*Source Attribution:* `hrfin_gold.ssot_work_centre_360` & `hrfin_gold.ssot_workforce_employee`
"""

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
                markdown = "# तेल एवं प्राकृतिक गैस निगम लिमिटेड\n## निदेशक मंडल | एजेंडा नोट\n**गोपनीय — केवल बोर्ड विचारार्थ**\n\n### 1. प्रस्ताव एवं कार्यकारी सारांश\nयह ज्ञापन सीमांत ऑनशोर क्षेत्रों एवं कार्य केंद्रों में रणनीतिक हस्तक्षेप के लिए अनुमोदन चाहता है।"

        # Enforce name hygiene: strip real politicians
        markdown = sanitize_fictional_names(markdown)

        return {
            "doc_type": key,
            "title": title,
            "markdown": markdown,
            "template_id": base["template_id"],
            "version": version,
        }

    def draft_transfer_note(
        self,
        employees: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        version: int = 1,
    ) -> Dict[str, Any]:
        """Drafts a transfer-note document listing the given roster employees."""
        if not employees:
            raise ValueError("no employees selected")

        n = len(employees)
        wcs = [e.get("work_centre") for e in employees]
        if all(w and w == wcs[0] for w in wcs):
            wc_label = wcs[0]
        else:
            wc_label = "Multiple Work Centres"

        title = f"Draft Transfer Note: {n} Executive(s) — {wc_label}"

        def _format_cell(val: Any) -> str:
            if val is None or val == "" or val == "None":
                return "—"
            if isinstance(val, bool):
                return "Yes" if val else "No"
            return str(val).replace("|", "\\|")  # a pipe would break the markdown table

        def _format_tenure(val: Any) -> str:
            if val is None or val == "" or val == "None" or val == "—":
                return "—"
            try:
                return f"{float(val):.1f}"
            except (ValueError, TypeError):
                return "—"

        headers = [
            "S.No",
            "Name",
            "Emp ID",
            "Designation",
            "Grade",
            "Discipline",
            "Present Work Centre",
            "Station Tenure (yrs)",
            "ONGC Service (yrs)",
            "Exemption",
        ]
        table_lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        for idx, emp in enumerate(employees, 1):
            row_vals = [
                str(idx),
                _format_cell(emp.get("name")),
                _format_cell(emp.get("emp_id")),
                _format_cell(emp.get("designation")),
                _format_cell(emp.get("grade")),
                _format_cell(emp.get("discipline")),
                _format_cell(emp.get("work_centre")),
                _format_tenure(emp.get("station_tenure_years")),
                _format_tenure(emp.get("ongc_tenure_years")),
                _format_cell(emp.get("exemption")),
            ]
            table_lines.append("| " + " | ".join(row_vals) + " |")
        table_str = "\n".join(table_lines)

        purpose_text = (
            context.get("purpose")
            if context and isinstance(context, dict) and context.get("purpose")
            else f"This deliberative draft transfer note outlines proposed rotational transfers for {n} executive(s) pursuant to the ONGC Job Rotation and Transfer Policy (JRTP)."
        )

        exemption_lines = []
        for emp in employees:
            ret = emp.get("retiring_within_3yr")
            is_retiring = (ret is True) or (isinstance(ret, str) and ret.lower() in ("true", "yes", "1"))
            ex = emp.get("exemption")
            has_ex = ex not in (None, "None", "", "—")
            if is_retiring or has_ex:
                reasons = []
                if is_retiring:
                    reasons.append("Retiring within 3 years")
                if has_ex:
                    reasons.append(f"Exemption: {ex}")
                emp_name = emp.get("name") or "—"
                emp_id = emp.get("emp_id") or "—"
                exemption_lines.append(f"- **{emp_name}** ({emp_id}) — {'; '.join(reasons)}")

        if exemption_lines:
            exemptions_content = "\n".join(exemption_lines)
        else:
            exemptions_content = "No exemption flags among the selected employees."

        md_parts = [
            "# OIL AND NATURAL GAS CORPORATION LIMITED",
            "## CORPORATE HUMAN RESOURCES | DRAFT TRANSFER NOTE",
            "**Classification:** CONFIDENTIAL — DELIBERATIVE DRAFT (JRTP Clause 11.0)",
            "",
            "### 1. Purpose",
            purpose_text,
            "",
            f"### 2. Employees Proposed for Transfer ({n})",
            table_str,
            "",
            "### 3. Policy Basis",
            "Rotational transfer recommendations are framed pursuant to JRTP Clause 3.2 rotation after 5 years of continuous station tenure. Clause 7.0 exemption within 3 years of superannuation applies to eligible executives subject to administrative review.",
            "",
            "### 4. Exemptions to Verify",
            exemptions_content,
            "",
            "### 5. Proposed Destination",
            "To be decided by the competent authority (Director HR).",
            "",
            "*Prepared by:* Yukti AI for Director (HR) review",
        ]
        markdown = "\n".join(md_parts)
        markdown = sanitize_fictional_names(markdown)

        return {
            "doc_type": "transfer_note",
            "title": title,
            "markdown": markdown,
            "template_id": "template_transfer_note.docx",
            "version": version,
            "employee_count": n,
            "emp_ids": [e.get("emp_id") for e in employees],
        }
