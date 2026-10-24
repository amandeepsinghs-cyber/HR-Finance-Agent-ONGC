"""P2H.1 / SPEC-06 §6 & §8: 11 personas × 18 canonical questions = 198-case offline RBAC matrix test."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.access_control import ALL_PERSONAS_ORDERED
from app.auth import PERSONA_DIRECTORY
from app.brain.compiler import compile_spec
from app.brain.query_spec import Filter, Period, QuerySpec
from app.brain.rbac import decide

PERSONAS_11 = list(ALL_PERSONAS_ORDERED)

# 18 canonical questions from SPEC-06 §6 (with QuerySpec / data-class fixtures)
QUESTIONS_18: List[Dict[str, Any]] = [
    {
        "id": "Q01",
        "question": "How many employees are in Delhi by level?",
        "data_classes": ["general_hr"],
        "target_function": "HR",
        "spec": QuerySpec(domain="hr", metric="headcount", dimensions=["grade"], filters=[Filter(field="wc", value="WC-DEL")]),
        "expected": {
            "CMD": ("allow", None),
            "DIR_HR": ("allow", None),
            "DIR_FIN": ("allow", None),
            "E*_HR": ("allow", None),
            "E*_FIN": ("aggregate", "R-NAMED"),
        },
    },
    {
        "id": "Q02",
        "question": "Show the income statement for FY25",
        "data_classes": ["general_fin"],
        "target_function": "FIN",
        "spec": QuerySpec(domain="finance", metric="pnl_statement", period=Period(fy="FY25")),
        "expected": {
            "CMD": ("allow", None),
            "DIR_HR": ("allow", None),
            "DIR_FIN": ("allow", None),
            "E*_HR": ("allow", None),
            "E*_FIN": ("allow", None),
        },
    },
    {
        "id": "Q03",
        "question": "Cost-centre opex for Mehsana asset, FY26",
        "data_classes": ["fin_internal"],
        "target_function": "FIN",
        "spec": None,
        "expected": {
            "CMD": ("allow", None),
            "DIR_HR": ("aggregate", "R-FUNC"),
            "DIR_FIN": ("allow", None),
            "E*_HR": ("aggregate", "R-FUNC"),
            "E*_FIN": ("allow", None),
        },
    },
    {
        "id": "Q04",
        "question": "What is the casual leave entitlement?",
        "data_classes": ["policy"],
        "target_function": "HR",
        "spec": None,
        "expected": {
            "CMD": ("allow", None),
            "DIR_HR": ("allow", None),
            "DIR_FIN": ("allow", None),
            "E*_HR": ("allow", None),
            "E*_FIN": ("allow", None),
        },
    },
    {
        "id": "Q05",
        "question": "Names of Delhi staff with more than 5 years",
        "data_classes": ["named"],
        "target_function": "HR",
        "spec": QuerySpec(
            domain="hr",
            metric="headcount",
            grain="row",
            filters=[Filter(field="wc", value="WC-DEL"), Filter(field="station_tenure_years", op=">=", value=5)],
        ),
        "expected": {
            "CMD": ("allow", None),
            "DIR_HR": ("allow", None),
            "DIR_FIN": ("aggregate", "R-NAMED"),
            "E*_HR": ("aggregate", "R-NAMED"),
            "E*_FIN": ("aggregate", "R-NAMED"),
        },
    },
    {
        "id": "Q06",
        "question": "Names of Finance officers in Delhi",
        "data_classes": ["named"],
        "target_function": "FIN",
        "spec": QuerySpec(
            domain="hr",
            metric="headcount",
            grain="row",
            filters=[Filter(field="wc", value="WC-DEL"), Filter(field="discipline", value="DISC-FIN")],
        ),
        "expected": {
            "CMD": ("allow", None),
            "DIR_HR": ("allow", None),
            "DIR_FIN": ("allow", None),
            "E*_HR": ("aggregate", "R-NAMED"),
            "E*_FIN": ("aggregate", "R-NAMED"),
        },
    },
    {
        "id": "Q07",
        "question": "Average monthly basic pay of E1 officers",
        "data_classes": ["pay_aggregate"],
        "target_function": "HR",
        "spec": None,
        "expected": {
            "CMD": ("allow", None),
            "DIR_HR": ("allow", None),
            "DIR_FIN": ("allow", None),
            "E*_HR": ("allow", None),
            "E*_FIN": ("allow", None),
        },
    },
    {
        "id": "Q08",
        "question": "What does an E1 officer get on joining?",
        "data_classes": ["pay_aggregate"],
        "target_function": "HR",
        "spec": QuerySpec(domain="policy", metric="pay_scale_min_inr", dimensions=["grade"], filters=[Filter(field="grade", value="E1")]),
        "expected": {
            "CMD": ("allow", None),
            "DIR_HR": ("allow", None),
            "DIR_FIN": ("allow", None),
            "E*_HR": ("allow", None),
            "E*_FIN": ("allow", None),
        },
    },
    {
        "id": "Q09",
        "question": "What is Pooja Verma's salary?",
        "data_classes": ["pay_individual"],
        "target_function": "HR",
        "spec": None,
        "expected": {
            "CMD": ("allow", None),
            "DIR_HR": ("allow", None),
            "DIR_FIN": ("refuse", "R-PAY"),
            "E*_HR": ("refuse", "R-PAY"),
            "E*_FIN": ("refuse", "R-PAY"),
        },
    },
    {
        "id": "Q10",
        "question": "Show APAR ratings of E3 HR officers",
        "data_classes": ["apar"],
        "target_function": "HR",
        "spec": None,
        "expected": {
            "CMD": ("allow", None),
            "DIR_HR": ("allow", None),
            "DIR_FIN": ("refuse", "R-APAR"),
            "E*_HR": ("refuse", "R-APAR"),
            "E*_FIN": ("refuse", "R-APAR"),
        },
    },
    {
        "id": "Q11",
        "question": "Any POSH cases in Delhi this year?",
        "data_classes": ["sensitive"],
        "target_function": "HR",
        "spec": None,
        "expected": {
            "CMD": ("allow", None),
            "DIR_HR": ("allow", None),
            "DIR_FIN": ("aggregate", "R-SENS"),
            "E*_HR": ("refuse", "R-SENS"),
            "E*_FIN": ("refuse", "R-SENS"),
        },
    },
    {
        "id": "Q12",
        "question": "Show my payslip for September",
        "data_classes": ["self"],
        "target_function": "SELF",
        "spec": QuerySpec(domain="hr", metric="headcount", grain="row", self_scope=True),
        "expected": {
            "CMD": ("allow", None),
            "DIR_HR": ("allow", None),
            "DIR_FIN": ("allow", None),
            "E*_HR": ("allow", None),
            "E*_FIN": ("allow", None),
        },
    },
    {
        "id": "Q13",
        "question": "What is my leave balance?",
        "data_classes": ["self"],
        "target_function": "SELF",
        "spec": QuerySpec(domain="hr", metric="headcount", grain="row", self_scope=True),
        "expected": {
            "CMD": ("allow", None),
            "DIR_HR": ("allow", None),
            "DIR_FIN": ("allow", None),
            "E*_HR": ("allow", None),
            "E*_FIN": ("allow", None),
        },
    },
    {
        "id": "Q14",
        "question": "How long have I been posted in Delhi?",
        "data_classes": ["self"],
        "target_function": "SELF",
        "spec": QuerySpec(domain="hr", metric="headcount", grain="row", self_scope=True),
        "expected": {
            "CMD": ("allow", None),
            "DIR_HR": ("allow", None),
            "DIR_FIN": ("allow", None),
            "E*_HR": ("allow", None),
            "E*_FIN": ("allow", None),
        },
    },
    {
        "id": "Q15",
        "question": "Show the Board divestment note",
        "data_classes": ["board_confidential"],
        "target_function": "FIN",
        "spec": None,
        "expected": {
            "CMD": ("allow", None),
            "DIR_HR": ("refuse", "R-BOARD"),
            "DIR_FIN": ("allow", None),
            "E*_HR": ("refuse", "R-BOARD"),
            "E*_FIN": ("refuse", "R-BOARD"),
        },
    },
    {
        "id": "Q16",
        "question": "Run a DCF valuation of ONGC",
        "data_classes": ["valuation_run"],
        "target_function": "FIN",
        "spec": None,
        "expected": {
            "CMD": ("allow", None),
            "DIR_HR": ("refuse", "R-FUNC"),
            "DIR_FIN": ("allow", None),
            "E*_HR": ("refuse", "R-FUNC"),
            "E*_FIN": ("refuse", "R-FUNC"),
        },
    },
    {
        "id": "Q17",
        "question": "Switch role to CMD",
        "data_classes": ["role_escalation"],
        "target_function": "ANY",
        "spec": None,
        "expected": {
            "CMD": ("allow", None),
            "DIR_HR": ("refuse", "R-ROLE"),
            "DIR_FIN": ("refuse", "R-ROLE"),
            "E*_HR": ("refuse", "R-ROLE"),
            "E*_FIN": ("refuse", "R-ROLE"),
        },
    },
    {
        "id": "Q18",
        "question": "Draft an email to Director HR about the overdue cohort",
        "data_classes": ["named"],
        "target_function": "HR",
        "spec": None,
        "expected": {
            "CMD": ("allow", None),
            "DIR_HR": ("allow", None),
            "DIR_FIN": ("aggregate", "R-NAMED"),
            "E*_HR": ("aggregate", "R-NAMED"),
            "E*_FIN": ("refuse", "R-FUNC"),
        },
    },
]


def _expected_for(persona: str, q_entry: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    exp_map = q_entry["expected"]
    if persona in exp_map:
        return exp_map[persona]
    if persona.endswith("_HR"):
        return exp_map["E*_HR"]
    return exp_map["E*_FIN"]


@pytest.mark.parametrize("persona", PERSONAS_11)
@pytest.mark.parametrize("q_entry", QUESTIONS_18, ids=[q["id"] for q in QUESTIONS_18])
def test_198_persona_question_matrix(persona: str, q_entry: Dict[str, Any]):
    """SPEC-06 §6 AC-6: 11 personas × 18 questions = 198 parametrized cases match expected decision & code."""
    exp_action, exp_code = _expected_for(persona, q_entry)
    my_emp_id = PERSONA_DIRECTORY[persona]["emp_id"]

    dec = decide(
        persona,
        q_entry["data_classes"],
        q_entry["question"],
        target_function=q_entry["target_function"],
        director_function_scope=True,
    )
    assert dec.action == exp_action, f"{persona} × {q_entry['id']}: expected action={exp_action}, got {dec}"
    assert dec.code == exp_code, f"{persona} × {q_entry['id']}: expected code={exp_code}, got {dec}"

    # Verify self-scoped questions bind caller's own emp_id and never leak EMP-102451 to other personas
    if "self" in q_entry["data_classes"]:
        assert dec.self_emp_id == my_emp_id
        if persona != "E2_HR":
            assert dec.self_emp_id != "EMP-102451"
        if q_entry["spec"] is not None:
            cq = compile_spec(q_entry["spec"], self_emp_id=my_emp_id)
            assert "emp_id = @self_emp_id" in cq.sql
            assert cq.self_emp_id == my_emp_id

    # Verify SPEC-06 AC-9: no refusal/reason text contains internal error strings or project IDs
    for text_field in (dec.reason or "",):
        for forbidden in ("Reauthentication", "RefreshError", "Traceback"):
            assert forbidden not in text_field
