"""P2H.3 V19 turns 1–3 chain & 11-persona RBAC matrix tests (SPEC-07 §4.1–4.3, §4.6, §4.7;
BEH-02.01–.04, .10, .16, .17, .20–.24, .30–.32; BUG-34).

Uses deterministic fixture execution backed by `data_bank/landing/sap/PA0002_PA0001.csv` so
all chain and RBAC tests run offline with exact SSOT numbers (`943` Delhi active, `419`
executives >5 yrs, `645` all cadres >5 yrs).
"""

from __future__ import annotations

import asyncio
import csv
from datetime import date
from functools import lru_cache
from pathlib import Path
import re
import sys
from typing import Any, Dict, List

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth import principal_for_persona
from app.brain.compiler import ALL_CADRE_GRADES, EXEC_GRADES, GRADE_LEVEL_ORDER, CompiledQuery, Compiler, QueryResult
from app.brain.planner import Plan, Planner
from app.brain.presenter import ALL_NON_BOARD_LEVELS, EXEC_LEVELS, LEVEL_CHART_NOTE
from app.config import DATA_BANK_DIR, ROOT_DIR
from app.turn_runner import AgentTurnRunner


AS_OF = date(2026, 10, 19)
_CAND_PA = ROOT_DIR.parent / "HR and Finance_ONGC" / "data_bank" / "landing" / "sap" / "PA0002_PA0001.csv"
if not _CAND_PA.exists():
    _CAND_PA = DATA_BANK_DIR / "landing" / "sap" / "PA0002_PA0001.csv"
PA_CSV = _CAND_PA
PA0001_CSV = PA_CSV.parent / "PA0001.csv"

ALL_11_PERSONAS = [
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


@lru_cache(maxsize=1)
def _fixture_employees() -> List[Dict[str, Any]]:
    by_emp: Dict[str, List[Dict[str, str]]] = {}
    with PA0001_CSV.open("r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            by_emp.setdefault(r["PERNR"], []).append(r)

    cont_from_by_emp: Dict[str, str] = {}
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

    rows: List[Dict[str, Any]] = []
    with PA_CSV.open("r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("STAT2") != "Active":
                continue
            emp_id = r["PERNR"]
            c_from = date.fromisoformat(cont_from_by_emp.get(emp_id, "2026-10-19"))
            stay_days = (AS_OF - c_from).days
            stay_yrs = round(stay_days / 365.25, 2)
            tot_yrs = float(r.get("total_tenure_years") or 0.0)
            ret_dt_str = r.get("retirement_date")
            if ret_dt_str:
                ytr = round((date.fromisoformat(ret_dt_str) - AS_OF).days / 365.25, 1)
            else:
                ytr = 10.0
            g = str(r.get("PERSK") or "").strip().upper()
            desig = r.get("current_designation") or g
            ex_tag = r.get("exemption_tag")
            if ex_tag in ("", "None", "null"):
                ex_tag = None
            is_ret_3y = ytr <= 3.0
            is_sup_ex = bool(ex_tag and "superannuation" in ex_tag.lower())
            wc_id = r.get("WERKS", "")
            disc_id = r.get("discipline_id", "")
            cadre = "Executive" if g in EXEC_GRADES else ("Board" if g in ("CMD", "DIR") else "Non-Executive")
            rows.append(
                {
                    "emp_id": emp_id,
                    "emp_name": r["name"],
                    "name": r["name"],
                    "functional_designation": desig,
                    "designation": desig,
                    "current_designation": desig,
                    "current_grade_id": g,
                    "grade": g,
                    "grade_level_order": GRADE_LEVEL_ORDER.get(g),
                    "cadre": cadre,
                    "discipline_id": disc_id,
                    "discipline_name": disc_id,
                    "discipline": disc_id,
                    "wc_id": wc_id,
                    "wc_name": wc_id,
                    "work_centre": wc_id,
                    "continuous_from_date": c_from,
                    "stay_days": stay_days,
                    "continuous_stay_years": round(stay_yrs, 1),
                    "delhi_tenure_years": round(stay_yrs, 1),
                    "station_tenure_years": round(stay_yrs, 1),
                    "total_tenure_years": round(tot_yrs, 1),
                    "ongc_tenure_years": round(tot_yrs, 1),
                    "years_to_retirement": round(ytr, 1),
                    "is_retiring_within_3yr": is_ret_3y,
                    "retiring_within_3yr": is_ret_3y,
                    "is_superannuation_exempt": is_sup_ex,
                    "exemption_tag": ex_tag,
                    "exemption": ex_tag,
                }
            )
    return rows


def _mock_compile_execute(compiled: CompiledQuery) -> QueryResult:
    """Offline SQL evaluator over PA0002_PA0001.csv matching CompiledQuery semantics."""
    sql = compiled.sql
    emps = list(_fixture_employees())

    # Filter by wc_id
    m_wc = re.search(r"wc_id\s*=\s*'([^']+)'", sql)
    if m_wc:
        wc_target = m_wc.group(1)
        emps = [e for e in emps if e["wc_id"] == wc_target]

    # Filter by discipline_id (e.g. DIR_FIN function scope)
    m_disc = re.search(r"discipline_id\s*=\s*'([^']+)'", sql)
    if m_disc:
        d_target = m_disc.group(1)
        emps = [e for e in emps if e["discipline_id"] == d_target]

    # Filter by strict > 1826 days
    if "1826" in sql:
        emps = [e for e in emps if e["stay_days"] > 1826]
    elif "continuous_stay_years >= 5" in sql:
        emps = [e for e in emps if e["continuous_stay_years"] >= 5.0]

    # Filter by grade list or cadre
    if "'GRP-B'" in sql and "'E1'" in sql:
        emps = [e for e in emps if e["grade"] in ALL_CADRE_GRADES]
    elif "'E1'" in sql and "'E9'" in sql:
        emps = [e for e in emps if e["grade"] in EXEC_GRADES]
    elif "LOWER(cadre) = LOWER('executive')" in sql:
        emps = [e for e in emps if e["cadre"].lower() == "executive"]

    if compiled.dims == [("grade", "grade")]:
        by_g: Dict[str, int] = {}
        for e in emps:
            g = e["grade"]
            by_g[g] = by_g.get(g, 0) + 1
        out_rows = [
            {"grade": g, "headcount": cnt, "_n": cnt}
            for g, cnt in sorted(by_g.items(), key=lambda kv: (GRADE_LEVEL_ORDER.get(kv[0], 99), kv[0]))
        ]
        return QueryResult(columns=["grade", "headcount"], rows=out_rows)

    if not compiled.dims and compiled.value_columns == ["headcount"]:
        return QueryResult(
            columns=["headcount"],
            rows=[{"headcount": len(emps)}],
        )

    # Row grain (roster)
    emps_sorted = sorted(
        emps,
        key=lambda e: (-float(e["delhi_tenure_years"]), str(e["emp_id"])),
    )
    row_keys = [
        "emp_id", "name", "functional_designation", "designation", "current_designation",
        "grade", "grade_level_order", "discipline_id", "discipline", "work_centre",
        "ongc_tenure_years", "delhi_tenure_years", "station_tenure_years",
        "years_to_retirement", "retiring_within_3yr", "is_superannuation_exempt", "exemption",
    ]
    n_tot = len(emps_sorted)
    out_rows = [
        {**{k: e.get(k) for k in row_keys}, "_total_rows": n_tot}
        for e in emps_sorted
    ]
    return QueryResult(columns=row_keys + ["_total_rows"], rows=out_rows)


@pytest.fixture()
def v19_runner(monkeypatch):
    """Provides an offline AgentTurnRunner with YUKTI_PLANNER=1 and deterministic PA0002_PA0001 execution."""
    monkeypatch.setenv("YUKTI_PLANNER", "1")
    monkeypatch.setenv("YUKTI_RESULT_CACHE", "0")

    async def fake_execute(self, compiled: CompiledQuery) -> QueryResult:
        return _mock_compile_execute(compiled)

    async def fake_planner_call(self, prompt: str) -> Dict[str, Any]:
        return {}

    monkeypatch.setattr(Compiler, "execute", fake_execute)
    monkeypatch.setattr(Planner, "_call", fake_planner_call)
    return AgentTurnRunner(model_name="gemini-2.5-flash")


@pytest.mark.parametrize(
    "phrasing",
    [
        "How many employees are here in Delhi across different levels? Draw a histogram",
        "Show Delhi staff by level",
        "Employees in Delhi across levels",
    ],
)
def test_v19_t1_three_phrasings_ordered_column_chart(v19_runner, phrasing):
    """SPEC-07 AC-1 & BEH-02.01/.04/.30/.31 (BUG-34): all 3 T1 phrasings return ordered E1..GRP-D column chart."""
    sid = f"v19-t1-{abs(hash(phrasing)) % 10000}"
    c = asyncio.run(
        v19_runner.execute_turn_async(
            phrasing, session_id=sid, persona="CMD", principal=principal_for_persona("CMD")
        )
    )
    vis = c["visual"]
    assert vis["type"] == "chart"
    ch = vis["chart"]
    assert ch["kind"] == "column", f"Expected column chart for '{phrasing}', got {ch['kind']}"
    assert "age" not in (vis.get("title") or "").lower(), "Legacy age histogram must never appear (BEH-02.30)"
    assert ch.get("x_order") == "explicit"
    assert ch.get("note") == LEVEL_CHART_NOTE
    assert ch.get("footnote") == "Also in Delhi: CMD 1, Directors 2"

    x_levels = [r["grade"] for r in ch["data"]]
    assert x_levels == ALL_NON_BOARD_LEVELS
    assert sum(int(r["headcount"]) for r in ch["data"]) == 940  # 943 minus CMD (1) and DIR (2)
    assert any("Delhi: 943 staff; E3 is the largest executive level (154)" in ins for ins in c.get("insights", []))
    dd_labels = [d["label"] for d in c.get("drilldowns") or []]
    assert "More than 5 years in Delhi" in dd_labels


def test_v19_turns_1_to_5_and_cohort_lifecycle_cmd(v19_runner):
    """SPEC-07 AC-1..3 & §4.6 C-1..C-8: full T1 -> T2 -> T2b -> T3 -> replot -> restore chain for CMD."""
    sid = "v19-chain-cmd"
    p_cmd = principal_for_persona("CMD")

    # Turn 1: Delhi across levels (creates root cohort C0)
    t1 = asyncio.run(
        v19_runner.execute_turn_async(
            "How many employees are here in Delhi across different levels? Draw a histogram",
            session_id=sid,
            persona="CMD",
            principal=p_cmd,
        )
    )
    st = v19_runner.session_manager.get_or_create(sid, persona="CMD", emp_id=p_cmd.emp_id)
    assert st.active_cohort_id == "C0"
    c0 = st.get_cohort("C0")
    assert c0 is not None and c0["parent_cohort_id"] is None
    assert c0["row_count"] == 943
    assert c0["emp_id"] == p_cmd.emp_id

    # Turn 2: >5 years follow-up (creates child cohort C1 under C0 with DELHI_GT5_CONT_V1)
    t2 = asyncio.run(
        v19_runner.execute_turn_async(
            "How many of these have been in Delhi for more than 5 years?",
            session_id=sid,
            persona="CMD",
            principal=p_cmd,
        )
    )
    assert t2.get("definition_id") == "DELHI_GT5_CONT_V1"
    kpis = t2["visual"].get("kpis") or []
    assert kpis and kpis[0]["value"] == 419
    assert "419 executives (645 including non-executive staff)" in str(kpis[0].get("delta") or "")
    ch2 = t2["visual"]["chart"]
    assert ch2["kind"] == "column"
    assert [r["grade"] for r in ch2["data"]] == EXEC_LEVELS
    assert [int(r["headcount"]) for r in ch2["data"]] == [35, 90, 87, 67, 57, 35, 33, 12, 3]
    assert sum(int(r["headcount"]) for r in ch2["data"]) == 419

    # Check rule sentence + Illustrative JRTP 3.2 + real Delhi HC 2018 J-03
    combined_text = f"{t2['spoken_summary']} {t2['display_text']} {t2.get('caveat', '')}"
    assert "419" in combined_text and "645" in combined_text
    assert "1,826 days" in combined_text
    assert "Illustrative" in combined_text and "3.2" in combined_text
    assert "Delhi High Court" in combined_text
    dd2_labels = [d["label"] for d in t2.get("drilldowns") or []]
    for expected_chip in ("Show the names", "Include all cadres", "Export to Excel", "Draft email to Director (HR)"):
        assert expected_chip in dd2_labels

    assert st.active_cohort_id == "C1"
    c1 = st.get_cohort("C1")
    assert c1 is not None and c1["parent_cohort_id"] == "C0"
    assert c1["definition_id"] == "DELHI_GT5_CONT_V1"
    assert c1["row_count"] == 419

    # Turn 2b: "Include all cadres" chip -> sibling cohort C1' (645 total)
    t2_all = asyncio.run(
        v19_runner.execute_turn_async(
            "Include all cadres",
            session_id=sid,
            persona="CMD",
            principal=p_cmd,
        )
    )
    assert t2_all.get("definition_id") == "DELHI_GT5_CONT_V1"
    ch2_all = t2_all["visual"]["chart"]
    assert [r["grade"] for r in ch2_all["data"]] == ALL_NON_BOARD_LEVELS
    assert sum(int(r["headcount"]) for r in ch2_all["data"]) == 645
    assert st.active_cohort_id == "C1'"
    c1_prime = st.get_cohort("C1'")
    assert c1_prime is not None and c1_prime["parent_cohort_id"] == "C0"
    assert c1_prime["row_count"] == 645

    # Activate C1 again and run Turn 3: "Give me their names"
    st.active_cohort_id = "C1"
    st.spec_history.append(dict(c1["spec"]))
    t3 = asyncio.run(
        v19_runner.execute_turn_async(
            "Give me their names",
            session_id=sid,
            persona="CMD",
            principal=p_cmd,
        )
    )
    tbl3 = t3["visual"]["table"]
    assert tbl3["total_rows"] == 419
    assert len(tbl3["rows"]) == 419
    expected_visible = [
        "name",
        "functional_designation",
        "grade",
        "ongc_tenure_years",
        "delhi_tenure_years",
        "years_to_retirement",
        "exemption",
    ]
    assert tbl3["columns"][:7] == expected_visible
    assert tbl3["hidden_columns"] == ["emp_id", "discipline"]
    assert tbl3["columns"] == expected_visible + ["emp_id", "discipline"]
    assert tbl3["column_labels"] == {
        "name": "Name",
        "functional_designation": "Designation",
        "grade": "Level",
        "ongc_tenure_years": "ONGC service (yrs)",
        "delhi_tenure_years": "Tenure in Delhi (yrs)",
        "years_to_retirement": "Years to retirement",
        "exemption": "Exemption",
    }
    assert tbl3["default_sort"] == {"key": "delhi_tenure_years", "dir": "desc"}
    assert tbl3["as_of"] == "2026-10-19"
    tenures = [float(r["delhi_tenure_years"]) for r in tbl3["rows"]]
    assert tenures == sorted(tenures, reverse=True)

    # C-3: Re-plot does not change active_cohort_id or lose level_rows
    cohorts_before = len(st.cohorts)
    asyncio.run(
        v19_runner.execute_turn_async(
            "Plot this as a bar chart",
            session_id=sid,
            persona="CMD",
            principal=p_cmd,
        )
    )
    assert st.active_cohort_id == "C1"
    assert len(st.cohorts) == cohorts_before
    assert len(st.get_cohort("C1")["level_rows"]) == 9

    # C-2: "Go back to all Delhi staff" restores C0
    t_back = asyncio.run(
        v19_runner.execute_turn_async(
            "Go back to all Delhi staff",
            session_id=sid,
            persona="CMD",
            principal=p_cmd,
        )
    )
    assert t_back["visual"]["mode"] == "restore"
    assert st.active_cohort_id == "C0"

    # C-8: New principal login clears cohorts
    p_e2 = principal_for_persona("E2_HR")
    st.ensure_principal(persona="E2_HR", emp_id=p_e2.emp_id)
    assert st.cohorts == []
    assert st.active_cohort_id is None


def test_v19_non_delhi_station_variant_mumbai(v19_runner):
    """BEH-02.17: Mumbai chain uses STATION_GT5_CONT_V1 and switches column label to 'Tenure at Mumbai (yrs)'."""
    sid = "v19-mumbai-cmd"
    p_cmd = principal_for_persona("CMD")

    t1 = asyncio.run(
        v19_runner.execute_turn_async(
            "How many employees are here in Mumbai across different levels? Draw a histogram",
            session_id=sid,
            persona="CMD",
            principal=p_cmd,
        )
    )
    assert t1["visual"]["chart"]["kind"] == "column"

    t2 = asyncio.run(
        v19_runner.execute_turn_async(
            "How many of these have been in Mumbai for more than 5 years?",
            session_id=sid,
            persona="CMD",
            principal=p_cmd,
        )
    )
    assert t2.get("definition_id") == "STATION_GT5_CONT_V1"

    t3 = asyncio.run(
        v19_runner.execute_turn_async(
            "Give me their names",
            session_id=sid,
            persona="CMD",
            principal=p_cmd,
        )
    )
    tbl3 = t3["visual"]["table"]
    assert "station_tenure_years" in tbl3["columns"]
    assert "delhi_tenure_years" not in tbl3["columns"]
    assert tbl3["column_labels"]["station_tenure_years"] == "Tenure at Mumbai (yrs)"
    assert tbl3["default_sort"] == {"key": "station_tenure_years", "dir": "desc"}


@pytest.mark.parametrize("persona", ALL_11_PERSONAS)
@pytest.mark.parametrize("turn_step", ["T1", "T2", "T3"])
def test_v19_rbac_11_personas_x_3_turns(v19_runner, persona: str, turn_step: str):
    """SPEC-07 §4.7 & BEH-02.20–.24: 11 personas × 3 turns = 33 RBAC cases."""
    sid = f"v19-rbac-{persona}-{turn_step}"
    principal = principal_for_persona(persona)

    # Always run up to the target turn_step in sequence so session context is realistic
    c1 = asyncio.run(
        v19_runner.execute_turn_async(
            "How many employees are here in Delhi across different levels? Draw a histogram",
            session_id=sid,
            persona=persona,
            principal=principal,
        )
    )
    if turn_step == "T1":
        c = c1
        assert c["access"]["status"] in ("allowed", "partial")
        assert c["visual"]["chart"]["kind"] == "column"
        insights_str = " ".join(c.get("insights", []))
        assert "CMD" not in insights_str and "DIR" not in insights_str
        rows = c["visual"]["table"]["rows"]
        if persona.startswith(("E1_", "E2_", "E3_", "E4_")):
            assert "943" in c["visual"].get("title", "") or "943" in c.get("display_text", "") or "943" in c.get("spoken_summary", "")

            # Juniors have k>=5 small-cell suppression (E9=4 -> '<5', GRP-B=0 -> '<5')
            by_g = {r["grade"]: r["headcount"] for r in rows}
            assert by_g.get("E9") == "<5"
            if persona.endswith("_FIN"):
                assert c["visual"]["table"]["masking"]["level"] == "aggregate"
        else:
            by_g = {r["grade"]: r["headcount"] for r in rows}
            assert by_g.get("E9") == 4
        return

    c2 = asyncio.run(
        v19_runner.execute_turn_async(
            "How many of these have been in Delhi for more than 5 years?",
            session_id=sid,
            persona=persona,
            principal=principal,
        )
    )
    if turn_step == "T2":
        c = c2
        assert c["access"]["status"] in ("allowed", "partial")
        assert c.get("definition_id") == "DELHI_GT5_CONT_V1"
        rows = c["visual"]["table"]["rows"]
        by_g = {r["grade"]: r["headcount"] for r in rows}
        if persona.startswith(("E1_", "E2_", "E3_", "E4_")):
            # E9 has 3 executives >5 yrs -> suppressed to '<5' for juniors
            assert by_g.get("E9") == "<5"
            text_all = c["visual"].get("title", "") + " " + c.get("display_text", "") + " " + " ".join(c.get("insights", []))
            assert "419" in text_all

            if persona.endswith("_FIN"):
                assert c["visual"]["table"]["masking"]["level"] == "aggregate"
        else:
            assert by_g.get("E9") == 3
        return

    c3 = asyncio.run(
        v19_runner.execute_turn_async(
            "Give me their names",
            session_id=sid,
            persona=persona,
            principal=principal,
        )
    )
    # Turn 3 assertions
    cols = set(c3["visual"]["table"]["columns"])
    st = v19_runner.session_manager.get_or_create(sid, persona=persona, emp_id=principal.emp_id)
    active_cohort = st.get_active_cohort()

    if persona in ("CMD", "DIR_HR"):
        assert c3["access"]["status"] == "allowed"
        assert "name" in cols and "functional_designation" in cols and "delhi_tenure_years" in cols
        assert c3["visual"]["table"]["hidden_columns"] == ["emp_id", "discipline"]
        assert c3["visual"]["table"]["total_rows"] == 419
    elif persona == "DIR_FIN":
        # DIR_FIN gets partial roster: granular names for FIN, collapsed groups for HR/Corp.
        assert c3["access"]["status"] == "partial"
        assert "name" in cols and "functional_designation" in cols
        assert c3["visual"]["table"]["hidden_columns"] == ["emp_id", "discipline"]
        assert c3["visual"]["table"]["masking"]["level"] == "aggregate"
        rows = c3["visual"]["table"]["rows"]
        has_named = any(r.get("name") and "employees" not in str(r.get("name")) for r in rows)
        has_collapsed = any("employees" in str(r.get("name")) for r in rows)
        assert has_named and has_collapsed
        assert active_cohort is not None
    else:
        # E1..E4_HR and E1..E4_FIN: R-NAMED + aggregate counts by grade (k>=5)
        assert c3["access"]["status"] == "partial"
        assert "name" not in cols and "emp_id" not in cols
        assert c3["visual"]["table"]["masking"]["level"] == "aggregate"
        assert c3["visual"]["table"]["masking"].get("code") == "R-NAMED"
        expected_copy = (
            "I can't share individual names at your access level. "
            "Here is the same group as counts by grade (groups under 5 shown as '<5')."
        )
        assert c3["spoken_summary"].startswith(expected_copy)
        by_g = {r["grade"]: r["headcount"] for r in c3["visual"]["table"]["rows"]}
        assert by_g.get("E9") == "<5"
        assert active_cohort is not None
        assert "name" not in set(active_cohort.get("columns") or [])
        assert active_cohort.get("rbac_decision") == "aggregate"
