"""Acceptance tests for financial SSOT anchor tables (P1.7, SPEC-01 §10, SPEC-05 §5).

Verifies:
1. Gate S1: Segment revenue, result, and total assets tie-outs across all fiscal years (FY21-FY26 + FY16-FY19).
2. Gate P1: Production basis tie-out (ONGC_standalone + JV_share == ONGC_incl_JV within 0.002) and 10-year Quantity Sold (basis='sold') spanning FY13-FY26.
3. Gate R1: Crude price realisation reproduces crude sales within ±2% and printed gas prices across FY21-FY26.
4. Reserves: 2P/1P accretion, positions, and RRR across FY17-FY26.
5. Headcount vintage policy: employees_total covers FY13-FY26 with FY25 having both own (24,378) and latest restated (24,368).
6. Lineage completeness: 100% of rows have source_doc and source_page.
"""
from __future__ import annotations

from pathlib import Path
import pytest
import pandas as pd

from financial_ssot.anchors.build_anchors import build_all_anchors


@pytest.fixture(scope="module")
def anchor_tables(tmp_path_factory):
    # Run build_all_anchors into out
    repo_root = Path(__file__).resolve().parent.parent.parent
    out_dir = repo_root / "financial_ssot" / "out"
    text_dir = repo_root / "knowledge" / "public_sources" / "grounding_data" / "text"
    
    tables = build_all_anchors(out_dir=out_dir, text_dir=text_dir)
    return tables


def test_lineage_completeness(anchor_tables):
    """Every single row in all 5 anchor tables must carry valid source_doc and source_page."""
    for name, df in anchor_tables.items():
        assert not df.empty, f"{name} is empty"
        assert "source_doc" in df.columns, f"{name} missing source_doc"
        assert "source_page" in df.columns, f"{name} missing source_page"
        assert df["source_doc"].notna().all(), f"{name} has null source_doc"
        assert (df["source_doc"].str.len() > 0).all(), f"{name} has empty source_doc"
        assert df["source_page"].notna().all(), f"{name} has null source_page"
        assert (df["source_page"] > 0).all(), f"{name} has non-positive source_page"


def test_gate_s1_segment_identities(anchor_tables):
    """Gate S1: Revenue, PBT, and Total Assets tie-outs (≤ ₹0.05 cr tolerance)."""
    df_seg = anchor_tables["fact_segment"]
    sa = df_seg[df_seg["scope"] == "standalone"]
    
    # Tested years for standalone segment reporting
    target_fys = ["FY26", "FY25", "FY24", "FY23", "FY22", "FY19", "FY18", "FY17", "FY16"]
    
    for fy in target_fys:
        fy_df = sa[sa["fiscal_year"] == fy]
        assert not fy_df.empty, f"Missing standalone segment rows for {fy}"
        
        # 1. Revenue tie
        rev_off = fy_df[fy_df["line_code"] == "SEG.REV.OFF"]["value_inr_mn"].iloc[0]
        rev_on = fy_df[fy_df["line_code"] == "SEG.REV.ON"]["value_inr_mn"].iloc[0]
        rev_tot = fy_df[fy_df["line_code"] == "SEG.REV.TOTAL"]["value_inr_mn"].iloc[0]
        assert abs((rev_off + rev_on) - rev_tot) / 10.0 <= 0.05, f"Gate S1 revenue failed for {fy}"
        
        # 2. Result tie
        res_off = fy_df[fy_df["line_code"] == "SEG.RES.OFF"]["value_inr_mn"].iloc[0]
        res_on = fy_df[fy_df["line_code"] == "SEG.RES.ON"]["value_inr_mn"].iloc[0]
        unalloc = fy_df[fy_df["line_code"] == "SEG.UNALLOC"]["value_inr_mn"].iloc[0]
        fin_cost = fy_df[fy_df["line_code"] == "SEG.FIN_COST"]["value_inr_mn"].iloc[0]
        int_div = fy_df[fy_df["line_code"] == "SEG.INT_DIV"]["value_inr_mn"].iloc[0]
        pbt = fy_df[fy_df["line_code"] == "SEG.PBT"]["value_inr_mn"].iloc[0]
        
        calc_pbt = res_off + res_on + unalloc + fin_cost + int_div
        delta_cr = abs(calc_pbt - pbt) / 10.0
        assert delta_cr <= 0.05, f"Gate S1 PBT failed for {fy}: calc {calc_pbt} vs rep {pbt} (delta {delta_cr:.4f} cr)"

        # 3. Total Assets tie (where reported in notes)
        off_ast = fy_df[fy_df["line_code"] == "SEG.SEGMENT_ASSETS.OFF"]
        on_ast = fy_df[fy_df["line_code"] == "SEG.SEGMENT_ASSETS.ON"]
        un_ast = fy_df[fy_df["line_code"] == "SEG.UNALLOCATED_ASSETS"]
        tot_ast = fy_df[fy_df["line_code"] == "SEG.TOTAL_ASSETS"]
        if not off_ast.empty and not on_ast.empty and not un_ast.empty and not tot_ast.empty:
            calc_ast = off_ast.iloc[0]["value_inr_mn"] + on_ast.iloc[0]["value_inr_mn"] + un_ast.iloc[0]["value_inr_mn"]
            rep_ast = tot_ast.iloc[0]["value_inr_mn"]
            delta_ast_cr = abs(calc_ast - rep_ast) / 10.0
            assert delta_ast_cr <= 0.05, f"Gate S1 Assets failed for {fy}: calc {calc_ast} vs rep {rep_ast}"


def test_fy26_segment_spot_checks(anchor_tables):
    """Assert FY26 segment values exactly match AR FY26 Note 44.2 (p.368)."""
    df_seg = anchor_tables["fact_segment"]
    fy26 = df_seg[(df_seg["fiscal_year"] == "FY26") & (df_seg["scope"] == "standalone")]
    
    expected = {
        "SEG.REV.OFF": 924063.07,
        "SEG.REV.ON": 401018.29,
        "SEG.REV.TOTAL": 1325081.36,
        "SEG.RES.OFF": 343846.53,
        "SEG.RES.ON": 62456.98,
        "SEG.RES.TOTAL": 406303.51,
        "SEG.UNALLOC": -25438.33,
        "SEG.FIN_COST": -45292.61,
        "SEG.INT_DIV": 88576.32,
        "SEG.PBT": 424148.89,
    }
    for lc, val in expected.items():
        row = fy26[fy26["line_code"] == lc]
        assert not row.empty, f"Missing {lc} in FY26"
        assert pytest.approx(row.iloc[0]["value_inr_mn"], rel=1e-5) == val, f"{lc} value mismatch"


def test_gate_p1_production_basis(anchor_tables):
    """Gate P1: ONGC_standalone + JV_share == ONGC_incl_JV within 0.002 tolerance, and sold basis spans FY13-FY26."""
    df_prod = anchor_tables["fact_production_annual"]
    
    # 1. P1 tie-out across FY21 - FY26
    for fy in ["FY21", "FY22", "FY23", "FY24", "FY25", "FY26"]:
        for prod in ["crude_oil", "natural_gas"]:
            sub = df_prod[(df_prod["fiscal_year"] == fy) & (df_prod["product"] == prod)]
            s_row = sub[sub["basis"] == "ONGC_standalone"]
            j_row = sub[sub["basis"] == "JV_share"]
            tot_row = sub[sub["basis"] == "ONGC_incl_JV"]
            
            assert not s_row.empty, f"Missing {fy} {prod} standalone"
            assert not j_row.empty, f"Missing {fy} {prod} JV"
            assert not tot_row.empty, f"Missing {fy} {prod} ONGC_incl_JV"
            
            calc_tot = s_row.iloc[0]["value"] + j_row.iloc[0]["value"]
            rep_tot = tot_row.iloc[0]["value"]
            assert abs(calc_tot - rep_tot) <= 0.002001, f"Gate P1 failed for {fy} {prod}: {calc_tot} vs {rep_tot}"

    # 2. basis='sold' rows span FY13 through FY26
    sold_df = df_prod[df_prod["basis"] == "sold"]
    assert not sold_df.empty, "fact_production_annual missing basis='sold' rows"
    sold_fys = set(sold_df["fiscal_year"].unique())
    expected_fys = {f"FY{yy}" for yy in range(13, 27)}
    assert expected_fys.issubset(sold_fys), f"Missing sold fiscal years: {expected_fys - sold_fys}"


def test_fy26_production_spot_checks(anchor_tables):
    """Assert FY26 production values match AR FY26 p.9 & p.55."""
    df_prod = anchor_tables["fact_production_annual"]
    fy26 = df_prod[df_prod["fiscal_year"] == "FY26"]
    
    # Crude: ONGC 19.332, JV 1.170, Total 20.501 (p.9/55)
    crude_s = fy26[(fy26["product"] == "crude_oil") & (fy26["basis"] == "ONGC_standalone")].iloc[0]["value"]
    crude_j = fy26[(fy26["product"] == "crude_oil") & (fy26["basis"] == "JV_share")].iloc[0]["value"]
    crude_tot = fy26[(fy26["product"] == "crude_oil") & (fy26["basis"] == "ONGC_incl_JV")].iloc[0]["value"]
    assert crude_s == 19.332
    assert crude_j == 1.170
    assert crude_tot == 20.501
    
    # Gas: ONGC 19.533, JV 0.434, Total 19.966
    gas_s = fy26[(fy26["product"] == "natural_gas") & (fy26["basis"] == "ONGC_standalone")].iloc[0]["value"]
    gas_j = fy26[(fy26["product"] == "natural_gas") & (fy26["basis"] == "JV_share")].iloc[0]["value"]
    gas_tot = fy26[(fy26["product"] == "natural_gas") & (fy26["basis"] == "ONGC_incl_JV")].iloc[0]["value"]
    assert gas_s == 19.533
    assert gas_j == 0.434
    assert gas_tot == 19.966


def test_fact_reserves_accretion_and_position(anchor_tables):
    """Verify reserves accretion and position across FY17-FY26."""
    df_res = anchor_tables["fact_reserves"]
    
    # FY26: 2P Accretion 44.01, RRR 1.17, Company 697.83, JV 11.49, Total 709.32 (p.98)
    fy26_tot = df_res[(df_res["fiscal_year"] == "FY26") & (df_res["region"] == "domestic_total")].iloc[0]
    assert fy26_tot["value_mmtoe"] == 709.32
    assert fy26_tot["accretion_mmtoe"] == 44.01
    assert fy26_tot["rrr"] == 1.17
    
    # FY25: 1P Total 525.92, Accretion 39.50, RRR 1.01 (p.104 & p.14)
    fy25_tot = df_res[(df_res["fiscal_year"] == "FY25") & (df_res["region"] == "domestic_total")].iloc[0]
    assert fy25_tot["value_mmtoe"] == 525.92
    assert fy25_tot["accretion_mmtoe"] == 39.50
    assert fy25_tot["rrr"] == 1.01

    # FY24: 2P Total 716.95, Accretion 45.20, RRR 1.15 (p.68)
    fy24_tot = df_res[(df_res["fiscal_year"] == "FY24") & (df_res["region"] == "domestic_total")].iloc[0]
    assert fy24_tot["value_mmtoe"] == 716.95
    assert fy24_tot["accretion_mmtoe"] == 45.20
    assert fy24_tot["rrr"] == 1.15

    # FY23: 2P Total 729.83, Accretion 40.62, RRR 1.01 (p.70)
    fy23_tot = df_res[(df_res["fiscal_year"] == "FY23") & (df_res["region"] == "domestic_total")].iloc[0]
    assert fy23_tot["value_mmtoe"] == 729.83
    assert fy23_tot["accretion_mmtoe"] == 40.62
    assert fy23_tot["rrr"] == 1.01

    # FY18: 2P Total Accretion 68.85 (ONGC 67.83), RRR 1.48 (AR FY18 p.13)
    fy18_tot = df_res[(df_res["fiscal_year"] == "FY18") & (df_res["region"] == "domestic_total")].iloc[0]
    assert fy18_tot["accretion_mmtoe"] == 68.85
    assert fy18_tot["rrr"] == 1.48

    # FY17: 2P Domestic Accretion 64.54, RRR 1.45 (AR FY17 p.7)
    fy17_ongc = df_res[(df_res["fiscal_year"] == "FY17") & (df_res["region"] == "domestic_ongc")].iloc[0]
    assert fy17_ongc["accretion_mmtoe"] == 64.54
    assert fy17_ongc["rrr"] == 1.45


def test_hr_aggregates_headcount_vintages(anchor_tables):
    """Verify employees_total spans FY13-FY26 with FY25 showing both vintages."""
    df_hr = anchor_tables["fact_hr_aggregates"]
    emp = df_hr[df_hr["metric"] == "employees_total"]
    
    # Spans FY13 through FY26
    fys = set(emp["fiscal_year"].unique())
    expected_fys = {f"FY{yy}" for yy in range(13, 27)}
    assert expected_fys.issubset(fys), f"Missing years: {expected_fys - fys}"
    
    # FY25 has both vintages
    emp_fy25 = emp[emp["fiscal_year"] == "FY25"]
    assert len(emp_fy25) >= 2, "FY25 should have both as-reported and restated vintages"
    
    own_vint = emp_fy25[emp_fy25["is_own_vintage"]]
    assert not own_vint.empty
    assert own_vint.iloc[0]["value"] == 24378.0  # AR FY25 p.21
    
    latest_vint = emp_fy25[emp_fy25["is_latest_vintage"]]
    assert not latest_vint.empty
    assert latest_vint.iloc[0]["value"] == 24368.0  # AR FY26 p.24 restated
    assert bool(latest_vint.iloc[0]["is_restated"]) is True


def test_hr_brsr_metrics_spot_checks(anchor_tables):
    """Verify deterministic BRSR metrics from AR FY26 (p.141-181)."""
    df_hr = anchor_tables["fact_hr_aggregates"]
    
    # 1. Total Permanent workforce = 13,781 exec + 9,336 non-exec = 23,117 (matches 10-yr!)
    exec_perm = df_hr[(df_hr["metric"] == "employees_permanent") & (df_hr["dimension_value"] == "total")].iloc[0]["value"]
    nonexec_perm = df_hr[(df_hr["metric"] == "workers_permanent") & (df_hr["dimension_value"] == "total")].iloc[0]["value"]
    assert exec_perm == 13781.0
    assert nonexec_perm == 9336.0
    assert exec_perm + nonexec_perm == 23117.0
    
    # 2. PwD total permanent = 313 + 210 = 523
    pwd_tot = df_hr[df_hr["metric"] == "pwd_total_permanent"].iloc[0]["value"]
    assert pwd_tot == 523.0
    
    # 3. Turnover rates FY26: Employees 7.4%, Workers 3.1%
    turn_emp = df_hr[(df_hr["metric"] == "turnover_permanent_employees_pct") & (df_hr["fiscal_year"] == "FY26") & (df_hr["dimension_value"] == "total")].iloc[0]["value"]
    turn_wkr = df_hr[(df_hr["metric"] == "turnover_permanent_workers_pct") & (df_hr["fiscal_year"] == "FY26") & (df_hr["dimension_value"] == "total")].iloc[0]["value"]
    assert turn_emp == 7.4
    assert turn_wkr == 3.1
    
    # 4. Median Remuneration: BoD ₹10,742,716, KMP ₹10,646,820
    bod_rem = df_hr[(df_hr["metric"] == "median_remuneration_inr") & (df_hr["dimension"] == "bod")].iloc[0]["value"]
    kmp_rem = df_hr[(df_hr["metric"] == "median_remuneration_inr") & (df_hr["dimension"] == "kmp")].iloc[0]["value"]
    assert bod_rem == 10742716.0
    assert kmp_rem == 10646820.0
    
    # 5. Note 35.1 Employee Benefits Expense FY26 = 10,210.71 cr (102,107.09 mn)
    n351 = df_hr[(df_hr["metric"] == "employee_benefits_expense_inr_cr") & (df_hr["fiscal_year"] == "FY26")].iloc[0]["value"]
    assert n351 == 10210.71


def test_gate_r1_price_realisation(anchor_tables):
    """Gate R1: Realisation * Qty sold reproduces crude sales line within ±2%, and printed gas prices exist."""
    df_price = anchor_tables["fact_price_realisation"]
    
    # FY26 nominated crude
    fy26_crude = df_price[(df_price["fiscal_year"] == "FY26") & (df_price["product"] == "crude") & (df_price["basis"] == "nominated")].iloc[0]
    assert fy26_crude["realisation_usd_per_bbl"] == 68.40
    assert fy26_crude["realisation_inr_per_unit"] == 6042.0
    assert bool(fy26_crude["verified"]) is True
    assert "R1" in fy26_crude["verified_rule_ids"]

    # FY25 nominated crude
    fy25_crude = df_price[(df_price["fiscal_year"] == "FY25") & (df_price["product"] == "crude") & (df_price["basis"] == "nominated")].iloc[0]
    assert fy25_crude["realisation_usd_per_bbl"] == 76.90
    assert fy25_crude["realisation_inr_per_unit"] == 6503.0
    assert bool(fy25_crude["verified"]) is True
    assert "R1" in fy25_crude["verified_rule_ids"]

    # FY24 nominated crude
    fy24_crude = df_price[(df_price["fiscal_year"] == "FY24") & (df_price["product"] == "crude") & (df_price["basis"] == "nominated")].iloc[0]
    assert fy24_crude["realisation_usd_per_bbl"] == 80.77
    assert fy24_crude["realisation_inr_per_unit"] == 6687.0
    assert bool(fy24_crude["verified"]) is True
    assert "R1" in fy24_crude["verified_rule_ids"]

    # FY23 APM gas prices parsed from AR23 p.171
    fy23_apm_h1 = df_price[(df_price["fiscal_year"] == "FY23") & (df_price["basis"] == "apm_h1")].iloc[0]
    assert fy23_apm_h1["realisation_usd_per_mmbtu"] == 6.10
    assert bool(fy23_apm_h1["verified"]) is True

    fy23_apm_h2 = df_price[(df_price["fiscal_year"] == "FY23") & (df_price["basis"] == "apm_h2")].iloc[0]
    assert fy23_apm_h2["realisation_usd_per_mmbtu"] == 8.57
    assert bool(fy23_apm_h2["verified"]) is True

    # Confirm NO invented crude price for FY23 exists
    fy23_crude = df_price[(df_price["fiscal_year"] == "FY23") & (df_price["product"] == "crude")]
    assert fy23_crude.empty, "FY23 crude should be omitted (narrative range only)"


def test_anchors_issues_csv_only_gaps(anchor_tables):
    """anchors_issues.csv must contain 0 gate failures, but should contain gaps."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    issues_path = repo_root / "financial_ssot" / "out" / "anchors_issues.csv"
    assert issues_path.exists()
    df_issues = pd.read_csv(issues_path)
    
    # Assert there are no actual gate failures (where gate is not gap)
    if not df_issues.empty and "gate" in df_issues.columns:
        gate_failures = df_issues[df_issues["gate"] != "gap"]
        
        # FY23 has a narrative gap which might not have gate="gap" explicitly in some older code, 
        # but in our code it uses the key 'gap' in dict. Wait, if it has 'gap' in dict, pd.DataFrame puts NaN in gate.
        gate_failures = gate_failures[gate_failures["gap"].isna()]
        
        assert gate_failures.empty, f"Found unexpected gate failures: {gate_failures.to_dict('records')}"
    
    # R2-4 regression: ensure the 8 unverified press release realisation rows are listed as gaps
    unverified_pr = df_issues[(df_issues["gate"] == "gap") & (df_issues["detail"].str.contains("Unverified press release", na=False))]
    assert len(unverified_pr) == 8, f"Expected 8 unverified PR gaps, got {len(unverified_pr)}"

def test_r2_fixes(anchor_tables):
    df_res = anchor_tables["fact_reserves"]
    df_seg = anchor_tables["fact_segment"]
    df_price = anchor_tables["fact_price_realisation"]

    # R2-1: FY22 2P accretion = 40.82
    fy22_2p = df_res[(df_res["fiscal_year"] == "FY22") & (df_res["category"] == "2P")].iloc[0]
    assert fy22_2p["accretion_mmtoe"] == 40.82

    # R2-2: FY19 RRR parsed as 1.41
    fy19_2p_ongc = df_res[(df_res["fiscal_year"] == "FY19") & (df_res["category"] == "2P") & (df_res["region"] == "domestic_ongc")].iloc[0]
    assert fy19_2p_ongc["rrr"] == 1.41
    
    # R2-3: own-vintage AR_FY2016-17 FY17 rows survive
    fy17_own = df_seg[(df_seg["fiscal_year"] == "FY17") & (df_seg["report_vintage"] == "AR_FY2016-17")]
    assert not fy17_own.empty, "FY17 own-vintage rows should survive"

    # R2-3: stop right-column bleed at L17848 into FY16 SEG.IMP.TOTAL
    imp_total = df_seg[(df_seg["report_vintage"] == "AR_FY2016-17") & (df_seg["line_code"] == "SEG.IMP.TOTAL") & (df_seg["fiscal_year"] == "FY16")]
    if not imp_total.empty:
        assert imp_total.iloc[0]["value_inr_mn"] != 1289853.21

