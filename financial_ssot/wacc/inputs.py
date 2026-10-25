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
    share_capital_inr_cr: float | None = None
    shares_outstanding: float | None = None
    share_capital_doc: str | None = None
    share_capital_page: int | None = None
    close_price_inr: float | None = None
    price_trade_date: str | None = None
    price_source_url: str | None = None
    price_retrieved_by: str | None = None
    price_retrieved_at: str | None = None
    rbi_source_table: str | None = None
    rbi_source_url: str | None = None
    rbi_downloaded_at: str | None = None
    rbi_sha256: str | None = None
    equity_mv_inr_cr: float | None = None
    damodaran_doc: str | None = None
    damodaran_notes: str | None = None
    failed_rule_ids: list[str] = field(default_factory=list)


# Face value per equity share in INR:
# Cited in ONGC AR FY2016-17 Note 21 (p.318): "12,833,235,180 Equity Shares of ₹5 each"
# and ONGC AR FY2025-26 Note 20 (p.342) / Standalone P&L (p.297): "12,580,279,206 Equity Shares of ₹5 each"
FACE_VALUE_INR = 5.0


def load_statement_inputs(parquet_path: Path | None = None) -> dict[str, dict[str, Any]]:
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
    out: dict[str, dict[str, Any]] = {}

    for fy in fys:
        sub = sa[sa["fiscal_year"] == fy]

        def get_row(lc: str) -> pd.Series | None:
            m = sub[sub["line_code"] == lc]
            if m.empty:
                return None
            m_latest = m[m["is_latest_vintage"] == True]
            if not m_latest.empty:
                return m_latest.iloc[0]
            return m.iloc[0]

        def get_val(lc: str) -> float | None:
            r = get_row(lc)
            if r is None:
                return None
            val = r["value_inr_cr"]
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
        sc_row = get_row("BS.SHARE_CAPITAL")
        share_capital = (
            float(sc_row["value_inr_cr"])
            if sc_row is not None and sc_row["value_inr_cr"] is not None and not pd.isna(sc_row["value_inr_cr"])
            else None
        )
        sc_doc = str(sc_row["source_doc"]) if sc_row is not None and pd.notna(sc_row.get("source_doc")) else None
        sc_page = (
            int(sc_row["source_page"])
            if sc_row is not None and sc_row.get("source_page") is not None and not pd.isna(sc_row.get("source_page"))
            else None
        )

        out[fy] = {
            "fin_cost": fin_cost,
            "decom_unwind": decom_unwind,
            "borrowings": borrowings,
            "lease_liab": lease_liab,
            "total_debt": (borrowings or 0.0) + (lease_liab or 0.0),
            "equity_bv": equity,
            "share_capital": share_capital,
            "share_capital_doc": sc_doc,
            "share_capital_page": sc_page,
        }

    return out


def load_rbi_seed_meta(seed_csv: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load RBI 10-year G-sec seed CSV with full lineage metadata."""
    if seed_csv is None:
        seed_csv = RBI_SEED_CSV
    if not seed_csv.exists():
        return {}

    meta: dict[str, dict[str, Any]] = {}
    with open(seed_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fy = (row.get("fiscal_year") or "").strip()
            y_val = (row.get("yield_pct") or "").strip()
            if fy and y_val:
                try:
                    meta[fy] = {
                        "yield_pct": float(y_val),
                        "as_of_date": (row.get("as_of_date") or "").strip(),
                        "source_table": (row.get("source_table") or "").strip(),
                        "source_url": (row.get("source_url") or "").strip(),
                        "downloaded_by": (row.get("downloaded_by") or "").strip(),
                        "downloaded_at": (row.get("downloaded_at") or "").strip(),
                        "sha256": (row.get("sha256_of_source_file") or "").strip(),
                    }
                except ValueError:
                    pass
    return meta


def load_rbi_seed(seed_csv: Path | None = None) -> dict[str, float]:
    """Load manual RBI 10-year G-sec seed CSV if present."""
    return {fy: m["yield_pct"] for fy, m in load_rbi_seed_meta(seed_csv).items()}


def load_market_prices_seed_meta(seed_csv: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load market prices seed CSV with full lineage metadata, keyed by trade date, FY-end date, and FY."""
    if seed_csv is None:
        seed_csv = MARKET_SEED_CSV
    if not seed_csv.exists():
        return {}

    meta: dict[str, dict[str, Any]] = {}
    latest_march_by_fy: dict[str, str] = {}
    with open(seed_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dt = (row.get("date") or "").strip()
            close = (row.get("close") or "").strip()
            ticker = (row.get("ticker") or "").strip()
            if ticker and ticker not in ("ONGC.NS", "ONGC"):
                continue
            if dt and close:
                try:
                    val = float(close)
                except ValueError:
                    continue
                entry = {
                    "ticker": ticker or "ONGC.NS",
                    "date": dt,
                    "close": val,
                    "source_url": (row.get("source_url") or "").strip() or None,
                    "retrieved_by": (row.get("retrieved_by") or "").strip() or None,
                    "retrieved_at": (row.get("retrieved_at") or "").strip() or None,
                }
                meta[dt] = entry
                # Map March trading dates (YYYY-03-DD) to both FYxx and YYYY-03-31 (last trading day of March wins)
                if len(dt) == 10 and dt[4] == "-" and dt[5:7] == "03":
                    fy_key = f"FY{dt[2:4]}"
                    fy_end_key = f"{dt[:4]}-03-31"
                    prev_dt = latest_march_by_fy.get(fy_key)
                    if prev_dt is None or dt >= prev_dt:
                        latest_march_by_fy[fy_key] = dt
                        meta[fy_key] = entry
                        meta[fy_end_key] = entry
    return meta


def load_market_prices_seed(seed_csv: Path | None = None) -> dict[str, float]:
    """Load manual market prices seed CSV if present."""
    return {k: m["close"] for k, m in load_market_prices_seed_meta(seed_csv).items()}


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
    rbi_meta = load_rbi_seed_meta(rbi_seed_csv)
    rbi_rates = {fy: m["yield_pct"] for fy, m in rbi_meta.items()}
    market_meta = load_market_prices_seed_meta(market_seed_csv)
    market_prices = {k: m["close"] for k, m in market_meta.items()}

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
        rf_info = rbi_meta.get(fy, {})
        default_spread = erp_info.get("default_spread_pct")

        # Rf used = raw INR 10-yr G-sec (OD-11 decision)
        rf_used = rf

        # Derive shares outstanding per FY from SSOT BS.SHARE_CAPITAL ÷ ₹5 face value
        # Do not fall back to a constant if BS.SHARE_CAPITAL is missing.
        share_capital = stmt_info.get("share_capital")
        shares_outstanding = (
            round((share_capital * 1e7) / FACE_VALUE_INR, 2)
            if share_capital is not None and share_capital > 0
            else None
        )

        # Market prices seed -> equity MV if both close price and SSOT shares_outstanding are available
        close_price = market_prices.get(as_of) or market_prices.get(fy)
        price_info = market_meta.get(as_of) or market_meta.get(fy) or {}
        equity_mv = (
            round((close_price * shares_outstanding) / 1e7, 2)
            if (close_price is not None and shares_outstanding is not None)
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
            share_capital_inr_cr=share_capital,
            shares_outstanding=shares_outstanding,
            share_capital_doc=stmt_info.get("share_capital_doc"),
            share_capital_page=stmt_info.get("share_capital_page"),
            close_price_inr=close_price,
            price_trade_date=price_info.get("date"),
            price_source_url=price_info.get("source_url"),
            price_retrieved_by=price_info.get("retrieved_by"),
            price_retrieved_at=price_info.get("retrieved_at"),
            rbi_source_table=rf_info.get("source_table"),
            rbi_source_url=rf_info.get("source_url"),
            rbi_downloaded_at=rf_info.get("downloaded_at"),
            rbi_sha256=rf_info.get("sha256"),
            equity_mv_inr_cr=equity_mv,
            damodaran_doc=erp_info.get("source_doc"),
            damodaran_notes=erp_info.get("notes"),
        )

        if rf is None:
            bundle.failed_rule_ids.append("W1")
        if shares_outstanding is None and "W1" not in bundle.failed_rule_ids:
            bundle.failed_rule_ids.append("W1")
        if equity_mv is None and "W1" not in bundle.failed_rule_ids:
            bundle.failed_rule_ids.append("W1")

        bundles[fy] = bundle

    return bundles
