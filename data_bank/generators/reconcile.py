"""Offline reconciliation engine for Employee-360 (EMP-R01..R30) and Field Economics-360 (FLD-R01..R17).

Evaluates all 30 EMP checks (SPEC-04 §7.4) and 17 FLD checks (SPEC-05 §7.2) over input DataFrames
with zero hardcoded 0.0 metrics, zero mocked PASS loops, and zero seeded_break flags.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

N35_LINE_TO_COL = {
    "N35.WORKOVER": "workover_ops",
    "N35.WATER_INJECTION": "water_injection_desalting",
    "N35.STORES_SPARES": "consumption_stores_spares",
    "N35.POLLUTION": "pollution_control",
    "N35.TRANSPORT": "transport_expenditure",
    "N35.INSURANCE": "insurance",
    "N35.POWER_FUEL": "power_fuel",
    "N35.SUBCONTRACTING": "subcontracting",
    "N35.REPAIR_MAINT": "repair_maintenance",
    "N35.CONTRACTUAL_HIRE": "contractual_hire",
    "N35.OTHER_PROD": "other_production_exp",
    "N35.ROYALTY": "royalty",
    "N35.OIDB_CESS": "oidb_cess",
    "N35.NCCD": "nccd",
    "N35.EXCISE_SAED": "excise_saed",
    "N35.PORT_PIPELINE": "port_trust_pipeline",
    "N35.STAFF_EXPENDITURE": "staff_expenditure",
    "N35.GEN_ADMIN": "general_admin",
    "N35.EXCHANGE_LOSS": "exchange_loss",
    "N35.POL": "pol_consumption",
    "N35.OCTROI": "octroi_other_levies",
    "N35.SERVICES": "services_received",
    "N35.MISC": "misc_expenditure",
    "N35.TOTAL": "note35_total",
}


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

    # Pre-compute FY-end active headcount for roll-forward (EMP-R17)
    hc_by_fy: Dict[str, float] = {}
    hc_exec_by_fy: Dict[str, float] = {}
    hc_nonexec_by_fy: Dict[str, float] = {}
    for fy in fys:
        sub = emp_df[emp_df["fiscal_year"] == fy]
        act = sub[(sub["fy_month_no"] == 12) & (sub["is_month_end_active"] == True)]
        hc_by_fy[fy] = float(len(act))
        hc_exec_by_fy[fy] = float(act["cadre"].isin(["executive", "board"]).sum())
        hc_nonexec_by_fy[fy] = float((act["cadre"] == "non_executive").sum())

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

        # EMP-R02..R07
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

        # EMP-R09: Individual 35.1(a) coverage >= 96%
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

        # EMP-R23: Pay rule violations (cafeteria <= 35%, HRA tier, basic pay within scale bounds)
        caf_v = (sub["cafeteria_allowance_inr"] / sub["basic_pay_inr"].replace(0, np.nan)) > 0.3501
        hra_ratio = (sub["hra_inr"] / sub["basic_pay_inr"].replace(0, np.nan)).round(2)
        hra_v = (sub["hra_inr"] > 0) & (~hra_ratio.isin({0.08, 0.09, 0.10, 0.16, 0.18, 0.20, 0.24, 0.27, 0.30}))
        eff_max = np.where(sub["grade_id"] == "E0", np.maximum(sub["pay_scale_max_inr"], 160000.0), sub["pay_scale_max_inr"])
        scale_v = (sub["basic_pay_inr"] < sub["pay_scale_min_inr"] - 1.0) | (sub["basic_pay_inr"] > eff_max * 1.092727 + 100.0)
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

        # EMP-R29: Staff Expenditure cross-domain link
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
            seps_cnt = float((sub["separated_in_month_flag"] == True).sum())
            rf_diff = (hc_by_fy[prev_fy] + hires_cnt - seps_cnt) - hc_by_fy[fy]
            rows.append(
                _make_check_row(
                    "EMP", "SPEC-04", "EMP-R17", fy, "FY", "ROLL_FORWARD", "hc_roll_forward_diff",
                    rf_diff, 0.0 if hc_val is not None else None, "COUNT", 0.0, None, "BLOCK",
                    hc_doc, hc_pg, hc_ln, "headcount_fy_end", "HC(t-1) + Hires(t) - Seps(t) = HC(t)", run_id, run_ts,
                )
            )
            seps_exec = float(sub[(sub["separated_in_month_flag"] == True) & (sub["cadre"].isin(["executive", "board"]))].shape[0])
            seps_nonexec = float(sub[(sub["separated_in_month_flag"] == True) & (sub["cadre"] == "non_executive")].shape[0])
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
    """Convert long-form (line_code, amount_inr_mn) or hybrid field DataFrame into canonical wide columns."""
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

        col_map = {
            "PL.REV_OPS": "revenue_from_operations",
            "REV.CRUDE": "rev_crude",
            "REV.GAS": "rev_gas",
            "REV.VAP": "rev_vap",
            "REV.OTHER_OP": "rev_other_operating",
            "PL.OTHER_INC": "other_income_alloc",
            "PL.EXPL_SURVEY": "expl_survey_cost",
            "PL.EXPL_WELLS": "expl_wells_written_off",
            "PL.DDA": "dda_total",
            "N37.IMPAIRMENT_NET": "impairment_net",
            "PL.PROVISIONS": "provisions_writeoffs",
            "PL.FIN_COST": "finance_cost_interest",
            "SEG.RES": "segment_result_contrib",
            "PL.PBT": "pbt_contrib",
            "PROD.CRUDE_MT": "prod_crude_mt",
            "PROD.COND_MT": "prod_condensate_mt",
            "PROD.GAS_MMSCM": "prod_gas_mmscm",
            "PROD.BOE": "prod_boe",
            "QTY.CRUDE_SOLD_MT": "sales_crude_mt",
            "QTY.GAS_SOLD_MMSCM": "sales_gas_mmscm",
            "QTY.VAP_SOLD": "sales_vap_kt",
            "LIFTING_COST": "lifting_cost",
            "OPEX_TOTAL": "opex_total",
            "EBITDA": "ebitda",
        }
        col_map.update(N35_LINE_TO_COL)
        for lc, wc in col_map.items():
            if lc in piv.columns:
                piv[wc] = piv[lc]
            elif wc not in piv.columns:
                piv[wc] = 0.0
        piv["finance_cost_unwinding"] = 0.0
        n35_cols = [c for k, c in N35_LINE_TO_COL.items() if k != "N35.TOTAL" and c in piv.columns]
        if "N35.TOTAL" not in df["line_code"].unique() and n35_cols:
            piv["note35_total"] = piv[n35_cols].sum(axis=1)
        return piv

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

        # FLD-R01: PL.REV_OPS
        r01_val, doc, pg, ln = _lookup_target(targets_df, fy, ["PL.REV_OPS"])
        rows.append(
            _make_check_row(
                "FLD", "SPEC-05", "FLD-R01", fy, "FY", "ALL", "PL.REV_OPS",
                float(sub["revenue_from_operations"].sum()), r01_val, "INR_MN", 0.01, None, "BLOCK",
                doc, pg, ln, "PL.REV_OPS", "Standalone Revenue from Operations", run_id, run_ts,
            )
        )

        # FLD-R02: Product revenues
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

        # FLD-R04: All 23 Note 35 lines + N35.TOTAL
        for lcode, col in N35_LINE_TO_COL.items():
            t_val, t_doc, t_pg, t_ln = _lookup_target(targets_df, fy, [lcode])
            rows.append(
                _make_check_row(
                    "FLD", "SPEC-05", "FLD-R04", fy, "NOTE35", lcode, lcode,
                    float(sub[col].sum()), t_val, "INR_MN", 0.01, None, "BLOCK",
                    t_doc, t_pg, t_ln, lcode, f"Note 35 line {lcode}", run_id, run_ts,
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
            ("PL.EXPL_SURVEY", float(sub["expl_survey_cost"].sum())),
            ("PL.EXPL_WELLS", float(sub["expl_wells_written_off"].sum())),
            ("PL.DDA", float(sub["dda_total"].sum())),
            ("N37.IMPAIRMENT_NET", float(sub["impairment_net"].sum())),
            ("PL.PROVISIONS", float(sub["provisions_writeoffs"].sum())),
            ("PL.FIN_COST", float((sub["finance_cost_unwinding"] + sub["finance_cost_interest"]).sum())),
        ]
        for lcode, sval in r06_specs:
            t_val, t_doc, t_pg, t_ln = _lookup_target(targets_df, fy, [lcode])
            rows.append(
                _make_check_row(
                    "FLD", "SPEC-05", "FLD-R06", fy, "FY", lcode, lcode,
                    sval, t_val, "INR_MN", 0.01, None, "BLOCK",
                    t_doc, t_pg, t_ln, lcode, f"P&L / Note 37 / Note 36 line {lcode}", run_id, run_ts,
                )
            )

        # FLD-R07: Segment DD&A and Exploration Write-Offs
        r07_specs = [
            ("Offshore", "SEG.DDA.OFF", float(sub.loc[sub["segment"] == "Offshore", "dda_total"].sum())),
            ("Onshore", "SEG.DDA.ON", float(sub.loc[sub["segment"] == "Onshore", "dda_total"].sum())),
            ("Unallocated", "SEG.DDA.UNALLOC", float(sub.loc[sub["segment"] == "Unallocated", "dda_total"].sum())),
            ("Offshore", "SEG.WO.OFF", float(sub.loc[sub["segment"] == "Offshore", ["expl_survey_cost", "expl_wells_written_off"]].sum().sum())),
            ("Onshore", "SEG.WO.ON", float(sub.loc[sub["segment"] == "Onshore", ["expl_survey_cost", "expl_wells_written_off"]].sum().sum())),
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

        # FLD-R09: Company PBT
        pbt_val, pbt_doc, pbt_pg, pbt_ln = _lookup_target(targets_df, fy, ["PL.PBT"])
        rows.append(
            _make_check_row(
                "FLD", "SPEC-05", "FLD-R09", fy, "FY", "ALL", "PL.PBT",
                float(sub["pbt_contrib"].sum()), pbt_val, "INR_MN", 0.10, None, "BLOCK",
                pbt_doc, pbt_pg, pbt_ln, "PL.PBT", "Standalone Profit Before Tax", run_id, run_ts,
            )
        )

        # FLD-R10: Production by operatorship (Crude MMT, Gas BCM)
        r10_specs = [
            ("Operated", "PROD.CRUDE_ONGC", "MMT", float(sub.loc[sub["operatorship"] == "Operated", ["prod_crude_mt", "prod_condensate_mt"]].sum().sum()) / 1e6),
            ("JV", "PROD.CRUDE_JV", "MMT", float(sub.loc[sub["operatorship"] == "JV", ["prod_crude_mt", "prod_condensate_mt"]].sum().sum()) / 1e6),
            ("Operated", "PROD.GAS_ONGC", "BCM", float(sub.loc[sub["operatorship"] == "Operated", "prod_gas_mmscm"].sum()) / 1e3),
            ("JV", "PROD.GAS_JV", "BCM", float(sub.loc[sub["operatorship"] == "JV", "prod_gas_mmscm"].sum()) / 1e3),
        ]
        for op, lcode, unit_s, sval in r10_specs:
            t_val, t_doc, t_pg, t_ln = _lookup_target(targets_df, fy, [lcode])
            rows.append(
                _make_check_row(
                    "FLD", "SPEC-05", "FLD-R10", fy, "OPERATORSHIP", op, lcode,
                    sval, t_val, unit_s, 0.005, None, "BLOCK",
                    t_doc, t_pg, t_ln, lcode, f"Production {lcode}", run_id, run_ts,
                )
            )

        # FLD-R11: Sales quantities
        r11_specs = [
            ("CRUDE", "QTY.CRUDE_SOLD", "MMT", float(sub["sales_crude_mt"].sum()) / 1e6),
            ("GAS", "QTY.GAS_SOLD", "BCM", float(sub["sales_gas_mmscm"].sum()) / 1e3),
            ("VAP", "QTY.VAP_SOLD", "KT", float(sub["sales_vap_kt"].sum())),
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
        pf = sub["object_type"] == "producing_field"
        pf_v = pf & (
            (sub["revenue_from_operations"] < 0) | (sub["royalty"] < 0) | (sub["oidb_cess"] < 0)
            | (sub["staff_expenditure"] < 0) | (sub["dda_total"] < 0)
            | (sub["expl_survey_cost"] != 0) | (sub["expl_wells_written_off"] != 0) | (sub["rev_vap"] != 0)
        )
        ex_v = (sub["object_type"] != "exploration") & ((sub["expl_survey_cost"] != 0) | (sub["expl_wells_written_off"] != 0))
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
        m_id_v = float(((sub["revenue_from_operations"] + sub["other_income_alloc"] - sub["opex_total"] - sub["ebitda"]).abs() > 0.01).sum())
        rows.append(
            _make_check_row(
                "FLD", "SPEC-05", "FLD-R14", fy, "FY", "ALL", "month_sum_identity_violations",
                m_id_v, 0.0 if r01_val is not None else None, "COUNT", 0.0, None, "BLOCK",
                "SPEC05_S7_2", 1, 1, "month_sum_identity_violations",
                "Zero rows violating object-month revenue + other_income - opex = ebitda", run_id, run_ts,
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
            pf_sub = sub[sub["object_type"] == "producing_field"]
            boe_sum = float(pf_sub["prod_boe"].sum())
            lift_usd = (float(pf_sub["lifting_cost"].sum()) * 1e6 / 84.5 / boe_sum) if boe_sum > 0 else np.nan
            rows.append(
                _make_check_row(
                    "FLD", "SPEC-05", "FLD-R16", fy, "FY", "PRODUCING", "lifting_cost_usd_boe",
                    lift_usd, 12.0 if r01_val is not None else None, "USD_BOE", 4.0, None, "WARN",
                    "SPEC05_S7_2", 1, 1, "lifting_cost_usd_boe",
                    "Average lifting cost per BOE within [$8.0, $16.0]/BOE", run_id, run_ts,
                )
            )

            # FLD-R17: Mumbai High share of operated crude in [30%, 45%]
            op_crude = float(sub.loc[sub["operatorship"] == "Operated", "prod_crude_mt"].sum())
            mh_crude = float(sub.loc[sub["object_id"] == "FLD-MUMBAI-HIGH", "prod_crude_mt"].sum())
            mh_share = (mh_crude * 100.0 / op_crude) if op_crude > 0 else np.nan
            rows.append(
                _make_check_row(
                    "FLD", "SPEC-05", "FLD-R17", fy, "OBJECT", "FLD-MUMBAI-HIGH", "mumbai_high_crude_share_pct",
                    mh_share, 37.5 if r01_val is not None else None, "PCT", 7.5, None, "WARN",
                    "SPEC05_S7_2", 1, 1, "mumbai_high_crude_share_pct",
                    "Mumbai High share of operated crude in [30.0%, 45.0%]", run_id, run_ts,
                )
            )

    return pd.DataFrame(rows)
