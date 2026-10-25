"""P2H.3 unit tests for canonical V19 >5-year station tenure definitions (`DELHI_GT5_CONT_V1`,
`STATION_GT5_CONT_V1`), SQL compilation, threshold edge cases (1826 vs 1827 days),
executive vs all-cadres toggle, and reference SQL parity against PA0002_PA0001.csv.
"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path
import re
import sys

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.brain.compiler import EXEC_GRADES, ALL_CADRE_GRADES, GRADE_LEVEL_ORDER, Compiler, get_definition, get_definitions
from app.brain.query_spec import Filter, QuerySpec
from app.config import DATA_BANK_DIR, ROOT_DIR


AS_OF = date(2026, 10, 19)
_CAND_PA = ROOT_DIR.parent / "HR and Finance_ONGC" / "data_bank" / "landing" / "sap" / "PA0002_PA0001.csv"
if not _CAND_PA.exists():
    _CAND_PA = DATA_BANK_DIR / "landing" / "sap" / "PA0002_PA0001.csv"
PA_CSV = _CAND_PA
PA0001_CSV = PA_CSV.parent / "PA0001.csv"


def _load_pa_rows():
    by_emp = {}
    with PA0001_CSV.open("r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            by_emp.setdefault(r["PERNR"], []).append(r)

    cont_from_by_emp = {}
    for emp_id, plist in by_emp.items():
        plist.sort(key=lambda x: x["BEGDA"])
        cur_wc = plist[-1]["WERKS"]
        c_from = plist[-1]["BEGDA"]
        for i in range(len(plist) - 2, -1, -1):
            if plist[i]["WERKS"] == cur_wc:
                c_from = plist[i]["BEGDA"]
            else:
                break
        cont_from_by_emp[emp_id] = c_from

    out = []
    with PA_CSV.open("r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            emp_id = r["PERNR"]
            out.append(
                {
                    **r,
                    "emp_id": emp_id,
                    "employment_status": r["STAT2"],
                    "wc_id": r["WERKS"],
                    "current_grade_id": r["PERSK"],
                    "continuous_from_date": cont_from_by_emp.get(emp_id, "2026-10-19"),
                }
            )
    return out


def test_definitions_registry_loaded():
    """Case 1: definitions.yaml exposes DELHI_GT5_CONT_V1 and STATION_GT5_CONT_V1 with SPEC-07 §4.2 metadata."""
    defs = get_definitions()
    assert "DELHI_GT5_CONT_V1" in defs
    assert "STATION_GT5_CONT_V1" in defs

    d_del = get_definition("DELHI_GT5_CONT_V1")
    assert d_del is not None
    assert d_del["as_of"] == "2026-10-19"
    assert d_del["min_days_exclusive"] == 1826
    assert d_del["wc_id"] == "WC-DEL"
    assert d_del["exemption_handling"] == "counted_not_removed"
    assert d_del["grades_executives"] == ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9"]
    assert d_del["grades_all_cadres"] == [
        "E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "GRP-B", "GRP-C", "GRP-D"
    ]
    assert d_del["board_grades_excluded"] == ["CMD", "DIR"]
    citations = d_del.get("citations") or []
    assert any(c.get("illustrative") is True and "3.2" in str(c.get("section") or c.get("title")) for c in citations)
    assert any(c.get("doc_id") == "J-03" and "Delhi High Court" in str(c.get("title")) for c in citations)


def test_compile_delhi_gt5_executives_default():
    """Case 2: DELHI_GT5_CONT_V1 compiles to > 1826 days, E1..E9 default, and grade_level_order sort."""
    c = Compiler()
    spec = QuerySpec(
        metric="headcount",
        dimensions=["grade"],
        filters=[
            Filter(field="wc", op="=", value="WC-DEL"),
            Filter(field="cadre", op="=", value="executive"),
            Filter(field="station_tenure_years", op=">=", value=5),
        ],
    )
    cq = c.compile(spec)
    assert cq.definition_id == "DELHI_GT5_CONT_V1"
    assert cq.all_cadres is False
    assert cq.station_wc_id == "WC-DEL"
    assert "DATE_DIFF(DATE '2026-10-19', continuous_from_date, DAY) > 1826" in cq.sql
    assert "current_grade_id IN ('E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7', 'E8', 'E9')" in cq.sql
    assert "GRP-C" not in cq.sql
    assert "ORDER BY MIN(grade_level_order) ASC, grade ASC" in cq.sql


def test_compile_delhi_gt5_all_cadres_toggle():
    """Case 3: All-cadres filter expands DELHI_GT5_CONT_V1 to E1..E9 + GRP-B/C/D (excluding CMD/DIR)."""
    c = Compiler()
    spec = QuerySpec(
        metric="headcount",
        dimensions=["grade"],
        filters=[
            Filter(field="wc", op="=", value="WC-DEL"),
            Filter(field="cadre", op="=", value="all"),
            Filter(field="station_tenure_years", op=">=", value=5),
        ],
    )
    cq = c.compile(spec)
    assert cq.definition_id == "DELHI_GT5_CONT_V1"
    assert cq.all_cadres is True
    for g in ALL_CADRE_GRADES:
        assert f"'{g}'" in cq.sql
    assert "'CMD'" not in cq.sql
    assert "'DIR'" not in cq.sql


def test_compile_station_gt5_non_delhi():
    """Case 4: Single non-Delhi station with 5-year tenure filter compiles to STATION_GT5_CONT_V1."""
    c = Compiler()
    spec = QuerySpec(
        metric="headcount",
        dimensions=["grade"],
        filters=[
            Filter(field="wc", op="=", value="WC-MUM"),
            Filter(field="cadre", op="=", value="executive"),
            Filter(field="station_tenure_years", op=">=", value=5),
        ],
    )
    cq = c.compile(spec)
    assert cq.definition_id == "STATION_GT5_CONT_V1"
    assert cq.station_wc_id == "WC-MUM"
    assert "wc_id = 'WC-MUM'" in cq.sql
    assert "DATE_DIFF(DATE '2026-10-19', continuous_from_date, DAY) > 1826" in cq.sql


def test_threshold_edge_1826_excluded_1827_included():
    """Case 5: Strictly > 1826 days excludes 1826 days (2021-10-19) and includes 1827 days (2021-10-18)."""
    d_def = get_definition("DELHI_GT5_CONT_V1")
    min_days = int(d_def["min_days_exclusive"])
    assert min_days == 1826

    def is_included(stay_start: date) -> bool:
        return (AS_OF - stay_start).days > min_days

    start_1826 = AS_OF - timedelta(days=1826)  # 2021-10-19 (exactly 5 calendar years)
    start_1827 = AS_OF - timedelta(days=1827)  # 2021-10-18 (5 years + 1 day)
    assert start_1826 == date(2021, 10, 19)
    assert start_1827 == date(2021, 10, 18)
    assert is_included(start_1826) is False, "1826 days must be excluded under strict > 1826 rule"
    assert is_included(start_1827) is True, "1827 days must be included under strict > 1826 rule"


def test_zero_legacy_60_months_or_retiree_subtraction_in_c1():
    """Case 6: Certified C1 uses DELHI_GT5_CONT_V1 (> 1826 days) and 0 paths use >= 60 months."""
    lib_paths = [
        ROOT_DIR / "yukti" / "backend" / "app" / "brain" / "certified" / "library.yaml",
        ROOT_DIR / "yukti" / "backend" / "certified" / "library.yaml",
    ]
    for lp in lib_paths:
        text = lp.read_text(encoding="utf-8")
        assert not re.search(r"60\s*months|>=\s*60", text, re.I), f"Legacy 60-month threshold found in {lp}"
        data = yaml.safe_load(text)
        queries = data.get("queries") or data.get("certified_queries") or []
        c1 = next(q for q in queries if q["id"] == "C1")
        assert c1.get("definition_id") == "DELHI_GT5_CONT_V1"
        assert "1826" in (c1.get("parameterized_sql") or c1.get("sql") or "")


def test_reference_sql_counts_on_pa0002_fixture():
    """Case 7: Reference SQL counts on PA0002_PA0001.csv match 419 executives and 645 all-cadres."""
    rows = _load_pa_rows()
    del_active = [
        r for r in rows
        if r.get("employment_status") == "Active" and r.get("wc_id") == "WC-DEL"
    ]
    assert len(del_active) == 943

    def stay_days(r) -> int:
        dt = date.fromisoformat(r["continuous_from_date"])
        return (AS_OF - dt).days

    gt5_exec = [
        r for r in del_active
        if stay_days(r) > 1826 and r["current_grade_id"] in EXEC_GRADES
    ]
    gt5_all = [
        r for r in del_active
        if stay_days(r) > 1826 and r["current_grade_id"] in ALL_CADRE_GRADES
    ]
    assert len(gt5_exec) == 419
    assert len(gt5_all) == 645

    by_lvl_exec = {g: 0 for g in EXEC_GRADES}
    for r in gt5_exec:
        by_lvl_exec[r["current_grade_id"]] += 1
    assert by_lvl_exec == {
        "E1": 35, "E2": 90, "E3": 87, "E4": 67, "E5": 57,
        "E6": 35, "E7": 33, "E8": 12, "E9": 3,
    }
    assert sum(by_lvl_exec.values()) == 419


def test_dim_grade_sqlx_and_level_order_mapping():
    """Case 8: dim_grade.sqlx defines grade_level_order matching compiler GRADE_LEVEL_ORDER."""
    sqlx_path = ROOT_DIR / "dataform" / "definitions" / "gold" / "dim_grade.sqlx"
    assert sqlx_path.exists()
    content = sqlx_path.read_text(encoding="utf-8")
    assert "grade_level_order" in content
    assert "WHEN 'E1' THEN 1" in content
    assert "WHEN 'E9' THEN 9" in content
    assert "WHEN 'GRP-D' THEN 12" in content
    assert "WHEN 'CMD' THEN NULL" in content
    assert [g for g, _ in sorted(GRADE_LEVEL_ORDER.items(), key=lambda kv: kv[1])] == [
        "E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "GRP-B", "GRP-C", "GRP-D"
    ]
