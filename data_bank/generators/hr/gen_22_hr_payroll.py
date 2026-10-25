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

_TS_2017_01_01 = pd.Timestamp(2017, 1, 1)
_TS_2016_12_31 = pd.Timestamp(2016, 12, 31)
_JULY1_TS = {y: pd.Timestamp(y, 7, 1) for y in range(1970, 2035)}

def get_bp_for_month(doj_dt, snap_dt, grade_id, grades, bundle, gender="Male"):
    is_2007 = snap_dt < _TS_2017_01_01
    if is_2007:
        scale_info = pay_rules.get_pay_scale(grade_id, "2007", bundle["allowance_rules"])
    else:
        scale_info = pay_rules.get_pay_scale(grade_id, "2017", bundle["allowance_rules"])
    
    scale_min = scale_info["min"]
    scale_max = scale_info["max"]
    
    import hashlib
    h = int(hashlib.md5(str(grade_id + str(doj_dt)).encode()).hexdigest(), 16)
    u_i = (h % 1000) / 1000.0
    tenure_yrs = max(0.0, (snap_dt - doj_dt).days / 365.25)
    is_exec = (grades.get(grade_id, {}).get("cadre") == "executive")
    
    if is_exec:
        t_norm = min(1.0, tenure_yrs / 34.0)
        if grade_id in ("E5", "E6", "E7", "E8", "E9", "DIR", "CMD"):
            if gender == "Female":
                u_pos = 0.01 + 0.15 * t_norm + 0.05 * u_i
            else:
                u_pos = 0.03 + 0.38 * t_norm + 0.10 * u_i
        else:
            if gender == "Female":
                u_pos = 0.59 + 0.06 * t_norm + 0.08 * u_i
            else:
                u_pos = 0.165 + 0.485 * t_norm + 0.12 * u_i
        vet_boost = 0.0 if gender == "Female" else 0.06 * max(0.0, (tenure_yrs - 21.0) / 10.0)
    else:
        t_norm = min(1.0, tenure_yrs / 30.0)
        if gender == "Female":
            u_pos = 0.60 + 0.35 * t_norm + 0.08 * u_i
            vet_boost = 0.0
        else:
            u_pos = 0.97 + 0.03 * t_norm
            vet_boost = 0.0

    u_pos = max(0.0, min(1.0, u_pos + vet_boost))
    if is_2007:
        u_pos = min(1.09, u_pos + 0.65)
    bp = scale_min + u_pos * (scale_max - scale_min)
    return round(bp / 10.0) * 10.0

def process_month(month_str, emp_df, post_df, grades, disciplines, work_centres, wc_cost_centre, default_cc):
    np.random.seed(2026 + int(month_str[:4]) * 100 + int(month_str[5:7]))
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
        
        gender = row.GESCH if hasattr(row, 'GESCH') else "Male"
        bp = get_bp_for_month(doj_dt, snap_dt, grade_id, grades, bundle, gender)
        
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
        
        if grades.get(grade_id, {}).get("cadre") == "executive":
            ot_base = 0.0
        else:
            if is_offshore:
                if np.random.rand() < 0.10:
                    ot_base = 0.0
                else:
                    ot_base = min(75.0, np.random.gamma(shape=10.0, scale=4.0))
            else:
                if np.random.rand() < 0.60:
                    ot_base = 0.0
                else:
                    ot_base = min(60.0, np.random.gamma(shape=2.0, scale=6.0))
            
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
            "cost_expensed_production_inr": components.get("cost_expensed_production_inr", 0.0),
            "caf_conveyance_inr": components.get("caf_conveyance_inr", 0.0),
            "caf_children_edu_inr": components.get("caf_children_edu_inr", 0.0),
            "caf_professional_dev_inr": components.get("caf_professional_dev_inr", 0.0),
            "caf_other_perks_inr": components.get("caf_other_perks_inr", 0.0),
            "hardship_offshore_inr": components.get("hardship_offshore_inr", 0.0),
            "field_duty_allowance_inr": components.get("field_duty_allowance_inr", 0.0),
            "location_comp_allowance_inr": components.get("location_comp_allowance_inr", 0.0),
            "hard_station_allowance_inr": components.get("hard_station_allowance_inr", 0.0),
            "shift_allowance_inr": components.get("shift_allowance_inr", 0.0),
            "night_duty_allowance_inr": components.get("night_duty_allowance_inr", 0.0),
            "npa_inr": components.get("npa_inr", 0.0),
            "special_allowance_inr": components.get("special_allowance_inr", 0.0),
            "prp_paid_inr": components.get("prp_paid_inr", 0.0),
            "leave_encashment_paid_inr": components.get("leave_encashment_paid_inr", 0.0),
            "ltc_inr": components.get("ltc_inr", 0.0),
            "medical_reimbursement_inr": components.get("medical_reimbursement_inr", 0.0),
            "ex_gratia_other_inr": components.get("ex_gratia_other_inr", 0.0),
            "employee_pf_inr": components.get("employee_pf_inr", 0.0),
            "vpf_inr": components.get("vpf_inr", 0.0),
            "professional_tax_inr": components.get("professional_tax_inr", 0.0),
            "hrr_recovery_inr": components.get("hrr_recovery_inr", 0.0),
            "loan_recoveries_inr": components.get("loan_recoveries_inr", 0.0),
            "other_recoveries_inr": components.get("other_recoveries_inr", 0.0),
            "capitalised_share": components.get("capitalised_share", 0.0),
            "cost_capitalised_inr": components.get("cost_capitalised_inr", 0.0),
            "cost_expensed_inr": components.get("cost_expensed_inr", 0.0),
            "cost_expensed_gae_inr": components.get("cost_expensed_gae_inr", 0.0),
            "cost_expensed_exploration_inr": components.get("cost_expensed_exploration_inr", 0.0),
            "field_id": None
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
    df_payroll["cost_note35_b_base"] = df_payroll["employer_cpf_inr"] + df_payroll["employer_prbs_inr"] + df_payroll["csss_contribution_inr"]
    
    fy_groups = df_payroll.groupby("fiscal_year")[["fixed_note35a", "adjustable_note35a_base", "cost_note35_b_base"]].sum().reset_index()
    
    payroll_policies = []
    
    # We will fit u_fy, k_fy, ot_fy for each FY separately.
    u_dict = {}
    k_dict = {}
    ot_dict = {}
    
    for _, row in fy_groups.iterrows():
        fy = row["fiscal_year"]
        target = note35_targets.get((fy, "note35_1_a"))
        target_total = note35_targets.get((fy, "employee_cost_total"))
        if not target and target_total:
            target = target_total * note35_targets.get(("FY21", "note35_1_a")) / note35_targets.get(("FY21", "employee_cost_total"))
        target_b = note35_targets.get((fy, "note35_1_b"))
        if not target_b and target_total:
            target_b = target_total * note35_targets.get(("FY21", "note35_1_b")) / note35_targets.get(("FY21", "employee_cost_total"))
        
        u_fy, k_fy, ot_fy = 1.0, 1.0, 1.0
        res_pool_pct = 0.0
        
        if target:
            target_inr = target * 1e6
            target_tot_inr = (target_total * 1e6) if target_total else (target_inr / 0.74)
            target_b_inr = (target_b * 1e6) if target_b else (target_tot_inr * 0.095)
            fixed_note35a = row["fixed_note35a"]
            mod_b_inr = row["cost_note35_b_base"]
            res_b = target_b_inr - mod_b_inr
            # 3rd-PRC arrears only in FY18 and FY19
            arrears_sum = 0.0
            if fy == "FY18":
                arrears_sum = df_payroll.loc[df_payroll["fiscal_year"] == "FY18", "LGART_1001"].sum() * 0.15
            elif fy == "FY19":
                arrears_sum = df_payroll.loc[df_payroll["fiscal_year"] == "FY19", "LGART_1001"].sum() * 0.10
            
            fixed_total = fixed_note35a + arrears_sum
            
            caf_base = df_payroll.loc[df_payroll["fiscal_year"] == fy, "cafeteria_allowance_inr_base"].sum()
            prp_base = df_payroll.loc[df_payroll["fiscal_year"] == fy, "prp_accrual_inr_base"].sum()
            ot_base = df_payroll.loc[df_payroll["fiscal_year"] == fy, "overtime_amount_inr_base"].sum()
            
            best_x = (1.0, 1.0, 1.0)
            best_val = float("inf")
            for u_cand in np.linspace(0.35, 1.00, 27):
                for k_cand in np.linspace(0.10, 3.20, 32):
                    for ot_cand in np.linspace(0.80, 2.20, 29):
                        calc_a = fixed_total + caf_base * min(1.0, u_cand) + prp_base * k_cand + ot_base * ot_cand
                        res_a = target_inr - calc_a
                        rel_a = res_a / target_inr
                        rel_tot = (res_a + res_b) / target_tot_inr
                        if abs(rel_a) <= 0.038 and (fy not in ["FY21", "FY22", "FY23", "FY24", "FY25", "FY26"] or abs(rel_tot) <= 0.028):
                            val = (rel_a / 0.01) ** 2 + 2.0 * (4.0 * (u_cand - 0.98) ** 2 + 0.5 * (k_cand - 0.40) ** 2 + 3.0 * (ot_cand - 1.85) ** 2)
                            if val < best_val:
                                best_val = val
                                best_x = (float(u_cand), float(k_cand), float(ot_cand))
            u_fy, k_fy, ot_fy = best_x
            calc_a = fixed_total + caf_base * min(1.0, u_fy) + prp_base * k_fy + ot_base * ot_fy
            res_pool_pct = round(abs((target_inr - calc_a) + res_b) / target_tot_inr * 100.0, 4)
                
        u_dict[fy] = u_fy
        k_dict[fy] = k_fy
        ot_dict[fy] = ot_fy
        
        fy_end_yr = 2000 + int(fy[2:])
        fy_start_yr = fy_end_yr - 1
        da_q1 = pay_rules.get_ida_rate(f"{fy_start_yr}-04")[0]
        da_q2 = pay_rules.get_ida_rate(f"{fy_start_yr}-07")[0]
        da_q3 = pay_rules.get_ida_rate(f"{fy_start_yr}-10")[0]
        da_q4 = pay_rules.get_ida_rate(f"{fy_end_yr}-01")[0]
        da_avg = round((da_q1 + da_q2 + da_q3 + da_q4) / 4.0, 2)
        arr_fac = 0.15 if fy == "FY18" else (0.10 if fy == "FY19" else 0.0)
        arr_mo = f"{fy_end_yr}-03" if fy in ("FY18", "FY19") else "None"
        
        payroll_policies.append({
            "fiscal_year": fy,
            "da_q1_pct": da_q1,
            "da_q2_pct": da_q2,
            "da_q3_pct": da_q3,
            "da_q4_pct": da_q4,
            "da_fy_avg_pct": da_avg,
            "prp_pool_factor": round(k_fy, 4),
            "Increment_rate_pct": 3.0,
            "arrears_factor": arr_fac,
            "arrears_month": arr_mo,
            "prbs_rate_pct": 10.19,
            "u_fy": round(u_fy, 4),
            "k_fy": round(k_fy, 4),
            "ot_fy": round(ot_fy, 4),
            "residual_pool_pct": res_pool_pct,
            "notes": "Generated by gen_22_hr_payroll"
        })
        
    df_policies = pd.DataFrame(payroll_policies)
    (DATA_BANK_ROOT / "reference" / "ar_targets").mkdir(parents=True, exist_ok=True)
    df_policies.to_csv(DATA_BANK_ROOT / "reference" / "ar_targets" / "payroll_policy_fy.csv", index=False)
    df_policies.to_csv(TARGETS_CSV.parent / "payroll_policy_fy.csv", index=False)
    df_policies.to_csv(LANDING_SAP / "payroll_policy_fy.csv", index=False)
    
    df_payroll["u_fy"] = df_payroll["fiscal_year"].map(u_dict)
    df_payroll["k_fy"] = df_payroll["fiscal_year"].map(k_dict)
    df_payroll["ot_fy"] = df_payroll["fiscal_year"].map(ot_dict)
    
    df_payroll["cafeteria_allowances_inr"] = (df_payroll["cafeteria_allowance_inr_base"] * df_payroll["u_fy"].clip(upper=1.0)).round(2)
    df_payroll["overtime_amount_inr"] = (df_payroll["overtime_amount_inr_base"] * df_payroll["ot_fy"]).round(2)
    df_payroll["prp_inr"] = (df_payroll["prp_accrual_inr_base"] * df_payroll["k_fy"]).round(2)
    
    # 3rd-PRC wage arrears only in FY18 and FY19 per SPEC-04 §6.4 step 4 (no per-person plugs outside FY18/FY19)
    df_payroll["arrears_inr"] = 0.0
    df_payroll.loc[df_payroll["fiscal_year"] == "FY18", "arrears_inr"] = (df_payroll.loc[df_payroll["fiscal_year"] == "FY18", "LGART_1001"] * 0.15).round(2)
    df_payroll.loc[df_payroll["fiscal_year"] == "FY19", "arrears_inr"] = (df_payroll.loc[df_payroll["fiscal_year"] == "FY19", "LGART_1001"] * 0.10).round(2)

    
    df_payroll["LGART_9001"] = df_payroll["fixed_note35a"] + df_payroll["cafeteria_allowances_inr"] + df_payroll["overtime_amount_inr"] + df_payroll["prp_inr"] + df_payroll["arrears_inr"]

    
    
    df_payroll["LGART_9002"] = df_payroll["LGART_9001"] - df_payroll["income_tax_tds_inr"] - df_payroll["employer_cpf_inr"]
    
    df_payroll["cost_expensed_inr"] = df_payroll["LGART_9001"] + df_payroll["employer_cpf_inr"] + df_payroll["employer_prbs_inr"] + df_payroll["csss_contribution_inr"] + df_payroll["gratuity_accrual_inr"] + df_payroll["leave_provision_accrual_inr"] + df_payroll["employer_prmb_inr"] + df_payroll["medical_scheme_cost_inr"] + df_payroll["group_insurance_premium_inr"] + df_payroll["accident_insurance_premium_inr"] + df_payroll["housing_cost_inr"] + df_payroll["canteen_subsidy_inr"] + df_payroll["transport_subsidy_inr"] + df_payroll["staff_welfare_alloc_inr"] + df_payroll["training_cost_inr"]
    df_payroll["cost_capitalised_inr"] = 0.0
    for fy in df_payroll["fiscal_year"].unique():
        target_staff_exp = note35_targets.get((fy, "staff_expenditure_note35"))
        if not target_staff_exp:
            target_staff_exp = note35_targets.get((fy, "employee_cost_total"), 0) * (26521.21 / 102107.09)
        if target_staff_exp:
            target_inr = target_staff_exp * 1e6
            fy_mask = df_payroll["fiscal_year"] == fy
            total_expensed = df_payroll.loc[fy_mask, "cost_expensed_inr"].sum()
            if total_expensed > 0:
                prod_sh = target_inr / total_expensed
                df_payroll.loc[fy_mask, "cost_expensed_production_inr"] = (df_payroll.loc[fy_mask, "cost_expensed_inr"] * prod_sh).round(2)
                df_payroll.loc[fy_mask, "cost_expensed_gae_inr"] = (df_payroll.loc[fy_mask, "cost_expensed_inr"] * (1.0 - prod_sh)).round(2)
                df_payroll.loc[fy_mask, "cost_allocated_ew_dd_survey_inr"] = 0.0
                df_payroll.loc[fy_mask, "cost_expensed_pnl_inr"] = df_payroll.loc[fy_mask, "cost_expensed_production_inr"] + df_payroll.loc[fy_mask, "cost_expensed_gae_inr"]
                df_payroll.loc[fy_mask, "cost_expensed_exploration_inr"] = 0.0

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
                # Lines a and b depend on FY
        for line, col in [
            ("note35_1_a", "cost_note35_a_inr"),
            ("note35_1_b", "cost_note35_b_inr")
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
                
                # For FY21-FY26, use POOL_RESIDUAL_*, basis="residual"
                # For FY17-FY20, use POOL_ACTUARIAL_TRUEUP, basis="real_total_modelled_split"
                
                # Wait, the problem says amount_inr = target_inr - modelled_inr for POOL_RESIDUAL.
                # So we can just emit it even if negative?
                # The rule for a/b: emit pool_amount directly!
                
                if fy in ["FY21", "FY22", "FY23", "FY24", "FY25", "FY26"]:
                    pool_code = f"POOL_RESIDUAL_{line[-1].upper()}"
                    basis = "residual"
                else:
                    pool_code = "POOL_ACTUARIAL_TRUEUP"
                    basis = "real_total_modelled_split"
                    
                if pool_amount != 0:
                    pools.append({
                        "fiscal_year": fy,
                        "month_start": f"20{fy[-2:]}-03-01",  # dummy
                        "pool_code": pool_code,
                        "note35_line": line[-1],
                        "amount_inr": pool_amount,
                        "allocation_basis": f"AR line {line[-1]} minus modelled active",
                        "cost_destination": "CO-HQ",
                        "segment": "Corporate",
                        "basis": basis
                    })

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
                
                if pool_amount != 0:
                    pools.append({
                        "fiscal_year": fy,
                        "month_start": f"20{fy[-2:]}-03-01",
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
    df_pools.to_csv(LANDING_SAP / "employee_cost_pool.csv", index=False)
    
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
