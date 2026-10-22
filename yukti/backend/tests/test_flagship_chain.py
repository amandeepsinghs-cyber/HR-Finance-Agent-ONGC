"""B2.5: flagship HR chain end to end through the turn runner with YUKTI_PLANNER=1 (live
Gemini planner + BigQuery). Checks that every follow-up resolves as a patch of the previous
QuerySpec, `query_spec` is echoed, and the numbers equal the audited answer key.

Chain (FEAT-009): Delhi 5+ yrs -> their names -> by discipline -> compare with Mumbai ->
only E5 and above -> last year -> draft transfer note.
"""

import asyncio
import os
from pathlib import Path
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _filters(c):
    return {(f["field"], f["op"], str(sorted(f["value"]) if isinstance(f["value"], list) else f["value"]))
            for f in (c.get("query_spec") or {}).get("filters", [])}


def _total(contract, key="headcount"):
    rows = (contract["visual"].get("table") or {}).get("rows") or []
    return sum(float(r.get(key) or 0) for r in rows)


def _by(contract, dim, value_key="headcount"):
    out = {}
    for r in (contract["visual"].get("table") or {}).get("rows") or []:
        out[r.get(dim)] = out.get(r.get(dim), 0) + float(r.get(value_key) or 0)
    return out


@pytest.fixture(scope="module")
def chain():
    os.environ["YUKTI_PLANNER"] = "1"
    os.environ["YUKTI_RESULT_CACHE"] = "0"
    from app.turn_runner import AgentTurnRunner

    qs = [
        "How many executives have been posted in the Delhi office for 5 years or more?",
        "Give me their names",
        "Break it down by discipline",
        "Compare with Mumbai",
        "Only E5 and above",
        "What about last year?",
        "Draft a transfer note for them",
    ]

    async def run():
        r = AgentTurnRunner(model_name="gemini-2.5-flash")
        sid = f"flagship-{int(time.time())}"
        out = []
        for q in qs:
            out.append(await r.execute_turn_async(q, session_id=sid, persona="CMD"))
        return out

    try:
        return asyncio.run(run())
    finally:
        os.environ.pop("YUKTI_PLANNER", None)


BASE = {("wc", "=", "WC-DEL"), ("cadre", "=", "executive"), ("station_tenure_years", ">=", "5")}


def test_t1_delhi_count(chain):
    c = chain[0]
    assert c["contract_version"] == 2 and c["query_spec"]["metric"] == "headcount"
    assert _filters(c) == BASE
    assert _total(c) == 419


def test_t2_names_roster(chain):
    c = chain[1]
    assert c["query_spec"]["grain"] == "row" and _filters(c) == BASE
    t = c["visual"]["table"]
    assert t.get("total_rows") == 419 and len(t["rows"]) == 419
    assert {"name", "designation", "grade", "ongc_tenure_years", "station_tenure_years"} <= set(t["columns"])


def test_t3_by_discipline(chain):
    c = chain[2]
    assert c["query_spec"]["dimensions"] == ["discipline"] and c["query_spec"]["grain"] == "aggregate"
    by = _by(c, "discipline")
    assert sum(by.values()) == 419
    assert by.get("Finance & Accounts (F&A)") == 99


def test_t4_compare_mumbai(chain):
    c = chain[3]
    assert ("wc", "in", str(["WC-DEL", "WC-MUM"])) in _filters(c)
    assert c["query_spec"]["dimensions"][0] == "wc"
    by = _by(c, "work_centre")
    assert by.get("Delhi HQ") == 419 and by.get("Mumbai High") == 560
    assert c["visual"].get("compare") and len(c["visual"]["compare"]["items"]) == 2


def test_t5_e5_and_above(chain):
    c = chain[4]
    assert ("grade", ">=", "E5") in _filters(c)
    by = _by(c, "work_centre")
    assert by.get("Delhi HQ") == 140 and by.get("Mumbai High") == 192


def test_t6_last_year_fy26(chain):
    c = chain[5]
    assert c["query_spec"].get("period", {}).get("fy") == "FY26"
    assert ("grade", ">=", "E5") in _filters(c)
    by = _by(c, "work_centre")
    assert by.get("Delhi HQ") == 122 and by.get("Mumbai High") == 187  # as of 31-Mar-2026
    assert "31-Mar-2026" in (c.get("caveat") or "")


def test_t7_draft_document(chain):
    c = chain[6]
    assert c["visual"]["type"] == "document"
