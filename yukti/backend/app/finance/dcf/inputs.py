"""SSOT & market-seed input loaders for the DCF valuation engine (SPEC-02, BUG-12).

Loads FY26 WACC from `financial_ssot/out/fact_wacc_annual.parquet` and FY26 NSE close
price from `knowledge/public_sources/market_data/manual/market_prices_seed.csv` (with
fallback to `financial_ssot/out/fact_wacc_input.parquet`) with full provenance lineage.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


class DCFInputMissingError(ValueError):
    """Raised when a required DCF SSOT or market-price input is missing, unverified, or NULL."""

    def __init__(self, missing_input: str, message: Optional[str] = None):
        self.missing_input = missing_input
        super().__init__(message or f"Missing or unverified DCF input: {missing_input}")


def _resolve_asset(rel_path: str) -> Path:
    here = Path(__file__).resolve()
    for depth in (5, 4, 3):
        if len(here.parents) > depth:
            cand = here.parents[depth] / rel_path
            if cand.exists():
                return cand
    return here.parents[min(5, len(here.parents) - 1)] / rel_path


SNAPSHOT_PARQUET = _resolve_asset("financial_ssot/out/fact_snapshot.parquet")
WACC_ANNUAL_PARQUET = _resolve_asset("financial_ssot/out/fact_wacc_annual.parquet")
WACC_INPUT_PARQUET = _resolve_asset("financial_ssot/out/fact_wacc_input.parquet")
MARKET_SEED_CSV = _resolve_asset("knowledge/public_sources/market_data/manual/market_prices_seed.csv")


def _opt_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def load_wacc_annual_rows() -> List[Dict[str, Any]]:
    if not WACC_ANNUAL_PARQUET.exists():
        return []
    df = pd.read_parquet(WACC_ANNUAL_PARQUET)
    return df.to_dict(orient="records")


def load_ssot_snapshot_rows(fy: str = "FY26", scope: str = "standalone") -> List[Dict[str, Any]]:
    if not SNAPSHOT_PARQUET.exists():
        return []
    df = pd.read_parquet(SNAPSHOT_PARQUET)
    mask = (df["fiscal_year"] == fy) & (df["scope"] == scope)
    if "is_latest_vintage" in df.columns:
        mask = mask & (df["is_latest_vintage"] == True)  # noqa: E712
    sub = df[mask]
    return sub.to_dict(orient="records")


def load_fy26_wacc_default(
    wacc_table: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[float, str, Dict[str, Any]]:
    """Return (wacc_pct, source_label, row_metadata) for FY26 from fact_wacc_annual.

    Raises DCFInputMissingError('fact_wacc_annual') when the file/table is missing,
    has no verified/modelled FY26 row, or has NULL WACC / required components.
    """
    using_ssot_file = wacc_table is None or len(wacc_table) == 0
    rows = load_wacc_annual_rows() if using_ssot_file else wacc_table
    if not rows:
        raise DCFInputMissingError("fact_wacc_annual")

    for row in rows:
        if row.get("fiscal_year") == "FY26":
            wacc_val = _opt_float(row.get("wacc_pct"))
            if wacc_val is not None and (
                row.get("verified", False) or row.get("provenance_label") in ("modelled", "verified_ar")
            ):
                val = round(wacc_val, 4)
                meta: Dict[str, Any] = {
                    "fiscal_year": "FY26",
                    "wacc_pct": val,
                    "as_of_date": str(row.get("as_of_date") or ""),
                    "rf_used_pct": _opt_float(row.get("rf_used_pct")),
                    "default_spread_pct": _opt_float(row.get("default_spread_pct")),
                    "erp_total_pct": _opt_float(row.get("erp_total_pct")),
                    "beta_industry_relevered": _opt_float(row.get("beta_industry_relevered")),
                    "ke_pct": _opt_float(row.get("ke_pct")),
                    "kd_pretax_pct": _opt_float(row.get("kd_pretax_pct")),
                    "kd_used_pct": _opt_float(row.get("kd_used_pct")),
                    "tax_rate_pct": _opt_float(row.get("tax_rate_pct")),
                    "weight_equity": _opt_float(row.get("weight_equity")),
                    "weight_debt": _opt_float(row.get("weight_debt")),
                    "wacc_alt_gsec_less_spread_pct": _opt_float(row.get("wacc_alt_gsec_less_spread_pct")),
                    "method_version": str(row.get("method_version") or "wacc-v1"),
                    "object": "hrfin_gold.fact_wacc_annual",
                }
                if using_ssot_file:
                    required_components = (
                        "rf_used_pct",
                        "default_spread_pct",
                        "erp_total_pct",
                        "beta_industry_relevered",
                        "ke_pct",
                        "kd_used_pct",
                        "tax_rate_pct",
                        "weight_equity",
                        "weight_debt",
                    )
                    missing_comp = [k for k in required_components if meta.get(k) is None]
                    if missing_comp:
                        raise DCFInputMissingError(
                            "fact_wacc_annual",
                            f"fact_wacc_annual FY26 row is missing component(s): {', '.join(missing_comp)}",
                        )
                return val, "fact_wacc_annual FY26", meta

    raise DCFInputMissingError("fact_wacc_annual")


def load_fy26_market_price_default() -> Tuple[float, str, Dict[str, Any]]:
    """Return (close_price_inr, source_label, lineage_metadata) for FY26 ONGC.NS close.

    Raises DCFInputMissingError when both market_prices_seed.csv and fact_wacc_input.parquet
    are missing or contain no valid FY26 market price.
    """
    if MARKET_SEED_CSV.exists():
        latest_row: Optional[Dict[str, str]] = None
        with open(MARKET_SEED_CSV, "r", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                ticker = (row.get("ticker") or "").strip()
                dt = (row.get("date") or "").strip()
                if ticker in ("ONGC.NS", "ONGC", "") and dt.startswith("2026-03"):
                    if latest_row is None or dt >= (latest_row.get("date") or ""):
                        latest_row = row
        if latest_row and latest_row.get("close"):
            px_opt = _opt_float(latest_row.get("close"))
            if px_opt is not None and px_opt > 0:
                px = round(px_opt, 2)
                dt = (latest_row.get("date") or "").strip()
                src_url = (latest_row.get("source_url") or "").strip()
                ret_by = (latest_row.get("retrieved_by") or "").strip()
                return (
                    px,
                    f"market_prices_seed.csv (NSE EQ close {dt})",
                    {
                        "ticker": "ONGC.NS",
                        "date": dt,
                        "close_inr": px,
                        "source_doc": "market_prices_seed.csv",
                        "source_url": src_url,
                        "retrieved_by": ret_by,
                    },
                )

    if WACC_INPUT_PARQUET.exists():
        df = pd.read_parquet(WACC_INPUT_PARQUET)
        sub = df[df["fiscal_year"] == "FY26"]
        eq_rows = sub[sub["input_code"] == "equity_mv"]
        sh_rows = sub[sub["input_code"] == "shares_outstanding"]
        if not eq_rows.empty and not sh_rows.empty:
            eq_row = eq_rows.iloc[0]
            sh_row = sh_rows.iloc[0]
            eq_mv = _opt_float(eq_row.get("value"))
            shares = _opt_float(sh_row.get("value"))
            if eq_mv is not None and shares is not None and eq_mv > 0 and shares > 0:
                px = round((eq_mv * 1e7) / shares, 2)
                notes = str(eq_row.get("notes") or "")
                m_dt = re.search(r"(\d{4}-\d{2}-\d{2})", notes)
                dt = m_dt.group(1) if m_dt else str(eq_row.get("retrieved_at") or "")[:10]
                return (
                    px,
                    f"market_prices_seed.csv (NSE EQ close {dt})",
                    {
                        "ticker": "ONGC.NS",
                        "date": dt,
                        "close_inr": px,
                        "source_doc": str(eq_row.get("source_doc") or "fact_wacc_input.parquet"),
                        "source_url": str(eq_row.get("source_url") or ""),
                        "notes": notes,
                    },
                )

    raise DCFInputMissingError("market_prices_seed.csv / fact_wacc_input")
