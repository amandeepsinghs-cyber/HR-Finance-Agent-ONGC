"""P1.10a tests: Compiler switch to verified SSOT rows, vintage rules, poisoned-row filter, and honest provenance."""

from __future__ import annotations

import asyncio
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import pytest

from app.brain.compiler import Compiler
from app.brain.planner import Filter, Period, QuerySpec
from app.brain.pipeline import run_planner_turn
from app.brain.presenter import build_visual
from app.session_memory import get_session_manager


FIXTURE_MIN_PARQUET = Path(__file__).resolve().parent / "fixtures" / "fact_snapshot_min.parquet"


# ---------------------------------------------------------------------------
# Canonical F01–F11, F13–F31 cases (SPEC-11 §8.2)
# ---------------------------------------------------------------------------
FINANCE_CASES: List[Dict[str, Any]] = [
    {
        "id": "F01",
        "spec": QuerySpec(metric="corporate_revenue_cr", period=Period(fy="FY24")),
        "col": "corporate_revenue_cr",
        "expected": {None: 138402.13},
        "tol": 0.05,
        "provenance": "verified_ar",
        "doc": "ONGC_AR_FY2023-24.pdf",
        "page_label": "245",
    },
    {
        "id": "F02",
        "spec": QuerySpec(metric="pat_cr", period=Period(fy="FY24")),
        "col": "pat_cr",
        "expected": {None: 40525.97},
        "tol": 0.05,
        "provenance": "verified_ar",
        "doc": "ONGC_AR_FY2023-24.pdf",
        "page_label": "245",
    },
    {
        "id": "F03",
        "spec": QuerySpec(metric="tax_expense_cr", period=Period(fy="FY25")),
        "col": "tax_expense_cr",
        "expected": {None: 11149.50},
        "tol": 0.05,
        "provenance": "verified_ar",
        "doc": "ONGC_AR_FY2024-25.pdf",
        "page_label": "271",
    },
    {
        "id": "F04",
        "spec": QuerySpec(metric="pbt_corporate_cr", period=Period(fy="FY26")),
        "col": "pbt_corporate_cr",
        "expected": {None: 42414.89},
        "tol": 0.05,
        "provenance": "verified_ar",
        "doc": "ONGC_AR_FY2025-26.pdf",
        "page_label": "295",
    },
    {
        "id": "F05",
        "spec": QuerySpec(metric="eps_basic_inr", period=Period(fy="FY25")),
        "col": "eps_basic_inr",
        "expected": {None: 28.31},
        "tol": 0.05,
        "provenance": "verified_ar",
        "doc": "ONGC_AR_FY2024-25.pdf",
        "page_label": "271",
    },
    {
        "id": "F07",
        "spec": QuerySpec(metric="total_assets_cr", period=Period(fy="FY26")),
        "col": "total_assets_cr",
        "expected": {None: 461276.20},
        "tol": 0.05,
        "provenance": "verified_ar",
        "doc": "ONGC_AR_FY2025-26.pdf",
        "page_label": "293",
    },
    {
        "id": "F08",
        "spec": QuerySpec(metric="operating_cash_flow_cr", period=Period(fy="FY25")),
        "col": "operating_cash_flow_cr",
        "expected": {None: 73010.24},
        "tol": 0.05,
        "provenance": "verified_ar",
    },
    {
        "id": "F09",
        "spec": QuerySpec(metric="operating_cash_flow_cr", period=Period(fy="FY24")),
        "col": "operating_cash_flow_cr",
        "expected": {None: 65335.52},
        "tol": 0.05,
        "provenance": "verified_ar",
    },
    {
        "id": "F10",
        "spec": QuerySpec(metric="operating_cash_flow_cr", period=Period(fy="FY26")),
        "col": "operating_cash_flow_cr",
        "expected": {None: 69272.39},
        "tol": 0.05,
        "provenance": "verified_ar",
    },
    {
        "id": "F11",
        "spec": QuerySpec(metric="cash_and_bank_cr", period=Period(fy="FY26")),
        "col": "cash_and_bank_cr",
        "expected": {None: 83.51},
        "tol": 0.05,
        "provenance": "verified_ar",
    },
    {
        "id": "F13",
        "spec": QuerySpec(
            metric="corporate_revenue_cr",
            period=Period(from_="FY17", to="FY26"),
            dimensions=["fy"],
        ),
        "col": "corporate_revenue_cr",
        "expected": {
            "FY17": 77907.8,
            "FY18": 85004.1,
            "FY19": 109654.6,
            "FY20": 96213.6,
            "FY21": 68141.1,
            "FY22": 110345.4,
            "FY23": 155517.3,
            "FY24": 138402.1,
            "FY25": 137846.3,
            "FY26": 132508.1,
        },
        "tol": 0.10,
        "provenance": "verified_ar",
    },
    {
        "id": "F14",
        "spec": QuerySpec(
            metric="pat_cr",
            period=Period(from_="FY22", to="FY26"),
            dimensions=["fy"],
        ),
        "col": "pat_cr",
        "expected": {
            "FY22": 40305.7,
            "FY23": 40096.5,
            "FY24": 40526.0,
            "FY25": 35610.3,
            "FY26": 32894.0,
        },
        "tol": 0.10,
        "provenance": "verified_ar",
    },
    {
        "id": "F15",
        "spec": QuerySpec(metric="roce_pct", period=Period(fy="FY23")),
        "col": "roce_pct",
        "expected": {None: 39.82},
        "extra_cols": {"roce_incl_exc_pct": 33.84},
        "tol": 0.05,
        "provenance": "verified_ar",
    },
    {
        "id": "F16",
        "spec": QuerySpec(
            metric="roce_pct",
            period=Period(from_="FY22", to="FY26"),
            dimensions=["fy"],
        ),
        "col": "roce_pct",
        "expected": {
            "FY22": 29.01,
            "FY23": 39.82,
            "FY24": 30.60,
            "FY25": 26.54,
            "FY26": 22.46,
        },
        "tol": 0.05,
        "provenance": "verified_ar",
    },
    {
        "id": "F17",
        "spec": QuerySpec(metric="royalty_cr", period=Period(fy="FY17")),
        "col": "royalty_cr",
        "expected": {None: 11574.8},
        "tol": 0.10,
        "provenance": "verified_ar",
    },
    {
        "id": "F18",
        "spec": QuerySpec(metric="statutory_levies_cr", period=Period(fy="FY24")),
        "col": "statutory_levies_cr",
        "expected": {None: 36797.5},
        "tol": 0.10,
        "provenance": "verified_ar",
    },
    {
        "id": "F19",
        "spec": QuerySpec(
            metric="saed_windfall_tax_cr",
            period=Period(from_="FY25", to="FY26"),
            dimensions=["fy"],
        ),
        "col": "saed_windfall_tax_cr",
        "expected": {"FY25": 4032.4, "FY26": 63.0},
        "tol": 0.10,
        "provenance": "verified_ar",
    },
    {
        "id": "F20",
        "spec": QuerySpec(metric="total_capex_cr", period=Period(fy="FY25")),
        "col": "total_capex_cr",
        "expected": {None: 62057.3},
        "tol": 0.10,
        "provenance": "verified_ar",
    },
    {
        "id": "F21",
        "spec": QuerySpec(
            metric="total_capex_cr",
            period=Period(from_="FY17", to="FY26"),
            dimensions=["fy"],
        ),
        "col": "total_capex_cr",
        "expected": {
            "FY17": 28006.4,
            "FY18": 72901.6,
            "FY19": 29449.8,
            "FY20": 29538.5,
            "FY21": 26859.3,
            "FY22": 27741.3,
            "FY23": 30208.4,
            "FY24": 37494.2,
            "FY25": 62057.3,
            "FY26": 35878.4,
        },
        "tol": 0.10,
        "provenance": "verified_ar",
    },
    {
        "id": "F22",
        "spec": QuerySpec(metric="dividend_payout_cr", period=Period(fy="FY26")),
        "col": "dividend_payout_cr",
        "expected": {None: 16668.9},
        "extra_cols": {"dividend_pct": 265.0},
        "tol": 0.10,
        "provenance": "verified_ar",
    },
    {
        "id": "F23",
        "spec": QuerySpec(metric="debt_to_equity_ratio", period=Period(fy="FY26")),
        "col": "debt_to_equity_ratio",
        "expected": {None: 0.02},
        "tol": 0.01,
        "provenance": "verified_ar",
    },
    {
        "id": "F24",
        "spec": QuerySpec(metric="total_debt_cr", period=Period(fy="FY26")),
        "col": "total_debt_cr",
        "expected": {None: 7823.4},
        "extra_cols": {"lease_liabilities_cr": 25821.8},
        "tol": 0.10,
        "provenance": "verified_ar",
    },
    {
        "id": "F25",
        "spec": QuerySpec(metric="exploration_costs_written_off_cr", period=Period(fy="FY25")),
        "col": "exploration_costs_written_off_cr",
        "expected": {None: 9825.8},
        "extra_cols": {"survey_costs_written_off_cr": 2345.8, "exploratory_wells_written_off_cr": 7480.0},
        "tol": 0.10,
        "provenance": "verified_ar",
    },
    {
        "id": "F26",
        "spec": QuerySpec(metric="dda_cr", period=Period(fy="FY26")),
        "col": "dda_cr",
        "expected": {None: 25133.82},
        "tol": 0.05,
        "provenance": "verified_ar",
        "doc": "ONGC_AR_FY2025-26.pdf",
        "page_label": "295",
    },
    {
        "id": "F27",
        "spec": QuerySpec(metric="finance_costs_cr", period=Period(fy="FY24")),
        "col": "finance_costs_cr",
        "expected": {None: 4081.31},
        "tol": 0.05,
        "provenance": "verified_ar",
        "doc": "ONGC_AR_FY2023-24.pdf",
        "page_label": "245",
    },
    {
        "id": "F28",
        "spec": QuerySpec(metric="other_income_cr", period=Period(fy="FY24")),
        "col": "other_income_cr",
        "expected": {None: 10778.19},
        "tol": 0.05,
        "provenance": "verified_ar",
        "expect_is_restated": False,
        "doc": "ONGC_AR_FY2023-24.pdf",
        "page_label": "245",
    },
    {
        "id": "F29",
        "spec": QuerySpec(
            metric="other_income_cr",
            period=Period(from_="FY24", to="FY26"),
            dimensions=["fy"],
        ),
        "col": "other_income_cr",
        "expected": {"FY24": 10735.52, "FY25": 10479.40, "FY26": 10355.81},
        "tol": 0.10,
        "provenance": "verified_ar",
        "restated_fy": "FY24",
    },
    {
        "id": "F30",
        "spec": QuerySpec(metric="pat_cr", period=Period(fy="FY19")),
        "col": "pat_cr",
        "expected": {None: 26715.79},
        "tol": 0.10,
        "provenance": "verified_ar",
        "expect_is_restated": False,
    },
    {
        "id": "F31",
        "spec": QuerySpec(
            metric="pat_cr",
            period=Period(from_="FY17", to="FY26"),
            dimensions=["fy"],
        ),
        "col": "pat_cr",
        "expected": {"FY19": 26764.60},
        "tol": 0.10,
        "provenance": "verified_ar",
        "restated_fy": "FY19",
    },
]


@pytest.mark.parametrize("mode", ["bigquery", "local_snapshot"])
@pytest.mark.parametrize("case", FINANCE_CASES, ids=[c["id"] for c in FINANCE_CASES])
def test_finance_cases_compiler_and_provenance(
    monkeypatch: pytest.MonkeyPatch, mode: str, case: Dict[str, Any]
) -> None:
    """Verify F01–F11, F13–F31 return exact SSOT values in both live BigQuery and local_snapshot modes."""
    if mode == "local_snapshot":
        monkeypatch.setenv("YUKTI_FORCE_BQ_FAIL", "1")
    else:
        monkeypatch.delenv("YUKTI_FORCE_BQ_FAIL", raising=False)

    comp = Compiler()
    compiled = comp.compile(case["spec"])
    res = asyncio.run(comp.execute(compiled))

    assert res.source == mode, f"{case['id']} ({mode}): expected source={mode}, got {res.source}"
    assert len(res.rows) >= 1, f"{case['id']} ({mode}): returned 0 rows"

    col = case["col"]
    tol = case["tol"]
    expected_map: Dict[Optional[str], float] = case["expected"]

    if None in expected_map:
        r0 = res.rows[0]
        actual = float(r0[col])
        exp = expected_map[None]
        assert abs(actual - exp) <= tol, f"{case['id']} ({mode}): expected {exp} ± {tol}, got {actual}"
        for extra_c, extra_exp in (case.get("extra_cols") or {}).items():
            assert abs(float(r0[extra_c]) - extra_exp) <= tol, (
                f"{case['id']} ({mode}) extra col {extra_c}: expected {extra_exp}, got {r0.get(extra_c)}"
            )
        if "expect_is_restated" in case:
            assert bool(r0.get("is_restated")) is case["expect_is_restated"]
        if mode == "bigquery" and "doc" in case:
            assert r0.get("source_doc") == case["doc"]
            assert str(r0.get("source_page_label")) == case["page_label"]
    else:
        by_fy = {str(r["fiscal_year"]): r for r in res.rows}
        for fy_k, exp_v in expected_map.items():
            assert fy_k in by_fy, f"{case['id']} ({mode}): missing {fy_k} in {list(by_fy.keys())}"
            actual = float(by_fy[fy_k][col])
            assert abs(actual - exp_v) <= tol, (
                f"{case['id']} ({mode}) {fy_k}: expected {exp_v} ± {tol}, got {actual}"
            )
        if "restated_fy" in case:
            rfy = case["restated_fy"]
            assert bool(by_fy[rfy].get("is_restated")) is True
            assert by_fy[rfy].get("footnote_marker"), f"{case['id']} ({mode}): missing footnote_marker on restated {rfy}"


@pytest.mark.parametrize("mode", ["bigquery", "local_snapshot"])
def test_f06_balance_sheet_2024_and_statement_columns(monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    """Verify F06 (FY24 Balance Sheet) returns exact Total Assets, Total Equity, and Packet §5.1 columns."""
    if mode == "local_snapshot":
        monkeypatch.setenv("YUKTI_FORCE_BQ_FAIL", "1")
    else:
        monkeypatch.delenv("YUKTI_FORCE_BQ_FAIL", raising=False)

    comp = Compiler()
    spec = QuerySpec(metric="balance_sheet", period=Period(fy="FY24"))
    compiled = comp.compile(spec)
    res = asyncio.run(comp.execute(compiled))

    assert res.source == mode
    required_cols = {
        "line_code",
        "display_name",
        "level",
        "line_kind",
        "fiscal_year",
        "value_inr_cr",
        "is_restated",
        "source_doc",
        "source_page_label",
    }
    assert required_cols.issubset(set(res.columns)), f"Missing required §5.1 columns: {required_cols - set(res.columns)}"

    by_code = {str(r["line_code"]): r for r in res.rows}
    assert abs(float(by_code["BS.TOTAL_ASSETS"]["value_inr_cr"]) - 446020.89) <= 0.05
    assert abs(float(by_code["BS.EQUITY.TOTAL"]["value_inr_cr"]) - 305976.51) <= 0.05
    assert by_code["BS.TOTAL_ASSETS"]["source_doc"] == "ONGC_AR_FY2023-24.pdf"
    assert str(by_code["BS.TOTAL_ASSETS"]["source_page_label"]) == "243"


def test_poisoned_unverified_row_never_served(monkeypatch: pytest.MonkeyPatch) -> None:
    """Packet P1.10a §7 AC-2: Poisoned row (verified=FALSE) in fact_snapshot_min.parquet is never served."""
    assert FIXTURE_MIN_PARQUET.exists(), f"Missing fixture {FIXTURE_MIN_PARQUET}"
    monkeypatch.setenv("YUKTI_FORCE_BQ_FAIL", "1")
    monkeypatch.setenv("YUKTI_FIN_SNAPSHOT_PATH", str(FIXTURE_MIN_PARQUET))

    comp = Compiler()
    # 1) Query PL.REV_OPS for FY24 (where fixture has both verified=True 138402.13 and a poisoned verified=False 999999.99 row)
    spec_rev = QuerySpec(metric="corporate_revenue_cr", period=Period(fy="FY24"))
    res_rev = asyncio.run(comp.execute(comp.compile(spec_rev)))
    assert len(res_rev.rows) == 1
    assert abs(float(res_rev.rows[0]["corporate_revenue_cr"]) - 138402.13) <= 0.05

    # 2) Query full FY24 P&L statement and verify neither 999999.99 nor PL.POISON_UNVERIFIED appears
    spec_pnl = QuerySpec(metric="pnl_statement", period=Period(fy="FY24"))
    res_pnl = asyncio.run(comp.execute(comp.compile(spec_pnl)))
    codes = {str(r["line_code"]) for r in res_pnl.rows}
    assert "PL.POISON_UNVERIFIED" not in codes
    for r in res_pnl.rows:
        assert float(r["value_inr_cr"]) != 999999.99


def test_pipeline_provenance_and_no_ebitda_synthesis(monkeypatch: pytest.MonkeyPatch) -> None:
    """Packet P1.10a §5.2–5.4: Verify pipeline provenance labels, snapshot caveat, and zero EBITDA synthesis on P&L waterfall."""
    sm = get_session_manager()

    # 1) Live BigQuery provenance on F01 and F15
    monkeypatch.delenv("YUKTI_FORCE_BQ_FAIL", raising=False)
    st1 = sm.get_or_create(f"p110a-f01-{time.time_ns()}", persona="CMD", language="en")
    r_f01 = asyncio.run(
        run_planner_turn(
            "What was revenue from operations in FY24?",
            st1,
            "CMD",
            "turn-f01",
            "en",
            time.perf_counter(),
            spec_override=QuerySpec(domain="finance", metric="corporate_revenue_cr", period=Period(fy="FY24")),
        )
    )
    assert r_f01 is not None
    c_f01 = r_f01["contract"]
    assert c_f01["provenance"]["label"] == "verified_ar"
    assert c_f01["provenance"]["doc"] == "ONGC_AR_FY2023-24.pdf"
    assert str(c_f01["provenance"]["page_label"]) == "245"
    assert all("unverified" not in str(s).lower() for s in c_f01["sources"])

    st2 = sm.get_or_create(f"p110a-f15-{time.time_ns()}", persona="DIR_FIN", language="en")
    r_f15 = asyncio.run(
        run_planner_turn(
            "What was ROCE in FY23?",
            st2,
            "DIR_FIN",
            "turn-f15",
            "en",
            time.perf_counter(),
            spec_override=QuerySpec(domain="finance", metric="roce_pct", period=Period(fy="FY23")),
        )
    )
    assert r_f15 is not None
    c_f15 = r_f15["contract"]
    assert c_f15["provenance"]["label"] == "verified_ar"
    assert c_f15["provenance"]["badge"] == "AR-printed"

    # 2) Local snapshot provenance and caveat
    monkeypatch.setenv("YUKTI_FORCE_BQ_FAIL", "1")
    st3 = sm.get_or_create(f"p110a-snap-{time.time_ns()}", persona="CMD", language="en")
    r_snap = asyncio.run(
        run_planner_turn(
            "What was ONGC's PAT in FY24?",
            st3,
            "CMD",
            "turn-snap",
            "en",
            time.perf_counter(),
            spec_override=QuerySpec(domain="finance", metric="pat_cr", period=Period(fy="FY24")),
        )
    )
    assert r_snap is not None
    c_snap = r_snap["contract"]
    assert c_snap["status"]["source"] == "local_snapshot"
    assert c_snap["generated_sql"] is None
    assert c_snap["provenance"]["label"] == "local_snapshot"
    assert "Served from the verified local snapshot of " in c_snap["caveat"]
    assert "BigQuery unavailable." in c_snap["caveat"]
    assert c_snap["sources"][0]["object"].startswith("local_snapshot:fact_financial_statement_line@")

    # 3) P&L statement visual waterfall has zero synthesized EBITDA stage
    comp = Compiler()
    spec_pnl = QuerySpec(metric="pnl_statement", period=Period(fy="FY26"))
    compiled_pnl = comp.compile(spec_pnl)
    res_pnl = asyncio.run(comp.execute(compiled_pnl))
    vis = build_visual(spec_pnl, compiled_pnl, res_pnl.columns, res_pnl.rows, "waterfall", "P&L", "FY26", "replace", len(res_pnl.rows))
    wf_stages = [str(r.get("pnl_stage", "")) for r in vis["chart"]["data"]]
    assert all("EBITDA" not in st.upper() for st in wf_stages), f"Found synthesized EBITDA in waterfall stages: {wf_stages}"
    for kpi in vis["kpis"]:
        assert "EBITDA" not in str(kpi.get("label", "")).upper()
