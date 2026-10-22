"""B2.1: QuerySpec model + patch semantics (offline)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.brain.query_spec import Compare, Filter, Period, QuerySpec, Sort, SpecPatch, apply_patch, shift_period

BASE = QuerySpec(
    domain="hr",
    metric="headcount",
    filters=[
        Filter(field="wc", value="WC-DEL"),
        Filter(field="cadre", value="executive"),
        Filter(field="station_tenure_years", op=">=", value=5),
    ],
)


def keys(spec):
    return {f.key() for f in spec.filters}


def test_contract_shape_and_roundtrip():
    s = BASE.model_copy(update={"period": Period(**{"from": "FY22", "to": "FY26"})})
    c = s.to_contract()
    assert c["version"] == 1 and c["metric"] == "headcount" and c["grain"] == "aggregate"
    assert c["period"] == {"from": "FY22", "to": "FY26"}  # alias 'from', no nulls
    assert QuerySpec.from_contract(c) == s


def test_filter_add_narrows():
    s = apply_patch(BASE, SpecPatch(add_filters=[Filter(field="grade", op=">=", value="E5")]))
    assert ("grade", ">=", "E5") in keys(s) and len(s.filters) == 4


def test_filter_add_on_same_field_replaces_entity_shift():
    s = apply_patch(BASE, SpecPatch(add_filters=[Filter(field="wc", value="WC-MUM")]))
    assert ("wc", "=", "WC-MUM") in keys(s) and ("wc", "=", "WC-DEL") not in keys(s)


def test_remove_filter():
    s = apply_patch(BASE, SpecPatch(remove_filters=["cadre"]))
    assert all(f.field != "cadre" for f in s.filters)


def test_compare_keeps_current_entity_first_and_leads_dimensions():
    s = apply_patch(BASE.model_copy(update={"dimensions": ["discipline"]}),
                    SpecPatch(compare=Compare(field="wc", values=["WC-DEL", "WC-MUM"])))
    f = s.filter_on("wc")
    assert f.op == "in" and f.value == ["WC-DEL", "WC-MUM"]
    assert s.dimensions == ["wc", "discipline"]
    assert s.is_compare() == ("wc", ["WC-DEL", "WC-MUM"])


def test_compare_from_row_grain_returns_to_aggregate():
    row = apply_patch(BASE, SpecPatch(grain="row"))
    s = apply_patch(row, SpecPatch(compare=Compare(field="wc", values=["WC-DEL", "WC-MUM"])))
    assert s.grain == "aggregate"


def test_grain_switch_keeps_filters():
    s = apply_patch(BASE, SpecPatch(grain="row"))
    assert s.grain == "row" and keys(s) == keys(BASE) and s.aggregation is None


def test_breakdown_after_compare_keeps_compare_dimension():
    cmp = apply_patch(BASE, SpecPatch(compare=Compare(field="wc", values=["WC-DEL", "WC-MUM"])))
    s = apply_patch(cmp, SpecPatch(dimensions=["grade"]))
    assert s.dimensions == ["wc", "grade"]


def test_time_shift_fy_clears_range_and_vice_versa():
    a = apply_patch(BASE, SpecPatch(period=Period(**{"from": "FY22", "to": "FY26"})))
    b = apply_patch(a, SpecPatch(period=Period(fy="FY25")))
    assert b.period.fy == "FY25" and b.period.from_ is None and b.period.to is None
    c = apply_patch(b, SpecPatch(period=Period(**{"from": "FY23"})))
    assert c.period.fy is None and c.period.from_ == "FY23"


def test_shift_period_helper():
    s = BASE.model_copy(update={"period": Period(fy="FY26")})
    assert shift_period(s, -1).period.fy == "FY25"


def test_metric_change_drops_stale_sort():
    s = BASE.model_copy(update={"sort": Sort(by="headcount", dir="desc")})
    t = apply_patch(s, SpecPatch(metric="avg_age"))
    assert t.metric == "avg_age" and t.sort is None


def test_chart_kind_is_presentation_only():
    p = SpecPatch(chart_kind="pie")
    assert p.is_presentation_only()
    assert apply_patch(BASE, p) == BASE


def test_patch_contract_shape():
    p = SpecPatch(add_filters=[Filter(field="grade", op=">=", value="E5")], chart_kind="bar")
    assert p.to_contract() == {"add_filters": [{"field": "grade", "op": ">=", "value": "E5"}], "chart_kind": "bar"}


def test_filter_shapes_validated():
    assert Filter(field="wc", op="in", value="WC-DEL").value == ["WC-DEL"]
    with pytest.raises(Exception):
        Filter(field="age", op="between", value=[30])
    with pytest.raises(Exception):
        Compare(field="wc", values=["WC-DEL"])  # contract: 2–4 values


def test_original_spec_not_mutated():
    before = BASE.to_contract()
    apply_patch(BASE, SpecPatch(add_filters=[Filter(field="wc", value="WC-MUM")], grain="row"))
    assert BASE.to_contract() == before
