"""Unit tests for the variance-attribution engine (P2F.4, SPEC-08 §6.1, §6.5)."""

from pathlib import Path
import sys

# Ensure yukti/backend is on sys.path regardless of execution cwd
_backend_dir = Path(__file__).resolve().parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

import pytest
import pandas as pd

from app.agents.fin_diagnostics import (
    Bridge,
    BridgeDoesNotClose,
    VarianceRow,
    attribute,
    pbt_bridge,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ten_year_fy25_fy26.csv"


@pytest.fixture
def df_fy25_fy26() -> pd.DataFrame:
    """Load verified FY25/FY26 10-year summary fixture."""
    return pd.read_csv(FIXTURE_PATH)


def test_pbt_bridge_fy26_closure_and_ranking(df_fy25_fy26: pd.DataFrame):
    """Assert full FY26 vs FY25 PBT bridge closure and driver ranking (SPEC-08 §6.5, packet §6)."""
    bridge = pbt_bridge(df_fy25_fy26, fy_to="FY26")

    # Bridge bounds
    assert bridge.start == pytest.approx(46759.8, abs=0.1)
    assert bridge.end == pytest.approx(42414.9, abs=0.1)
    assert bridge.delta == pytest.approx(-4344.9, abs=0.1)
    assert bridge.closure_error <= 0.1

    # Exactly 10 drivers
    assert len(bridge.rows) == 10

    # Ordered ranking by |impact_on_pbt| descending
    expected_ranking = [
        ("PL.REV_OPS", -5338.2, 1),
        ("LEVY.TOTAL", 4820.4, 2),
        ("PL.EXCHANGE_LOSS_10YR", -1931.7, 3),
        ("PL.PROVISIONS_WRITEOFF", -1142.4, 4),
        ("PL.DDA", -781.4, 5),
        ("PL.OPEX_10YR", -730.1, 6),
        ("PL.OTHER_EXP_10YR", 710.4, 7),
        ("PL.OTHER_INCOME", -123.6, 8),
        ("PL.EXPL_WRITEOFF", 97.0, 9),
        ("PL.FIN_COST", 74.7, 10),
    ]

    for idx, (expected_code, expected_impact, expected_rank) in enumerate(expected_ranking):
        row = bridge.rows[idx]
        assert row.line_code == expected_code
        assert row.rank == expected_rank
        assert row.impact_on_pbt_inr_cr == pytest.approx(expected_impact, abs=0.2)
        assert row.method == "M-BRIDGE"
        assert row.coverage == "full"
        assert len(row.inputs) >= 2
        for inp in row.inputs:
            assert inp["line_code"]
            assert inp["fy"] in ("FY25", "FY26")
            assert inp["value"] is not None
            assert inp["source"]


def test_attribute_crude_revenue_pv(df_fy25_fy26: pd.DataFrame):
    """Assert Crude revenue M-REV-PV volume and price/FX decomposition (packet §6)."""
    rows = attribute(df_fy25_fy26, "REV.CRUDE", "FY26")
    assert len(rows) == 2

    # Map by component
    by_comp = {r.component: r for r in rows}
    assert "volume" in by_comp
    assert "price_incl_fx" in by_comp

    vol_row = by_comp["volume"]
    price_row = by_comp["price_incl_fx"]

    # Expected values from packet §6: volume +382.8, price_incl_fx −6107.9 (±0.1)
    assert vol_row.impact_inr_cr == pytest.approx(382.8, abs=0.1)
    assert vol_row.impact_on_pbt_inr_cr == pytest.approx(382.8, abs=0.1)
    assert vol_row.method == "M-REV-PV"
    assert vol_row.coverage == "full"

    assert price_row.impact_inr_cr == pytest.approx(-6107.9, abs=0.1)
    assert price_row.impact_on_pbt_inr_cr == pytest.approx(-6107.9, abs=0.1)
    assert price_row.method == "M-REV-PV"
    assert price_row.coverage == "full"

    # Exact closure to line delta
    expected_delta = 83810.2 - 89535.3
    assert (vol_row.impact_inr_cr + price_row.impact_inr_cr) == pytest.approx(expected_delta, abs=0.1)

    # Ranking: price_incl_fx has larger magnitude -> rank 1, volume -> rank 2
    assert price_row.rank == 1
    assert vol_row.rank == 2


def test_attribute_gas_revenue_pv(df_fy25_fy26: pd.DataFrame):
    """Assert Natural Gas revenue M-REV-PV volume and price/FX decomposition (packet §6)."""
    rows = attribute(df_fy25_fy26, "REV.GAS", "FY26")
    assert len(rows) == 2

    by_comp = {r.component: r for r in rows}
    assert "volume" in by_comp
    assert "price_incl_fx" in by_comp

    vol_row = by_comp["volume"]
    price_row = by_comp["price_incl_fx"]

    # Expected values from packet §6: volume −41.4, price_incl_fx +2553.5 (±0.1)
    assert vol_row.impact_inr_cr == pytest.approx(-41.4, abs=0.1)
    assert vol_row.impact_on_pbt_inr_cr == pytest.approx(-41.4, abs=0.1)
    assert vol_row.method == "M-REV-PV"

    assert price_row.impact_inr_cr == pytest.approx(2553.5, abs=0.1)
    assert price_row.impact_on_pbt_inr_cr == pytest.approx(2553.5, abs=0.1)
    assert price_row.method == "M-REV-PV"

    # Exact closure to line delta
    expected_delta = 36329.9 - 33817.8
    assert (vol_row.impact_inr_cr + price_row.impact_inr_cr) == pytest.approx(expected_delta, abs=0.1)


def test_attribute_policy_levy(df_fy25_fy26: pd.DataFrame):
    """Assert SAED / policy levy M-POLICY decomposition (packet §6)."""
    for code in ("LEVY.OTHER", "LEVY.OTHER_SAED"):
        rows = attribute(df_fy25_fy26, code, "FY26")
        assert len(rows) == 1
        r = rows[0]
        assert r.component == "policy_levy"
        assert r.method == "M-POLICY"
        assert r.impact_inr_cr == pytest.approx(-3969.4, abs=0.1)
        assert r.impact_on_pbt_inr_cr == pytest.approx(3969.4, abs=0.1)
        assert r.coverage == "full"
        assert r.rank == 1


def test_degradation_missing_crude_qty(df_fy25_fy26: pd.DataFrame):
    """Assert graceful degradation when QTY.CRUDE_SOLD is dropped (packet §7)."""
    df_no_qty = df_fy25_fy26[df_fy25_fy26["line_code"] != "QTY.CRUDE_SOLD"]

    # Crude revenue degrades to other_unexplained with coverage='partial'
    rows = attribute(df_no_qty, "REV.CRUDE", "FY26")
    assert len(rows) == 1
    r = rows[0]
    assert r.component == "other_unexplained"
    assert r.coverage == "partial"
    assert r.impact_inr_cr == pytest.approx(83810.2 - 89535.3, abs=0.1)
    assert r.impact_on_pbt_inr_cr == pytest.approx(83810.2 - 89535.3, abs=0.1)

    # Full PBT bridge still closes
    bridge = pbt_bridge(df_no_qty, "FY26")
    assert bridge.closure_error <= 0.1
    assert bridge.delta == pytest.approx(-4344.9, abs=0.1)


def test_bridge_does_not_close_when_cost_line_missing(df_fy25_fy26: pd.DataFrame):
    """Assert BridgeDoesNotClose is raised when a cost line is omitted (packet §7)."""
    df_no_cost = df_fy25_fy26[~df_fy25_fy26["line_code"].isin(["PL.FIN_COST"])]
    with pytest.raises(BridgeDoesNotClose) as exc_info:
        pbt_bridge(df_no_cost, "FY26")
    assert "PBT bridge does not close" in str(exc_info.value)


def test_determinism(df_fy25_fy26: pd.DataFrame):
    """Assert deterministic execution: repeated runs produce identical outputs (packet §7)."""
    b1 = pbt_bridge(df_fy25_fy26, "FY26")
    b2 = pbt_bridge(df_fy25_fy26, "FY26")
    assert b1.to_dict() == b2.to_dict()
    assert b1 == b2

    a1 = attribute(df_fy25_fy26, "REV.CRUDE", "FY26")
    a2 = attribute(df_fy25_fy26, "REV.CRUDE", "FY26")
    assert [r.to_dict() for r in a1] == [r.to_dict() for r in a2]
    assert a1 == a2


def test_sub_line_decompositions(df_fy25_fy26: pd.DataFrame):
    """Assert sub-line decompositions for exploration, other income, and statutory levies."""
    # Exploration write-offs
    expl_rows = attribute(df_fy25_fy26, "PL.EXPL_WRITEOFF", "FY26")
    assert len(expl_rows) == 2
    expl_map = {r.line_code: r for r in expl_rows}
    assert expl_map["PL.EXPL_SURVEY"].impact_inr_cr == pytest.approx(1492.8 - 2345.8, abs=0.1)
    assert expl_map["PL.EXPL_SURVEY"].impact_on_pbt_inr_cr == pytest.approx(-(1492.8 - 2345.8), abs=0.1)
    assert expl_map["PL.EXPL_WELL"].impact_inr_cr == pytest.approx(8236.0 - 7480.0, abs=0.1)
    assert expl_map["PL.EXPL_WELL"].impact_on_pbt_inr_cr == pytest.approx(-(8236.0 - 7480.0), abs=0.1)

    # Other income
    inc_rows = attribute(df_fy25_fy26, "PL.OTHER_INCOME", "FY26")
    assert len(inc_rows) == 2
    inc_map = {r.line_code: r for r in inc_rows}
    assert inc_map["PL.DIVIDEND_INCOME_10YR"].impact_inr_cr == pytest.approx(4806.8 - 3460.4, abs=0.1)
    assert inc_map["PL.OTHER_NON_OP_INCOME_10YR"].impact_inr_cr == pytest.approx(5549.0 - 7019.0, abs=0.1)

    # Statutory levies
    levy_rows = attribute(df_fy25_fy26, "LEVY.TOTAL", "FY26")
    assert len(levy_rows) == 4
    levy_map = {r.line_code: r for r in levy_rows}
    assert levy_map["LEVY.ROYALTY"].impact_inr_cr == pytest.approx(12965.1 - 13368.0, abs=0.1)
    assert levy_map["LEVY.OIDB_CESS"].impact_inr_cr == pytest.approx(13033.5 - 13480.2, abs=0.1)
    assert levy_map["LEVY.NCCD"].impact_inr_cr == pytest.approx(86.0 - 87.4, abs=0.1)
    assert levy_map["LEVY.OTHER_SAED"].impact_inr_cr == pytest.approx(63.0 - 4032.4, abs=0.1)


def test_line_aliases(df_fy25_fy26: pd.DataFrame):
    """Assert canonical aliases resolve correctly."""
    r_opex1 = attribute(df_fy25_fy26, "PL.OPEX", "FY26")
    r_opex2 = attribute(df_fy25_fy26, "PL.OPEX_10YR", "FY26")
    assert r_opex1[0].delta_inr_cr == r_opex2[0].delta_inr_cr

    r_exch1 = attribute(df_fy25_fy26, "PL.EXCHANGE_LOSS", "FY26")
    r_exch2 = attribute(df_fy25_fy26, "PL.EXCHANGE_LOSS_10YR", "FY26")
    assert r_exch1[0].delta_inr_cr == r_exch2[0].delta_inr_cr
