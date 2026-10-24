"""Deterministic verification gates V01-V12 for the Yukti v3 financial SSOT (SPEC-01 §6, Packet P1.6).

Gates (SPEC-01 §6 / Packet P1.6):
- V01: Subtotal exact — for each subtotal/total line with a formula, signed sum of components == printed total
       (tolerance <= 0.05 cr for AR 2-dp; <= 0.50 cr when children come from 0-dp 10-yr table).
- V02: No plugs — no line may be computed/plugged; `extraction_method` must be in
       {'text_parse', 'xbrl', 'yahoo_api', 'gemini_table', 'manual'} (and 'manual' requires notes).
- V03: Balance sheet identity — BS.TOTAL_ASSETS == BS.EQUITY.TOTAL + BS.LIAB.NON_CURRENT.TOTAL + BS.LIAB.CURRENT.TOTAL
       (or BS.EQUITY.TOTAL + BS.LIAB.TOTAL / BS.TOTAL_EQ_LIAB) within tolerance (<= 0.05 cr for AR 2-dp).
- V04: Cash tie-out — CF.CCE_CLOSE (CF statement) == BS.CCE (BS) for the same FY and scope (or net of bank overdraft
       per D-57); CF.CFO + CF.CFI + CF.CFF == CF.NET_CHANGE_CCE; CF.CCE_OPEN + CF.NET_CHANGE_CCE + FX == CF.CCE_CLOSE.
- V05: P&L chain — PL.TOTAL_INCOME = PL.REV_OPS + PL.OTHER_INCOME; PL.PBT_PRE_EXC = PL.TOTAL_INCOME - PL.TOTAL_EXP;
       PL.PBT = PL.PBT_PRE_EXC + PL.EXCEPTIONAL (+ JV share for AR consolidated); PL.PAT = PL.PBT - PL.TAX; PL.TCI = PL.PAT + PL.OCI.
- V06: Note & SOCE link — Note totals tie to statement lines (Note 30==PL.REV_OPS, Note 31==PL.OTHER_INCOME,
       Note 35==PL.PROD_EXP, Note 36==PL.FIN_COST, Note 37==PL.DDA, Note 38==PL.TAX, Note 22==BS.LEASE_LIAB_NC+C,
       Segment rev/PBT/assets==statement totals, CF.START_PROFIT==PL.PAT).
- V07: Cross-AR comparative — FY value in AR(FY) == comparative in AR(FY+1) within <= 0.05 cr or raw_is_restated=True;
       unflagged restatements fail V07 and open a conflict (`status='open'`); >1% restatements also open a conflict.
- V08: 10-yr vs statement — 10-yr table value (INR_mn, 0-dp) == full-statement value within <= 0.10 cr or raw_is_restated=True.
- V09: 10-yr cross-edition — AR FY22 vs AR FY24 vs AR FY26 10-yr tables agree on overlapping years within <= 0.10 cr
       (or half-unit for ratios/pct), or later edition marks `*` (raw_is_restated=True); unflagged & >1% logged as `status='open'`.
- V10: XBRL cross-check — XBRL FourD/OneI value == AR value within <= 0.50 cr (or cross-vintage raw_is_restated=True).
- V11: Yahoo cross-check (conditional: runs when Yahoo rows exist; absence never blocks verified) & scope/magnitude sanity
       (consolidated > standalone * 1.05 on PL.REV_OPS and BS.TOTAL_ASSETS).
- V12: Coverage & vintage completeness — every annual (FY, scope, line_code) has is_own_vintage/is_fallback_vintage and
       is_latest_vintage; evaluates is_kpi × FY coverage (standalone FY17-FY26, consolidated FY22-FY26, 10-yr FY13-FY26)
       and lists every missing KPI×FY cell.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

VALID_EXTRACTION_METHODS: Set[str] = {
    "text_parse",
    "xbrl",
    "yahoo_api",
    "gemini_table",
    "manual",
}

GATE_METADATA: Dict[str, Tuple[str, str]] = {
    "V01": ("Subtotal exact", "Signed sum of child lines equals AR-printed subtotal/total (<=0.05 cr AR 2-dp; <=0.50 cr 10-yr 0-dp)."),
    "V02": ("No plugs", "Zero computed/plugged lines; extraction_method in {text_parse, xbrl, yahoo_api, gemini_table, manual}."),
    "V03": ("Balance sheet identity", "BS.TOTAL_ASSETS == BS.EQUITY.TOTAL + BS.LIAB.NON_CURRENT.TOTAL + BS.LIAB.CURRENT.TOTAL (<=0.05 cr)."),
    "V04": ("Cash tie-out", "CF.CCE_CLOSE == BS.CCE (or net of bank OD per D-57) and CF.CFO + CF.CFI + CF.CFF == CF.NET_CHANGE_CCE (<=0.05 cr)."),
    "V05": ("P&L chain", "REV_OPS+OTHER_INCOME==TOTAL_INCOME; TOTAL_INCOME-TOTAL_EXP==PBT_PRE_EXC; PBT_PRE_EXC+EXC(+JV)==PBT; PBT-TAX==PAT; PAT+OCI==TCI."),
    "V06": ("Note & cross-statement link", "Notes 30/31/35/36/37/38/22/44 and CF.START_PROFIT tie to P&L/BS face totals (<=0.05 cr)."),
    "V07": ("Cross-AR comparative", "Comparative column in AR(FY+1) matches AR(FY) within <=0.05 cr or prints `*`/Restated (`raw_is_restated`)."),
    "V08": ("10-yr vs statement", "10-yr summary value (0-dp INR_mn) matches full-statement value within <=0.10 cr or prints `*` (`raw_is_restated`)."),
    "V09": ("10-yr cross-edition", "AR FY22, AR FY24, AR FY26 10-yr editions agree within <=0.10 cr or print `*` (`raw_is_restated`)."),
    "V10": ("XBRL cross-check", "XBRL filing value matches AR value within <=0.50 cr (or cross-vintage `raw_is_restated`)."),
    "V11": ("Yahoo & scope cross-check", "Conditional Yahoo vs AR consolidated check (<=1.0 cr when loaded) plus consolidated > standalone * 1.05 on REV_OPS & TOTAL_ASSETS."),
    "V12": ("Coverage & vintage completeness", "Annual vintage flags present and KPI × FY coverage matrix (SA FY17-26, CO FY22-26, 10-yr FY13-26) audited with gap list."),
}

CONFLICT_COLUMNS = [
    "fiscal_year",
    "scope",
    "line_code",
    "source_a",
    "value_a",
    "source_b",
    "value_b",
    "delta_inr_cr",
    "pct_delta",
    "rule_id",
    "status",
    "resolution_rule",
    "resolution",
    "resolved_by",
    "resolved_at",
]

# Synonym groups so both SPEC-01 §5.2 codes and legacy aliases resolve in fixtures
LINE_SYNONYMS: Dict[str, Tuple[str, ...]] = {
    "BS.EQUITY.TOTAL": ("BS.EQUITY.TOTAL", "BS.EQUITY_TOTAL"),
    "BS.LIAB.TOTAL": ("BS.LIAB.TOTAL", "BS.LIAB_TOTAL"),
    "BS.CCE": ("BS.CCE", "BS.CASH_AND_EQ"),
    "CF.CFO": ("CF.CFO", "CF.NET_CASH_OPS"),
    "CF.CFI": ("CF.CFI", "CF.NET_CASH_INV"),
    "CF.CFF": ("CF.CFF", "CF.NET_CASH_FIN"),
    "PL.PBT_PRE_EXC": ("PL.PBT_PRE_EXC", "PL.PBT_BEFORE_EXC"),
    "PL.TAX": ("PL.TAX", "PL.TAX_TOTAL"),
    "PL.OCI": ("PL.OCI", "PL.OCI_TOTAL"),
    "PL.TCI": ("PL.TCI", "PL.TCI_TOTAL"),
}


def normalize_vintage(v: Any) -> str:
    """Normalise report_vintage strings such as 'AR_FY2023-24' -> 'AR_FY24'."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    s = str(v).strip()
    m = re.match(r"^(AR|XBRL)_FY\d{2}(\d{2})-(\d{2})$", s)
    if m:
        return f"{m.group(1)}_FY{m.group(3)}"
    m2 = re.match(r"^(AR|XBRL)_FY20(\d{2})$", s)
    if m2:
        return f"{m2.group(1)}_FY{m2.group(2)}"
    return s


def fy_number(fy: Any) -> Optional[int]:
    """Extract 2-digit fiscal year integer from 'FY24' -> 24."""
    if fy is None or (isinstance(fy, float) and math.isnan(fy)):
        return None
    m = re.search(r"FY(\d{2})$", str(fy).strip())
    return int(m.group(1)) if m else None


def vintage_fy_number(v: Any) -> Optional[int]:
    """Extract 2-digit fiscal year integer from 'AR_FY24' or 'AR_FY2023-24' -> 24."""
    nv = normalize_vintage(v)
    m = re.search(r"_FY(\d{2})$", nv)
    return int(m.group(1)) if m else None


@dataclass
class GateRunResult:
    """Result container from `verify_gates`, supporting both attribute access and tuple unpacking `(df, conflicts)`."""

    df: pd.DataFrame
    conflicts: pd.DataFrame
    gate_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    coverage_gaps: List[Dict[str, str]] = field(default_factory=list)
    run_id: str = ""
    run_at: str = ""

    def __iter__(self):
        yield self.df
        yield self.conflicts

    @property
    def all_reported_verified(self) -> bool:
        ar_rows = self.df[self.df["source_system"].isin(["ar", "xbrl"])]
        if ar_rows.empty:
            return bool(self.df["verified"].all())
        return bool(ar_rows["verified"].all())

    def to_markdown(self) -> str:
        return render_gate_report_md(self)

    def gate_run_rows(self) -> pd.DataFrame:
        """Return a DataFrame matching `hrfin_gold.fin_gate_run` schema."""
        rows = []
        for gid in [f"V{i:02d}" for i in range(1, 13)]:
            st = self.gate_stats.get(gid, {})
            rows.append(
                {
                    "run_id": self.run_id,
                    "run_at": self.run_at,
                    "gate_id": gid,
                    "gate_name": GATE_METADATA[gid][0],
                    "rows_checked": int(st.get("checked", 0)),
                    "rows_passed": int(st.get("passed", 0)),
                    "rows_failed": int(st.get("failed", 0)),
                    "max_delta_inr_cr": round(float(st.get("max_delta_inr_cr", 0.0)), 4),
                    "examples": json.dumps(st.get("examples", []), ensure_ascii=False),
                }
            )
        return pd.DataFrame(rows)


def compute_vintage_flags(df: pd.DataFrame, tol_2dp_cr: float = 0.05, tol_10yr_cr: float = 0.10) -> pd.DataFrame:
    """Compute `is_own_vintage`, `is_fallback_vintage`, `is_latest_vintage`, and `is_restated` per SPEC-01 §5.1 & §7.1.

    Rules (B3 & I1):
    - Only `period_type == 'annual'` rows may have `is_own_vintage`, `is_fallback_vintage`, or `is_latest_vintage` = True.
      Quarterly (`period_type == 'quarter'`) and opening balance sheet (`period_type == 'opening'`) rows always have all three False.
    - `is_own_vintage = True` ONLY when the annual row comes from that FY's own AR (`vintage_fy == fy_num` and `source_system == 'ar'`),
      or from that FY's own XBRL (`vintage_fy == fy_num` and `source_system == 'xbrl'`) when no own-year AR exists (e.g. FY20/FY21).
    - When no own-year vintage exists for an annual `(fiscal_year, scope, line_code)` (e.g. FY16 from AR_FY17 comparative, or
      10-yr summary lines in FY13-FY19/FY23/FY25 from AR_FY22/AR_FY24/AR_FY26), `is_own_vintage` is False and the earliest
      available annual row gets `is_fallback_vintage = True`.
    - `raw_is_restated` preserves the printed `*` / `Restated` column marker from the source and is NEVER overwritten by
      inferred differences. `is_restated` is True when `raw_is_restated` is True OR when a later AR vintage differs from
      the earliest/own vintage beyond tolerance.
    """
    out = df.copy()
    if "raw_is_restated" not in out.columns:
        out["raw_is_restated"] = out["is_restated"].fillna(False).astype(bool) if "is_restated" in out.columns else False
    else:
        out["raw_is_restated"] = out["raw_is_restated"].fillna(False).astype(bool)
    out["is_restated"] = out["raw_is_restated"].copy()

    out["_norm_vintage"] = out["report_vintage"].map(normalize_vintage)
    out["_vnum"] = out["_norm_vintage"].map(vintage_fy_number).fillna(999).astype(int)
    out["_fynum"] = out["fiscal_year"].map(fy_number).fillna(-1).astype(int)
    out["_is_ar"] = (out["source_system"] == "ar").astype(int)
    out["_is_stmt"] = (~out["source_table"].isin(["ten_year_summary"])).astype(int)

    out["is_own_vintage"] = False
    out["is_fallback_vintage"] = False
    out["is_latest_vintage"] = False

    ann_df = out[out["period_type"] == "annual"]
    grp_cols = ["fiscal_year", "scope", "line_code"]
    for _, grp in ann_df.groupby(grp_cols, dropna=False):
        if grp.empty:
            continue
        # 1. Strictly determine own vintage vs fallback vintage:
        own_idx: Optional[int] = None
        fallback_idx: Optional[int] = None
        own_ar = grp[(grp["_is_ar"] == 1) & (grp["_vnum"] == grp["_fynum"])]
        if not own_ar.empty:
            own_idx = int(own_ar.sort_values(["_is_stmt", "_vnum"], ascending=[False, True]).index[0])
            out.at[own_idx, "is_own_vintage"] = True
        else:
            own_xbrl = grp[(grp["source_system"] == "xbrl") & (grp["_vnum"] == grp["_fynum"])]
            if not own_xbrl.empty:
                own_idx = int(own_xbrl.index[0])
                out.at[own_idx, "is_own_vintage"] = True
            else:
                ar_only = grp[grp["_is_ar"] == 1]
                if not ar_only.empty:
                    fallback_idx = int(ar_only.sort_values(["_vnum", "_is_stmt"], ascending=[True, False]).index[0])
                else:
                    fallback_idx = int(grp.sort_values(["_vnum"], ascending=[True]).index[0])
                out.at[fallback_idx, "is_fallback_vintage"] = True

        # Check later AR vintages against base vintage (own_idx or fallback_idx) to set `is_restated = True` when |delta| > tolerance
        base_idx = own_idx if own_idx is not None else fallback_idx
        assert base_idx is not None
        base_val = out.at[base_idx, "value_inr_cr"] if "value_inr_cr" in out.columns else None
        base_nat = out.at[base_idx, "value"] if "value" in out.columns else None
        base_prec = (
            float(out.at[base_idx, "precision_inr_cr"])
            if "precision_inr_cr" in out.columns and not pd.isna(out.at[base_idx, "precision_inr_cr"])
            else 0.01
        )
        base_vnum = int(out.at[base_idx, "_vnum"])

        for idx_raw, r in grp.iterrows():
            idx = int(idx_raw)
            if idx == base_idx or int(r["_is_ar"]) == 0:
                continue
            if int(r["_vnum"]) <= base_vnum:
                continue
            # When base_idx is XBRL (e.g. FY21 standalone PL.TAX_CURRENT), CurrentTax in XBRL includes
            # PL.TAX_EARLIER, whereas AR splits PL.TAX_CURRENT and PL.TAX_EARLIER; only flag genuine restatements.
            if str(out.at[base_idx, "source_system"]) == "xbrl" and str(r["line_code"]) == "PL.TAX_CURRENT" and str(r["scope"]) == "standalone":
                continue
            r_prec = float(r["precision_inr_cr"]) if "precision_inr_cr" in out.columns and not pd.isna(r["precision_inr_cr"]) else 0.01
            tol = (tol_2dp_cr + 1e-6) if (base_prec <= 0.01 and r_prec <= 0.01) else (max(base_prec, r_prec, tol_10yr_cr) + 1e-6)
            r_val = r.get("value_inr_cr")
            if base_val is not None and not pd.isna(base_val) and r_val is not None and not pd.isna(r_val):
                if abs(float(r_val) - float(base_val)) > tol:
                    out.at[idx, "is_restated"] = True
            elif base_nat is not None and not pd.isna(base_nat) and r.get("value") is not None and not pd.isna(r.get("value")):
                if abs(float(r["value"]) - float(base_nat)) > (0.05 + 1e-6):
                    out.at[idx, "is_restated"] = True

        # 2. Determine latest vintage row (at most 1 annual row per (fiscal_year, scope, line_code)):
        ar_cands = grp[grp["_is_ar"] == 1]
        if not ar_cands.empty:
            ar_sorted = ar_cands.sort_values(["_vnum", "_is_stmt"], ascending=[False, False])
            top_idx = int(ar_sorted.index[0])
            top_row = out.loc[top_idx]
            stmt_cands = ar_cands[ar_cands["_is_stmt"] == 1]
            if top_row["source_table"] == "ten_year_summary" and not stmt_cands.empty:
                latest_stmt_idx = int(stmt_cands.sort_values(["_vnum"], ascending=[False]).index[0])
                latest_stmt_row = out.loc[latest_stmt_idx]
                t_val = top_row.get("value_inr_cr")
                s_val = latest_stmt_row.get("value_inr_cr")
                if (
                    t_val is not None
                    and not pd.isna(t_val)
                    and s_val is not None
                    and not pd.isna(s_val)
                    and abs(float(t_val) - float(s_val)) <= (tol_10yr_cr + 1e-6)
                ):
                    top_idx = latest_stmt_idx
            out.at[top_idx, "is_latest_vintage"] = True
        else:
            top_idx = int(grp.sort_values(["_vnum"], ascending=[False]).index[0])
            out.at[top_idx, "is_latest_vintage"] = True

    out = out.drop(columns=["_norm_vintage", "_vnum", "_fynum", "_is_ar", "_is_stmt"])
    return out


def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Populate default columns when `verify_gates` is called on a minimal test fixture DataFrame."""
    out = df.copy()
    if "period_type" not in out.columns:
        out["period_type"] = "annual"
    if "period_end" not in out.columns:
        def _default_pe(fy: Any) -> str:
            n = fy_number(fy)
            return f"20{n:02d}-03-31" if n is not None else "2024-03-31"
        out["period_end"] = out["fiscal_year"].map(_default_pe)
    if "scope" not in out.columns:
        out["scope"] = "standalone"
    if "statement" not in out.columns:
        def _guess_stmt(lc: Any) -> str:
            s = str(lc)
            if s.startswith("BS."):
                return "balance_sheet"
            if s.startswith("CF."):
                return "cash_flow"
            if s.startswith("RATIO."):
                return "ratio"
            if s.startswith(("QTY.", "PROD.")):
                return "physical"
            if s.startswith(("OTH.", "CAPEX.")):
                return "other_info"
            return "pnl"
        out["statement"] = out["line_code"].map(_guess_stmt)
    if "source_system" not in out.columns:
        def _guess_sys(v: Any) -> str:
            s = str(v).upper()
            if s.startswith("XBRL"):
                return "xbrl"
            if s.startswith("YAHOO"):
                return "yahoo"
            return "ar"
        if "report_vintage" in out.columns:
            out["source_system"] = out["report_vintage"].map(_guess_sys)
        else:
            out["source_system"] = "ar"
    if "report_vintage" not in out.columns:
        out["report_vintage"] = [
            f"{'XBRL' if str(sys).lower() == 'xbrl' else 'AR'}_{fy}"
            for fy, sys in zip(out["fiscal_year"], out["source_system"])
        ]
    if "unit" not in out.columns:
        if "unit_native" in out.columns:
            out["unit"] = out["unit_native"]
        elif "value_inr_cr" in out.columns and "value" not in out.columns:
            out["unit"] = "INR_cr"
        else:
            out["unit"] = "INR_mn"
    if "value" not in out.columns:
        if "value_native" in out.columns:
            out["value"] = out["value_native"]
        elif "value_inr_cr" in out.columns:
            out["value"] = np.where(out["unit"] == "INR_mn", out["value_inr_cr"] * 10.0, out["value_inr_cr"])
        else:
            out["value"] = np.nan
    if "value_inr_cr" not in out.columns:
        out["value_inr_cr"] = np.where(
            out["unit"] == "INR_mn",
            pd.to_numeric(out["value"], errors="coerce") / 10.0,
            np.where(
                out["unit"] == "INR_cr",
                pd.to_numeric(out["value"], errors="coerce"),
                np.where(
                    out["unit"] == "INR",
                    pd.to_numeric(out["value"], errors="coerce") / 1e7,
                    np.nan,
                ),
            ),
        )
    if "value_native" not in out.columns:
        out["value_native"] = out["value"]
    if "unit_native" not in out.columns:
        out["unit_native"] = out["unit"]
    if "precision_inr_cr" not in out.columns:
        out["precision_inr_cr"] = np.where(
            out["source_system"] == "xbrl",
            1.0,
            np.where(out.get("source_table", pd.Series(["full_statement"] * len(out))) == "ten_year_summary", 0.1, 0.001),
        )
    if "source_table" not in out.columns:
        out["source_table"] = "full_statement"
    if "source_doc" not in out.columns:
        out["source_doc"] = out["report_vintage"].astype(str)
    if "source_page" not in out.columns:
        out["source_page"] = None
    if "source_page_label" not in out.columns:
        out["source_page_label"] = None
    if "source_text_line" not in out.columns:
        out["source_text_line"] = None
    if "source_snippet" not in out.columns:
        out["source_snippet"] = None
    if "extractor_version" not in out.columns:
        out["extractor_version"] = "v3.0"
    if "extracted_at" not in out.columns:
        out["extracted_at"] = "2026-10-24T00:00:00Z"
    if "extract_id" not in out.columns:
        out["extract_id"] = None
    if "parent_line_code" not in out.columns:
        out["parent_line_code"] = None
    if "line_order" not in out.columns:
        out["line_order"] = 0
    if "line_name_as_reported" not in out.columns:
        out["line_name_as_reported"] = out["raw_label"] if "raw_label" in out.columns else out["line_code"].astype(str)
    if "raw_label" not in out.columns:
        out["raw_label"] = out["line_name_as_reported"]
    if "raw_value_text" not in out.columns:
        out["raw_value_text"] = out["value"].astype(str)
    if "extraction_method" not in out.columns:
        out["extraction_method"] = np.where(out["source_system"] == "xbrl", "xbrl", "text_parse")
    if "is_nil" not in out.columns:
        out["is_nil"] = False
    if "sign_convention" not in out.columns:
        out["sign_convention"] = "as_reported"
    if "cross_check_source" not in out.columns:
        out["cross_check_source"] = None
    if "cross_check_value" not in out.columns:
        out["cross_check_value"] = np.nan
    if "cross_check_delta_inr_cr" not in out.columns:
        out["cross_check_delta_inr_cr"] = np.nan
    if "notes" not in out.columns:
        out["notes"] = None

    # Always compute/refresh vintage flags so fixtures passed directly to verify_gates get accurate flags
    out = compute_vintage_flags(out)
    return out


def _add_conflict(
    conflicts: List[Dict[str, Any]],
    fiscal_year: str,
    scope: str,
    line_code: str,
    source_a: str,
    value_a: Optional[float],
    source_b: str,
    value_b: Optional[float],
    delta_inr_cr: Optional[float],
    rule_id: str,
    status: str = "open",
    resolution: Optional[str] = None,
    resolution_rule: Optional[str] = None,
) -> None:
    """Append a conflict row. Per B1, conflicts are NEVER auto-resolved (`status='open'`, `resolved_by=None`, `resolved_at=None`)."""
    pct_delta: Optional[float] = None
    if (
        value_a is not None
        and not pd.isna(value_a)
        and value_b is not None
        and not pd.isna(value_b)
        and delta_inr_cr is not None
        and not pd.isna(delta_inr_cr)
    ):
        denom = max(abs(float(value_a)), abs(float(value_b)), 1e-9)
        pct_delta = round(abs(float(delta_inr_cr)) / denom * 100.0, 4)

    conflicts.append(
        {
            "fiscal_year": str(fiscal_year),
            "scope": str(scope),
            "line_code": str(line_code),
            "source_a": str(source_a),
            "value_a": round(float(value_a), 4) if value_a is not None and not pd.isna(value_a) else None,
            "source_b": str(source_b),
            "value_b": round(float(value_b), 4) if value_b is not None and not pd.isna(value_b) else None,
            "delta_inr_cr": round(float(delta_inr_cr), 4) if delta_inr_cr is not None and not pd.isna(delta_inr_cr) else None,
            "pct_delta": pct_delta,
            "rule_id": str(rule_id),
            "status": "open",
            "resolution_rule": resolution_rule,
            "resolution": resolution,
            "resolved_by": None,
            "resolved_at": None,
        }
    )


def _record_gate(
    gate_stats: Dict[str, Dict[str, Any]],
    passed_rules: List[Set[str]],
    failed_rules: List[Set[str]],
    gate_id: str,
    indices: List[int],
    ok: bool,
    delta_cr: float = 0.0,
    example: Optional[str] = None,
) -> None:
    st = gate_stats[gate_id]
    st["checked"] += 1
    if not pd.isna(delta_cr):
        st["max_delta_inr_cr"] = max(float(st["max_delta_inr_cr"]), abs(float(delta_cr)))
    if example and len(st["examples"]) < 5:
        st["examples"].append(example)
    if ok:
        st["passed"] += 1
        for i in indices:
            passed_rules[i].add(gate_id)
    else:
        st["failed"] += 1
        for i in indices:
            failed_rules[i].add(gate_id)


def _lookup(code_val: Dict[str, float], code_idx: Dict[str, List[int]], canonical: str) -> Tuple[Optional[float], List[int]]:
    for cand in LINE_SYNONYMS.get(canonical, (canonical,)):
        if cand in code_val:
            return code_val[cand], code_idx.get(cand, [])
    return None, []


def verify_gates(
    df: pd.DataFrame,
    dim_df: Optional[pd.DataFrame] = None,
) -> GateRunResult:
    """Run deterministic verification gates V01-V12 on `df` and return `GateRunResult`."""
    out = _ensure_columns(df).reset_index(drop=True)
    n = len(out)

    passed_rules: List[Set[str]] = [set() for _ in range(n)]
    failed_rules: List[Set[str]] = [set() for _ in range(n)]
    gate_col_failed: Dict[str, Set[int]] = {f"V{i:02d}": set() for i in range(1, 13)}
    notes_list: List[List[str]] = [
        [str(x)] if (x is not None and not pd.isna(x) and str(x).strip()) else []
        for x in out["notes"]
    ]
    conflicts: List[Dict[str, Any]] = []
    coverage_gaps: List[Dict[str, str]] = []

    gate_stats: Dict[str, Dict[str, Any]] = {
        f"V{i:02d}": {
            "checked": 0,
            "passed": 0,
            "failed": 0,
            "max_delta_inr_cr": 0.0,
            "examples": [],
        }
        for i in range(1, 13)
    }

    out["_norm_vintage"] = out["report_vintage"].map(normalize_vintage)

    # ------------------------------------------------------------------
    # V02: No plugs (extraction_method validation on every row)
    # ------------------------------------------------------------------
    for idx, r in out.iterrows():
        em = str(r.get("extraction_method", "")).strip()
        has_manual_note = bool(notes_list[idx]) if em == "manual" else True
        ok_v02 = (em in VALID_EXTRACTION_METHODS) and has_manual_note
        ex_str = f"{r['fiscal_year']} {r['scope']} {r['line_code']} method={em}"
        _record_gate(gate_stats, passed_rules, failed_rules, "V02", [idx], ok_v02, 0.0, ex_str)
        if not ok_v02:
            gate_col_failed["V02"].add(idx)
            notes_list[idx].append(f"V02 fail: invalid or plug extraction_method='{em}'")
            _add_conflict(
                conflicts, r["fiscal_year"], r["scope"], r["line_code"],
                f"{r['source_system']}:{r['_norm_vintage']}:{em}", r.get("value_inr_cr"),
                "V02_valid_extraction_method", None,
                None, "V02", "open", "Rejected plug/computed extraction_method.",
            )

    # ------------------------------------------------------------------
    # V01, V03, V05: Intra-slice subtotals, Balance Sheet identity, P&L chain
    # ------------------------------------------------------------------
    slice_cols = ["fiscal_year", "period_type", "scope", "source_system", "_norm_vintage", "source_table"]
    for slice_key, grp in out.groupby(slice_cols, dropna=False):
        fy, ptype, scope, src_sys, nvint, stbl = slice_key
        is_10yr = stbl == "ten_year_summary"
        tol_v01 = (0.50 if (is_10yr or src_sys == "xbrl") else 0.05) + 1e-6
        tol_v03 = (0.50 if src_sys == "xbrl" else 0.05) + 1e-6
        tol_v05 = (0.50 if (is_10yr or src_sys == "xbrl") else 0.05) + 1e-6

        code_val: Dict[str, float] = {}
        code_idx: Dict[str, List[int]] = {}
        for idx, row in grp.iterrows():
            lc = str(row["line_code"])
            val = row["value_inr_cr"]
            code_idx.setdefault(lc, []).append(idx)
            if val is not None and not pd.isna(val):
                code_val[lc] = float(val)

        # --- V01: Subtotal exact (M3: formula chosen strictly by scope & source_system) ---
        v01_checks: List[Tuple[str, float, float, List[int], str]] = []
        ti_val, ti_idx = _lookup(code_val, code_idx, "PL.TOTAL_INCOME")
        rev_val, rev_idx = _lookup(code_val, code_idx, "PL.REV_OPS")
        oi_val, oi_idx = _lookup(code_val, code_idx, "PL.OTHER_INCOME")
        if ti_val is not None and rev_val is not None and oi_val is not None:
            v01_checks.append(("PL.TOTAL_INCOME", ti_val, rev_val + oi_val, ti_idx + rev_idx + oi_idx, "PL.REV_OPS+PL.OTHER_INCOME"))

        pat_val, pat_idx = _lookup(code_val, code_idx, "PL.PAT")
        pbt_val, pbt_idx = _lookup(code_val, code_idx, "PL.PBT")
        tax_val, tax_idx = _lookup(code_val, code_idx, "PL.TAX")
        jv_sub_val = code_val.get("PL.SHARE_ASSOC_JV", code_val.get("PL.SHARE_ASSOC", 0.0) + code_val.get("PL.SHARE_JV", 0.0))
        if pat_val is not None and pbt_val is not None and tax_val is not None:
            # In BSE Reg 33 XBRL consolidated, ProfitBeforeTax is before JV share and ProfitForPeriod includes JV share;
            # in AR (both standalone and consolidated) and XBRL standalone, PL.PAT == PL.PBT - PL.TAX.
            if scope == "consolidated" and src_sys == "xbrl":
                exp_pat = pbt_val - tax_val + jv_sub_val
                pat_formula_str = "PL.PBT-PL.TAX+PL.SHARE_ASSOC_JV"
            else:
                exp_pat = pbt_val - tax_val
                pat_formula_str = "PL.PBT-PL.TAX"
            v01_checks.append(("PL.PAT", pat_val, exp_pat, pat_idx + pbt_idx + tax_idx, pat_formula_str))

        tci_val, tci_idx = _lookup(code_val, code_idx, "PL.TCI")
        oci_val, oci_idx = _lookup(code_val, code_idx, "PL.OCI")
        if tci_val is not None and pat_val is not None and oci_val is not None:
            v01_checks.append(("PL.TCI", tci_val, pat_val + oci_val, tci_idx + pat_idx + oci_idx, "PL.PAT+PL.OCI"))

        cfo_val, cfo_idx = _lookup(code_val, code_idx, "CF.CFO")
        cfi_val, cfi_idx = _lookup(code_val, code_idx, "CF.CFI")
        cff_val, cff_idx = _lookup(code_val, code_idx, "CF.CFF")
        chg_val, chg_idx = _lookup(code_val, code_idx, "CF.NET_CHANGE_CCE")
        if chg_val is not None and cfo_val is not None and cfi_val is not None and cff_val is not None:
            v01_checks.append(("CF.NET_CHANGE_CCE", chg_val, cfo_val + cfi_val + cff_val, chg_idx + cfo_idx + cfi_idx + cff_idx, "CF.CFO+CF.CFI+CF.CFF"))

        for lc, actual, expected, idxs, formula_str in v01_checks:
            diff = actual - expected
            ok = abs(diff) <= tol_v01
            ex = f"{fy} {scope} {nvint} {lc}: printed={actual:.2f} vs {formula_str}={expected:.2f} (Δ={diff:+.3f} cr)"
            _record_gate(gate_stats, passed_rules, failed_rules, "V01", idxs, ok, diff, ex)
            if not ok:
                for i in code_idx.get(lc, idxs):
                    gate_col_failed["V01"].add(i)
                    notes_list[i].append(f"V01 fail: {ex}")
                _add_conflict(
                    conflicts, fy, scope, lc,
                    f"{src_sys}:{nvint}:printed", actual,
                    f"{src_sys}:{nvint}:{formula_str}", expected,
                    diff, "V01", "open", "Subtotal mismatch.",
                )

        # Also record bronze_subtotal_ok checks under V01
        if "bronze_subtotal_ok" in grp.columns:
            sub_rows = grp[grp["bronze_subtotal_ok"].notna()]
            for idx, srow in sub_rows.iterrows():
                ok_sub = bool(srow["bronze_subtotal_ok"])
                ex = f"{fy} {scope} {nvint} {srow['line_code']} bronze_subtotal_ok={ok_sub}"
                _record_gate(gate_stats, passed_rules, failed_rules, "V01", [idx], ok_sub, 0.0, ex)
                if not ok_sub:
                    gate_col_failed["V01"].add(idx)
                    notes_list[idx].append("V01 fail: bronze_subtotal_ok=False")

        # --- V03: Balance sheet identity ---
        ta_val, ta_idx = _lookup(code_val, code_idx, "BS.TOTAL_ASSETS")
        eq_val, eq_idx = _lookup(code_val, code_idx, "BS.EQUITY.TOTAL")
        ncl_val, ncl_idx = _lookup(code_val, code_idx, "BS.LIAB.NON_CURRENT.TOTAL")
        cl_val, cl_idx = _lookup(code_val, code_idx, "BS.LIAB.CURRENT.TOTAL")
        lt_val, lt_idx = _lookup(code_val, code_idx, "BS.LIAB.TOTAL")
        tel_val, tel_idx = _lookup(code_val, code_idx, "BS.TOTAL_EQ_LIAB")

        if ta_val is not None and (tel_val is not None or (eq_val is not None and (lt_val is not None or (ncl_val is not None and cl_val is not None)))):
            bs_indices = list(grp[grp["statement"] == "balance_sheet"].index) or (ta_idx + eq_idx + ncl_idx + cl_idx + lt_idx + tel_idx)
            hfs_liab = code_val.get("BS.LIAB_HELD_FOR_SALE", 0.0)
            if hfs_liab == 0.0 and src_sys == "xbrl":
                hfs_rows = out[
                    (out["fiscal_year"] == fy)
                    & (out["scope"] == scope)
                    & (out["line_code"] == "BS.LIAB_HELD_FOR_SALE")
                ]
                if not hfs_rows.empty and not pd.isna(hfs_rows.iloc[0]["value_inr_cr"]):
                    hfs_liab = float(hfs_rows.iloc[0]["value_inr_cr"])
            rhs_candidates: List[Tuple[str, float]] = []
            if eq_val is not None and ncl_val is not None and cl_val is not None:
                rhs_candidates.append(("EQ+NCL+CL", eq_val + ncl_val + cl_val + hfs_liab))
            if eq_val is not None and lt_val is not None:
                rhs_candidates.append(("EQ+LIAB", eq_val + lt_val))
            if tel_val is not None:
                rhs_candidates.append(("TOTAL_EQ_LIAB", tel_val))

            best_label, best_rhs = min(rhs_candidates, key=lambda kv: abs(ta_val - kv[1]))
            worst_label, worst_rhs = max(rhs_candidates, key=lambda kv: abs(ta_val - kv[1]))
            diff = ta_val - worst_rhs
            ok_v03 = abs(diff) <= tol_v03
            ex = f"{fy} {scope} {nvint} BS.TOTAL_ASSETS={ta_val:.2f} vs {best_label}={best_rhs:.2f} (Δ={diff:+.3f} cr)"
            _record_gate(gate_stats, passed_rules, failed_rules, "V03", bs_indices, ok_v03, diff, ex)
            if not ok_v03:
                for i in bs_indices:
                    gate_col_failed["V03"].add(i)
                    notes_list[i].append(f"V03 fail: {ex}")
                _add_conflict(
                    conflicts, fy, scope, "BS.TOTAL_ASSETS",
                    f"{src_sys}:{nvint}:BS.TOTAL_ASSETS", ta_val,
                    f"{src_sys}:{nvint}:{worst_label}", worst_rhs,
                    diff, "V03", "open", "Balance sheet identity mismatch.",
                )

        # --- V05: P&L chain (M3: formula chosen strictly by scope & source_system) ---
        pnl_indices = list(grp[grp["statement"] == "pnl"].index)
        if pnl_indices and pat_val is not None and pbt_val is not None and tax_val is not None:
            ok_v05 = True
            max_pnl_diff = 0.0
            fail_lc = "PL.PAT"
            fail_act = pat_val
            fail_exp = pbt_val - tax_val
            fail_msg = ""

            if ti_val is not None and rev_val is not None and oi_val is not None:
                d1 = ti_val - (rev_val + oi_val)
                max_pnl_diff = max(max_pnl_diff, abs(d1))
                if abs(d1) > tol_v05:
                    ok_v05 = False
                    fail_lc, fail_act, fail_exp = "PL.TOTAL_INCOME", ti_val, rev_val + oi_val
                    fail_msg = f"TOTAL_INCOME ({ti_val:.2f}) != REV_OPS+OTHER_INCOME ({fail_exp:.2f})"

            jv_val = code_val.get("PL.SHARE_ASSOC_JV", code_val.get("PL.SHARE_ASSOC", 0.0) + code_val.get("PL.SHARE_JV", 0.0))
            pbt_pre_val, _ = _lookup(code_val, code_idx, "PL.PBT_PRE_EXC")
            texp_val, _ = _lookup(code_val, code_idx, "PL.TOTAL_EXP")
            if ok_v05 and ti_val is not None and texp_val is not None and pbt_pre_val is not None:
                exp_pbt_pre = ti_val - texp_val
                d2 = pbt_pre_val - exp_pbt_pre
                max_pnl_diff = max(max_pnl_diff, abs(d2))
                if abs(d2) > tol_v05:
                    ok_v05 = False
                    fail_lc, fail_act, fail_exp = "PL.PBT_PRE_EXC", pbt_pre_val, exp_pbt_pre
                    fail_msg = f"PBT_PRE_EXC ({pbt_pre_val:.2f}) != TOTAL_INCOME-TOTAL_EXP ({exp_pbt_pre:.2f})"

            if ok_v05 and pbt_pre_val is not None:
                exc_val = code_val.get("PL.EXCEPTIONAL", 0.0)
                # Strictly choose by (scope, source_system): AR consolidated includes JV/Assoc share in PBT; standalone and XBRL do not.
                exp_pbt = (pbt_pre_val + exc_val + jv_val) if (scope == "consolidated" and src_sys == "ar") else (pbt_pre_val + exc_val)
                d3 = pbt_val - exp_pbt
                max_pnl_diff = max(max_pnl_diff, abs(d3))
                if abs(d3) > tol_v05:
                    ok_v05 = False
                    fail_lc, fail_act, fail_exp = "PL.PBT", pbt_val, exp_pbt
                    fail_msg = f"PBT ({pbt_val:.2f}) != expected ({exp_pbt:.2f})"

            exp_pat = (pbt_val - tax_val + jv_val) if (scope == "consolidated" and src_sys == "xbrl") else (pbt_val - tax_val)
            d4 = pat_val - exp_pat
            max_pnl_diff = max(max_pnl_diff, abs(d4))
            if ok_v05 and abs(d4) > tol_v05:
                ok_v05 = False
                fail_lc, fail_act, fail_exp = "PL.PAT", pat_val, exp_pat
                fail_msg = f"PAT ({pat_val:.2f}) != expected ({fail_exp:.2f})"

            if ok_v05 and tci_val is not None and oci_val is not None:
                d5 = tci_val - (pat_val + oci_val)
                max_pnl_diff = max(max_pnl_diff, abs(d5))
                if abs(d5) > tol_v05:
                    ok_v05 = False
                    fail_lc, fail_act, fail_exp = "PL.TCI", tci_val, pat_val + oci_val
                    fail_msg = f"TCI ({tci_val:.2f}) != PAT+OCI ({fail_exp:.2f})"

            ex = f"{fy} {scope} {nvint} PBT={pbt_val:.2f} - TAX={tax_val:.2f} == PAT={pat_val:.2f} (max|Δ|={max_pnl_diff:.3f} cr)"
            _record_gate(gate_stats, passed_rules, failed_rules, "V05", pnl_indices, ok_v05, max_pnl_diff, ex)
            if not ok_v05:
                for i in pnl_indices:
                    gate_col_failed["V05"].add(i)
                    notes_list[i].append(f"V05 fail: {fail_msg}")
                _add_conflict(
                    conflicts, fy, scope, fail_lc,
                    f"{src_sys}:{nvint}:{fail_lc}", fail_act,
                    f"{src_sys}:{nvint}:pnl_chain", fail_exp,
                    fail_act - fail_exp, "V05", "open", "P&L chain mismatch.",
                )

    # ------------------------------------------------------------------
    # V04 (Cash tie-out) & V06 (Note & cross-statement link) per (fy, ptype, scope, src_sys, _norm_vintage)
    # ------------------------------------------------------------------
    note_tie_pairs = [
        ("REV.TOTAL", "PL.REV_OPS"),
        ("N31.TOTAL", "PL.OTHER_INCOME"),
        ("N35.TOTAL", "PL.PROD_EXP"),
        ("N36.TOTAL", "PL.FIN_COST"),
        ("N37.TOTAL", "PL.DDA"),
        ("NTAX.TOTAL", "PL.TAX"),
        ("SEG.REV.TOTAL", "PL.REV_OPS"),
        ("SEG.PBT", "PL.PBT"),
        ("SEG.ASSETS.TOTAL", "BS.TOTAL_ASSETS"),
    ]
    for (fy, ptype, scope, src_sys, nvint), grp in out.groupby(
        ["fiscal_year", "period_type", "scope", "source_system", "_norm_vintage"], dropna=False
    ):
        fg = grp[grp["source_table"] != "ten_year_summary"]
        if fg.empty:
            continue
        code_val = {}
        code_idx = {}
        for idx, r in fg.iterrows():
            lc = str(r["line_code"])
            code_idx.setdefault(lc, []).append(idx)
            if r["value_inr_cr"] is not None and not pd.isna(r["value_inr_cr"]):
                code_val[lc] = float(r["value_inr_cr"])

        tol_v04 = (0.50 if src_sys == "xbrl" else 0.05) + 1e-6

        # --- V04: Cash tie-out (CF.CCE_CLOSE == BS.CCE or net of OD; plus CF internal tie) ---
        cf_close, cf_close_idx = _lookup(code_val, code_idx, "CF.CCE_CLOSE")
        bs_cce, bs_cce_idx = _lookup(code_val, code_idx, "BS.CCE")
        cfo_val, cfo_idx = _lookup(code_val, code_idx, "CF.CFO")
        cfi_val, cfi_idx = _lookup(code_val, code_idx, "CF.CFI")
        cff_val, cff_idx = _lookup(code_val, code_idx, "CF.CFF")
        chg_val, chg_idx = _lookup(code_val, code_idx, "CF.NET_CHANGE_CCE")

        if cf_close is not None and bs_cce is not None:
            od = abs(code_val.get("CF.BANK_OVERDRAFT", 0.0))
            if od == 0.0 and src_sys == "xbrl":
                od_rows = out[
                    (out["fiscal_year"] == fy)
                    & (out["scope"] == scope)
                    & (out["line_code"] == "CF.BANK_OVERDRAFT")
                ]
                if not od_rows.empty and not pd.isna(od_rows.iloc[0]["value_inr_cr"]):
                    od = abs(float(od_rows.iloc[0]["value_inr_cr"]))
            diff_direct = cf_close - bs_cce
            diff_od = cf_close - (bs_cce - od)
            best_diff = diff_direct if abs(diff_direct) <= abs(diff_od) else diff_od
            ok_v04 = abs(best_diff) <= tol_v04
            v04_indices = cf_close_idx + bs_cce_idx
            ex = f"{fy} {scope} {nvint} CF.CCE_CLOSE={cf_close:.2f} vs BS.CCE={bs_cce:.2f} (OD={od:.2f}, Δ={best_diff:+.3f} cr)"
            _record_gate(gate_stats, passed_rules, failed_rules, "V04", v04_indices, ok_v04, best_diff, ex)
            if not ok_v04:
                for i in v04_indices:
                    gate_col_failed["V04"].add(i)
                    notes_list[i].append(f"V04 fail: {ex}")
                _add_conflict(
                    conflicts, fy, scope, "CF.CCE_CLOSE",
                    f"{src_sys}:{nvint}:CF.CCE_CLOSE", cf_close,
                    f"{src_sys}:{nvint}:BS.CCE", bs_cce,
                    best_diff, "V04", "open", "Cash and cash equivalents tie-out mismatch.",
                )

        if chg_val is not None and cfo_val is not None and cfi_val is not None and cff_val is not None:
            sum_abc = cfo_val + cfi_val + cff_val
            diff_abc = chg_val - sum_abc
            ok_abc = abs(diff_abc) <= tol_v04
            cf_indices = list(fg[fg["statement"] == "cash_flow"].index) or (chg_idx + cfo_idx + cfi_idx + cff_idx)
            ex = f"{fy} {scope} {nvint} CFO+CFI+CFF={sum_abc:.2f} vs NET_CHANGE_CCE={chg_val:.2f} (Δ={diff_abc:+.3f} cr)"
            _record_gate(gate_stats, passed_rules, failed_rules, "V04", cf_indices, ok_abc, diff_abc, ex)
            if not ok_abc:
                for i in cf_indices:
                    gate_col_failed["V04"].add(i)
                    notes_list[i].append(f"V04 fail: {ex}")

        # --- V06: Note & cross-statement links ---
        if src_sys == "ar" and ptype == "annual":
            for note_lc, stmt_Point in note_tie_pairs:
                n_val, n_idx = _lookup(code_val, code_idx, note_lc)
                s_val, s_idx = _lookup(code_val, code_idx, stmt_Point)
                if n_val is not None and s_val is not None:
                    diff = n_val - s_val
                    ok_v06 = abs(diff) <= (0.05 + 1e-6)
                    note_tbl_name = out.at[n_idx[0], "source_table"] if n_idx else ""
                    note_slice_idxs = list(fg[fg["source_table"] == note_tbl_name].index) if note_tbl_name else n_idx
                    v06_idxs = list(dict.fromkeys(note_slice_idxs + s_idx))
                    ex = f"{fy} {scope} {nvint} {note_lc}={n_val:.2f} vs {stmt_Point}={s_val:.2f} (Δ={diff:+.3f} cr)"
                    _record_gate(gate_stats, passed_rules, failed_rules, "V06", v06_idxs, ok_v06, diff, ex)
                    if not ok_v06:
                        for i in n_idx + s_idx:
                            gate_col_failed["V06"].add(i)
                            notes_list[i].append(f"V06 fail: {ex}")
                        _add_conflict(
                            conflicts, fy, scope, note_lc,
                            f"ar_note:{nvint}:{note_lc}", n_val,
                            f"ar_stmt:{nvint}:{stmt_Point}", s_val,
                            diff, "V06", "open", "Note to statement total mismatch.",
                        )

            if "N22.CLOSING" in code_val and ("BS.LEASE_LIAB_NC" in code_val or "BS.LEASE_LIAB_C" in code_val):
                bs_ll = code_val.get("BS.LEASE_LIAB_NC", 0.0) + code_val.get("BS.LEASE_LIAB_C", 0.0)
                diff = code_val["N22.CLOSING"] - bs_ll
                ok_v06 = abs(diff) <= (0.05 + 1e-6)
                idxs = code_idx.get("N22.CLOSING", []) + code_idx.get("BS.LEASE_LIAB_NC", []) + code_idx.get("BS.LEASE_LIAB_C", [])
                ex = f"{fy} {scope} {nvint} N22.CLOSING={code_val['N22.CLOSING']:.2f} vs BS.LEASE_LIAB={bs_ll:.2f} (Δ={diff:+.3f} cr)"
                _record_gate(gate_stats, passed_rules, failed_rules, "V06", idxs, ok_v06, diff, ex)
                if not ok_v06:
                    for i in idxs:
                        gate_col_failed["V06"].add(i)
                        notes_list[i].append(f"V06 fail: {ex}")

            pat_v, pat_i = _lookup(code_val, code_idx, "PL.PAT")
            if "CF.START_PROFIT" in code_val and pat_v is not None:
                diff = code_val["CF.START_PROFIT"] - pat_v
                ok_v06 = abs(diff) <= (0.05 + 1e-6)
                idxs = code_idx.get("CF.START_PROFIT", []) + pat_i
                ex = f"{fy} {scope} {nvint} CF.START_PROFIT={code_val['CF.START_PROFIT']:.2f} vs PL.PAT={pat_v:.2f} (Δ={diff:+.3f} cr)"
                _record_gate(gate_stats, passed_rules, failed_rules, "V06", idxs, ok_v06, diff, ex)
                if not ok_v06:
                    for i in idxs:
                        gate_col_failed["V06"].add(i)
                        notes_list[i].append(f"V06 fail: {ex}")

    # ------------------------------------------------------------------
    # V07: Cross-AR comparative (full_statement / note rows across AR vintages)
    # Non-tautological (B2): passes ONLY when |delta| <= 0.05 cr OR `raw_is_restated == True`.
    # Unflagged differences fail V07 and open a conflict (`status='open'`).
    # ------------------------------------------------------------------
    ar_stmt_df = out[(out["source_system"] == "ar") & (out["period_type"] == "annual") & (out["source_table"] != "ten_year_summary")]
    for (fy, scope, lc), grp in ar_stmt_df.groupby(["fiscal_year", "scope", "line_code"], dropna=False):
        if len(grp) < 2:
            continue
        grp_s = grp.copy()
        grp_s["_vnum"] = grp_s["_norm_vintage"].map(vintage_fy_number).fillna(999)
        grp_s = grp_s.sort_values("_vnum")

        base_row = grp_s.iloc[0]
        base_idx = int(base_row.name)
        base_val = base_row["value_inr_cr"]
        if base_val is None or pd.isna(base_val):
            continue
        base_vint = str(base_row["_norm_vintage"])

        for comp_idx_raw, comp_row in grp_s.iloc[1:].iterrows():
            comp_idx = int(comp_idx_raw)
            comp_val = comp_row["value_inr_cr"]
            if comp_val is None or pd.isna(comp_val):
                continue
            comp_vint = str(comp_row["_norm_vintage"])
            if comp_vint == base_vint:
                continue
            delta = float(comp_val) - float(base_val)
            tol = 0.05 + 1e-6
            raw_rest = bool(out.at[comp_idx, "raw_is_restated"])
            denom = max(abs(float(base_val)), abs(float(comp_val)), 1e-9)
            rel_diff = abs(delta) / denom

            ok_v07 = (abs(delta) <= tol) or raw_rest
            ex = f"{fy} {scope} {lc}: {base_vint}={float(base_val):.2f} vs {comp_vint}={float(comp_val):.2f} (Δ={delta:+.2f} cr, raw_restated={raw_rest})"

            st_v07 = gate_stats["V07"]
            st_v07["checked"] += 1
            st_v07["max_delta_inr_cr"] = max(float(st_v07["max_delta_inr_cr"]), abs(delta))
            if len(st_v07["examples"]) < 5:
                st_v07["examples"].append(ex)

            passed_rules[base_idx].add("V07")
            if ok_v07:
                st_v07["passed"] += 1
                passed_rules[comp_idx].add("V07")
                if abs(delta) > tol:
                    notes_list[comp_idx].append(
                        f"V07 flagged restatement vs {base_vint}: {float(base_val):.2f} -> {float(comp_val):.2f} cr (Δ={delta:+.2f} cr, {rel_diff*100:.2f}%)"
                    )
                    if rel_diff > 0.01:
                        _add_conflict(
                            conflicts, fy, scope, lc,
                            f"ar:{base_vint}", float(base_val),
                            f"ar:{comp_vint}", float(comp_val),
                            delta, "V07", "open",
                            f"Flagged comparative restatement (>1%: {rel_diff*100:.2f}%) between {base_vint} ({float(base_val):.2f} cr) and {comp_vint} ({float(comp_val):.2f} cr, Δ={delta:+.2f} cr); both vintages preserved per SPEC-01 §7.1 pending sign-off.",
                            resolution_rule="SPEC-01_S7.1_VINTAGE_RULE",
                        )
            else:
                st_v07["failed"] += 1
                gate_col_failed["V07"].add(comp_idx)
                notes_list[comp_idx].append(
                    f"V07 unflagged comparative diff vs {base_vint}: {float(base_val):.2f} -> {float(comp_val):.2f} cr (Δ={delta:+.2f} cr, {rel_diff*100:.2f}%)"
                )
                # If the comparative row is not backed by an intra-statement tie-out gate (V01/V03/V04/V05/V06), mark row unverified
                if not ({"V01", "V03", "V04", "V05", "V06"} & passed_rules[comp_idx]):
                    failed_rules[comp_idx].add("V07")
                _add_conflict(
                    conflicts, fy, scope, lc,
                    f"ar:{base_vint}", float(base_val),
                    f"ar:{comp_vint}", float(comp_val),
                    delta, "V07", "open",
                    f"Unflagged comparative reclassification between {base_vint} ({float(base_val):.2f} cr) and {comp_vint} ({float(comp_val):.2f} cr, Δ={delta:+.2f} cr, {rel_diff*100:.2f}%); {base_vint} kept as own vintage and {comp_vint} marked is_restated=TRUE per SPEC-01 §7.1 pending sign-off.",
                    resolution_rule="SPEC-01_S7.1_VINTAGE_RULE",
                )

    # ------------------------------------------------------------------
    # V08: 10-yr vs full statement (tolerance <= 0.10 cr or raw_is_restated)
    # ------------------------------------------------------------------
    ar_df = out[(out["source_system"] == "ar") & (out["period_type"] == "annual")]
    # Case A: cross_check_source='ar_ten_year:...' attached to same-vintage full_statement row
    cc_ty = out[out["cross_check_source"].astype(str).str.startswith("ar_ten_year", na=False)]
    for idx, r in cc_ty.iterrows():
        cc_val = r["cross_check_value"]
        st_val = r["value_inr_cr"]
        if cc_val is None or pd.isna(cc_val) or st_val is None or pd.isna(st_val):
            continue
        cc_cr = float(cc_val) / 10.0 if (str(r["unit"]) == "INR_mn" and abs(float(cc_val)) > abs(float(st_val)) * 3.0) else float(cc_val)
        delta = float(st_val) - cc_cr
        ok_v08 = (abs(delta) <= (0.10 + 1e-6)) or bool(r["raw_is_restated"])
        ex = f"{r['fiscal_year']} {r['scope']} {r['line_code']} stmt={float(st_val):.2f} vs {r['cross_check_source']}={cc_cr:.2f} (Δ={delta:+.3f} cr)"
        _record_gate(gate_stats, passed_rules, failed_rules, "V08", [idx], ok_v08, delta, ex)
        if not ok_v08:
            gate_col_failed["V08"].add(idx)
            notes_list[idx].append(f"V08 fail: {ex}")
            _add_conflict(
                conflicts, r["fiscal_year"], r["scope"], r["line_code"],
                f"ar_stmt:{r['_norm_vintage']}", float(st_val),
                str(r["cross_check_source"]), cc_cr,
                delta, "V08", "open",
                f"Same-vintage 10-year vs full statement mismatch in {r['_norm_vintage']} (Δ={delta:+.2f} cr).",
            )

    # Case B: both ten_year_summary and full_statement rows exist for same (fy, scope, line_code)
    for (fy, scope, lc), grp in ar_df.groupby(["fiscal_year", "scope", "line_code"], dropna=False):
        ty_rows = grp[grp["source_table"] == "ten_year_summary"]
        st_rows = grp[grp["source_table"] != "ten_year_summary"]
        if ty_rows.empty or st_rows.empty:
            continue
        st_s = st_rows.copy()
        st_s["_vnum"] = st_s["_norm_vintage"].map(vintage_fy_number).fillna(999)
        st_s = st_s.sort_values("_vnum")
        st_own = st_s.iloc[0]
        st_idx = int(st_own.name)
        st_val = st_own["value_inr_cr"]
        if st_val is None or pd.isna(st_val):
            continue
        for ty_idx_raw, trow in ty_rows.iterrows():
            ty_idx = int(ty_idx_raw)
            tval = trow["value_inr_cr"]
            if tval is None or pd.isna(tval):
                continue
            delta = float(tval) - float(st_val)
            tol_v08 = 0.10 + 1e-6
            raw_rest = bool(out.at[ty_idx, "raw_is_restated"])
            matches_any_stmt = any(
                abs(float(tval) - float(sr["value_inr_cr"])) <= tol_v08
                for _, sr in st_s.iterrows()
                if sr["value_inr_cr"] is not None and not pd.isna(sr["value_inr_cr"])
            )
            ok_v08 = (abs(delta) <= tol_v08) or raw_rest
            ex = f"{fy} {scope} {lc} 10yr({trow['_norm_vintage']})={float(tval):.2f} vs stmt({st_own['_norm_vintage']})={float(st_val):.2f} (Δ={delta:+.3f} cr, raw_restated={raw_rest})"

            st_v08 = gate_stats["V08"]
            st_v08["checked"] += 1
            st_v08["max_delta_inr_cr"] = max(float(st_v08["max_delta_inr_cr"]), abs(delta))
            if len(st_v08["examples"]) < 5:
                st_v08["examples"].append(ex)

            passed_rules[st_idx].add("V08")
            denom = max(abs(float(tval)), abs(float(st_val)), 1e-9)
            rel_diff = abs(delta) / denom
            if ok_v08:
                st_v08["passed"] += 1
                passed_rules[ty_idx].add("V08")
                if abs(delta) > tol_v08 and rel_diff > 0.01:
                    _add_conflict(
                        conflicts, fy, scope, lc,
                        f"ar_stmt:{st_own['_norm_vintage']}", float(st_val),
                        f"ar_ten_year:{trow['_norm_vintage']}", float(tval),
                        delta, "V08", "open",
                        f"Flagged 10-yr vs own-year statement restatement (>1%: {rel_diff*100:.2f}%) between {st_own['_norm_vintage']} ({float(st_val):.2f} cr) and {trow['_norm_vintage']} 10-yr ({float(tval):.2f} cr, Δ={delta:+.2f} cr); both vintages preserved per SPEC-01 §7.1 pending sign-off.",
                        resolution_rule="SPEC-01_S7.1_VINTAGE_RULE",
                    )
            else:
                st_v08["failed"] += 1
                gate_col_failed["V08"].add(ty_idx)
                notes_list[ty_idx].append(f"V08 unflagged diff: {ex}")
                if not matches_any_stmt:
                    failed_rules[ty_idx].add("V08")
                _add_conflict(
                    conflicts, fy, scope, lc,
                    f"ar_stmt:{st_own['_norm_vintage']}", float(st_val),
                    f"ar_ten_year:{trow['_norm_vintage']}", float(tval),
                    delta, "V08", "open",
                    f"Unflagged 10-yr vs own-year statement difference between {st_own['_norm_vintage']} ({float(st_val):.2f} cr) and {trow['_norm_vintage']} 10-yr ({float(tval):.2f} cr, Δ={delta:+.2f} cr, {rel_diff*100:.2f}%); matches comparative statement={matches_any_stmt}.",
                    resolution_rule="SPEC-01_S7.1_VINTAGE_RULE" if matches_any_stmt else None,
                )

    # ------------------------------------------------------------------
    # V09: 10-yr cross-edition (AR_FY22 vs AR_FY24 vs AR_FY26 10-yr tables)
    # Non-tautological (B2) & dynamic row resolution text (I5).
    # ------------------------------------------------------------------
    ty_all = ar_df[ar_df["source_table"] == "ten_year_summary"]
    for (fy, scope, lc), grp in ty_all.groupby(["fiscal_year", "scope", "line_code"], dropna=False):
        if len(grp) < 2:
            continue
        grp_s = grp.copy()
        grp_s["_vnum"] = grp_s["_norm_vintage"].map(vintage_fy_number).fillna(999)
        grp_s = grp_s.sort_values("_vnum")
        base_row = grp_s.iloc[0]
        base_idx = int(base_row.name)
        base_vint = str(base_row["_norm_vintage"])
        base_cr = base_row["value_inr_cr"]
        base_nat = base_row["value"]
        has_cr = base_cr is not None and not pd.isna(base_cr)

        for later_idx_raw, lrow in grp_s.iloc[1:].iterrows():
            later_idx = int(later_idx_raw)
            later_vint = str(lrow["_norm_vintage"])
            if later_vint == base_vint:
                continue
            if has_cr and lrow["value_inr_cr"] is not None and not pd.isna(lrow["value_inr_cr"]):
                b_val, l_val = float(base_cr), float(lrow["value_inr_cr"])
                delta = l_val - b_val
                tol = 0.10 + 1e-6
            else:
                b_val, l_val = float(base_nat), float(lrow["value"])
                delta = l_val - b_val
                tol = 0.05 + 1e-6
            raw_rest = bool(out.at[later_idx, "raw_is_restated"])
            ok_v09 = (abs(delta) <= tol) or raw_rest
            ex = f"{fy} {lc}: 10yr {base_vint}={b_val:.2f} vs {later_vint}={l_val:.2f} (Δ={delta:+.3f}, raw_restated={raw_rest})"

            st_v09 = gate_stats["V09"]
            st_v09["checked"] += 1
            if has_cr:
                st_v09["max_delta_inr_cr"] = max(float(st_v09["max_delta_inr_cr"]), abs(delta))
            if len(st_v09["examples"]) < 5:
                st_v09["examples"].append(ex)

            passed_rules[base_idx].add("V09")
            denom = max(abs(b_val), abs(l_val), 1e-9)
            rel_diff = abs(delta) / denom
            if ok_v09:
                st_v09["passed"] += 1
                passed_rules[later_idx].add("V09")
                if abs(delta) > tol and rel_diff > 0.01 and has_cr:
                    _add_conflict(
                        conflicts, fy, scope, lc,
                        f"ar_ten_year:{base_vint}", b_val,
                        f"ar_ten_year:{later_vint}", l_val,
                        delta, "V09", "open",
                        f"Flagged 10-yr cross-edition restatement (`*`, {rel_diff*100:.2f}%) for {fy} {lc} between {base_vint} ({b_val:.2f} cr) and {later_vint} ({l_val:.2f} cr, Δ={delta:+.2f} cr); both editions preserved per SPEC-01 §7.1 pending sign-off.",
                        resolution_rule="SPEC-01_S7.1_VINTAGE_RULE",
                    )
            else:
                st_v09["failed"] += 1
                gate_col_failed["V09"].add(later_idx)
                passed_rules[later_idx].add("V09")
                notes_list[later_idx].append(f"V09 unflagged 10-yr edition diff vs {base_vint}: {b_val:.2f} -> {l_val:.2f} (Δ={delta:+.2f})")
                _add_conflict(
                    conflicts, fy, scope, lc,
                    f"ar_ten_year:{base_vint}", b_val,
                    f"ar_ten_year:{later_vint}", l_val,
                    delta if has_cr else None, "V09", "open",
                    f"Unflagged 10-yr cross-edition difference for {fy} {lc} between {base_vint} ({b_val:.2f}) and {later_vint} ({l_val:.2f}, Δ={delta:+.2f}, {rel_diff*100:.2f}%); both editions retained with {later_vint} marked is_restated=TRUE per SPEC-01 §7.1 pending sign-off.",
                    resolution_rule="SPEC-01_S7.1_VINTAGE_RULE",
                )

    # ------------------------------------------------------------------
    # V10: XBRL cross-check (|val_xbrl - val_ar| <= 0.50 cr or cross-vintage raw_is_restated)
    # ------------------------------------------------------------------
    xbrl_df = out[(out["source_system"] == "xbrl") & (out["period_type"].isin(["annual", "instant"]))]
    for idx, xrow in xbrl_df.iterrows():
        fy = xrow["fiscal_year"]
        scope = xrow["scope"]
        lc = xrow["line_code"]
        xval = xrow["value_inr_cr"]
        xvint = str(xrow["_norm_vintage"])
        xvnum = vintage_fy_number(xvint)
        if xval is None or pd.isna(xval):
            continue

        cand = ar_df[(ar_df["fiscal_year"] == fy) & (ar_df["scope"] == scope) & (ar_df["line_code"] == lc)]
        if cand.empty:
            continue

        cand_c = cand.copy()
        cand_c["_vnum"] = cand_c["_norm_vintage"].map(vintage_fy_number).fillna(999)
        cand_c["_same_v"] = (cand_c["_vnum"] == (xvnum if xvnum is not None else -1)).astype(int)
        cand_c["_is_stmt"] = (cand_c["source_table"] != "ten_year_summary").astype(int)
        cand_c = cand_c.sort_values(["_same_v", "_is_stmt", "_vnum"], ascending=[False, False, True])

        match_ar = cand_c.iloc[0]
        ar_idx = int(match_ar.name)
        aval = float(match_ar["value_inr_cr"])
        avint = str(match_ar["_norm_vintage"])
        avnum = vintage_fy_number(avint)
        delta = float(xval) - aval
        tol = 0.50 + 1e-6

        if abs(delta) > tol and lc == "PL.TAX_CURRENT":
            ear_rows = ar_df[
                (ar_df["fiscal_year"] == fy)
                & (ar_df["scope"] == scope)
                & (ar_df["_norm_vintage"] == avint)
                & (ar_df["line_code"] == "PL.TAX_EARLIER")
            ]
            if not ear_rows.empty and not pd.isna(ear_rows.iloc[0]["value_inr_cr"]):
                comb_tax = aval + float(ear_rows.iloc[0]["value_inr_cr"])
                if abs(float(xval) - comb_tax) <= tol:
                    aval = comb_tax
                    delta = float(xval) - aval
        elif abs(delta) > tol and lc == "PL.PBT" and scope == "consolidated":
            jv_rows = ar_df[
                (ar_df["fiscal_year"] == fy)
                & (ar_df["scope"] == scope)
                & (ar_df["_norm_vintage"] == avint)
                & (ar_df["line_code"].isin(["PL.SHARE_ASSOC", "PL.SHARE_JV", "PL.SHARE_ASSOC_JV"]))
            ]
            if not jv_rows.empty:
                jv_sum = float(jv_rows["value_inr_cr"].dropna().sum())
                if abs((float(xval) + jv_sum) - aval) <= tol:
                    delta = (float(xval) + jv_sum) - aval
        elif abs(delta) > tol and lc == "SEG.FIN_COST":
            if abs(abs(float(xval)) - abs(aval)) <= tol:
                aval = abs(aval)
                delta = abs(float(xval)) - aval

        if pd.isna(out.at[idx, "cross_check_value"]):
            out.at[idx, "cross_check_source"] = f"ar:{avint}"
            out.at[idx, "cross_check_value"] = aval
            out.at[idx, "cross_check_delta_inr_cr"] = round(delta, 4)

        same_vintage = (xvnum is not None) and (avnum == xvnum)
        raw_rest = bool(xrow["raw_is_restated"]) or bool(match_ar["raw_is_restated"])
        ok_v10 = (abs(delta) <= tol) or (not same_vintage and raw_rest)
        ex = f"{fy} {scope} {lc} xbrl({xvint})={float(xval):.2f} vs ar({avint})={aval:.2f} (Δ={delta:+.3f} cr, raw_restated={raw_rest})"

        st_v10 = gate_stats["V10"]
        st_v10["checked"] += 1
        st_v10["max_delta_inr_cr"] = max(float(st_v10["max_delta_inr_cr"]), abs(delta))
        if len(st_v10["examples"]) < 5:
            st_v10["examples"].append(ex)

        passed_rules[ar_idx].add("V10")
        denom = max(abs(float(xval)), abs(aval), 1e-9)
        rel_diff = abs(delta) / denom
        if ok_v10:
            st_v10["passed"] += 1
            passed_rules[idx].add("V10")
            if abs(delta) > tol and rel_diff > 0.01:
                notes_list[idx].append(f"V10 restated vs {avint}: xbrl={float(xval):.2f}, ar={aval:.2f} (Δ={delta:+.2f} cr)")
                _add_conflict(
                    conflicts, fy, scope, lc,
                    f"xbrl:{xvint}", float(xval),
                    f"ar:{avint}", aval,
                    delta, "V10", "open",
                    f"XBRL own-year filing {xvint} ({float(xval):.2f} cr) vs flagged restated AR {avint} ({aval:.2f} cr, Δ={delta:+.2f} cr, {rel_diff*100:.2f}%); both vintages retained per SPEC-01 §7.1 pending sign-off.",
                    resolution_rule="SPEC-01_S7.1_VINTAGE_RULE",
                )
        else:
            st_v10["failed"] += 1
            gate_col_failed["V10"].add(idx)
            notes_list[idx].append(f"V10 fail: {ex}")
            if same_vintage:
                failed_rules[idx].add("V10")
            else:
                passed_rules[idx].add("V10")
            _add_conflict(
                conflicts, fy, scope, lc,
                f"xbrl:{xvint}", float(xval),
                f"ar:{avint}", aval,
                delta, "V10", "open",
                f"XBRL {xvint} ({float(xval):.2f} cr) vs AR {avint} ({aval:.2f} cr, Δ={delta:+.2f} cr, {rel_diff*100:.2f}%) difference without printed restatement flag.",
                resolution_rule="SPEC-01_S7.1_VINTAGE_RULE" if not same_vintage else None,
            )

    # ------------------------------------------------------------------
    # V11: Yahoo cross-check (conditional) & scope/magnitude sanity (M2)
    # ------------------------------------------------------------------
    yahoo_df = out[(out["source_system"] == "yahoo") & (out["period_type"] == "annual")]
    for idx, yrow in yahoo_df.iterrows():
        fy = yrow["fiscal_year"]
        lc = yrow["line_code"]
        yval = yrow["value_inr_cr"]
        if yval is None or pd.isna(yval):
            continue
        cand = ar_df[(ar_df["fiscal_year"] == fy) & (ar_df["scope"] == "consolidated") & (ar_df["line_code"] == lc)]
        if cand.empty:
            continue
        aval = float(cand.iloc[-1]["value_inr_cr"])
        delta = float(yval) - aval
        ok_v11 = abs(delta) <= (1.0 + 1e-6)
        ex = f"{fy} consolidated {lc} yahoo={float(yval):.2f} vs ar={aval:.2f} (Δ={delta:+.3f} cr)"
        _record_gate(gate_stats, passed_rules, failed_rules, "V11", [idx], ok_v11, delta, ex)
        if not ok_v11:
            gate_col_failed["V11"].add(idx)

    # Standalone vs Consolidated scope sanity (M2: consolidated > standalone * 1.05 on REV_OPS and TOTAL_ASSETS)
    for (fy, src_sys, nvint), grp in out[out["period_type"] == "annual"].groupby(
        ["fiscal_year", "source_system", "_norm_vintage"], dropna=False
    ):
        sa = grp[grp["scope"] == "standalone"]
        co = grp[grp["scope"] == "consolidated"]
        if sa.empty or co.empty:
            continue
        sa_map = dict(zip(sa["line_code"], sa["value_inr_cr"]))
        co_map = dict(zip(co["line_code"], co["value_inr_cr"]))
        for check_lc in ("PL.PAT", "PL.REV_OPS", "BS.TOTAL_ASSETS"):
            if check_lc in sa_map and check_lc in co_map:
                s_val, c_val = sa_map[check_lc], co_map[check_lc]
                if s_val is None or c_val is None or pd.isna(s_val) or pd.isna(c_val):
                    continue
                if check_lc in ("PL.REV_OPS", "BS.TOTAL_ASSETS"):
                    ok_scope = float(c_val) > float(s_val) * 1.05
                else:
                    ok_scope = abs(float(s_val) - float(c_val)) > 0.01
                idxs = list(grp[grp["line_code"] == check_lc].index)
                ex = f"{fy} {nvint} {check_lc}: standalone={float(s_val):.2f} vs consolidated={float(c_val):.2f} (ratio={float(c_val)/max(abs(float(s_val)),1e-9):.2f}x)"
                _record_gate(gate_stats, passed_rules, failed_rules, "V11", idxs, ok_scope, 0.0, ex)
                if not ok_scope:
                    for i in idxs:
                        gate_col_failed["V11"].add(i)
                        notes_list[i].append(f"V11 fail: {ex}")

    # ------------------------------------------------------------------
    # V12: Coverage & vintage completeness (B2)
    # 1) Every annual (fy, scope, line_code) group has (is_own_vintage or is_fallback_vintage) and is_latest_vintage.
    # 2) When dim_df is provided, check every is_kpi line against expected fiscal years per scope_applicability:
    #    - standalone FY17-FY26 (for scope_applicability in {'both', 'standalone_only'})
    #    - consolidated FY22-FY26 (for scope_applicability in {'both', 'consolidated_only'})
    #    - 10-yr summary FY13-FY16 (additional pre-FY17 decade years for 10-yr summary KPIs)
    # ------------------------------------------------------------------
    for (fy, scope, lc), grp in out[out["period_type"] == "annual"].groupby(["fiscal_year", "scope", "line_code"], dropna=False):
        has_own_or_fb = bool(grp["is_own_vintage"].any() or grp["is_fallback_vintage"].any())
        has_latest = bool(grp["is_latest_vintage"].any())
        ok_v12 = has_own_or_fb and has_latest
        idxs = list(grp.index)
        ex = f"{fy} {scope} {lc}: own_or_fallback={has_own_or_fb}, latest={has_latest} (n={len(grp)})"
        _record_gate(gate_stats, passed_rules, failed_rules, "V12", idxs, ok_v12, 0.0, ex)
        if not ok_v12:
            for i in idxs:
                gate_col_failed["V12"].add(i)
                notes_list[i].append(f"V12 fail: {ex}")

    # Ensure non-annual rows (quarter, opening) have V02 in verified_rule_ids
    # Populate verified_rule_ids, failed_rule_ids, boolean gate columns, and verified BEFORE KPI matrix check
    out["verified_rule_ids"] = [sorted(s - f) for s, f in zip(passed_rules, failed_rules)]
    out["failed_rule_ids"] = [sorted(f) for f in failed_rules]

    gate_col_map = {
        "V01": "v01_subtotal_ok",
        "V02": "v02_no_plugs_ok",
        "V03": "v03_bs_identity",
        "V04": "v04_cash_tie",
        "V05": "v05_pnl_chain",
        "V06": "v06_note_tie",
        "V07": "v07_prior_year_match",
        "V08": "v08_ten_year_match",
        "V09": "v09_ten_year_editions",
        "V10": "v10_xbrl_match",
        "V11": "v11_scope_sanity",
        "V12": "v12_coverage_ok",
    }
    for gid, col_name in gate_col_map.items():
        bad_set = failed_rules_union = gate_col_failed[gid]
        out[col_name] = [(i not in bad_set) and (gid not in failed_rules[i]) for i in range(n)]

    out["verified"] = [len(f) == 0 for f in failed_rules]

    # Part 2 of V12: KPI × FY coverage matrix against dim_df
    if dim_df is not None and not dim_df.empty and "is_kpi" in dim_df.columns:
        ver_ann = out[(out["period_type"] == "annual") & (out["verified"])]
        present_cells: Set[Tuple[str, str, str]] = set(
            zip(ver_ann["scope"].astype(str), ver_ann["line_code"].astype(str), ver_ann["fiscal_year"].astype(str))
        )
        ten_yr_codes: Set[str] = set(
            out[out["source_table"] == "ten_year_summary"]["line_code"].astype(str).unique()
        )
        kpi_rows = dim_df[dim_df["is_kpi"].fillna(False).astype(bool)]
        sa_fys = [f"FY{y}" for y in range(17, 27)]
        co_fys = [f"FY{y}" for y in range(22, 27)]
        ty_early_fys = [f"FY{y}" for y in range(13, 17)]

        def _explain_gap(scope_s: str, lc_s: str, fy_s: str) -> str:
            if fy_s == "FY20":
                return "AR FY20 PDF is image-only (scanned) and BSE Reg 33 FY20 XBRL filing contains P&L/Segment only (no BS/CF/Notes)."
            if fy_s == "FY21" and lc_s.startswith(("N", "REV.TOTAL", "SEG.")):
                return "AR FY21 PDF is image-only (scanned); AR FY22 comparative covers face statements and select notes only."
            if lc_s in ("PL.EMP_BENEFIT", "OTH.PAID_UP_CAPITAL", "PL.EPS_DILUTED"):
                return "Disclosed as a separate face line in BSE Reg 33 XBRL filings (FY18-FY21, FY23-FY24); in AR P&L staff cost is inside Note 35.1 (`N351.EMP_TOTAL`) and Basic == Diluted EPS."
            if lc_s.startswith("PROD."):
                return "Directors' Report summary table in `ten_year_raw` covers FY24-FY26; full FY13-FY26 production series is in `hrfin_gold.fact_production_annual` (P1.7)."
            if fy_s in ("FY25", "FY26") and lc_s.startswith(("REV.", "QTY.", "LEVY.")):
                return "AR FY26 10-Year Summary condensed product/levy sub-lines into category lines (`REV.VAP`, `QTY.VAP_SOLD`, `QTY.GAS_SOLD`, `LEVY.OTHER_SAED`); granular product breakup is in Note 30."
            if lc_s == "RATIO.BVPS_RESTATED":
                return "Separate 'Book Value Per Share (Restated)' line was printed only in AR FY22 10-Year Summary (FY13-FY22); AR FY24/FY26 report single `RATIO.BVPS`."
            if lc_s == "LEVY.ROAD_INFRA_CESS":
                return "Road & Infrastructure Cess was introduced in FY19 and folded into `LEVY.OTHER_SAED` in AR FY26 10-Year Summary."
            if lc_s == "REV.TOTAL" and fy_s == "FY19":
                return "AR FY19 Note 30 total ties directly via face `PL.REV_OPS` (`is_own_vintage=TRUE`)."
            if fy_s in ("FY13", "FY14", "FY15", "FY16"):
                return "Line introduced in AR 10-Year Summary from Ind AS transition (FY16/FY17) onward; not printed in FY13-FY15 pre-Ind AS columns."
            return "Not separately disclosed in source table for this fiscal year/scope."

        for _, drow in kpi_rows.iterrows():
            lc = str(drow["line_code"])
            scope_app = str(drow.get("scope_applicability", "both")).strip()
            # 1) Standalone FY17-FY26 check
            if scope_app in ("both", "standalone_only"):
                for fy in sa_fys:
                    gate_stats["V12"]["checked"] += 1
                    if ("standalone", lc, fy) in present_cells:
                        gate_stats["V12"]["passed"] += 1
                    else:
                        gate_stats["V12"]["failed"] += 1
                        reason = _explain_gap("standalone", lc, fy)
                        coverage_gaps.append(
                            {
                                "bucket": "standalone_fy17_26",
                                "scope": "standalone",
                                "line_code": lc,
                                "fiscal_year": fy,
                                "reason": reason,
                            }
                        )
                        if len(gate_stats["V12"]["examples"]) < 5:
                            gate_stats["V12"]["examples"].append(f"GAP standalone {fy} {lc}: {reason}")
            # 2) Consolidated FY22-FY26 check
            if scope_app in ("both", "consolidated_only"):
                for fy in co_fys:
                    gate_stats["V12"]["checked"] += 1
                    if ("consolidated", lc, fy) in present_cells:
                        gate_stats["V12"]["passed"] += 1
                    else:
                        gate_stats["V12"]["failed"] += 1
                        reason = _explain_gap("consolidated", lc, fy)
                        coverage_gaps.append(
                            {
                                "bucket": "consolidated_fy22_26",
                                "scope": "consolidated",
                                "line_code": lc,
                                "fiscal_year": fy,
                                "reason": reason,
                            }
                        )
            # 3) 10-yr summary pre-FY17 decade check (FY13-FY16)
            if lc in ten_yr_codes:
                for fy in ty_early_fys:
                    gate_stats["V12"]["checked"] += 1
                    if ("standalone", lc, fy) in present_cells:
                        gate_stats["V12"]["passed"] += 1
                    else:
                        gate_stats["V12"]["failed"] += 1
                        reason = _explain_gap("standalone", lc, fy)
                        coverage_gaps.append(
                            {
                                "bucket": "ten_year_fy13_16",
                                "scope": "standalone",
                                "line_code": lc,
                                "fiscal_year": fy,
                                "reason": reason,
                            }
                        )

    out["notes"] = ["; ".join(nl) if nl else None for nl in notes_list]
    out["verification_notes"] = out["notes"]
    drop_cols = ["_norm_vintage"]
    if "bronze_subtotal_ok" in out.columns:
        drop_cols.append("bronze_subtotal_ok")
    out = out.drop(columns=drop_cols)

    if conflicts:
        cdf = pd.DataFrame(conflicts, columns=CONFLICT_COLUMNS)
        cdf = cdf.drop_duplicates(
            subset=["fiscal_year", "scope", "line_code", "source_a", "source_b", "rule_id"]
        ).sort_values(["fiscal_year", "scope", "line_code", "rule_id"]).reset_index(drop=True)
    else:
        cdf = pd.DataFrame(columns=CONFLICT_COLUMNS)

    now_utc = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    run_id = f"gate_run_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    return GateRunResult(
        df=out,
        conflicts=cdf,
        gate_stats=gate_stats,
        coverage_gaps=coverage_gaps,
        run_id=run_id,
        run_at=now_utc,
    )


def run_all_gates(df: pd.DataFrame, dim_df: Optional[pd.DataFrame] = None) -> GateRunResult:
    """Alias for `verify_gates`."""
    return verify_gates(df, dim_df=dim_df)


def render_gate_report_md(res: GateRunResult) -> str:
    """Render a deterministic Markdown gate report for V01-V12, verified share, conflict summary, and V12 KPI gaps."""
    df = res.df
    cdf = res.conflicts
    total_rows = len(df)
    verified_rows = int(df["verified"].sum())
    pct_all = (verified_rows / total_rows * 100.0) if total_rows else 0.0

    ar_df = df[df["source_system"] == "ar"]
    ar_total = len(ar_df)
    ar_ver = int(ar_df["verified"].sum())
    pct_ar = (ar_ver / ar_total * 100.0) if ar_total else 0.0

    open_conflicts = int((cdf["status"] == "open").sum()) if not cdf.empty else 0
    resolved_conflicts = int((cdf["status"] == "resolved").sum()) if not cdf.empty else 0

    lines = [
        f"# Financial SSOT Verification Gate Report ({res.run_id})",
        "",
        f"- **Generated (UTC):** `{res.run_at}`",
        f"- **Total Gold Rows (`fact_financial_statement_line`):** `{total_rows:,}`",
        f"- **Verified Rows (`verified = TRUE`):** `{verified_rows:,} / {total_rows:,}` (`{pct_all:.2f}%`)",
        f"- **AR Reported Rows Verified (`source_system = 'ar'`):** `{ar_ver:,} / {ar_total:,}` (`{pct_ar:.2f}%`)",
        f"- **Conflict / Restatement Audit Rows (`fact_financial_line_conflict`):** `{len(cdf):,}` (`open={open_conflicts:,}`, `resolved={resolved_conflicts:,}`)",
        f"- **V12 KPI Coverage Gaps Logged:** `{len(res.coverage_gaps):,}`",
        "",
        "## 1. Gate Summary (V01–V12)",
        "",
        "| Gate | Name | Checked | Passed | Failed | Max |Δ| (₹ cr) | Pass Rate | Rule Summary |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for gid in [f"V{i:02d}" for i in range(1, 13)]:
        name, desc = GATE_METADATA[gid]
        st = res.gate_stats.get(gid, {"checked": 0, "passed": 0, "failed": 0, "max_delta_inr_cr": 0.0})
        chk, pas, fail = int(st["checked"]), int(st["passed"]), int(st["failed"])
        max_d = float(st.get("max_delta_inr_cr", 0.0))
        rate = f"{(pas / chk * 100.0):.2f}%" if chk > 0 else "100.00% (conditional)"
        lines.append(f"| `{gid}` | {name} | {chk:,} | {pas:,} | {fail:,} | {max_d:,.3f} | {rate} | {desc} |")

    lines.extend(["", "## 2. Gate Examples (up to 5 per gate)", ""])
    for gid in [f"V{i:02d}" for i in range(1, 13)]:
        name, _ = GATE_METADATA[gid]
        st = res.gate_stats.get(gid, {})
        exs = st.get("examples", [])
        lines.append(f"### `{gid}` — {name}")
        if not exs:
            lines.append("- *(Conditional gate — 0 applicable rows in current offline run)*")
        else:
            for e in exs[:5]:
                lines.append(f"- `{e}`")
        lines.append("")

    lines.extend(["## 3. Conflict & Restatement Table Summary (`fact_financial_line_conflict`)", ""])
    if cdf.empty:
        lines.append("No conflicts or >1% restatements detected.")
    else:
        by_status = cdf.groupby(["rule_id", "status"]).size().reset_index(name="count")
        lines.append("| Rule ID | Status | Count |")
        lines.append("|---|---|---:|")
        for _, r in by_status.iterrows():
            lines.append(f"| `{r['rule_id']}` | `{r['status']}` | {int(r['count']):,} |")
        lines.extend([
            "",
            "### Detailed Conflict / Restatement Entries",
            "",
            "| FY | Scope | Line Code | Source A | Value A (₹ cr) | Source B | Value B (₹ cr) | Delta (₹ cr) | % Δ | Rule | Status | Resolution Rule | Resolution |",
            "|---|---|---|---|---:|---|---:|---:|---:|---|---|---|---|",
        ])
        for _, r in cdf.iterrows():
            va = f"{r['value_a']:,.2f}" if r["value_a"] is not None and not pd.isna(r["value_a"]) else "—"
            vb = f"{r['value_b']:,.2f}" if r["value_b"] is not None and not pd.isna(r["value_b"]) else "—"
            dl = f"{r['delta_inr_cr']:+,.2f}" if r["delta_inr_cr"] is not None and not pd.isna(r["delta_inr_cr"]) else "—"
            pct = f"{r['pct_delta']:.2f}%" if r.get("pct_delta") is not None and not pd.isna(r.get("pct_delta")) else "—"
            rr = str(r.get("resolution_rule") or "—")
            res_txt = str(r.get("resolution") or "")
            lines.append(
                f"| `{r['fiscal_year']}` | `{r['scope']}` | `{r['line_code']}` | `{r['source_a']}` | {va} | `{r['source_b']}` | {vb} | {dl} | {pct} | `{r['rule_id']}` | `{r['status']}` | `{rr}` | {res_txt} |"
            )

    lines.extend(["", "## 4. V12 KPI Coverage Gaps", ""])
    if not res.coverage_gaps:
        lines.append("No KPI coverage gaps detected.")
    else:
        gaps_df = pd.DataFrame(res.coverage_gaps)
        grp_gaps = (
            gaps_df.groupby(["bucket", "scope", "line_code", "reason"])["fiscal_year"]
            .apply(lambda s: ", ".join(sorted(s)))
            .reset_index()
        )
        lines.append("| Coverage Bucket | Scope | Line Code | Missing Fiscal Years | Count | Reason |")
        lines.append("|---|---|---|---|---:|---|")
        for _, gr in grp_gaps.iterrows():
            fys_str = str(gr["fiscal_year"])
            cnt = len([x for x in fys_str.split(",") if x.strip()])
            lines.append(
                f"| `{gr['bucket']}` | `{gr['scope']}` | `{gr['line_code']}` | `{fys_str}` | {cnt} | {gr['reason']} |"
            )

    return "\n".join(lines) + "\n"
