"""Unit tests for WACC 5-factor Shapley attribution (SPEC-02 §5.3, Packet P2F.3 §6)."""

import pytest

from app.agents.fin_diagnostics.wacc_attribution import (
    WACCParameters,
    calculate_ke,
    calculate_wacc,
    compute_wacc_shapley,
)


def test_packet_fixture_wacc_shapley():
    """Verify Packet P2F.3 §6 fixture:

    WACC_a from (rf 5%, erp 7%, β 1.0, kd_at 4%, wE 0.9)
    to WACC_b (rf 5.5%, erp 7.5%, β 1.1, kd_at 4.2%, wE 0.88)
    → Σ contributions = WACC_b − WACC_a (±1e-9);
      rf, erp, β, kd contributions > 0;
      weights contribution < 0 (equity weight falls while Ke > Kd after tax)
    """
    params_a = WACCParameters(
        fiscal_year="FY22",
        rf_used=5.0,
        erp_total=7.0,
        beta=1.0,
        kd_after_tax=4.0,
        weight_equity=0.90,
    )
    params_b = WACCParameters(
        fiscal_year="FY23",
        rf_used=5.5,
        erp_total=7.5,
        beta=1.1,
        kd_after_tax=4.2,
        weight_equity=0.88,
    )

    # Hand-calculate Ke and WACC
    # Ke_a = 5.0 + 1.0 * 7.0 = 12.0
    # WACC_a = 0.9 * 12.0 + 0.1 * 4.0 = 10.8 + 0.4 = 11.20%
    assert abs(params_a.ke() - 12.0) < 1e-6
    assert abs(params_a.wacc() - 11.20) < 1e-6

    # Ke_b = 5.5 + 1.1 * 7.5 = 5.5 + 8.25 = 13.75%
    # WACC_b = 0.88 * 13.75 + 0.12 * 4.2 = 12.10 + 0.504 = 12.604%
    assert abs(params_b.ke() - 13.75) < 1e-6
    assert abs(params_b.wacc() - 12.604) < 1e-6

    delta_expected = 12.604 - 11.20  # 1.404%
    assert abs(delta_expected - 1.404) < 1e-6

    # Execute Shapley decomposition
    result = compute_wacc_shapley(params_a, params_b)

    assert result.fy_from == "FY22"
    assert result.fy_to == "FY23"
    assert abs(result.wacc_from - 11.20) < 1e-6
    assert abs(result.wacc_to - 12.604) < 1e-6
    assert abs(result.delta_wacc - 1.404) < 1e-6

    c = result.contributions
    assert len(c) == 5

    # 1. Closure rule: sum of contributions == ΔWACC within ±1e-9
    sum_c = sum(c.values())
    assert abs(sum_c - result.delta_wacc) < 1e-9

    # 2. Signs per Packet §6:
    # rf, erp, beta, kd contributions > 0
    assert c["rf_used"] > 0, f"rf_used contribution should be > 0, got {c['rf_used']}"
    assert c["erp_total"] > 0, f"erp_total contribution should be > 0, got {c['erp_total']}"
    assert c["beta"] > 0, f"beta contribution should be > 0, got {c['beta']}"
    assert c["kd_after_tax"] > 0, f"kd_after_tax contribution should be > 0, got {c['kd_after_tax']}"

    # weights contribution < 0 (equity weight falls while Ke > Kd after tax)
    assert c["weights"] < 0, f"weights contribution should be < 0, got {c['weights']}"

    # 3. Exact values check
    assert abs(c["rf_used"] - 0.4450) < 1e-4
    assert abs(c["erp_total"] - 0.467167) < 1e-4
    assert abs(c["beta"] - 0.645167) < 1e-4
    assert abs(c["kd_after_tax"] - 0.0220) < 1e-4
    assert abs(c["weights"] - (-0.175333)) < 1e-4

    # 4. Ranking order check
    # |beta| (0.645) > |erp| (0.467) > |rf| (0.445) > |weights| (0.175) > |kd| (0.022)
    ranking = [fd.factor for fd in result.factor_details]
    assert ranking == ["beta", "erp_total", "rf_used", "weights", "kd_after_tax"]

    # 5. Top 2 factors in narrative
    assert len(result.top_factors) == 2
    assert result.top_factors[0].factor == "beta"
    assert result.top_factors[1].factor == "erp_total"
    assert "Beta" in result.narrative
    assert "Equity Risk Premium" in result.narrative
    assert "1.40" in result.narrative

    # 6. Waterfall bars check
    bars = result.waterfall_bars
    assert len(bars) == 7  # base + 5 factors + total
    assert bars[0]["factor"] == "WACC FY22"
    assert bars[0]["bar_type"] == "base"
    assert bars[0]["amount"] == 11.20
    assert bars[-1]["factor"] == "WACC FY23"
    assert bars[-1]["bar_type"] == "total"
    assert bars[-1]["amount"] == 12.604


def test_shapley_identical_inputs():
    """Identical inputs should yield zero delta and zero contributions."""
    params = WACCParameters(
        fiscal_year="FY24",
        rf_used=7.1,
        erp_total=7.3,
        beta=1.15,
        kd_after_tax=3.9,
        weight_equity=0.85,
    )
    result = compute_wacc_shapley(params, params)
    assert abs(result.delta_wacc) < 1e-12
    for val in result.contributions.values():
        assert abs(val) < 1e-12


def test_shapley_falling_rates():
    """Rates and ERP falling should produce negative contributions and exact closure."""
    params_a = WACCParameters(
        fiscal_year="FY23",
        rf_used=7.5,
        erp_total=8.0,
        beta=1.2,
        kd_after_tax=4.5,
        weight_equity=0.85,
    )
    params_b = WACCParameters(
        fiscal_year="FY24",
        rf_used=6.8,
        erp_total=7.2,
        beta=1.0,
        kd_after_tax=4.0,
        weight_equity=0.87,
    )
    result = compute_wacc_shapley(params_a, params_b)
    assert result.delta_wacc < 0
    assert abs(sum(result.contributions.values()) - result.delta_wacc) < 1e-9
    assert result.contributions["rf_used"] < 0
    assert result.contributions["erp_total"] < 0
    assert result.contributions["beta"] < 0
    assert result.contributions["kd_after_tax"] < 0
