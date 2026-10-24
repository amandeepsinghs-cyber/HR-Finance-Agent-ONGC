"""B3 live checks (Gemini planner + BigQuery, YUKTI_PLANNER=1):
- B3.1 roster grain matches a direct BigQuery count and sample (Delhi 5+ yrs = 419)
- B3.3/B3.4 RBAC end to end: E2_HR names -> aggregate (partial), pay/APAR -> refusal, status/text/visual agree
- B3.5 transfer note lists exactly the selected people; junior refused
"""

import asyncio
import os
from pathlib import Path
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROSTER_Q = "Give me the names of executives posted in the Delhi office for 5 years or more"


@pytest.fixture(scope="module")
def results():
    os.environ["YUKTI_PLANNER"] = "1"
    os.environ["YUKTI_RESULT_CACHE"] = "0"
    from app.turn_runner import AgentTurnRunner
    from google.cloud import bigquery
    from app.config import BQ_LOCATION, GCP_PROJECT, JOB_LABELS

    async def run():
        r = AgentTurnRunner(model_name="gemini-2.5-flash")
        t = int(time.time())
        out = {}
        out["cmd_roster"] = await r.execute_turn_async(ROSTER_Q, session_id=f"b3-cmd-{t}", persona="CMD")
        # "for them" right after the roster = everyone on screen; then a row-action selection of 3
        out["cmd_note_all"] = await r.execute_turn_async("Draft a transfer note for them", session_id=f"b3-cmd-{t}",
                                                         persona="CMD")
        sel = [row["emp_id"] for row in out["cmd_roster"]["visual"]["table"]["rows"][:3]]
        out["cmd_note_sel"] = await r.execute_turn_async(
            "Draft a transfer note for the selected employees", session_id=f"b3-cmd-{t}", persona="CMD",
            ui_context={"selected_emp_ids": sel})
        out["cmd_note_sel_ids"] = sel
        # U5 row action: spec_patch add_filters emp_id in [...] + text question
        sel2 = [row["emp_id"] for row in out["cmd_roster"]["visual"]["table"]["rows"][3:5]]
        out["cmd_note_patch"] = await r.execute_turn_async(
            "Draft a transfer note for the selected 2 employees", session_id=f"b3-cmd-{t}", persona="CMD",
            spec_patch={"add_filters": [{"field": "emp_id", "op": "in", "value": sel2}]},
            base_spec=out["cmd_roster"]["query_spec"])
        out["cmd_note_patch_ids"] = sel2
        out["dirfin_roster"] = await r.execute_turn_async(ROSTER_Q, session_id=f"b3-df-{t}", persona="DIR_FIN")
        out["e2_roster"] = await r.execute_turn_async(ROSTER_Q, session_id=f"b3-e2-{t}", persona="E2_HR")
        out["e2_note"] = await r.execute_turn_async("Draft a transfer note for them", session_id=f"b3-e2-{t}",
                                                    persona="E2_HR")
        out["e2_m3"] = await r.execute_turn_async("Show me the salary and APAR of employee 104523.",
                                                  session_id=f"b3-e2m3-{t}", persona="E2_HR")
        out["e3_pay"] = await r.execute_turn_async("What is the average gross salary by grade?",
                                                   session_id=f"b3-e3-{t}", persona="E3_FIN")
        out["e2_compare_small"] = await r.execute_turn_async(
            "Compare executives in Delhi and Mumbai by grade", session_id=f"b3-e2c-{t}", persona="E2_HR")
        out["e2_retiring"] = await r.execute_turn_async(
            "How many employees retire within 3 years at Delhi HQ by discipline?", session_id=f"b3-e2r-{t}",
            persona="E2_HR")
        out["e2_person"] = await r.execute_turn_async(
            "Show details of employee EMP-100522", session_id=f"b3-e2p-{t}", persona="E2_HR")
        out["e2_person_doc"] = await r.execute_turn_async(
            "Draft a board note on this", session_id=f"b3-e2p-{t}", persona="E2_HR")
        out["cmd_pay"] = await r.execute_turn_async("What is the average gross salary by grade?",
                                                    session_id=f"b3-cmdpay-{t}", persona="CMD")
        return out

    try:
        out = asyncio.run(run())
    finally:
        os.environ.pop("YUKTI_PLANNER", None)
    c = bigquery.Client(project=GCP_PROJECT, location=BQ_LOCATION)
    sql = ("SELECT emp_id FROM `%s.hrfin_gold.ssot_workforce_employee` WHERE employment_status = 'Active' "
           "AND wc_id = 'WC-DEL' AND cadre = 'executive' AND continuous_stay_years >= 5" % GCP_PROJECT)
    out["bq_ids"] = {r["emp_id"] for r in c.query(sql, job_config=bigquery.QueryJobConfig(labels=JOB_LABELS)).result()}
    return out


def _cols(c):
    return set((c["visual"].get("table") or {}).get("columns") or [])


def test_b31_roster_matches_bigquery(results):
    c = results["cmd_roster"]
    t = c["visual"]["table"]
    ids = {r["emp_id"] for r in t["rows"]}
    assert len(results["bq_ids"]) == 419 and ids == results["bq_ids"] and t["total_rows"] == 419
    assert {"name", "designation", "grade", "discipline", "ongc_tenure_years", "station_tenure_years",
            "exemption", "retiring_within_3yr"} <= _cols(c)
    assert all(r["designation"] for r in t["rows"])  # B3.2: grade_designation populated


def test_b3_row_action_for_leadership(results):
    acts = results["cmd_roster"]["visual"]["table"].get("row_actions") or []
    assert acts and acts[0]["action"] == "draft_transfer_note"
    assert results["cmd_roster"]["access"]["status"] == "allowed"


def test_b3_director_sees_names_d10(results):
    # D-43 (supersedes D-10): DIR_FIN is function-scoped and receives aggregate counts (partial) for general HR rosters.
    c = results["dirfin_roster"]
    assert c["access"]["status"] == "partial" and "name" not in _cols(c)


def test_b34_junior_names_become_aggregate_and_agree(results):
    c = results["e2_roster"]
    assert c["access"]["status"] == "partial"
    assert "name" not in _cols(c) and "emp_id" not in _cols(c)
    assert c["visual"]["table"]["masking"]["level"] == "aggregate"
    spoken_low = c["spoken_summary"].lower()
    assert any(k in spoken_low for k in ("restricted", "can't share individual names", "individual names"))
    assert c["query_spec"]["grain"] == "aggregate"


def test_b34_junior_pay_and_apar_refused(results):
    for key in ("e2_m3", "e3_pay"):
        c = results[key]
        assert c["access"]["status"] == "refused", key
        assert c["visual"]["type"] == "refusal", key
        assert "name" not in _cols(c) and "emp_name" not in _cols(c)


def test_b3_cmd_pay_allowed_d10(results):
    assert results["cmd_pay"]["access"]["status"] == "allowed"


def test_b35_transfer_note_lists_selected_people(results):
    c = results["cmd_note_sel"]
    assert c["visual"]["type"] == "document"
    rows = c["visual"]["table"]["rows"]
    assert [r["emp_id"] for r in rows] and {r["emp_id"] for r in rows} == set(results["cmd_note_sel_ids"])
    md = c["visual"]["document"]["markdown"]
    for r in rows:
        assert r["name"] in md and r["emp_id"] in md
    assert "word" in c["export_options"] and "pdf" in c["export_options"]


def test_b35_transfer_note_for_whole_roster(results):
    c = results["cmd_note_all"]
    assert c["visual"]["type"] == "document" and c["visual"]["table"]["total_rows"] == 419


def test_b35_junior_cannot_draft_named_note(results):
    c = results["e2_note"]
    assert c["access"]["status"] == "refused" and c["visual"]["type"] == "refusal"


def test_b35_row_action_spec_patch_selection(results):
    c = results["cmd_note_patch"]
    assert c["visual"]["type"] == "document"
    assert {r["emp_id"] for r in c["visual"]["table"]["rows"]} == set(results["cmd_note_patch_ids"])


def _numbers_below_5(c, cols):
    out = []
    for r in (c["visual"].get("table") or {}).get("rows") or []:
        for k in cols:
            v = r.get(k)
            if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 < v < 5:
                out.append((k, v))
    return out


def test_b2_junior_compare_with_small_cells_answers_and_suppresses(results):
    c = results["e2_compare_small"]
    assert c.get("query_spec"), c["spoken_summary"]  # answered by the planner, no crash/fallback
    assert _numbers_below_5(c, ["headcount"]) == []
    assert c["access"]["status"] == "partial"


def test_b1_junior_retiring_counts_suppressed(results):
    c = results["e2_retiring"]
    assert _numbers_below_5(c, ["retiring_within_3yr", "headcount"]) == []


def test_b3_legacy_path_and_drafts_never_leak_names_to_juniors(results):
    import re
    for key in ("e2_person", "e2_person_doc"):
        c = results[key]
        cols = set((c["visual"].get("table") or {}).get("columns") or [])
        assert not ({"name", "emp_name", "employee_name"} & cols), key
        md = str((c["visual"].get("document") or {}).get("markdown") or "")
        assert "EMP-100522" not in md and "Ramesh Goswami" not in str(c), key
