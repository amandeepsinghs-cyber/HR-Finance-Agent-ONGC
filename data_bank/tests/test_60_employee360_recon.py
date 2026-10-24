import pytest
import pandas as pd
from pathlib import Path

DATA_BANK_ROOT = Path(__file__).resolve().parent.parent
LANDING_SAP = DATA_BANK_ROOT / "landing" / "sap"
TARGETS_CSV = DATA_BANK_ROOT / "world_bible" / "reference" / "real_targets" / "employee_targets_fy.csv"
COST_POOL_CSV = LANDING_SAP.parent / "employee_cost_pool.csv"

def test_emp_r01_to_r09_reconciliation():
    payroll_df = pd.read_csv(LANDING_SAP / "PY_CLUSTER_EXP.csv")
    pools_df = pd.read_csv(COST_POOL_CSV)
    targets_df = pd.read_csv(TARGETS_CSV)
    
    fy_sums = payroll_df.groupby("fiscal_year")[
        ["cost_note35_a_inr", "cost_note35_b_inr", "cost_note35_c_inr", "cost_note35_d_inr", "cost_note35_e_inr", "cost_note35_f_inr"]
    ].sum().reset_index()
    
    pools_df = pools_df[pools_df["basis"] == "residual"]
    pool_sums = pools_df.groupby(["fiscal_year", "note35_line"])["amount_inr"].sum().reset_index()
    
    for fy in ["FY17", "FY18", "FY19", "FY21", "FY22", "FY23", "FY24", "FY25", "FY26"]:
        target_total_series = targets_df[(targets_df["fiscal_year"] == fy) & (targets_df["metric"] == "employee_cost_total")]
        if not target_total_series.empty:
            target_total = target_total_series["value"].values[0] * 1e6
            row_sum = fy_sums[fy_sums["fiscal_year"] == fy].iloc[0]
            total_modelled = sum(row_sum[f"cost_note35_{c}_inr"] for c in "abcdef")
            total_pool = pools_df[pools_df["fiscal_year"] == fy]["amount_inr"].sum()
            final_total = total_modelled + total_pool
            
            print(f"EMP-R01 {fy} Total: Modelled={total_modelled/1e7:,.2f} Cr, Pool={total_pool/1e7:,.2f} Cr, Target={target_total/1e7:,.2f} Cr")
            assert abs(final_total - target_total) < 1e5, f"EMP-R01 failed for {fy}"
            
        for c in "abcdef":
            target_line_series = targets_df[(targets_df["fiscal_year"] == fy) & (targets_df["metric"] == f"note35_1_{c}")]
            if target_line_series.empty: continue
            target_line = target_line_series["value"].values[0] * 1e6
            modelled_line = row_sum[f"cost_note35_{c}_inr"]
            pool_line_series = pool_sums[(pool_sums["fiscal_year"] == fy) & (pool_sums["note35_line"] == c)]
            pool_line = pool_line_series["amount_inr"].values[0] if not pool_line_series.empty else 0.0
            
            final_line = modelled_line + pool_line
            assert abs(final_line - target_line) < 1e5, f"EMP-R02-R07 failed for {fy} line {c}"
            
            residual_pct = abs(pool_line) / target_line if target_line > 0 else 0
            if residual_pct > 0.0305:
                print(f"  Note35.1.{c} {fy}: Warning, high residual {residual_pct:.2%}")
            if c == 'a':
                diff_pct = abs(target_line - modelled_line) / target_line
                assert diff_pct <= 0.0405, f"EMP-R09 failed for {fy} line a"
                print(f"  Note35.1.a {fy}: Modelled={modelled_line/1e7:,.2f} Cr, Target={target_line/1e7:,.2f} Cr, Diff={diff_pct*100:.2f}%")

def test_emp_r10_headcount():
    hc_df = pd.read_csv(LANDING_SAP / "headcount_monthly_snapshot.csv")
    targets_df = pd.read_csv(TARGETS_CSV)
    
    for fy in ["FY17", "FY18", "FY19", "FY21", "FY22", "FY23", "FY24", "FY25", "FY26"]:
        target_series = targets_df[(targets_df["fiscal_year"] == fy) & (targets_df["metric"] == "headcount_fy_end")]["value"]
        if target_series.empty: continue
        target_hc = target_series.values[0]
        
        year_str = "20" + fy[2:4]
        month_str = f"{year_str}-03"
        modeled_hc = hc_df[hc_df["month"].str.startswith(month_str)]["active_headcount"].sum()
        assert modeled_hc == target_hc, f"EMP-R10 failed for {fy}: {modeled_hc} != {target_hc}"
