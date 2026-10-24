"""Unit tests for deterministic insight library (B4.1, FEAT-011)."""

import pytest
from app.brain.insights import (
    Insight,
    InsightContext,
    aggregate_by_dim,
    compute_insights,
    concentration,
    delta_vs_last_year,
    fmt,
    named_exceptions,
    numeric_rows,
    outliers,
    policy_flags,
    rank_extremes,
    share_of_total,
    vs_target,
    INSIGHT_FUNCS,
)


@pytest.fixture
def example_context() -> InsightContext:
    """Example fixture from packet B4.1 §6:
    discipline, headcount, employees:
    F&A 99, HR 81, MM 60, IT 50, Legal 40, Drilling 30, Prod 25, Geology 24, HSE 10 (sum 419).
    """
    rows = [
        {"discipline": "F&A", "headcount": 99},
        {"discipline": "HR", "headcount": 81},
        {"discipline": "MM", "headcount": 60},
        {"discipline": "IT", "headcount": 50},
        {"discipline": "Legal", "headcount": 40},
        {"discipline": "Drilling", "headcount": 30},
        {"discipline": "Prod", "headcount": 25},
        {"discipline": "Geology", "headcount": 24},
        {"discipline": "HSE", "headcount": 10},
    ]
    return InsightContext(
        metric="headcount",
        metric_label="Headcount",
        unit="employees",
        dim="discipline",
        value_col="headcount",
        rows=rows,
        n_total=419,
    )


# ------------------------------------------------------------------ Reference tests
def test_share_of_total(example_context: InsightContext):
    ins = share_of_total(example_context)
    assert ins is not None
    assert ins.kind == "headline"
    assert ins.type == "share"
    assert ins.priority == 10
    assert ins.ref == "F&A"
    assert ins.value == 23.6
    assert ins.text == "F&A accounts for 23.6% of the total (99 of 419)."
    assert ins.facts == [23.6, 99.0, 419.0]

    # None when non-additive
    ctx_non_add = InsightContext(
        metric="cost", metric_label="Cost", unit="usd_per_boe",
        dim="discipline", value_col="headcount", rows=example_context.rows,
    )
    assert share_of_total(ctx_non_add) is None


def test_rank_extremes(example_context: InsightContext):
    ins = rank_extremes(example_context)
    assert ins is not None
    assert ins.kind == "comparison"
    assert ins.type == "rank"
    assert ins.priority == 20
    assert ins.ref == "F&A"
    assert ins.text == "Highest is F&A (99); lowest is HSE (10) across 9 groups."
    assert ins.facts == [99.0, 10.0, 9.0]

    # None when fewer than 3 groups
    ctx_small = InsightContext(
        metric="headcount", metric_label="Headcount", unit="employees",
        dim="discipline", value_col="headcount",
        rows=[{"discipline": "A", "headcount": 10}, {"discipline": "B", "headcount": 20}],
    )
    assert rank_extremes(ctx_small) is None


# ------------------------------------------------------------------ 1. delta_vs_last_year
def test_delta_vs_last_year_up(example_context: InsightContext):
    example_context.prev_rows = [{"discipline": "Total", "headcount": 400}]
    example_context.prev_label = "FY25"
    ins = delta_vs_last_year(example_context)
    assert ins is not None
    assert ins.kind == "trend"
    assert ins.type == "delta"
    assert ins.priority == 15
    assert ins.value == 4.8
    assert ins.unit == "%"
    assert ins.text == "Headcount is up 19 (+4.8%) vs FY25."
    assert 19.0 in ins.facts
    assert 4.8 in ins.facts


def test_delta_vs_last_year_down():
    ctx = InsightContext(
        metric="headcount",
        metric_label="Headcount",
        unit="employees",
        dim="discipline",
        value_col="headcount",
        rows=[{"discipline": "A", "headcount": 380}],
        prev_rows=[{"discipline": "A", "headcount": 400}],
        prev_label="FY25",
    )
    ins = delta_vs_last_year(ctx)
    assert ins is not None
    assert ins.kind == "trend"
    assert ins.type == "delta"
    assert ins.value == -5.0
    assert ins.text == "Headcount is down 20 (-5.0%) vs FY25."
    assert 20.0 in ins.facts
    assert -5.0 in ins.facts


def test_delta_vs_last_year_unchanged():
    ctx = InsightContext(
        metric="headcount",
        metric_label="Headcount",
        unit="employees",
        dim="discipline",
        value_col="headcount",
        rows=[{"discipline": "A", "headcount": 400}],
        prev_rows=[{"discipline": "A", "headcount": 400}],
        prev_label="FY25",
    )
    ins = delta_vs_last_year(ctx)
    assert ins is not None
    assert ins.text == "Headcount is unchanged vs FY25."
    assert ins.value == 0.0


def test_delta_vs_last_year_non_additive_single_row():
    ctx = InsightContext(
        metric="cost",
        metric_label="Lifting Cost",
        unit="usd_per_boe",
        dim=None,
        value_col="cost",
        rows=[{"cost": 12.5}],
        prev_rows=[{"cost": 10.0}],
        prev_label="FY25",
    )
    ins = delta_vs_last_year(ctx)
    assert ins is not None
    assert ins.text == "Lifting Cost is up $2.50 (+25.0%) vs FY25."
    assert ins.value == 25.0


def test_delta_vs_last_year_none_cases(example_context: InsightContext):
    # Missing prev_rows
    assert delta_vs_last_year(example_context) is None

    # Missing prev_label
    example_context.prev_rows = [{"headcount": 400}]
    example_context.prev_label = None
    assert delta_vs_last_year(example_context) is None

    # prev_total == 0
    example_context.prev_label = "FY25"
    example_context.prev_rows = [{"headcount": 0}]
    assert delta_vs_last_year(example_context) is None

    # Non-additive with multiple rows returns None
    ctx_multi_non_add = InsightContext(
        metric="cost",
        metric_label="Cost",
        unit="usd_per_boe",
        dim="dim",
        value_col="cost",
        rows=[{"dim": "A", "cost": 10.0}, {"dim": "B", "cost": 12.0}],
        prev_rows=[{"dim": "A", "cost": 10.0}, {"dim": "B", "cost": 12.0}],
        prev_label="FY25",
    )
    assert delta_vs_last_year(ctx_multi_non_add) is None


# ------------------------------------------------------------------ 2. vs_target
def test_vs_target_shortfall(example_context: InsightContext):
    example_context.targets = {"F&A": 100.0, "HR": 100.0, "MM": 50.0}
    # F&A: actual 99 vs target 100 -> gap -1
    # HR: actual 81 vs target 100 -> gap -19 (largest shortfall)
    # MM: actual 60 vs target 50 -> meets
    ins = vs_target(example_context)
    assert ins is not None
    assert ins.kind == "risk"
    assert ins.type == "vs_target"
    assert ins.priority == 12
    assert ins.ref == "HR"
    assert ins.text == "HR is 19 below target (81 vs 100)."
    assert 19.0 in ins.facts
    assert 81.0 in ins.facts
    assert 100.0 in ins.facts


def test_vs_target_all_meet(example_context: InsightContext):
    example_context.targets = {"F&A": 90.0, "HR": 80.0, "MM": 50.0}
    ins = vs_target(example_context)
    assert ins is not None
    assert ins.kind == "comparison"
    assert ins.type == "vs_target"
    assert ins.priority == 12
    assert ins.ref is None
    assert ins.text == "All 3 categories meet the target."
    assert ins.facts == [3.0]


def test_vs_target_custom_target_label():
    ctx = InsightContext(
        metric="headcount",
        metric_label="Headcount",
        unit="employees",
        dim="discipline",
        value_col="headcount",
        rows=[{"discipline": "HR", "headcount": 81}],
        targets={"HR": 100.0},
        target_label="sanctioned strength",
    )
    ins = vs_target(ctx)
    assert ins is not None
    assert ins.text == "HR is 19 below sanctioned strength (81 vs 100)."


def test_vs_target_none_cases(example_context: InsightContext):
    # No targets
    assert vs_target(example_context) is None

    # No categories match targets
    example_context.targets = {"NonExistent": 100.0}
    assert vs_target(example_context) is None

    # Missing dim
    ctx_no_dim = InsightContext(
        metric="m", metric_label="M", unit="employees",
        dim=None, value_col="headcount", rows=[{"headcount": 10}],
        targets={"HR": 10.0},
    )
    assert vs_target(ctx_no_dim) is None


# ------------------------------------------------------------------ 3. outliers
def test_outliers_positive():
    rows = [
        {"asset": "A", "val": 10.0},
        {"asset": "B", "val": 11.0},
        {"asset": "C", "val": 12.0},
        {"asset": "D", "val": 10.0},
        {"asset": "E", "val": 11.0},
        {"asset": "Extreme", "val": 100.0},
    ]
    ctx = InsightContext(
        metric="production",
        metric_label="Production",
        unit="boe",
        dim="asset",
        value_col="val",
        rows=rows,
    )
    ins = outliers(ctx)
    assert ins is not None
    assert ins.kind == "outlier"
    assert ins.type == "outlier"
    assert ins.priority == 25
    assert ins.ref == "Extreme"
    assert ins.text == "Extreme is an outlier at 100 (median 11)."
    assert 100.0 in ins.facts
    assert 11.0 in ins.facts


def test_outliers_none_cases(example_context: InsightContext):
    # Normal distribution with no |z| > 3.5
    assert outliers(example_context) is None

    # Fewer than 5 categories
    ctx_small = InsightContext(
        metric="p", metric_label="P", unit="boe", dim="asset", value_col="val",
        rows=[{"asset": f"A{i}", "val": float(i * 10)} for i in range(4)],
    )
    assert outliers(ctx_small) is None

    # MAD == 0
    ctx_zero_mad = InsightContext(
        metric="p", metric_label="P", unit="boe", dim="asset", value_col="val",
        rows=[{"asset": f"A{i}", "val": 10.0} for i in range(6)],
    )
    assert outliers(ctx_zero_mad) is None


# ------------------------------------------------------------------ 4. concentration
def test_concentration_positive(example_context: InsightContext):
    # Top 3: F&A (99) + HR (81) + MM (60) = 240 / 419 = 57.279% -> 57.3%
    ins = concentration(example_context)
    assert ins is not None
    assert ins.kind == "note"
    assert ins.type == "concentration"
    assert ins.priority == 30
    assert ins.value == 57.3
    assert ins.unit == "%"
    assert ins.ref is None
    assert ins.text == "The top 3 (F&A, HR, MM) hold 57.3% of the total."
    assert 57.3 in ins.facts
    assert 3.0 in ins.facts


def test_concentration_none_cases():
    # Top 3 share < 50%
    rows = [{"cat": f"C{i}", "val": 10.0} for i in range(10)]
    ctx_diffuse = InsightContext(
        metric="headcount", metric_label="Headcount", unit="employees",
        dim="cat", value_col="val", rows=rows,
    )
    assert concentration(ctx_diffuse) is None

    # Fewer than 4 categories
    ctx_few = InsightContext(
        metric="headcount", metric_label="Headcount", unit="employees",
        dim="cat", value_col="val",
        rows=[{"cat": "A", "val": 60}, {"cat": "B", "val": 40}, {"cat": "C", "val": 30}],
    )
    assert concentration(ctx_few) is None

    # Non-additive unit
    ctx_non_add = InsightContext(
        metric="rate", metric_label="Rate", unit="pct",
        dim="cat", value_col="val",
        rows=[{"cat": f"C{i}", "val": 20.0} for i in range(5)],
    )
    assert concentration(ctx_non_add) is None


# ------------------------------------------------------------------ 5. named_exceptions
def test_named_exceptions_single():
    ctx = InsightContext(
        metric="pnl",
        metric_label="P&L",
        unit="inr_cr",
        dim="field",
        value_col="inr_cr",
        rows=[
            {"field": "Mumbai High", "inr_cr": 1500.0},
            {"field": "Champang", "inr_cr": -4.93},
        ],
    )
    ins = named_exceptions(ctx)
    assert ins is not None
    assert ins.kind == "risk"
    assert ins.type == "named_exception"
    assert ins.priority == 18
    assert ins.ref == "Champang"
    assert ins.value == -4.93
    assert ins.unit == "inr_cr"
    assert ins.text == "1 is negative: Champang (−₹4.93 cr)."
    assert -4.93 in ins.facts
    assert 1.0 in ins.facts


def test_named_exceptions_multiple_ordered_most_negative():
    ctx = InsightContext(
        metric="pnl",
        metric_label="P&L",
        unit="inr_cr",
        dim="field",
        value_col="inr_cr",
        rows=[
            {"field": "FieldA", "inr_cr": -10.0},
            {"field": "FieldB", "inr_cr": -25.5},
            {"field": "FieldC", "inr_cr": -5.0},
            {"field": "FieldD", "inr_cr": -1.0},
            {"field": "FieldE", "inr_cr": 100.0},
        ],
    )
    ins = named_exceptions(ctx)
    assert ins is not None
    assert ins.ref == "FieldB"
    assert ins.value == -25.5
    # Max 3 names, most negative first (-25.5, -10.0, -5.0)
    assert ins.text == "4 negative: FieldB (−₹25.50 cr), FieldA (−₹10 cr), FieldC (−₹5 cr)."
    assert -25.5 in ins.facts
    assert -10.0 in ins.facts
    assert -5.0 in ins.facts
    assert 4.0 in ins.facts


def test_named_exceptions_none(example_context: InsightContext):
    # All positive
    assert named_exceptions(example_context) is None


# ------------------------------------------------------------------ 6. policy_flags
def test_policy_flags_positive():
    rows = [
        {"name": f"Emp_{i}", "station_tenure_years": 6.0, "is_superannuation_exempt": False}
        for i in range(4)
    ] + [
        {"name": f"Emp_{i+4}", "station_tenure_years": 2.0, "is_superannuation_exempt": True}
        for i in range(2)
    ] + [
        {"name": f"Emp_{i+6}", "station_tenure_years": 3.0, "is_superannuation_exempt": False}
        for i in range(4)
    ]
    ctx = InsightContext(
        metric="roster",
        metric_label="Roster",
        unit="employees",
        dim=None,
        value_col=None,
        grain="row",
        rows=rows,
    )
    ins = policy_flags(ctx)
    assert ins is not None
    assert ins.kind == "risk"
    assert ins.type == "policy_flag"
    assert ins.priority == 16
    assert ins.value == 4.0
    assert ins.unit == "employees"
    assert ins.text == "4 of 10 are past the 5-year rotation norm; 2 are within 2 years of superannuation (exempt)."
    assert ins.facts == [4.0, 10.0, 5.0, 2.0, 2.0]


def test_policy_flags_none_cases():
    # Not row grain (e.g. aggregate)
    ctx_agg = InsightContext(
        metric="headcount", metric_label="Headcount", unit="employees",
        dim="discipline", value_col="headcount", grain="aggregate",
        rows=[{"discipline": "HR", "headcount": 10, "station_tenure_years": 6.0}],
    )
    assert policy_flags(ctx_agg) is None

    # Row grain without station_tenure_years column
    ctx_no_col = InsightContext(
        metric="roster", metric_label="Roster", unit="employees",
        dim=None, value_col=None, grain="row",
        rows=[{"name": "Emp1", "grade": "E4"}],
    )
    assert policy_flags(ctx_no_col) is None


# ------------------------------------------------------------------ compute_insights integration
def test_compute_insights_cap_and_order(example_context: InsightContext):
    example_context.prev_rows = [{"headcount": 400}]
    example_context.prev_label = "FY25"
    example_context.targets = {"HR": 100.0}

    # Triggered:
    # share_of_total (10)
    # vs_target (12)
    # delta_vs_last_year (15)
    # rank_extremes (20)
    # concentration (30)
    results = compute_insights(example_context, max_n=4)
    assert len(results) == 4
    priorities = [i.priority for i in results]
    assert priorities == sorted(priorities)
    assert priorities == [10, 12, 15, 20]


def test_compute_insights_exception_isolation(example_context: InsightContext, monkeypatch):
    def bad_insight(ctx):
        raise RuntimeError("Crash inside insight computation")

    monkeypatch.setattr("app.brain.insights.share_of_total", bad_insight)
    # Rebuild INSIGHT_FUNCS with bad_insight
    monkeypatch.setattr(
        "app.brain.insights.INSIGHT_FUNCS",
        [bad_insight, rank_extremes, concentration],
    )

    results = compute_insights(example_context)
    # Bad insight was safely caught; other insights computed
    types = [i.type for i in results]
    assert "rank" in types
    assert "concentration" in types


def test_to_contract_mapping():
    ins = Insight(
        kind="trend",
        type="delta",
        value=4.821,
        unit="%",
        ref="HR",
        text="Some text",
        facts=[4.8],
        priority=15,
    )
    c = ins.to_contract()
    assert c == {
        "text": "Some text",
        "kind": "trend",
        "value": 4.82,
        "unit": "%",
        "ref": "HR",
    }
