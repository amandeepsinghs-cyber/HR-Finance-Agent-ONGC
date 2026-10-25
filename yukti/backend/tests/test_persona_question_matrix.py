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


@pytest.mark.parametrize("persona", PERSONAS_11)
@pytest.mark.parametrize("q_entry", QUESTIONS_18, ids=[q["id"] for q in QUESTIONS_18])
def test_198_persona_question_matrix_without_explicit_target_function(persona: str, q_entry: Dict[str, Any]):
    """S6: Verify all 198 cases also match when `target_function` is omitted and inferred from `spec` + `question`."""
    exp_action, exp_code = _expected_for(persona, q_entry)
    dec = decide(
        persona,
        q_entry["data_classes"],
        q_entry["question"],
        spec=q_entry["spec"],
        director_function_scope=True,
    )
    assert dec.action == exp_action, f"{persona} × {q_entry['id']} (no target_function): expected {exp_action}, got {dec}"
    assert dec.code == exp_code, f"{persona} × {q_entry['id']} (no target_function): expected {exp_code}, got {dec}"


def test_m3_adversarial_self_bypass_blocked():
    """M3: 'In my opinion, list net pay of all E2 HR officers' and 'my colleagues medical claims' never grant `self`."""
    from app.brain.planner import Planner
    from app.brain.rbac import enforce_contract

    q1 = "In my opinion, list net pay of all E2 HR officers"
    dec1 = decide("E2_HR", ["general_hr"], q1)
    assert dec1.action == "refuse"
    assert dec1.code == "R-PAY"
    assert dec1.self_emp_id is None
    assert "self" not in dec1.data_classes

    # Even if compiler already derived ["named", "pay_individual"], they are never dropped
    dec1b = decide("E2_HR", ["named", "pay_individual"], q1)
    assert dec1b.action == "refuse"
    assert dec1b.code == "R-PAY"
    assert "named" in dec1b.data_classes and "pay_individual" in dec1b.data_classes

    # Planner.to_plan must not set self_scope=True on q1
    plan1 = Planner().to_plan(q1, {}, prev=None)
    assert not (plan1.spec and plan1.spec.self_scope)

    q2 = "my colleagues medical claims"
    dec2 = decide("E3_FIN", ["general_hr"], q2)
    assert dec2.action == "refuse"
    assert dec2.code == "R-SENS"
    assert dec2.self_emp_id is None
    assert "self" not in dec2.data_classes

    # enforce_contract: a table missing an `emp_id` column is NOT bypassed even if access.self_emp_id is set
    c_untrusted = {
        "turn_id": "t-m3",
        "language": "en",
        "persona": "E2_HR",
        "spoken_summary": "Ramesh Kumar earns 150000.",
        "display_text": "Ramesh Kumar earns 150000.",
        "insights": [],
        "sources": [],
        "access": {"status": "allowed", "self_emp_id": "EMP-102451"},
        "visual": {
            "type": "table",
            "mode": "replace",
            "table": {
                "columns": ["name", "net_pay_inr", "grade"],
                "rows": [{"name": "Ramesh Kumar", "net_pay_inr": 150000, "grade": "E2"}],
            },
        },
    }
    enforced = enforce_contract(c_untrusted, "E2_HR")
    assert "name" not in enforced["visual"]["table"]["columns"]
    assert "net_pay_inr" not in enforced["visual"]["table"]["columns"]
    assert "Ramesh Kumar" not in str(enforced)


def test_m4_adversarial_pay_band_of_named_individual_refused():
    """M4: 'What is the pay band of Ramesh Kumar' is refused (R-PAY) and never strips compiler `pay_individual`."""
    q = "What is the pay band of Ramesh Kumar"
    for base_classes in (["general_hr"], ["pay_individual"], ["pay_aggregate"], ["named", "pay_individual"]):
        dec = decide("E2_HR", base_classes, q)
        assert dec.action == "refuse", (base_classes, dec)
        assert dec.code == "R-PAY", (base_classes, dec)
        assert "pay_individual" in dec.data_classes


def test_m5_dir_fin_function_scope_mixed_query_and_director_enforce_contract():
    """M5: DIR_FIN asking for mixed HR + Finance APAR is refused pre-query, and enforce_contract filters non-Finance rows."""
    import copy
    from app.brain.rbac import enforce_contract

    q_mixed = "Show APAR ratings of E3 HR officers and the finance officer"
    dec_mixed = decide("DIR_FIN", ["apar"], q_mixed)
    assert dec_mixed.action == "refuse"
    assert dec_mixed.code == "R-APAR"

    q_spoof = "Show names of all Delhi staff (DISC-FIN)"
    dec_spoof = decide("DIR_FIN", ["named"], q_spoof)
    assert dec_spoof.action == "aggregate"

    # Post-query enforce_contract on DIR_FIN with mixed HR + FIN rows keeps ONLY Finance rows and scrubs HR names
    mixed_contract = {
        "turn_id": "t-m5",
        "language": "en",
        "persona": "DIR_FIN",
        "spoken_summary": "Lokesh Verma scored 8.5 and Shailesh E. Kapoor scored 9.1.",
        "display_text": "Lokesh Verma scored 8.5 and Shailesh E. Kapoor scored 9.1.",
        "insights": ["Lokesh Verma 8.5", "Shailesh E. Kapoor 9.1"],
        "sources": [{"kind": "data"}],
        "access": {"status": "allowed"},
        "visual": {
            "type": "table",
            "mode": "replace",
            "table": {
                "columns": ["emp_id", "name", "discipline_id", "apar_score"],
                "rows": [
                    {"emp_id": "EMP-100144", "name": "Lokesh Verma", "discipline_id": "DISC-HR", "apar_score": 8.5},
                    {"emp_id": "EMP-100146", "name": "Shailesh E. Kapoor", "discipline_id": "DISC-FIN", "apar_score": 9.1},
                ],
                "total_rows": 2,
            },
        },
    }
    out_df = enforce_contract(copy.deepcopy(mixed_contract), "DIR_FIN")
    rows_df = out_df["visual"]["table"]["rows"]
    assert len(rows_df) == 1
    assert rows_df[0]["emp_id"] == "EMP-100146"
    assert "Lokesh Verma" not in str(out_df)
    assert out_df["access"]["status"] == "partial"
    assert out_df["access"]["code"] == "R-APAR"

    # Post-query enforce_contract on DIR_HR strips fin_internal columns
    fin_internal_contract = {
        "turn_id": "t-m5-hr",
        "language": "en",
        "persona": "DIR_HR",
        "spoken_summary": "Vendor Acme Ltd invoice INV-9001 is overdue.",
        "display_text": "Vendor Acme Ltd invoice INV-9001 is overdue.",
        "insights": [],
        "sources": [{"kind": "data"}],
        "access": {"status": "allowed"},
        "visual": {
            "type": "table",
            "mode": "replace",
            "table": {
                "columns": ["vendor_name", "invoice_no", "amount_cr"],
                "rows": [{"vendor_name": "Acme Ltd", "invoice_no": "INV-9001", "amount_cr": 12.4}],
            },
        },
    }
    out_dhr = enforce_contract(copy.deepcopy(fin_internal_contract), "DIR_HR")
    assert "vendor_name" not in out_dhr["visual"]["table"]["columns"]
    assert "invoice_no" not in out_dhr["visual"]["table"]["columns"]
    assert "Acme Ltd" not in str(out_dhr)
    assert out_dhr["access"]["status"] == "partial"
    assert out_dhr["access"]["code"] == "R-FUNC"


def test_s1_s2_s3_s4_regressions():
    """S1 (check_access order), S2 (R-POSH/R-MED), S3 (WACC is general_fin), S4 (decide raises UnknownPersona)."""
    from app.access_control import UnknownPersona, check_access

    # S1: topic refusals are not bypassed by self/aggregate-pay regexes
    assert check_access("E1_HR", query="pay scale and salary of each employee in Delhi").status == "refused"
    dec_team = check_access("E3_FIN", query="list my team's APAR ratings")
    assert dec_team.status == "refused"
    assert dec_team.self_emp_id is None

    # S2: R-POSH and R-MED restrict all 8 juniors and return partial/aggregate for DIR_FIN
    assert check_access("E1_HR", entry_id="R-POSH").status == "refused"
    assert check_access("E4_FIN", entry_id="R-MED").status == "refused"
    assert check_access("DIR_FIN", entry_id="R-POSH").status == "partial"

    # S3: WACC is general_fin (allowed for all 11 personas), whereas running a DCF valuation is valuation_run
    for p in PERSONAS_11:
        assert decide(p, ["general_fin"], "What is ONGC's WACC for FY25?").action == "allow"
    assert decide("E1_HR", ["general_fin"], "Run a DCF valuation of ONGC").action == "refuse"

    # S4: decide() raises UnknownPersona on empty, unknown, or un-normalized persona strings
    for bad in ("", None, "E5_HR", "DEMO_ADMIN", "chairman"):
        with pytest.raises(UnknownPersona):
            decide(bad, ["general_hr"])  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "persona",
    ["E1_HR", "E2_HR", "E3_HR", "E4_HR", "E1_FIN", "E2_FIN", "E3_FIN", "E4_FIN"],
)
@pytest.mark.parametrize(
    "query",
    [
        "Average monthly basic pay of E1 officers",          # SPEC-06 Q07
        "What does an E1 officer get on joining?",           # SPEC-06 Q08
        "average salary of E1 officers",                     # P2H.1 §6 packet example
        "joining pay of E1",                                 # reviewer R2-M1 probe
        "Average CTC of E3 executives",
    ],
)
def test_r2_m1_check_access_and_decide_allow_junior_aggregate_pay(persona: str, query: str):
    """R2-M1 (BUG-28): check_access and decide() both allow aggregate pay by grade for all 8 juniors."""
    from app.access_control import check_access

    acc = check_access(persona, query=query)
    assert acc.status == "allowed", f"{persona} x {query!r} -> check_access returned {acc.status} ({acc.code})"
    dec = decide(persona, ["general"], query)
    assert dec.action == "allow", f"{persona} x {query!r} -> decide returned {dec.action} ({dec.code})"


