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

    # D-60 specific identity checks
    assert csv_by_id["CMD"]["emp_id"] == "EMP-000001"
    assert csv_by_id["CMD"]["display_name"] == "Arun Mehra"
    assert csv_by_id["DIR_HR"]["emp_id"] == "EMP-000002"
    assert csv_by_id["DIR_HR"]["display_name"] == "Manish Deshpande"
    assert csv_by_id["DIR_FIN"]["emp_id"] == "EMP-000003"
    assert csv_by_id["DIR_FIN"]["display_name"] == "Vivek Rao"
    assert csv_by_id["E2_HR"]["emp_id"] == "EMP-102451"
    assert csv_by_id["E2_HR"]["display_name"] == "Pooja Verma"
    assert csv_by_id["E3_FIN"]["emp_id"] == "EMP-100146"
    assert csv_by_id["E3_FIN"]["display_name"] == "Asha Mishra"

    for pid in CANONICAL_11:
        r = csv_by_id[pid]
        y = yaml_personas[pid]
        assert r["emp_id"] == y["emp_id"] == PERSONA_DIRECTORY[pid]["emp_id"]
        assert r["display_name"] == y["display_name"] == PERSONA_DIRECTORY[pid]["display_name"]
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
