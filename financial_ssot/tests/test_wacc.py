"""Unit tests for WACC calculation engine, fixtures, Blume adjustment, OLS, and Damodaran extraction.

SPEC-02 §3, §4, §10; Packet: docs/delegation/packets/v3/P1.9_wacc_inputs.md
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pytest

from financial_ssot.wacc import calculator, damodaran, inputs
from financial_ssot.wacc.build_wacc import build_wacc_dataset

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "wacc_fixture.json"


def test_wacc_fixture_from_json():
    """Verify SPEC-02 §10 base WACC fixture (Rf raw 7%, β 1.2, ERP 7%, Kd 6%, t 25.17%, E 900, D 100)."""
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    base = data["base_fixture"]
    rf = base["rf_used_pct"]
    beta = base["beta_raw"]
    erp = base["erp_pct"]
    kd_pretax = base["kd_pretax_pct"]
    tax_rate = base["tax_rate_pct"]
    equity = base["equity_mv"]
    debt = base["debt_bv"]

    ke = calculator.compute_ke(rf, beta, erp)
    assert ke == pytest.approx(base["expected_ke_pct"], abs=1e-4)

    kd_after_tax = calculator.compute_kd_after_tax(kd_pretax, tax_rate)
    assert kd_after_tax == pytest.approx(base["expected_kd_after_tax_pct"], abs=1e-4)

    wacc, w_e, w_d = calculator.compute_wacc(equity, debt, ke, kd_after_tax)
    assert wacc == pytest.approx(base["expected_wacc_pct"], abs=1e-4)
    assert w_e + w_d == pytest.approx(1.0, abs=1e-6)


def test_wacc_sensitivity_fixture_from_json():
    """Verify SPEC-02 §10 sensitivity fixture (default spread 2%, Rf = 5%)."""
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    sens = data["sensitivity_fixture"]
    rf = sens["rf_used_pct"]  # 7 - 2 = 5%
    beta = sens["beta_raw"]
    erp = sens["erp_pct"]
    kd_pretax = sens["kd_pretax_pct"]
    tax_rate = sens["tax_rate_pct"]
    equity = sens["equity_mv"]
    debt = sens["debt_bv"]

    ke = calculator.compute_ke(rf, beta, erp)
    assert ke == pytest.approx(sens["expected_ke_pct"], abs=1e-4)

    kd_after_tax = calculator.compute_kd_after_tax(kd_pretax, tax_rate)
    wacc_alt, _, _ = calculator.compute_wacc(equity, debt, ke, kd_after_tax)
    assert wacc_alt == pytest.approx(sens["expected_wacc_alt_gsec_less_spread_pct"], abs=1e-4)


def test_blume_adjustment():
    """Blume adjustment: 0.67 * 1.2 + 0.33 = 1.134."""
    assert calculator.blume_adjustment(1.2) == pytest.approx(1.134, abs=1e-4)
    assert calculator.blume_adjustment(1.0) == pytest.approx(1.0, abs=1e-4)


def test_synthetic_ols_beta():
    """OLS beta on synthetic series: r_s = 1.5 * r_m + noise(seed=7, σ=0.001) -> 1.50 ± 0.02."""
    rng = np.random.default_rng(7)
    r_m = rng.normal(0.001, 0.02, size=104)
    noise = rng.normal(0.0, 0.001, size=104)
    r_s = 1.5 * r_m + noise

    beta, r2 = calculator.compute_ols_beta(r_s, r_m)
    assert beta == pytest.approx(1.50, abs=0.02)
    assert r2 > 0.95


def test_fy26_kd_check():
    """FY26 Kd check from SPEC-02 §4 values ≈ 4.13%."""
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    ref = data["fy26_kd_reference"]

    fin_cost = ref["finance_costs_fy26_mn"]
    decom_unwind = ref["decom_unwind_fy26_mn"]
    prior_debt = ref["borrowings_fy25_mn"] + ref["lease_liab_fy25_mn"]
    curr_debt = ref["borrowings_fy26_mn"] + ref["lease_liab_fy26_mn"]
    avg_debt = (prior_debt + curr_debt) / 2.0

    kd = ((fin_cost - decom_unwind) / avg_debt) * 100.0
    assert kd == pytest.approx(ref["expected_kd_pretax_pct"], abs=0.01)
    assert round(kd, 2) == 4.13


def test_hamada_relevering():
    """Hamada re-levering test."""
    beta_u = 1.0
    debt = 100.0
    equity = 200.0
    t = 25.17
    # 1.0 * (1 + (1 - 0.2517) * 0.5) = 1.0 * (1 + 0.37415) = 1.37415
    beta_l = calculator.hamada_relever(beta_u, debt, equity, t)
    assert beta_l == pytest.approx(1.3742, abs=1e-4)


def test_damodaran_extraction():
    """Test extraction from Damodaran files for all 10 FYs."""
    erp_data = damodaran.extract_india_erp()
    beta_data = damodaran.extract_industry_beta()

    assert len(erp_data) == 10
    assert len(beta_data) == 10

    for fy in [f"FY{y}" for y in range(17, 27)]:
        assert fy in erp_data
        assert fy in beta_data
        e = erp_data[fy]
        b = beta_data[fy]

        assert 4.0 <= e["erp_total_pct"] <= 12.0
        assert 1.0 <= e["default_spread_pct"] <= 4.0
        assert 0.5 <= b["unlevered_beta"] <= 2.0

    # FY25 must have vintage gap note
    assert erp_data["FY25"]["notes"] == "erp_vintage_gap"


def test_build_wacc_dataset_structure():
    """Test full dataset generation and gates W1-W4 structure."""
    df_annual, df_input, report_md = build_wacc_dataset()

    assert len(df_annual) == 10
    assert "fiscal_year" in df_annual.columns
    assert "beta_industry_relevered" in df_annual.columns
    assert "kd_pretax_pct" in df_annual.columns
    assert "verified" in df_annual.columns

    # Since Rf seed is absent, verified must be False and W1 present in failed_rule_ids
    for _, r in df_annual.iterrows():
        assert r["verified"] is False
        assert "W1" in r["failed_rule_ids"]
        assert r["beta_industry_relevered"] is not None
        assert r["kd_pretax_pct"] is not None

    # Lineage inputs: at least 9 lineage rows per FY = 90 rows
    assert len(df_input) >= 90
    assert "# WACC Input Pack and fact_wacc_annual Build Report" in report_md
