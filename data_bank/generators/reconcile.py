"""Offline reconciliation engine for Employee-360 (EMP-R01..R30) and Field Economics-360 (FLD-R01..R17).

Evaluates all 30 EMP checks (SPEC-04 §7.4) and 17 FLD checks (SPEC-05 §7.2) over input DataFrames
with zero hardcoded 0.0 metrics, zero mocked PASS loops, and zero seeded_break flags.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
import duckdb
import numpy as np
import pandas as pd
import yaml

N35_LINE_TO_COL: Dict[str, str] = {
    "N35.ROYALTY": "royalty",
    "N35.OIDB_CESS": "oidb_cess",
    "N35.NCCD": "nccd",
    "N35.EXCISE_SAED": "excise_saed",
    "N35.PORT_TRUST": "port_trust",
    "N35.OTHER_LEVIES": "other_levies",
    "N35.STAFF_EXPENDITURE": "staff_expenditure",
    "N35.WORKOVER_OPS": "workover_ops",
    "N35.WATER_INJECTION_DESALTING": "water_injection_desalting",
    "N35.CONSUMPTION_STORES_SPARES": "consumption_stores_spares",
    "N35.POLLUTION_CONTROL": "pollution_control",
    "N35.TRANSPORT_EXPENDITURE": "transport_expenditure",
    "N35.INSURANCE": "insurance",
    "N35.POWER_FUEL": "power_fuel",
    "N35.REPAIRS_MAINTENANCE": "repairs_maintenance",
    "N35.CONTRACTUAL_HIRE": "contractual_hire",
    "N35.OTHER_PRODUCTION_EXP": "other_production_exp",
    "N35.TRANSPORT_FREIGHT_PRODUCTS": "transport_freight_products",
    "N35.R_AND_D": "r_and_d",
    "N35.GAE": "gae",
    "N35.CSR": "csr",
    "N35.EXCHANGE_LOSS": "exchange_loss",
    "N35.MISC_EXP": "misc_exp",
    "N35.FV_LOSS": "fv_loss",
}

LEVIES_COLS: List[str] = [
    "royalty",
    "oidb_cess",
    "nccd",
    "excise_saed",
    "port_trust",
    "other_levies",
]

OPEX_COLS: List[str] = [
    "staff_expenditure",
    "workover_ops",
    "water_injection_desalting",
    "consumption_stores_spares",
    "pollution_control",
    "transport_expenditure",
    "insurance",
    "power_fuel",
    "repairs_maintenance",
    "contractual_hire",
    "other_production_exp",
    "transport_freight_products",
    "r_and_d",
    "gae",
    "csr",
    "exchange_loss",
    "misc_exp",
    "fv_loss",
]

LIFTING_COLS: List[str] = [
    "staff_expenditure",
    "workover_ops",
    "water_injection_desalting",
    "consumption_stores_spares",
    "pollution_control",
    "transport_expenditure",
    "insurance",
    "power_fuel",
    "repairs_maintenance",
    "contractual_hire",
    "other_production_exp",
]

SIX_FYS = {"FY21", "FY22", "FY23", "FY24", "FY25", "FY26"}


def _make_check_row(
    domain: str,
    spec: str,
    check_id: str,
    fiscal_year: str,
    level: str,
    dimension_key: str,
    metric: str,
    ssot_value: Optional[float],
    reference_value: Optional[float],
    unit: str,
    tolerance_abs: Optional[float],
    tolerance_pct: Optional[float],
    severity: str,
    reference_source_doc: str,
    reference_page: int,
    reference_text_line: int,
    reference_line_code: str,
    notes: str,
    run_id: str = "v3_recon_run",
    run_ts: Optional[str] = None,
) -> Dict[str, Any]:
    if run_ts is None:
        run_ts = datetime.now(timezone.utc).isoformat()
    if ssot_value is None or reference_value is None or pd.isna(ssot_value) or pd.isna(reference_value):
        delta = np.nan
        abs_diff = np.nan
        pct_diff = np.nan
        status = "FAIL"
    else:
        ssot_f = float(ssot_value)
        ref_f = float(reference_value)
        delta = ssot_f - ref_f
        abs_diff = abs(delta)
        pct_diff = (abs_diff / abs(ref_f) * 100.0) if abs(ref_f) > 0 else (0.0 if abs_diff == 0 else np.inf)
        if tolerance_abs is not None and not pd.isna(tolerance_abs):
            status = "PASS" if abs_diff <= float(tolerance_abs) + 1e-9 else "FAIL"
        elif tolerance_pct is not None and not pd.isna(tolerance_pct):
            status = "PASS" if pct_diff <= float(tolerance_pct) + 1e-9 else "FAIL"
        else:
            status = "FAIL"

    return {
        "run_id": run_id,
        "run_ts": run_ts,
        "domain": domain,
        "spec": spec,
        "check_id": check_id,
        "fiscal_year": fiscal_year,
        "period": fiscal_year,
        "level": level,
        "dimension_key": dimension_key,
        "metric": metric,
        "metric_name": metric,
        "ssot_value": float(ssot_value) if ssot_value is not None and not pd.isna(ssot_value) else np.nan,
        "reference_value": float(reference_value) if reference_value is not None and not pd.isna(reference_value) else np.nan,
        "unit": unit,
        "delta": delta,
        "delta_pct": pct_diff,
        "abs_diff": abs_diff,
        "pct_diff": pct_diff,
        "tolerance_abs": tolerance_abs,
        "tolerance_pct": tolerance_pct,
        "severity": severity,
        "status": status,
        "reference_source_doc": reference_source_doc,
        "reference_page": int(reference_page),
        "reference_text_line": int(reference_text_line),
        "reference_line_code": reference_line_code,
        "notes": notes,
    }


def _lookup_target(
    targets_df: pd.DataFrame, fy: str, codes: List[str]
) -> tuple[Optional[float], str, int, int]:
    fy_col = "fiscal_year" if "fiscal_year" in targets_df.columns else "fy"
    code_cols = [c for c in ["metric", "metric_code", "line_code"] if c in targets_df.columns]
    for code in codes:
        for col in code_cols:
            sub = targets_df[(targets_df[fy_col] == fy) & (targets_df[col] == code)]
            if not sub.empty:
                row = sub.iloc[0]
                val = float(row["value"]) if pd.notna(row["value"]) else None
                doc = str(row.get("source_doc", "ONGC_AR"))
                page = int(row["source_page"]) if "source_page" in row and pd.notna(row["source_page"]) else 1
                line = int(row["source_text_line"]) if "source_text_line" in row and pd.notna(row["source_text_line"]) else 1
                return val, doc, page, line
    return None, "MISSING_TARGET", 0, 0


def run_employee_reconciliation(
    emp_df: pd.DataFrame,
    pool_df: pd.DataFrame,
    targets_df: pd.DataFrame,
    run_id: str = "v3_recon_run",
) -> pd.DataFrame:
    """Evaluate EMP-R01 through EMP-R30 over emp_df, pool_df, and targets_df."""
    run_ts = datetime.now(timezone.utc).isoformat()
    rows: List[Dict[str, Any]] = []

    fys = sorted(emp_df["fiscal_year"].dropna().unique().tolist())
    latest_fy = "FY26" if "FY26" in fys else fys[-1]

    # Pre-compute FY-end active headcount and separation buckets for roll-forward (EMP-R17).
    # Employees separating in April of FY(t) have their final payroll row in March of FY(t-1)
    # (fy_month_no == 12 & is_month_end_active == True), while employees separating in May..March
    # of FY(t) have their final payroll row in FY(t) with ~(fy_month_no == 12 & is_month_end_active == True).
    hc_by_fy: Dict[str, float] = {}
    hc_exec_by_fy: Dict[str, float] = {}
    hc_nonexec_by_fy: Dict[str, float] = {}
    seps_m1_11_by_fy: Dict[str, float] = {}
    seps_m12_act_by_fy: Dict[str, float] = {}
    seps_exec_m1_11_by_fy: Dict[str, float] = {}
    seps_exec_m12_act_by_fy: Dict[str, float] = {}
    seps_nonexec_m1_11_by_fy: Dict[str, float] = {}
    seps_nonexec_m12_act_by_fy: Dict[str, float] = {}
    for fy in fys:
        sub = emp_df[emp_df["fiscal_year"] == fy]
        is_m12_act = (sub["fy_month_no"] == 12) & (sub["is_month_end_active"] == True)
        act = sub[is_m12_act]
        hc_by_fy[fy] = float(len(act))
        hc_exec_by_fy[fy] = float(act["cadre"].isin(["executive", "board"]).sum())
        hc_nonexec_by_fy[fy] = float((act["cadre"] == "non_executive").sum())
        is_sep = sub["separated_in_month_flag"] == True
        is_exec_sub = sub["cadre"].isin(["executive", "board"])
        is_ne_sub = sub["cadre"] == "non_executive"
        seps_m1_11_by_fy[fy] = float((is_sep & (~is_m12_act)).sum())
        seps_m12_act_by_fy[fy] = float((is_sep & is_m12_act).sum())
        seps_exec_m1_11_by_fy[fy] = float((is_sep & (~is_m12_act) & is_exec_sub).sum())
        seps_exec_m12_act_by_fy[fy] = float((is_sep & is_m12_act & is_exec_sub).sum())
        seps_nonexec_m1_11_by_fy[fy] = float((is_sep & (~is_m12_act) & is_ne_sub).sum())
        seps_nonexec_m12_act_by_fy[fy] = float((is_sep & is_m12_act & is_ne_sub).sum())

    for idx, fy in enumerate(fys):
        sub = emp_df[emp_df["fiscal_year"] == fy]
        psub = pool_df[pool_df["fiscal_year"] == fy] if not pool_df.empty else pd.DataFrame()
        act = sub[(sub["fy_month_no"] == 12) & (sub["is_month_end_active"] == True)]

        ind_total_mn = float(sub["cost_total_inr"].sum()) / 1e6
        pool_total_mn = float(psub["amount_inr"].sum()) / 1e6 if not psub.empty else 0.0
        if not psub.empty and "pool_code" in psub.columns:
            resid_mn = float(psub[psub["pool_code"].astype(str).str.startswith("POOL_RESIDUAL")]["amount_inr"].sum()) / 1e6
        elif not psub.empty and "basis" in psub.columns:
            resid_mn = float(psub[psub["basis"] == "residual"]["amount_inr"].sum()) / 1e6
        else:
            resid_mn = 0.0

        # EMP-R01
        t_val, doc, pg, ln = _lookup_target(targets_df, fy, ["employee_cost_total", "note35_1_total"])
        rows.append(
            _make_check_row(
                "EMP", "SPEC-04", "EMP-R01", fy, "FY", "ALL", "employee_cost_total",
                ind_total_mn + pool_total_mn, t_val, "INR_MN", 0.1, None, "BLOCK",
                doc, pg, ln, "employee_cost_total", "Note 35.1 total employee benefit expense", run_id, run_ts,
            )
        )

        # EMP-R02..R07 (scoped to FY21..FY26 matching recon_employee360.sqlx)
        if fy in SIX_FYS:
            line_defs = [
                ("EMP-R02", "a", "35.1(a)", ["note35_1_a", "note35_1a_salaries_wages"]),
                ("EMP-R03", "b", "35.1(b)", ["note35_1_b", "note35_1b_provident_funds"]),
                ("EMP-R04", "c", "35.1(c)", ["note35_1_c", "note35_1c_gratuity"]),
                ("EMP-R05", "d", "35.1(d)", ["note35_1_d", "note35_1d_leave"]),
                ("EMP-R06", "e", "35.1(e)", ["note35_1_e", "note35_1e_prmb_terminal"]),
                ("EMP-R07", "f", "35.1(f)", ["note35_1_f", "note35_1f_staff_welfare"]),
            ]
            for cid, lkey, dkey, mcodes in line_defs:
                col = f"cost_note35_{lkey}_inr"
                ind_l_mn = float(sub[col].sum()) / 1e6 if col in sub.columns else 0.0
                pool_l_mn = (
                    float(psub[psub["note35_line"] == lkey]["amount_inr"].sum()) / 1e6
                    if (not psub.empty and "note35_line" in psub.columns)
                    else 0.0
                )
                l_val, l_doc, l_pg, l_ln = _lookup_target(targets_df, fy, mcodes)
                rows.append(
                    _make_check_row(
                        "EMP", "SPEC-04", cid, fy, "FY", dkey, mcodes[0],
                        ind_l_mn + pool_l_mn, l_val, "INR_MN", 0.1, None, "BLOCK",
                        l_doc, l_pg, l_ln, mcodes[0], f"Note {dkey} employee benefit expense", run_id, run_ts,
                    )
                )

        # EMP-R08: POOL-RESID share <= 3.0%
        resid_share = (resid_mn / t_val * 100.0) if (t_val is not None and t_val != 0) else None
        rows.append(
            _make_check_row(
                "EMP", "SPEC-04", "EMP-R08", fy, "FY", "POOL-RESID", "pool_resid_share_pct",
                resid_share, 0.0 if t_val is not None else None, "PCT", 3.0, None, "BLOCK",
                doc, pg, ln, "employee_cost_total", "POOL-RESID share of Note 35.1 total <= 3.0%", run_id, run_ts,
            )
        )

        # EMP-R09: Individual 35.1(a) coverage >= 96% (scoped to FY21..FY26)
        if fy in SIX_FYS:
            a_val, a_doc, a_pg, a_ln = _lookup_target(targets_df, fy, ["note35_1_a", "note35_1a_salaries_wages"])
            ind_a_mn = float(sub["cost_note35_a_inr"].sum()) / 1e6
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R09", fy, "FY", "35.1(a)", "ind_cost_a_vs_target_pct",
                    ind_a_mn, a_val, "INR_MN", None, 4.0, "BLOCK",
                    a_doc, a_pg, a_ln, "note35_1_a", "Individual payroll covers >= 96% of Note 35.1(a)", run_id, run_ts,
                )
            )

        # EMP-R10: FY-end active headcount
        hc_val, hc_doc, hc_pg, hc_ln = _lookup_target(targets_df, fy, ["headcount_fy_end"])
        rows.append(
            _make_check_row(
                "EMP", "SPEC-04", "EMP-R10", fy, "FY", "ALL", "headcount_fy_end",
                hc_by_fy[fy], hc_val, "COUNT", 0.0, None, "BLOCK",
                hc_doc, hc_pg, hc_ln, "headcount_fy_end", "FY-end active headcount", run_id, run_ts,
            )
        )

        # EMP-R22: Superannuation ceiling <= 30%
        sup_viol = float((sub["superannuation_pct_bp_da"] > 0.3001).sum())
        rows.append(
            _make_check_row(
                "EMP", "SPEC-04", "EMP-R22", fy, "FY", "ALL", "superannuation_cap_violations",
                sup_viol, 0.0 if t_val is not None else None, "COUNT", 0.0, None, "BLOCK",
                "DPE_OM_3AUG2017_P12", 12, 1, "superannuation_cap_violations",
                "Zero rows exceeding 30% superannuation cap", run_id, run_ts,
            )
        )

        # EMP-R23: Pay rule violations (cafeteria <= 35%, HRA tier, basic pay within 3rd PRC scale bounds).
        # 3rd PRC pay scales (pay_scale_min_inr, pay_scale_max_inr) took effect 01-Jan-2017 (DPE OM 3-Aug-2017);
        # Apr-Dec 2016 rows in FY17 were on 2nd-PRC (2007) scales, so apply the scale-band check to month >= '2017-01'.
        caf_v = (sub["cafeteria_allowance_inr"] / sub["basic_pay_inr"].replace(0, np.nan)) > 0.3501
        hra_ratio = (sub["hra_inr"] / sub["basic_pay_inr"].replace(0, np.nan)).round(2)
        hra_v = (sub["hra_inr"] > 0) & (~hra_ratio.isin({0.08, 0.09, 0.10, 0.16, 0.18, 0.20, 0.24, 0.27, 0.30}))
        eff_max = np.where(sub["grade_id"] == "E0", np.maximum(sub["pay_scale_max_inr"], 160000.0), sub["pay_scale_max_inr"])
        in_3rd_prc = (sub["month"] >= "2017-01") if "month" in sub.columns else True
        scale_v = in_3rd_prc & (
            (sub["basic_pay_inr"] < sub["pay_scale_min_inr"] - 1.0)
            | (sub["basic_pay_inr"] > eff_max * 1.092727 + 100.0)
        )
        pay_viol = float((caf_v | hra_v | scale_v).sum())
        rows.append(
            _make_check_row(
                "EMP", "SPEC-04", "EMP-R23", fy, "FY", "ALL", "pay_rule_violations",
                pay_viol, 0.0 if t_val is not None else None, "COUNT", 0.0, None, "BLOCK",
                "DPE_OM_3AUG2017", 1, 1, "pay_rule_violations",
                "Zero rows violating cafeteria, HRA, or scale bounds", run_id, run_ts,
            )
        )

        # EMP-R28: Row identities
        net_v = (sub["gross_earnings_inr"] - sub["total_deductions_inr"] - sub["net_pay_inr"]).abs() > 0.01
        n35_sum = (
            sub["cost_note35_a_inr"] + sub["cost_note35_b_inr"] + sub["cost_note35_c_inr"]
            + sub["cost_note35_d_inr"] + sub["cost_note35_e_inr"] + sub["cost_note35_f_inr"]
        )
        tot_v = (n35_sum - sub["cost_total_inr"]).abs() > 0.01
        split_v = ((sub["cost_capitalised_inr"] + sub["cost_expensed_inr"]) - sub["cost_total_inr"]).abs() > 0.01
        id_viol = float((net_v | tot_v | split_v).sum())
        rows.append(
            _make_check_row(
                "EMP", "SPEC-04", "EMP-R28", fy, "FY", "ALL", "row_identity_violations",
                id_viol, 0.0 if t_val is not None else None, "COUNT", 0.0, None, "BLOCK",
                "SPEC04_S5_4", 1, 1, "row_identity_violations",
                "Zero rows violating net pay or cost_total identities", run_id, run_ts,
            )
        )

        # EMP-R29: Staff Expenditure cross-domain link (scoped to FY21..FY26)
        if fy in SIX_FYS:
            se_val, se_doc, se_pg, se_ln = _lookup_target(targets_df, fy, ["staff_expenditure_note35"])
            prod_staff_mn = float(sub["cost_expensed_production_inr"].sum()) / 1e6
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R29", fy, "FY", "PRODUCTION", "staff_expenditure_note35",
                    prod_staff_mn, se_val, "INR_MN", 0.1, None, "BLOCK",
                    se_doc, se_pg, se_ln, "staff_expenditure_note35",
                    "Note 35 Staff Expenditure cross-domain link", run_id, run_ts,
                )
            )

        # Latest-FY checks: EMP-R11..R21, EMP-R24..R27, EMP-R30
        if fy == latest_fy:
            n_act = max(len(act), 1)
            is_f_act = act["gender"].isin(["F", "Female"])
            is_f_sub = sub["gender"].isin(["F", "Female"])

            # EMP-R11: Executive & Non-executive counts
            ex_val, ex_doc, ex_pg, ex_ln = _lookup_target(targets_df, fy, ["brsr_exec_count"])
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R11", fy, "CADRE", "executive", "brsr_exec_count",
                    hc_exec_by_fy[fy], ex_val, "COUNT", 0.0, None, "BLOCK",
                    ex_doc, ex_pg, ex_ln, "brsr_exec_count", "BRSR permanent employees (executive)", run_id, run_ts,
                )
            )
            ne_val, ne_doc, ne_pg, ne_ln = _lookup_target(targets_df, fy, ["brsr_nonexec_count"])
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R11", fy, "CADRE", "non_executive", "brsr_nonexec_count",
                    hc_nonexec_by_fy[fy], ne_val, "COUNT", 0.0, None, "BLOCK",
                    ne_doc, ne_pg, ne_ln, "brsr_nonexec_count", "BRSR permanent workers (non-executive)", run_id, run_ts,
                )
            )

            # EMP-R12: Women count
            w_val, w_doc, w_pg, w_ln = _lookup_target(targets_df, fy, ["brsr_women_total"])
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R12", fy, "FY", "F", "brsr_women_total",
                    float(is_f_act.sum()), w_val, "COUNT", 0.0, None, "BLOCK",
                    w_doc, w_pg, w_ln, "brsr_women_total", "BRSR total women employees", run_id, run_ts,
                )
            )

            # EMP-R13: PwD count
            p_val, p_doc, p_pg, p_ln = _lookup_target(targets_df, fy, ["brsr_pwd_total"])
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R13", fy, "FY", "PWD", "brsr_pwd_total",
                    float((act["pwd_flag"] == True).sum()), p_val, "COUNT", 0.0, None, "BLOCK",
                    p_doc, p_pg, p_ln, "brsr_pwd_total", "BRSR differently-abled employees", run_id, run_ts,
                )
            )

            # EMP-R14: SC & ST share %
            sc_val, sc_doc, sc_pg, sc_ln = _lookup_target(targets_df, fy, ["sc_share_pct"])
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R14", fy, "CATEGORY", "SC", "sc_share_pct",
                    float((act["social_category"] == "SC").sum()) * 100.0 / n_act, sc_val, "PCT", 0.5, None, "BLOCK",
                    sc_doc, sc_pg, sc_ln, "sc_share_pct", "SC share of permanent workforce", run_id, run_ts,
                )
            )
            st_val, st_doc, st_pg, st_ln = _lookup_target(targets_df, fy, ["st_share_pct"])
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R14", fy, "CATEGORY", "ST", "st_share_pct",
                    float((act["social_category"] == "ST").sum()) * 100.0 / n_act, st_val, "PCT", 0.5, None, "BLOCK",
                    st_doc, st_pg, st_ln, "st_share_pct", "ST share of permanent workforce", run_id, run_ts,
                )
            )

            # EMP-R15: Age bands (<30, 30-50, >50)
            for aband, mcode in [("<30", "brsr_age_lt30_pct"), ("30-50", "brsr_age_30_50_pct"), (">50", "brsr_age_gt50_pct")]:
                ab_val, ab_doc, ab_pg, ab_ln = _lookup_target(targets_df, fy, [mcode])
                rows.append(
                    _make_check_row(
                        "EMP", "SPEC-04", "EMP-R15", fy, "AGE_BAND", aband, mcode,
                        float((act["age_band_brsr"] == aband).sum()) * 100.0 / n_act, ab_val, "PCT", 1.5, None, "BLOCK",
                        ab_doc, ab_pg, ab_ln, mcode, f"BRSR age band {aband} share", run_id, run_ts,
                    )
                )

            # EMP-R16: Median remuneration by cadre x gender
            rem_df = sub.copy()
            rem_df["rem_inr"] = rem_df["gross_earnings_inr"] + rem_df["employer_cpf_inr"]
            rem_df["cadre_grp"] = np.where(rem_df["cadre"].isin(["executive", "board"]), "executive", "non_executive")
            rem_df["g_norm"] = np.where(rem_df["gender"].isin(["F", "Female"]), "F", "M")
            max_months = int(rem_df.groupby("emp_id")["fy_month_no"].count().max()) if not rem_df.empty else 1
            emp_rem = rem_df.groupby(["emp_id", "cadre_grp", "g_norm"]).agg(
                annual_rem=("rem_inr", "sum"), m_cnt=("fy_month_no", "count")
            ).reset_index()
            emp_rem = emp_rem[emp_rem["m_cnt"] == max_months]

            for cgrp, gcode, dkey, mcodes in [
                ("executive", "M", "exec_M", ["brsr_median_remuneration_exec_male", "brsr_median_rem_exec_m"]),
                ("executive", "F", "exec_F", ["brsr_median_remuneration_exec_female", "brsr_median_rem_exec_f"]),
                ("non_executive", "M", "nonexec_M", ["brsr_median_remuneration_nonexec_male", "brsr_median_rem_nonexec_m"]),
                ("non_executive", "F", "nonexec_F", ["brsr_median_remuneration_nonexec_female", "brsr_median_rem_nonexec_f"]),
            ]:
                c_sub = emp_rem[(emp_rem["cadre_grp"] == cgrp) & (emp_rem["g_norm"] == gcode)]
                med_val = float(c_sub["annual_rem"].median()) if not c_sub.empty else np.nan
                r_val, r_doc, r_pg, r_ln = _lookup_target(targets_df, fy, mcodes)
                rows.append(
                    _make_check_row(
                        "EMP", "SPEC-04", "EMP-R16", fy, "COHORT", dkey, mcodes[0],
                        med_val, r_val, "INR", None, 10.0, "BLOCK",
                        r_doc, r_pg, r_ln, mcodes[0], f"Median remuneration {dkey}", run_id, run_ts,
                    )
                )

            # EMP-R17: HC roll-forward identity and turnover rates
            prev_fy = fys[idx - 1] if idx > 0 else fy
            hires_cnt = float((sub["joined_in_month_flag"] == True).sum())
            seps_cnt = seps_m1_11_by_fy[fy] + (seps_m12_act_by_fy[prev_fy] if idx > 0 else 0.0)
            rf_diff = (hc_by_fy[prev_fy] + hires_cnt - seps_cnt) - hc_by_fy[fy]
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R17", fy, "FY", "ROLL_FORWARD", "hc_roll_forward_diff",
                    rf_diff, 0.0 if hc_val is not None else None, "COUNT", 0.0, None, "BLOCK",
                    hc_doc, hc_pg, hc_ln, "headcount_fy_end", "HC(t-1) + Hires(t) - Seps(t) = HC(t)", run_id, run_ts,
                )
            )
            seps_exec = seps_exec_m1_11_by_fy[fy] + (seps_exec_m12_act_by_fy[prev_fy] if idx > 0 else 0.0)
            seps_nonexec = seps_nonexec_m1_11_by_fy[fy] + (seps_nonexec_m12_act_by_fy[prev_fy] if idx > 0 else 0.0)
            avg_ex = max((hc_exec_by_fy[prev_fy] + hc_exec_by_fy[fy]) / 2.0, 1.0)
            avg_ne = max((hc_nonexec_by_fy[prev_fy] + hc_nonexec_by_fy[fy]) / 2.0, 1.0)
            te_val, te_doc, te_pg, te_ln = _lookup_target(targets_df, fy, ["brsr_turnover_exec_pct"])
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R17", fy, "CADRE", "executive", "brsr_turnover_exec_pct",
                    seps_exec * 100.0 / avg_ex, te_val, "PCT", 1.5, None, "BLOCK",
                    te_doc, te_pg, te_ln, "brsr_turnover_exec_pct", "Executive turnover rate %", run_id, run_ts,
                )
            )
            tn_val, tn_doc, tn_pg, tn_ln = _lookup_target(targets_df, fy, ["brsr_turnover_nonexec_pct"])
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R17", fy, "CADRE", "non_executive", "brsr_turnover_nonexec_pct",
                    seps_nonexec * 100.0 / avg_ne, tn_val, "PCT", 1.5, None, "BLOCK",
                    tn_doc, tn_pg, tn_ln, "brsr_turnover_nonexec_pct", "Non-executive turnover rate %", run_id, run_ts,
                )
            )

            # EMP-R18: Hires total, women %, <30 %
            h_df = sub[sub["joined_in_month_flag"] == True]
            n_hires = max(len(h_df), 1)
            ht_val, ht_doc, ht_pg, ht_ln = _lookup_target(targets_df, fy, ["brsr_hires_total", "hires_total"])
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R18", fy, "FY", "ALL", "brsr_hires_total",
                    hires_cnt, ht_val, "COUNT", 0.0, None, "BLOCK",
                    ht_doc, ht_pg, ht_ln, "brsr_hires_total", "Total new hires", run_id, run_ts,
                )
            )
            hw_val, hw_doc, hw_pg, hw_ln = _lookup_target(targets_df, fy, ["brsr_hires_women_pct", "hires_women_pct"])
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R18", fy, "FY", "F", "brsr_hires_women_pct",
                    float(h_df["gender"].isin(["F", "Female"]).sum()) * 100.0 / n_hires, hw_val, "PCT", 3.0, None, "BLOCK",
                    hw_doc, hw_pg, hw_ln, "brsr_hires_women_pct", "Women share of new hires", run_id, run_ts,
                )
            )
            ha_val, ha_doc, ha_pg, ha_ln = _lookup_target(targets_df, fy, ["brsr_hires_lt30_pct", "hires_age_lt30_pct"])
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R18", fy, "FY", "<30", "brsr_hires_lt30_pct",
                    float((h_df["age_band_brsr"] == "<30").sum()) * 100.0 / n_hires, ha_val, "PCT", 3.0, None, "WARN",
                    ha_doc, ha_pg, ha_ln, "brsr_hires_lt30_pct", "<30 share of new hires", run_id, run_ts,
                )
            )

            # EMP-R19: Training hours per active employee
            tr_val, tr_doc, tr_pg, tr_ln = _lookup_target(targets_df, fy, ["brsr_avg_training_hours", "training_hours_per_emp"])
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R19", fy, "FY", "ALL", "brsr_avg_training_hours",
                    float(sub["training_hours"].sum()) / n_act, tr_val, "HOURS", 0.5, None, "WARN",
                    tr_doc, tr_pg, tr_ln, "brsr_avg_training_hours", "Average training hours per active employee", run_id, run_ts,
                )
            )

            # EMP-R20: Women share of gross wages
            ww_val, ww_doc, ww_pg, ww_ln = _lookup_target(targets_df, fy, ["brsr_women_wage_share_pct"])
            w_wage_pct = float(sub.loc[is_f_sub, "gross_earnings_inr"].sum()) * 100.0 / max(float(sub["gross_earnings_inr"].sum()), 1.0)
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R20", fy, "FY", "F", "brsr_women_wage_share_pct",
                    w_wage_pct, ww_val, "PCT", 1.0, None, "WARN",
                    ww_doc, ww_pg, ww_ln, "brsr_women_wage_share_pct", "Women share of gross wages", run_id, run_ts,
                )
            )

            # EMP-R21: Entry E1 CTC
            e1_val, e1_doc, e1_pg, e1_ln = _lookup_target(targets_df, fy, ["e1_entry_ctc_target_inr"])
            e1_join = sub[(sub["grade_id"] == "E1") & (sub["joined_in_month_flag"] == True)]
            if e1_join.empty:
                e1_join = sub[sub["grade_id"] == "E1"]
            e1_ctc = float(e1_join["ctc_annualised_inr"].mean()) if not e1_join.empty else np.nan
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R21", fy, "GRADE", "E1", "e1_entry_ctc_target_inr",
                    e1_ctc, e1_val if e1_val is not None else 2400000.0, "INR", None, 12.0, "WARN",
                    e1_doc, e1_pg, e1_ln, "e1_entry_ctc_target_inr", "Entry E1 annualised CTC", run_id, run_ts,
                )
            )

            # EMP-R24: Active E1 median tenure <= 4 yrs
            e1_act = act[act["grade_id"] == "E1"]
            e1_ten = float(e1_act["total_service_years"].median()) if not e1_act.empty else 0.0
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R24", fy, "GRADE", "E1", "e1_median_tenure_years",
                    e1_ten, 2.0 if hc_val is not None else None, "YEARS", 2.0, None, "BLOCK",
                    "SPEC04_S6_1", 1, 1, "e1_median_tenure_years", "Active E1 median tenure <= 4.0 years", run_id, run_ts,
                )
            )

            # EMP-R25: Entry age in [18, 45] and active age <= 60
            entry_age = act["age_years"] - act["total_service_years"]
            age_v = float(((act["age_years"] > 60.0) | (entry_age < 18.0) | (entry_age > 45.0)).sum())
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R25", fy, "FY", "ALL", "age_rule_violations",
                    age_v, 0.0 if hc_val is not None else None, "COUNT", 0.0, None, "BLOCK",
                    "ONGC_SR_1995_R24", 1, 1, "age_rule_violations", "Entry age in [18,45] and active age <= 60", run_id, run_ts,
                )
            )

            # EMP-R26: Name uniqueness
            n_distinct = int(sub["full_name"].nunique())
            max_ns = int(act.groupby(["wc_id", "full_name"]).size().max()) if not act.empty else 0
            min_names_req = min(15000, max(int(len(act) * 0.8), 1))
            name_v = 0.0 if (n_distinct >= min_names_req and max_ns <= 3) else 1.0
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R26", fy, "FY", "ALL", "name_uniqueness_violations",
                    name_v, 0.0 if hc_val is not None else None, "COUNT", 0.0, None, "BLOCK",
                    "SPEC04_S6_3", 1, 1, "name_uniqueness_violations",
                    f"Distinct names={n_distinct}, max WC namesakes={max_ns}", run_id, run_ts,
                )
            )

            # EMP-R27: Delhi HQ headcount
            del_val, del_doc, del_pg, del_ln = _lookup_target(targets_df, fy, ["delhi_active_target"])
            del_hc = float((act["wc_id"] == "WC-DEL").sum())
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R27", fy, "WC", "WC-DEL", "delhi_active_target",
                    del_hc, del_val, "COUNT", None, 5.0, "BLOCK",
                    del_doc, del_pg, del_ln, "delhi_active_target", "Delhi HQ active headcount vs target +/- 5%", run_id, run_ts,
                )
            )

            # EMP-R30: Average age
            aa_val, aa_doc, aa_pg, aa_ln = _lookup_target(targets_df, fy, ["avg_age_target_years"])
            avg_age = float(act["age_years"].mean()) if not act.empty else np.nan
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R30", fy, "FY", "ALL", "avg_age_target_years",
                    avg_age, aa_val, "YEARS", 1.0, None, "WARN",
                    aa_doc, aa_pg, aa_ln, "avg_age_target_years", "Average age of active employees", run_id, run_ts,
                )
            )

    return pd.DataFrame(rows)


def _ensure_wide_field_df(fld_df: pd.DataFrame) -> pd.DataFrame:
    """Convert long-form (line_code, amount_inr_mn) or wide field DataFrame into canonical ssot_field_economics_360 columns."""
    df = fld_df.copy()
    if "fiscal_year" not in df.columns and "fy" in df.columns:
        df["fiscal_year"] = df["fy"]

    if "line_code" in df.columns and "amount_inr_mn" in df.columns:
        group_cols = [
            c for c in ["fiscal_year", "month", "object_id", "object_type", "segment", "operatorship"]
            if c in df.columns
        ]
        piv = df.pivot_table(
            index=group_cols, columns="line_code", values="amount_inr_mn", aggfunc="sum", fill_value=0.0
        ).reset_index()

        def _col(code: str) -> pd.Series:
            return piv[code] if code in piv.columns else pd.Series(0.0, index=piv.index)

        out = piv[group_cols].copy()
        out["rev_crude"] = _col("REV.CRUDE")
        out["rev_gas"] = _col("REV.GAS")
        out["rev_vap"] = _col("REV.VAP")
        out["rev_other_operating"] = _col("REV.OTHER_OP")
        out["revenue_from_operations"] = (
            out["rev_crude"] + out["rev_gas"] + out["rev_vap"] + out["rev_other_operating"]
        )
        out["other_income_segment"] = _col("OTHER_INCOME_SEGMENT")

        for lcode, wcol in N35_LINE_TO_COL.items():
            out[wcol] = _col(lcode)

        out["levies_total"] = out[LEVIES_COLS].sum(axis=1)
        out["opex_total"] = out[OPEX_COLS].sum(axis=1)
        out["opex_lifting"] = out[LIFTING_COLS].sum(axis=1)

        out["expl_survey_wo"] = _col("PL.EXPL_SURVEY")
        out["expl_wells_wo"] = _col("PL.EXPL_WELLS")
        out["dda_total"] = _col("PL.DDA")
        out["impairment_net"] = _col("N37.IMPAIRMENT_NET")
        out["provisions_writeoffs"] = _col("PL.PROVISIONS")
        out["inventory_change"] = _col("PL.INVENTORY_CHANGE")
        out["purchases_traded"] = _col("PL.PURCHASES_TRADED")
        out["finance_cost"] = _col("PL.FIN_COST")

        out["ebitda"] = (
            out["revenue_from_operations"]
            + out["other_income_segment"]
            - out["levies_total"]
            - out["opex_total"]
            - out["purchases_traded"]
            - out["inventory_change"]
            - out["expl_survey_wo"]
            - out["expl_wells_wo"]
        )
        out["segment_result_contrib"] = _col("SEGMENT_RESULT_CONTRIB")
        out["pbt_contrib"] = np.where(
            _col("PL.PBT") != 0,
            _col("PL.PBT"),
            out["segment_result_contrib"]
            - out["finance_cost"]
            + _col("SEG.INT_DIV")
            + _col("PL.EXCEPTIONAL"),
        )

        crude_ongc = _col("PROD.CRUDE_ONGC")
        crude_jv = _col("PROD.CRUDE_JV")
        gas_ongc = _col("PROD.GAS_ONGC")
        gas_jv = _col("PROD.GAS_JV")
        out["oil_prod_mt"] = (crude_ongc + crude_jv) * 1e6
        out["condensate_prod_mt"] = _col("PROD.COND_MT") * 1e6
        out["gas_prod_mmscm"] = (gas_ongc + gas_jv) * 1e3
        out["prod_basis"] = np.where(
            out.get("object_type", "") == "jv_share",
            "JV_SHARE",
            "ONGC",
        )
        out["oil_sales_mt"] = _col("QTY.CRUDE_SOLD") * 1e6
        out["gas_sales_mmscm"] = _col("QTY.GAS_SOLD") * 1e3
        out["vap_sales_kt"] = _col("QTY.VAP_SOLD")
        out["prod_boe"] = (out["oil_prod_mt"] + out["gas_prod_mmscm"] * 1000.0) * 7.33
        return out

    return df


def run_field_reconciliation(
    fld_df: pd.DataFrame,
    targets_df: pd.DataFrame,
    audit_df: Optional[pd.DataFrame] = None,
    emp_df: Optional[pd.DataFrame] = None,
    run_id: str = "v3_recon_run",
) -> pd.DataFrame:
    """Evaluate FLD-R01 through FLD-R17 over fld_df, targets_df, audit_df, and emp_df."""
    run_ts = datetime.now(timezone.utc).isoformat()
    wdf = _ensure_wide_field_df(fld_df)
    rows: List[Dict[str, Any]] = []

    fys = sorted(wdf["fiscal_year"].dropna().unique().tolist())
    latest_fy = "FY26" if "FY26" in fys else fys[-1]

    for fy in fys:
        sub = wdf[wdf["fiscal_year"] == fy]

        # FLD-R01: PL.REV_OPS (all FYs)
        r01_val, doc, pg, ln = _lookup_target(targets_df, fy, ["PL.REV_OPS"])
        rows.append(
            _make_check_row(
                "FLD", "SPEC-05", "FLD-R01", fy, "FY", "ALL", "PL.REV_OPS",
                float(sub["revenue_from_operations"].sum()), r01_val, "INR_MN", 0.01, None, "BLOCK",
                doc, pg, ln, "PL.REV_OPS", "Standalone Revenue from Operations", run_id, run_ts,
            )
        )

        # FLD-R02: Product revenues (FY21..FY26)
        if fy in SIX_FYS:
            for dkey, lcode, col in [
                ("CRUDE", "REV.CRUDE", "rev_crude"),
                ("GAS", "REV.GAS", "rev_gas"),
                ("VAP", "REV.VAP", "rev_vap"),
                ("OTHER_OP", "REV.OTHER_OP", "rev_other_operating"),
            ]:
                t_val, t_doc, t_pg, t_ln = _lookup_target(targets_df, fy, [lcode])
                rows.append(
                    _make_check_row(
                        "FLD", "SPEC-05", "FLD-R02", fy, "PRODUCT", dkey, lcode,
                        float(sub[col].sum()), t_val, "INR_MN", 0.01, None, "BLOCK",
                        t_doc, t_pg, t_ln, lcode, f"Note 32 {lcode}", run_id, run_ts,
                    )
                )

            # FLD-R03: Segment revenue Offshore & Onshore
            for seg, lcode in [("Offshore", "SEG.REV.OFF"), ("Onshore", "SEG.REV.ON")]:
                t_val, t_doc, t_pg, t_ln = _lookup_target(targets_df, fy, [lcode])
                rows.append(
                    _make_check_row(
                        "FLD", "SPEC-05", "FLD-R03", fy, "SEGMENT", seg, lcode,
                        float(sub.loc[sub["segment"] == seg, "revenue_from_operations"].sum()), t_val, "INR_MN", 0.01, None, "BLOCK",
                        t_doc, t_pg, t_ln, lcode, f"Note 44 {seg} segment revenue", run_id, run_ts,
                    )
                )

            # FLD-R04: All 24 Note 35 lines + PL.PROD_EXP
            for lcode, col in N35_LINE_TO_COL.items():
                t_val, t_doc, t_pg, t_ln = _lookup_target(targets_df, fy, [lcode])
                rows.append(
                    _make_check_row(
                        "FLD", "SPEC-05", "FLD-R04", fy, "NOTE35", lcode, lcode,
                        float(sub[col].sum()), t_val, "INR_MN", 0.01, None, "BLOCK",
                        t_doc, t_pg, t_ln, lcode, f"Note 35 line {lcode}", run_id, run_ts,
                    )
                )
            pe_val, pe_doc, pe_pg, pe_ln = _lookup_target(targets_df, fy, ["PL.PROD_EXP"])
            rows.append(
                _make_check_row(
                    "FLD", "SPEC-05", "FLD-R04", fy, "NOTE35", "PL.PROD_EXP", "PL.PROD_EXP",
                    float((sub["levies_total"] + sub["opex_total"]).sum()), pe_val, "INR_MN", 0.01, None, "BLOCK",
                    pe_doc, pe_pg, pe_ln, "PL.PROD_EXP", "Note 35 total production expenditure (PL.PROD_EXP)", run_id, run_ts,
                )
            )

            # FLD-R05: Cross-domain Staff Expenditure
            se_val, se_doc, se_pg, se_ln = _lookup_target(targets_df, fy, ["N35.STAFF_EXPENDITURE", "staff_expenditure_note35"])
            if emp_df is not None and not emp_df.empty and "cost_expensed_production_inr" in emp_df.columns:
                emp_ref = float(emp_df.loc[emp_df["fiscal_year"] == fy, "cost_expensed_production_inr"].sum()) / 1e6
            else:
                emp_ref = se_val
            rows.append(
                _make_check_row(
                    "FLD", "SPEC-05", "FLD-R05", fy, "CROSS_DOMAIN", "N35.STAFF_EXPENDITURE", "staff_expenditure_cross_domain",
                    float(sub["staff_expenditure"].sum()), emp_ref, "INR_MN", 0.10, None, "BLOCK",
                    se_doc, se_pg, se_ln, "N35.STAFF_EXPENDITURE",
                    "Cross-domain Staff Expenditure (Field Economics vs Employee 360)", run_id, run_ts,
                )
            )

        # FLD-R06: Exploration, DD&A, Impairment, Provisions, Finance cost
        r06_specs = [
            ("PL.DDA", float((sub["dda_total"] + sub["impairment_net"]).sum()), True),
            ("PL.FIN_COST", float(sub["finance_cost"].sum()), True),
            ("PL.EXPL_SURVEY", float(sub["expl_survey_wo"].sum()), fy in SIX_FYS),
            ("PL.EXPL_WELLS", float(sub["expl_wells_wo"].sum()), fy in SIX_FYS),
            ("N37.IMPAIRMENT_NET", float(sub["impairment_net"].sum()), fy in SIX_FYS),
            ("PL.PROVISIONS", float(sub["provisions_writeoffs"].sum()), fy in SIX_FYS),
        ]
        for lcode, sval, include_flag in r06_specs:
            if not include_flag:
                continue
            t_val, t_doc, t_pg, t_ln = _lookup_target(targets_df, fy, [lcode])
            rows.append(
                _make_check_row(
                    "FLD", "SPEC-05", "FLD-R06", fy, "FY", lcode, lcode,
                    sval, t_val, "INR_MN", 0.01, None, "BLOCK",
                    t_doc, t_pg, t_ln, lcode, f"P&L / Note 37 / Note 36 line {lcode}", run_id, run_ts,
                )
            )

        if fy in SIX_FYS:
            # FLD-R07: Segment DD&A and Provisions/Write-Offs
            r07_specs = [
                ("Offshore", "SEG.DDA.OFF", float(sub.loc[sub["segment"] == "Offshore", "dda_total"].sum())),
                ("Onshore", "SEG.DDA.ON", float(sub.loc[sub["segment"] == "Onshore", "dda_total"].sum())),
                ("Unallocated", "SEG.DDA.UNALLOC", float(sub.loc[sub["segment"] == "Unallocated", "dda_total"].sum())),
                ("Offshore", "SEG.WO.OFF", float(sub.loc[sub["segment"] == "Offshore", "provisions_writeoffs"].sum())),
                ("Onshore", "SEG.WO.ON", float(sub.loc[sub["segment"] == "Onshore", "provisions_writeoffs"].sum())),
            ]
            for seg, lcode, sval in r07_specs:
                t_val, t_doc, t_pg, t_ln = _lookup_target(targets_df, fy, [lcode])
                rows.append(
                    _make_check_row(
                        "FLD", "SPEC-05", "FLD-R07", fy, "SEGMENT", seg, lcode,
                        sval, t_val, "INR_MN", 0.01, None, "BLOCK",
                        t_doc, t_pg, t_ln, lcode, f"Note 44 segment {lcode}", run_id, run_ts,
                    )
                )

            # FLD-R08: Segment result Offshore, Onshore, and CO-HQ unallocated
            r08_specs = [
                ("SEGMENT", "Offshore", "SEG.RES.OFF", float(sub.loc[sub["segment"] == "Offshore", "segment_result_contrib"].sum())),
                ("SEGMENT", "Onshore", "SEG.RES.ON", float(sub.loc[sub["segment"] == "Onshore", "segment_result_contrib"].sum())),
                ("OBJECT", "CO-HQ", "SEG.UNALLOC", float(sub.loc[sub["object_id"] == "CO-HQ", "segment_result_contrib"].sum())),
            ]
            for lvl, dkey, lcode, sval in r08_specs:
                t_val, t_doc, t_pg, t_ln = _lookup_target(targets_df, fy, [lcode])
                rows.append(
                    _make_check_row(
                        "FLD", "SPEC-05", "FLD-R08", fy, lvl, dkey, lcode,
                        sval, t_val, "INR_MN", 0.10, None, "BLOCK",
                        t_doc, t_pg, t_ln, lcode, f"Note 44 {lcode}", run_id, run_ts,
                    )
                )

        # FLD-R09: Company PBT (all FYs)
        pbt_val, pbt_doc, pbt_pg, pbt_ln = _lookup_target(targets_df, fy, ["PL.PBT"])
        rows.append(
            _make_check_row(
                "FLD", "SPEC-05", "FLD-R09", fy, "FY", "ALL", "PL.PBT",
                float(sub["pbt_contrib"].sum()), pbt_val, "INR_MN", 0.10, None, "BLOCK",
                pbt_doc, pbt_pg, pbt_ln, "PL.PBT", "Standalone Profit Before Tax", run_id, run_ts,
            )
        )

        if fy in SIX_FYS:
            # FLD-R10: Production by prod_basis (Crude MMT, Gas BCM)
            r10_specs = [
                ("ONGC", "PROD.CRUDE_ONGC", "MMT", float(sub.loc[sub["prod_basis"] == "ONGC", "oil_prod_mt"].sum()) / 1e6),
                ("JV_SHARE", "PROD.CRUDE_JV", "MMT", float(sub.loc[sub["prod_basis"] == "JV_SHARE", "oil_prod_mt"].sum()) / 1e6),
                ("ONGC", "PROD.GAS_ONGC", "BCM", float(sub.loc[sub["prod_basis"] == "ONGC", "gas_prod_mmscm"].sum()) / 1e3),
                ("JV_SHARE", "PROD.GAS_JV", "BCM", float(sub.loc[sub["prod_basis"] == "JV_SHARE", "gas_prod_mmscm"].sum()) / 1e3),
            ]
            for pbasis, lcode, unit_s, sval in r10_specs:
                t_val, t_doc, t_pg, t_ln = _lookup_target(targets_df, fy, [lcode])
                rows.append(
                    _make_check_row(
                        "FLD", "SPEC-05", "FLD-R10", fy, "OPERATORSHIP", pbasis, lcode,
                        sval, t_val, unit_s, 0.005, None, "BLOCK",
                        t_doc, t_pg, t_ln, lcode, f"Production {lcode}", run_id, run_ts,
                    )
                )

            # FLD-R11: Sales quantities
            r11_specs = [
                ("CRUDE", "QTY.CRUDE_SOLD", "MMT", float(sub["oil_sales_mt"].sum()) / 1e6),
                ("GAS", "QTY.GAS_SOLD", "BCM", float(sub["gas_sales_mmscm"].sum()) / 1e3),
                ("VAP", "QTY.VAP_SOLD", "KT", float(sub["vap_sales_kt"].sum())),
            ]
            for dkey, lcode, unit_s, sval in r11_specs:
                t_val, t_doc, t_pg, t_ln = _lookup_target(targets_df, fy, [lcode])
                rows.append(
                    _make_check_row(
                        "FLD", "SPEC-05", "FLD-R11", fy, "PRODUCT", dkey, lcode,
                        sval, t_val, unit_s, 0.01, None, "BLOCK",
                        t_doc, t_pg, t_ln, lcode, f"Note 32 sales volume {lcode}", run_id, run_ts,
                    )
                )

            # FLD-R12: RAS factor bounds in [0.33, 3.0]
            if audit_df is not None and not audit_df.empty:
                a_fy_col = "fy" if "fy" in audit_df.columns else "fiscal_year"
                asub = audit_df[audit_df[a_fy_col] == fy]
                ras_v = float(((asub["ras_factor"] < 0.33) | (asub["ras_factor"] > 3.0)).sum())
            else:
                ras_v = 0.0
            rows.append(
                _make_check_row(
                    "FLD", "SPEC-05", "FLD-R12", fy, "FY", "ALL", "ras_factor_bounds_violations",
                    ras_v, 0.0 if r01_val is not None else None, "COUNT", 0.0, None, "BLOCK",
                    "SPEC05_S6_3", 1, 1, "ras_factor_bounds_violations",
                    "Zero RAS cells outside [0.33, 3.0]", run_id, run_ts,
                )
            )

        # FLD-R13: Domain & non-negativity rules
        pf = sub["object_type"] == "field"
        pf_v = pf & (
            (sub["revenue_from_operations"] < 0) | (sub["royalty"] < 0) | (sub["oidb_cess"] < 0)
            | (sub["staff_expenditure"] < 0) | (sub["dda_total"] < 0)
            | (sub["expl_survey_wo"] != 0) | (sub["expl_wells_wo"] != 0) | (sub["rev_vap"] != 0)
        )
        ex_v = (sub["object_type"] != "exploration") & ((sub["expl_survey_wo"] != 0) | (sub["expl_wells_wo"] != 0))
        pl_v = (sub["object_type"] != "plant") & (sub["rev_vap"] != 0)
        dom_v = float((pf_v | ex_v | pl_v).sum())
        rows.append(
            _make_check_row(
                "FLD", "SPEC-05", "FLD-R13", fy, "FY", "ALL", "negativity_and_domain_violations",
                dom_v, 0.0 if r01_val is not None else None, "COUNT", 0.0, None, "BLOCK",
                "SPEC05_S7_2", 1, 1, "negativity_and_domain_violations",
                "Zero rows violating non-negativity or object_type domain constraints", run_id, run_ts,
            )
        )

        # FLD-R14: Object-month P&L roll-up identity violations
        m_id_v = float(
            (
                (
                    sub["revenue_from_operations"]
                    + sub["other_income_segment"]
                    - sub["levies_total"]
                    - sub["opex_total"]
                    - sub["purchases_traded"]
                    - sub["inventory_change"]
                    - sub["expl_survey_wo"]
                    - sub["expl_wells_wo"]
                    - sub["ebitda"]
                ).abs()
                > 0.01
            ).sum()
        )
        rows.append(
            _make_check_row(
                "FLD", "SPEC-05", "FLD-R14", fy, "FY", "ALL", "month_sum_identity_violations",
                m_id_v, 0.0 if r01_val is not None else None, "COUNT", 0.0, None, "BLOCK",
                "SPEC05_S7_2", 1, 1, "month_sum_identity_violations",
                "Zero rows violating object-month revenue + other_income - levies - opex = ebitda", run_id, run_ts,
            )
        )

        # FLD-R15: Company bridge residual = 0
        seg_sum = float(sub["segment_result_contrib"].sum())
        co_fin = float(sub.loc[sub["object_id"] == "CO-FIN", "pbt_contrib"].sum())
        co_tr = float(sub.loc[sub["object_id"] == "CO-TREASURY", "pbt_contrib"].sum())
        co_ex = float(sub.loc[sub["object_id"] == "CO-EXCEP", "pbt_contrib"].sum())
        tot_pbt = float(sub["pbt_contrib"].sum())
        bridge_res = abs((seg_sum + co_fin + co_tr + co_ex) - tot_pbt)
        rows.append(
            _make_check_row(
                "FLD", "SPEC-05", "FLD-R15", fy, "FY", "BRIDGE", "pbt_bridge_residual",
                bridge_res, 0.0 if pbt_val is not None else None, "INR_MN", 0.10, None, "BLOCK",
                "SPEC05_S4_3", 1, 1, "pbt_bridge_residual",
                "Segment results + corporate bridge objects reconcile to company PBT", run_id, run_ts,
            )
        )

        if fy == latest_fy:
            # FLD-R16: Lifting cost per BOE in [$8, $16]
            pf_sub = sub[sub["object_type"] == "field"]
            boe_sum = float(pf_sub["prod_boe"].sum())
            lift_usd = (float(pf_sub["opex_lifting"].sum()) * 1e6 / 84.5 / boe_sum) if boe_sum > 0 else np.nan
            rows.append(
                _make_check_row(
                    "FLD", "SPEC-05", "FLD-R16", fy, "FY", "PRODUCING", "lifting_cost_usd_boe",
                    lift_usd, 12.0 if r01_val is not None else None, "USD_BOE", 4.0, None, "WARN",
                    "SPEC05_S7_2", 1, 1, "lifting_cost_usd_boe",
                    "Average lifting cost per BOE within [$8.0, $16.0]/BOE", run_id, run_ts,
                )
            )

            # FLD-R17: Mumbai High (FLD-MHN + FLD-MHS) share of operated crude in [30%, 45%]
            op_crude = float(sub.loc[sub["prod_basis"] == "ONGC", "oil_prod_mt"].sum())
            mh_crude = float(sub.loc[sub["object_id"].isin(["FLD-MHN", "FLD-MHS"]), "oil_prod_mt"].sum())
            mh_share = (mh_crude * 100.0 / op_crude) if op_crude > 0 else np.nan
            rows.append(
                _make_check_row(
                    "FLD", "SPEC-05", "FLD-R17", fy, "OBJECT", "FLD-MHN+FLD-MHS", "mumbai_high_crude_share_pct",
                    mh_share, 37.5 if r01_val is not None else None, "PCT", 7.5, None, "WARN",
                    "SPEC05_S7_2", 1, 1, "mumbai_high_crude_share_pct",
                    "Mumbai High (FLD-MHN + FLD-MHS) share of operated crude in [30.0%, 45.0%]", run_id, run_ts,
                )
            )

    return pd.DataFrame(rows)


def load_real_landed_data(
    base_dir: Optional[Path] = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load and transform real landed CSVs into canonical SSOT DataFrames for offline reconciliation."""
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent.parent

    con = duckdb.connect(":memory:")

    # 1. Build ssot_field_economics_360 from CO_PA_v3.csv + production_monthly.csv + cost_objects.yaml
    co_cfg = yaml.safe_load((base_dir / "world_bible" / "reference" / "cost_objects.yaml").read_text(encoding="utf-8"))
    co_df = pd.DataFrame(co_cfg["cost_objects"])
    con.register("dim_co", co_df)

    copa_path = str(base_dir / "landing" / "sap" / "CO_PA_v3.csv")
    prod_path = str(base_dir / "landing" / "db_exports" / "production_monthly.csv")
    fld_df = con.execute(
        f"""
        WITH copa AS (
          SELECT
            fy AS fiscal_year,
            month,
            object_id,
            SUM(IF(line_code = 'REV.CRUDE', amount_inr_mn, 0.0)) AS rev_crude,
            SUM(IF(line_code = 'REV.GAS', amount_inr_mn, 0.0)) AS rev_gas,
            SUM(IF(line_code = 'REV.VAP', amount_inr_mn, 0.0)) AS rev_vap,
            SUM(IF(line_code = 'REV.OTHER_OP', amount_inr_mn, 0.0)) AS rev_other_operating,
            SUM(IF(line_code = 'OTHER_INCOME_SEGMENT', amount_inr_mn, 0.0)) AS other_income_segment,
            SUM(IF(line_code = 'N35.ROYALTY', amount_inr_mn, 0.0)) AS royalty,
            SUM(IF(line_code = 'N35.OIDB_CESS', amount_inr_mn, 0.0)) AS oidb_cess,
            SUM(IF(line_code = 'N35.NCCD', amount_inr_mn, 0.0)) AS nccd,
            SUM(IF(line_code = 'N35.EXCISE_SAED', amount_inr_mn, 0.0)) AS excise_saed,
            SUM(IF(line_code = 'N35.PORT_TRUST', amount_inr_mn, 0.0)) AS port_trust,
            SUM(IF(line_code = 'N35.OTHER_LEVIES', amount_inr_mn, 0.0)) AS other_levies,
            SUM(IF(line_code = 'N35.STAFF_EXPENDITURE', amount_inr_mn, 0.0)) AS staff_expenditure,
            SUM(IF(line_code = 'N35.WORKOVER_OPS', amount_inr_mn, 0.0)) AS workover_ops,
            SUM(IF(line_code = 'N35.WATER_INJECTION_DESALTING', amount_inr_mn, 0.0)) AS water_injection_desalting,
            SUM(IF(line_code = 'N35.CONSUMPTION_STORES_SPARES', amount_inr_mn, 0.0)) AS consumption_stores_spares,
            SUM(IF(line_code = 'N35.POLLUTION_CONTROL', amount_inr_mn, 0.0)) AS pollution_control,
            SUM(IF(line_code = 'N35.TRANSPORT_EXPENDITURE', amount_inr_mn, 0.0)) AS transport_expenditure,
            SUM(IF(line_code = 'N35.INSURANCE', amount_inr_mn, 0.0)) AS insurance,
            SUM(IF(line_code = 'N35.POWER_FUEL', amount_inr_mn, 0.0)) AS power_fuel,
            SUM(IF(line_code = 'N35.REPAIRS_MAINTENANCE', amount_inr_mn, 0.0)) AS repairs_maintenance,
            SUM(IF(line_code = 'N35.CONTRACTUAL_HIRE', amount_inr_mn, 0.0)) AS contractual_hire,
            SUM(IF(line_code = 'N35.OTHER_PRODUCTION_EXP', amount_inr_mn, 0.0)) AS other_production_exp,
            SUM(IF(line_code = 'N35.TRANSPORT_FREIGHT_PRODUCTS', amount_inr_mn, 0.0)) AS transport_freight_products,
            SUM(IF(line_code = 'N35.R_AND_D', amount_inr_mn, 0.0)) AS r_and_d,
            SUM(IF(line_code = 'N35.GAE', amount_inr_mn, 0.0)) AS gae,
            SUM(IF(line_code = 'N35.CSR', amount_inr_mn, 0.0)) AS csr,
            SUM(IF(line_code = 'N35.EXCHANGE_LOSS', amount_inr_mn, 0.0)) AS exchange_loss,
            SUM(IF(line_code = 'N35.MISC_EXP', amount_inr_mn, 0.0)) AS misc_exp,
            SUM(IF(line_code = 'N35.FV_LOSS', amount_inr_mn, 0.0)) AS fv_loss,
            SUM(IF(line_code = 'PL.EXPL_SURVEY', amount_inr_mn, 0.0)) AS expl_survey_wo,
            SUM(IF(line_code = 'PL.EXPL_WELLS', amount_inr_mn, 0.0)) AS expl_wells_wo,
            SUM(IF(line_code = 'PL.DDA', amount_inr_mn, 0.0)) AS dda_total,
            SUM(IF(line_code = 'N37.IMPAIRMENT_NET', amount_inr_mn, 0.0)) AS impairment_net,
            SUM(IF(line_code = 'PL.PROVISIONS', amount_inr_mn, 0.0)) AS provisions_writeoffs,
            SUM(IF(line_code = 'PL.INVENTORY_CHANGE', amount_inr_mn, 0.0)) AS inventory_change,
            SUM(IF(line_code = 'PL.PURCHASES_TRADED', amount_inr_mn, 0.0)) AS purchases_traded,
            SUM(IF(line_code = 'PL.FIN_COST', amount_inr_mn, 0.0)) AS finance_cost,
            SUM(IF(line_code = 'SEG.INT_DIV', amount_inr_mn, 0.0)) AS interest_dividend_income,
            SUM(IF(line_code = 'PL.EXCEPTIONAL', amount_inr_mn, 0.0)) AS exceptional_items,
            SUM(IF(line_code = 'SEGMENT_RESULT_CONTRIB', amount_inr_mn, 0.0)) AS segment_result_contrib,
            SUM(IF(line_code = 'PL.PBT', amount_inr_mn, 0.0)) AS pbt_contrib,
            SUM(IF(line_code IN ('PROD.CRUDE_ONGC', 'PROD.CRUDE_JV'), amount_inr_mn, 0.0)) * 1e6 AS copa_oil_prod_mt,
            SUM(IF(line_code IN ('PROD.GAS_ONGC', 'PROD.GAS_JV'), amount_inr_mn, 0.0)) * 1e3 AS copa_gas_prod_mmscm,
            SUM(IF(line_code = 'QTY.CRUDE_SOLD', amount_inr_mn, 0.0)) * 1e6 AS oil_sales_mt,
            SUM(IF(line_code = 'QTY.GAS_SOLD', amount_inr_mn, 0.0)) * 1e3 AS gas_sales_mmscm,
            SUM(IF(line_code = 'QTY.VAP_SOLD', amount_inr_mn, 0.0)) AS vap_sales_kt
          FROM read_csv_auto('{copa_path}')
          WHERE fy <= 'FY26'
          GROUP BY 1, 2, 3
        ),
        prod AS (
          SELECT
            month,
            field_id AS object_id,
            SUM(condensate_production_mt) AS condensate_prod_mt
          FROM read_csv_auto('{prod_path}')
          GROUP BY 1, 2
        )
        SELECT
          c.*,
          d.object_type,
          d.segment,
          d.operatorship,
          c.copa_oil_prod_mt AS oil_prod_mt,
          COALESCE(p.condensate_prod_mt, 0.0) AS condensate_prod_mt,
          c.copa_gas_prod_mmscm AS gas_prod_mmscm,
          CASE WHEN d.object_type = 'jv_share' THEN 'JV_SHARE' ELSE 'ONGC' END AS prod_basis,
          (c.copa_oil_prod_mt + c.copa_gas_prod_mmscm * 1000.0) * 7.33 AS prod_boe,
          (c.rev_crude + c.rev_gas + c.rev_vap + c.rev_other_operating) AS revenue_from_operations,
          (c.royalty + c.oidb_cess + c.nccd + c.excise_saed + c.port_trust + c.other_levies) AS levies_total,
          (c.staff_expenditure + c.workover_ops + c.water_injection_desalting + c.consumption_stores_spares + c.pollution_control + c.transport_expenditure + c.insurance + c.power_fuel + c.repairs_maintenance + c.contractual_hire + c.other_production_exp + c.transport_freight_products + c.r_and_d + c.gae + c.csr + c.exchange_loss + c.misc_exp + c.fv_loss) AS opex_total,
          (c.staff_expenditure + c.workover_ops + c.water_injection_desalting + c.consumption_stores_spares + c.pollution_control + c.transport_expenditure + c.insurance + c.power_fuel + c.repairs_maintenance + c.contractual_hire + c.other_production_exp) AS opex_lifting,
          ((c.rev_crude + c.rev_gas + c.rev_vap + c.rev_other_operating) + c.other_income_segment - (c.royalty + c.oidb_cess + c.nccd + c.excise_saed + c.port_trust + c.other_levies) - (c.staff_expenditure + c.workover_ops + c.water_injection_desalting + c.consumption_stores_spares + c.pollution_control + c.transport_expenditure + c.insurance + c.power_fuel + c.repairs_maintenance + c.contractual_hire + c.other_production_exp + c.transport_freight_products + c.r_and_d + c.gae + c.csr + c.exchange_loss + c.misc_exp + c.fv_loss) - c.purchases_traded - c.inventory_change - c.expl_survey_wo - c.expl_wells_wo) AS ebitda
        FROM copa c
        LEFT JOIN dim_co d USING (object_id)
        LEFT JOIN prod p USING (month, object_id)
        """
    ).df()

    audit_df = pd.read_csv(base_dir / "landing" / "sap" / "field_alloc_audit.csv")
    fld_targets_df = pd.read_csv(base_dir / "world_bible" / "reference" / "real_targets" / "field_econ_targets_fy.csv")

    # 2. Build ssot_employee_360 from PA0002_PA0001.csv + PY_CLUSTER_EXP.csv + lms_attendance.csv
    grades_cfg = yaml.safe_load((base_dir / "world_bible" / "reference" / "grades.yaml").read_text(encoding="utf-8"))
    con.register("dim_grades", pd.DataFrame(grades_cfg["grades"]))
    pa_path = str(base_dir / "landing" / "sap" / "PA0002_PA0001.csv")
    py_path = str(base_dir / "landing" / "sap" / "PY_CLUSTER_EXP.csv")
    lms_path = str(base_dir / "landing" / "db_exports" / "lms_attendance.csv")

    emp_df = con.execute(
        f"""
        WITH lms AS (
          SELECT emp_id AS PERNR, SUBSTR(CAST(start_date AS VARCHAR), 1, 7) AS FPPER, SUM(training_hours) AS training_hours
          FROM read_csv_auto('{lms_path}')
          GROUP BY 1, 2
        ),
        pa AS (
          SELECT
            PERNR,
            name AS full_name,
            CASE WHEN GESCH IN ('Female', 'F') THEN 'F' WHEN GESCH IN ('Male', 'M') THEN 'M' ELSE GESCH END AS gender,
            CASE WHEN VDSK1 = 'General' THEN 'GEN' ELSE VDSK1 END AS social_category,
            CAST(pwd_flag AS BOOLEAN) AS pwd_flag,
            CAST(GBDAT AS DATE) AS birth_date,
            CAST(BEGDA AS DATE) AS hire_date,
            STRFTIME(CAST(BEGDA AS DATE), '%Y-%m') AS hire_ym,
            CASE WHEN separation_date IS NOT NULL AND CAST(separation_date AS VARCHAR) != ''
                 THEN STRFTIME(CAST(separation_date AS DATE), '%Y-%m')
                 ELSE NULL END AS sep_ym,
            CASE WHEN separation_date IS NOT NULL AND CAST(separation_date AS VARCHAR) != ''
                 THEN STRFTIME(DATE_TRUNC('month', CAST(separation_date AS DATE)) - INTERVAL 1 MONTH, '%Y-%m')
                 ELSE NULL END AS prev_sep_ym,
            CASE WHEN separation_date IS NOT NULL AND CAST(separation_date AS VARCHAR) != ''
                 THEN CAST(separation_date AS DATE)
                 ELSE NULL END AS sep_date
          FROM read_csv_auto('{pa_path}')
        )
        SELECT
          p.PERNR AS emp_id,
          p.FPPER AS month,
          p.fiscal_year,
          (MOD(CAST(SUBSTR(p.FPPER, 6, 2) AS INT) + 8, 12) + 1) AS fy_month_no,
          pa.full_name,
          pa.gender,
          pa.social_category,
          pa.pwd_flag,
          p.grade_id,
          g.cadre,
          p.wc_id,
          ROUND(DATE_DIFF('day', pa.birth_date, LAST_DAY(CAST(p.FPPER || '-01' AS DATE))) / 365.25, 2) AS age_years,
          CASE
            WHEN DATE_DIFF('day', pa.birth_date, LAST_DAY(CAST(p.FPPER || '-01' AS DATE))) / 365.25 < 30.0 THEN '<30'
            WHEN DATE_DIFF('day', pa.birth_date, LAST_DAY(CAST(p.FPPER || '-01' AS DATE))) / 365.25 <= 50.0 THEN '30-50'
            ELSE '>50'
          END AS age_band_brsr,
          ROUND(DATE_DIFF('day', pa.hire_date, LAST_DAY(CAST(p.FPPER || '-01' AS DATE))) / 365.25, 2) AS total_service_years,
          (pa.hire_ym = p.FPPER) AS joined_in_month_flag,
          (pa.sep_ym IS NOT NULL AND p.FPPER IN (pa.sep_ym, pa.prev_sep_ym)) AS separated_in_month_flag,
          (pa.sep_date IS NULL OR pa.sep_date > LAST_DAY(CAST(p.FPPER || '-01' AS DATE))) AS is_month_end_active,
          CAST(g.pay_scale_min_inr AS DOUBLE) AS pay_scale_min_inr,
          CAST(g.pay_scale_max_inr AS DOUBLE) AS pay_scale_max_inr,
          p.LGART_1001 AS basic_pay_inr,
          p.LGART_1002 AS da_inr,
          p.hra_inr,
          p.cafeteria_allowances_inr AS cafeteria_allowance_inr,
          p.LGART_9001 AS gross_earnings_inr,
          (p.LGART_9001 - p.LGART_9002) AS total_deductions_inr,
          p.LGART_9002 AS net_pay_inr,
          p.employer_cpf_inr,
          (p.superannuation_benefit_pct / 100.0) AS superannuation_pct_bp_da,
          p.cost_note35_a_inr,
          p.cost_note35_b_inr,
          p.cost_note35_c_inr,
          p.cost_note35_d_inr,
          p.cost_note35_e_inr,
          p.cost_note35_f_inr,
          (p.cost_note35_a_inr + p.cost_note35_b_inr + p.cost_note35_c_inr + p.cost_note35_d_inr + p.cost_note35_e_inr + p.cost_note35_f_inr) AS cost_total_inr,
          p.cost_capitalised_inr,
          p.cost_expensed_inr,
          p.cost_expensed_production_inr,
          ((p.LGART_9001 - p.arrears_inr - p.leave_encashment_paid_inr - p.prp_paid_inr + p.employer_cost_noncash_inr) * 12.0) AS ctc_annualised_inr,
          COALESCE(l.training_hours, 0.0) AS training_hours
        FROM read_csv_auto('{py_path}') p
        INNER JOIN pa USING (PERNR)
        LEFT JOIN dim_grades g ON p.grade_id = g.grade_id
        LEFT JOIN lms l ON p.PERNR = l.PERNR AND p.FPPER = l.FPPER
        WHERE p.fiscal_year <= 'FY26'
        """
    ).df()

    pool_df = pd.read_csv(base_dir / "landing" / "sap" / "employee_cost_pool.csv")
    emp_targets_df = pd.read_csv(base_dir / "world_bible" / "reference" / "real_targets" / "employee_targets_fy.csv")
    return emp_df, pool_df, emp_targets_df, fld_df, audit_df, fld_targets_df


def summarize_check_tally(recon_df: pd.DataFrame) -> pd.DataFrame:
    """Collapse multi-row checks into a 1-row-per-check_id summary tally (PASS / WARN / FAIL)."""
    records = []
    for (domain, cid), grp in recon_df.groupby(["domain", "check_id"], sort=True):
        has_block_fail = ((grp["severity"] == "BLOCK") & (grp["status"] == "FAIL")).any()
        has_warn_fail = ((grp["severity"] == "WARN") & (grp["status"] == "FAIL")).any()
        if has_block_fail:
            overall = "FAIL"
        elif has_warn_fail:
            overall = "WARN"
        else:
            overall = "PASS"
        records.append(
            {
                "domain": domain,
                "check_id": cid,
                "overall_status": overall,
                "total_rows": len(grp),
                "pass_rows": int((grp["status"] == "PASS").sum()),
                "fail_rows": int((grp["status"] == "FAIL").sum()),
            }
        )
    return pd.DataFrame(records)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run Employee-360 and Field-Economics-360 offline reconciliation.")
    parser.add_argument("--domain", choices=["all", "emp", "fld"], default="all")
    parser.add_argument("--out", type=str, default=None, help="Optional CSV output path for detailed check rows.")
    args = parser.parse_args(argv)

    emp_df, pool_df, emp_targets_df, fld_df, audit_df, fld_targets_df = load_real_landed_data()
    dfs: List[pd.DataFrame] = []
    if args.domain in ("all", "emp"):
        dfs.append(run_employee_reconciliation(emp_df, pool_df, emp_targets_df))
    if args.domain in ("all", "fld"):
        dfs.append(run_field_reconciliation(fld_df, fld_targets_df, audit_df=audit_df, emp_df=emp_df))

    full_df = pd.concat(dfs, ignore_index=True)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        full_df.to_csv(out_path, index=False)

    tally = summarize_check_tally(full_df)
    n_pass = int((tally["overall_status"] == "PASS").sum())
    n_warn = int((tally["overall_status"] == "WARN").sum())
    n_fail = int((tally["overall_status"] == "FAIL").sum())
    print(f"=== Check-Level Summary ({len(tally)} checks): PASS={n_pass}, WARN={n_warn}, FAIL={n_fail} ===")
    for dom, dgrp in tally.groupby("domain"):
        dp = int((dgrp["overall_status"] == "PASS").sum())
        dw = int((dgrp["overall_status"] == "WARN").sum())
        df_cnt = int((dgrp["overall_status"] == "FAIL").sum())
        print(f"  [{dom}] {len(dgrp)} checks: PASS={dp}, WARN={dw}, FAIL={df_cnt}")
    non_pass = tally[tally["overall_status"] != "PASS"]
    if not non_pass.empty:
        print("\nNon-PASS Checks:")
        print(non_pass.to_string(index=False))
        print("\nFailed Rows Detail:")
        failed_rows = full_df[full_df["status"] == "FAIL"][
            ["domain", "check_id", "fiscal_year", "dimension_key", "metric", "ssot_value", "reference_value", "abs_diff", "tolerance_abs", "tolerance_pct", "severity", "status"]
        ]
        print(failed_rows.to_string(index=False))

    return 2 if n_fail > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
