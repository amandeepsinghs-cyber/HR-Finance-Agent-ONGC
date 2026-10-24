"""Input loading from SSOT gold tables, Damodaran archives, and manual seeds.

SPEC-02 §3.1, §3.3; Packet: docs/delegation/packets/v3/P1.9_wacc_inputs.md
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import pandas as pd

from financial_ssot.wacc import damodaran

APP_ROOT = Path(__file__).resolve().parents[2]
FACT_PARQUET = APP_ROOT / "financial_ssot" / "out" / "fact_financial_statement_line.parquet"
RBI_SEED_CSV = APP_ROOT / "knowledge" / "public_sources" / "market_data" / "rbi" / "gsec10y_fy_end_seed.csv"
MARKET_SEED_CSV = APP_ROOT / "knowledge" / "public_sources" / "market_data" / "manual" / "market_prices_seed.csv"

# Statutory tax rates for ONGC Standalone (from AR Tax Reconciliation Notes / Finance Acts)
# FY17-FY18: 30% + 12% surcharge + 3% cess = 34.608%
# FY19: 30% + 12% surcharge + 4% cess = 34.944%
# FY20-FY26: Section 115BAA 22% + 10% surcharge + 4% cess = 25.168% (cited as 25.17%)
STATUTORY_TAX_RATES: dict[str, float] = {
    "FY16": 34.608,
    "FY17": 34.608,
    "FY18": 34.608,
    "FY19": 34.944,
    "FY20": 25.170,
    "FY21": 25.170,
    "FY22": 25.170,
    "FY23": 25.170,
    "FY24": 25.170,
    "FY25": 25.170,
    "FY26": 25.170,
}

# Fiscal year end date mapping
FY_END_DATES: dict[str, str] = {
    "FY17": "2017-03-31",
    "FY18": "2018-03-31",
    "FY19": "2019-03-31",
    "FY20": "2020-03-31",
    "FY21": "2021-03-31",
    "FY22": "2022-03-31",
    "FY23": "2023-03-31",
    "FY24": "2024-03-31",
    "FY25": "2025-03-31",
    "FY26": "2026-03-31",
}


@dataclass
class FYInputBundle:
    fiscal_year: str
    as_of_date: str
    rf_gsec_10y_pct: float | None = None
    default_spread_pct: float | None = None
    rf_used_pct: float | None = None
    erp_mature_pct: float | None = None
    crp_pct: float | None = None
    erp_total_pct: float | None = None
    unlevered_beta: float | None = None
    beta_doc: str | None = None
    tax_rate_pct: float | None = None
    finance_cost_inr_cr: float | None = None
    decom_unwind_inr_cr: float | None = None
    borrowings_inr_cr: float | None = None
    lease_liab_inr_cr: float | None = None
    total_debt_inr_cr: float | None = None
    prior_total_debt_inr_cr: float | None = None
    avg_total_debt_inr_cr: float | None = None
    equity_bv_inr_cr: float | None = None
    equity_mv_inr_cr: float | None = None
    damodaran_doc: str | None = None
    damodaran_notes: str | None = None
    failed_rule_ids: list[str] = field(default_factory=list)


def load_statement_inputs(parquet_path: Path | None = None) -> dict[str, dict[str, float]]:
    """Extract required financial lines per fiscal year from gold statements parquet."""
    if parquet_path is None:
        parquet_path = FACT_PARQUET
    if not parquet_path.exists():
        raise FileNotFoundError(f"Parquet file not found: {parquet_path}")

    df = pd.read_parquet(parquet_path)
    sa = df[
        (df["scope"] == "standalone")
        & (df["period_type"] == "annual")
        & (df["verified"] == True)
    ]

    fys = [f"FY{y}" for y in range(16, 27)]
    out: dict[str, dict[str, float]] = {}

    for fy in fys:
        sub = sa[sa["fiscal_year"] == fy]

        def get_val(lc: str) -> float | None:
            m = sub[sub["line_code"] == lc]
            if m.empty:
                return None
            m_latest = m[m["is_latest_vintage"] == True]
            if not m_latest.empty:
                val = m_latest.iloc[0]["value_inr_cr"]
            else:
                val = m.iloc[0]["value_inr_cr"]
            return float(val) if val is not None and not pd.isna(val) else None

        fin_cost = get_val("PL.FIN_COST")
        decom_unwind = get_val("N36.UNWIND_DECOM")

        # Borrowings: prefer audited Balance Sheet (NC + C) when present and > 0, fallback to 10-year summary
        borrow_10yr = get_val("BS.BORROW_TOTAL_10YR")
        borrow_nc = get_val("BS.BORROW_NC")
        borrow_cur = get_val("BS.BORROW_CUR")
        borrow_bs = (
            (borrow_nc or 0.0) + (borrow_cur or 0.0)
            if (borrow_nc is not None or borrow_cur is not None)
            else None
        )
        if borrow_bs is not None and borrow_bs > 0:
            borrowings = borrow_bs
        elif borrow_10yr is not None:
            borrowings = borrow_10yr
        else:
            borrowings = borrow_bs

        # Lease liabilities: prefer audited Balance Sheet (NC + C) when present and > 0, fallback to 10-year summary
        lease_10yr = get_val("BS.LEASE_LIAB_TOTAL_10YR")
        lease_nc = get_val("BS.LEASE_LIAB_NC")
        lease_cur = get_val("BS.LEASE_LIAB_C")
        lease_bs = (
            (lease_nc or 0.0) + (lease_cur or 0.0)
            if (lease_nc is not None or lease_cur is not None)
            else None
        )
        if lease_bs is not None and lease_bs > 0:
            lease_liab = lease_bs
        elif lease_10yr is not None:
            lease_liab = lease_10yr
        else:
            lease_liab = lease_bs

        equity = get_val("BS.EQUITY.TOTAL")

        out[fy] = {
            "fin_cost": fin_cost,
            "decom_unwind": decom_unwind,
            "borrowings": borrowings,
            "lease_liab": lease_liab,
            "total_debt": (borrowings or 0.0) + (lease_liab or 0.0),
            "equity_bv": equity,
        }

    return out


def load_rbi_seed(seed_csv: Path | None = None) -> dict[str, float]:
    """Load manual RBI 10-year G-sec seed CSV if present."""
    if seed_csv is None:
        seed_csv = RBI_SEED_CSV
    if not seed_csv.exists():
        return {}

    rates: dict[str, float] = {}
    with open(seed_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fy = row.get("fiscal_year")
            y_val = row.get("yield_pct")
            if fy and y_val:
                try:
                    rates[fy.strip()] = float(y_val.strip())
                except ValueError:
                    pass
    return rates


def load_market_prices_seed(seed_csv: Path | None = None) -> dict[str, float]:
    """Load manual market prices seed CSV if present."""
    if seed_csv is None:
        seed_csv = MARKET_SEED_CSV
    if not seed_csv.exists():
        return {}

    prices: dict[str, float] = {}
    with open(seed_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dt = row.get("date")
            close = row.get("close")
            if dt and close:
                try:
                    prices[dt.strip()] = float(close.strip())
                except ValueError:
                    pass
    return prices


def build_all_inputs(
    parquet_path: Path | None = None,
    market_dir: Path | None = None,
    rbi_seed_csv: Path | None = None,
    market_seed_csv: Path | None = None,
) -> dict[str, FYInputBundle]:
    """Assemble all WACC input bundles for FY17 through FY26."""
    erp_data = damodaran.extract_india_erp(market_dir)
    beta_data = damodaran.extract_industry_beta(market_dir)
    stmt_data = load_statement_inputs(parquet_path)
    rbi_rates = load_rbi_seed(rbi_seed_csv)
    market_prices = load_market_prices_seed(market_seed_csv)

    bundles: dict[str, FYInputBundle] = {}

    fys = [f"FY{y}" for y in range(17, 27)]
    for idx, fy in enumerate(fys):
        as_of = FY_END_DATES.get(fy, f"20{fy[2:]}-03-31")
        erp_info = erp_data.get(fy, {})
        beta_info = beta_data.get(fy, {})
        stmt_info = stmt_data.get(fy, {})

        prior_fy = f"FY{int(fy[2:]) - 1}"
        prior_stmt_info = stmt_data.get(prior_fy, {})
        prior_debt = prior_stmt_info.get("total_debt")
        curr_debt = stmt_info.get("total_debt")

        avg_debt = (
            (prior_debt + curr_debt) / 2.0
            if prior_debt is not None and curr_debt is not None
            else curr_debt
        )

        rf = rbi_rates.get(fy)
        default_spread = erp_info.get("default_spread_pct")

        # Rf used = raw INR 10-yr G-sec (OD-11 decision)
        rf_used = rf

        # Market prices seed -> equity MV if available
        # Shares outstanding = 12,580,279,206 per SPEC-01 §9.1 and SPEC-02 §4
        close_price = market_prices.get(as_of) or market_prices.get(fy)
        equity_mv = (
            round((close_price * 12_580_279_206) / 1e7, 2)
            if close_price is not None
            else None
        )

        bundle = FYInputBundle(
            fiscal_year=fy,
            as_of_date=as_of,
            rf_gsec_10y_pct=rf,
            default_spread_pct=default_spread,
            rf_used_pct=rf_used,
            erp_mature_pct=erp_info.get("erp_mature_pct"),
            crp_pct=erp_info.get("crp_pct"),
            erp_total_pct=erp_info.get("erp_total_pct"),
            unlevered_beta=beta_info.get("unlevered_beta"),
            beta_doc=beta_info.get("source_doc"),
            tax_rate_pct=STATUTORY_TAX_RATES.get(fy, 25.17),
            finance_cost_inr_cr=stmt_info.get("fin_cost"),
            decom_unwind_inr_cr=stmt_info.get("decom_unwind"),
            borrowings_inr_cr=stmt_info.get("borrowings"),
            lease_liab_inr_cr=stmt_info.get("lease_liab"),
            total_debt_inr_cr=curr_debt,
            prior_total_debt_inr_cr=prior_debt,
            avg_total_debt_inr_cr=avg_debt,
            equity_bv_inr_cr=stmt_info.get("equity_bv"),
            equity_mv_inr_cr=equity_mv,
            damodaran_doc=erp_info.get("source_doc"),
            damodaran_notes=erp_info.get("notes"),
        )

        if rf is None:
            bundle.failed_rule_ids.append("W1")
        if equity_mv is None:
            bundle.failed_rule_ids.append("W1")

        bundles[fy] = bundle

    return bundles
