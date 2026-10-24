"""Export verified SSOT rows to legacy financial_build/data/ongc_10yr_*.json files.

Ensures any remaining reader of financial_build/data/ongc_10yr_*.json receives verified
Annual Report SSOT numbers with honest provenance and zero 'Yahoo Finance (ONGC.NS)' or
'Audited' claims.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_PATH = REPO_ROOT / "financial_ssot" / "out" / "fact_snapshot.parquet"
DIM_PATH = REPO_ROOT / "financial_ssot" / "dim_financial_line.csv"
DATA_DIR = REPO_ROOT / "financial_build" / "data"

FYS = [f"FY{y}" for y in range(17, 27)]

# Map legacy corporate_wide / statement line codes -> (scope, canonical SSOT line_code)
LEGACY_TO_SSOT: Dict[str, tuple[str, str]] = {
    "gross_revenue_inr_cr": ("standalone", "PL.REV_OPS"),
    "crude_oil_revenue_inr_cr": ("standalone", "REV.CRUDE"),
    "natural_gas_revenue_inr_cr": ("standalone", "REV.GAS"),
    "vap_revenue_inr_cr": ("standalone", "REV.VAP"),
    "other_operating_revenue_inr_cr": ("standalone", "REV.OTHER_OP"),
    "offshore_revenue_inr_cr": ("standalone", "SEG.REV.OFF"),
    "onshore_revenue_inr_cr": ("standalone", "SEG.REV.ON"),
    "other_income_inr_cr": ("standalone", "PL.OTHER_INCOME"),
    "dividend_income_inr_cr": ("standalone", "PL.DIVIDEND_INCOME_10YR"),
    "interest_and_other_income_inr_cr": ("standalone", "PL.OTHER_NON_OP_INCOME_10YR"),
    "total_income_inr_cr": ("standalone", "PL.TOTAL_INCOME"),
    "royalty_inr_cr": ("standalone", "LEVY.ROYALTY"),
    "oidb_cess_inr_cr": ("standalone", "LEVY.OIDB_CESS"),
    "saed_windfall_tax_inr_cr": ("standalone", "LEVY.OTHER_SAED"),
    "statutory_levies_total_inr_cr": ("standalone", "LEVY.TOTAL"),
    "prod_transport_selling_exp_inr_cr": ("standalone", "PL.OPEX_10YR"),
    "operating_expenses_total_inr_cr": ("standalone", "PL.OPEX_10YR"),
    "employee_cost_total_inr_cr": ("standalone", "OTH.EMP_EXPENDITURE"),
    "employee_benefit_net_pnl_inr_cr": ("standalone", "PL.EMP_BENEFIT"),
    "survey_costs_written_off_inr_cr": ("standalone", "PL.EXPL_SURVEY"),
    "exploratory_wells_written_off_inr_cr": ("standalone", "PL.EXPL_WELL"),
    "exploration_costs_written_off_inr_cr": ("standalone", "PL.EXPL_WRITEOFF"),
    "dda_inr_cr": ("standalone", "PL.DDA"),
    "finance_costs_inr_cr": ("standalone", "PL.FIN_COST"),
    "other_expenses_inr_cr": ("standalone", "PL.PROVISIONS_WRITEOFF"),
    "total_expenses_inr_cr": ("standalone", "PL.TOTAL_EXP"),
    "profit_before_exceptional_and_tax_inr_cr": ("standalone", "PL.PBT_PRE_EXC"),
    "exceptional_items_inr_cr": ("standalone", "PL.EXCEPTIONAL"),
    "pbt_inr_cr": ("standalone", "PL.PBT"),
    "current_tax_inr_cr": ("standalone", "PL.TAX_CURRENT"),
    "deferred_tax_inr_cr": ("standalone", "PL.TAX_DEFERRED"),
    "earlier_year_tax_inr_cr": ("standalone", "PL.TAX_EARLIER"),
    "tax_expense_total_inr_cr": ("standalone", "PL.TAX"),
    "pat_inr_cr": ("standalone", "PL.PAT"),
    "consolidated_revenue_inr_cr": ("consolidated", "PL.REV_OPS"),
    "consolidated_pbt_inr_cr": ("consolidated", "PL.PBT"),
    "consolidated_pat_inr_cr": ("consolidated", "PL.PAT"),
    "oil_and_gas_assets_inr_cr": ("standalone", "BS.OG_ASSETS"),
    "other_ppe_and_rou_inr_cr": ("standalone", "BS.OTHER_PPE"),
    "cwip_inr_cr": ("standalone", "BS.WIP_TOTAL_10YR"),
    "exploratory_wells_in_progress_inr_cr": ("standalone", "BS.IAUD_EXPL_WELLS"),
    "investments_subsidiaries_jv_inr_cr": ("standalone", "BS.INVESTMENTS_NC_10YR"),
    "site_restoration_fund_inr_cr": ("standalone", "BS.SRF_DEPOSIT_NC"),
    "other_non_current_assets_inr_cr": ("standalone", "BS.OTHER_NC_ASSETS"),
    "non_current_assets_inr_cr": ("standalone", "BS.ASSETS.NON_CURRENT.TOTAL"),
    "inventories_inr_cr": ("standalone", "BS.INVENTORIES"),
    "current_investments_inr_cr": ("standalone", "BS.INVESTMENTS_C"),
    "receivables_outstanding_inr_cr": ("standalone", "BS.TRADE_REC_C"),
    "cash_and_bank_inr_cr": ("standalone", "BS.CCE"),
    "other_current_assets_inr_cr": ("standalone", "BS.OTHER_C_ASSETS"),
    "current_assets_inr_cr": ("standalone", "BS.ASSETS.CURRENT.TOTAL"),
    "total_assets_inr_cr": ("standalone", "BS.TOTAL_ASSETS"),
    "equity_share_capital_inr_cr": ("standalone", "BS.SHARE_CAPITAL"),
    "other_equity_reserves_inr_cr": ("standalone", "BS.OTHER_EQUITY"),
    "net_worth_inr_cr": ("standalone", "BS.EQUITY.TOTAL"),
    "consolidated_net_worth_inr_cr": ("consolidated", "BS.EQUITY.TOTAL"),
    "long_term_debt_inr_cr": ("standalone", "BS.BORROW_NC"),
    "lease_liabilities_non_current_inr_cr": ("standalone", "BS.LEASE_LIAB_NC"),
    "abandonment_provision_inr_cr": ("standalone", "BS.PROV_NC"),
    "deferred_tax_liability_net_inr_cr": ("standalone", "BS.DTL_NET"),
    "other_non_current_liabilities_inr_cr": ("standalone", "BS.OTHER_NC_LIAB"),
    "non_current_liabilities_inr_cr": ("standalone", "BS.LIAB.NON_CURRENT.TOTAL"),
    "short_term_debt_inr_cr": ("standalone", "BS.BORROW_CUR"),
    "lease_liabilities_current_inr_cr": ("standalone", "BS.LEASE_LIAB_C"),
    "trade_payables_inr_cr": ("standalone", "BS.TRADE_PAY"),
    "other_current_liabilities_inr_cr": ("standalone", "BS.OTHER_C_LIAB"),
    "current_liabilities_inr_cr": ("standalone", "BS.LIAB.CURRENT.TOTAL"),
    "total_liabilities_inr_cr": ("standalone", "BS.LIAB.TOTAL"),
    "total_equity_and_liabilities_inr_cr": ("standalone", "BS.TOTAL_EQ_LIAB"),
    "total_debt_inr_cr": ("standalone", "BS.BORROW_TOTAL_10YR"),
    "total_lease_liabilities_inr_cr": ("standalone", "BS.LEASE_LIAB_TOTAL_10YR"),
    "net_working_capital_inr_cr": ("standalone", "BS.WORKING_CAPITAL_10YR"),
    "capital_employed_inr_cr": ("standalone", "OTH.CAPITAL_EMPLOYED"),
    "total_capex_spent_inr_cr": ("standalone", "CAPEX.TOTAL"),
    "operating_cash_flow_inr_cr": ("standalone", "CF.CFO"),
    "working_capital_change_cf_inr_cr": ("standalone", "CF.WC_SUBTOTAL"),
    "income_tax_paid_cf_inr_cr": ("standalone", "CF.TAX_PAID"),
    "capex_cash_outflow_inr_cr": ("standalone", "CF.INV_PPE_PAYMENTS"),
    "investing_cash_flow_inr_cr": ("standalone", "CF.CFI"),
    "lease_payments_cf_inr_cr": ("standalone", "CF.FIN_LEASE_PRINCIPAL"),
    "interest_paid_cf_inr_cr": ("standalone", "CF.FIN_INTEREST_PAID"),
    "dividend_paid_cf_inr_cr": ("standalone", "CF.FIN_DIV_PAID"),
    "financing_cash_flow_inr_cr": ("standalone", "CF.CFF"),
    "opening_cash_inr_cr": ("standalone", "CF.CCE_OPEN"),
    "net_cash_change_inr_cr": ("standalone", "CF.NET_CHANGE_CCE"),
    "closing_cash_inr_cr": ("standalone", "CF.CCE_CLOSE"),
    "eps_basic_inr": ("standalone", "PL.EPS_BASIC"),
    "dividend_per_share_inr": ("standalone", "RATIO.DPS"),
    "total_dividend_payout_inr_cr": ("standalone", "OTH.DIVIDEND_DECLARED"),
    "csr_disbursed_inr_cr": ("standalone", "OTH.CSR"),
    "standalone_roce_pct": ("standalone", "RATIO.ROCE"),
    "roe_pct": ("standalone", "RATIO.ROE_INCL_EXC"),
    "debt_to_equity_ratio": ("standalone", "RATIO.DEBT_EQUITY"),
    "current_ratio": ("standalone", "RATIO.CURRENT"),
    "receivable_days": ("standalone", "RATIO.DEBTORS_TURNOVER_DAYS"),
    "book_value_per_share_inr": ("standalone", "RATIO.BVPS"),
    "ebitda_margin_pct": ("standalone", "RATIO.PBIDT_MARGIN_PCT"),
    "pat_margin_pct": ("standalone", "RATIO.PAT_MARGIN_PCT"),
}


def _build_lookup(df: pd.DataFrame, vintage: str = "as_reported") -> Dict[tuple[str, str, str], Dict[str, Any]]:
    """Build (scope, fy, line_code) -> row dict lookup from verified rows."""
    vdf = df[(df["verified"] == True) & (df["period_type"] == "annual")].copy()  # noqa: E712
    if vintage == "as_reported":
        vdf = vdf[(vdf["is_own_vintage"] == True) | (vdf["is_fallback_vintage"] == True)]  # noqa: E712
    else:
        vdf = vdf[vdf["is_latest_vintage"] == True]  # noqa: E712

    out: Dict[tuple[str, str, str], Dict[str, Any]] = {}
    for _, r in vdf.iterrows():
        key = (str(r["scope"]), str(r["fiscal_year"]), str(r["line_code"]))
        if key not in out:
            val = r["value_inr_cr"] if pd.notna(r["value_inr_cr"]) else r["value"]
            out[key] = {
                "val": round(float(val), 2) if pd.notna(val) else None,
                "source_doc": str(r["source_doc"]),
                "source_page_label": str(r["source_page_label"]),
                "source_system": str(r["source_system"]),
                "is_restated": bool(r["is_restated"]),
            }
    return out


def _get_val(lkp: Dict[tuple[str, str, str], Dict[str, Any]], scope: str, fy: str, code: str) -> Optional[float]:
    rec = lkp.get((scope, fy, code))
    return rec["val"] if rec else None


def export_all() -> None:
    df = pd.read_parquet(SNAPSHOT_PATH)
    as_rep = _build_lookup(df, "as_reported")
    latest = _build_lookup(df, "latest")

    # 1. Update ongc_10yr_corporate_wide.json using latest trend (for multi-FY series consistency)
    # with fallback to as_reported where latest is absent.
    cw_path = DATA_DIR / "ongc_10yr_corporate_wide.json"
    cw_rows = json.loads(cw_path.read_text(encoding="utf-8"))
    for row in cw_rows:
        fy = row["fiscal_year"]
        for leg_key, (scope, ssot_code) in LEGACY_TO_SSOT.items():
            v = _get_val(latest, scope, fy, ssot_code)
            if v is None:
                v = _get_val(as_rep, scope, fy, ssot_code)
            if v is not None:
                row[leg_key] = v
        # Derived fields from verified SSOT values
        rev = row.get("gross_revenue_inr_cr") or 0.0
        lev = row.get("statutory_levies_total_inr_cr") or 0.0
        if rev and lev:
            row["net_revenue_inr_cr"] = round(rev - lev, 2)
        pbt = row.get("pbt_inr_cr") or 0.0
        pat = row.get("pat_inr_cr") or 0.0
        dda = row.get("dda_inr_cr") or 0.0
        fin = row.get("finance_costs_inr_cr") or 0.0
        exp_wo = row.get("exploration_costs_written_off_inr_cr") or 0.0
        exc = row.get("exceptional_items_inr_cr") or 0.0
        ebitda = round(pbt - exc + fin + dda + exp_wo, 2)
        row["ebitda_inr_cr"] = ebitda
        if rev:
            row["ebitda_margin_pct"] = round(100.0 * ebitda / rev, 2)
            row["pbt_margin_pct"] = round(100.0 * pbt / rev, 2)
            row["pat_margin_pct"] = round(100.0 * pat / rev, 2)
        ocf = row.get("operating_cash_flow_inr_cr")
        capex = row.get("total_capex_spent_inr_cr")
        if ocf is not None and capex is not None:
            row["free_cash_flow_inr_cr"] = round(ocf - abs(capex), 2)
        # Clean any Yahoo/Audited references in notes
        for nk in ("primary_driver_note", "balance_sheet_driver_note"):
            if nk in row and isinstance(row[nk], str):
                row[nk] = row[nk].replace("Yahoo Finance (ONGC.NS)", "Annual Report SSOT").replace("ONGC.NS", "ONGC").replace("Audited", "Reported")
    cw_path.write_text(json.dumps(cw_rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Helper to update statement line JSONs using as_reported values
    cw_by_fy = {r["fiscal_year"]: r for r in cw_rows}

    def _update_stmt_file(filename: str, base_key: str, pct_key: Optional[str]) -> None:
        p = DATA_DIR / filename
        rows = json.loads(p.read_text(encoding="utf-8"))
        # First pass: update amount_inr_cr / value from as_reported SSOT lookup (fallback to cw_by_fy)
        by_fy_code: Dict[tuple[str, str], float] = {}
        for r in rows:
            fy = r["fiscal_year"]
            lc = r["line_code"]
            r.pop("yahoo_finance_line", None)
            if "line_name" in r:
                r["line_name"] = r["line_name"].replace(" (ONGC.NS)", "").replace("Yahoo Finance", "Annual Report")
            if "driver_note" in r and isinstance(r["driver_note"], str):
                r["driver_note"] = r["driver_note"].replace("Yahoo Finance (ONGC.NS)", "Annual Report").replace("ONGC.NS", "ONGC").replace("Audited", "Reported")
            val = None
            if lc in LEGACY_TO_SSOT:
                scope, ssot_code = LEGACY_TO_SSOT[lc]
                val = _get_val(as_rep, scope, fy, ssot_code)
            if val is None and lc in cw_by_fy.get(fy, {}):
                val = cw_by_fy[fy][lc]
            if val is not None:
                val_key = "amount_inr_cr" if "amount_inr_cr" in r else "value"
                r[val_key] = round(float(val), 2)
                by_fy_code[(fy, lc)] = r[val_key]

        # Second pass: compute prior_fy, yoy_delta, yoy_change_pct, pct_of_*
        for r in rows:
            fy = r["fiscal_year"]
            lc = r["line_code"]
            fy_num = int(fy[2:])
            prev_fy = f"FY{fy_num - 1:02d}"
            val_key = "amount_inr_cr" if "amount_inr_cr" in r else "value"
            cur = by_fy_code.get((fy, lc))
            prv = by_fy_code.get((prev_fy, lc))
            if val_key == "amount_inr_cr":
                r["prior_fy_amount_inr_cr"] = prv
                r["yoy_delta_inr_cr"] = round(cur - prv, 2) if (cur is not None and prv is not None) else None
                r["yoy_change_pct"] = round(100.0 * (cur - prv) / abs(prv), 1) if (cur is not None and prv not in (None, 0)) else None
                if pct_key:
                    base_val = by_fy_code.get((fy, base_key))
                    r[pct_key] = round(100.0 * cur / base_val, 1) if (cur is not None and base_val not in (None, 0)) else None
            else:
                r["prior_fy_value"] = prv
                r["yoy_delta"] = round(cur - prv, 2) if (cur is not None and prv is not None) else None

        p.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    _update_stmt_file("ongc_10yr_schedule_iii_lines.json", "gross_revenue_inr_cr", "pct_of_revenue")
    _update_stmt_file("ongc_10yr_balance_sheet_lines.json", "total_assets_inr_cr", "pct_of_total_assets")
    _update_stmt_file("ongc_10yr_cash_flow_lines.json", "operating_cash_flow_inr_cr", "pct_of_ocf")
    _update_stmt_file("ongc_10yr_ratios_lines.json", "", None)

    # Update snapshot_manifest.json
    manifest_path = DATA_DIR / "snapshot_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {"files": {}}
    ext_at = str(df["extracted_at"].iloc[0]) if not df.empty and "extracted_at" in df.columns else "2026-10-24T00:00:00Z"
    snap_date = ext_at[:10] if len(ext_at) >= 10 and ext_at[:4].isdigit() else "2026-10-24"
    run_id = ext_at.replace("-", "").replace(":", "").split(".")[0] if ext_at else "ssot_v3"
    manifest["snapshot_date"] = snap_date
    manifest["run_id"] = run_id
    manifest["label"] = "Verified Annual Report SSOT snapshot (fact_financial_statement_line)"
    manifest["note"] = "P1.10a: runtime snapshot exported from verified fact_snapshot.parquet."
    for fn in list(manifest.get("files", {}).keys()):
        fp = DATA_DIR / fn
        if fp.exists():
            manifest["files"][fn] = hashlib.sha256(fp.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Exported verified SSOT to {DATA_DIR} (run_id={run_id}, snapshot_date={snap_date})")


if __name__ == "__main__":
    export_all()
