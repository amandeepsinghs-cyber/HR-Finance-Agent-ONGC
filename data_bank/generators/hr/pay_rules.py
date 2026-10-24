#!/usr/bin/env python3
"""Pure, deterministic pay & allowance rule engine for Employee-360 (SPEC-04 §5–§6 / P2H.5).

All functions are pure and side-effect-free so they can be unit-tested directly
by `test_22_hr_sat.py` and `test_60_employee360_recon.py` and called from
`gen_22_hr_sat.py`. No hardcoded entity IDs (Rule 5a compliant).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
REF_DIR = REPO_ROOT / "data_bank" / "world_bible" / "reference"


def load_pay_reference_bundle(ref_dir: Path = REF_DIR) -> dict[str, Any]:
    """Load `ida_rates.yaml`, `hra_rates.yaml`, and `allowance_rules.yaml`."""
    with (ref_dir / "ida_rates.yaml").open("r", encoding="utf-8") as f:
        ida_doc = yaml.safe_load(f)
    with (ref_dir / "hra_rates.yaml").open("r", encoding="utf-8") as f:
        hra_doc = yaml.safe_load(f)
    with (ref_dir / "allowance_rules.yaml").open("r", encoding="utf-8") as f:
        allow_doc = yaml.safe_load(f)
    return {
        "ida_rates": ida_doc["ida_rates"],
        "hra_rules": hra_doc,
        "allowance_rules": allow_doc,
    }


def roundup_10(amount: float) -> float:
    """Round up `amount` to the next multiple of ₹10 (DPE OM 3-Aug-2017 para 6 / fitment & increment rule)."""
    if amount <= 0.0:
        return 0.0
    # Guard against IEEE-754 representation noise like 61800.00000000001
    return float(math.ceil(round(amount, 4) / 10.0) * 10.0)


def apply_annual_increment(
    basic_pay_inr: float,
    scale_max_inr: float,
    increment_rate: float = 0.03,
    stagnation_increments_held: int = 0,
    max_stagnation_increments: int = 3,
) -> tuple[float, int, bool]:
    """Apply 3% annual increment rounded up to next ₹10, respecting scale max and stagnation rules.

    Returns `(new_basic_pay_inr, new_stagnation_increments_held, applied_stagnation_flag)`.
    """
    proposed = roundup_10(basic_pay_inr * (1.0 + increment_rate))
    if proposed <= scale_max_inr:
        return proposed, stagnation_increments_held, False
    if basic_pay_inr < scale_max_inr:
        return float(scale_max_inr), stagnation_increments_held, False
    if stagnation_increments_held < max_stagnation_increments:
        stag_cap = roundup_10(scale_max_inr * ((1.0 + increment_rate) ** (stagnation_increments_held + 1)))
        return min(proposed, stag_cap), stagnation_increments_held + 1, True
    return float(basic_pay_inr), stagnation_increments_held, False


def apply_promotion_fixation(
    old_basic_pay_inr: float,
    new_scale_min_inr: float,
    new_scale_max_inr: float,
    increment_rate: float = 0.03,
) -> float:
    """Fix basic pay on promotion: one notional increment (3%, rounded to next ₹10), floored at new scale min."""
    notional = roundup_10(old_basic_pay_inr * (1.0 + increment_rate))
    return float(min(new_scale_max_inr, max(new_scale_min_inr, notional)))


def apply_3rd_prc_fitment_2017(
    basic_2007_inr: float,
    ida_pct_jan2017_on_2007: float,
    new_scale_min_inr: float,
    new_scale_max_inr: float,
    fitment_factor: float = 1.15,
) -> float:
    """Apply 3rd PRC fitment as on 01-Jan-2017 (DPE OM 3-Aug-2017 para 4):
    `(BP_2007 + DA_as_on_1_Jan_2017) * 1.15`, rounded up to next ₹10, clamped to `[new_min, new_max]`.
    """
    base_plus_da = basic_2007_inr * (1.0 + ida_pct_jan2017_on_2007 / 100.0)
    fitted = roundup_10(base_plus_da * fitment_factor)
    return float(min(new_scale_max_inr, max(new_scale_min_inr, fitted)))


def get_ida_rate(
    month_str: str,
    ida_rates: list[dict[str, Any]] | None = None,
) -> tuple[float, str, str]:
    """Return `(ida_pct, scale_version, status)` effective for `month_str` (`YYYY-MM` or `YYYY-MM-DD`)."""
    if ida_rates is None:
        ida_rates = load_pay_reference_bundle()["ida_rates"]
    ym = month_str[:7]
    chosen: dict[str, Any] | None = None
    for row in ida_rates:
        eff_ym = str(row.get("effective_date") or row.get("effective_from"))[:7]
        if eff_ym <= ym:
            chosen = row
        else:
            break
    if chosen is None:
        chosen = ida_rates[0]
    return float(chosen["ida_pct"]), str(chosen["scale_version"]), str(chosen["status"])


def get_hra_rate_pct(
    city_class: str,
    ida_pct: float,
    hra_rules: dict[str, Any] | None = None,
) -> float:
    """Return DPE HRA rate % of Basic Pay for `city_class` (`X`, `Y`, `Z`, `NONE`) and `ida_pct`.

    Reads bands from `hra_rates.yaml` (DPE OM 4-Aug-2017).
    """
    cc = (city_class or "Z").upper()
    if cc == "NONE":
        return 0.0
    if hra_rules is None:
        hra_rules = load_pay_reference_bundle()["hra_rules"]
    for row in hra_rules["hra_rates"]:
        if str(row["city_class"]).upper() != cc:
            continue
        if ida_pct >= 50.0:
            return float(row["hra_pct_ida_ge_50"])
        if ida_pct >= 25.0:
            return float(row["hra_pct_ida_25_to_50"])
        return float(row["hra_pct_ida_lt_25"])
    return 0.0


def get_hrr_rate_pct(city_class: str, hra_rules: dict[str, Any] | None = None) -> float:
    """Return House Rent Recovery (HRR) % of Basic Pay for company/leased accommodation."""
    cc = (city_class or "Z").upper()
    if hra_rules is None:
        hra_rules = load_pay_reference_bundle()["hra_rules"]
    for row in hra_rules["hra_rates"]:
        if str(row["city_class"]).upper() == cc:
            return float(row["hrr_pct_bp"])
    return 0.0


def get_gratuity_ceiling(ida_pct: float) -> float:
    """Return gratuity ceiling in INR (₹20L from 1-Jan-2017; +25% to ₹25L once IDA reaches 50%)."""
    return 2500000.0 if ida_pct >= 50.0 else 2000000.0


def get_pay_scale(
    grade_id: str,
    scale_version: str = "2017",
    allowance_rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return `{min, max, prp_ceiling_pct, cadre, group_class}` for `grade_id` and `scale_version` (`2007` or `2017`)."""
    if allowance_rules is None:
        allowance_rules = load_pay_reference_bundle()["allowance_rules"]
    key = "pay_scales_2007" if scale_version in ("2007", "WS2007") else "pay_scales_2017"
    table = allowance_rules[key]
    if grade_id not in table:
        raise KeyError(f"Unknown grade_id={grade_id!r} in {key}")
    raw = dict(table[grade_id])
    base_2017 = allowance_rules["pay_scales_2017"].get(grade_id, {})
    min_val = float(raw.get("min", raw.get("min_inr", 0.0)))
    max_val = float(raw.get("max", raw.get("max_inr", 0.0)))
    prp_val = float(raw.get("prp_ceiling_pct", base_2017.get("prp_ceiling_pct", 40.0)))
    if grade_id in ("DIR", "CMD"):
        cadre = "board"
        group_class = "Group A"
    elif grade_id.startswith("E"):
        cadre = "executive"
        group_class = "Group A"
    else:
        cadre = "non_executive"
        group_class = {"GRP-B": "Group B", "GRP-C": "Group C", "GRP-D": "Group D"}.get(grade_id, "Group C")
    return {
        "min": min_val,
        "max": max_val,
        "min_inr": min_val,
        "max_inr": max_val,
        "prp_ceiling_pct": prp_val,
        "cadre": cadre,
        "group_class": group_class,
        "status": raw.get("status", base_2017.get("status", "illustrative")),
    }


def compute_monthly_pay_components(
    *,
    grade_id: str,
    month_str: str,
    city_class: str = "X",
    accommodation_type: str = "HRA",
    basic_pay_inr: float | None = None,
    ida_pct_override: float | None = None,
    increments_count: int = 0,
    stagnation_increments: int = 0,
    u_fy: float = 1.0,
    k_fy: float = 0.90,
    apar_factor: float = 1.0,
    lca_zone: str | None = None,
    offshore_days: float = 0.0,
    days_in_month: int = 30,
    field_duty_pct: float = 0.0,
    hard_station_flag: bool = False,
    shift_allowance_inr: float = 0.0,
    night_duty_allowance_inr: float = 0.0,
    npa_flag: bool = False,
    special_allowance_inr: float = 0.0,
    overtime_hours: float = 0.0,
    prp_paid_inr: float = 0.0,
    arrears_inr: float = 0.0,
    leave_encashment_paid_inr: float = 0.0,
    ltc_inr: float = 0.0,
    medical_reimbursement_inr: float = 0.0,
    ex_gratia_other_inr: float = 0.0,
    prbs_rate_pct: float = 10.19,
    gratuity_rate_pct: float = 4.81,
    prmb_rate_pct: float = 3.0,
    csss_contribution_inr: float = 800.0,
    leave_provision_accrual_inr: float = 5500.0,
    medical_scheme_cost_inr: float = 6500.0,
    group_insurance_premium_inr: float = 500.0,
    accident_insurance_premium_inr: float = 400.0,
    housing_cost_inr: float = 0.0,
    canteen_subsidy_inr: float = 2200.0,
    transport_subsidy_inr: float = 1800.0,
    staff_welfare_alloc_inr: float = 5000.0,
    training_cost_inr: float = 0.0,
    vpf_rate_pct: float = 0.0,
    professional_tax_inr: float = 0.0,
    loan_recoveries_inr: float = 0.0,
    other_recoveries_inr: float = 0.0,
    capitalised_share: float = 0.0,
    expensed_dest_shares: tuple[float, float, float] = (0.0, 1.0, 0.0),
    bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute a complete, rule-accurate monthly pay & cost breakdown for one employee-month (SPEC-04 §4 E–I).

    Check worked example (P2H.5 §6: E1 joined 2025-07-01 at Delhi HQ, city_class='X', accommodation_type='HRA', u_fy=1.0):
      - basic_pay_inr = 60000.00
      - ida_pct = 49.0 -> ida_inr = 29400.00
      - hra_rate_pct = 27.0 -> hra_inr = 16200.00
      - cafeteria_allowance_inr = 21000.00
      - gross_earnings_inr = 126600.00
      - employer_cpf_inr = 10728.00
    """
    if bundle is None:
        bundle = load_pay_reference_bundle()
    ida_pct, raw_scale_ver, ida_status = get_ida_rate(month_str, bundle["ida_rates"])
    if ida_pct_override is not None:
        ida_pct = float(ida_pct_override)
    scale_info = get_pay_scale(grade_id, raw_scale_ver, bundle["allowance_rules"])
    cadre = str(scale_info["cadre"])
    is_workman = cadre == "non_executive"
    pay_scale_version = f"WS{raw_scale_ver}" if is_workman else raw_scale_ver
    scale_min = float(scale_info["min"])
    scale_max = float(scale_info["max"])
    prp_ceiling_pct = float(scale_info["prp_ceiling_pct"])

    if basic_pay_inr is None:
        basic = scale_min
        for _ in range(max(0, increments_count)):
            basic, _, _ = apply_annual_increment(basic, scale_max, 0.03)
    else:
        basic = float(basic_pay_inr)

    basic = round(basic, 2)
    ida_inr = round(basic * (ida_pct / 100.0), 2)
    bp_plus_da = round(basic + ida_inr, 2)

    hra_rate_pct = get_hra_rate_pct(city_class, ida_pct, bundle["hra_rules"])
    if accommodation_type == "HRA":
        hra_inr = round(basic * (hra_rate_pct / 100.0), 2)
        hrr_recovery_inr = 0.0
    elif accommodation_type in ("LEASED", "COMPANY_QUARTERS", "TOWNSHIP"):
        hra_inr = 0.0
        hrr_recovery_inr = round(basic * (get_hrr_rate_pct(city_class, bundle["hra_rules"]) / 100.0), 2)
    else:
        hra_inr = 0.0
        hrr_recovery_inr = 0.0

    # Read caps from allowance_rules.yaml (no hardcoded numeric literals)
    rule_map = {r["allowance_code"]: r for r in bundle["allowance_rules"]["allowance_rules"]}
    caf_cap_pct = float(rule_map["CAFETERIA_PERKS"]["cap_pct_bp"])
    superann_cap_pct = float(rule_map["SUPERANNUATION_CAP"]["cap_pct_bp_plus_da"])
    cpf_rate_pct = float(rule_map["SUPERANNUATION_CAP"]["cpf_pct_bp_plus_da"])

    # Cafeteria perks: <= caf_cap_pct of Basic Pay (DPE OM 3-Aug-2017 para 9)
    caf_eff_pct = min(caf_cap_pct, round(caf_cap_pct * max(0.0, min(1.0, u_fy)), 4))
    cafeteria_allowance_inr = round(basic * (caf_eff_pct / 100.0), 2)
    caf_conveyance_inr = round(cafeteria_allowance_inr * 0.35, 2)
    caf_children_edu_inr = round(cafeteria_allowance_inr * 0.15, 2)
    caf_professional_dev_inr = round(cafeteria_allowance_inr * 0.20, 2)
    caf_other_perks_inr = round(
        cafeteria_allowance_inr - (caf_conveyance_inr + caf_children_edu_inr + caf_professional_dev_inr),
        2,
    )

    # Offshore hardship: <= 12% BP pro-rated by offshore_days / days_in_month (outside 35% ceiling)
    hardship_cap_pct = float(rule_map["HARDSHIP_OFFSHORE"]["cap_pct_bp"])
    if offshore_days > 0 and days_in_month > 0:
        offshore_frac = min(1.0, float(offshore_days) / float(days_in_month))
        hardship_offshore_inr = round(basic * (hardship_cap_pct / 100.0) * offshore_frac, 2)
    else:
        hardship_offshore_inr = 0.0

    field_duty_allowance_inr = round(basic * (field_duty_pct / 100.0), 2) if field_duty_pct > 0 else 0.0

    lca_rates = {str(k).upper(): float(v) for k, v in rule_map["LOCATION_COMP_ALLOWANCE"]["rates_pct_bp"].items()}
    lca_pct = lca_rates.get((lca_zone or "").upper(), 0.0)
    location_comp_allowance_inr = round(basic * (lca_pct / 100.0), 2) if lca_pct > 0 else 0.0

    hard_station_allowance_inr = 3500.0 if hard_station_flag else 0.0
    shift_allowance_inr = round(float(shift_allowance_inr), 2)
    night_duty_allowance_inr = round(float(night_duty_allowance_inr), 2)

    if npa_flag and not is_workman:
        npa_inr = round(min(basic * 0.20, max(0.0, 237500.0 - basic)), 2)
    else:
        npa_inr = 0.0

    special_allowance_inr = round(float(special_allowance_inr), 2)

    # Overtime: workmen only (executives = 0)
    if is_workman and overtime_hours > 0:
        ot_h = round(float(overtime_hours), 2)
        overtime_amount_inr = round(ot_h * 2.0 * bp_plus_da / 208.0, 2)
    else:
        ot_h = 0.0
        overtime_amount_inr = 0.0

    # Monthly accrual of expected PRP (not included in gross_earnings_inr, included in ctc_monthly_inr)
    prp_accrual_inr = round(basic * (prp_ceiling_pct / 100.0) * k_fy * apar_factor / 12.0, 2)
    prp_paid_inr = round(float(prp_paid_inr), 2)
    arrears_inr = round(float(arrears_inr), 2)
    leave_encashment_paid_inr = round(float(leave_encashment_paid_inr), 2)
    ltc_inr = round(float(ltc_inr), 2)
    medical_reimbursement_inr = round(float(medical_reimbursement_inr), 2)
    ex_gratia_other_inr = round(float(ex_gratia_other_inr), 2)

    gross_earnings_inr = round(
        basic
        + ida_inr
        + hra_inr
        + cafeteria_allowance_inr
        + hardship_offshore_inr
        + field_duty_allowance_inr
        + location_comp_allowance_inr
        + hard_station_allowance_inr
        + shift_allowance_inr
        + night_duty_allowance_inr
        + npa_inr
        + special_allowance_inr
        + overtime_amount_inr
        + prp_paid_inr
        + arrears_inr
        + leave_encashment_paid_inr
        + ltc_inr
        + medical_reimbursement_inr
        + ex_gratia_other_inr,
        2,
    )

    # Family G: Employer contributions & benefits (Superannuation cap <= superann_cap_pct of BP + DA)
    employer_cpf_inr = round((cpf_rate_pct / 100.0) * bp_plus_da, 2)
    employer_prmb_inr = round((prmb_rate_pct / 100.0) * bp_plus_da, 2)
    gratuity_accrual_inr = round((gratuity_rate_pct / 100.0) * bp_plus_da, 2)
    # Enforce DPE superannuation ceiling strictly
    max_superann_inr = math.floor((superann_cap_pct / 100.0) * bp_plus_da * 100.0) / 100.0
    rem_for_prbs = max(0.0, round(max_superann_inr - (employer_cpf_inr + employer_prmb_inr + gratuity_accrual_inr), 2))
    desired_prbs = round((prbs_rate_pct / 100.0) * bp_plus_da, 2)
    employer_prbs_inr = min(rem_for_prbs, desired_prbs)

    superannuation_total_inr = round(
        employer_cpf_inr + employer_prbs_inr + gratuity_accrual_inr + employer_prmb_inr,
        2,
    )
    superannuation_pct_bp_da = round((superannuation_total_inr / bp_plus_da) * 100.0, 4) if bp_plus_da > 0 else 0.0
    superannuation_cap_ok = superannuation_pct_bp_da <= (superann_cap_pct + 0.0001)

    csss_contribution_inr = round(float(csss_contribution_inr), 2)
    leave_provision_accrual_inr = round(float(leave_provision_accrual_inr), 2)
    medical_scheme_cost_inr = round(float(medical_scheme_cost_inr), 2)
    group_insurance_premium_inr = round(float(group_insurance_premium_inr), 2)
    accident_insurance_premium_inr = round(float(accident_insurance_premium_inr), 2)
    housing_cost_inr = round(float(housing_cost_inr), 2)
    canteen_subsidy_inr = round(float(canteen_subsidy_inr), 2)
    transport_subsidy_inr = round(float(transport_subsidy_inr), 2)
    staff_welfare_alloc_inr = round(float(staff_welfare_alloc_inr), 2)
    training_cost_inr = round(float(training_cost_inr), 2)

    employer_cost_noncash_inr = round(
        superannuation_total_inr
        + csss_contribution_inr
        + leave_provision_accrual_inr
        + medical_scheme_cost_inr
        + group_insurance_premium_inr
        + accident_insurance_premium_inr
        + housing_cost_inr
        + canteen_subsidy_inr
        + transport_subsidy_inr
        + staff_welfare_alloc_inr
        + training_cost_inr,
        2,
    )

    # Family H: Deductions & net pay
    employee_pf_inr = employer_cpf_inr
    vpf_inr = round((vpf_rate_pct / 100.0) * bp_plus_da, 2) if vpf_rate_pct > 0 else 0.0
    # Simplified progressive monthly TDS on taxable gross (gross - PF - standard deduction ₹6,250/mo)
    taxable_mo = max(0.0, gross_earnings_inr - employee_pf_inr - 6250.0)
    if taxable_mo <= 60000.0:
        tds_inr = round(max(0.0, (taxable_mo - 30000.0) * 0.05), 2)
    elif taxable_mo <= 125000.0:
        tds_inr = round(1500.0 + (taxable_mo - 60000.0) * 0.15, 2)
    else:
        tds_inr = round(11250.0 + (taxable_mo - 125000.0) * 0.25, 2)

    professional_tax_inr = round(float(professional_tax_inr), 2)
    loan_recoveries_inr = round(float(loan_recoveries_inr), 2)
    other_recoveries_inr = round(float(other_recoveries_inr), 2)

    total_deductions_inr = round(
        employee_pf_inr
        + vpf_inr
        + tds_inr
        + professional_tax_inr
        + hrr_recovery_inr
        + loan_recoveries_inr
        + other_recoveries_inr,
        2,
    )
    net_pay_inr = round(gross_earnings_inr - total_deductions_inr, 2)

    # Family I: CTC, accounting cost, capitalisation
    ctc_monthly_inr = round(
        gross_earnings_inr
        - arrears_inr
        - leave_encashment_paid_inr
        + prp_accrual_inr
        - prp_paid_inr
        + employer_cost_noncash_inr,
        2,
    )
    ctc_annualised_inr = round(ctc_monthly_inr * 12.0, 2)

    cost_note35_a_inr = gross_earnings_inr
    cost_note35_b_inr = round(employer_cpf_inr + employer_prbs_inr + csss_contribution_inr, 2)
    cost_note35_c_inr = gratuity_accrual_inr
    cost_note35_d_inr = leave_provision_accrual_inr
    cost_note35_e_inr = employer_prmb_inr
    cost_note35_f_inr = round(
        medical_scheme_cost_inr
        + group_insurance_premium_inr
        + accident_insurance_premium_inr
        + housing_cost_inr
        + canteen_subsidy_inr
        + transport_subsidy_inr
        + staff_welfare_alloc_inr
        + training_cost_inr,
        2,
    )
    cost_total_inr = round(
        cost_note35_a_inr
        + cost_note35_b_inr
        + cost_note35_c_inr
        + cost_note35_d_inr
        + cost_note35_e_inr
        + cost_note35_f_inr,
        2,
    )

    cap_share = round(max(0.0, min(1.0, float(capitalised_share))), 4)
    cost_capitalised_inr = round(cost_total_inr * cap_share, 2)
    cost_expensed_inr = round(cost_total_inr - cost_capitalised_inr, 2)

    prod_sh, gae_sh, exp_sh = expensed_dest_shares
    cost_expensed_production_inr = round(cost_expensed_inr * prod_sh, 2)
    cost_expensed_exploration_inr = round(cost_expensed_inr * exp_sh, 2)
    cost_expensed_gae_inr = round(
        cost_expensed_inr - cost_expensed_production_inr - cost_expensed_exploration_inr,
        2,
    )

    return {
        "pay_scale_version": pay_scale_version,
        "pay_scale_min_inr": scale_min,
        "pay_scale_max_inr": scale_max,
        "increments_count": int(increments_count),
        "stagnation_increments": int(stagnation_increments),
        "ida_pct": ida_pct,
        "ida_status": ida_status,
        "hra_rate_pct": hra_rate_pct,
        "accommodation_type": accommodation_type,
        "basic_pay_inr": basic,
        "ida_inr": ida_inr,
        "hra_inr": hra_inr,
        "cafeteria_allowance_inr": cafeteria_allowance_inr,
        "caf_conveyance_inr": caf_conveyance_inr,
        "caf_children_edu_inr": caf_children_edu_inr,
        "caf_professional_dev_inr": caf_professional_dev_inr,
        "caf_other_perks_inr": caf_other_perks_inr,
        "hardship_offshore_inr": hardship_offshore_inr,
        "field_duty_allowance_inr": field_duty_allowance_inr,
        "location_comp_allowance_inr": location_comp_allowance_inr,
        "hard_station_allowance_inr": hard_station_allowance_inr,
        "shift_allowance_inr": shift_allowance_inr,
        "night_duty_allowance_inr": night_duty_allowance_inr,
        "npa_inr": npa_inr,
        "special_allowance_inr": special_allowance_inr,
        "overtime_hours": ot_h,
        "overtime_amount_inr": overtime_amount_inr,
        "prp_accrual_inr": prp_accrual_inr,
        "prp_paid_inr": prp_paid_inr,
        "arrears_inr": arrears_inr,
        "leave_encashment_paid_inr": leave_encashment_paid_inr,
        "ltc_inr": ltc_inr,
        "medical_reimbursement_inr": medical_reimbursement_inr,
        "ex_gratia_other_inr": ex_gratia_other_inr,
        "gross_earnings_inr": gross_earnings_inr,
        "employer_cpf_inr": employer_cpf_inr,
        "employer_prbs_inr": employer_prbs_inr,
        "gratuity_accrual_inr": gratuity_accrual_inr,
        "employer_prmb_inr": employer_prmb_inr,
        "csss_contribution_inr": csss_contribution_inr,
        "superannuation_total_inr": superannuation_total_inr,
        "superannuation_pct_bp_da": superannuation_pct_bp_da,
        "superannuation_cap_ok": superannuation_cap_ok,
        "leave_provision_accrual_inr": leave_provision_accrual_inr,
        "medical_scheme_cost_inr": medical_scheme_cost_inr,
        "group_insurance_premium_inr": group_insurance_premium_inr,
        "accident_insurance_premium_inr": accident_insurance_premium_inr,
        "housing_cost_inr": housing_cost_inr,
        "canteen_subsidy_inr": canteen_subsidy_inr,
        "transport_subsidy_inr": transport_subsidy_inr,
        "staff_welfare_alloc_inr": staff_welfare_alloc_inr,
        "training_cost_inr": training_cost_inr,
        "employer_cost_noncash_inr": employer_cost_noncash_inr,
        "employee_pf_inr": employee_pf_inr,
        "vpf_inr": vpf_inr,
        "tds_inr": tds_inr,
        "professional_tax_inr": professional_tax_inr,
        "hrr_recovery_inr": hrr_recovery_inr,
        "loan_recoveries_inr": loan_recoveries_inr,
        "other_recoveries_inr": other_recoveries_inr,
        "total_deductions_inr": total_deductions_inr,
        "net_pay_inr": net_pay_inr,
        "ctc_monthly_inr": ctc_monthly_inr,
        "ctc_annualised_inr": ctc_annualised_inr,
        "cost_note35_a_inr": cost_note35_a_inr,
        "cost_note35_b_inr": cost_note35_b_inr,
        "cost_note35_c_inr": cost_note35_c_inr,
        "cost_note35_d_inr": cost_note35_d_inr,
        "cost_note35_e_inr": cost_note35_e_inr,
        "cost_note35_f_inr": cost_note35_f_inr,
        "cost_total_inr": cost_total_inr,
        "capitalised_share": cap_share,
        "cost_capitalised_inr": cost_capitalised_inr,
        "cost_expensed_inr": cost_expensed_inr,
        "cost_expensed_production_inr": cost_expensed_production_inr,
        "cost_expensed_gae_inr": cost_expensed_gae_inr,
        "cost_expensed_exploration_inr": cost_expensed_exploration_inr,
    }
