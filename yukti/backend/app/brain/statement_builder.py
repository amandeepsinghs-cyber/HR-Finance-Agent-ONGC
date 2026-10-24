"""Financial Statement Visual Builder (P4.2; SPEC-09 §4.1, SPEC-01 §5.1–5.2, SPEC-03 §5.1).

Transforms verified SPEC-01 statement-line SSOT rows or local snapshot rows into the canonical
`visual.type = "statement"` (`StatementSpec`) payload for:
  - `pnl` (Statement of Profit and Loss)
  - `balance_sheet` (Balance Sheet)
  - `cash_flow` (Statement of Cash Flows)

Key guarantees:
1. Only `verified=TRUE` rows are emitted; any period lacking verified rows is omitted and a
   caveat footnote is attached (no silent fallback to unverified numbers).
2. `None` / `null` is preserved as `None` (never coerced to `0`).
3. Row order within and across sections preserves SSOT `line_order` (`order`) 100%.
4. Artificial prefixes (`"A1."`, `"I."`, `"   — "`, `"Less: "`, `"Add/(Less): "`) and formula
   suffixes (`"(I + II)"`, `"(A1 to A7)"`) are stripped so hierarchy is expressed purely via
   `level` (0–3) and `kind` (`"line" | "subtotal" | "total"`) (BUG-39).
5. `totals_check` is computed for P&L, Balance Sheet (`A = E + L`), and Cash Flow
   (`Closing Cash = Opening Cash + Net Cash Change = BS Cash`).
6. Emission of `visual.type="statement"` in `presenter.py` is gated behind the `statement`
   token in `YUKTI_CONTRACT_V3_FIELDS` (SPEC-03 §5.1).
"""

from __future__ import annotations

from functools import lru_cache
import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple

StatementKind = Literal["pnl", "balance_sheet", "cash_flow"]
RowKind = Literal["line", "subtotal", "total"]

# Strip artificial numbering/indent prefixes and formula parentheticals (BUG-39)
_LEADING_DASH_RE = re.compile(r"^\s*(?:[—–-]+\s*)+")
_LEADING_CODE_RE = re.compile(r"^\s*(?:(?:[IVX]{1,4}|[A-Z]\d{0,2}|\d{1,2})[.)]\s+)+")
_LEADING_VERB_RE = re.compile(r"^\s*(?:less|add|add\s*/\s*\(less\)|memo)\s*:\s*", re.IGNORECASE)
_TRAILING_FORMULA_RE = re.compile(
    r"\s*\((?:[IVX]+\s*(?:\+|\-|\bto\b)\s*[IVX]+(?:\s*\+\s*[IVX]+)*|[A-Z]\d+\s*(?:\+|\bto\b)\s*[A-Z]\d+)\)\s*$",
    re.IGNORECASE,
)


def v3_field_enabled(token: str = "statement") -> bool:
    """Returns True if `token` is enabled in `YUKTI_CONTRACT_V3_FIELDS` (SPEC-03 §5.1)."""
    raw = os.getenv("YUKTI_CONTRACT_V3_FIELDS", "")
    if not raw:
        return False
    tokens = {t.strip().lower() for t in raw.split(",") if t.strip()}
    return token.strip().lower() in tokens or "all" in tokens or "*" in tokens


def fy_sort_key(fy: str) -> int:
    """Extracts numeric FY key for latest-first sorting (e.g. 'FY26' -> 2026, 'FY99' -> 1999)."""
    m = re.search(r"(\d{2,4})$", str(fy).strip().upper())
    if not m:
        return 0
    val = int(m.group(1))
    if val < 100:
        return (2000 + val) if val <= 79 else (1900 + val)
    return val


def sort_periods_latest_first(periods: Sequence[str]) -> List[str]:
    """Returns deduplicated periods ordered latest-first (e.g. ['FY26', 'FY25', 'FY24'])."""
    seen: List[str] = []
    for p in periods:
        ps = str(p).strip().upper()
        if ps and ps not in seen:
            seen.append(ps)
    return sorted(seen, key=fy_sort_key, reverse=True)


def prior_fy(fy: str) -> str:
    """Returns the immediately preceding fiscal year code (e.g. 'FY26' -> 'FY25')."""
    m = re.match(r"^FY(\d{2})$", str(fy).strip().upper())
    if m:
        yr = int(m.group(1))
        prev = (yr - 1) % 100
        return f"FY{prev:02d}"
    return "Prior FY"


def format_period_label(fy: str) -> str:
    """Formats 'FY26' -> 'FY 2025-26' per SPEC-09 §4.1."""
    m = re.match(r"^FY(\d{2})$", str(fy).strip().upper())
    if m:
        end_yy = int(m.group(1))
        end_yyyy = (2000 + end_yy) if end_yy <= 79 else (1900 + end_yy)
        start_yyyy = end_yyyy - 1
        return f"FY {start_yyyy}-{end_yy:02d}"
    return str(fy).strip()


# Canonical metadata per line_code (supports both SPEC-01 SSOT codes and legacy 10-yr snapshot codes)
# Fields: (statement, section_id, section_label, level, kind, order, clean_label)
STATEMENT_LINE_META: Dict[str, Tuple[StatementKind, str, str, int, RowKind, int, str]] = {
    # ---------------- P&L (SSOT & Synthetic Fixture Codes) ----------------
    "REV_OPS": ("pnl", "income", "Income", 1, "line", 10, "Revenue from operations"),
    "PL.REV_OPS": ("pnl", "income", "Income", 1, "line", 10, "Revenue from operations"),
    "OTHER_INC": ("pnl", "income", "Income", 1, "line", 20, "Other income"),
    "PL.OTHER_INCOME": ("pnl", "income", "Income", 1, "line", 20, "Other income"),
    "TOT_INC": ("pnl", "income", "Income", 0, "subtotal", 30, "Total income"),
    "PL.TOTAL_INCOME": ("pnl", "income", "Income", 0, "subtotal", 30, "Total income"),
    "PURCHASES": ("pnl", "expenses", "Expenses", 1, "line", 40, "Purchases of stock-in-trade"),
    "PL.PURCHASES": ("pnl", "expenses", "Expenses", 1, "line", 40, "Purchases of stock-in-trade"),
    "INV_CHANGE": ("pnl", "expenses", "Expenses", 1, "line", 45, "Changes in inventories of finished goods and stock-in-trade"),
    "PL.INV_CHANGE": ("pnl", "expenses", "Expenses", 1, "line", 45, "Changes in inventories of finished goods and stock-in-trade"),
    "STAT_LEVIES": ("pnl", "expenses", "Expenses", 1, "line", 50, "Statutory levies"),
    "PL.STAT_LEVIES": ("pnl", "expenses", "Expenses", 1, "line", 50, "Statutory levies"),
    "PROD_EXP": ("pnl", "expenses", "Expenses", 1, "line", 60, "Production, transportation & operating expenditure"),
    "PL.PROD_EXP": ("pnl", "expenses", "Expenses", 1, "line", 60, "Production, transportation & operating expenditure"),
    "EMP_BENEFIT": ("pnl", "expenses", "Expenses", 1, "line", 70, "Employee benefits expense"),
    "PL.EMP_BENEFIT": ("pnl", "expenses", "Expenses", 1, "line", 70, "Employee benefits expense"),
    "EXPL_WRITEOFF": ("pnl", "expenses", "Expenses", 1, "line", 80, "Exploration costs written off"),
    "PL.EXPL_WRITEOFF": ("pnl", "expenses", "Expenses", 1, "line", 80, "Exploration costs written off"),
    "DDA": ("pnl", "expenses", "Expenses", 1, "line", 90, "Depletion, depreciation & amortisation"),
    "PL.DDA": ("pnl", "expenses", "Expenses", 1, "line", 90, "Depletion, depreciation & amortisation"),
    "FIN_COST": ("pnl", "expenses", "Expenses", 1, "line", 100, "Finance costs"),
    "PL.FIN_COST": ("pnl", "expenses", "Expenses", 1, "line", 100, "Finance costs"),
    "OTHER_EXP": ("pnl", "expenses", "Expenses", 1, "line", 110, "Other expenses"),
    "PL.OTHER_EXP": ("pnl", "expenses", "Expenses", 1, "line", 110, "Other expenses"),
    "TOT_EXP": ("pnl", "expenses", "Expenses", 0, "subtotal", 115, "Total expenses"),
    "PL.TOTAL_EXPENSE": ("pnl", "expenses", "Expenses", 0, "subtotal", 115, "Total expenses"),
    "PBT_BEFORE_EXC": ("pnl", "profit", "Profit & Tax", 0, "subtotal", 118, "Profit before exceptional items and tax"),
    "PL.PBT_PRE_EXC": ("pnl", "profit", "Profit & Tax", 0, "subtotal", 118, "Profit before exceptional items and tax"),
    "EXCEPTIONAL": ("pnl", "profit", "Profit & Tax", 1, "line", 120, "Exceptional items"),
    "PL.EXCEPTIONAL": ("pnl", "profit", "Profit & Tax", 1, "line", 120, "Exceptional items"),
    "PBT": ("pnl", "profit", "Profit & Tax", 0, "subtotal", 130, "Profit before tax (PBT)"),
    "PL.PBT": ("pnl", "profit", "Profit & Tax", 0, "subtotal", 130, "Profit before tax (PBT)"),
    "TAX_EXP": ("pnl", "profit", "Profit & Tax", 1, "line", 140, "Tax expense"),
    "PL.TAX": ("pnl", "profit", "Profit & Tax", 1, "line", 140, "Tax expense"),
    "CURR_TAX": ("pnl", "profit", "Profit & Tax", 2, "line", 141, "Current tax"),
    "PL.CURR_TAX": ("pnl", "profit", "Profit & Tax", 2, "line", 141, "Current tax"),
    "DEF_TAX": ("pnl", "profit", "Profit & Tax", 2, "line", 142, "Deferred tax"),
    "PL.DEF_TAX": ("pnl", "profit", "Profit & Tax", 2, "line", 142, "Deferred tax"),
    "PAT": ("pnl", "profit", "Profit & Tax", 0, "total", 150, "Profit for the year (PAT)"),
    "PL.PAT": ("pnl", "profit", "Profit & Tax", 0, "total", 150, "Profit for the year (PAT)"),
    "OCI": ("pnl", "profit", "Profit & Tax", 1, "line", 160, "Other comprehensive income (net of tax)"),
    "PL.OCI": ("pnl", "profit", "Profit & Tax", 1, "line", 160, "Other comprehensive income (net of tax)"),
    "TCI": ("pnl", "profit", "Profit & Tax", 0, "subtotal", 170, "Total comprehensive income"),
    "PL.TCI": ("pnl", "profit", "Profit & Tax", 0, "subtotal", 170, "Total comprehensive income"),
    "EPS_BASIC": ("pnl", "profit", "Profit & Tax", 1, "line", 180, "Basic and diluted EPS (₹)"),
    "PL.EPS_BASIC": ("pnl", "profit", "Profit & Tax", 1, "line", 180, "Basic and diluted EPS (₹)"),
    "EPS_DILUTED": ("pnl", "profit", "Profit & Tax", 1, "line", 185, "Diluted EPS (₹)"),
    "PL.EPS_DILUTED": ("pnl", "profit", "Profit & Tax", 1, "line", 185, "Diluted EPS (₹)"),
    # ---------------- P&L (Legacy 23-line Snapshot Codes) ----------------
    "gross_revenue_inr_cr": ("pnl", "income", "Income", 1, "line", 1, "Revenue from operations"),
    "crude_oil_revenue_inr_cr": ("pnl", "income", "Income", 2, "line", 2, "Crude oil revenue"),
    "natural_gas_revenue_inr_cr": ("pnl", "income", "Income", 2, "line", 3, "Natural gas revenue"),
    "vap_revenue_inr_cr": ("pnl", "income", "Income", 2, "line", 4, "Value-added products (LPG, Naphtha, C2-C3)"),
    "other_income_inr_cr": ("pnl", "income", "Income", 1, "line", 5, "Other income"),
    "total_income_inr_cr": ("pnl", "income", "Income", 0, "subtotal", 6, "Total income"),
    "statutory_levies_total_inr_cr": ("pnl", "expenses", "Expenses", 1, "line", 7, "Statutory levies"),
    "royalty_inr_cr": ("pnl", "expenses", "Expenses", 2, "line", 8, "Royalty (Offshore & Onshore)"),
    "oidb_cess_inr_cr": ("pnl", "expenses", "Expenses", 2, "line", 9, "OIDB cess"),
    "saed_windfall_tax_inr_cr": ("pnl", "expenses", "Expenses", 2, "line", 10, "SAED / windfall tax on crude"),
    "net_revenue_inr_cr": ("pnl", "expenses", "Expenses", 0, "subtotal", 11, "Net realised revenue (after statutory levies)"),
    "prod_transport_selling_exp_inr_cr": ("pnl", "expenses", "Expenses", 1, "line", 12, "Production, transportation & operating expenditure"),
    "employee_benefit_net_pnl_inr_cr": ("pnl", "expenses", "Expenses", 1, "line", 13, "Employee benefits expense"),
    "other_expenses_inr_cr": ("pnl", "expenses", "Expenses", 1, "line", 14, "Other operating & provisions expense"),
    "ebitda_inr_cr": ("pnl", "expenses", "Expenses", 0, "subtotal", 15, "EBITDA (operating profit before exploration & DD&A)"),
    "exploration_costs_written_off_inr_cr": ("pnl", "expenses", "Expenses", 1, "line", 16, "Exploration costs written off"),
    "dda_inr_cr": ("pnl", "expenses", "Expenses", 1, "line", 17, "Depletion, depreciation & impairment (DD&A)"),
    "finance_costs_inr_cr": ("pnl", "expenses", "Expenses", 1, "line", 18, "Finance costs"),
    "exceptional_items_inr_cr": ("pnl", "profit", "Profit & Tax", 1, "line", 19, "Exceptional items"),
    "pbt_inr_cr": ("pnl", "profit", "Profit & Tax", 0, "subtotal", 20, "Profit before tax (PBT)"),
    "tax_expense_total_inr_cr": ("pnl", "profit", "Profit & Tax", 1, "line", 21, "Tax expense (current & deferred)"),
    "pat_inr_cr": ("pnl", "profit", "Profit & Tax", 0, "total", 22, "Profit for the year (PAT)"),
    "consolidated_pat_inr_cr": ("pnl", "profit", "Profit & Tax", 1, "line", 23, "Consolidated group PAT (memo)"),
    # ---------------- Balance Sheet (SSOT & Legacy 24-line Snapshot Codes) ----------------
    "BS.OIL_GAS_ASSETS": ("balance_sheet", "non_current_assets", "Non-Current Assets", 1, "line", 1, "Oil and gas assets (net block)"),
    "oil_and_gas_assets_inr_cr": ("balance_sheet", "non_current_assets", "Non-Current Assets", 1, "line", 1, "Oil and gas assets (net block)"),
    "BS.OTHER_PPE_ROU": ("balance_sheet", "non_current_assets", "Non-Current Assets", 1, "line", 2, "Other property, plant, equipment & right-of-use assets"),
    "other_ppe_and_rou_inr_cr": ("balance_sheet", "non_current_assets", "Non-Current Assets", 1, "line", 2, "Other property, plant, equipment & right-of-use assets"),
    "BS.CWIP": ("balance_sheet", "non_current_assets", "Non-Current Assets", 1, "line", 3, "Capital work-in-progress (CWIP & development wells)"),
    "cwip_inr_cr": ("balance_sheet", "non_current_assets", "Non-Current Assets", 1, "line", 3, "Capital work-in-progress (CWIP & development wells)"),
    "BS.EXPL_WIP": ("balance_sheet", "non_current_assets", "Non-Current Assets", 1, "line", 4, "Exploratory & evaluation wells-in-progress"),
    "exploratory_wells_in_progress_inr_cr": ("balance_sheet", "non_current_assets", "Non-Current Assets", 1, "line", 4, "Exploratory & evaluation wells-in-progress"),
    "BS.INVESTMENTS_JV": ("balance_sheet", "non_current_assets", "Non-Current Assets", 1, "line", 5, "Investments in subsidiaries, joint ventures & associates"),
    "investments_subsidiaries_jv_inr_cr": ("balance_sheet", "non_current_assets", "Non-Current Assets", 1, "line", 5, "Investments in subsidiaries, joint ventures & associates"),
    "BS.SRF": ("balance_sheet", "non_current_assets", "Non-Current Assets", 1, "line", 6, "Site restoration / abandonment deposit fund"),
    "site_restoration_fund_inr_cr": ("balance_sheet", "non_current_assets", "Non-Current Assets", 1, "line", 6, "Site restoration / abandonment deposit fund"),
    "BS.OTHER_NCA": ("balance_sheet", "non_current_assets", "Non-Current Assets", 1, "line", 7, "Long-term loans, tax & other non-current assets"),
    "other_non_current_assets_inr_cr": ("balance_sheet", "non_current_assets", "Non-Current Assets", 1, "line", 7, "Long-term loans, tax & other non-current assets"),
    "BS.NCA.TOTAL": ("balance_sheet", "non_current_assets", "Non-Current Assets", 0, "subtotal", 8, "Total non-current assets"),
    "non_current_assets_inr_cr": ("balance_sheet", "non_current_assets", "Non-Current Assets", 0, "subtotal", 8, "Total non-current assets"),
    "BS.INVENTORIES": ("balance_sheet", "current_assets", "Current Assets", 1, "line", 9, "Inventories"),
    "inventories_inr_cr": ("balance_sheet", "current_assets", "Current Assets", 1, "line", 9, "Inventories"),
    "BS.CURR_INVESTMENTS": ("balance_sheet", "current_assets", "Current Assets", 1, "line", 10, "Current investments"),
    "current_investments_inr_cr": ("balance_sheet", "current_assets", "Current Assets", 1, "line", 10, "Current investments"),
    "BS.RECEIVABLES": ("balance_sheet", "current_assets", "Current Assets", 1, "line", 11, "Trade receivables"),
    "receivables_outstanding_inr_cr": ("balance_sheet", "current_assets", "Current Assets", 1, "line", 11, "Trade receivables"),
    "BS.CCE": ("balance_sheet", "current_assets", "Current Assets", 1, "line", 12, "Cash, cash equivalents & other bank balances"),
    "cash_and_bank_inr_cr": ("balance_sheet", "current_assets", "Current Assets", 1, "line", 12, "Cash, cash equivalents & other bank balances"),
    "BS.OTHER_CA": ("balance_sheet", "current_assets", "Current Assets", 1, "line", 13, "Short-term loans & other current assets"),
    "other_current_assets_inr_cr": ("balance_sheet", "current_assets", "Current Assets", 1, "line", 13, "Short-term loans & other current assets"),
    "BS.CA.TOTAL": ("balance_sheet", "current_assets", "Current Assets", 0, "subtotal", 14, "Total current assets"),
    "current_assets_inr_cr": ("balance_sheet", "current_assets", "Current Assets", 0, "subtotal", 14, "Total current assets"),
    "BS.TOTAL_ASSETS": ("balance_sheet", "current_assets", "Current Assets", 0, "total", 15, "Total assets"),
    "total_assets_inr_cr": ("balance_sheet", "current_assets", "Current Assets", 0, "total", 15, "Total assets"),
    "BS.EQUITY.SHARE_CAPITAL": ("balance_sheet", "equity", "Equity", 1, "line", 16, "Equity share capital"),
    "equity_share_capital_inr_cr": ("balance_sheet", "equity", "Equity", 1, "line", 16, "Equity share capital"),
    "BS.EQUITY.OTHER": ("balance_sheet", "equity", "Equity", 1, "line", 17, "Other equity (retained earnings & reserves)"),
    "other_equity_reserves_inr_cr": ("balance_sheet", "equity", "Equity", 1, "line", 17, "Other equity (retained earnings & reserves)"),
    "BS.EQUITY.TOTAL": ("balance_sheet", "equity", "Equity", 0, "subtotal", 18, "Total equity"),
    "net_worth_inr_cr": ("balance_sheet", "equity", "Equity", 0, "subtotal", 18, "Total equity"),
    "BS.LIAB.LT_BORROWINGS": ("balance_sheet", "non_current_liabilities", "Non-Current Liabilities", 1, "line", 19, "Long-term borrowings"),
    "long_term_debt_inr_cr": ("balance_sheet", "non_current_liabilities", "Non-Current Liabilities", 1, "line", 19, "Long-term borrowings"),
    "BS.LIAB.LEASE_NC": ("balance_sheet", "non_current_liabilities", "Non-Current Liabilities", 1, "line", 20, "Non-current lease liabilities"),
    "lease_liabilities_non_current_inr_cr": ("balance_sheet", "non_current_liabilities", "Non-Current Liabilities", 1, "line", 20, "Non-current lease liabilities"),
    "BS.LIAB.PROVISIONS_NC": ("balance_sheet", "non_current_liabilities", "Non-Current Liabilities", 1, "line", 21, "Decommissioning & site restoration provisions"),
    "abandonment_provision_inr_cr": ("balance_sheet", "non_current_liabilities", "Non-Current Liabilities", 1, "line", 21, "Decommissioning & site restoration provisions"),
    "BS.LIAB.DTL": ("balance_sheet", "non_current_liabilities", "Non-Current Liabilities", 1, "line", 22, "Deferred tax liabilities (net)"),
    "deferred_tax_liability_net_inr_cr": ("balance_sheet", "non_current_liabilities", "Non-Current Liabilities", 1, "line", 22, "Deferred tax liabilities (net)"),
    "BS.LIAB.OTHER_NC": ("balance_sheet", "non_current_liabilities", "Non-Current Liabilities", 1, "line", 23, "Other non-current liabilities"),
    "other_non_current_liabilities_inr_cr": ("balance_sheet", "non_current_liabilities", "Non-Current Liabilities", 1, "line", 23, "Other non-current liabilities"),
    "BS.LIAB.NON_CURRENT.TOTAL": ("balance_sheet", "non_current_liabilities", "Non-Current Liabilities", 0, "subtotal", 24, "Total non-current liabilities"),
    "non_current_liabilities_inr_cr": ("balance_sheet", "non_current_liabilities", "Non-Current Liabilities", 0, "subtotal", 24, "Total non-current liabilities"),
    "BS.LIAB.ST_BORROWINGS": ("balance_sheet", "current_liabilities", "Current Liabilities", 1, "line", 25, "Short-term borrowings"),
    "BS.LIAB.PAYABLES": ("balance_sheet", "current_liabilities", "Current Liabilities", 1, "line", 26, "Trade payables"),
    "BS.LIAB.OTHER_C": ("balance_sheet", "current_liabilities", "Current Liabilities", 1, "line", 27, "Other current liabilities & provisions"),
    "BS.LIAB.CURRENT.TOTAL": ("balance_sheet", "current_liabilities", "Current Liabilities", 0, "subtotal", 28, "Total current liabilities"),
    "current_liabilities_inr_cr": ("balance_sheet", "current_liabilities", "Current Liabilities", 0, "subtotal", 28, "Total current liabilities"),
    "BS.TOTAL_EQ_LIAB": ("balance_sheet", "current_liabilities", "Current Liabilities", 0, "total", 29, "Total equity and liabilities"),
    "total_equity_and_liabilities_inr_cr": ("balance_sheet", "current_liabilities", "Current Liabilities", 0, "total", 29, "Total equity and liabilities"),
    # ---------------- Cash Flow (SSOT & Legacy 18-line Snapshot Codes) ----------------
    "CF.PBT": ("cash_flow", "operating", "Cash Flows from Operating Activities", 1, "line", 1, "Profit before tax"),
    "CF.NON_CASH_ADJ": ("cash_flow", "operating", "Cash Flows from Operating Activities", 1, "line", 2, "Adjustments for non-cash items (DD&A, write-offs & other)"),
    "non_cash_adjustments_cf_inr_cr": ("cash_flow", "operating", "Cash Flows from Operating Activities", 1, "line", 2, "Adjustments for non-cash items (DD&A, write-offs & other)"),
    "CF.WC_CHANGES": ("cash_flow", "operating", "Cash Flows from Operating Activities", 1, "line", 3, "Working capital changes"),
    "working_capital_change_cf_inr_cr": ("cash_flow", "operating", "Cash Flows from Operating Activities", 1, "line", 3, "Working capital changes"),
    "CF.TAX_PAID": ("cash_flow", "operating", "Cash Flows from Operating Activities", 1, "line", 4, "Income taxes paid (net of refunds)"),
    "income_tax_paid_cf_inr_cr": ("cash_flow", "operating", "Cash Flows from Operating Activities", 1, "line", 4, "Income taxes paid (net of refunds)"),
    "CF.CFO": ("cash_flow", "operating", "Cash Flows from Operating Activities", 0, "subtotal", 5, "Net cash from operating activities"),
    "operating_cash_flow_inr_cr": ("cash_flow", "operating", "Cash Flows from Operating Activities", 0, "subtotal", 5, "Net cash from operating activities"),
    "CF.CAPEX": ("cash_flow", "investing", "Cash Flows from Investing Activities", 1, "line", 6, "Capital expenditure on oil & gas assets, PPE & CWIP"),
    "capex_cash_outflow_inr_cr": ("cash_flow", "investing", "Cash Flows from Investing Activities", 1, "line", 6, "Capital expenditure on oil & gas assets, PPE & CWIP"),
    "CF.SUB_INV": ("cash_flow", "investing", "Cash Flows from Investing Activities", 1, "line", 7, "Investments in subsidiaries, joint ventures & associates"),
    "subsidiary_investment_cf_inr_cr": ("cash_flow", "investing", "Cash Flows from Investing Activities", 1, "line", 7, "Investments in subsidiaries, joint ventures & associates"),
    "CF.DIV_INT_REC": ("cash_flow", "investing", "Cash Flows from Investing Activities", 1, "line", 8, "Dividends and treasury interest received"),
    "dividend_interest_received_cf_inr_cr": ("cash_flow", "investing", "Cash Flows from Investing Activities", 1, "line", 8, "Dividends and treasury interest received"),
    "CF.CFI": ("cash_flow", "investing", "Cash Flows from Investing Activities", 0, "subtotal", 9, "Net cash used in investing activities"),
    "investing_cash_flow_inr_cr": ("cash_flow", "investing", "Cash Flows from Investing Activities", 0, "subtotal", 9, "Net cash used in investing activities"),
    "CF.BORROWINGS_NET": ("cash_flow", "financing", "Cash Flows from Financing Activities", 1, "line", 10, "Proceeds from / (repayment of) borrowings"),
    "net_borrowings_cf_inr_cr": ("cash_flow", "financing", "Cash Flows from Financing Activities", 1, "line", 10, "Proceeds from / (repayment of) borrowings"),
    "CF.LEASE_PAID": ("cash_flow", "financing", "Cash Flows from Financing Activities", 1, "line", 11, "Payment of lease liabilities"),
    "lease_payments_cf_inr_cr": ("cash_flow", "financing", "Cash Flows from Financing Activities", 1, "line", 11, "Payment of lease liabilities"),
    "CF.INT_PAID": ("cash_flow", "financing", "Cash Flows from Financing Activities", 1, "line", 12, "Finance costs / interest paid"),
    "interest_paid_cf_inr_cr": ("cash_flow", "financing", "Cash Flows from Financing Activities", 1, "line", 12, "Finance costs / interest paid"),
    "CF.DIV_PAID": ("cash_flow", "financing", "Cash Flows from Financing Activities", 1, "line", 13, "Dividends paid to equity shareholders"),
    "dividend_paid_cf_inr_cr": ("cash_flow", "financing", "Cash Flows from Financing Activities", 1, "line", 13, "Dividends paid to equity shareholders"),
    "CF.CFF": ("cash_flow", "financing", "Cash Flows from Financing Activities", 0, "subtotal", 14, "Net cash used in financing activities"),
    "financing_cash_flow_inr_cr": ("cash_flow", "financing", "Cash Flows from Financing Activities", 0, "subtotal", 14, "Net cash used in financing activities"),
    "CF.NET_CHANGE": ("cash_flow", "cash_summary", "Cash and Cash Equivalents", 0, "subtotal", 15, "Net increase / (decrease) in cash and cash equivalents"),
    "net_cash_change_inr_cr": ("cash_flow", "cash_summary", "Cash and Cash Equivalents", 0, "subtotal", 15, "Net increase / (decrease) in cash and cash equivalents"),
    "CF.CCE_OPEN": ("cash_flow", "cash_summary", "Cash and Cash Equivalents", 1, "line", 16, "Opening cash and cash equivalents"),
    "opening_cash_inr_cr": ("cash_flow", "cash_summary", "Cash and Cash Equivalents", 1, "line", 16, "Opening cash and cash equivalents"),
    "CF.CCE_CLOSE": ("cash_flow", "cash_summary", "Cash and Cash Equivalents", 0, "total", 17, "Closing cash and cash equivalents"),
    "closing_cash_inr_cr": ("cash_flow", "cash_summary", "Cash and Cash Equivalents", 0, "total", 17, "Closing cash and cash equivalents"),
    "CF.FCF": ("cash_flow", "cash_summary", "Cash and Cash Equivalents", 1, "line", 18, "Free cash flow (OCF less capex)"),
    "free_cash_flow_inr_cr": ("cash_flow", "cash_summary", "Cash and Cash Equivalents", 1, "line", 18, "Free cash flow (OCF less capex)"),
}

_SECTION_LABELS_FALLBACK: Dict[str, str] = {
    "income": "Income",
    "expenses": "Expenses",
    "profit": "Profit & Tax",
    "oci": "Other Comprehensive Income",
    "eps": "Earnings per Share",
    "non_current_assets": "Non-Current Assets",
    "current_assets": "Current Assets",
    "equity": "Equity",
    "non_current_liabilities": "Non-Current Liabilities",
    "current_liabilities": "Current Liabilities",
    "operating": "Cash Flows from Operating Activities",
    "investing": "Cash Flows from Investing Activities",
    "financing": "Cash Flows from Financing Activities",
    "cash_summary": "Cash and Cash Equivalents",
}


def _merge_contract_line_classes() -> None:
    """Loads fallback line metadata from `yukti/contracts/statement_line_classes.json` (P4.2 §5.2)."""
    try:
        contract_path = Path(__file__).resolve().parents[3] / "contracts" / "statement_line_classes.json"
        if not contract_path.exists():
            return
        with open(contract_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        lines_map = data.get("lines")
        if not isinstance(lines_map, dict):
            return
        for code, info in lines_map.items():
            if code in STATEMENT_LINE_META or not isinstance(info, dict):
                continue
            stmt: StatementKind = str(info.get("statement") or "pnl")  # type: ignore[assignment]
            sec_id = str(info.get("section") or "expenses")
            sec_label = str(info.get("section_label") or _SECTION_LABELS_FALLBACK.get(sec_id, sec_id.capitalize()))
            level = int(info.get("level", 1))
            kind: RowKind = str(info.get("kind") or "line")  # type: ignore[assignment]
            order = int(info.get("order", 99))
            label = str(info.get("label") or code)
            STATEMENT_LINE_META[code] = (stmt, sec_id, sec_label, level, kind, order, label)
    except Exception:
        pass


_merge_contract_line_classes()


def clean_statement_label(raw_label: str, line_code: Optional[str] = None) -> str:
    """Strips artificial numbering/indent prefixes and formula parentheticals (BUG-39)."""
    txt = str(raw_label or "").strip()
    if not txt and line_code and line_code in STATEMENT_LINE_META:
        return STATEMENT_LINE_META[line_code][6]
    # Repeatedly strip leading dashes, codes ("A1. ", "I. "), and "Less: " / "Add/(Less): "
    for _ in range(3):
        prev = txt
        txt = _LEADING_DASH_RE.sub("", txt)
        txt = _LEADING_CODE_RE.sub("", txt)
        txt = _LEADING_VERB_RE.sub("", txt)
        if txt == prev:
            break
    txt = _TRAILING_FORMULA_RE.sub("", txt)
    txt = re.sub(r"\s{2,}", " ", txt).strip()
    if not txt and line_code and line_code in STATEMENT_LINE_META:
        return STATEMENT_LINE_META[line_code][6]
    return txt or str(line_code or "Line item")


def _normalize_note_ref(raw_ref: Any) -> Optional[str]:
    if raw_ref is None:
        return None
    s = str(raw_ref).strip()
    if not s or s.lower() in ("none", "null", "schedule iii", "ind-as 7", "derived", "consolidated p&l"):
        return None
    s = re.sub(r"^note\s+", "", s, flags=re.IGNORECASE).strip()
    return s or None


def _coerce_num_or_none(v: Any) -> Optional[float]:
    """Converts finite numbers to float; preserves None/null (never coerces None to 0)."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace(",", "")
        if not s or s in ("-", "—", "null", "None"):
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _infer_meta(
    statement: StatementKind,
    line_code: Optional[str],
    raw_label: str,
    raw_row: Dict[str, Any],
    fallback_order: int,
) -> Tuple[str, str, int, RowKind, int]:
    """Returns (section_id, section_label, level, kind, order) for a statement line."""
    # Cash Flow shares `pbt_inr_cr` with P&L in the legacy snapshot
    if statement == "cash_flow" and line_code == "pbt_inr_cr":
        meta = ("cash_flow", "operating", "Cash Flows from Operating Activities", 1, "line", 1, "Profit before tax")
    else:
        meta = STATEMENT_LINE_META.get(line_code or "")

    # Order: explicit row order (`line_order` or `order`) ALWAYS wins so SSOT order is preserved 100%
    raw_order = raw_row.get("line_order") if raw_row.get("line_order") is not None else raw_row.get("order")
    order = int(raw_order) if isinstance(raw_order, (int, float)) else (meta[5] if meta else fallback_order)

    # Kind: explicit `kind` or `line_kind` on row, else meta, else label regex
    rk_raw = str(raw_row.get("kind") or raw_row.get("line_kind") or "").strip().lower()
    if rk_raw in ("total", "subtotal", "line"):
        kind: RowKind = rk_raw  # type: ignore[assignment]
    elif rk_raw in ("detail", "memo"):
        kind = "line"
    elif meta:
        kind = meta[4]
    else:
        lbl_clean = clean_statement_label(raw_label, line_code).lower()
        if re.search(r"^(profit|loss)\s+(for|after)\b|^total\s+(assets|equity\s+and\s+liabilities)|^closing\s+cash", lbl_clean):
            kind = "total"
        elif re.search(r"^(total|net\s+cash|net\s+increase|net\s+decrease|profit\s+before|ebitda|net\s+worth|net\s+realised)", lbl_clean):
            kind = "subtotal"
        else:
            kind = "line"

    # Level: explicit `level` on row (0..3), else meta, else indentation/parent inference
    raw_level = raw_row.get("level")
    if isinstance(raw_level, (int, float)) and not isinstance(raw_level, bool):
        level = max(0, min(3, int(raw_level)))
    elif meta:
        level = meta[3]
    elif kind in ("subtotal", "total"):
        level = 0
    elif raw_row.get("parent_line_code") or re.match(r"^\s{2,}|^\s*[—–-]", str(raw_label or "")):
        level = 2
    else:
        level = 1

    # Section id & label
    if meta and meta[0] == statement:
        sec_id, sec_label = meta[1], meta[2]
    else:
        raw_sec = str(raw_row.get("section") or "").strip()
        if statement == "pnl":
            if order <= 6 or raw_sec.lower() in ("revenue", "revenue breakdown", "income"):
                sec_id, sec_label = "income", "Income"
            elif order >= 19 or raw_sec.lower() in ("exceptional", "tax", "bottom line", "profit", "profit & tax"):
                sec_id, sec_label = "profit", "Profit & Tax"
            else:
                sec_id, sec_label = "expenses", "Expenses"
        elif statement == "balance_sheet":
            sl = raw_sec.lower()
            if "non-current asset" in sl or order <= 8:
                sec_id, sec_label = "non_current_assets", "Non-Current Assets"
            elif "current asset" in sl or order <= 15:
                sec_id, sec_label = "current_assets", "Current Assets"
            elif "equity" in sl or order <= 18:
                sec_id, sec_label = "equity", "Equity"
            elif "non-current liab" in sl or order <= 23:
                sec_id, sec_label = "non_current_liabilities", "Non-Current Liabilities"
            else:
                sec_id, sec_label = "current_liabilities", "Current Liabilities"
        else:
            sl = raw_sec.lower()
            if "operat" in sl or order <= 5:
                sec_id, sec_label = "operating", "Cash Flows from Operating Activities"
            elif "invest" in sl or order <= 9:
                sec_id, sec_label = "investing", "Cash Flows from Investing Activities"
            elif "financ" in sl or order <= 14:
                sec_id, sec_label = "financing", "Cash Flows from Financing Activities"
            else:
                sec_id, sec_label = "cash_summary", "Cash and Cash Equivalents"

    return sec_id, sec_label, level, kind, order


def compute_totals_check(
    statement: StatementKind,
    periods: Sequence[str],
    rows_by_code: Dict[str, Dict[str, Any]],
    all_rows: Sequence[Dict[str, Any]],
    bs_cash_by_period: Optional[Dict[str, Optional[float]]] = None,
    tolerance_cr: float = 0.5,
) -> Dict[str, Any]:
    """Computes `totals_check` across all periods for P&L, Balance Sheet, and Cash Flow."""
    def _val(codes: Sequence[str], period: str) -> Optional[float]:
        for c in codes:
            r = rows_by_code.get(c)
            if r and isinstance(r.get("values"), dict):
                v = r["values"].get(period)
                if isinstance(v, (int, float)):
                    return float(v)
        return None

    deltas: List[float] = []
    if statement == "balance_sheet":
        identity = "A = E + L"
        for p in periods:
            ta = _val(["BS.TOTAL_ASSETS", "total_assets_inr_cr", "TOTAL_ASSETS"], p)
            nca = _val(["BS.NCA.TOTAL", "non_current_assets_inr_cr", "TOT_NCA"], p)
            ca = _val(["BS.CA.TOTAL", "current_assets_inr_cr", "TOT_CA"], p)
            eq = _val(["BS.EQUITY.TOTAL", "net_worth_inr_cr", "TOT_EQUITY"], p)
            ncl = _val(["BS.LIAB.NON_CURRENT.TOTAL", "non_current_liabilities_inr_cr", "TOT_NCL"], p)
            cl = _val(["BS.LIAB.CURRENT.TOTAL", "current_liabilities_inr_cr", "TOT_CL"], p)
            teql = _val(["BS.TOTAL_EQ_LIAB", "total_equity_and_liabilities_inr_cr", "TOTAL_EQ_LIAB"], p)
            if ta is not None and nca is not None and ca is not None:
                deltas.append(abs(ta - (nca + ca)))
            if ta is not None and eq is not None and ncl is not None and cl is not None:
                deltas.append(abs(ta - (eq + ncl + cl)))
            elif ta is not None and teql is not None:
                deltas.append(abs(ta - teql))
    elif statement == "cash_flow":
        bs_tie_checked = False
        for p in periods:
            ocf = _val(["CF.CFO", "operating_cash_flow_inr_cr", "OCF"], p)
            icf = _val(["CF.CFI", "investing_cash_flow_inr_cr", "ICF"], p)
            cff = _val(["CF.CFF", "financing_cash_flow_inr_cr", "FCF_ACT"], p)
            net_chg = _val(["CF.NET_CHANGE", "net_cash_change_inr_cr", "NET_CASH_CHANGE"], p)
            open_c = _val(["CF.CCE_OPEN", "opening_cash_inr_cr", "OPENING_CASH"], p)
            close_c = _val(["CF.CCE_CLOSE", "closing_cash_inr_cr", "CLOSING_CASH"], p)
            if ocf is not None and icf is not None and cff is not None and net_chg is not None:
                deltas.append(abs((ocf + icf + cff) - net_chg))
            if open_c is not None and net_chg is not None and close_c is not None:
                deltas.append(abs((open_c + net_chg) - close_c))
            if bs_cash_by_period and close_c is not None and isinstance(bs_cash_by_period.get(p), (int, float)):
                deltas.append(abs(close_c - float(bs_cash_by_period[p])))  # type: ignore[arg-type]
                bs_tie_checked = True
        identity = (
            "Closing Cash = Opening Cash + Net Cash Change = BS Cash"
            if bs_tie_checked
            else "Closing Cash = Opening Cash + Net Cash Change"
        )
    else:
        identity = "Total Income = Revenue + Other Income; PAT = PBT - Tax"
        for p in periods:
            rev = _val(["REV_OPS", "PL.REV_OPS", "gross_revenue_inr_cr"], p)
            oi = _val(["OTHER_INC", "PL.OTHER_INCOME", "other_income_inr_cr"], p)
            ti = _val(["TOT_INC", "PL.TOTAL_INCOME", "total_income_inr_cr"], p)
            pbt = _val(["PBT", "PL.PBT", "pbt_inr_cr"], p)
            tax = _val(["TAX_EXP", "PL.TAX", "tax_expense_total_inr_cr"], p)
            pat = _val(["PAT", "PL.PAT", "pat_inr_cr"], p)
            if rev is not None and oi is not None and ti is not None:
                deltas.append(abs((rev + oi) - ti))
            if pbt is not None and tax is not None and pat is not None:
                deltas.append(abs((pbt - tax) - pat))

    max_delta = round(max(deltas), 2) if deltas else 0.0
    passed = bool(deltas) and max_delta <= tolerance_cr
    return {
        "identity": identity,
        "passed": passed,
        "max_abs_delta_cr": max_delta,
    }


@lru_cache(maxsize=1)
def load_snapshot_bs_cash_by_period() -> Dict[str, Optional[float]]:
    """Loads Balance Sheet cash & bank balances (`cash_and_bank_inr_cr` / `BS.CCE`) per FY from the local snapshot (M3)."""
    out: Dict[str, Optional[float]] = {}
    try:
        bs_path = (
            Path(__file__).resolve().parents[4]
            / "financial_build"
            / "data"
            / "ongc_10yr_balance_sheet_lines.json"
        )
        if not bs_path.exists():
            return out
        with open(bs_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            for r in data:
                if isinstance(r, dict) and r.get("line_code") in ("cash_and_bank_inr_cr", "BS.CCE"):
                    fy = str(r.get("fiscal_year") or "").strip().upper()
                    val = _coerce_num_or_none(
                        r.get("amount_inr_cr", r.get("amount_cr", r.get("value_inr_cr")))
                    )
                    if fy and val is not None:
                        out[fy] = val
    except Exception:
        pass
    return out


def build_statement_spec(
    statement: StatementKind,
    rows: Sequence[Dict[str, Any]],
    periods: Optional[Sequence[str]] = None,
    *,
    fy: Optional[str] = None,
    scope: Literal["standalone", "consolidated"] = "standalone",
    title: Optional[str] = None,
    unit: str = "INR_crore",
    show_yoy: Optional[bool] = None,
    include_prior_from_single_fy: bool = False,
    bs_cash_by_period: Optional[Dict[str, Optional[float]]] = None,
    synthetic: Optional[bool] = None,
    source_meta: Optional[Dict[str, Any]] = None,
    as_of: Optional[str] = None,
    footnotes: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Builds a `StatementSpec` dict conforming to `yukti/contracts/answer_contract.schema.json`."""
    # 1. Filter to verified=TRUE rows only (SPEC-09 §4.1, P4.2 §5.1)
    # TODO(P1): tighten to `r.get("verified") is True` once SPEC-01 SSOT rows replace the local snapshot (S1).
    verified_rows: List[Dict[str, Any]] = []
    unverified_periods: set[str] = set()
    for r in rows:
        if not isinstance(r, dict):
            continue
        if "verified" in r and r.get("verified") is not True:
            if r.get("fiscal_year"):
                unverified_periods.add(str(r["fiscal_year"]).strip().upper())
            continue
        verified_rows.append(r)

    # 2. Determine available verified periods and target period list (latest-first)
    discovered_periods: List[str] = []
    for r in verified_rows:
        if isinstance(r.get("values"), dict):
            for k, v in r["values"].items():
                if _coerce_num_or_none(v) is not None and str(k).strip().upper() not in discovered_periods:
                    discovered_periods.append(str(k).strip().upper())
        elif r.get("fiscal_year"):
            fy_k = str(r["fiscal_year"]).strip().upper()
            val_num = _coerce_num_or_none(
                r.get("value_inr_cr")
                if "value_inr_cr" in r
                else (r.get("amount_cr") if "amount_cr" in r else (r.get("amount_inr_cr") if "amount_inr_cr" in r else r.get("value")))
            )
            if val_num is not None and fy_k not in discovered_periods:
                discovered_periods.append(fy_k)
        else:
            for k, v in r.items():
                if re.match(r"^FY\d{2}$", str(k).strip().upper()) and _coerce_num_or_none(v) is not None:
                    fy_k = str(k).strip().upper()
                    if fy_k not in discovered_periods:
                        discovered_periods.append(fy_k)

    primary_fy = str(fy or (periods[0] if periods else (discovered_periods[0] if discovered_periods else "FY26"))).strip().upper()
    has_single_fy_amount = any("amount_cr" in r or "amount_inr_cr" in r for r in verified_rows if not r.get("fiscal_year"))
    has_prior_col = any("prior_fy_cr" in r or "prior_fy_amount_inr_cr" in r for r in verified_rows)
    if has_single_fy_amount and primary_fy not in discovered_periods:
        if any(_coerce_num_or_none(r.get("amount_cr", r.get("amount_inr_cr"))) is not None for r in verified_rows):
            discovered_periods.append(primary_fy)
    prior_code = prior_fy(primary_fy)
    if include_prior_from_single_fy and has_prior_col and prior_code not in discovered_periods:
        if any(_coerce_num_or_none(r.get("prior_fy_cr", r.get("prior_fy_amount_inr_cr"))) is not None for r in verified_rows):
            discovered_periods.append(prior_code)

    requested_periods = sort_periods_latest_first(periods) if periods else sort_periods_latest_first(discovered_periods)
    omitted_periods: List[str] = []
    active_periods: List[str] = []
    for p in requested_periods:
        if p in discovered_periods:
            active_periods.append(p)
        else:
            omitted_periods.append(p)

    # 3. Group rows by line_code (or clean label) while preserving 100% of SSOT `line_order` (`order`)
    grouped: Dict[str, Dict[str, Any]] = {}
    for idx, r in enumerate(verified_rows):
        code = str(r.get("line_code") or "").strip() or None
        raw_lbl = str(
            r.get("line_name_as_reported")
            or r.get("display_name")
            or r.get("label")
            or r.get("line_item")
            or r.get("line_name")
            or code
            or f"Row {idx + 1}"
        )
        sec_id, sec_label, level, kind, order = _infer_meta(statement, code, raw_lbl, r, fallback_order=(idx + 1) * 10)
        key = code or f"__row_{idx}_{clean_statement_label(raw_lbl)}"

        if key not in grouped:
            # S2 (BUG-39): strip artificial prefixes/formula suffixes from the reported label rather than
            # replacing reported parentheticals (e.g. "(HPCL, OVL, MRPL, OPaL)") with a generic label.
            clean_lbl = clean_statement_label(raw_lbl, code)

            grouped[key] = {
                "line_code": code,
                "label": clean_lbl,
                "level": level,
                "kind": kind,
                "values": {p: None for p in active_periods},
                "note_ref": _normalize_note_ref(r.get("note_ref") or r.get("schedule_ref")),
                "source": None,
                "is_restated": bool(r.get("is_restated")) if "is_restated" in r else None,
                "_raw_yoy": _coerce_num_or_none(r.get("yoy_pct") if "yoy_pct" in r else r.get("yoy_change_pct")),
                "_sec_id": sec_id,
                "_sec_label": sec_label,
                "_order": order,
                "_idx": idx,
            }

        entry = grouped[key]
        # Populate period values (preserving None for missing/null)
        if isinstance(r.get("values"), dict):
            for p in active_periods:
                if p in r["values"]:
                    entry["values"][p] = _coerce_num_or_none(r["values"][p])
        elif r.get("fiscal_year"):
            r_fy = str(r["fiscal_year"]).strip().upper()
            if r_fy in active_periods:
                raw_v = (
                    r.get("value_inr_cr")
                    if "value_inr_cr" in r
                    else (r.get("amount_cr") if "amount_cr" in r else (r.get("amount_inr_cr") if "amount_inr_cr" in r else r.get("value")))
                )
                entry["values"][r_fy] = _coerce_num_or_none(raw_v)
        else:
            # Single-FY (+ optional prior_fy_cr) or wide FY columns
            if primary_fy in active_periods and ("amount_cr" in r or "amount_inr_cr" in r or "value" in r):
                raw_v = r.get("amount_cr") if "amount_cr" in r else (r.get("amount_inr_cr") if "amount_inr_cr" in r else r.get("value"))
                entry["values"][primary_fy] = _coerce_num_or_none(raw_v)
            if prior_code in active_periods and ("prior_fy_cr" in r or "prior_fy_amount_inr_cr" in r):
                raw_pv = r.get("prior_fy_cr") if "prior_fy_cr" in r else r.get("prior_fy_amount_inr_cr")
                entry["values"][prior_code] = _coerce_num_or_none(raw_pv)
            for p in active_periods:
                if p in r:
                    entry["values"][p] = _coerce_num_or_none(r[p])

        # Source lineage per row (from latest period or explicit `source` dict)
        if isinstance(r.get("source"), dict) and r["source"].get("doc"):
            pg = r["source"].get("page")
            entry["source"] = {
                "doc": str(r["source"]["doc"]),
                "page": int(pg) if isinstance(pg, (int, float)) and not isinstance(pg, bool) else None,
            }
        elif r.get("source_doc") and entry["source"] is None:
            pg = r.get("source_page")
            entry["source"] = {
                "doc": str(r["source_doc"]),
                "page": int(pg) if isinstance(pg, (int, float)) and not isinstance(pg, bool) else None,
            }
        if r.get("is_restated"):
            entry["is_restated"] = True

    # 4. Sort rows strictly by (order, original_index) so SSOT `line_order` is preserved 100%
    ordered_entries = sorted(grouped.values(), key=lambda x: (x["_order"], x["_idx"]))

    # 5. Compute YoY % (for periods[0] vs periods[1]; omitted for subtotals/totals when base <= 0 per SPEC-09 §4.1)
    effective_show_yoy = (len(active_periods) >= 2) if show_yoy is None else bool(show_yoy)
    sections_list: List[Dict[str, Any]] = []
    rows_by_code: Dict[str, Dict[str, Any]] = {}
    flat_rows_out: List[Dict[str, Any]] = []

    for item in ordered_entries:
        row_out: Dict[str, Any] = {
            "label": item["label"],
            "level": item["level"],
            "kind": item["kind"],
            "values": {p: item["values"].get(p, None) for p in active_periods},
        }
        if item.get("line_code"):
            row_out["line_code"] = item["line_code"]

        # YoY calculation
        yoy_val: Optional[float] = None
        if len(active_periods) >= 2:
            v0 = row_out["values"].get(active_periods[0])
            v1 = row_out["values"].get(active_periods[1])
            if isinstance(v0, (int, float)) and isinstance(v1, (int, float)):
                if item["kind"] in ("subtotal", "total") and v1 <= 0:
                    yoy_val = None
                elif v1 != 0:
                    yoy_val = round(((float(v0) - float(v1)) / abs(float(v1))) * 100.0, 1)
        elif item.get("_raw_yoy") is not None and item["kind"] == "line":
            yoy_val = round(float(item["_raw_yoy"]), 1)

        if yoy_val is not None:
            row_out["yoy_pct"] = yoy_val

        if item.get("note_ref"):
            row_out["note_ref"] = item["note_ref"]
        if item.get("source"):
            row_out["source"] = item["source"]
        if item.get("is_restated") is not None:
            row_out["is_restated"] = bool(item["is_restated"])

        if row_out.get("line_code"):
            rows_by_code[row_out["line_code"]] = row_out
        flat_rows_out.append(row_out)

        sec_id = item["_sec_id"]
        sec_label = item["_sec_label"]
        if not sections_list or sections_list[-1]["id"] != sec_id:
            sections_list.append({"id": sec_id, "label": sec_label, "rows": [row_out]})
        else:
            sections_list[-1]["rows"].append(row_out)

    # 6. Build default title, period_labels, footnotes, and totals_check
    default_titles: Dict[StatementKind, str] = {
        "pnl": f"Statement of Profit and Loss ({scope.capitalize()})",
        "balance_sheet": f"Balance Sheet ({scope.capitalize()})",
        "cash_flow": f"Statement of Cash Flows ({scope.capitalize()})",
    }
    period_labels = {p: format_period_label(p) for p in active_periods}
    footnotes_out: List[str] = list(footnotes) if footnotes else [
        "Figures in ₹ crore. Negative values in parentheses."
    ]
    for om_p in omitted_periods:
        reason = (
            f"Period {om_p} omitted: rows for {om_p} failed verification gates (verified=FALSE)."
            if om_p in unverified_periods
            else f"Period {om_p} omitted: no verified rows available for {om_p}."
        )
        if reason not in footnotes_out:
            footnotes_out.append(reason)

    totals_check = compute_totals_check(
        statement=statement,
        periods=active_periods,
        rows_by_code=rows_by_code,
        all_rows=flat_rows_out,
        bs_cash_by_period=bs_cash_by_period,
    )

    spec_out: Dict[str, Any] = {
        "statement": statement,
        "scope": scope,
        "title": title or default_titles.get(statement, "Financial Statement"),
        "unit": unit,
        "periods": active_periods,
        "period_labels": period_labels,
        "show_yoy": effective_show_yoy,
        "sections": sections_list,
        "totals_check": totals_check,
        "footnotes": footnotes_out,
    }
    if source_meta is not None:
        spec_out["source"] = source_meta
    if as_of:
        spec_out["as_of"] = as_of
    if synthetic is not None:
        spec_out["synthetic"] = bool(synthetic)
    return spec_out
