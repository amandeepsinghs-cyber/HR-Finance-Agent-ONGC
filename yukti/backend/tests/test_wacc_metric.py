"""Tests for WACC metrics, planning, charts, and execution (SPEC-02 §5, BEH-03.05, BEH-03.06)."""

import pandas as pd
import pytest

from app.agents.fin_diagnostics.wacc_attribution import (
    FACTOR_LABELS,
    WACCParameters,
    attribute_wacc_change,
    compute_wacc_shapley,
)
from app.brain.compiler import get_compiler
from app.brain.planner import get_planner


@pytest.fixture
def planner():
    return get_planner()


@pytest.fixture
def compiler():
    return get_compiler()


def test_planner_wacc_5_years(planner):
    """'WACC for the past 5 years' routes to wacc_pct, FY22–FY26, line chart."""
    plan = planner.to_plan("WACC for the past 5 years", {}, None)
    assert plan.intent == "data"
    assert plan.spec.metric == "wacc_pct"
    assert plan.chart_kind == "line"
    assert plan.spec.period.from_ == "FY22"
    assert plan.spec.period.to == "FY26"


def test_planner_wacc_10_years(planner):
    """'What was the weighted average cost of capital for the past 10 years?' routes to wacc_pct, FY17–FY26, line chart."""
    plan = planner.to_plan("What was the weighted average cost of capital for the past 10 years?", {}, None)
    assert plan.intent == "data"
    assert plan.spec.metric == "wacc_pct"
    assert plan.chart_kind == "line"
    assert plan.spec.period.from_ == "FY17"
    assert plan.spec.period.to == "FY26"


def test_planner_wacc_components_standalone(planner):
    """'show the WACC build-up / drivers' routes to wacc_components, stacked_bar."""
    plan = planner.to_plan("show the WACC build-up / drivers", {}, None)
    assert plan.intent == "data"
    assert plan.spec.metric == "wacc_components"
    assert plan.chart_kind == "stacked_bar"


def test_planner_wacc_components_followup(planner):
    """'show the build-up / drivers' as follow-up to wacc_pct routes to wacc_components, stacked_bar."""
    prev_plan = planner.to_plan("What was the weighted average cost of capital for the past 10 years?", {}, None)
    plan = planner.to_plan("show the build-up / drivers", {}, prev_plan.spec)
    assert plan.intent == "data"
    assert plan.spec.metric == "wacc_components"
    assert plan.chart_kind == "stacked_bar"


def test_planner_wacc_build_up_single_year(planner):
    """'WACC FY24' routes to wacc_build_up, table, period FY24."""
    plan = planner.to_plan("WACC FY24", {}, None)
    assert plan.intent == "data"
    assert plan.spec.metric == "wacc_build_up"
    assert plan.chart_kind == "table"
    assert plan.spec.period.fy == "FY24"


def test_planner_why_was_wacc_high_standalone(planner):
    """'why was WACC high in FY23' routes to wacc_change_attribution, waterfall, period FY23."""
    plan = planner.to_plan("why was WACC high in FY23", {}, None)
    assert plan.intent == "data"
    assert plan.spec.metric == "wacc_change_attribution"
    assert plan.chart_kind == "waterfall"
    assert plan.spec.period.fy == "FY23"


def test_planner_why_was_it_high_followup_beh_03_06(planner):
    """BEH-03.06: 'Why was it high in FY23?' after 10-year WACC routes to wacc_change_attribution waterfall."""
    prev_plan = planner.to_plan("What was the weighted average cost of capital for the past 10 years?", {}, None)
    plan = planner.to_plan("Why was it high in FY23?", {}, prev_plan.spec)
    assert plan.intent == "data"
    assert plan.spec.metric == "wacc_change_attribution"
    assert plan.chart_kind == "waterfall"
    assert plan.spec.period.fy == "FY23"


def test_fin_kw_guard_never_returns_pnl_for_wacc(planner):
    """Critical packet requirement: 'why is WACC high' never returns the P&L."""
    plan = planner.to_plan("why is WACC high", {}, None)
    assert plan.intent == "data"
    assert plan.spec.metric != "pnl_statement", "Guard regression: 'why is WACC high' returned pnl_statement!"
    assert plan.spec.metric == "wacc_change_attribution"
    assert plan.chart_kind == "waterfall"


def test_compiler_wacc_pct_sql(planner, compiler):
    """Verify compilation of wacc_pct produces valid SQL and metadata."""
    plan = planner.to_plan("WACC for the past 5 years", {}, None)
    compiled = compiler.compile(plan.spec)
    assert "hrfin_gold.fact_wacc_annual" in compiled.tables
    assert "fiscal_year" in compiled.sql
    assert "wacc_pct" in compiled.sql
    assert "ke_pct" in compiled.sql
    assert "kd_after_tax_pct" in compiled.value_columns
    assert compiled.unit == "pct"


def test_compiler_wacc_components_sql(planner, compiler):
    """Verify compilation of wacc_components produces stacked_bar columns."""
    plan = planner.to_plan("show the WACC build-up / drivers", {}, None)
    compiled = compiler.compile(plan.spec)
    assert "hrfin_gold.fact_wacc_annual" in compiled.tables
    assert "weighted_rf_pct" in compiled.value_columns
    assert "weighted_erp_pct" in compiled.value_columns
    assert "weighted_kd_after_tax_pct" in compiled.value_columns
    assert "wacc_pct" in compiled.value_columns


def test_compiler_wacc_build_up_sql(planner, compiler):
    """Verify compilation of wacc_build_up produces table of inputs from fact_wacc_input."""
    plan = planner.to_plan("WACC FY24", {}, None)
    compiled = compiler.compile(plan.spec)
    assert "hrfin_gold.fact_wacc_input" in compiled.tables
    assert "input_code" in compiled.sql
    assert compiled.effective_period["fy"] == "FY24"


def test_compiler_wacc_change_attribution_sql(planner, compiler):
    """Verify compilation of wacc_change_attribution sets waterfall dims and period."""
    plan = planner.to_plan("why was WACC high in FY23", {}, None)
    compiled = compiler.compile(plan.spec)
    assert "hrfin_gold.fact_wacc_annual" in compiled.tables
    assert compiled.effective_period["fy"] == "FY23"
    assert compiled.effective_period["from"] == "FY22"
    assert compiled.effective_period["to"] == "FY23"


def test_execution_local_fallback_wacc_pct_5yr(planner, compiler):
    """Local fallback execution for 5-yr WACC returns 5 rows, Modelled badge, caveat."""
    plan = planner.to_plan("WACC for the past 5 years", {}, None)
    compiled = compiler.compile(plan.spec)
    result = compiler._execute_local_financial_fallback(compiled)
    assert result is not None
    assert len(result.rows) == 5
    fys = [r["fiscal_year"] for r in result.rows]
    assert fys == ["FY22", "FY23", "FY24", "FY25", "FY26"]
    for r in result.rows:
        assert r["provenance_label"] == "modelled"
        assert "notes" in r


def test_execution_local_fallback_wacc_pct_10yr(planner, compiler):
    """Local fallback execution for 10-yr WACC returns 10 rows (FY17–FY26)."""
    plan = planner.to_plan("What was the weighted average cost of capital for the past 10 years?", {}, None)
    compiled = compiler.compile(plan.spec)
    result = compiler._execute_local_financial_fallback(compiled)
    assert result is not None
    assert len(result.rows) == 10
    assert result.rows[0]["fiscal_year"] == "FY17"
    assert result.rows[-1]["fiscal_year"] == "FY26"


def test_execution_local_fallback_wacc_components(planner, compiler):
    """Local fallback execution for wacc_components returns component columns."""
    plan = planner.to_plan("show the WACC build-up / drivers", {}, None)
    compiled = compiler.compile(plan.spec)
    result = compiler._execute_local_financial_fallback(compiled)
    assert result is not None
    assert len(result.rows) == 5
    first = result.rows[0]
    assert "weighted_rf_pct" in first
    assert "weighted_erp_pct" in first
    assert "weighted_kd_after_tax_pct" in first
    assert "wacc_pct" in first


def test_execution_local_fallback_wacc_build_up(planner, compiler):
    """Local fallback execution for wacc_build_up returns 17 lineage inputs (including shares_outstanding)."""
    plan = planner.to_plan("WACC FY24", {}, None)
    compiled = compiler.compile(plan.spec)
    result = compiler._execute_local_financial_fallback(compiled)
    assert result is not None
    assert len(result.rows) == 17
    codes = {r["input_code"] for r in result.rows}
    assert "rf_gsec_10y" in codes
    assert "erp_total_india" in codes
    assert "kd_used" in codes
    assert "shares_outstanding" in codes
    assert "wacc" in codes


def test_execution_local_fallback_wacc_change_attribution(planner, compiler):
    """Local fallback execution for wacc_change_attribution returns 7 waterfall rows."""
    plan = planner.to_plan("why was WACC high in FY23", {}, None)
    compiled = compiler.compile(plan.spec)
    result = compiler._execute_local_financial_fallback(compiled)
    assert result is not None
    assert len(result.rows) == 7
    assert result.rows[0]["factor"] == "WACC FY22"
    assert result.rows[0]["bar_type"] == "base"
    assert result.rows[-1]["factor"] == "WACC FY23"
    assert result.rows[-1]["bar_type"] == "total"


def test_attribute_wacc_change_with_populated_dataframe():
    """Verify attribute_wacc_change on a DataFrame with complete values."""
    mock_ann = pd.DataFrame([
        {
            "fiscal_year": "FY22",
            "rf_used_pct": 5.0,
            "erp_total_pct": 7.0,
            "beta_2y_weekly_adj": 1.0,
            "kd_used_pct": 5.3454,
            "tax_rate_pct": 25.17,
            "weight_equity": 0.90,
            "wacc_pct": 11.20,
            "verified": True,
            "notes": None,
        },
        {
            "fiscal_year": "FY23",
            "rf_used_pct": 5.5,
            "erp_total_pct": 7.5,
            "beta_2y_weekly_adj": 1.1,
            "kd_used_pct": 5.6127,
            "tax_rate_pct": 25.17,
            "weight_equity": 0.88,
            "wacc_pct": 12.604,
            "verified": True,
            "notes": None,
        },
    ])

    res = attribute_wacc_change(mock_ann, "FY22", "FY23")
    assert res is not None
    assert abs(res.delta_wacc - 1.404) < 1e-4
    assert abs(sum(res.contributions.values()) - res.delta_wacc) < 1e-9
    assert res.contributions["rf_used"] > 0
    assert res.contributions["erp_total"] > 0
    assert res.contributions["beta"] > 0
    assert res.contributions["kd_after_tax"] > 0
    assert res.contributions["weights"] < 0
    assert len(res.top_factors) == 2
    assert res.top_factors[0].factor == "beta"
    assert res.top_factors[1].factor == "erp_total"
