import pandas as pd
import numpy as np
import datetime
from typing import Dict, Any, List
import pay_rules
from pathlib import Path
import os
import multiprocessing
from functools import partial
from gen_22_hr_sat import get_month_end_date, get_fiscal_year, set_seed

DATA_BANK_ROOT = Path(__file__).resolve().parent.parent.parent
LANDING_SAP = DATA_BANK_ROOT / "landing" / "sap"
TARGETS_CSV = DATA_BANK_ROOT / "world_bible" / "reference" / "real_targets" / "employee_targets_fy.csv"

def get_bp_for_month(doj_dt, snap_dt, grade_id, grades, bundle):
    is_2007 = snap_dt < pd.to_datetime("2017-01-01")
    if is_2007:
        scale_info = pay_rules.get_pay_scale(grade_id, "2007", bundle["allowance_rules"])
    else:
        scale_info = pay_rules.get_pay_scale(grade_id, "2017", bundle["allowance_rules"])
    
    scale_min = scale_info["min"]
    scale_max = scale_info["max"]
    
    if doj_dt < pd.to_datetime("2017-01-01") and snap_dt >= pd.to_datetime("2017-01-01"):
        scale_2007 = pay_rules.get_pay_scale(grade_id, "2007", bundle["allowance_rules"])
        bp = scale_2007["min"]
        for y in range(doj_dt.year, 2017):
            july1 = pd.to_datetime(f"{y}-07-01")
            if doj_dt < july1 <= pd.to_datetime("2016-12-31"):
                bp, _, _ = pay_rules.apply_annual_increment(bp, scale_2007["max"], 0.03)
        bp = pay_rules.apply_3rd_prc_fitment_2017(bp, 119.5, scale_info["min"], scale_info["max"])
        for y in range(2017, snap_dt.year + 1):
            july1 = pd.to_datetime(f"{y}-07-01")
            if july1 <= snap_dt:
                bp, _, _ = pay_rules.apply_annual_increment(bp, scale_info["max"], 0.03)
        return bp
    else:
        bp = scale_min
        for y in range(doj_dt.year, snap_dt.year + 1):
            july1 = pd.to_datetime(f"{y}-07-01")
            if doj_dt < july1 <= snap_dt:
                bp, _, _ = pay_rules.apply_annual_increment(bp, scale_max, 0.03)
        return bp

def process_month(month_str, emp_df, post_df, grades, disciplines, work_centres, wc_cost_centre, default_cc):
    bundle = pay_rules.load_pay_reference_bundle()
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
    for row in m.itertuples(index=False):
        grade_id = row.PERSK
        wc_id = row.WERKS
        doj_dt = row.doj_dt
        
        bp = get_bp_for_month(doj_dt, snap_dt, grade_id, grades, bundle)
        
        wc = work_centres.get(wc_id, {})
        city_raw = wc.get("hra_city_class") or wc.get("city", "")
        city_upper = city_raw.upper()
        if city_upper in ["NEW DELHI", "DELHI", "MUMBAI", "NAVI MUMBAI", "CHENNAI", "KOLKATA", "BENGALURU", "HYDERABAD", "AHMEDABAD", "PUNE"]:
            city_class = "X"
        elif city_upper in ["DEHRADUN", "VADODARA", "SURAT", "RAJAHMUNDRY", "KAKINADA", "JODHPUR", "JORHAT", "AGARTALA", "RANCHI", "BOKARO", "GOA", "PANAJI", "HAZIRA", "ANKLESHWAR", "MEHSANA", "CAMBAY", "CAUVERY", "KARAIKAL"]:
            city_class = "Y"
        else:
            city_class = "Z"
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
            basic_pay_inr=bp,
            u_fy=1.0,
            k_fy=1.0,
            apar_factor=1.0,
            offshore_days=15.0 if is_offshore else 0.0,
            hard_station_flag=is_hard,
            overtime_hours=ot_base,
            prp_paid_inr=0.0,
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
            "prp_accrual_inr_base": components.get("prp_accrual_inr", 0.0),
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

def generate_payroll_monthly_continue(df_emp, df_post, work_centres, grades, disciplines, cost_centres, wc_cost_centre, default_cc, payroll_months, note35_targets):
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
    
    df_payroll["fixed_note35a"] = df_payroll["LGART_1001"] + df_payroll["LGART_1002"] + df_payroll["hra_inr"] + df_payroll["mining_offshore_allowance_inr"]
    df_payroll["adjustable_note35a_base"] = df_payroll["cafeteria_allowance_inr_base"] + df_payroll["overtime_amount_inr_base"] + df_payroll["prp_accrual_inr_base"]
    
    fy_groups = df_payroll.groupby("fiscal_year")[["fixed_note35a", "adjustable_note35a_base"]].sum().reset_index()
    
    payroll_policies = []
    
    # We will fit u_fy, k_fy, ot_fy for each FY separately.
    u_dict = {}
    k_dict = {}
    ot_dict = {}
    
    for _, row in fy_groups.iterrows():
        fy = row["fiscal_year"]
        target = note35_targets.get((fy, "note35_1_a"))
        if not target:
            target_total = note35_targets.get((fy, "employee_cost_total"))
            if target_total:
                target = target_total * note35_targets.get(("FY21", "note35_1_a")) / note35_targets.get(("FY21", "employee_cost_total"))
        
        u_fy, k_fy, ot_fy = 1.0, 1.0, 1.0
        
        if target:
            target_inr = target * 1e6
            fixed_note35a = row["fixed_note35a"]
            # Arrears are part of fixed_note35a effectively
            arrears_sum = 0
            if fy == "FY17":
                arrears_sum = df_payroll.loc[df_payroll["fiscal_year"] == "FY17", "LGART_1001"].sum() * 0.25
            elif fy == "FY18":
                arrears_sum = df_payroll.loc[df_payroll["fiscal_year"] == "FY18", "LGART_1001"].sum() * 0.15
            elif fy == "FY19":
                arrears_sum = df_payroll.loc[df_payroll["fiscal_year"] == "FY19", "LGART_1001"].sum() * 0.10
            
            fixed_total = fixed_note35a + arrears_sum
            
            caf_base = df_payroll.loc[df_payroll["fiscal_year"] == fy, "cafeteria_allowance_inr_base"].sum()
            prp_base = df_payroll.loc[df_payroll["fiscal_year"] == fy, "prp_accrual_inr_base"].sum()
            ot_base = df_payroll.loc[df_payroll["fiscal_year"] == fy, "overtime_amount_inr_base"].sum()
            
            if fy == "FY17":
                print(f"FY17 target_inr={target_inr/1e7:.2f} Cr, fixed_total={fixed_total/1e7:.2f} Cr (fixed={fixed_note35a/1e7:.2f}, arrears={arrears_sum/1e7:.2f}), caf={caf_base/1e7:.2f}, prp={prp_base/1e7:.2f}, ot={ot_base/1e7:.2f}")
            def objective(x):
                calc = (fixed_total + caf_base*min(1.0, x[0]) + prp_base*x[1] + ot_base*x[2]) / 1e7
                t_inr = target_inr / 1e7
                return (calc - t_inr)**2 + 100.0 * ((x[0]-1.0)**2 + (x[1]-1.0)**2 + (x[2]-1.0)**2)
                
            import scipy.optimize as opt
            res = opt.minimize(objective, [1.0, 1.0, 1.0], bounds=[(0.85, 1.00), (0.30, 1.00), (0.70, 1.30)])
            u_fy, k_fy, ot_fy = res.x
                
        u_dict[fy] = u_fy
        k_dict[fy] = k_fy
        ot_dict[fy] = ot_fy
        
        payroll_policies.append({
            "fiscal_year": fy,
            "k_fy": k_fy,
            "u_fy": u_fy,
            "ot_fy": ot_fy
        })
        
    df_policies = pd.DataFrame(payroll_policies)
    df_policies.to_csv(TARGETS_CSV.parent / "payroll_policy_fy.csv", index=False)
    
    df_payroll["u_fy"] = df_payroll["fiscal_year"].map(u_dict)
    df_payroll["k_fy"] = df_payroll["fiscal_year"].map(k_dict)
    df_payroll["ot_fy"] = df_payroll["fiscal_year"].map(ot_dict)
    
    df_payroll["cafeteria_allowances_inr"] = df_payroll["cafeteria_allowance_inr_base"] * df_payroll["u_fy"].clip(upper=1.0)
    df_payroll["overtime_amount_inr"] = df_payroll["overtime_amount_inr_base"] * df_payroll["ot_fy"]
    df_payroll["prp_inr"] = df_payroll["prp_accrual_inr_base"] * df_payroll["k_fy"]
    
    # 3rd-PRC wage arrears paid in FY18 and FY19 + provision in FY17
    df_payroll["arrears_inr"] = 0.0
    # Q4 FY17 3rd-PRC provision to hit 7440.27 Cr target for line A
    df_payroll.loc[df_payroll["fiscal_year"] == "FY17", "arrears_inr"] = df_payroll.loc[df_payroll["fiscal_year"] == "FY17", "LGART_1001"] * 0.25
    df_payroll.loc[df_payroll["fiscal_year"] == "FY18", "arrears_inr"] = df_payroll.loc[df_payroll["fiscal_year"] == "FY18", "LGART_1001"] * 0.15
    df_payroll.loc[df_payroll["fiscal_year"] == "FY19", "arrears_inr"] = df_payroll.loc[df_payroll["fiscal_year"] == "FY19", "LGART_1001"] * 0.10

    
    df_payroll["LGART_9001"] = df_payroll["fixed_note35a"] + df_payroll["cafeteria_allowances_inr"] + df_payroll["overtime_amount_inr"] + df_payroll["prp_inr"] + df_payroll["arrears_inr"]
    
    df_payroll["LGART_9002"] = df_payroll["LGART_9001"] - df_payroll["income_tax_tds_inr"] - df_payroll["employer_cpf_inr"]
    df_payroll["payroll_id"] = [f"PAY-{i:08d}" for i in range(1, len(df_payroll) + 1)]
    
    df_payroll["cost_note35_a_inr"] = df_payroll["LGART_9001"]
    df_payroll["cost_note35_b_inr"] = df_payroll["employer_cpf_inr"] + df_payroll["employer_prbs_inr"] + df_payroll["csss_contribution_inr"]
    df_payroll["cost_note35_c_inr"] = df_payroll["gratuity_accrual_inr"]
    df_payroll["cost_note35_d_inr"] = df_payroll["leave_provision_accrual_inr"]
    df_payroll["cost_note35_e_inr"] = df_payroll["employer_prmb_inr"]
    df_payroll["cost_note35_f_inr"] = (df_payroll["medical_scheme_cost_inr"] + df_payroll["group_insurance_premium_inr"] + df_payroll["accident_insurance_premium_inr"] + df_payroll["housing_cost_inr"] + df_payroll["canteen_subsidy_inr"] + df_payroll["transport_subsidy_inr"] + df_payroll["staff_welfare_alloc_inr"] + df_payroll["training_cost_inr"])
    
    pools = []
    fy_sums = df_payroll.groupby("fiscal_year")[["cost_note35_a_inr", "cost_note35_b_inr", "cost_note35_c_inr", "cost_note35_d_inr", "cost_note35_e_inr", "cost_note35_f_inr"]].sum().reset_index()
    
    # Calculate basic + da by year for driver
    bp_da_by_fy = df_payroll.groupby("fiscal_year")[["LGART_1001", "LGART_1002"]].sum().sum(axis=1).to_dict()

    for _, row in fy_sums.iterrows():
        fy = row["fiscal_year"]
        
        # Actuarial and welfare pools (c to f)
        for line, col, pool_code in [
            ("note35_1_c", "cost_note35_c_inr", "POOL_ACTUARIAL_TRUEUP"),
            ("note35_1_d", "cost_note35_d_inr", "POOL_ACTUARIAL_TRUEUP"),
            ("note35_1_e", "cost_note35_e_inr", "POOL_RETIREE_PRMB"),
            ("note35_1_f", "cost_note35_f_inr", "POOL_WELFARE_INFRA"),
        ]:
            target = note35_targets.get((fy, line))
            if not target:
                target_total = note35_targets.get((fy, "employee_cost_total"))
                if target_total:
                    target = target_total * note35_targets.get(("FY21", line)) / note35_targets.get(("FY21", "employee_cost_total"))
            if target:
                target_inr = target * 1e6
                modelled_inr = row[col]
                
                pool_amount = target_inr - modelled_inr
                
                if pool_amount > 0:
                    pools.append({
                        "fiscal_year": fy,
                        "month_start": f"{fy[:2]}26-03-01",
                        "pool_code": pool_code,
                        "note35_line": line[-1],
                        "amount_inr": pool_amount,
                        "allocation_basis": f"AR line {line[-1]} minus modelled active",
                        "cost_destination": "CO-HQ",
                        "segment": "Corporate",
                        "basis": "real_total_modelled_split"
                    })


                
    df_pools = pd.DataFrame(pools)
    df_pools.to_csv(LANDING_SAP.parent / "employee_cost_pool.csv", index=False)
    
    return df_payroll

def generate_payroll_monthly_wrapper(df_emp, df_post, work_centres, grades, disciplines, cost_centres):
    set_seed(2026)
    payroll_months = []
    for y in range(2016, 2027):
        for m in range(1, 13):
            if y == 2016 and m < 4: continue
            if y == 2026 and m > 9: continue
            payroll_months.append(f"{y:04d}-{m:02d}")
            
    wc_cost_centre = {}
    for cc in cost_centres:
        w_id = cc.get("wc_id")
        if w_id and w_id not in wc_cost_centre:
            wc_cost_centre[w_id] = cc.get("cost_centre_id")
    default_cc = cost_centres[0].get("cost_centre_id") if cost_centres else "CC-10001"

    df_targets = pd.read_csv(TARGETS_CSV)
    note35_targets = {}
    for _, row in df_targets.iterrows():
        note35_targets[(row["fiscal_year"], row["metric"])] = row["value"]

    pay_rules.load_pay_reference_bundle()

    return generate_payroll_monthly_continue(df_emp, df_post, work_centres, grades, disciplines, cost_centres, wc_cost_centre, default_cc, payroll_months, note35_targets)
