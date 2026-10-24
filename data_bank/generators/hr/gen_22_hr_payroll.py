import pandas as pd
import numpy as np
import datetime
from typing import Dict, Any, List
from . import pay_rules
from pathlib import Path
import os
from .gen_22_hr_sat import get_month_end_date, get_fiscal_year, set_seed

DATA_BANK_ROOT = Path(__file__).resolve().parent.parent.parent
LANDING_SAP = DATA_BANK_ROOT / "landing" / "sap"
TARGETS_CSV = DATA_BANK_ROOT / "world_bible" / "reference" / "real_targets" / "employee_targets_fy.csv"

def generate_payroll_monthly(
    df_emp: pd.DataFrame, df_post: pd.DataFrame,
    work_centres: Dict[str, Any], grades: Dict[str, Any], disciplines: Dict[str, Any],
    cost_centres: List[Dict[str, Any]]
) -> pd.DataFrame:
    print("Generating H8: payroll_monthly using pay_rules (P2H.5)...")
    set_seed(2026)
    
    payroll_months = []
    for y in range(2016, 2027):
        for m in range(1, 13):
            if y == 2016 and m < 4: continue
            if y == 2026 and m > 9: continue
            payroll_months.append(f"{y:04d}-{m:02d}")
            
    # Lookup dictionaries
    wc_cost_centre = {}
    for cc in cost_centres:
        w_id = cc.get("wc_id")
        if w_id and w_id not in wc_cost_centre:
            wc_cost_centre[w_id] = cc.get("cost_centre_id")
    default_cc = cost_centres[0].get("cost_centre_id") if cost_centres else "CC-10001"

    emp_df = df_emp[["PERNR", "BEGDA", "separation_date", "GESCH", "has_offshore_tenure", "has_hard_station_tenure"]].copy()
    emp_df["doj_dt"] = pd.to_datetime(emp_df["BEGDA"])
    emp_df["sep_dt"] = pd.to_datetime(emp_df["separation_date"])

    post_df = df_post[["PERNR", "WERKS", "PERSK", "discipline_id", "BEGDA", "ENDDA"]].copy()
    post_df["post_start_dt"] = pd.to_datetime(post_df["BEGDA"])
    post_df["post_end_dt"] = pd.to_datetime(post_df["ENDDA"])

    # Load targets
    df_targets = pd.read_csv(TARGETS_CSV)
    note35a_targets = dict(zip(
        df_targets[df_targets["metric"] == "note35_1_a"]["fiscal_year"],
        df_targets[df_targets["metric"] == "note35_1_a"]["value"]
    ))

    # Pre-load reference bundle to avoid repeating I/O
    pay_rules.load_pay_reference_bundle()

    # Pre-compute employee state changes? Let's just use multiprocessing for month loop if needed.
    # Actually, 3.55M rows is ~10-20 seconds in a good Pandas vectorization, but we must use a loop per spec.
    # Using a list comprehension or fast loop is fine.
import multiprocessing
from functools import partial

# We'll use a global function for multiprocessing
def process_month(month_str, emp_df, post_df, grades, disciplines, work_centres, wc_cost_centre, default_cc):
    snap_date_str = get_month_end_date(month_str)
    snap_dt = pd.to_datetime(snap_date_str)
    fy = get_fiscal_year(snap_date_str)

    active_emp_mask = (emp_df["doj_dt"] <= snap_dt) & (emp_df["sep_dt"].isna() | (emp_df["sep_dt"] > snap_dt))
    active_emps = emp_df[active_emp_mask]

    active_post_mask = (post_df["post_start_dt"] <= snap_dt) & (post_df["post_end_dt"].isna() | (post_df["post_end_dt"] >= snap_dt))
    active_posts = post_df[active_post_mask]

    m = active_posts.merge(active_emps, on="PERNR", how="inner")
    m = m.sort_values("post_start_dt", ascending=False).drop_duplicates(subset=["PERNR"])

    records = []
    
    # Fast iteration
    for row in m.itertuples(index=False):
        grade_id = row.PERSK
        wc_id = row.WERKS
        doj_dt = row.doj_dt
        
        tenure_years = (snap_dt - doj_dt).days / 365.25
        increments_count = int(tenure_years)
        # simplistic stagnation estimation
        stag = max(0, increments_count - max(0, int((grades.get(grade_id, {}).get("pay_scale_max_inr", 0) - grades.get(grade_id, {}).get("pay_scale_min_inr", 0)) / (grades.get(grade_id, {}).get("pay_scale_min_inr", 1) * 0.03))))
        
        wc = work_centres.get(wc_id, {})
        city_class = wc.get("hra_city_class", "Z")
        is_offshore = (wc.get("onshore_offshore") == "offshore")
        is_hard = (wc.get("hard_station_cat") in ["A", "B", "C"])
        wc_type = wc.get("type", "office")
        
        ot_base = 54.0 if is_offshore else (36.0 if wc_type in ["asset", "plant"] else 3.0)
        if grades.get(grade_id, {}).get("cadre") == "executive":
            ot_base = 0.0
            
        components = pay_rules.compute_monthly_pay_components(
            grade_id=grade_id,
            month_str=snap_date_str,
            city_class=city_class,
            accommodation_type="HRA",
            increments_count=increments_count,
            stagnation_increments=min(3, stag),
            u_fy=1.0,
            k_fy=1.0,
            apar_factor=1.0,
            offshore_days=15.0 if is_offshore else 0.0,
            hard_station_flag=is_hard,
            overtime_hours=ot_base,
        )
        
        cc_id = wc_cost_centre.get(wc_id, default_cc)
        
        records.append({
            "PERNR": row.PERNR,
            "FPPER": month_str,
            "fiscal_year": fy,
            "wc_id": wc_id,
            "grade_id": grade_id,
            "discipline_id": row.discipline_id,
            "cost_centre_id": cc_id,
            "LGART_1001": components["basic_pay_inr"],
            "LGART_1002": components["ida_inr"],
            "cafeteria_allowance_inr_base": components["cafeteria_allowance_inr"],
            "hra_inr": components["hra_inr"],
            "mining_offshore_allowance_inr": components.get("hardship_offshore_inr", 0.0) + components.get("hard_station_allowance_inr", 0.0),
            "overtime_hours": components["overtime_hours"],
            "overtime_amount_inr_base": components["overtime_amount_inr"],
            "prp_inr_base": components["prp_paid_inr"],
            "employer_cpf_inr": components["employer_cpf_inr"],
            "employer_prbs_inr": components["employer_prbs_inr"],
            "employer_prmb_inr": components["employer_prmb_inr"],
            "gratuity_accrual_inr": components.get("gratuity_accrual_inr", 0.0),
            "leave_provision_accrual_inr": components.get("leave_provision_accrual_inr", 0.0),
            "employer_cost_noncash_inr": components.get("employer_cost_noncash_inr", 0.0),
            "medical_scheme_cost_inr": components.get("medical_scheme_cost_inr", 0.0),
            "group_insurance_premium_inr": components.get("group_insurance_premium_inr", 0.0),
            "accident_insurance_premium_inr": components.get("accident_insurance_premium_inr", 0.0),
            "housing_cost_inr": components.get("housing_cost_inr", 0.0),
            "canteen_subsidy_inr": components.get("canteen_subsidy_inr", 0.0),
            "transport_subsidy_inr": components.get("transport_subsidy_inr", 0.0),
            "staff_welfare_alloc_inr": components.get("staff_welfare_alloc_inr", 0.0),
            "training_cost_inr": components.get("training_cost_inr", 0.0),
            "csss_contribution_inr": components.get("csss_contribution_inr", 0.0),
            "income_tax_tds_inr": components["tds_inr"],
            "superannuation_benefit_pct": components.get("superannuation_pct_bp_da", 0.0),
            "cost_expensed_production_inr": components.get("cost_expensed_production_inr", 0.0)
        })
    return records
def generate_payroll_monthly_continue(df_emp, df_post, work_centres, grades, disciplines, cost_centres, wc_cost_centre, default_cc, payroll_months, note35a_targets):
    emp_df = df_emp[["PERNR", "BEGDA", "separation_date", "GESCH", "has_offshore_tenure", "has_hard_station_tenure"]].copy()
    emp_df["doj_dt"] = pd.to_datetime(emp_df["BEGDA"])
    emp_df["sep_dt"] = pd.to_datetime(emp_df["separation_date"])

    post_df = df_post[["PERNR", "WERKS", "PERSK", "discipline_id", "BEGDA", "ENDDA"]].copy()
    post_df["post_start_dt"] = pd.to_datetime(post_df["BEGDA"])
    post_df["post_end_dt"] = pd.to_datetime(post_df["ENDDA"])

    print("Running parallel month computation...")
    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
    func = partial(process_month, emp_df=emp_df, post_df=post_df, grades=grades, disciplines=disciplines, work_centres=work_centres, wc_cost_centre=wc_cost_centre, default_cc=default_cc)
    
    all_records = []
    for month_records in pool.map(func, payroll_months):
        all_records.extend(month_records)
    
    pool.close()
    pool.join()
    print(f"Parallel computation finished. Total rows: {len(all_records)}")
    
    df_payroll = pd.DataFrame(all_records)
    
    # Now fit the knobs for each FY to minimize gap with note35_1_a
    # note35_a = basic + ida + cafeteria + hra + mining + overtime + prp_paid + arrears + leave_encashment_paid + ex_gratia_other
    # Let's say basic + ida + hra + mining is fixed base.
    
    df_payroll["fixed_note35a"] = df_payroll["LGART_1001"] + df_payroll["LGART_1002"] + df_payroll["hra_inr"] + df_payroll["mining_offshore_allowance_inr"]
    df_payroll["adjustable_note35a_base"] = df_payroll["cafeteria_allowance_inr_base"] + df_payroll["overtime_amount_inr_base"] + df_payroll["prp_inr_base"]
    
    # We will compute a single scalar 'alpha' for each FY to apply to adjustable components so that note35_1_a matches EXACTLY!
    
    fy_groups = df_payroll.groupby("fiscal_year")[["fixed_note35a", "adjustable_note35a_base"]].sum().reset_index()
    
    alpha_dict = {}
    payroll_policies = []
    
    for _, row in fy_groups.iterrows():
        fy = row["fiscal_year"]
        target = note35a_targets.get(fy)
        if not target:
            # Fallback if no target (e.g. FY16, FY27)
            alpha = 1.0
        else:
            target_inr = target * 1e6 # INR mn to INR
            if row["adjustable_note35a_base"] > 0:
                alpha = (target_inr - row["fixed_note35a"]) / row["adjustable_note35a_base"]
            else:
                alpha = 1.0
                
        alpha_dict[fy] = alpha
        payroll_policies.append({
            "fiscal_year": fy,
            "k_fy": alpha,
            "u_fy": alpha,
            "ot_fy": alpha
        })
        
    df_policies = pd.DataFrame(payroll_policies)
    df_policies.to_csv(TARGETS_CSV.parent / "payroll_policy_fy.csv", index=False)
    print(f"Wrote payroll_policy_fy.csv")
    
    # Apply alpha
    df_payroll["alpha"] = df_payroll["fiscal_year"].map(alpha_dict)
    
    df_payroll["cafeteria_allowances_inr"] = df_payroll["cafeteria_allowance_inr_base"] * df_payroll["alpha"]
    df_payroll["overtime_amount_inr"] = df_payroll["overtime_amount_inr_base"] * df_payroll["alpha"]
    df_payroll["prp_inr"] = df_payroll["prp_inr_base"] * df_payroll["alpha"]
    
    df_payroll["LGART_9001"] = df_payroll["fixed_note35a"] + df_payroll["cafeteria_allowances_inr"] + df_payroll["overtime_amount_inr"] + df_payroll["prp_inr"]
    
    # Net salary
    df_payroll["LGART_9002"] = df_payroll["LGART_9001"] - df_payroll["income_tax_tds_inr"] - df_payroll["employer_cpf_inr"]
    
    df_payroll["payroll_id"] = [f"PAY-{i:08d}" for i in range(1, len(df_payroll) + 1)]
    
    # Note 35.1 lines for pools
    df_payroll["cost_note35_a_inr"] = df_payroll["LGART_9001"]
    df_payroll["cost_note35_b_inr"] = df_payroll["employer_cpf_inr"] + df_payroll["employer_prbs_inr"] + df_payroll["csss_contribution_inr"]
    df_payroll["cost_note35_c_inr"] = df_payroll["gratuity_accrual_inr"]
    df_payroll["cost_note35_d_inr"] = df_payroll["leave_provision_accrual_inr"]
    df_payroll["cost_note35_e_inr"] = df_payroll["employer_prmb_inr"]
    df_payroll["cost_note35_f_inr"] = (df_payroll["medical_scheme_cost_inr"] + df_payroll["group_insurance_premium_inr"] + df_payroll["accident_insurance_premium_inr"] + df_payroll["housing_cost_inr"] + df_payroll["canteen_subsidy_inr"] + df_payroll["transport_subsidy_inr"] + df_payroll["staff_welfare_alloc_inr"] + df_payroll["training_cost_inr"])
    
    # Now generate employee_cost_pool.csv
    # Residual pool: pool = AR line - Σ individual allocations
    df_targets_all = pd.read_csv(TARGETS_CSV)
    pools = []
    
    # We will sum by fiscal year
    fy_sums = df_payroll.groupby("fiscal_year")[["cost_note35_a_inr", "cost_note35_b_inr", "cost_note35_c_inr", "cost_note35_d_inr", "cost_note35_e_inr", "cost_note35_f_inr"]].sum().reset_index()
    
    for _, row in fy_sums.iterrows():
        fy = row["fiscal_year"]
        for line, col, pool_code in [
            ("note35_1_a", "cost_note35_a_inr", "POOL_RESIDUAL_a"),
            ("note35_1_b", "cost_note35_b_inr", "POOL_RESIDUAL_b"),
            ("note35_1_c", "cost_note35_c_inr", "POOL_RESIDUAL_c"),
            ("note35_1_d", "cost_note35_d_inr", "POOL_RESIDUAL_d"),
            ("note35_1_e", "cost_note35_e_inr", "POOL_RESIDUAL_e"),
            ("note35_1_f", "cost_note35_f_inr", "POOL_RESIDUAL_f"),
        ]:
            target_series = df_targets_all[(df_targets_all["fiscal_year"] == fy) & (df_targets_all["metric"] == line)]["value"]
            if not target_series.empty:
                target_inr = target_series.values[0] * 1e6
                modelled_inr = row[col]
                residual = target_inr - modelled_inr
                pools.append({
                    "fiscal_year": fy,
                    "month_start": f"{fy[:2]}26-03-01", # simplistic, or 2026-03-01
                    "pool_code": pool_code,
                    "note35_line": line[-1],
                    "amount_inr": residual,
                    "allocation_basis": "AR line - Σ individual allocations",
                    "cost_destination": "CO-HQ",
                    "segment": "Corporate",
                    "basis": "residual"
                })
                
    df_pools = pd.DataFrame(pools)
    df_pools.to_csv(LANDING_SAP.parent / "employee_cost_pool.csv", index=False)
    print(f"Wrote employee_cost_pool.csv")
    
    # Return formatted df
    ordered_cols = [
        "payroll_id", "PERNR", "FPPER", "fiscal_year", "wc_id", "grade_id", "discipline_id",
        "cost_centre_id", "LGART_1001", "LGART_1002", "cafeteria_allowances_inr", "hra_inr",
        "mining_offshore_allowance_inr", "overtime_hours", "overtime_amount_inr", "prp_inr",
        "employer_cpf_inr", "employer_prbs_inr", "employer_prmb_inr", "LGART_9001",
        "income_tax_tds_inr", "LGART_9002", "superannuation_benefit_pct"
    ]
    return df_payroll

def generate_payroll_monthly_wrapper(df_emp, df_post, work_centres, grades, disciplines, cost_centres):
    set_seed(2026)
    payroll_months = []
    for y in range(2016, 2027):
        for m in range(1, 13):
            if y == 2016 and m < 4: continue
            if y == 2026 and m > 9: continue
            payroll_months.append(f"{y:04d}-{m:02d}")
            
    # Lookup dictionaries
    wc_cost_centre = {}
    for cc in cost_centres:
        w_id = cc.get("wc_id")
        if w_id and w_id not in wc_cost_centre:
            wc_cost_centre[w_id] = cc.get("cost_centre_id")
    default_cc = cost_centres[0].get("cost_centre_id") if cost_centres else "CC-10001"

    df_targets = pd.read_csv(TARGETS_CSV)
    note35a_targets = dict(zip(
        df_targets[df_targets["metric"] == "note35_1_a"]["fiscal_year"],
        df_targets[df_targets["metric"] == "note35_1_a"]["value"]
    ))

    pay_rules.load_pay_reference_bundle()

    return generate_payroll_monthly_continue(df_emp, df_post, work_centres, grades, disciplines, cost_centres, wc_cost_centre, default_cc, payroll_months, note35a_targets)
