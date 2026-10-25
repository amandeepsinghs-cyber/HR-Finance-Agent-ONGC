"""Unit tests for WACC calculation engine, fixtures, Blume adjustment, OLS, and Damodaran extraction.

SPEC-02 §3, §4, §10; Packet: docs/delegation/packets/v3/P1.9_wacc_inputs.md
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
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
    """Test full dataset generation and gates W1-W4 structure with populated RBI & NSE seeds."""
    df_annual, df_input, report_md = build_wacc_dataset()

    assert len(df_annual) == 10
    assert "fiscal_year" in df_annual.columns
    assert "beta_industry_relevered" in df_annual.columns
    assert "kd_pretax_pct" in df_annual.columns
    assert "verified" in df_annual.columns

    for _, r in df_annual.iterrows():
        fy = r["fiscal_year"]
        assert r["beta_industry_relevered"] is not None
        assert not pd.isna(r["rf_gsec_10y_pct"])
        assert not pd.isna(r["ke_pct"])
        assert not pd.isna(r["equity_mv_inr_cr"])
        if fy == "FY20":
            # P19-B1: FY20 missing N36.UNWIND_DECOM must have None / NaN kd_pretax and W1, W4 failed
            assert r["verified"] is False
            assert pd.isna(r["kd_pretax_pct"])
            assert pd.isna(r["wacc_pct"])
            assert r["kd_flag"] == "out_of_band"
            assert "W1" in r["failed_rule_ids"]
            assert "W4" in r["failed_rule_ids"]
            assert "N36.UNWIND_DECOM unavailable for FY20" in r["notes"]
        elif fy == "FY24":
            # FY24 passes all W1-W4 gates (Kd 7.2861% within [Rf - 1pp, Rf + 3pp])
            assert r["verified"] is True
            assert r["failed_rule_ids"] == []
            assert not pd.isna(r["wacc_pct"])
            assert r["weight_equity"] + r["weight_debt"] == pytest.approx(1.0, abs=1e-6)
        else:
            # Other FYs have complete WACC but Kd outside [Rf - 1pp, Rf + 3pp] -> W4 flagged, no W1 failure
            assert r["verified"] is False
            assert "W1" not in r["failed_rule_ids"]
            assert "W4" in r["failed_rule_ids"]
            assert not pd.isna(r["kd_pretax_pct"])
            assert not pd.isna(r["wacc_pct"])
            assert r["weight_equity"] + r["weight_debt"] == pytest.approx(1.0, abs=1e-6)

    # Lineage inputs: 17 lineage rows per FY (including shares_outstanding) = 170 rows
    assert len(df_input) == 170
    assert "# WACC Input Pack and fact_wacc_annual Build Report" in report_md


def test_build_wacc_missing_seeds_and_share_capital_flag(tmp_path):
    """Verify missing Rf/market seeds or missing BS.SHARE_CAPITAL sets NULL and flags W1 without constant fallback."""
    missing_rbi = tmp_path / "missing_rbi.csv"
    missing_mkt = tmp_path / "missing_mkt.csv"
    df_annual, _, _ = build_wacc_dataset(rbi_seed_csv=missing_rbi, market_seed_csv=missing_mkt)
    for _, r in df_annual.iterrows():
        assert r["verified"] is False
        assert "W1" in r["failed_rule_ids"]
        assert pd.isna(r["wacc_pct"])

    # Verify SSOT shares_outstanding differs between pre-buyback (FY17-FY18) and post-buyback (FY21-FY26)
    bundles = inputs.build_all_inputs()
    assert bundles["FY17"].shares_outstanding == pytest.approx(12_833_264_000.0, rel=1e-6)
    assert bundles["FY18"].shares_outstanding == pytest.approx(12_833_264_000.0, rel=1e-6)
    assert bundles["FY26"].shares_outstanding == pytest.approx(12_580_278_000.0, rel=1e-6)


def test_p19_b1_b2_b3_reviews():
    """Verify specific fixes for reviewer comments P19-B1, P19-B2, and P19-B3."""
    df_annual, df_input, _ = build_wacc_dataset()
    annual_by_fy = {r["fiscal_year"]: r for _, r in df_annual.iterrows()}

    # P19-B1: FY17 and FY18 out-of-band sanity check
    assert annual_by_fy["FY17"]["kd_flag"] == "out_of_band"
    assert "W4" in annual_by_fy["FY17"]["failed_rule_ids"]
    assert annual_by_fy["FY18"]["kd_flag"] == "out_of_band"
    assert "W4" in annual_by_fy["FY18"]["failed_rule_ids"]

    # P19-B2: FY17 preserved lease liabilities from balance sheet
    fy17_debt = annual_by_fy["FY17"]["debt_bv_inr_cr"]
    assert fy17_debt == pytest.approx(41.796, abs=1e-3)

    # P19-B3 + P5 shares_outstanding: All 17 input codes present per fiscal year
    expected_codes = {
        "rf_gsec_10y",
        "default_spread_india",
        "rf_used",
        "erp_mature",
        "crp_india",
        "erp_total_india",
        "unlevered_beta",
        "beta_industry_relevered",
        "kd_pretax",
        "kd_used",
        "ke",
        "tax_rate",
        "debt_bv",
        "equity_bv",
        "shares_outstanding",
        "equity_mv",
        "wacc",
    }
    for fy in [f"FY{y}" for y in range(17, 27)]:
        fy_codes = set(df_input[df_input["fiscal_year"] == fy]["input_code"])
        assert expected_codes.issubset(fy_codes)

        # Check beta_industry_relevered source_doc cites beta workbook
        beta_rel_row = df_input[
            (df_input["fiscal_year"] == fy) & (df_input["input_code"] == "beta_industry_relevered")
        ].iloc[0]
        assert "betaemerg" in beta_rel_row["source_doc"]
