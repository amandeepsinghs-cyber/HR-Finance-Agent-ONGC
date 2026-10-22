"""B4.2 drill-down chips and B4.3 narrator grounding (offline)."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.brain.drilldowns import make_drilldowns
from app.brain.insights import Insight
from app.brain.narrator import allowed_numbers, compose_spoken, grounding_violations
from app.brain.query_spec import Filter, QuerySpec, SpecPatch, apply_patch

DELHI = QuerySpec(metric="headcount", filters=[Filter(field="wc", value="WC-DEL"), Filter(field="cadre", value="executive"),
                                               Filter(field="station_tenure_years", op=">=", value=5)])


def _executable(spec, chip):
    if "spec_patch" not in chip:
        return True
    apply_patch(spec, SpecPatch.model_validate(chip["spec_patch"]))  # raises if not a valid patch
    return True


def test_at_least_two_executable_chips_per_data_answer():
    cases = [
        (DELHI, "CMD", "aggregate"),
        (apply_patch(DELHI, SpecPatch(grain="row")), "CMD", "row"),
        (QuerySpec(metric="pbt_cr", dimensions=["field"]), "DIR_FIN", "aggregate"),
        (QuerySpec(metric="capex_vs_reserves"), "CMD", "aggregate"),
        (QuerySpec(metric="headcount_change"), "CMD", "aggregate"),
        (QuerySpec(metric="mou_scorecard"), "DIR_FIN", "row"),
        (DELHI, "E2_HR", "aggregate"),
    ]
    for spec, persona, grain in cases:
        chips = make_drilldowns(spec, persona, grain)
        assert 2 <= len(chips) <= 3, (spec.metric, persona, chips)
        assert all(_executable(spec, c) for c in chips)


def test_names_chip_only_where_named_data_is_allowed():
    assert any(c.get("spec_patch") == {"grain": "row"} for c in make_drilldowns(DELHI, "CMD", "aggregate"))
    assert not any(c.get("spec_patch") == {"grain": "row"} for c in make_drilldowns(DELHI, "E2_HR", "aggregate"))


def test_compare_chip_uses_two_values_contract():
    chip = next(c for c in make_drilldowns(DELHI, "DIR_HR", "aggregate", max_n=5) if "compare" in c.get("spec_patch", {}))
    assert chip["spec_patch"]["compare"]["values"][0] == "WC-DEL" and len(chip["spec_patch"]["compare"]["values"]) == 2


def test_grounding_flags_invented_numbers_only():
    rows = [{"discipline": "F&A", "headcount": 99}, {"discipline": "HR", "headcount": 81}]
    ins = [Insight(kind="headline", text="F&A is 23.6% of 419.", facts=[23.6, 99, 419])]
    allowed = allowed_numbers(rows, ins, DELHI, extra=[419])
    assert grounding_violations("F&A has 99 of 419 (23.6%) in FY26, as of 19-Oct-2026; grade E5.", allowed) == []
    assert grounding_violations("HR has 812 officers.", allowed) == ["812"]
    assert grounding_violations("Top 3 groups.", allowed) == []  # small structural integers


def test_compose_spoken_is_2_to_4_sentences_and_falls_back_on_ungrounded():
    rows = [{"d": "A", "v": 10}, {"d": "B", "v": 20}]
    allowed = allowed_numbers(rows, [], None, extra=[30])
    good = compose_spoken("30 employees across 2 groups. Highest: B (20).",
                          [Insight(kind="headline", text="B holds 66.7% of the total.", facts=[66.7])],
                          allowed | {66.7})
    assert 2 <= good["sentences"] <= 4 and good["ungrounded"] == []
    bad = compose_spoken("30 employees across 2 groups.", [Insight(kind="note", text="That is 45% more than 2019.")],
                         allowed)
    assert "45" not in bad["text"] and bad["ungrounded"] == []



def test_headline_values_and_roster_mix_cover_kpi_and_roster_answers():
    from app.brain.insights import InsightContext, compute_insights
    kpi = InsightContext(metric="headcount", metric_label="Employees", unit="employees", dim=None,
                         value_col="headcount", rows=[{"headcount": 419, "avg_age": 47.2}], scope=["Delhi HQ"])
    ins = compute_insights(kpi)
    assert len(ins) >= 2 and ins[0].text == "Employees: 419 (Delhi HQ)."
    roster = InsightContext(metric="headcount", metric_label="Employees", unit="employees", dim=None, value_col=None,
                            grain="row", rows=[{"grade": "E3", "discipline": "HR", "station_tenure_years": 6.0},
                                               {"grade": "E3", "discipline": "IT", "station_tenure_years": 5.5},
                                               {"grade": "E5", "discipline": "HR", "station_tenure_years": 7.0}])
    ins2 = compute_insights(roster)
    texts = [i.text for i in ins2]
    assert any("largest grade group is E3: 2 of 3" in t for t in texts) and len(ins2) >= 2


def test_top_two_gap_for_two_way_and_non_additive():
    from app.brain.insights import InsightContext, top_two_gap
    ctx = InsightContext(metric="m", metric_label="EBITDA margin", unit="pct", dim="asset", value_col="m",
                         rows=[{"asset": "Ankleshwar", "m": 69.2}, {"asset": "Bassein", "m": 64.2}, {"asset": "MH", "m": 58.1}])
    ins = top_two_gap(ctx)
    assert ins.text == "Ankleshwar leads Bassein by 5.0 pts (69.2% vs 64.2%)."
    add3 = InsightContext(metric="h", metric_label="Employees", unit="employees", dim="wc", value_col="h",
                          rows=[{"wc": "A", "h": 3}, {"wc": "B", "h": 2}, {"wc": "C", "h": 1}])
    assert top_two_gap(add3) is None
