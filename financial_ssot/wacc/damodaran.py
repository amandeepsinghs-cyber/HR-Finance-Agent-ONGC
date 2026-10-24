"""Damodaran data extraction for India ERP, CRP, Default Spread, and Industry Beta.

SPEC-02 §3.1, §3.3; Packet: docs/delegation/packets/v3/P1.9_wacc_inputs.md
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import pandas as pd
import xlrd

APP_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MARKET_DIR = APP_ROOT / "knowledge" / "public_sources" / "market_data" / "damodaran"

# Map of fiscal year to the appropriate Damodaran files
# Each FY maps to (country_risk_file, emerging_market_beta_file)
# Note: Jan-2025 is missing from archives -> use Jan-2024 with notes='erp_vintage_gap'
FY_DAMODARAN_FILE_MAP: dict[str, tuple[str, str, str | None]] = {
    "FY17": ("archives/ctryprem17.xls", "archives/betaemerg17.xls", None),
    "FY18": ("archives/ctryprem18.xls", "archives/betaemerg18.xls", None),
    "FY19": ("archives/ctryprem19.xls", "archives/betaemerg19.xls", None),
    "FY20": ("archives/ctryprem20.xls", "archives/betaemerg20.xls", None),
    "FY21": ("archives/ctryprem21.xlsx", "archives/betaemerg21.xls", None),
    "FY22": ("archives/ctryprem22.xlsx", "archives/betaemerg22.xls", None),
    "FY23": ("archives/ctryprem23.xlsx", "archives/betaemerg23.xls", None),
    "FY24": ("archives/ctryprem24.xlsx", "archives/betaemerg24.xls", None),
    "FY25": ("archives/ctryprem24.xlsx", "archives/betaemerg24.xls", "erp_vintage_gap"),
    "FY26": ("ctryprem_20261023T071522Z.xlsx", "betaemerg_20261023T071522Z.xls", None),
}


def extract_india_erp(market_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Extract India ERP, CRP, mature market ERP, and default spread per fiscal year.

    Returns dict keyed by fiscal_year (FY17..FY26). Values are percentages (e.g. 7.263 for 7.263%).
    """
    if market_dir is None:
        market_dir = DEFAULT_MARKET_DIR

    results: dict[str, dict[str, Any]] = {}

    for fy, (cp_rel, _, note) in FY_DAMODARAN_FILE_MAP.items():
        cp_path = market_dir / cp_rel
        if not cp_path.exists():
            raise FileNotFoundError(f"Damodaran country risk file not found: {cp_path}")

        # Read sheet 'ERPs by country'
        df = pd.read_excel(cp_path, sheet_name="ERPs by country", header=None)

        # Locate India row (case-insensitive full match in any column, usually col 0)
        india_mask = df.apply(
            lambda r: r.astype(str).str.contains(r"^India$", case=False, regex=True).any(),
            axis=1,
        )
        india_matches = df[india_mask]
        if india_matches.empty:
            raise ValueError(f"India row not found in {cp_path}")

        i_row = india_matches.iloc[0]

        # In all Damodaran ctryprem templates:
        # col 0: Country
        # col 2: Moody's rating
        # col 3: Rating-based Default Spread
        # col 4: Total Equity Risk Premium
        # col 5: Country Risk Premium
        default_spread_pct = float(i_row[3]) * 100.0
        erp_total_pct = float(i_row[4]) * 100.0
        crp_pct = float(i_row[5]) * 100.0
        erp_mature_pct = erp_total_pct - crp_pct
        rating = str(i_row[2]).strip()

        results[fy] = {
            "fiscal_year": fy,
            "default_spread_pct": round(default_spread_pct, 4),
            "erp_total_pct": round(erp_total_pct, 4),
            "crp_pct": round(crp_pct, 4),
            "erp_mature_pct": round(erp_mature_pct, 4),
            "rating_moodys": rating,
            "source_doc": cp_path.name,
            "notes": note,
        }

    return results


def extract_industry_beta(market_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Extract unlevered beta for EM 'Oil/Gas (Production and Exploration)'.

    Returns dict keyed by fiscal_year (FY17..FY26).
    """
    if market_dir is None:
        market_dir = DEFAULT_MARKET_DIR

    results: dict[str, dict[str, Any]] = {}

    for fy, (_, beta_rel, _) in FY_DAMODARAN_FILE_MAP.items():
        beta_path = market_dir / beta_rel
        if not beta_path.exists():
            raise FileNotFoundError(f"Damodaran beta file not found: {beta_path}")

        wb = xlrd.open_workbook(str(beta_path))
        sheet_name = "Sheet1" if "Sheet1" in wb.sheet_names() else "Industry Averages"
        df = pd.read_excel(beta_path, sheet_name=sheet_name, header=None)

        # Locate 'Oil/Gas (Production and Exploration)' row
        og_mask = df.apply(
            lambda r: r.astype(str)
            .str.contains(r"Oil/Gas.*Production", case=False, regex=True)
            .any(),
            axis=1,
        )
        og_matches = df[og_mask]
        if og_matches.empty:
            raise ValueError(
                f"Oil/Gas (Production and Exploration) row not found in {beta_path}"
            )

        b_row = og_matches.iloc[0]
        # In all betaemerg editions: col 5 is Unlevered Beta
        unlevered_beta = float(b_row[5])
        raw_beta = float(b_row[2]) if not pd.isna(b_row[2]) else None

        results[fy] = {
            "fiscal_year": fy,
            "unlevered_beta": round(unlevered_beta, 4),
            "raw_beta": round(raw_beta, 4) if raw_beta is not None else None,
            "source_doc": beta_path.name,
        }

    return results
