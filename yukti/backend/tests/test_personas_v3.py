"""P2H.1 / SPEC-06 §4.1 & §8: 11-persona identity, alias normalization, UnknownPersona, and dim_app_user completeness."""

from __future__ import annotations

import csv
from pathlib import Path
import re
import sys

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.access_control import (
    ALL_PERSONAS_ORDERED,
    JUNIOR_FIN_PERSONAS,
    JUNIOR_HR_PERSONAS,
    JUNIOR_PERSONAS,
    SENIOR_PERSONAS,
    VALID_PERSONAS,
    UnknownPersona,
    normalize_persona,
)
from app.auth import ADMIN_PERSONA_ID, PERSONA_DIRECTORY

REPO_ROOT = Path(__file__).resolve().parents[3]
DIM_APP_USER_CSV = REPO_ROOT / "data_bank" / "landing" / "sap" / "dim_app_user.csv"
APP_USERS_YAML = Path(__file__).resolve().parent.parent / "app" / "brain" / "app_users.yaml"

CANONICAL_11 = [
    "CMD",
    "DIR_HR",
    "DIR_FIN",
    "E1_HR",
    "E2_HR",
    "E3_HR",
    "E4_HR",
    "E1_FIN",
    "E2_FIN",
    "E3_FIN",
    "E4_FIN",
]


def test_valid_personas_exact_11():
    assert set(VALID_PERSONAS) == set(CANONICAL_11)
    assert len(VALID_PERSONAS) == 11
    assert list(ALL_PERSONAS_ORDERED) == CANONICAL_11
    assert set(SENIOR_PERSONAS) == {"CMD", "DIR_HR", "DIR_FIN"}
    assert set(JUNIOR_HR_PERSONAS) == {"E1_HR", "E2_HR", "E3_HR", "E4_HR"}
    assert set(JUNIOR_FIN_PERSONAS) == {"E1_FIN", "E2_FIN", "E3_FIN", "E4_FIN"}
    assert set(JUNIOR_PERSONAS) == set(JUNIOR_HR_PERSONAS) | set(JUNIOR_FIN_PERSONAS)


@pytest.mark.parametrize("persona_id", CANONICAL_11)
def test_canonical_personas_normalize_to_self(persona_id: str):
    assert normalize_persona(persona_id) == persona_id
    assert normalize_persona(persona_id.lower()) == persona_id
    assert normalize_persona(f"  {persona_id}  ") == persona_id


@pytest.mark.parametrize(
    "alias,expected",
    [
        ("cmd", "CMD"),
        ("Chairman & MD", "CMD"),
        ("Chairman and Managing Director", "CMD"),
        ("Director HR", "DIR_HR"),
        ("Director (HR)", "DIR_HR"),
        ("dir-hr", "DIR_HR"),
        ("Director Finance", "DIR_FIN"),
        ("Director (Finance)", "DIR_FIN"),
        ("dir-fin", "DIR_FIN"),
        ("E1 HR officer", "E1_HR"),
        ("e1-hr", "E1_HR"),
        ("E2 HR Executive", "E2_HR"),
        ("e2-hr", "E2_HR"),
        ("E3 HR Officer", "E3_HR"),
        ("e3-hr", "E3_HR"),
        ("E4 HR Manager", "E4_HR"),
        ("e4-hr", "E4_HR"),
        ("E1 Finance Officer", "E1_FIN"),
        ("e1-fin", "E1_FIN"),
        ("E2 Finance Executive", "E2_FIN"),
        ("e2-fin", "E2_FIN"),
        ("E3 Finance Officer", "E3_FIN"),
        ("e3-fin", "E3_FIN"),
        ("E4 Finance Manager", "E4_FIN"),
        ("e4-fin", "E4_FIN"),
    ],
)
def test_persona_aliases_normalize(alias: str, expected: str):
    assert normalize_persona(alias) == expected


@pytest.mark.parametrize(
    "bad_persona",
    [
        "E5_HR",
        "E0_FIN",
        "E6_HR",
        "ADMIN",
        "GUEST",
        "INTERN",
        "SUPERUSER",
        "",
        "   ",
        None,
    ],
)
def test_unknown_persona_raises_never_coerces(bad_persona):
    """BUG-27 / SPEC-06 AC-1: Unknown or empty personas raise UnknownPersona (never coerced to E2_HR or CMD)."""
    with pytest.raises(UnknownPersona):
        normalize_persona(bad_persona)


def test_demo_admin_and_11_personas_in_auth_directory():
    """SPEC-06 AC-2: PERSONA_DIRECTORY contains all 11 personas and ADMIN_PERSONA_ID is DEMO_ADMIN."""
    assert set(PERSONA_DIRECTORY.keys()) == set(CANONICAL_11)
    assert ADMIN_PERSONA_ID == "DEMO_ADMIN"
    for pid in CANONICAL_11:
        entry = PERSONA_DIRECTORY[pid]
        assert bool(entry.get("is_admin", False)) is False
        assert re.fullmatch(r"EMP-\d{6}", entry["emp_id"]), f"Invalid emp_id for {pid}: {entry}"
        assert entry["wc_id"] == "WC-DEL"
        assert entry["display_name"] not in ("", "Chairman & CEO", "Director", "Director (HR)", "Director (Finance)")


def test_dim_app_user_csv_and_yaml_completeness():
    """SPEC-06 AC-2 & D-60: 11 seeded rows in dim_app_user.csv and app_users.yaml pass all completeness flags."""
    assert DIM_APP_USER_CSV.exists(), f"Missing {DIM_APP_USER_CSV}"
    assert APP_USERS_YAML.exists(), f"Missing {APP_USERS_YAML}"

    with DIM_APP_USER_CSV.open("r", encoding="utf-8") as f:
        csv_rows = list(csv.DictReader(f))
    assert len(csv_rows) == 11

    yaml_data = yaml.safe_load(APP_USERS_YAML.read_text(encoding="utf-8"))
    yaml_personas = yaml_data.get("personas") or {}
    assert set(yaml_personas.keys()) == set(CANONICAL_11)

    csv_by_id = {r["persona_id"]: r for r in csv_rows}
    assert set(csv_by_id.keys()) == set(CANONICAL_11)

    # D-66 specific identity checks
    assert csv_by_id["CMD"]["emp_id"] == "EMP-000001"
    assert csv_by_id["CMD"]["display_name"] == "Arun Kumar Singh"
    assert csv_by_id["CMD"]["functional_designation"] == "Chairman & CEO"
    assert csv_by_id["DIR_HR"]["emp_id"] == "EMP-000002"
    assert csv_by_id["DIR_HR"]["display_name"] == "Manish Patil"
    assert csv_by_id["DIR_HR"]["functional_designation"] == "Director (Human Resources)"
    assert csv_by_id["DIR_FIN"]["emp_id"] == "EMP-000003"
    assert csv_by_id["DIR_FIN"]["display_name"] == "Anupam Agarwal"
    assert csv_by_id["DIR_FIN"]["functional_designation"] == "Director (Finance)"
    assert csv_by_id["E2_HR"]["emp_id"] == "EMP-102451"
    assert csv_by_id["E2_HR"]["display_name"] == "Pooja Verma"
    assert csv_by_id["E3_HR"]["emp_id"] == "EMP-100144"
    assert csv_by_id["E3_HR"]["display_name"] == "Lokesh Verma"
    assert csv_by_id["E4_HR"]["emp_id"] == "EMP-100178"
    assert csv_by_id["E4_HR"]["display_name"] == "Umesh D. Bhatia"
    assert csv_by_id["E3_FIN"]["emp_id"] == "EMP-100146"
    assert csv_by_id["E3_FIN"]["display_name"] == "Shailesh E. Kapoor"

    pa_csv = REPO_ROOT / "data_bank" / "landing" / "sap" / "PA0002_PA0001.csv"
    pa_names = {}
    if pa_csv.exists():
        with pa_csv.open("r", encoding="utf-8") as f:
            pa_names = {row["PERNR"]: row["name"] for row in csv.DictReader(f)}

    for pid in CANONICAL_11:
        r = csv_by_id[pid]
        y = yaml_personas[pid]
        assert r["emp_id"] == y["emp_id"] == PERSONA_DIRECTORY[pid]["emp_id"]
        assert r["display_name"] == y["display_name"] == PERSONA_DIRECTORY[pid]["display_name"]
        if pa_names:
            assert y["display_name"] == pa_names[y["emp_id"]], (
                f"{pid} ({y['emp_id']}): display_name {y['display_name']!r} != Employee-360 {pa_names[y['emp_id']]!r}"
            )
        assert r["wc_id"] == "WC-DEL"
        assert str(r["synthetic"]).lower() == "true"
        assert y["synthetic"] is True
        assert int(r["pay_fy26_months"]) >= 12
        assert int(r["posting_rows"]) >= 1
        assert int(r["apar_rows"]) >= 1
        for flag in ("has_pay_fy26", "has_leave_el", "has_posting", "has_apar"):
            assert str(r[flag]).lower() == "true", f"{pid} CSV flag {flag} is not true"
            assert y[flag] is True, f"{pid} YAML flag {flag} is not True"
        for ok_flag in ("ok_pay", "ok_leave", "ok_posting", "ok_apar"):
            assert str(r[ok_flag]).lower() == "true", f"{pid} CSV completeness flag {ok_flag} is not true"
            assert y[ok_flag] is True, f"{pid} YAML completeness flag {ok_flag} is not True"


@pytest.mark.asyncio
async def test_d66_cmd_self_leave_balance_carries_synthetic_label():
    """D-66: CMD asks 'my leave balance' -> answer carries 'Illustrative HR record (synthetic)' in provenance and visible caveat."""
    import time
    from app.answer_composer import validate_and_repair_contract
    from app.brain.pipeline import run_planner_turn
    from app.brain.rbac import OFFICE_HOLDER_SYNTHETIC_LABEL, enforce_contract
    from app.session_memory import get_session_manager

    sess = get_session_manager().get_or_create("s-d66-cmd-leave", persona="CMD", language="en", emp_id="EMP-000001")
    planned = await run_planner_turn(
        query="my leave balance",
        session_state=sess,
        persona="CMD",
        turn_id="t-d66-cmd-leave",
        language="en",
        t0=time.perf_counter(),
    )
    assert planned is not None and "contract" in planned
    contract = enforce_contract(planned["contract"], "CMD", query="my leave balance")
    contract = validate_and_repair_contract(contract)

    assert contract["access"]["status"] == "allowed"
    assert contract.get("provenance", {}).get("label") == "synthetic"
    assert OFFICE_HOLDER_SYNTHETIC_LABEL in str(contract.get("provenance", {}).get("detail", ""))
    assert OFFICE_HOLDER_SYNTHETIC_LABEL in str(contract.get("caveat", ""))
    assert OFFICE_HOLDER_SYNTHETIC_LABEL in str(contract.get("display_text", ""))


@pytest.mark.asyncio
@pytest.mark.parametrize("persona_id", CANONICAL_11)
@pytest.mark.parametrize(
    "query,expected_code",
    [
        ("Show Arun Kumar Singh's APAR rating", "R-APAR"),
        ("Show Arun Kumar Singh's medical records", "R-SENS"),
        ("What is Manish Patil's APAR score?", "R-APAR"),
        ("Show Anupam Agarwal's medical claim history", "R-SENS"),
    ],
)
async def test_d66_office_holder_apar_and_medical_refused_for_every_persona(
    persona_id: str, query: str, expected_code: str
):
    """D-66: Any persona (including CMD and self) asking for Arun Kumar Singh / Manish Patil / Anupam Agarwal APAR or medical is refused."""
    import time
    from app.access_control import check_access
    from app.answer_composer import build_refusal_contract, validate_and_repair_contract
    from app.brain.pipeline import run_planner_turn
    from app.brain.rbac import OFFICE_HOLDER_REFUSAL_COPY, decide
    from app.session_memory import get_session_manager

    pol = decide(persona_id, question=query)
    assert pol.action == "refuse"
    assert pol.code == expected_code
    assert pol.rule_ref == "D-66"
    assert pol.reason == OFFICE_HOLDER_REFUSAL_COPY

    acc = check_access(persona_id, query=query)
    assert acc.status == "refused"
    assert acc.code == expected_code
    assert acc.rule_ref == "D-66"
    assert acc.reason == OFFICE_HOLDER_REFUSAL_COPY

    sess = get_session_manager().get_or_create(f"s-d66-{persona_id}", persona=persona_id, language="en")
    planned = await run_planner_turn(
        query=query,
        session_state=sess,
        persona=persona_id,
        turn_id=f"t-d66-{persona_id}",
        language="en",
        t0=time.perf_counter(),
    )
    assert planned is not None and "contract" in planned
    c = validate_and_repair_contract(planned["contract"])
    assert c["access"]["status"] == "refused"
    assert c["access"]["code"] == expected_code
    assert c["access"]["rule_ref"] == "D-66"
    assert c["access"]["reason"] == OFFICE_HOLDER_REFUSAL_COPY
    assert c["spoken_summary"] == OFFICE_HOLDER_REFUSAL_COPY
    assert c["display_text"] == OFFICE_HOLDER_REFUSAL_COPY

    # Also check self-queries for office-holder personas
    if persona_id in ("CMD", "DIR_HR", "DIR_FIN"):
        for self_q, self_code in [("What is my APAR rating?", "R-APAR"), ("Show my medical records", "R-SENS")]:
            self_pol = decide(persona_id, question=self_q)
            assert self_pol.action == "refuse"
            assert self_pol.code == self_code
            assert self_pol.rule_ref == "D-66"
            assert self_pol.reason == OFFICE_HOLDER_REFUSAL_COPY
            self_acc = check_access(persona_id, query=self_q)
            assert self_acc.status == "refused"
            assert self_acc.reason == OFFICE_HOLDER_REFUSAL_COPY
            ref_c = validate_and_repair_contract(
                build_refusal_contract(code=self_code, persona=persona_id, turn_id="t-self-d66", rule_ref="D-66")
            )
            assert ref_c["spoken_summary"] == OFFICE_HOLDER_REFUSAL_COPY


@pytest.mark.parametrize("qid,expected_code", [("my_apar", "R-APAR"), ("E3", "R-SENS")])
@pytest.mark.parametrize("persona_id", ["CMD", "DIR_HR", "DIR_FIN"])
def test_d66_certified_query_my_apar_and_e3_refused_for_office_holders(
    qid: str, expected_code: str, persona_id: str
):
    """D-66 Bypass 1: run_certified_query('my_apar'/'E3', persona in CMD/DIR_HR/DIR_FIN) is refused with 0 rows."""
    from app.brain.rbac import OFFICE_HOLDER_REFUSAL_COPY
    from app.tools.certified_query import run_certified_query

    res = run_certified_query(qid, persona=persona_id)
    assert res["status"] == "refused"
    assert res["rows"] == []
    assert res["row_count"] == 0
    assert res["access"]["status"] == "refused"
    assert res["access"]["code"] == expected_code
    assert res["access"]["rule_ref"] == "D-66"
    assert res["access"]["reason"] == OFFICE_HOLDER_REFUSAL_COPY
    assert res["deterministic_summary"] == OFFICE_HOLDER_REFUSAL_COPY
    assert res["visual"]["type"] == "refusal"
    assert res["visual"]["rows"] == []


@pytest.mark.parametrize("persona_id", ["CMD", "DIR_HR", "DIR_FIN"])
@pytest.mark.parametrize("qid", ["my_leave_balance", "E1", "my_payslip", "my_postings"])
def test_d66_certified_self_queries_for_office_holders_carry_synthetic_label(persona_id: str, qid: str):
    """D-66: Certified self-queries (e.g. my_leave_balance, E1) for CMD/DIR_HR/DIR_FIN carry 'Illustrative HR record (synthetic)'."""
    from app.brain.rbac import OFFICE_HOLDER_SYNTHETIC_LABEL
    from app.tools.certified_query import get_tool_cache, run_certified_query

    get_tool_cache().clear()
    res = run_certified_query(qid, persona=persona_id)
    assert res.get("status") != "refused"
    assert len(res.get("rows") or []) >= 1
    assert res.get("caveat") == OFFICE_HOLDER_SYNTHETIC_LABEL
    prov = res.get("provenance") or {}
    assert prov.get("label") == "synthetic"
    assert OFFICE_HOLDER_SYNTHETIC_LABEL in str(prov.get("detail", ""))
    assert OFFICE_HOLDER_SYNTHETIC_LABEL in str(res.get("deterministic_summary", ""))


@pytest.mark.parametrize("persona_id", CANONICAL_11)
def test_d66_enforce_contract_and_export_rbac_refuse_office_holder_apar_and_medical(persona_id: str):
    """D-66 Bypasses 2 & 3: enforce_contract and enforce_export_rbac refuse APAR/medical contracts containing EMP-000001..3 even for CMD."""
    from app.brain.rbac import OFFICE_HOLDER_REFUSAL_COPY, enforce_contract
    from app.export_audit import enforce_export_rbac

    apar_contract = {
        "turn_id": "t-d66-apar",
        "persona": persona_id,
        "spoken_summary": "Arun Kumar Singh APAR is 94.6.",
        "display_text": "Arun Kumar Singh APAR is 94.6.",
        "visual": {
            "type": "table",
            "mode": "replace",
            "table": {
                "columns": ["emp_id", "name", "numerical_score", "final_rating"],
                "rows": [
                    {
                        "emp_id": "EMP-000001",
                        "name": "Arun Kumar Singh",
                        "numerical_score": 94.6,
                        "final_rating": "Outstanding",
                    }
                ],
            },
        },
        "access": {"status": "allowed"},
    }
    enforced = enforce_contract(apar_contract, persona_id, query="show CMD APAR")
    assert enforced["access"]["status"] == "refused"
    assert enforced["access"]["code"] == "R-APAR"
    assert enforced["access"]["rule_ref"] == "D-66"
    assert enforced["access"]["reason"] == OFFICE_HOLDER_REFUSAL_COPY
    assert enforced["spoken_summary"] == OFFICE_HOLDER_REFUSAL_COPY
    assert enforced["display_text"] == OFFICE_HOLDER_REFUSAL_COPY
    assert enforced["visual"]["type"] == "refusal"
    assert enforced["visual"]["table"]["rows"] == []

    # Also test data-driven refusal with empty query string (purely from EMP-000001 + APAR columns in rows)
    enforced_no_q = enforce_contract(apar_contract, persona_id, query="")
    assert enforced_no_q["access"]["status"] == "refused"
    assert enforced_no_q["access"]["code"] == "R-APAR"
    assert enforced_no_q["access"]["rule_ref"] == "D-66"
    assert enforced_no_q["visual"]["table"]["rows"] == []

    # Export RBAC check
    masked_c, masked_flag, _, _, _ = enforce_export_rbac(apar_contract, persona_id)
    assert masked_flag is True
    assert masked_c["access"]["status"] == "refused"
    assert masked_c["access"]["code"] == "R-APAR"
    assert masked_c["access"]["rule_ref"] == "D-66"
    assert masked_c["access"]["reason"] == OFFICE_HOLDER_REFUSAL_COPY
    assert masked_c["visual"]["type"] == "refusal"
    assert masked_c["visual"]["table"]["rows"] == []

    # Medical contract containing EMP-000002 (Manish Patil)
    med_contract = {
        "turn_id": "t-d66-med",
        "persona": persona_id,
        "spoken_summary": "Manish Patil medical claim is ₹42,000.",
        "display_text": "Manish Patil medical claim is ₹42,000.",
        "visual": {
            "type": "table",
            "mode": "replace",
            "table": {
                "columns": ["emp_id", "claim_id", "claim_type", "claimed_amount_inr"],
                "rows": [
                    {
                        "emp_id": "EMP-000002",
                        "claim_id": "CLM-001",
                        "claim_type": "OPD",
                        "claimed_amount_inr": 42000,
                    }
                ],
            },
        },
        "access": {"status": "allowed"},
    }
    enforced_med = enforce_contract(med_contract, persona_id)
    assert enforced_med["access"]["status"] == "refused"
    assert enforced_med["access"]["code"] == "R-SENS"
    assert enforced_med["access"]["rule_ref"] == "D-66"
    assert enforced_med["visual"]["table"]["rows"] == []

    masked_med, med_flag, _, _, _ = enforce_export_rbac(med_contract, persona_id)
    assert med_flag is True
    assert masked_med["access"]["status"] == "refused"
    assert masked_med["access"]["code"] == "R-SENS"
    assert masked_med["access"]["rule_ref"] == "D-66"
    assert masked_med["visual"]["table"]["rows"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hi_query,expected_code",
    [
        ("अरुण कुमार सिंह का एपार दिखाओ", "R-APAR"),
        ("अरुण कुमार सिंह का वार्षिक कार्य निष्पादन मूल्यांकन", "R-APAR"),
        ("मनीष पाटिल का मेडिकल रिकॉर्ड दिखाओ", "R-SENS"),
        ("अनुपम अग्रवाल के स्वास्थ्य बीमा दावे", "R-SENS"),
        ("चेयरमैन का एपीएआर रेटिंग क्या है?", "R-APAR"),
        ("निदेशक (मानव संसाधन) का चिकित्सा दावा", "R-SENS"),
        ("निदेशक एचआर का एपार स्कोर", "R-APAR"),
        ("निदेशक (वित्त) का मेडिकल क्लेम", "R-SENS"),
        ("अध्यक्ष का एपीएआर दिखाओ", "R-APAR"),
        ("सीएमडी का स्वास्थ्य बीमा दावा", "R-SENS"),
    ],
)
async def test_d66_all_hindi_and_hinglish_queries_refused(hi_query: str, expected_code: str):
    """D-66 Bypass 4: All 6 Hindi queries from the review (plus title/medical/APAR variants) are refused."""
    import time
    from app.access_control import check_access
    from app.brain.pipeline import run_planner_turn
    from app.brain.rbac import OFFICE_HOLDER_REFUSAL_COPY, decide
    from app.session_memory import get_session_manager

    for persona_id in ("CMD", "DIR_HR", "DIR_FIN", "E2_HR"):
        pol = decide(persona_id, question=hi_query)
        assert pol.action == "refuse", f"Expected refuse for {persona_id} on {hi_query!r}, got {pol}"
        assert pol.code == expected_code
        assert pol.rule_ref == "D-66"
        assert pol.reason == OFFICE_HOLDER_REFUSAL_COPY

        acc = check_access(persona_id, query=hi_query)
        assert acc.status == "refused"
        assert acc.code == expected_code
        assert acc.rule_ref == "D-66"

    sess = get_session_manager().get_or_create("s-d66-hi", persona="CMD", language="hi")
    planned = await run_planner_turn(
        query=hi_query,
        session_state=sess,
        persona="CMD",
        turn_id="t-d66-hi",
        language="hi",
        t0=time.perf_counter(),
    )
    assert planned is not None and "contract" in planned
    c = planned["contract"]
    assert c["access"]["status"] == "refused"
    assert c["access"]["code"] == expected_code
    assert c["access"]["rule_ref"] == "D-66"
    assert c["spoken_summary"] == OFFICE_HOLDER_REFUSAL_COPY

    # Also test Hindi self-queries ('मेरा' / 'मेरी') when caller is an office-holder
    for oh_persona in ("CMD", "DIR_HR", "DIR_FIN"):
        for self_hi, scode in [("मेरा एपीएआर दिखाओ", "R-APAR"), ("मेरी मेडिकल क्लेम स्थिति क्या है?", "R-SENS")]:
            spol = decide(oh_persona, question=self_hi)
            assert spol.action == "refuse"
            assert spol.code == scode
            assert spol.rule_ref == "D-66"


def test_d66_non_regression_salary_refusal_aggregate_apar_and_junior_self_apar():
    """D-66 Non-Regression:
    1. E2_HR is still refused another employee's salary;
    2. CMD can still see aggregate APAR distributions (no named office-holder rows);
    3. Junior self-APAR still works.
    """
    from app.access_control import check_access
    from app.brain.rbac import decide, enforce_contract
    from app.tools.certified_query import get_tool_cache, run_certified_query

    # 1. E2_HR refused another employee's salary
    sal_q = "What is Lokesh Verma's salary?"
    sal_pol = decide("E2_HR", question=sal_q)
    assert sal_pol.action == "refuse"
    assert sal_pol.code == "R-PAY"
    sal_acc = check_access("E2_HR", query=sal_q)
    assert sal_acc.status == "refused"
    assert sal_acc.code == "R-PAY"

    # 2. CMD can still see aggregate APAR distributions (no named office-holder rows)
    agg_q = "Show APAR rating distribution by grade"
    agg_pol = decide("CMD", question=agg_q)
    assert agg_pol.action == "allow"
    agg_contract = {
        "turn_id": "t-cmd-agg-apar",
        "persona": "CMD",
        "spoken_summary": "Average APAR score across grades is 86.2.",
        "display_text": "Average APAR score across grades is 86.2.",
        "visual": {
            "type": "table",
            "mode": "replace",
            "table": {
                "columns": ["grade_id", "headcount", "avg_apar_score"],
                "rows": [
                    {"grade_id": "E1", "headcount": 420, "avg_apar_score": 85.4},
                    {"grade_id": "E2", "headcount": 510, "avg_apar_score": 86.8},
                ],
            },
        },
        "access": {"status": "allowed"},
    }
    agg_enforced = enforce_contract(agg_contract, "CMD", query=agg_q)
    assert agg_enforced["access"]["status"] == "allowed"
    assert len(agg_enforced["visual"]["table"]["rows"]) == 2

    # 3. Junior self-APAR still works
    jr_pol = decide("E2_HR", question="Show my APAR ratings", data_classes=["self"], self_emp_id="EMP-102451")
    assert jr_pol.action == "allow"
    get_tool_cache().clear()
    jr_res = run_certified_query("my_apar", persona="E2_HR")
    assert jr_res.get("status") != "refused"
    assert len(jr_res.get("rows") or []) >= 1
    assert all(r.get("emp_id") == "EMP-102451" for r in jr_res["rows"])

