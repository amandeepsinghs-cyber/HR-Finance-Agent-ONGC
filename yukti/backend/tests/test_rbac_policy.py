"""B3.3/B3.4: RBAC policy matrix (every persona x data class), topic guard, small-cell
suppression and the contract consistency rule (offline)."""

import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.brain.query_spec import Filter, QuerySpec
from app.brain.rbac import (decide, enforce_contract, load_policy, persona_class, row_actions,
                            suppress_small_cells, to_aggregate)

PERSONAS = ["CMD", "DIR_HR", "DIR_FIN", "E2_HR", "E3_FIN"]
CLASSES = ["general", "named", "pay", "apar", "sensitive"]
# Expected outcome per D-10 (CMD + Directors see everything) and D-11 (E1–E4 aggregate / refuse).
EXPECTED = {
    "CMD":    dict(general="allow", named="allow", pay="allow", apar="allow", sensitive="allow"),
    "DIR_HR": dict(general="allow", named="allow", pay="allow", apar="allow", sensitive="allow"),
    "DIR_FIN": dict(general="allow", named="allow", pay="allow", apar="allow", sensitive="allow"),
    "E2_HR":  dict(general="allow", named="aggregate", pay="refuse", apar="refuse", sensitive="refuse"),
    "E3_FIN": dict(general="allow", named="aggregate", pay="refuse", apar="refuse", sensitive="refuse"),
}


@pytest.mark.parametrize("persona", PERSONAS)
@pytest.mark.parametrize("data_class", CLASSES)
def test_rbac_matrix(persona, data_class):
    assert decide(persona, [data_class]).action == EXPECTED[persona][data_class]


def test_matrix_is_complete_and_unknown_persona_is_junior():
    pol = load_policy()
    for cls in pol["matrix"].values():
        assert set(cls) == set(CLASSES)
    assert persona_class("SOMEONE") == "junior"


def test_most_restrictive_class_wins():
    assert decide("E2_HR", ["general", "named", "pay"]).action == "refuse"
    assert decide("E2_HR", ["general", "named"]).action == "aggregate"


@pytest.mark.parametrize("q,expected", [
    ("What is the average salary of GMs in Delhi?", "refuse"),
    ("Show APAR ratings by grade", "refuse"),
    ("How many vigilance cases are pending?", "refuse"),
    ("How many executives are in Delhi?", "allow"),
])
def test_junior_topic_guard(q, expected):
    assert decide("E3_FIN", ["general"], q).action == expected


def test_topic_guard_does_not_apply_to_leadership():
    assert decide("CMD", ["general"], "average salary of GMs").action == "allow"


def test_to_aggregate_turns_roster_into_counts_by_grade():
    s = QuerySpec(metric="headcount", grain="row", filters=[Filter(field="wc", value="WC-DEL")])
    a = to_aggregate(s)
    assert a.grain == "aggregate" and a.dimensions == ["grade"] and a.filters == s.filters
    b = to_aggregate(s.model_copy(update={"dimensions": ["discipline"]}))
    assert b.dimensions == ["discipline"]


def test_small_cell_suppression():
    rows = [{"grade": "E1", "headcount": 3}, {"grade": "E2", "headcount": 5}, {"grade": "E3", "headcount": 0},
            {"grade": "E4", "avg_age": 2.0}]
    out, n = suppress_small_cells(rows, ["headcount", "avg_age"])
    assert out[0]["headcount"] == "<5" and out[1]["headcount"] == 5 and out[2]["headcount"] == 0
    assert out[3]["avg_age"] == 2.0  # not a count column
    assert n == 1


def test_row_actions_only_for_leadership_and_directors():
    assert row_actions("CMD", "workforce")[0]["action"] == "draft_transfer_note"
    assert row_actions("DIR_FIN", "workforce")
    assert row_actions("E2_HR", "workforce") == []
    assert row_actions("CMD", "field_pnl") == []


def _contract(cols, rows, status="allowed", vtype="table"):
    return {"turn_id": "t", "language": "en", "spoken_summary": "Here.", "display_text": "Here.",
            "access": {"status": status}, "sources": [{"kind": "data"}],
            "visual": {"type": vtype, "mode": "replace", "table": {"columns": cols, "rows": rows},
                       "chart": {"kind": "bar", "data": copy.deepcopy(rows)}}}


def test_enforce_contract_masks_named_and_pay_for_junior_and_sets_partial():
    c = _contract(["emp_name", "grade", "gross_salary_inr", "headcount"],
                  [{"emp_name": "A", "grade": "E2", "gross_salary_inr": 1, "headcount": 2}])
    out = enforce_contract(copy.deepcopy(c), "E2_HR")
    t = out["visual"]["table"]
    assert t["columns"] == ["grade", "headcount"]
    assert "emp_name" not in t["rows"][0] and "gross_salary_inr" not in t["rows"][0]
    assert t["rows"][0]["headcount"] == "<5"
    assert out["access"]["status"] == "partial" and t["masking"]["level"] == "partial"
    assert "chart" not in out["visual"]  # chart carried a named column
    assert "hidden" in out["spoken_summary"]


def test_enforce_contract_leaves_leadership_untouched():
    c = _contract(["emp_name", "grade"], [{"emp_name": "A", "grade": "E2"}])
    assert enforce_contract(copy.deepcopy(c), "CMD") == c


def test_refusal_never_ships_granular_visual():
    c = _contract(["emp_name"], [{"emp_name": "A"}], status="refused", vtype="chart")
    out = enforce_contract(c, "DIR_HR")
    assert out["visual"]["type"] == "refusal" and "chart" not in out["visual"]


def test_enforce_is_idempotent():
    c = _contract(["emp_id", "headcount"], [{"emp_id": "EMP-1", "headcount": 12}])
    once = enforce_contract(copy.deepcopy(c), "E3_FIN")
    twice = enforce_contract(copy.deepcopy(once), "E3_FIN")
    assert once == twice


# ------------------------------------------------------------------ G4 B3 round-1 regressions
def test_b1_count_columns_suppressed_regardless_of_name():
    rows = [{"discipline": "HR", "retiring_within_3yr": 2, "voluntary_exits": 3, "in_position": 4, "women_share_pct": 3.2}]
    out, n = suppress_small_cells(rows, ["retiring_within_3yr", "voluntary_exits", "in_position"], by_name=False)
    assert out[0]["retiring_within_3yr"] == "<5" and out[0]["voluntary_exits"] == "<5" and out[0]["in_position"] == "<5"
    assert out[0]["women_share_pct"] == 3.2 and n == 3


def test_b1_small_cells_hide_averages_via_population_count():
    rows = [{"grade": "E9", "avg_age": 58.2, "_n": 3}, {"grade": "E2", "avg_age": 31.0, "_n": 400}]
    out, n = suppress_small_cells(rows, ["avg_age"], cell_count_col="_n", value_check=False)
    assert out[0]["avg_age"] == "<5" and out[1]["avg_age"] == 31.0 and "_n" not in out[0] and n == 1


def test_b2_presenter_survives_suppressed_cells():
    from app.brain.compiler import CompiledQuery
    from app.brain.presenter import build_visual, narrate
    spec = QuerySpec(metric="headcount", dimensions=["wc", "grade"],
                     filters=[Filter(field="wc", op="in", value=["WC-DEL", "WC-MUM"])])
    cq = CompiledQuery(sql="", subject="workforce", metric="headcount", metric_label="Employees", unit="employees",
                       source="generated", tables=["t"], dims=[("wc", "work_centre"), ("grade", "grade")],
                       value_columns=["headcount"], aggregation="count")
    rows = [{"work_centre": "Delhi HQ", "grade": "E9", "headcount": "<5"},
            {"work_centre": "Delhi HQ", "grade": "E2", "headcount": 120},
            {"work_centre": "Mumbai High", "grade": "E2", "headcount": 200}]
    vis = build_visual(spec, cq, ["work_centre", "grade", "headcount"], rows, None, "t", "s", "compare")
    text = narrate(spec, cq, ["work_centre", "grade", "headcount"], rows)
    assert vis["mode"] == "compare" and "Delhi HQ" in text


@pytest.mark.parametrize("q,expected", [
    ("How many executives are posted apart from Delhi?", []),
    ("Did the vendor pay off the dues?", []),
    ("What is the average gross pay of GMs?", ["pay"]),
    ("Show wages and bonus by grade", ["pay"]),
    ("APARs of my team", ["apar"]),
    ("Any sexual harassment complaints?", ["sensitive"]),
])
def test_i3_topic_keywords_word_boundaries(q, expected):
    from app.brain.rbac import topic_classes
    assert topic_classes(q) == expected


@pytest.mark.parametrize("col,cls", [("avg_salary", "pay"), ("gross_pay", "pay"), ("apar", "apar"),
                                     ("employee_name", "named"), ("headcount", None), ("payroll_cr", None)])
def test_i4_column_patterns(col, cls):
    from app.brain.rbac import column_class
    assert column_class(col) == cls


def test_b3_junior_text_and_document_scrubbed():
    c = {"turn_id": "t", "language": "en", "spoken_summary": "Ramesh Goswami has the longest stay.",
         "display_text": "Ramesh Goswami ...", "insights": ["Ramesh Goswami 8.4 yrs"], "access": {"status": "allowed"},
         "sources": [{"kind": "data"}],
         "visual": {"type": "document", "mode": "replace", "document": {"markdown": "| Ramesh Goswami | E2 |"},
                    "table": {"columns": ["name", "grade"], "rows": [{"name": "Ramesh Goswami", "grade": "E2"}]}}}
    out = enforce_contract(c, "E2_HR")
    blob = str(out)
    assert "Ramesh Goswami" not in blob
    assert out["visual"]["type"] != "document" and out["access"]["status"] == "partial"


def test_b3_suppression_only_sets_partial():
    c = _contract(["grade", "headcount"], [{"grade": "E9", "headcount": 2}])
    out = enforce_contract(c, "E3_FIN")
    assert out["access"]["status"] == "partial" and out["visual"]["table"]["masking"]["level"] == "aggregate"


def test_i1_unknown_persona_is_junior_not_cmd():
    # P0.4 (SPEC-06 §4.4 rule 1): unknown / empty personas are an identity error (401), never coerced.
    import pytest
    from app.access_control import UnknownPersona, normalize_persona
    with pytest.raises(UnknownPersona):
        normalize_persona("intern")
    with pytest.raises(UnknownPersona):
        normalize_persona(None)
    assert normalize_persona("Director (Finance)") == "DIR_FIN"


def test_m1_refusal_strips_granular_table_and_marks_refused():
    c = _contract(["emp_name", "grade"], [{"emp_name": "A", "grade": "E2"}], status="refused", vtype="table")
    out = enforce_contract(c, "CMD")
    assert "emp_name" not in out["visual"]["table"]["columns"]
    assert out["visual"]["table"]["masking"]["level"] == "refused"
