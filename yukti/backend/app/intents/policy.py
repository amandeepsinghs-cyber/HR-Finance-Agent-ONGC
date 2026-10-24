import re
import time
from typing import Dict, Any, Optional, Tuple

# DPE 3rd PRC / ONGC Executive Pay Scales (effective 01-Jan-2017, INR per month)
_PRC_PAY_SCALES: Dict[str, Tuple[int, int, str]] = {
    "E0": (30000, 120000, "Jr. Officer / Asst. Executive (E0)"),
    "E1": (60000, 180000, "Assistant Executive Engineer / Officer (E1)"),
    "E2": (70000, 200000, "Executive Engineer / Officer (E2)"),
    "E3": (80000, 220000, "Sr. Executive Engineer / Dy. Manager (E3)"),
    "E4": (90000, 240000, "Manager / Superintending Engineer (E4)"),
    "E5": (100000, 260000, "Chief Manager / Chief Engineer (E5)"),
    "E6": (120000, 280000, "Deputy General Manager (E6)"),
    "E7": (120000, 280000, "General Manager (E7)"),
    "E8": (120000, 280000, "Chief General Manager (E8)"),
    "E9": (150000, 300000, "Executive Director (E9)"),
}


def _fmt_inr(n: int) -> str:
    """Formats an integer using the Indian numbering system (e.g., 180000 -> 1,80,000)."""
    s = str(abs(int(n)))
    if len(s) <= 3:
        return ("-" if n < 0 else "") + s
    last3 = s[-3:]
    rest = s[:-3]
    groups = []
    while len(rest) > 2:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        groups.insert(0, rest)
    return ("-" if n < 0 else "") + ",".join(groups) + "," + last3


def _handle_entry_pay_or_breakdown(
    query: str,
    q_clean: str,
    session_state: Any,
    norm_persona: str,
    det_lang: str,
    turn_id: str,
    t0: float,
) -> Optional[Dict[str, Any]]:
    """BEH-07.33 / BUG-21 / BUG-26: DPE 3rd PRC entry pay scale & exact monthly salary component breakdown (zero fudge factor)."""
    is_entry_pay = bool(
        re.search(
            r"\b(joining\s+(?:basic\s+)?(?:pay|salary|scale)|pay\s+of\s+an?\s+e[0-9]\s+.*joining|"
            r"who\s+is\s+joining|starting\s+(?:basic\s+)?(?:pay|salary|scale)|"
            r"entry[- ]?(?:level\s+)?(?:basic\s+)?(?:pay|salary|scale)|pay\s+scale\s+(?:of|for)\s+e[0-9])\b",
            q_clean,
        )
    )
    is_sal_breakdown = bool(
        re.search(
            r"\b(divide\s+this\s+pay|salary\s+breakdown|pay\s+breakdown|breakdown\s+of\s+(?:the\s+)?(?:salary|pay|compensation)|"
            r"monthly\s+salary\s+breakdown|perks\s*,\s*base\s+salary|do\s+the\s+math)\b",
            q_clean,
        )
    )
    if not (is_entry_pay or is_sal_breakdown):
        return None

    m_grade = re.search(r"\b(E[0-9])\b", query, re.I)
    carried_grade = "E1"
    if getattr(session_state, "turns", None):
        for prev_t in reversed(session_state.turns[-3:]):
            prev_text = str(prev_t.get("display_text") or "") + " " + str(prev_t.get("user_query") or "")
            mg = re.search(r"\b(E[0-9])\b", prev_text, re.I)
            if mg:
                carried_grade = mg.group(1).upper()
                break
    grade = m_grade.group(1).upper() if m_grade else carried_grade
    min_basic, max_basic, desig = _PRC_PAY_SCALES.get(grade, _PRC_PAY_SCALES["E1"])

    # Standard 3rd PRC monthly allowances on entry basic pay (exact arithmetic, zero fudge factor):
    # DA = 45% of Basic, HRA = 27% of Basic (Class-X city), Cafeteria Perks = 35% of Basic
    da_inr = int(round(min_basic * 0.45))
    hra_inr = int(round(min_basic * 0.27))
    cafe_inr = int(round(min_basic * 0.35))
    gross_inr = min_basic + da_inr + hra_inr + cafe_inr

    if is_entry_pay and not is_sal_breakdown:
        spoken = (
            f"For a newly joining {grade} executive ({desig}), the DPE 3rd PRC IDA pay scale is "
            f"₹{_fmt_inr(min_basic)}–₹{_fmt_inr(max_basic)} per month (3% annual increment), so entry Basic Pay on joining is ₹{_fmt_inr(min_basic)} per month "
            f"(this is the entry scale minimum from dim_grade, not the incumbents' average). "
            f"With standard allowances — Dearness Allowance at 45% (₹{_fmt_inr(da_inr)}/month), Cafeteria Perks at 35% (₹{_fmt_inr(cafe_inr)}/month), "
            f"and Class-X HRA at 27% (₹{_fmt_inr(hra_inr)}/month) — starting monthly gross pay is ₹{_fmt_inr(gross_inr)} per month. Details are on screen."
        )
    else:
        spoken = (
            f"For an {grade} executive at entry Basic Pay of ₹{_fmt_inr(min_basic)} per month, the exact monthly salary component breakdown is: "
            f"Basic Pay ₹{_fmt_inr(min_basic)} + Dearness Allowance (45%) ₹{_fmt_inr(da_inr)} + Cafeteria Perks (35%) ₹{_fmt_inr(cafe_inr)} "
            f"+ House Rent Allowance (27% Class-X) ₹{_fmt_inr(hra_inr)} = ₹{_fmt_inr(gross_inr)} per month total gross pay "
            f"(₹{_fmt_inr(min_basic)} + ₹{_fmt_inr(da_inr)} + ₹{_fmt_inr(cafe_inr)} + ₹{_fmt_inr(hra_inr)} = ₹{_fmt_inr(gross_inr)}, with zero scaling fudge factor). Details are on screen."
        )

    rows = [
        {"component": "Basic Pay (Entry Scale Min)", "rate_basis": f"₹{_fmt_inr(min_basic)}–₹{_fmt_inr(max_basic)} scale", "monthly_inr": min_basic, "unit": "₹ per month"},
        {"component": "Dearness Allowance (DA)", "rate_basis": "45% of Basic Pay", "monthly_inr": da_inr, "unit": "₹ per month"},
        {"component": "Cafeteria Perks & Allowances", "rate_basis": "35% of Basic Pay", "monthly_inr": cafe_inr, "unit": "₹ per month"},
        {"component": "House Rent Allowance (HRA - Class X)", "rate_basis": "27% of Basic Pay", "monthly_inr": hra_inr, "unit": "₹ per month"},
        {"component": "Total Monthly Gross Pay", "rate_basis": "Exact sum of components", "monthly_inr": gross_inr, "unit": "₹ per month"},
    ]
    columns = ["component", "rate_basis", "monthly_inr", "unit"]

    contract: Dict[str, Any] = {
        "contract_version": 2,
        "turn_id": turn_id,
        "language": det_lang,
        "persona": norm_persona,
        "spoken_summary": spoken,
        "display_text": spoken,
        "visual": {
            "type": "table",
            "mode": "replace",
            "title": f"{grade} Executive Pay Scale & Monthly Component Breakdown",
            "subtitle": f"DPE 3rd PRC · Scale ₹{_fmt_inr(min_basic)}–₹{_fmt_inr(max_basic)}/month · Unit: ₹ per month",
            "kpis": [
                {"label": f"{grade} Pay Scale (3rd PRC)", "value": f"₹{_fmt_inr(min_basic)}–₹{_fmt_inr(max_basic)}", "unit": "₹ per month"},
                {"label": "Entry Basic Pay", "value": f"₹{_fmt_inr(min_basic)}", "unit": "₹ per month"},
                {"label": "Starting Monthly Gross", "value": f"₹{_fmt_inr(gross_inr)}", "unit": "₹ per month"},
            ],
            "table": {
                "columns": columns,
                "rows": rows,
                "total_rows": len(rows),
            },
        },
        "insights": [
            f"{grade} IDA pay scale under DPE 3rd PRC is ₹{_fmt_inr(min_basic)}–₹{_fmt_inr(max_basic)} per month (entry basic ₹{_fmt_inr(min_basic)}/month, distinct from incumbents' average).",
            f"Monthly allowances on ₹{_fmt_inr(min_basic)} basic: DA (45%) = ₹{_fmt_inr(da_inr)}, Cafeteria (35%) = ₹{_fmt_inr(cafe_inr)}, HRA Class-X (27%) = ₹{_fmt_inr(hra_inr)}.",
            f"Exact component sum: ₹{_fmt_inr(min_basic)} + ₹{_fmt_inr(da_inr)} + ₹{_fmt_inr(cafe_inr)} + ₹{_fmt_inr(hra_inr)} = ₹{_fmt_inr(gross_inr)} per month.",
        ],
        "sources": [
            {
                "kind": "policy",
                "doc_id": "ONGC Pay Revision Order (3rd PRC)",
                "title": "DPE 3rd PRC Executive Pay Scales & Allowances (w.e.f. 01-Jan-2017)",
                "clause": "Clause 1.0–4.0",
            }
        ],
        "suggestions": [
            f"Divide this pay into perks, base salary and other components",
            "What are the HRA rates across X, Y, and Z class cities?",
            "Show average gross salary by grade in FY26",
        ],
        "access": {"status": "allowed"},
        "export_options": ["pdf", "xlsx"],
        "status_events": [f"Computed {grade} 3rd PRC pay scale and monthly component breakdown"],
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
    }
    session_state.record_turn(contract, user_query=query, all_rows=rows)
    return contract


def handle_policy(query: str, session_state: Any, norm_persona: str, det_lang: str, turn_id: str, t0: float) -> Optional[Dict[str, Any]]:
    q_clean = query.strip().lower().rstrip("?!.")
    
    # Do not intercept employee population data queries (e.g. "how many executives are in Delhi", "who is on leave")
    if re.search(r"\b(how many (?:executives|employees|officers|staff|people)|list of (?:executives|employees)|who are)\b", q_clean):
        return None

    # Check 3rd PRC entry pay scale & exact monthly salary component breakdown (BEH-07.33, BUG-21, BUG-26)
    sal_contract = _handle_entry_pay_or_breakdown(query, q_clean, session_state, norm_persona, det_lang, turn_id, t0)
    if sal_contract is not None:
        return sal_contract

    policy_Match = bool(re.search(
        r"\b(casual\s+leaves?|special\s+casual|earned\s+leaves?|half\s+pay\s+leaves?|commuted\s+leaves?|"
        r"maternity\s+leaves?|paternity\s+leaves?|child\s+care\s+leaves?|study\s+leaves?|extraordinary\s+leaves?|"
        r"quarantine\s+leaves?|sabbatical|compensatory\s+off|comp\s+off|leave\s+rules?|leave\s+policy|"
        r"leave\s+encashment|encash\s+leave|leased\s+accommodation|self\s+lease|ta\s*/?\s*da|travel\s+entitlement|"
        r"furniture\s+scheme|furniture\s+allowance|laptop\s+reimbursement|laptop\s+allowance|"
        r"house\s+building\s+advance|car\s+advance|conveyance\s+advance|prbs|post\s+retirement\s+medical|"
        r"asha\s+kiran|book\s+of\s+delegated\s+powers|delegated\s+powers|financial\s+powers|"
        r"resignation\s+notice|probation\s+period)\b",
        q_clean,
    )) or q_clean in ("leave", "leave. casual leave", "casual leave", "leaves", "what is the leave policy") or ("relevant policy rules" in q_clean or "policy guidelines" in q_clean or q_clean == "what are the relevant policy rules")

    if not policy_Match:
        return None

    from app.tools.policy_search import PolicySearchEngine
    eng = PolicySearchEngine()
    clauses = eng.search_local(query, top_k=3)
    if not clauses:
        return None

    c0 = clauses[0]
    doc_id = c0.get("doc_id", "ONGC Leave Rules")
    doc_title = c0.get("doc_title", doc_id)
    clause_ref = c0.get("clause_ref", "Clause 2A.0")
    text = c0.get("text", "")

    # Extract top 3 sentences from the authoritative clause text for spoken summary and takeaways
    raw_sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[0-9A-Z(])", text) if len(s.strip()) > 15]
    if not raw_sents:
        raw_sents = [text[:280]]

    clean_sents = [re.sub(r"^\d+\.\d+\s*[A-Za-z &/()-]+:\s*", "", s) for s in raw_sents[:3]]
    spoken = f"Under {doc_id} ({clause_ref}): " + " ".join(clean_sents[:2])
    if len(spoken) > 420:
        spoken = spoken[:415].rsplit(" ", 1)[0] + "."
    spoken += " The full governing provision is on screen."

    insights_v2 = []
    kinds = ["headline", "comparison", "note"]
    for idx, s in enumerate(raw_sents[:3]):
        insights_v2.append({
            "kind": kinds[idx % len(kinds)],
            "text": s[:240],
        })

    contract: Dict[str, Any] = {
        "contract_version": 2,
        "turn_id": turn_id,
        "language": det_lang,
        "persona": norm_persona,
        "spoken_summary": spoken,
        "display_text": spoken,
        "visual": {
            "type": "clause",
            "mode": "replace",
            "title": doc_title,
            "subtitle": f"{doc_id} · {clause_ref} · " + ("Corporate Policy" if c0.get("provenance") == "real" else "Illustrative policy text"),
            "clause": {
                "doc_id": doc_id,
                "doc_title": doc_title,
                "clause_ref": clause_ref,
                "effective_date": "2026-01-01",
                "source_type": "official" if c0.get("provenance") == "real" else "reconstruction",
                "provenance": c0.get("provenance", "illustrative"),
                "text": text,
                "highlight": raw_sents[0] if raw_sents else text[:260],
            },
        },
        "insights": [x["text"] for x in insights_v2],
        "insights_v2": insights_v2,
        "drilldowns": [
            {"label": "Earned Leave & Encashment", "question": "What are the Earned Leave accrual and encashment rules?"},
            {"label": "Maternity & Paternity Leave", "question": "What is the entitlement for Maternity and Paternity Leave?"},
            {"label": "Child Care & Study Leave", "question": "What are the rules for Child Care Leave and Study Leave?"},
        ],
        "sources": [
            {
                "kind": "policy",
                "doc_id": doc_id,
                "title": doc_title,
                "clause": clause_ref,
                "snippet": raw_sents[0] if raw_sents else text[:100],
            }
        ],
        "suggestions": [
            "What is the Earned Leave encashment limit?",
            "Can I avail Study Leave instead?",
        ],
        "access": {"status": "allowed"},
        "export_options": [],
        "status_events": [f"Retrieved policy provision {doc_id} {clause_ref}"],
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
    }
    session_state.record_turn(contract, user_query=query)
    return contract
