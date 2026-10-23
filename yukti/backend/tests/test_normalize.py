"""Unit tests for query normalisation and FY resolution (Task Packet B1.3 §5.1 & §5.2)."""

from datetime import date
from pathlib import Path
import sys
import pytest

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.semantic.normalize import (
    current_fy,
    fiscal_years_for_sql,
    fy_of,
    last_complete_fy,
    normalize_categorical_filters,
    resolve_fy,
)

CASES_RESOLVE_FY = [
    ("What was ONGC's profit last year?", None, {"fy": "FY26"}),
    ("previous financial year revenue", None, {"fy": "FY26"}),
    ("pichle saal ka profit", None, {"fy": "FY26"}),
    ("How are we tracking against MoU targets this year?", None, {"fy": "FY27", "ytd": True}),
    ("this year", ["FY24", "FY25", "FY26"], {"fy": "FY26"}),
    ("current year capex", ["FY25", "FY26", "FY27"], {"fy": "FY27", "ytd": True}),
    ("capex in the last 5 years", None, {"from": "FY22", "to": "FY26", "n_years": 5}),
    ("past three years", None, {"from": "FY24", "to": "FY26", "n_years": 3}),
    ("pichle 5 saal", None, {"from": "FY22", "to": "FY26", "n_years": 5}),
    ("FY25 revenue", None, {"fy": "FY25"}),
    ("fy 25", None, {"fy": "FY25"}),
    ("FY2025", None, {"fy": "FY25"}),
    ("FY 2024-25", None, {"fy": "FY25"}),
    ("2024-25", None, {"fy": "FY25"}),
    ("headcount as of 2026-10-19", None, None),
    ("year before last", None, {"fy": "FY25"}),
    ("plan for next year", None, {"fy": "FY28"}),
    ("headcount in Delhi", None, None),
]


@pytest.mark.parametrize("text,available,expected", CASES_RESOLVE_FY)
def test_resolve_fy(text, available, expected):
    assert resolve_fy(text, available=available) == expected


# P0.2 (BUG-20): `YYYY-YY` / `FY YYYY-YY` name ONE Indian FY; ranges need FY on both sides or a range word.
CASES_RESOLVE_FY_P02 = [
    ("Show the balance sheet for FY 2024-25", {"fy": "FY25"}),
    ("revenue 2024-25", {"fy": "FY25"}),
    ("FY2024–25 cash flow", {"fy": "FY25"}),
    ("FY2024-25 profit", {"fy": "FY25"}),
    ("FY 2023-24 ka balance sheet dikhao", {"fy": "FY24"}),
    ("वित्त वर्ष 2024-25 का लाभ", {"fy": "FY25"}),
    ("FY22 to FY25 revenue", {"from": "FY22", "to": "FY25", "n_years": 4}),
    ("FY2022–FY2025 trend", {"from": "FY22", "to": "FY25", "n_years": 4}),
    ("FY24-FY25 comparison", {"from": "FY24", "to": "FY25", "n_years": 2}),
    ("capex over the last 5 years", {"from": "FY22", "to": "FY26", "n_years": 5}),
    ("pichle 3 saal ka revenue", {"from": "FY24", "to": "FY26", "n_years": 3}),
    ("profit in 2024", {"fy": "FY24"}),
]


@pytest.mark.parametrize("text,expected", CASES_RESOLVE_FY_P02)
def test_resolve_fy_single_fy_forms(text, expected):
    assert resolve_fy(text) == expected


def test_fy_helpers():
    assert current_fy() == "FY27"
    assert last_complete_fy() == "FY26"
    assert fy_of(date(2026, 3, 31)) == 26
    assert fy_of(date(2026, 4, 1)) == 27


# Synthetic catalog fixture for §5.2
CAT = {
    "tables": {
        "hrfin_gold.ssot_workforce_employee": {
            "columns": {
                "employment_status": {"type": "STRING", "values": ["Active", "Separated"]},
                "cadre": {"type": "STRING", "values": ["executive", "non_executive", "board"]},
                "emp_name": {"type": "STRING", "distinct": 40000},
                "fiscal_year_joined": {"type": "STRING", "values": ["FY20", "FY21"]},
            }
        },
        "hrfin_silver.employee_master": {
            "columns": {
                "employment_status": {"type": "STRING", "values": ["active", "separated"]}
            }
        },
        "hrfin_gold.ssot_field_economics_360": {
            "columns": {
                "fiscal_year": {"type": "STRING", "values": ["FY25", "FY26"]}
            }
        },
    }
}
E = "FROM hrfin_gold.ssot_workforce_employee"


def test_categorical_normalizer_case_1():
    sql = f"SELECT 1 {E} WHERE employment_status = 'active'"
    res = normalize_categorical_filters(sql, CAT)
    assert "employment_status = 'Active'" in res


def test_categorical_normalizer_case_2():
    sql = f"SELECT 1 {E} WHERE cadre='Executive'"
    res = normalize_categorical_filters(sql, CAT)
    assert "cadre = 'executive'" in res


def test_categorical_normalizer_case_3():
    sql = f"SELECT 1 {E} WHERE LOWER(cadre) = 'Executive'"
    res = normalize_categorical_filters(sql, CAT)
    assert "LOWER(cadre) = 'executive'" in res


def test_categorical_normalizer_case_4():
    sql = f"SELECT 1 {E} WHERE employment_status IN ('active','SEPARATED')"
    res = normalize_categorical_filters(sql, CAT)
    assert "employment_status IN ('Active', 'Separated')" in res


def test_categorical_normalizer_case_5():
    sql = f"SELECT 1 {E} WHERE employment_status NOT IN ('active')"
    res = normalize_categorical_filters(sql, CAT)
    assert "employment_status NOT IN ('Active')" in res


def test_categorical_normalizer_case_6():
    sql = (
        "SELECT 1 FROM hrfin_gold.ssot_workforce_employee e "
        "JOIN hrfin_silver.employee_master m ON e.emp_id = m.emp_id "
        "WHERE e.employment_status = 'Active'"
    )
    res = normalize_categorical_filters(sql, CAT)
    assert "LOWER(e.employment_status) = 'active'" in res


def test_categorical_normalizer_case_7_unknown_value():
    sql = f"SELECT 1 {E} WHERE employment_status = 'retired'"
    res = normalize_categorical_filters(sql, CAT)
    assert res == sql


def test_categorical_normalizer_case_8_not_profiled():
    sql = f"SELECT 1 {E} WHERE emp_name = 'abc'"
    res = normalize_categorical_filters(sql, CAT)
    assert res == sql


def test_categorical_normalizer_case_9_unknown_table():
    sql = "SELECT 1 FROM hrfin_gold.mart_postings WHERE employment_status = 'active'"
    res = normalize_categorical_filters(sql, CAT)
    assert res == sql


def test_categorical_normalizer_case_10_alias():
    sql = f"SELECT 1 {E} e WHERE e.cadre = 'EXECUTIVE'"
    res = normalize_categorical_filters(sql, CAT)
    assert "e.cadre = 'executive'" in res


def test_categorical_normalizer_case_11_backticks_and_project():
    sql = (
        "SELECT 1 FROM `ongc-hr-finance-agent.hrfin_gold.ssot_workforce_employee` "
        "WHERE employment_status = 'active'"
    )
    res = normalize_categorical_filters(sql, CAT)
    assert "'Active'" in res


def test_categorical_normalizer_case_12_idempotence():
    cases_1_to_6 = [
        f"SELECT 1 {E} WHERE employment_status = 'active'",
        f"SELECT 1 {E} WHERE cadre='Executive'",
        f"SELECT 1 {E} WHERE LOWER(cadre) = 'Executive'",
        f"SELECT 1 {E} WHERE employment_status IN ('active','SEPARATED')",
        f"SELECT 1 {E} WHERE employment_status NOT IN ('active')",
        (
            "SELECT 1 FROM hrfin_gold.ssot_workforce_employee e "
            "JOIN hrfin_silver.employee_master m ON e.emp_id = m.emp_id "
            "WHERE e.employment_status = 'Active'"
        ),
    ]
    for sql in cases_1_to_6:
        first = normalize_categorical_filters(sql, CAT)
        second = normalize_categorical_filters(first, CAT)
        assert second == first


def test_categorical_normalizer_case_13_fiscal_years_for_sql():
    assert fiscal_years_for_sql("SELECT 1 FROM hrfin_gold.ssot_field_economics_360", CAT) == ["FY25", "FY26"]
    assert fiscal_years_for_sql("SELECT 1 FROM hrfin_gold.unknown_table", CAT) == []
