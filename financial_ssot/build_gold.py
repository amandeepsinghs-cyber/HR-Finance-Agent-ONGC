"""Build the verified v3 Financial SSOT (`fact_financial_statement_line`, `dim_financial_line`, `conflicts.csv`, `gate_report_<UTC>.md`).

Packet P1.6 / SPEC-01 §5–§7 / SPEC-05 §5:
- Maps bronze extracts (`statements_raw.parquet`, `ten_year_raw.parquet`, `notes_raw.parquet`, `xbrl_raw.parquet`)
  to canonical `line_code`s.
- Emits `financial_ssot/dim_financial_line.csv` (21 columns per SPEC-01 §5.2; clean display names per BUG-39).
- Runs deterministic verification gates V01–V12 (`financial_ssot.gates.verify_gates`).
- Writes:
  - `financial_ssot/out/fact_financial_statement_line.parquet`
  - `financial_ssot/out/fact_snapshot.parquet` (verified=TRUE rows only, identical schema)
  - `financial_ssot/out/fin_gate_run.parquet`
  - `financial_ssot/out/conflicts.csv`
  - `financial_ssot/out/gate_report_<UTC>.md`
"""
from __future__ import annotations

import datetime as dt
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from financial_ssot.gates.verify_gates import (
    GateRunResult,
    compute_vintage_flags,
    fy_number,
    normalize_vintage,
    verify_gates,
)

SSOT_DIR = Path(__file__).resolve().parent
OUT_DIR = SSOT_DIR / "out"
DIM_CSV_PATH = SSOT_DIR / "dim_financial_line.csv"

DIM_COLUMNS = [
    "line_code",
    "statement",
    "display_name",
    "line_name",
    "line_name_aliases",
    "section",
    "subsection",
    "parent_line_code",
    "level",
    "hierarchy_level",
    "line_order",
    "display_order",
    "line_kind",
    "line_class",
    "subtotal_formula",
    "formula",
    "sign_in_parent",
    "natural_sign",
    "schedule3_ref",
    "ind_as_schedule_iii_ref",
    "ar_note_ref_typical",
    "ar_labels",
    "ten_year_label",
    "xbrl_tags",
    "xbrl_element_name",
    "yahoo_types",
    "yahoo_field_name",
    "yahoo_equivalence",
    "scope_applicability",
    "valid_from_fy",
    "valid_to_fy",
    "unit_default",
    "is_subtotal",
    "is_total",
    "is_kpi",
    "description",
]


def _norm(s: Any) -> str:
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ""
    return re.sub(r"\s+", " ", str(s).strip()).lower()


def _clean_text(s: Any) -> Optional[str]:
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return None
    t = str(s).strip()
    return t if t and t.lower() != "nan" else None


def map_statements_group(grp: pd.DataFrame) -> List[str]:
    """Deterministically map a `(source_doc, scope, statement, fiscal_year, period_type)` slice of `statements_raw`."""
    stmt = str(grp["statement"].iloc[0])
    rows = grp.sort_values("line_seq").to_dict("records")
    codes: List[str] = []

    if stmt == "pnl":
        last_oci_item = "PL.OCI_OTHER"
        for i, r in enumerate(rows):
            lab = _norm(r["raw_label"])
            sec = _norm(r["section_path"])
            is_sub = bool(r["is_subtotal"])

            if "revenue from operations" in lab:
                code = "PL.REV_OPS"
            elif "other income" in lab and "comprehensive" not in lab:
                code = "PL.OTHER_INCOME"
            elif "total income" in lab:
                code = "PL.TOTAL_INCOME"
            elif "cost of materials consumed" in lab:
                code = "PL.COST_MATERIALS"
            elif "purchase of stock-in-trade" in lab:
                code = "PL.PURCHASES_TRADED"
            elif "changes in inventories" in lab or "32 & 33 goods and work in progress" in lab:
                code = "PL.INVENTORY_CHANGE"
            elif "production, transportation, selling" in lab:
                code = "PL.PROD_EXP"
            elif "survey cost" in lab:
                code = "PL.EXPL_SURVEY"
            elif "exploratory well cost" in lab or "exploration well cost" in lab:
                code = "PL.EXPL_WELL"
            elif "depreciation, depletion" in lab or "depletion, depreciation" in lab or "depreciation,depletion" in lab:
                code = "PL.DDA"
            elif "finance cost" in lab:
                code = "PL.FIN_COST"
            elif "impairment and write off" in lab:
                code = "PL.PROVISIONS_WRITEOFF"
            elif "total expenses" in lab:
                code = "PL.TOTAL_EXP"
            elif "profit before exceptional items and tax" in lab:
                code = "PL.PBT_PRE_EXC"
            elif "exceptional items" in lab:
                code = "PL.EXCEPTIONAL"
            elif "share of profit of associates" in lab or "share of profit/ (loss) of associates" in lab:
                code = "PL.SHARE_ASSOC"
            elif "share of profit of joint ventures" in lab or "share of profit/ (loss) of joint ventures" in lab:
                code = "PL.SHARE_JV"
            elif "profit before tax" in lab:
                code = "PL.PBT"
            elif ("current tax" in lab and "relating to" not in sec) or ("- current year" in lab and "current tax" in sec):
                code = "PL.TAX_CURRENT"
            elif "earlier years" in lab:
                code = "PL.TAX_EARLIER"
            elif "deferred tax" in lab and "tax expense" in sec:
                code = "PL.TAX_DEFERRED"
            elif "total tax expense" in lab:
                code = "PL.TAX"
            elif "profit for the year" in lab and "attributable" not in sec:
                code = "PL.PAT"
            elif "defined benefit" in lab:
                code = "PL.OCI_REMEASURE"
                last_oci_item = code
            elif "equity instruments through other comprehensive income" in lab:
                code = "PL.OCI_EQUITY"
                last_oci_item = code
            elif "exchange differences in translating" in lab:
                code = "PL.OCI_FX_TRANS"
                last_oci_item = code
            elif "effective portion of gains" in lab:
                code = "PL.OCI_HEDGE"
                last_oci_item = code
            elif "share of other comprehensive income" in lab and "not to be reclassified" in lab:
                code = "PL.OCI_JV_NR"
                last_oci_item = code
            elif "share of other comprehensive income" in lab:
                code = "PL.OCI_JV_RECLASS"
                last_oci_item = code
            elif "gain on bargain purchase" in lab:
                code = "PL.OCI_BARGAIN_GAIN"
                last_oci_item = code
            elif ("deferred tax" in lab or "income tax relating to above" in lab) and "other comprehensive income" in sec:
                code = f"{last_oci_item}_TAX"
            elif "total other comprehensive income" in lab or "total other comprehensice income" in lab:
                code = "PL.OCI"
            elif "total comprehensive income for the year" in lab and "attributable" not in sec:
                code = "PL.TCI"
            elif "owners of the company" in lab:
                if "profit for the year" in sec:
                    code = "PL.PAT_OWNERS"
                elif "other comprehensive income" in sec:
                    code = "PL.OCI_OWNERS"
                else:
                    code = "PL.TCI_OWNERS"
            elif "non-controlling interests" in lab:
                if "profit for the year" in sec:
                    code = "PL.PAT_NCI"
                elif "other comprehensive income" in sec:
                    code = "PL.OCI_NCI"
                else:
                    code = "PL.TCI_NCI"
            elif lab == "[unlabelled line]" and is_sub:
                prev_code = codes[-1] if codes else ""
                if prev_code == "PL.PAT_NCI":
                    code = "PL.PAT_ATTR_TOTAL"
                elif prev_code == "PL.OCI_NCI":
                    code = "PL.OCI_ATTR_TOTAL"
                elif prev_code == "PL.TCI_NCI":
                    code = "PL.TCI_ATTR_TOTAL"
                else:
                    code = f"PL.SUBTOTAL_{i}"
            elif "basic and diluted" in lab or "(a) basic" in lab:
                code = "PL.EPS_BASIC"
            elif "(b) diluted" in lab:
                code = "PL.EPS_DILUTED"
            else:
                code = f"UNMAPPED_PNL:{sec}:{lab}"
            codes.append(code)
        return codes

    if stmt == "balance_sheet":
        nc_assets_end = -1
        eq_start = 999999
        nc_liab_end = -1
        for r in rows:
            l = _norm(r["raw_label"])
            s = _norm(r["section_path"])
            seq = int(r["line_seq"])
            if "total non-current assets" in l or "total non- current assets" in l or "total non current assets" in l or (
                l == "[unlabelled line]" and "(1) non-current assets" in s
            ):
                nc_assets_end = seq
            if "equity share capital" in l and eq_start == 999999:
                eq_start = seq
            if "total non-current liabilities" in l or "total non- current liabilities" in l or "total non current liabilities" in l or (
                l == "[unlabelled line]" and "(1) non-current liabilities" in s
            ):
                nc_liab_end = seq

        for i, r in enumerate(rows):
            lab = _norm(r["raw_label"])
            sec = _norm(r["section_path"])
            seq = int(r["line_seq"])
            is_sub = bool(r["is_subtotal"])
            is_asset = seq < eq_start
            is_nc_asset = is_asset and (seq <= nc_assets_end or "(1) non-current assets" in sec)
            is_nc_liab = (not is_asset) and (seq <= nc_liab_end or "(1) non-current liabilities" in sec)

            if "oil and gas assets" in lab and "intangible" not in lab:
                code = "BS.OG_ASSETS"
            elif "(a) tangible" in lab and "oil and gas assets" in sec:
                code = "BS.OG_ASSETS_TANGIBLE"
            elif "(b) intangible" in lab and "oil and gas assets" in sec:
                code = "BS.OG_ASSETS_INTANGIBLE"
            elif "other property, plant and equipment" in lab:
                code = "BS.OTHER_PPE"
            elif "right-of-use assets" in lab or "right of use assets" in lab:
                code = "BS.ROU_ASSETS"
            elif "development wells in progress" in lab:
                code = "BS.CWIP_DEV_WELLS"
            elif "oil and gas facilities in progress" in lab:
                code = "BS.CWIP_OG_FACILITIES"
            elif "acquisition cost" in lab and "capital work" in sec:
                code = "BS.CWIP_ACQ_COST"
            elif "(ii) others" in lab and "capital work" in sec:
                code = "BS.CWIP_OTHER"
            elif "investment property" in lab:
                code = "BS.INV_PROPERTY"
            elif "goodwill" in lab:
                code = "BS.GOODWILL"
            elif "intangible assets" in lab and "in progress" not in lab and "under development" not in sec:
                code = "BS.INTANG_ASSETS"
            elif "exploratory wells in progress" in lab or "exploratory wells-in-progress" in lab:
                code = "BS.IAUD_EXPL_WELLS"
            elif "acquisition cost" in lab and "intangible" in sec:
                code = "BS.IAUD_ACQ_COST"
            elif "intangible oil and gas assets in progress" in lab:
                code = "BS.IAUD_INTANG_OG"
            elif ("(iii) others" in lab or "(iv) others" in lab) and "intangible assets under development" in sec:
                code = "BS.IAUD_OTHER"
            elif "joint ventures and associates" in lab:
                code = "BS.INVESTMENTS_JV_ASSOC"
            elif "other investments" in lab:
                code = "BS.INVESTMENTS_OTHER_NC"
            elif "(i) investments" in lab:
                code = "BS.INVESTMENTS_NC" if is_nc_asset else "BS.INVESTMENTS_C"
            elif "trade receivables" in lab:
                code = "BS.TRADE_REC_NC" if is_nc_asset else "BS.TRADE_REC_C"
            elif "loans" in lab:
                code = "BS.LOANS_NC" if is_nc_asset else "BS.LOANS_C"
            elif "site restoration fund" in lab:
                code = "BS.SRF_DEPOSIT_NC" if is_nc_asset else "BS.SRF_DEPOSIT_C"
            elif "finance lease receivables" in lab:
                code = "BS.FIN_LEASE_REC_NC" if is_nc_asset else "BS.FIN_LEASE_REC_C"
            elif "others" in lab and is_asset and ("financial assets" in sec or is_nc_asset):
                if "other non-current assets" in lab:
                    code = "BS.OTHER_NC_ASSETS"
                elif "other current assets" in lab:
                    code = "BS.OTHER_C_ASSETS"
                else:
                    code = "BS.OTHER_FIN_ASSETS_NC" if is_nc_asset else "BS.OTHER_FIN_ASSETS_C"
            elif "deferred tax assets" in lab:
                code = "BS.DTA_NET"
            elif "non-current tax assets" in lab:
                code = "BS.NC_TAX_ASSETS"
            elif "other non-current assets" in lab:
                code = "BS.OTHER_NC_ASSETS"
            elif "total non-current assets" in lab or "total non- current assets" in lab or "total non current assets" in lab:
                code = "BS.ASSETS.NON_CURRENT.TOTAL"
            elif "inventories" in lab:
                code = "BS.INVENTORIES"
            elif "cash and cash equivalents" in lab:
                code = "BS.CCE"
            elif "other bank balances" in lab:
                code = "BS.OTHER_BANK_BAL"
            elif "current tax assets" in lab:
                code = "BS.C_TAX_ASSETS"
            elif "other current assets" in lab:
                code = "BS.OTHER_C_ASSETS"
            elif "sub-total current assets" in lab:
                code = "BS.ASSETS.CURRENT.SUBTOTAL"
            elif "liabilities directly associated with assets" in lab:
                code = "BS.LIAB_HELD_FOR_SALE"
            elif "assets classified as held for sale" in lab or "assets/ disposal group classified as held for sale" in lab:
                code = "BS.ASSETS_HELD_FOR_SALE"
            elif "total current assets" in lab:
                code = "BS.ASSETS.CURRENT.TOTAL"
            elif "total assets" in lab:
                code = "BS.TOTAL_ASSETS"
            elif "equity share capital" in lab:
                code = "BS.SHARE_CAPITAL"
            elif "other equity" in lab:
                code = "BS.OTHER_EQUITY"
            elif "equity attributable to owners" in lab:
                code = "BS.EQUITY_OWNERS"
            elif "non-controlling interests" in lab:
                code = "BS.NCI"
            elif "total equity" == lab:
                code = "BS.EQUITY.TOTAL"
            elif "borrowings" in lab:
                code = "BS.BORROW_NC" if is_nc_liab else "BS.BORROW_CUR"
            elif "lease liabilities" in lab or "finance lease obligation" in lab:
                code = "BS.LEASE_LIAB_NC" if is_nc_liab else "BS.LEASE_LIAB_C"
            elif "trade payables" in lab:
                code = "BS.TRADE_PAY"
            elif "micro and small enterprises" in lab and "other than" not in lab:
                code = "BS.TRADE_PAY_MSME"
            elif "other than micro and small enterprises" in lab or "- to others" in lab:
                code = "BS.TRADE_PAY_OTHERS"
            elif "others" in lab and not is_asset:
                code = "BS.OTHER_FIN_LIAB_NC" if is_nc_liab else "BS.OTHER_FIN_LIAB_C"
            elif "provisions" in lab:
                code = "BS.PROV_NC" if is_nc_liab else "BS.PROV_C"
            elif "deferred tax liabilities" in lab:
                code = "BS.DTL_NET"
            elif "other non-current liabilities" in lab:
                code = "BS.OTHER_NC_LIAB"
            elif "total non-current liabilities" in lab or "total non- current liabilities" in lab or "total non current liabilities" in lab:
                code = "BS.LIAB.NON_CURRENT.TOTAL"
            elif "other current liabilities" in lab:
                code = "BS.OTHER_C_LIAB"
            elif "current tax liabilities" in lab:
                code = "BS.C_TAX_LIAB"
            elif "total current liabilities" in lab:
                code = "BS.LIAB.CURRENT.TOTAL"
            elif "total liabilities" == lab:
                code = "BS.LIAB.TOTAL"
            elif "total equity and liabilities" in lab:
                code = "BS.TOTAL_EQ_LIAB"
            elif lab == "[unlabelled line]" and is_sub:
                if is_nc_asset:
                    code = "BS.ASSETS.NON_CURRENT.TOTAL"
                elif is_asset:
                    next_labs = [_norm(rows[j]["raw_label"]) for j in range(i + 1, min(i + 4, len(rows)))]
                    if any("held for sale" in nl or "total current assets" in nl for nl in next_labs):
                        code = "BS.ASSETS.CURRENT.SUBTOTAL"
                    elif any("total assets" in nl for nl in next_labs):
                        code = "BS.ASSETS.CURRENT.TOTAL"
                    else:
                        code = "BS.TOTAL_ASSETS"
                elif is_nc_liab:
                    code = "BS.LIAB.NON_CURRENT.TOTAL"
                else:
                    code = "BS.LIAB.CURRENT.TOTAL"
            else:
                code = f"UNMAPPED_BS:{sec}:{lab}"
            codes.append(code)
        return codes

    if stmt == "cash_flow":
        seen_cce_close = False
        for i, r in enumerate(rows):
            lab = _norm(r["raw_label"])
            sec = _norm(r["section_path"])
            is_sub = bool(r["is_subtotal"])
            sub_comp = _norm(r.get("subtotal_components", ""))
            in_inv = "investing" in sec or "b. activities" in sec

            if "net profit after tax" in lab or "profit for the year" in lab:
                code = "CF.START_PROFIT"
            elif "income tax expense" in lab:
                code = "CF.ADJ_TAX"
            elif "depreciation, depletion, amortisation" in lab or "depletion, depreciation, amortisation" in lab:
                code = "CF.ADJ_DDA"
            elif "exploratory well costs written off" in lab or "exploratory well cost written off" in lab:
                code = "CF.ADJ_EXPL_WRITEOFF"
            elif "finance cost" in lab:
                code = "CF.ADJ_FIN_COST"
            elif "unrealized foreign exchange" in lab:
                code = "CF.ADJ_UNREAL_FX"
            elif "other impairment and write offs" in lab or "other provisions and write offs" in lab:
                code = "CF.ADJ_OTHER_IMPAIR"
            elif "excess provision written back" in lab:
                code = "CF.ADJ_EXCESS_PROV_WB"
            elif "interest income" in lab:
                code = "CF.ADJ_INTEREST_INC"
            elif "dividend income" in lab:
                code = "CF.ADJ_DIVIDEND_INC"
            elif "profit on sale of investment and property" in lab:
                code = "CF.ADJ_LOSS_PROFIT_INV_PPE"
            elif "sale of non-current assets" in lab or "sale of non current assets" in lab or "sale of property, plant" in lab:
                code = "CF.ADJ_SALE_PPE"
            elif "remeasurement of defined benefit" in lab or "re-measurement of defined benefit" in lab:
                code = "CF.ADJ_REMEASURE_DBP"
            elif "amortization of government grant" in lab:
                code = "CF.ADJ_AMORT_GOV_GRANT"
            elif "amortization of financial guarantee" in lab:
                code = "CF.ADJ_AMORT_FIN_GUAR"
            elif "liabilities no longer required" in lab:
                code = "CF.ADJ_LIAB_WRITTEN_BACK"
            elif "fair value loss" in lab or "fair valuation of financial instruments" in lab:
                code = "CF.ADJ_FV_FIN_INSTR"
            elif "derecognition of financial instruments" in lab:
                code = "CF.ADJ_DERECOG_FIN_INSTR"
            elif "sale of investment" in lab and not in_inv:
                code = "CF.ADJ_SALE_INV"
            elif "exceptional items" in lab:
                code = "CF.ADJ_EXCEPTIONAL"
            elif "revaluation / redemption of financial liability towards ccds" in lab or "revaluation of financial liability towards ccds" in lab:
                code = "CF.ADJ_REVAL_CCD"
            elif "pass through gain from aif" in lab:
                code = "CF.INV_AIF_GAIN" if in_inv else "CF.ADJ_AIF_GAIN"
            elif "provision for decommissioning" in lab or "provision for decommisioning" in lab:
                code = "CF.ADJ_PROV_DECOMM"
            elif "other non-cash expenditure" in lab or "other non cash expenditure" in lab:
                code = "CF.ADJ_OTHER_NON_CASH"
            elif "operating leasold land" in lab:
                code = "CF.ADJ_AMORT_LEASE_LAND"
            elif "amortization of prepayments" in lab:
                code = "CF.ADJ_AMORT_PREPAY"
            elif "gain on foreign exchange, forward contract" in lab:
                code = "CF.ADJ_FX_FORWARD_MTM"
            elif "share of profit of joint ventures" in lab:
                code = "CF.ADJ_SHARE_JV_ASSOC"
            elif "effective portion of gains/(loss) in a cash flow hedge" in lab:
                code = "CF.ADJ_CF_HEDGE"
            elif "other expenditure/income" in lab:
                code = "CF.ADJ_OTHER_EXP_INC"
            elif "operating profit before working capital changes" in lab:
                code = "CF.OP_PROFIT_BEFORE_WC"
            elif "receivables" in lab:
                code = "CF.WC_RECEIVABLES"
            elif "loans and advances" in lab:
                code = "CF.WC_LOANS_ADV"
            elif "other assets" in lab:
                code = "CF.WC_OTHER_ASSETS"
            elif "inventories" in lab:
                code = "CF.WC_INVENTORIES"
            elif "trade payable and other liabilities" in lab:
                code = "CF.WC_PAYABLES_LIAB"
            elif is_sub and ("adjustments for" in lab or "subtotal] block" in lab):
                prev_codes = codes[-3:] if codes else []
                if any(c.startswith("CF.WC_") for c in prev_codes):
                    code = "CF.WC_SUBTOTAL"
                else:
                    code = "CF.ADJ_SUBTOTAL"
            elif "cash generated from operations" in lab:
                code = "CF.CASH_GEN_OPS"
            elif "income taxes paid" in lab or "direct taxes paid" in lab:
                code = "CF.TAX_PAID"
            elif "net cash generated by operating activities" in lab or "net cash generated from operating activities" in lab:
                code = "CF.CFO"
            elif "payments for property, plant and equipment" in lab:
                code = "CF.INV_PPE_PAYMENTS"
            elif "proceeds from disposal of property, plant and equipment" in lab:
                code = "CF.INV_PPE_PROCEEDS"
            elif "exploratory and development drilling" in lab:
                code = "CF.INV_EXPL_DEV_DRILLING"
            elif "term deposits" in lab:
                code = "CF.INV_TERM_DEPOSITS"
            elif "mutual funds" in lab:
                code = "CF.INV_MUTUAL_FUNDS"
            elif "sale / (investment) in subsidiaries" in lab or "investment - subsidiaries" in lab:
                code = "CF.INV_SUBSIDIARIES"
            elif "payment for acquisition of subsidiary" in lab:
                code = "CF.INV_ACQ_SUBSIDIARY"
            elif "consideration paid towards acquisition of hpcl" in lab:
                code = "CF.INV_ACQ_HPCL"
            elif "sale of investment in joint controlled" in lab:
                code = "CF.INV_SALE_JV_ASSOC"
            elif "investment in joint" in lab or "advance/investment in joint" in lab or "redemption/(investment) in joint" in lab:
                code = "CF.INV_JV_ASSOC"
            elif "investment - associates" in lab:
                code = "CF.INV_ASSOCIATES"
            elif "investment-others" in lab or "investment- others" in lab or "investments- others" in lab:
                code = "CF.INV_OTHER"
            elif "sale proceeds of current investments" in lab:
                code = "CF.INV_SALE_CURR_INV"
            elif "loan - subsidiaries" in lab:
                code = "CF.INV_LOAN_SUBSIDIARIES"
            elif "loan - associates" in lab or "loan to associates" in lab or "loan to joint ventures" in lab or "repayment of loan by joint" in lab or "repayment/(grant) of loan to joint" in lab:
                code = "CF.INV_LOAN_JV_ASSOC"
            elif "site restoration fund" in lab:
                code = "CF.INV_SRF_DEPOSIT"
            elif "dividends received from subsidiaries" in lab or "dividends received from associates" in lab or "dividend received from associates" in lab:
                code = "CF.INV_DIV_SUB_ASSOC_JV"
            elif "dividends received on other" in lab or "dividends received from other" in lab or "dividend received from other" in lab:
                code = "CF.INV_DIV_OTHER"
            elif "interest received" in lab:
                code = "CF.INV_INTEREST_REC"
            elif "receipt towards financial guarantee" in lab:
                code = "CF.INV_FIN_GUAR_RECEIPT"
            elif "changes in non current assets/liabilities" in lab:
                code = "CF.INV_CHG_NC_ASSETS_LIAB"
            elif "capital grants received" in lab:
                code = "CF.INV_CAP_GRANTS"
            elif "earmarked deposits held on behalf of s-1 llc" in lab:
                code = "CF.INV_S1_DEPOSITS"
            elif "funds received on behalf of s-1 llc" in lab:
                code = "CF.INV_S1_FUNDS"
            elif "extinguishment of s-1 llc" in lab:
                code = "CF.INV_S1_EXTINGUISH"
            elif "investing activities" in lab and is_sub:
                code = "CF.CFI"
            elif "proceeds / repayment of current borrowings" in lab or "proceeds/repayment of current borrowings" in lab or "proceeds/(repayment) of current borrowings" in lab or "proceeds/(repayment) of short term borrowings" in lab:
                code = "CF.FIN_CURR_BORROW_NET"
            elif "proceeds from short term borrowings" in lab:
                code = "CF.FIN_ST_BORROW_PROC"
            elif "repayment of short term borrowings" in lab:
                code = "CF.FIN_ST_BORROW_REPAY"
            elif "proceeds from non-current borrowings" in lab or "proceeds from non current borrowings" in lab or "proceeds from long term borrowings" in lab:
                code = "CF.FIN_NC_BORROW_PROC"
            elif "repayment of non-current borrowing" in lab or "repayment of non current borrowings" in lab or "repayment of long term borrowings" in lab:
                code = "CF.FIN_NC_BORROW_REPAY"
            elif "dividends paid on equity" in lab or "dividend paid on equity" in lab:
                code = "CF.FIN_DIV_PAID"
            elif "tax paid on dividend" in lab:
                code = "CF.FIN_DIV_TAX_PAID"
            elif "interest paid" in lab:
                code = "CF.FIN_INTEREST_PAID"
            elif "payment of lease liabilities" in lab:
                code = "CF.FIN_LEASE_PRINCIPAL"
            elif "interest expense on lease liabilities" in lab:
                code = "CF.FIN_LEASE_INTEREST"
            elif "buyback of equity shares" in lab and "expenses" not in lab:
                code = "CF.FIN_BUYBACK"
            elif "expenses for buyback" in lab:
                code = "CF.FIN_BUYBACK_EXP"
            elif "change in equity" in lab:
                code = "CF.FIN_CHG_EQUITY"
            elif "change in nci" in lab or "change in non-controlling interests" in lab:
                code = "CF.FIN_CHG_NCI"
            elif "payment of other non current financial liability" in lab:
                code = "CF.FIN_OTHER_NC_FIN_LIAB"
            elif "capital grant" in lab:
                code = "CF.FIN_CAP_GRANT"
            elif "share issue expenses" in lab:
                code = "CF.FIN_SHARE_ISSUE_EXP"
            elif "financing activities" in lab and is_sub:
                code = "CF.CFF"
            elif "net increase" in lab and "cash and cash equivalents" in lab:
                code = "CF.NET_CHANGE_CCE"
            elif "beginning of the year" in lab or "beginning of the period" in lab:
                code = "CF.CCE_OPEN"
            elif "effect of exchange rate changes" in lab:
                code = "CF.FX_ON_CCE"
            elif ("end of the year" in lab or "end of year" in lab or "end of the period" in lab) and is_sub:
                if not seen_cce_close:
                    code = "CF.CCE_CLOSE"
                    seen_cce_close = True
                else:
                    code = "CF.CCE_CLOSE_RECON"
            elif "cash in hand" in lab or "cash on hand" in lab:
                code = "CF.CCE_CASH_ON_HAND"
            elif "balances with banks" in lab:
                code = "CF.CCE_BANK_BAL"
            elif "bank deposit with original maturity" in lab:
                code = "CF.CCE_SHORT_DEPOSITS"
            elif "cash and cash equivalents (note" in lab:
                code = "CF.CCE_NOTE_18"
            elif "bank overdraft" in lab or "cash credit" in lab:
                code = "CF.BANK_OVERDRAFT"
            elif "cash and cash equivalents in cash flows statement" in lab:
                code = "CF.CCE_IN_CF_STMT"
            elif lab == "[unlabelled line]" and is_sub:
                if "repeats line" in sub_comp:
                    code = "CF.CCE_CLOSE_REPEAT"
                else:
                    code = "CF.CCE_BEFORE_OD"
            else:
                code = f"UNMAPPED_CF:{sec}:{lab}"
            codes.append(code)
        return codes

    return [f"UNMAPPED:{stmt}" for _ in rows]


def map_ten_year_row(r: pd.Series) -> Tuple[str, str]:
    """Return `(statement, line_code)` for a row in `ten_year_raw.parquet`."""
    blk = _norm(r["block"])
    par = _norm(r["parent_label"])
    lab = _norm(r["raw_label"])
    vint = str(r["report_vintage"]).strip()

    # 1. Ratios
    if blk == "ratio":
        if "return on capital employed" in lab and "incl" in lab:
            return ("ratio", "RATIO.ROCE_INCL_EXC")
        if "return on capital employed" in lab:
            return ("ratio", "RATIO.ROCE")
        if "current ratio" in lab:
            return ("ratio", "RATIO.CURRENT")
        if "debt equity ratio" in lab:
            return ("ratio", "RATIO.DEBT_EQUITY")
        if "debtors turnover" in lab:
            return ("ratio", "RATIO.DEBTORS_TURNOVER_DAYS")
        if "dividend (%)" in lab:
            return ("ratio", "RATIO.DIVIDEND_PCT")
        if "dividend per share" in lab:
            return ("ratio", "RATIO.DPS")
        if "earning per share" in lab:
            return ("ratio", "RATIO.EPS")
        if "book value per share" in lab and "restated" in lab:
            return ("ratio", "RATIO.BVPS_RESTATED")
        if "book value per share" in lab:
            return ("ratio", "RATIO.BVPS")
        if "market value per share" in lab:
            return ("ratio", "RATIO.MVPS")
        if "net profit to equity" in lab:
            return ("ratio", "RATIO.ROE_INCL_EXC")
        if "pbdt to turnover" in lab:
            return ("ratio", "RATIO.PBDT_MARGIN_PCT")
        if "pbidt to turnover" in lab:
            return ("ratio", "RATIO.PBIDT_MARGIN_PCT")
        if "profit margin" in lab:
            return ("ratio", "RATIO.PAT_MARGIN_PCT")
        if "contribution to exchequer to turnover" in lab:
            return ("ratio", "RATIO.EXCHEQUER_TURNOVER_PCT")
        return ("ratio", f"UNMAPPED_RATIO:{lab}")

    # 2. Physical (Quantity Sold)
    if blk == "physical":
        if "crude oil" in lab:
            return ("physical", "QTY.CRUDE_SOLD")
        if "natural gas (bcm)" in lab:
            return ("physical", "QTY.GAS_SOLD")
        if "natural gas (mmm3)" in lab:
            return ("physical", "QTY.GAS_SOLD_MMM3")
        if "value added product" in lab:
            return ("physical", "QTY.VAP_SOLD")
        if "lpg" in lab:
            return ("physical", "QTY.LPG_SOLD")
        if "naphtha" in lab:
            return ("physical", "QTY.NAPHTHA_SOLD")
        if "ethane-propane" in lab:
            return ("physical", "QTY.C2C3_SOLD")
        return ("physical", f"UNMAPPED_PHYS:{lab}")

    # 3. Parent-context disambiguation
    if "research & development" in par:
        if lab == "capital":
            return ("other_info", "OTH.RD_CAPITAL")
        if lab == "revenue":
            return ("other_info", "OTH.RD_REVENUE")
    if "work in progress" in par:
        if "development wells" in lab:
            return ("balance_sheet", "BS.CWIP_DEV_WELLS")
        if "exploratory wells" in lab:
            return ("balance_sheet", "BS.IAUD_EXPL_WELLS")
        if "oil and gas facilities" in lab:
            return ("balance_sheet", "BS.CWIP_OG_FACILITIES")
        if lab == "others":
            return ("balance_sheet", "BS.WIP_OTHER_10YR")
    if "block capital" in par:
        if "oil and gas assets" in lab:
            return ("balance_sheet", "BS.OG_ASSETS")
        if "other property, plant" in lab:
            return ("balance_sheet", "BS.OTHER_PPE")
        if "right-of-use" in lab:
            return ("balance_sheet", "BS.ROU_ASSETS")
        if "intangible assets" in lab:
            return ("balance_sheet", "BS.INTANG_ASSETS")
    if "borrowings" in par:
        if "non current" in lab or "non-current" in lab:
            return ("balance_sheet", "BS.BORROW_NC")
        if "current" in lab:
            return ("balance_sheet", "BS.BORROW_CUR")
    if "investments" in par:
        if "non-current" in lab or "non current" in lab:
            return ("balance_sheet", "BS.INVESTMENTS_NC_10YR")
        if "current" in lab:
            return ("balance_sheet", "BS.INVESTMENTS_C")
    if "exploration costs" in par:
        if "survey" in lab:
            return ("pnl", "PL.EXPL_SURVEY")
        if "exploratory well" in lab:
            return ("pnl", "PL.EXPL_WELL")
    if "sale of product" in par:
        if "crude oil" in lab:
            return ("pnl", "REV.CRUDE")
        if "natural gas" in lab:
            return ("pnl", "REV.GAS")
        if "value added product" in lab:
            return ("pnl", "REV.VAP")
        if "traded products" in lab:
            return ("pnl", "REV.TRADED")
    if "statutory levies" in par:
        if "royalty" in lab:
            return ("pnl", "LEVY.ROYALTY")
        if "oidb cess" in lab:
            return ("pnl", "LEVY.OIDB_CESS")
        if "contingent duty" in lab:
            return ("pnl", "LEVY.NCCD")
        if "other levies" in lab:
            return ("pnl", "LEVY.OTHER_SAED")

    # 4. Top-level labels
    if lab in ("crude oil (including condensate)", "crude oil(including condensate)"):
        return ("pnl", "REV.CRUDE")
    if lab == "natural gas (incl. gas marketing margin)":
        return ("pnl", "REV.GAS")
    if "liquified petroleum gas" in lab:
        return ("pnl", "REV.LPG")
    if lab == "naphtha":
        return ("pnl", "REV.NAPHTHA")
    if "ethane-propane" in lab:
        return ("pnl", "REV.C2C3")
    if lab == "aviation turbine fuel":
        return ("pnl", "REV.ATF")
    if "lshs" in lab:
        return ("pnl", "REV.LSHS")
    if "kerosene" in lab:
        return ("pnl", "REV.SKO")
    if lab == "hsd":
        return ("pnl", "REV.HSD")
    if lab == "others":
        return ("pnl", "REV.OTHER_PRODUCTS")
    if lab == "sub- total":
        return ("pnl", "REV.OWN_PRODUCTS_SUBTOTAL")
    if lab == "sub-total":
        return ("pnl", "LEVY.TOTAL")
    if lab == "sale of traded products":
        return ("pnl", "REV.TRADED")
    if lab == "sale of product:":
        return ("pnl", "REV.SALE_OF_PRODUCT")
    if lab in ("other operating revenue", "other operating income"):
        return ("pnl", "REV.OTHER_OP")
    if lab == "revenue from operations":
        return ("pnl", "PL.REV_OPS")
    if lab == "dividend income":
        return ("pnl", "PL.DIVIDEND_INCOME_10YR")
    if lab in ("other non-operating income", "other non operating income"):
        return ("pnl", "PL.OTHER_NON_OP_INCOME_10YR")
    if lab in ("total income", "total revenues"):
        return ("pnl", "PL.TOTAL_INCOME")
    if lab in ("statutory levies", "statutory levies:"):
        return ("pnl", "LEVY.TOTAL")
    if lab == "royalty":
        return ("pnl", "LEVY.ROYALTY")
    if lab == "oidb cess":
        return ("pnl", "LEVY.OIDB_CESS")
    if "contingent duty" in lab:
        return ("pnl", "LEVY.NCCD")
    if lab == "excise duty":
        return ("pnl", "LEVY.EXCISE")
    if "sales tax" in lab:
        return ("pnl", "LEVY.SALES_TAX")
    if lab == "service tax":
        return ("pnl", "LEVY.SERVICE_TAX")
    if lab == "education cess":
        return ("pnl", "LEVY.EDU_CESS")
    if "octroi and port trust" in lab:
        return ("pnl", "LEVY.OCTROI_PORT")
    if lab == "motor spirit cess":
        return ("pnl", "LEVY.MS_CESS")
    if "road and infrastructure" in lab:
        return ("pnl", "LEVY.ROAD_INFRA_CESS")
    if lab == "operating expenses":
        return ("pnl", "PL.OPEX_10YR")
    if lab == "operating expenses ^":
        return ("pnl", "PL.OPEX_10YR_AGG")
    if lab == "purchases":
        return ("pnl", "PL.PURCHASES_TRADED")
    if "(accretion) / decretion in stock" in lab:
        return ("pnl", "PL.INVENTORY_CHANGE")
    if "exchange loss" in lab:
        return ("pnl", "PL.EXCHANGE_LOSS_10YR")
    if "exploration costs written" in lab:
        return ("pnl", "PL.EXPL_WRITEOFF")
    if lab == "other expenses^":
        return ("pnl", "PL.OTHER_EXP_10YR")
    if lab == "provisions and write-offs":
        return ("pnl", "PL.PROVISIONS_WRITEOFF")
    if lab == "prior period expenses (net)":
        return ("pnl", "PL.PRIOR_PERIOD_10YR")
    if lab == "total expenses":
        if "2025-26" in vint:
            return ("pnl", "PL.TOTAL_EXP_EX_DDA")
        return ("pnl", "PL.TOTAL_EXP_EX_FIN")
    if "profit before interest, depreciation & tax (pbidt)" in lab:
        return ("pnl", "PL.PBIDT")
    if "depreciation, depletion, amortisation and impairment" in lab:
        return ("pnl", "PL.DDA")
    if "profit before interest & tax (pbit)" in lab or "operating income before interest &tax" in lab:
        return ("pnl", "PL.PBIT")
    if lab in ("finance cost", "finance costs"):
        return ("pnl", "PL.FIN_COST")
    if lab == "profit before tax and exceptional items":
        return ("pnl", "PL.PBT_PRE_EXC")
    if "exceptional items" in lab:
        return ("pnl", "PL.EXCEPTIONAL")
    if lab in ("profit before tax", "profit before tax (pbt)"):
        return ("pnl", "PL.PBT")
    if lab in ("corporate tax", "corporate tax ( net)"):
        return ("pnl", "PL.TAX")
    if lab in ("profit after tax", "profit after tax (pat)", "net profit (pat)", "profit after tax for the year"):
        return ("pnl", "PL.PAT")
    if lab == "other comprehensive income (oci)":
        return ("pnl", "PL.OCI")
    if "other comprehensive income arising from" in lab:
        return ("soce", "SOCE.OCI_DBP_NET")
    if lab == "total comprehensive income for the year":
        return ("pnl", "PL.TCI")
    if lab == "dividend (declared for fy)":
        return ("other_info", "OTH.DIVIDEND_DECLARED")
    if lab == "dividend (paid in fy)" or lab == "dividend":
        return ("other_info", "OTH.DIVIDEND_PAID")
    if lab == "tax on dividend":
        return ("other_info", "OTH.DIVIDEND_TAX")
    if lab == "share capital":
        return ("balance_sheet", "BS.SHARE_CAPITAL")
    if lab == "other equity (reserve and surplus)":
        return ("balance_sheet", "BS.OTHER_EQUITY")
    if lab == "reserve & surplus":
        return ("balance_sheet", "BS.RESERVE_SURPLUS_10YR")
    if lab in ("total equity (net worth)", "net worth (equity)"):
        return ("balance_sheet", "BS.EQUITY.TOTAL")
    if lab in ("borrowings", "borrowings:"):
        return ("balance_sheet", "BS.BORROW_TOTAL_10YR")
    if lab == "current maturity of non-current borrowings":
        return ("balance_sheet", "BS.BORROW_CURR_MAT_10YR")
    if lab == "working capital":
        return ("balance_sheet", "BS.WORKING_CAPITAL_10YR")
    if lab == "capital employed":
        return ("other_info", "OTH.CAPITAL_EMPLOYED")
    if lab == "internal resources generation":
        return ("other_info", "OTH.INTERNAL_RESOURCES")
    if lab == "capex":
        return ("other_info", "CAPEX.TOTAL")
    if lab == "contribution to exchequer":
        return ("other_info", "OTH.EXCHEQUER")
    if lab == "expenditure on employees":
        return ("other_info", "OTH.EMP_EXPENDITURE")
    if lab == "number of employees":
        return ("other_info", "OTH.EMPLOYEES")
    if lab == "corporate social responsibility (csr)":
        return ("other_info", "OTH.CSR")
    if lab == "block capital:":
        return ("balance_sheet", "BS.BLOCK_CAPITAL_10YR")
    if lab == "work in progress:":
        return ("balance_sheet", "BS.WIP_TOTAL_10YR")
    if lab == "capital advance":
        return ("balance_sheet", "BS.CAP_ADVANCE_10YR")
    if lab == "investments:":
        return ("balance_sheet", "BS.INVESTMENTS_TOTAL_10YR")
    if lab == "cash and bank balances":
        return ("balance_sheet", "BS.CASH_BANK_10YR")
    if lab == "deposits under site restoration fund":
        return ("balance_sheet", "BS.SRF_DEPOSIT_NC")
    if lab == "trade receivable":
        return ("balance_sheet", "BS.TRADE_REC_C")
    if lab == "trade payable":
        return ("balance_sheet", "BS.TRADE_PAY_10YR")
    if lab == "lease liabilities":
        return ("balance_sheet", "BS.LEASE_LIAB_TOTAL_10YR")
    if lab == "deferred tax liabilities (net)":
        return ("balance_sheet", "BS.DTL_NET")
    if "retained earnings at beginning" in lab:
        return ("soce", "SOCE.RE_OPEN")
    if "effect of restatement" in lab:
        return ("soce", "SOCE.RE_RESTATEMENT")
    if "expenses relating to buyback" in lab:
        return ("soce", "SOCE.RE_BUYBACK_EXP")
    if "transfer to general reserve" in lab:
        return ("soce", "SOCE.RE_TRANSFER_GR")
    if "retained earnings at end" in lab:
        return ("soce", "SOCE.RE_CLOSE")
    return ("other_info", f"UNMAPPED_TY:{blk}:{par}:{lab}")


def map_note_row(r: pd.Series) -> Tuple[str, Optional[str]]:
    """Return `(statement, line_code)` for canonical note rows, or `(stmt, None)` for sub-schedule detail."""
    nk = _norm(r["note_key"])
    tbl = _norm(r["source_table"])
    cg = _norm(r["column_group"])
    lab = _norm(r["raw_label"])
    is_sub = bool(r["is_subtotal"])
    tie_ok = r["statement_tie_ok"]
    seq = int(r["line_seq"]) if not pd.isna(r.get("line_seq")) else 0
    cidx = int(r["column_index"]) if not pd.isna(r.get("column_index")) else 0
    chdr = str(r.get("column_header", "")).strip()

    # Skip Ind AS transition opening BS 3rd column ('2015' = April 1, 2015) tagged as FY16 in AR_FY2016-17
    if chdr == "2015":
        return ("balance_sheet", None)

    if nk == "production":
        if "crude oil" in lab and "[ongc]" in lab:
            return ("physical", "PROD.CRUDE_ONGC")
        if "crude oil" in lab and "[jv share]" in lab:
            return ("physical", "PROD.CRUDE_JV")
        if "natural gas" in lab and "[ongc]" in lab:
            return ("physical", "PROD.GAS_ONGC")
        if "natural gas" in lab and "[jv share]" in lab:
            return ("physical", "PROD.GAS_JV")
        return ("physical", None)

    if nk == "revenue" and tbl in ("note_30", "note_31"):
        if lab == "total" and is_sub and tie_ok is True:
            return ("pnl", "REV.TOTAL")
        return ("pnl", None)

    if nk == "other_income" and tbl in ("note_31", "note_32"):
        if lab == "total" and is_sub and tie_ok is True:
            return ("pnl", "N31.TOTAL")
        return ("pnl", None)

    if nk == "opex":
        if tbl in ("note_34", "note_35"):
            if "royalty" in lab:
                return ("pnl", "N35.ROYALTY")
            if "oidb cess" in lab:
                return ("pnl", "N35.OIDB_CESS")
            if "national calamity contingent duty" in lab:
                return ("pnl", "N35.NCCD")
            if "excise duty" in lab:
                return ("pnl", "N35.EXCISE")
            if "port trust" in lab:
                return ("pnl", "N35.PORT_TRUST")
            if "other levies" in lab:
                return ("pnl", "N35.OTHER_LEVIES")
            if "staff expenditure" in lab:
                return ("pnl", "N35.STAFF")
            if "workover operations" in lab:
                return ("pnl", "N35.WORKOVER")
            if "water injection" in lab:
                return ("pnl", "N35.WATER_INJECTION")
            if "consumption of raw materials" in lab:
                return ("pnl", "N35.CONSUMPTION")
            if "pollution control" in lab:
                return ("pnl", "N35.POLLUTION")
            if "transport expenditure" in lab:
                return ("pnl", "N35.TRANSPORT")
            if "insurance" in lab:
                return ("pnl", "N35.INSURANCE")
            if "power and fuel" in lab:
                return ("pnl", "N35.POWER_FUEL")
            if "repairs and maintenance" in lab:
                return ("pnl", "N35.REPAIRS")
            if "contractual payments" in lab:
                return ("pnl", "N35.CONTRACTUAL")
            if "other production expenditure" in lab:
                return ("pnl", "N35.OTHER_PROD")
            if "transportation and freight of products" in lab:
                return ("pnl", "N35.FREIGHT")
            if "research and development" in lab:
                return ("pnl", "N35.RD")
            if "general administrative expenditure" in lab:
                return ("pnl", "N35.GA")
            if "csr expenditure" in lab:
                return ("pnl", "N35.CSR")
            if "exchange loss" in lab:
                return ("pnl", "N35.FX_LOSS")
            if "miscellaneous expenditure" in lab:
                return ("pnl", "N35.MISC")
            if "loss on fair valuation" in lab:
                return ("pnl", "N35.FV_LOSS")
            if lab == "total" and is_sub:
                return ("pnl", "N35.TOTAL")
        elif tbl in ("note_34_1", "note_35_1"):
            if "sub total" in lab and is_sub:
                return ("pnl", "N351.EMP_TOTAL")
        return ("pnl", None)

    if nk == "finance_cost" and tbl in ("note_35", "note_36"):
        if "decommissioning provisions" in lab:
            return ("pnl", "N36.UNWIND_DECOM")
        if "lease liabilities" in lab:
            return ("pnl", "N36.UNWIND_LEASE")
        if lab == "total" and is_sub and tie_ok is True:
            return ("pnl", "N36.TOTAL")
        return ("pnl", None)

    if nk == "dda" and tbl in ("note_36", "note_37"):
        if "depletion of oil and gas assets" in lab:
            return ("pnl", "N37.DEPLETION")
        if "depreciation of right-of-use assets" in lab:
            return ("pnl", "N37.DEPR_ROU")
        if "amortisation of intangible assets" in lab:
            return ("pnl", "N37.AMORT")
        if "impairment loss" in lab and is_sub:
            return ("pnl", "N37.IMPAIR")
        if lab == "total" and is_sub and tie_ok is True:
            return ("pnl", "N37.TOTAL")
        return ("pnl", None)

    if nk == "lease" and tbl == "note_22_1":
        if "balance at beginning" in lab:
            return ("balance_sheet", "N22.OPENING")
        if "recognized during the year" in lab:
            return ("balance_sheet", "N22.RECOGNIZED")
        if "unwinding of discount" in lab:
            return ("balance_sheet", "N22.UNWIND")
        if "payment during the year" in lab:
            return ("balance_sheet", "N22.PAYMENT")
        if "balance at end of the year" in lab:
            return ("balance_sheet", "N22.CLOSING")
        return ("balance_sheet", None)

    if nk == "tax" and tbl in ("note_38", "note_39"):
        if lab in ("current year", "- current year"):
            return ("pnl", "NTAX.CURRENT_YR")
        if lab in ("earlier years", "- earlier years"):
            return ("pnl", "NTAX.EARLIER_YR")
        if lab == "[unlabelled line]" and is_sub:
            return ("pnl", "NTAX.CURRENT" if seq <= 4 else "NTAX.DEFERRED")
        if lab == "deferred tax":
            return ("pnl", "NTAX.DEFERRED")
        if ("total income tax expense" in lab or lab == "total") and is_sub:
            return ("pnl", "NTAX.TOTAL")
        return ("pnl", None)

    if nk == "provisions" and tbl in ("note_24_1", "note_25_1") and "decommissioning" in cg and cidx in (0, 1):
        if "balance at beginning" in lab:
            return ("balance_sheet", "NPROV.DECOM_OPEN")
        if "recognized during the year" in lab:
            return ("balance_sheet", "NPROV.DECOM_ADD")
        if "unwinding of discount" in lab:
            return ("balance_sheet", "NPROV.DECOM_UNWIND")
        if "balance at end of the year" in lab:
            return ("balance_sheet", "NPROV.DECOM_CLOSE")
        return ("balance_sheet", None)

    if nk == "segment":
        if tbl in ("note_43_2", "note_44_2", "note_44_2_1"):
            if "segment revenue" in cg:
                if lab == "offshore":
                    return ("pnl", "SEG.REV.OFF")
                if lab == "onshore":
                    return ("pnl", "SEG.REV.ON")
                if lab == "total" and is_sub:
                    return ("pnl", "SEG.REV.TOTAL")
            elif "segment profit" in cg:
                if lab == "offshore":
                    return ("pnl", "SEG.RES.OFF")
                if lab == "onshore":
                    return ("pnl", "SEG.RES.ON")
                if lab == "total" and is_sub:
                    return ("pnl", "SEG.RES.TOTAL")
                if "unallocated corporate" in lab:
                    return ("pnl", "SEG.UNALLOC")
                if "finance costs" in lab:
                    return ("pnl", "SEG.FIN_COST")
                if "interest/dividend" in lab:
                    return ("pnl", "SEG.INT_DIV")
                if "profit before tax" in lab:
                    return ("pnl", "SEG.PBT")
        elif tbl in ("note_43_3", "note_44_3"):
            if lab == "total assets" and is_sub:
                return ("balance_sheet", "SEG.ASSETS.TOTAL")
        elif tbl in ("note_43_4", "note_44_4"):
            if "amortization" in cg:
                if lab == "offshore":
                    return ("pnl", "SEG.DDA.OFF")
                if lab == "onshore":
                    return ("pnl", "SEG.DDA.ON")
            elif "impairment" in cg:
                if lab == "offshore":
                    return ("pnl", "SEG.IMPAIR.OFF")
                if lab == "onshore":
                    return ("pnl", "SEG.IMPAIR.ON")
            elif "write off" in cg:
                if lab == "offshore":
                    return ("pnl", "SEG.EXPL_WRITEOFF.OFF")
                if lab == "onshore":
                    return ("pnl", "SEG.EXPL_WRITEOFF.ON")
        return ("pnl", None)

    return ("pnl", None)


def map_xbrl_row(r: pd.Series) -> Optional[Tuple[str, str, str]]:
    """Return `(statement, period_type, line_code)` for an XBRL row, or `None` if unmapped/dimensional."""
    plc = _clean_text(r.get("proposed_line_code"))
    if not plc:
        return None
    ctx = str(r.get("context_ref", "")).strip()
    seg = _norm(r.get("segment_member"))
    ptype_raw = str(r.get("period_type", "annual")).strip()
    ptype = "annual" if ptype_raw == "instant" else ptype_raw

    if ctx in ("FourD", "OneD", "OneI"):
        if plc == "SEG.REV":
            lc = "SEG.REV.TOTAL" if str(r.get("scope")) == "standalone" else "SEG.REV"
        elif plc == "SEG.RES":
            lc = "SEG.RES.TOTAL" if str(r.get("scope")) == "standalone" else "SEG.RES"
        elif plc == "SEG.UNALLOC":
            # In XBRL Reg 33, Unallocable income/expense has opposite sign convention or includes interest in consolidated;
            # keep XBRL-specific code SEG.UNALLOC_XBRL so it does not falsely collide with AR Note 44 SEG.UNALLOC
            lc = "SEG.UNALLOC_XBRL"
        else:
            lc = plc
    elif "OperatingExpenses" in ctx:
        if "survey" in seg:
            lc = "PL.EXPL_SURVEY"
        elif "exploratory well" in seg:
            lc = "PL.EXPL_WELL"
        elif "statutory levies" in seg:
            lc = "LEVY.TOTAL"
        else:
            return None
    else:
        return None

    if lc.startswith("BS."):
        stmt = "balance_sheet"
    elif lc.startswith("CF."):
        stmt = "cash_flow"
    elif lc.startswith("OTH."):
        stmt = "other_info"
    else:
        stmt = "pnl"
    return (stmt, ptype, lc)


# Canonical metadata catalog for dim_financial_line.csv (SPEC-01 §5.2, SPEC-05 §5, BUG-39 clean display names)
CANONICAL_LINE_META: Dict[str, Dict[str, Any]] = {
    "PL.REV_OPS": {
        "line_name": "Revenue from Operations",
        "aliases": "Gross Revenue|Operating Revenue|Turnover|Sale of Products and Other Operating Revenue",
        "statement": "pnl", "section": "Income", "subsection": "Operating Revenue",
        "parent": "PL.TOTAL_INCOME", "level": 1, "order": 10, "line_class": "flow", "sign": "credit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Schedule III Part II Line I", "note": "Note 30",
        "xbrl": "RevenueFromOperations", "yahoo": "Total Revenue",
        "desc": "Gross revenue from operations (Crude Oil, Natural Gas, VAP, Traded Products, and Other Operating Revenue).",
    },
    "PL.OTHER_INCOME": {
        "line_name": "Other Income",
        "aliases": "Non-Operating Income|Interest and Dividend Income",
        "statement": "pnl", "section": "Income", "subsection": "Other Income",
        "parent": "PL.TOTAL_INCOME", "level": 1, "order": 20, "line_class": "flow", "sign": "credit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Schedule III Part II Line II", "note": "Note 31",
        "xbrl": "OtherIncome", "yahoo": "Other Income Expense",
        "desc": "Interest income, dividend income, excess provisions written back, and other non-operating income.",
    },
    "PL.TOTAL_INCOME": {
        "line_name": "Total Income",
        "aliases": "Total Revenues|Gross Total Income",
        "statement": "pnl", "section": "Income", "subsection": "Total Income",
        "parent": None, "level": 0, "order": 30, "line_class": "subtotal", "sign": "credit",
        "unit": "INR_cr", "is_sub": True, "is_tot": False, "is_kpi": True,
        "formula": "+PL.REV_OPS +PL.OTHER_INCOME",
        "ind_as": "Schedule III Part II Line III", "note": None,
        "xbrl": "Income", "yahoo": None,
        "desc": "Sum of Revenue from Operations and Other Income.",
    },
    "PL.COST_MATERIALS": {
        "line_name": "Cost of Materials Consumed",
        "aliases": "Raw Materials Consumed",
        "statement": "pnl", "section": "Expenses", "subsection": "Operating Expenses",
        "parent": "PL.TOTAL_EXP", "level": 1, "order": 40, "line_class": "flow", "sign": "debit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": False, "formula": None,
        "ind_as": "Schedule III Part II Line IV(a)", "note": "Note 32",
        "xbrl": "CostOfMaterialsConsumed", "yahoo": None,
        "desc": "Cost of raw materials consumed in refining/petrochemical/VAP operations.",
    },
    "PL.PURCHASES_TRADED": {
        "line_name": "Purchases of Stock-in-Trade",
        "aliases": "Purchases of Traded Goods|Purchases",
        "statement": "pnl", "section": "Expenses", "subsection": "Operating Expenses",
        "parent": "PL.TOTAL_EXP", "level": 1, "order": 50, "line_class": "flow", "sign": "debit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": False, "formula": None,
        "ind_as": "Schedule III Part II Line IV(b)", "note": None,
        "xbrl": "PurchasesOfStockInTrade", "yahoo": None,
        "desc": "Purchases of traded goods (including LNG trading).",
    },
    "PL.INVENTORY_CHANGE": {
        "line_name": "Changes in Inventories of Finished Goods, Stock-in-Trade and Work-in-Progress",
        "aliases": "(Accretion) / Decretion in Stock|Inventory Change",
        "statement": "pnl", "section": "Expenses", "subsection": "Operating Expenses",
        "parent": "PL.TOTAL_EXP", "level": 1, "order": 60, "line_class": "flow", "sign": "debit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": False, "formula": None,
        "ind_as": "Schedule III Part II Line IV(c)", "note": "Note 34",
        "xbrl": "ChangesInInventoriesOfFinishedGoodsWorkInProgressAndStockInTrade", "yahoo": None,
        "desc": "Net change in inventories of finished goods, work-in-progress, and stock-in-trade.",
    },
    "PL.PROD_EXP": {
        "line_name": "Production, Transportation, Selling and Distribution Expenditure",
        "aliases": "Production Expenditure|Operating and Statutory Expenditure",
        "statement": "pnl", "section": "Expenses", "subsection": "Operating Expenses",
        "parent": "PL.TOTAL_EXP", "level": 1, "order": 70, "line_class": "flow", "sign": "debit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Schedule III Part II Line IV", "note": "Note 35",
        "xbrl": None, "yahoo": "Cost Of Revenue",
        "desc": "Production, transportation, selling and distribution expenditure including statutory levies and staff expenditure.",
    },
    "PL.EMP_BENEFIT": {
        "line_name": "Employee Benefit Expense",
        "aliases": "Staff Cost|Employee Costs",
        "statement": "pnl", "section": "Expenses", "subsection": "Operating Expenses",
        "parent": "PL.TOTAL_EXP", "level": 1, "order": 75, "line_class": "flow", "sign": "debit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Schedule III Part II Line IV(d)", "note": "Note 35.1",
        "xbrl": "EmployeeBenefitExpense", "yahoo": None,
        "desc": "Employee benefit expense disclosed in BSE Regulation 33 XBRL / Note 35.1.",
    },
    "PL.EXPL_SURVEY": {
        "line_name": "Exploration Costs Written Off — Survey Costs",
        "aliases": "Survey Costs|Seismic Survey Expenditure",
        "statement": "pnl", "section": "Expenses", "subsection": "Exploration Costs Written Off",
        "parent": "PL.TOTAL_EXP", "level": 1, "order": 80, "line_class": "flow", "sign": "debit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Schedule III Part II Line IV", "note": None,
        "xbrl": "OtherExpenses[SurveyCosts]", "yahoo": None,
        "desc": "Geological, geophysical and seismic survey costs expensed during the year.",
    },
    "PL.EXPL_WELL": {
        "line_name": "Exploration Costs Written Off — Exploratory Well Costs",
        "aliases": "Dry Well Write-Off|Exploratory Well Costs Written Off",
        "statement": "pnl", "section": "Expenses", "subsection": "Exploration Costs Written Off",
        "parent": "PL.TOTAL_EXP", "level": 1, "order": 90, "line_class": "flow", "sign": "debit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Schedule III Part II Line IV", "note": None,
        "xbrl": "OtherExpenses[ExploratoryWellCosts]", "yahoo": None,
        "desc": "Dry/unsuccessful exploratory well drilling costs written off during the year.",
    },
    "PL.FIN_COST": {
        "line_name": "Finance Costs",
        "aliases": "Interest Expense|Finance Cost",
        "statement": "pnl", "section": "Expenses", "subsection": "Finance & Depreciation",
        "parent": "PL.TOTAL_EXP", "level": 1, "order": 100, "line_class": "flow", "sign": "debit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Schedule III Part II Line IV(e)", "note": "Note 36",
        "xbrl": "FinanceCosts", "yahoo": "Interest Expense",
        "desc": "Interest on borrowings, unwinding of decommissioning and lease liabilities, and exchange differences.",
    },
    "PL.DDA": {
        "line_name": "Depreciation, Depletion, Amortisation and Impairment",
        "aliases": "DD&A|Depreciation and Depletion",
        "statement": "pnl", "section": "Expenses", "subsection": "Finance & Depreciation",
        "parent": "PL.TOTAL_EXP", "level": 1, "order": 110, "line_class": "flow", "sign": "debit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Schedule III Part II Line IV(f)", "note": "Note 37",
        "xbrl": "DepreciationDepletionAndAmortisationExpense", "yahoo": "Reconciled Depreciation",
        "desc": "Depletion of oil & gas assets, depreciation of PPE and ROU assets, amortisation, and impairment.",
    },
    "PL.PROVISIONS_WRITEOFF": {
        "line_name": "Other Impairment and Write-Offs",
        "aliases": "Provisions and Write-Offs",
        "statement": "pnl", "section": "Expenses", "subsection": "Operating Expenses",
        "parent": "PL.TOTAL_EXP", "level": 1, "order": 120, "line_class": "flow", "sign": "debit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": False, "formula": None,
        "ind_as": "Schedule III Part II Line IV(g)", "note": "Note 38",
        "xbrl": None, "yahoo": None,
        "desc": "Other impairment provisions and write-offs.",
    },
    "PL.OTHER_EXP": {
        "line_name": "Other Expenses (XBRL Regulation 33)",
        "aliases": "Other Operating Expenses",
        "statement": "pnl", "section": "Expenses", "subsection": "Operating Expenses",
        "parent": "PL.TOTAL_EXP", "level": 1, "order": 125, "line_class": "flow", "sign": "debit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": False, "formula": None,
        "ind_as": "Schedule III Part II Line IV(g)", "note": None,
        "xbrl": "OtherExpenses", "yahoo": "Operating Expense",
        "desc": "Aggregate Other Expenses as reported in BSE Regulation 33 XBRL filings.",
    },
    "PL.TOTAL_EXP": {
        "line_name": "Total Expenses",
        "aliases": "Total Expenditure",
        "statement": "pnl", "section": "Expenses", "subsection": "Total Expenses",
        "parent": None, "level": 0, "order": 130, "line_class": "subtotal", "sign": "debit",
        "unit": "INR_cr", "is_sub": True, "is_tot": False, "is_kpi": True,
        "formula": "+PL.COST_MATERIALS +PL.PURCHASES_TRADED +PL.INVENTORY_CHANGE +PL.PROD_EXP +PL.EXPL_SURVEY +PL.EXPL_WELL +PL.FIN_COST +PL.DDA +PL.PROVISIONS_WRITEOFF",
        "ind_as": "Schedule III Part II Line IV", "note": None,
        "xbrl": "Expenses", "yahoo": "Total Expenses",
        "desc": "Total expenses on the face of the Statement of Profit and Loss.",
    },
    "PL.PBT_PRE_EXC": {
        "line_name": "Profit Before Exceptional Items and Tax",
        "aliases": "Profit Before Tax and Exceptional Items",
        "statement": "pnl", "section": "Profit", "subsection": "Pre-Tax Profit",
        "parent": "PL.PBT", "level": 0, "order": 140, "line_class": "subtotal", "sign": "credit",
        "unit": "INR_cr", "is_sub": True, "is_tot": False, "is_kpi": True,
        "formula": "+PL.TOTAL_INCOME -PL.TOTAL_EXP",
        "ind_as": "Schedule III Part II Line V", "note": None,
        "xbrl": "ProfitBeforeExceptionalItemsAndTax", "yahoo": None,
        "desc": "Profit before exceptional items and tax (Total Income minus Total Expenses).",
    },
    "PL.EXCEPTIONAL": {
        "line_name": "Exceptional Items",
        "aliases": "Exceptional Income / (Expense)",
        "statement": "pnl", "section": "Profit", "subsection": "Pre-Tax Profit",
        "parent": "PL.PBT", "level": 1, "order": 150, "line_class": "flow", "sign": "credit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Schedule III Part II Line VI", "note": "Note 48",
        "xbrl": "ExceptionalItemsBeforeTax", "yahoo": None,
        "desc": "Exceptional impairment/reversals or one-off items before tax.",
    },
    "PL.PBT": {
        "line_name": "Profit Before Tax",
        "aliases": "PBT|Earnings Before Tax",
        "statement": "pnl", "section": "Profit", "subsection": "Pre-Tax Profit",
        "parent": "PL.PAT", "level": 0, "order": 160, "line_class": "subtotal", "sign": "credit",
        "unit": "INR_cr", "is_sub": True, "is_tot": False, "is_kpi": True,
        "formula": "+PL.PBT_PRE_EXC +PL.EXCEPTIONAL",
        "ind_as": "Schedule III Part II Line VII", "note": None,
        "xbrl": "ProfitBeforeTax", "yahoo": "Pretax Income",
        "desc": "Profit before tax (PBT).",
    },
    "PL.TAX_CURRENT": {
        "line_name": "Current Tax",
        "aliases": "Current Tax — Current Year",
        "statement": "pnl", "section": "Tax", "subsection": "Tax Expense",
        "parent": "PL.TAX", "level": 1, "order": 170, "line_class": "flow", "sign": "debit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": False, "formula": None,
        "ind_as": "Schedule III Part II Line VIII(1)", "note": "Note 38",
        "xbrl": "CurrentTax", "yahoo": None,
        "desc": "Current income tax expense.",
    },
    "PL.TAX_EARLIER": {
        "line_name": "Current Tax Relating to Earlier Years",
        "aliases": "Earlier Years Tax Adjustment",
        "statement": "pnl", "section": "Tax", "subsection": "Tax Expense",
        "parent": "PL.TAX", "level": 1, "order": 175, "line_class": "flow", "sign": "debit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": False, "formula": None,
        "ind_as": "Schedule III Part II Line VIII(1)", "note": "Note 38",
        "xbrl": None, "yahoo": None,
        "desc": "Current tax adjustments relating to earlier years.",
    },
    "PL.TAX_DEFERRED": {
        "line_name": "Deferred Tax",
        "aliases": "Deferred Tax Expense / (Credit)",
        "statement": "pnl", "section": "Tax", "subsection": "Tax Expense",
        "parent": "PL.TAX", "level": 1, "order": 180, "line_class": "flow", "sign": "debit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": False, "formula": None,
        "ind_as": "Schedule III Part II Line VIII(2)", "note": "Note 38",
        "xbrl": "DeferredTax", "yahoo": None,
        "desc": "Deferred income tax charge or credit.",
    },
    "PL.TAX": {
        "line_name": "Total Tax Expense",
        "aliases": "Corporate Tax|Income Tax Expense",
        "statement": "pnl", "section": "Tax", "subsection": "Tax Expense",
        "parent": "PL.PAT", "level": 0, "order": 190, "line_class": "subtotal", "sign": "debit",
        "unit": "INR_cr", "is_sub": True, "is_tot": False, "is_kpi": True,
        "formula": "+PL.TAX_CURRENT +PL.TAX_EARLIER +PL.TAX_DEFERRED",
        "ind_as": "Schedule III Part II Line VIII", "note": "Note 38",
        "xbrl": "TaxExpense", "yahoo": "Tax Provision",
        "desc": "Total income tax expense (current tax + earlier years + deferred tax).",
    },
    "PL.PAT": {
        "line_name": "Profit After Tax",
        "aliases": "Net Profit|Profit for the Year|PAT",
        "statement": "pnl", "section": "Profit", "subsection": "Net Profit",
        "parent": None, "level": 0, "order": 200, "line_class": "total", "sign": "credit",
        "unit": "INR_cr", "is_sub": True, "is_tot": True, "is_kpi": True,
        "formula": "+PL.PBT -PL.TAX",
        "ind_as": "Schedule III Part II Line IX", "note": None,
        "xbrl": "ProfitLossForPeriod", "yahoo": "Net Income",
        "desc": "Profit for the year after tax (PAT).",
    },
    "PL.OCI": {
        "line_name": "Total Other Comprehensive Income",
        "aliases": "Other Comprehensive Income (OCI)",
        "statement": "pnl", "section": "OCI", "subsection": "Total OCI",
        "parent": "PL.TCI", "level": 0, "order": 220, "line_class": "subtotal", "sign": "credit",
        "unit": "INR_cr", "is_sub": True, "is_tot": False, "is_kpi": False, "formula": None,
        "ind_as": "Schedule III Part II Line XIV", "note": None,
        "xbrl": "OtherComprehensiveIncomeNetOfTaxes", "yahoo": None,
        "desc": "Other comprehensive income for the year, net of income tax.",
    },
    "PL.TCI": {
        "line_name": "Total Comprehensive Income for the Year",
        "aliases": "Total Comprehensive Income",
        "statement": "pnl", "section": "OCI", "subsection": "Total Comprehensive Income",
        "parent": None, "level": 0, "order": 230, "line_class": "total", "sign": "credit",
        "unit": "INR_cr", "is_sub": True, "is_tot": True, "is_kpi": False,
        "formula": "+PL.PAT +PL.OCI",
        "ind_as": "Schedule III Part II Line XV", "note": None,
        "xbrl": "TotalComprehensiveIncome", "yahoo": None,
        "desc": "Total comprehensive income for the year (PAT + OCI).",
    },
    "PL.PAT_OWNERS": {
        "line_name": "Profit Attributable to Owners of the Company",
        "aliases": "Net Profit — Owners Share",
        "statement": "pnl", "section": "Profit", "subsection": "Attribution",
        "parent": "PL.PAT", "level": 1, "order": 232, "line_class": "flow", "sign": "credit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Schedule III Part II", "note": None,
        "xbrl": "ProfitOrLossAttributableToOwnersOfParent", "yahoo": "Net Income Common Stockholders",
        "desc": "Consolidated profit for the year attributable to owners of ONGC.",
    },
    "PL.PAT_NCI": {
        "line_name": "Profit Attributable to Non-Controlling Interests",
        "aliases": "Minority Interest Profit",
        "statement": "pnl", "section": "Profit", "subsection": "Attribution",
        "parent": "PL.PAT", "level": 1, "order": 234, "line_class": "flow", "sign": "credit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": False, "formula": None,
        "ind_as": "Schedule III Part II", "note": None,
        "xbrl": "ProfitOrLossAttributableToNonControllingInterests", "yahoo": "Minority Interests",
        "desc": "Consolidated profit for the year attributable to non-controlling interests.",
    },
    "PL.EPS_BASIC": {
        "line_name": "Basic Earnings Per Equity Share",
        "aliases": "Basic EPS",
        "statement": "pnl", "section": "Per Share", "subsection": "EPS",
        "parent": None, "level": 1, "order": 240, "line_class": "per_share", "sign": "credit",
        "unit": "INR", "is_sub": False, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Schedule III Part II Line XVI(1)", "note": "Note 40",
        "xbrl": "BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations", "yahoo": "Basic EPS",
        "desc": "Basic earnings per equity share (face value ₹5 each).",
    },
    "PL.EPS_DILUTED": {
        "line_name": "Diluted Earnings Per Equity Share",
        "aliases": "Diluted EPS",
        "statement": "pnl", "section": "Per Share", "subsection": "EPS",
        "parent": None, "level": 1, "order": 245, "line_class": "per_share", "sign": "credit",
        "unit": "INR", "is_sub": False, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Schedule III Part II Line XVI(2)", "note": "Note 40",
        "xbrl": "DilutedEarningsLossPerShareFromContinuingAndDiscontinuedOperations", "yahoo": "Diluted EPS",
        "desc": "Diluted earnings per equity share (face value ₹5 each).",
    },
    "BS.ASSETS.NON_CURRENT.TOTAL": {
        "line_name": "Total Non-Current Assets",
        "aliases": "Non-Current Assets Total",
        "statement": "balance_sheet", "section": "Assets", "subsection": "Non-Current Assets",
        "parent": "BS.TOTAL_ASSETS", "level": 0, "order": 300, "line_class": "subtotal", "sign": "debit",
        "unit": "INR_cr", "is_sub": True, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Schedule III Part I Assets (1)", "note": None,
        "xbrl": "NoncurrentAssets", "yahoo": "Total Non Current Assets",
        "desc": "Total non-current assets on the Balance Sheet.",
    },
    "BS.CCE": {
        "line_name": "Cash and Cash Equivalents",
        "aliases": "Cash & Cash Equivalents",
        "statement": "balance_sheet", "section": "Assets", "subsection": "Current Assets",
        "parent": "BS.ASSETS.CURRENT.TOTAL", "level": 1, "order": 310, "line_class": "stock", "sign": "debit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Schedule III Part I Assets (2)(b)(ii)", "note": "Note 17",
        "xbrl": "CashAndCashEquivalents", "yahoo": "Cash And Cash Equivalents",
        "desc": "Cash on hand, balances with banks, and short-term deposits with maturity <= 3 months.",
    },
    "BS.ASSETS.CURRENT.TOTAL": {
        "line_name": "Total Current Assets",
        "aliases": "Current Assets Total",
        "statement": "balance_sheet", "section": "Assets", "subsection": "Current Assets",
        "parent": "BS.TOTAL_ASSETS", "level": 0, "order": 320, "line_class": "subtotal", "sign": "debit",
        "unit": "INR_cr", "is_sub": True, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Schedule III Part I Assets (2)", "note": None,
        "xbrl": "CurrentAssets", "yahoo": "Current Assets",
        "desc": "Total current assets on the Balance Sheet.",
    },
    "BS.TOTAL_ASSETS": {
        "line_name": "Total Assets",
        "aliases": "Balance Sheet Total Assets",
        "statement": "balance_sheet", "section": "Assets", "subsection": "Total Assets",
        "parent": None, "level": 0, "order": 330, "line_class": "total", "sign": "debit",
        "unit": "INR_cr", "is_sub": True, "is_tot": True, "is_kpi": True,
        "formula": "+BS.ASSETS.NON_CURRENT.TOTAL +BS.ASSETS.CURRENT.TOTAL",
        "ind_as": "Schedule III Part I Total Assets", "note": None,
        "xbrl": "Assets", "yahoo": "Total Assets",
        "desc": "Total assets (Non-Current Assets + Current Assets).",
    },
    "BS.SHARE_CAPITAL": {
        "line_name": "Equity Share Capital",
        "aliases": "Paid-up Equity Share Capital|Share Capital",
        "statement": "balance_sheet", "section": "Equity and Liabilities", "subsection": "Equity",
        "parent": "BS.EQUITY.TOTAL", "level": 1, "order": 340, "line_class": "stock", "sign": "credit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Schedule III Part I Equity (a)", "note": "Note 19",
        "xbrl": "EquityShareCapital", "yahoo": "Common Stock",
        "desc": "Issued, subscribed, and paid-up equity share capital.",
    },
    "BS.OTHER_EQUITY": {
        "line_name": "Other Equity",
        "aliases": "Reserves and Surplus",
        "statement": "balance_sheet", "section": "Equity and Liabilities", "subsection": "Equity",
        "parent": "BS.EQUITY.TOTAL", "level": 1, "order": 345, "line_class": "stock", "sign": "credit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Schedule III Part I Equity (b)", "note": "Note 20",
        "xbrl": "OtherEquity", "yahoo": "Retained Earnings",
        "desc": "Reserves and surplus, retained earnings, and other comprehensive income reserves.",
    },
    "BS.EQUITY.TOTAL": {
        "line_name": "Total Equity",
        "aliases": "Net Worth|Total Shareholders Equity",
        "statement": "balance_sheet", "section": "Equity and Liabilities", "subsection": "Equity",
        "parent": "BS.TOTAL_EQ_LIAB", "level": 0, "order": 350, "line_class": "subtotal", "sign": "credit",
        "unit": "INR_cr", "is_sub": True, "is_tot": False, "is_kpi": True,
        "formula": "+BS.SHARE_CAPITAL +BS.OTHER_EQUITY",
        "ind_as": "Schedule III Part I Equity", "note": None,
        "xbrl": "Equity", "yahoo": "Stockholders Equity",
        "desc": "Total equity (Net Worth).",
    },
    "BS.BORROW_NC": {
        "line_name": "Non-Current Borrowings",
        "aliases": "Long-Term Borrowings|Long-Term Debt",
        "statement": "balance_sheet", "section": "Equity and Liabilities", "subsection": "Non-Current Liabilities",
        "parent": "BS.LIAB.NON_CURRENT.TOTAL", "level": 1, "order": 360, "line_class": "stock", "sign": "credit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Schedule III Part I Liabilities (1)(a)(i)", "note": "Note 21",
        "xbrl": "BorrowingsNoncurrent", "yahoo": "Long Term Debt",
        "desc": "Non-current financial borrowings.",
    },
    "BS.LEASE_LIAB_NC": {
        "line_name": "Non-Current Lease Liabilities",
        "aliases": "Long-Term Lease Liabilities",
        "statement": "balance_sheet", "section": "Equity and Liabilities", "subsection": "Non-Current Liabilities",
        "parent": "BS.LIAB.NON_CURRENT.TOTAL", "level": 1, "order": 362, "line_class": "stock", "sign": "credit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": False, "formula": None,
        "ind_as": "Schedule III Part I Liabilities (1)(a)(ia)", "note": "Note 22",
        "xbrl": "LeaseLiabilitiesNoncurrent", "yahoo": None,
        "desc": "Non-current lease liabilities under Ind AS 116.",
    },
    "BS.LIAB.NON_CURRENT.TOTAL": {
        "line_name": "Total Non-Current Liabilities",
        "aliases": "Non-Current Liabilities Total",
        "statement": "balance_sheet", "section": "Equity and Liabilities", "subsection": "Non-Current Liabilities",
        "parent": "BS.LIAB.TOTAL", "level": 0, "order": 370, "line_class": "subtotal", "sign": "credit",
        "unit": "INR_cr", "is_sub": True, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Schedule III Part I Liabilities (1)", "note": None,
        "xbrl": "NoncurrentLiabilities", "yahoo": "Total Non Current Liabilities Net Minority Interest",
        "desc": "Total non-current liabilities.",
    },
    "BS.BORROW_CUR": {
        "line_name": "Current Borrowings",
        "aliases": "Short-Term Borrowings|Short-Term Debt",
        "statement": "balance_sheet", "section": "Equity and Liabilities", "subsection": "Current Liabilities",
        "parent": "BS.LIAB.CURRENT.TOTAL", "level": 1, "order": 375, "line_class": "stock", "sign": "credit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Schedule III Part I Liabilities (2)(a)(i)", "note": "Note 21",
        "xbrl": "BorrowingsCurrent", "yahoo": "Current Debt",
        "desc": "Current financial borrowings.",
    },
    "BS.LEASE_LIAB_C": {
        "line_name": "Current Lease Liabilities",
        "aliases": "Short-Term Lease Liabilities",
        "statement": "balance_sheet", "section": "Equity and Liabilities", "subsection": "Current Liabilities",
        "parent": "BS.LIAB.CURRENT.TOTAL", "level": 1, "order": 377, "line_class": "stock", "sign": "credit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": False, "formula": None,
        "ind_as": "Schedule III Part I Liabilities (2)(a)(ia)", "note": "Note 22",
        "xbrl": "LeaseLiabilitiesCurrent", "yahoo": None,
        "desc": "Current lease liabilities under Ind AS 116.",
    },
    "BS.LIAB.CURRENT.TOTAL": {
        "line_name": "Total Current Liabilities",
        "aliases": "Current Liabilities Total",
        "statement": "balance_sheet", "section": "Equity and Liabilities", "subsection": "Current Liabilities",
        "parent": "BS.LIAB.TOTAL", "level": 0, "order": 380, "line_class": "subtotal", "sign": "credit",
        "unit": "INR_cr", "is_sub": True, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Schedule III Part I Liabilities (2)", "note": None,
        "xbrl": "CurrentLiabilities", "yahoo": "Current Liabilities",
        "desc": "Total current liabilities.",
    },
    "BS.LIAB.TOTAL": {
        "line_name": "Total Liabilities",
        "aliases": "Total Non-Current and Current Liabilities",
        "statement": "balance_sheet", "section": "Equity and Liabilities", "subsection": "Total Liabilities",
        "parent": "BS.TOTAL_EQ_LIAB", "level": 0, "order": 390, "line_class": "subtotal", "sign": "credit",
        "unit": "INR_cr", "is_sub": True, "is_tot": False, "is_kpi": True,
        "formula": "+BS.LIAB.NON_CURRENT.TOTAL +BS.LIAB.CURRENT.TOTAL",
        "ind_as": "Schedule III Part I Total Liabilities", "note": None,
        "xbrl": "Liabilities", "yahoo": "Total Liabilities Net Minority Interest",
        "desc": "Total liabilities (Non-Current Liabilities + Current Liabilities).",
    },
    "BS.TOTAL_EQ_LIAB": {
        "line_name": "Total Equity and Liabilities",
        "aliases": "Balance Sheet Total Equity and Liabilities",
        "statement": "balance_sheet", "section": "Equity and Liabilities", "subsection": "Total Equity and Liabilities",
        "parent": None, "level": 0, "order": 400, "line_class": "total", "sign": "credit",
        "unit": "INR_cr", "is_sub": True, "is_tot": True, "is_kpi": True,
        "formula": "+BS.EQUITY.TOTAL +BS.LIAB.TOTAL",
        "ind_as": "Schedule III Part I Total Equity and Liabilities", "note": None,
        "xbrl": "EquityAndLiabilities", "yahoo": None,
        "desc": "Total equity and liabilities (ties to Total Assets).",
    },
    "CF.CFO": {
        "line_name": "Net Cash Generated by Operating Activities",
        "aliases": "Cash Flow from Operating Activities|Operating Cash Flow|CFO",
        "statement": "cash_flow", "section": "Operating Activities", "subsection": "Net Cash from Operations",
        "parent": "CF.NET_CHANGE_CCE", "level": 0, "order": 500, "line_class": "subtotal", "sign": "debit",
        "unit": "INR_cr", "is_sub": True, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Ind AS 7 Operating Activities", "note": None,
        "xbrl": "CashFlowsFromUsedInOperatingActivities", "yahoo": "Operating Cash Flow",
        "desc": "Net cash generated from operating activities (after direct taxes paid).",
    },
    "CF.CFI": {
        "line_name": "Net Cash Used in Investing Activities",
        "aliases": "Cash Flow from Investing Activities|CFI",
        "statement": "cash_flow", "section": "Investing Activities", "subsection": "Net Cash from Investing",
        "parent": "CF.NET_CHANGE_CCE", "level": 0, "order": 510, "line_class": "subtotal", "sign": "debit",
        "unit": "INR_cr", "is_sub": True, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Ind AS 7 Investing Activities", "note": None,
        "xbrl": "CashFlowsFromUsedInInvestingActivities", "yahoo": "Investing Cash Flow",
        "desc": "Net cash used in investing activities.",
    },
    "CF.CFF": {
        "line_name": "Net Cash Used in Financing Activities",
        "aliases": "Cash Flow from Financing Activities|CFF",
        "statement": "cash_flow", "section": "Financing Activities", "subsection": "Net Cash from Financing",
        "parent": "CF.NET_CHANGE_CCE", "level": 0, "order": 520, "line_class": "subtotal", "sign": "debit",
        "unit": "INR_cr", "is_sub": True, "is_tot": False, "is_kpi": True, "formula": None,
        "ind_as": "Ind AS 7 Financing Activities", "note": None,
        "xbrl": "CashFlowsFromUsedInFinancingActivities", "yahoo": "Financing Cash Flow",
        "desc": "Net cash generated from / (used in) financing activities.",
    },
    "CF.NET_CHANGE_CCE": {
        "line_name": "Net Increase / (Decrease) in Cash and Cash Equivalents",
        "aliases": "Net Change in Cash and Cash Equivalents",
        "statement": "cash_flow", "section": "Cash Reconciliation", "subsection": "Net Change",
        "parent": "CF.CCE_CLOSE", "level": 0, "order": 530, "line_class": "subtotal", "sign": "debit",
        "unit": "INR_cr", "is_sub": True, "is_tot": False, "is_kpi": True,
        "formula": "+CF.CFO +CF.CFI +CF.CFF",
        "ind_as": "Ind AS 7", "note": None,
        "xbrl": "IncreaseDecreaseInCashAndCashEquivalents", "yahoo": "Changes In Cash",
        "desc": "Net change in cash and cash equivalents (CFO + CFI + CFF).",
    },
    "CF.CCE_OPEN": {
        "line_name": "Cash and Cash Equivalents at the Beginning of the Year",
        "aliases": "Opening Cash and Cash Equivalents",
        "statement": "cash_flow", "section": "Cash Reconciliation", "subsection": "Opening Balance",
        "parent": "CF.CCE_CLOSE", "level": 1, "order": 540, "line_class": "stock", "sign": "debit",
        "unit": "INR_cr", "is_sub": False, "is_tot": False, "is_kpi": False, "formula": None,
        "ind_as": "Ind AS 7", "note": "Note 17",
        "xbrl": "CashAndCashEquivalentsCashFlowStatement[Open]", "yahoo": "Beginning Cash Position",
        "desc": "Cash and cash equivalents as at the beginning of the year.",
    },
    "CF.CCE_CLOSE": {
        "line_name": "Cash and Cash Equivalents at the End of the Year",
        "aliases": "Closing Cash and Cash Equivalents",
        "statement": "cash_flow", "section": "Cash Reconciliation", "subsection": "Closing Balance",
        "parent": None, "level": 0, "order": 550, "line_class": "total", "sign": "debit",
        "unit": "INR_cr", "is_sub": True, "is_tot": True, "is_kpi": True,
        "formula": "+CF.CCE_OPEN +CF.NET_CHANGE_CCE +CF.FX_ON_CCE",
        "ind_as": "Ind AS 7", "note": "Note 17",
        "xbrl": "CashAndCashEquivalentsCashFlowStatement", "yahoo": "End Cash Position",
        "desc": "Cash and cash equivalents as at the end of the year (ties to BS.CCE or net of bank overdraft).",
    },
}


def _humanize_code(line_code: str, sample_label: Optional[str] = None) -> str:
    """Produce a clean human-readable display name without artificial prefixes (BUG-39)."""
    if line_code in CANONICAL_LINE_META:
        return CANONICAL_LINE_META[line_code]["line_name"]
    if sample_label:
        s = str(sample_label).strip()
        s = re.sub(r"^\[subtotal\]\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"^[-•]+\s*", "", s)
        s = re.sub(r"^\([a-z0-9]+\)\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s+", " ", s).strip(" :")
        if s and s.lower() not in ("[unlabelled line]", "total", "sub-total", "sub- total", "sub total"):
            return s[0].upper() + s[1:]
    # Fallback: humanize suffix after prefix dot
    parts = line_code.split(".")
    tail = " ".join(parts[1:]) if len(parts) > 1 else line_code
    tail = tail.replace("_", " ").title()
    prefix_map = {
        "PL": "P&L",
        "BS": "Balance Sheet",
        "CF": "Cash Flow",
        "REV": "Revenue —",
        "LEVY": "Statutory Levy —",
        "QTY": "Sales Volume —",
        "PROD": "Production Volume —",
        "RATIO": "Financial Ratio —",
        "OTH": "Key Metric —",
        "CAPEX": "Capital Expenditure —",
        "N35": "Note 35 Opex —",
        "N351": "Note 35.1 Employee Benefit —",
        "N36": "Note 36 Finance Cost —",
        "N37": "Note 37 DD&A —",
        "N22": "Note 22 Lease Liability —",
        "NTAX": "Note 38 Tax —",
        "NPROV": "Note 24 Decommissioning Provision —",
        "SEG": "Segment —",
        "SOCE": "Retained Earnings —",
    }
    pref = prefix_map.get(parts[0], "")
    return f"{pref} {tail}".strip()


def build_dim_financial_line(gold_df: pd.DataFrame) -> pd.DataFrame:
    """Construct `dim_financial_line` with all SPEC-01 §5.2 columns for all canonical and observed codes."""
    all_codes = sorted(set(gold_df["line_code"].dropna().unique()).union(CANONICAL_LINE_META.keys()))
    rows: List[Dict[str, Any]] = []

    consolidated_only_codes = {
        "PL.PAT_OWNERS",
        "PL.PAT_NCI",
        "PL.OCI_OWNERS",
        "PL.OCI_NCI",
        "PL.TCI_OWNERS",
        "PL.TCI_NCI",
        "PL.PAT_ATTR_TOTAL",
        "PL.OCI_ATTR_TOTAL",
        "PL.TCI_ATTR_TOTAL",
        "PL.SHARE_ASSOC",
        "PL.SHARE_JV",
        "PL.SHARE_ASSOC_JV",
        "BS.EQUITY_OWNERS",
        "BS.NCI",
        "BS.GOODWILL",
    }

    for idx, lc in enumerate(all_codes, start=1):
        sub_df = gold_df[gold_df["line_code"] == lc]
        meta = CANONICAL_LINE_META.get(lc, {})

        sample_label = None
        ar_labels_list: List[str] = []
        ten_year_lbl: Optional[str] = None
        valid_from_fy: Optional[str] = None
        valid_to_fy: Optional[str] = None
        observed_scopes: set[str] = set()

        if not sub_df.empty:
            non_unlabelled = sub_df[~sub_df["line_name_as_reported"].astype(str).str.contains("unlabelled|subtotal", case=False, na=True)]
            if not non_unlabelled.empty:
                sample_label = str(non_unlabelled.iloc[-1]["line_name_as_reported"])
            else:
                sample_label = str(sub_df.iloc[-1]["line_name_as_reported"])

            ar_sub = sub_df[sub_df["source_system"] == "ar"]
            if not ar_sub.empty:
                seen_lbls = []
                for lbl in ar_sub["line_name_as_reported"].dropna().astype(str):
                    cl = lbl.strip()
                    if cl and cl not in seen_lbls and "unlabelled" not in cl.lower():
                        seen_lbls.append(cl)
                ar_labels_list = seen_lbls[:8]
            ty_sub = sub_df[sub_df["source_table"] == "ten_year_summary"]
            if not ty_sub.empty:
                ten_year_lbl = str(ty_sub.iloc[-1]["line_name_as_reported"]).strip()

            fys_obs = sorted(sub_df["fiscal_year"].dropna().astype(str).unique())
            if fys_obs:
                valid_from_fy = fys_obs[0]
                valid_to_fy = fys_obs[-1]
            observed_scopes = set(sub_df["scope"].dropna().astype(str).unique())

        line_name = meta.get("line_name") or _humanize_code(lc, sample_label)
        stmt = meta.get("statement") or (str(sub_df.iloc[0]["statement"]) if not sub_df.empty else "pnl")
        unit_def = meta.get("unit") or (
            "INR_cr"
            if (not sub_df.empty and str(sub_df.iloc[0]["unit"]) in ("INR_mn", "INR_cr"))
            else (str(sub_df.iloc[0]["unit"]) if not sub_df.empty else "INR_cr")
        )

        if "line_class" in meta:
            lclass = meta["line_class"]
        elif lc.startswith("RATIO."):
            lclass = "ratio"
        elif lc.startswith(("QTY.", "PROD.")):
            lclass = "volume"
        elif lc == "OTH.EMPLOYEES":
            lclass = "headcount"
        elif lc.startswith("PL.EPS"):
            lclass = "per_share"
        elif lc.endswith(".TOTAL") or lc in ("PL.PAT", "PL.TCI", "BS.TOTAL_ASSETS", "BS.TOTAL_EQ_LIAB", "CF.CCE_CLOSE"):
            lclass = "total"
        elif "SUBTOTAL" in lc or lc in ("PL.TOTAL_INCOME", "PL.TOTAL_EXP", "PL.PBT_PRE_EXC", "PL.PBT", "PL.TAX", "PL.OCI", "CF.CFO", "CF.CFI", "CF.CFF", "CF.NET_CHANGE_CCE"):
            lclass = "subtotal"
        elif stmt == "balance_sheet":
            lclass = "stock"
        else:
            lclass = "flow"

        is_sub = bool(meta.get("is_sub", lclass in ("subtotal", "total")))
        is_tot = bool(meta.get("is_tot", lclass == "total"))
        is_kpi = bool(
            meta.get(
                "is_kpi",
                lc.startswith(("RATIO.", "REV.", "LEVY.", "QTY.", "PROD.", "CAPEX.", "OTH."))
                or lc in ("N35.TOTAL", "N36.TOTAL", "N37.TOTAL", "NTAX.TOTAL", "SEG.REV.OFF", "SEG.REV.ON", "SEG.RES.OFF", "SEG.RES.ON"),
            )
        )

        if is_tot:
            line_kind = "total"
        elif is_sub:
            line_kind = "subtotal"
        elif lclass == "ratio":
            line_kind = "ratio"
        elif stmt in ("physical", "other_info") or lclass in ("volume", "headcount"):
            line_kind = "memo"
        else:
            line_kind = "detail"

        lvl = int(meta.get("level", 0 if is_tot else (1 if is_sub else 2)))
        ord_num = int(meta.get("order", 1000 + idx))
        nat_sign = meta.get("sign") or (
            "credit"
            if lc.startswith(("PL.REV", "PL.OTHER_INCOME", "PL.TOTAL_INCOME", "PL.PBT", "PL.PAT", "BS.EQUITY", "BS.SHARE", "BS.OTHER_EQUITY", "BS.LIAB", "BS.BORROW", "REV."))
            else "debit"
        )
        sign_in_parent = -1 if lc in ("PL.TOTAL_EXP", "PL.TAX", "PL.TAX_CURRENT", "PL.TAX_DEFERRED", "PL.TAX_EARLIER", "CF.TAX_PAID", "CF.BANK_OVERDRAFT") else 1

        if lc in consolidated_only_codes or observed_scopes == {"consolidated"}:
            scope_app = "consolidated_only"
        elif observed_scopes == {"standalone"} or lc.startswith(("LEVY.", "REV.", "QTY.", "PROD.", "RATIO.", "OTH.", "CAPEX.", "N35", "N36", "N37", "N22", "NTAX", "NPROV", "SEG.")):
            scope_app = "standalone_only" if "consolidated" not in observed_scopes else "both"
        else:
            scope_app = "both"

        xbrl_elem = meta.get("xbrl")
        xbrl_tags_str = f"in-bse-fin:{xbrl_elem}" if xbrl_elem else None
        yahoo_fld = meta.get("yahoo")
        yahoo_type_str = f"annual{yahoo_fld.replace(' ', '')}" if yahoo_fld else None
        if yahoo_fld:
            yahoo_eq = "approx" if lc in ("PL.REV_OPS", "PL.PAT", "BS.EQUITY.TOTAL") else "exact"
        else:
            yahoo_eq = "none"

        aliases_str = meta.get("aliases") or (sample_label if sample_label and sample_label != line_name else line_name)
        ar_labels_str = "|".join(ar_labels_list) if ar_labels_list else aliases_str

        rows.append(
            {
                "line_code": lc,
                "statement": stmt,
                "display_name": line_name,
                "line_name": line_name,
                "line_name_aliases": aliases_str,
                "section": meta.get("section") or stmt.replace("_", " ").title(),
                "subsection": meta.get("subsection"),
                "parent_line_code": meta.get("parent"),
                "level": lvl,
                "hierarchy_level": lvl,
                "line_order": ord_num,
                "display_order": ord_num,
                "line_kind": line_kind,
                "line_class": lclass,
                "subtotal_formula": meta.get("formula"),
                "formula": meta.get("formula"),
                "sign_in_parent": sign_in_parent,
                "natural_sign": nat_sign,
                "schedule3_ref": meta.get("ind_as"),
                "ind_as_schedule_iii_ref": meta.get("ind_as"),
                "ar_note_ref_typical": meta.get("note"),
                "ar_labels": ar_labels_str,
                "ten_year_label": ten_year_lbl,
                "xbrl_tags": xbrl_tags_str,
                "xbrl_element_name": xbrl_elem,
                "yahoo_types": yahoo_type_str,
                "yahoo_field_name": yahoo_fld,
                "yahoo_equivalence": yahoo_eq,
                "scope_applicability": scope_app,
                "valid_from_fy": valid_from_fy or "FY17",
                "valid_to_fy": valid_to_fy or "FY26",
                "unit_default": unit_def,
                "is_subtotal": is_sub,
                "is_total": is_tot,
                "is_kpi": is_kpi,
                "description": meta.get("desc") or f"Canonical financial line {lc} ({line_name}).",
            }
        )

    dim_df = pd.DataFrame(rows, columns=DIM_COLUMNS).sort_values(["display_order", "line_code"]).reset_index(drop=True)
    return dim_df


def _make_snippet(r: pd.Series) -> str:
    raw_lbl = str(r.get("raw_label", "")).strip()
    raw_val = str(r.get("raw_value_text", "")).strip()
    s = f"{raw_lbl} | {raw_val}"
    return s[:200]


def _with_extract_id_note(note_val: Optional[str], extract_id: Optional[str]) -> Optional[str]:
    if not extract_id:
        return note_val
    tag = f"extract_id={extract_id}"
    if not note_val:
        return tag
    if tag in note_val:
        return note_val
    return f"{tag}; {note_val}"


def build_gold_dataframe(out_dir: Path = OUT_DIR) -> Tuple[pd.DataFrame, pd.DataFrame, GateRunResult]:
    """Build `fact_financial_statement_line`, `dim_financial_line`, and run `verify_gates`."""
    st = pd.read_parquet(out_dir / "statements_raw.parquet")
    ty = pd.read_parquet(out_dir / "ten_year_raw.parquet")
    nt = pd.read_parquet(out_dir / "notes_raw.parquet")
    xb = pd.read_parquet(out_dir / "xbrl_raw.parquet")

    records: List[Dict[str, Any]] = []

    # 1. Full financial statements (`statements_raw.parquet`)
    for _, grp in st.groupby(["source_doc", "scope", "statement", "fiscal_year", "period_type"], sort=False):
        grp_sorted = grp.sort_values("line_seq")
        codes = map_statements_group(grp_sorted)
        for (_, r), lc in zip(grp_sorted.iterrows(), codes):
            val = float(r["parsed_value"]) if r["parsed_value"] is not None and not pd.isna(r["parsed_value"]) else np.nan
            unit = str(r["unit"]).strip()
            val_cr = val / 10.0 if unit == "INR_mn" else (val if unit == "INR_cr" else np.nan)
            prec_cr = 0.001 if unit == "INR_mn" else np.nan
            nvint = normalize_vintage(r["report_vintage"])
            ext_id = _clean_text(r.get("extract_id"))
            records.append(
                {
                    "fiscal_year": str(r["fiscal_year"]).strip(),
                    "period_type": str(r["period_type"]).strip(),
                    "period_end": str(r["period_end"]).strip(),
                    "scope": str(r["scope"]).strip(),
                    "statement": str(r["statement"]).strip(),
                    "line_code": lc,
                    "line_name_as_reported": str(r["raw_label"]).strip(),
                    "value_native": val,
                    "unit_native": unit,
                    "value_inr_cr": round(val_cr, 6) if not pd.isna(val_cr) else np.nan,
                    "value": val,
                    "unit": unit,
                    "precision_inr_cr": prec_cr,
                    "is_restated": bool(r["is_restated"]) if not pd.isna(r["is_restated"]) else False,
                    "raw_is_restated": bool(r["is_restated"]) if not pd.isna(r["is_restated"]) else False,
                    "is_nil": bool(r["is_nil"]) if not pd.isna(r["is_nil"]) else False,
                    "sign_convention": "deduction_negative" if bool(r.get("is_deduction", False)) else "as_reported",
                    "source_system": "ar",
                    "report_vintage": nvint,
                    "source_doc": str(r["source_doc"]).strip(),
                    "source_page": int(r["source_page"]) if not pd.isna(r["source_page"]) else None,
                    "source_page_label": _clean_text(r.get("source_page_label")),
                    "source_table": str(r["source_table"]).strip(),
                    "source_text_line": int(r["source_text_line"]) if "source_text_line" in r and not pd.isna(r["source_text_line"]) else None,
                    "source_snippet": _make_snippet(r),
                    "raw_label": str(r["raw_label"]).strip(),
                    "raw_value_text": str(r["raw_value_text"]).strip(),
                    "extraction_method": str(r["extraction_method"]).strip(),
                    "extractor_version": str(r.get("extractor_version", "p1.3")).strip(),
                    "extracted_at": str(r.get("extracted_at", "2026-10-24T00:00:00Z")).strip(),
                    "extract_id": ext_id,
                    "cross_check_source": None,
                    "cross_check_value": np.nan,
                    "cross_check_delta_inr_cr": np.nan,
                    "notes": _with_extract_id_note(_clean_text(r.get("notes")), ext_id),
                    "bronze_subtotal_ok": bool(r["subtotal_ok"]) if not pd.isna(r.get("subtotal_ok")) else None,
                }
            )

    # Index existing statement rows by (fiscal_year, period_type, scope, line_code, report_vintage)
    stmt_key_to_idx: Dict[Tuple[str, str, str, str, str], int] = {}
    for idx, rec in enumerate(records):
        key = (rec["fiscal_year"], rec["period_type"], rec["scope"], rec["line_code"], rec["report_vintage"])
        stmt_key_to_idx[key] = idx

    # 2. 10-year tables (`ten_year_raw.parquet`)
    # First deduplicate identical (report_vintage, fiscal_year, line_code) rows across 10-yr sub-blocks
    ty_mapped_rows: List[Tuple[int, str, str]] = []
    for idx, r in ty.iterrows():
        stmt_m, lc_m = map_ten_year_row(r)
        ty_mapped_rows.append((idx, stmt_m, lc_m))

    seen_ty_keys: Dict[Tuple[str, str, str], int] = {}
    for idx, stmt_m, lc_m in ty_mapped_rows:
        r = ty.loc[idx]
        nvint = normalize_vintage(r["report_vintage"])
        fy = str(r["fiscal_year"]).strip()
        scope = str(r.get("scope", "standalone")).strip()
        ptype = str(r.get("period_type", "annual")).strip()
        fyn = fy_number(fy)
        pend = str(r["period_end"]).strip() if "period_end" in r and not pd.isna(r["period_end"]) else (f"20{fyn:02d}-03-31" if fyn is not None else "2024-03-31")
        val = float(r["parsed_value"]) if r["parsed_value"] is not None and not pd.isna(r["parsed_value"]) else np.nan
        unit = str(r["unit"]).strip()
        val_cr = val / 10.0 if unit == "INR_mn" else (val if unit == "INR_cr" else np.nan)
        prec_cr = 0.1 if unit == "INR_mn" else np.nan
        ext_id = _clean_text(r.get("extract_id"))

        # If a 2-dp full_statement row already exists for the exact same (fy, ptype, scope, lc_m, nvint),
        # attach the 10-yr value as its cross_check_source/value so V08 verifies it without grain collision.
        skey = (fy, ptype, scope, lc_m, nvint)
        if skey in stmt_key_to_idx:
            sidx = stmt_key_to_idx[skey]
            records[sidx]["cross_check_source"] = f"ar_ten_year:{nvint}"
            records[sidx]["cross_check_value"] = round(val_cr, 4) if not pd.isna(val_cr) else val
            if not pd.isna(val_cr) and not pd.isna(records[sidx]["value_inr_cr"]):
                records[sidx]["cross_check_delta_inr_cr"] = round(float(records[sidx]["value_inr_cr"]) - val_cr, 4)
            continue

        ty_key = (nvint, fy, lc_m)
        if ty_key in seen_ty_keys:
            continue
        seen_ty_keys[ty_key] = 1

        records.append(
            {
                "fiscal_year": fy,
                "period_type": ptype,
                "period_end": pend,
                "scope": scope,
                "statement": stmt_m,
                "line_code": lc_m,
                "line_name_as_reported": str(r["raw_label"]).strip(),
                "value_native": val,
                "unit_native": unit,
                "value_inr_cr": round(val_cr, 6) if not pd.isna(val_cr) else np.nan,
                "value": val,
                "unit": unit,
                "precision_inr_cr": prec_cr,
                "is_restated": bool(r["is_restated"]) if not pd.isna(r["is_restated"]) else False,
                "raw_is_restated": bool(r["is_restated"]) if not pd.isna(r["is_restated"]) else False,
                "is_nil": bool(r["is_nil"]) if not pd.isna(r["is_nil"]) else False,
                "sign_convention": "as_reported",
                "source_system": "ar",
                "report_vintage": nvint,
                "source_doc": str(r["source_doc"]).strip(),
                "source_page": int(r["source_page"]) if not pd.isna(r["source_page"]) else None,
                "source_page_label": _clean_text(r.get("source_page_label")),
                "source_table": "ten_year_summary",
                "source_text_line": int(r["source_text_line"]) if "source_text_line" in r and not pd.isna(r["source_text_line"]) else None,
                "source_snippet": _make_snippet(r),
                "raw_label": str(r["raw_label"]).strip(),
                "raw_value_text": str(r["raw_value_text"]).strip(),
                "extraction_method": str(r.get("extraction_method", "text_parse")).strip(),
                "extractor_version": str(r.get("extractor_version", "p1.2")).strip(),
                "extracted_at": str(r.get("extracted_at", "2026-10-24T00:00:00Z")).strip(),
                "extract_id": ext_id,
                "cross_check_source": None,
                "cross_check_value": np.nan,
                "cross_check_delta_inr_cr": np.nan,
                "notes": _with_extract_id_note(_clean_text(r.get("notes")), ext_id),
                "bronze_subtotal_ok": None,
            }
        )

    # 3. Notes (`notes_raw.parquet`)
    seen_note_keys: Dict[Tuple[str, str, str, str], int] = {}
    for _, r in nt.iterrows():
        stmt_n, lc_n = map_note_row(r)
        if not lc_n:
            continue
        nvint = normalize_vintage(r["report_vintage"])
        fy = str(r["fiscal_year"]).strip()
        scope = str(r["scope"]).strip()
        ptype = str(r["period_type"]).strip()
        nkey = (nvint, fy, scope, lc_n)
        if nkey in seen_note_keys:
            continue
        seen_note_keys[nkey] = 1

        val = float(r["parsed_value"]) if r["parsed_value"] is not None and not pd.isna(r["parsed_value"]) else np.nan
        unit = str(r["unit"]).strip()
        val_cr = val / 10.0 if unit == "INR_mn" else (val if unit == "INR_cr" else np.nan)
        prec_cr = 0.001 if unit == "INR_mn" else np.nan
        ext_id = _clean_text(r.get("extract_id"))

        records.append(
            {
                "fiscal_year": fy,
                "period_type": ptype,
                "period_end": str(r["period_end"]).strip(),
                "scope": scope,
                "statement": stmt_n,
                "line_code": lc_n,
                "line_name_as_reported": str(r["raw_label"]).strip(),
                "value_native": val,
                "unit_native": unit,
                "value_inr_cr": round(val_cr, 6) if not pd.isna(val_cr) else np.nan,
                "value": val,
                "unit": unit,
                "precision_inr_cr": prec_cr,
                "is_restated": bool(r["is_restated"]) if not pd.isna(r["is_restated"]) else False,
                "raw_is_restated": bool(r["is_restated"]) if not pd.isna(r["is_restated"]) else False,
                "is_nil": bool(r["is_nil"]) if not pd.isna(r["is_nil"]) else False,
                "sign_convention": "deduction_negative" if bool(r.get("is_deduction", False)) else "as_reported",
                "source_system": "ar",
                "report_vintage": nvint,
                "source_doc": str(r["source_doc"]).strip(),
                "source_page": int(r["source_page"]) if not pd.isna(r["source_page"]) else None,
                "source_page_label": _clean_text(r.get("source_page_label")),
                "source_table": str(r["source_table"]).strip(),
                "source_text_line": int(r["source_text_line"]) if "source_text_line" in r and not pd.isna(r["source_text_line"]) else None,
                "source_snippet": _make_snippet(r),
                "raw_label": str(r["raw_label"]).strip(),
                "raw_value_text": str(r["raw_value_text"]).strip(),
                "extraction_method": str(r.get("extraction_method", "text_parse")).strip(),
                "extractor_version": str(r.get("extractor_version", "p1.3")).strip(),
                "extracted_at": str(r.get("extracted_at", "2026-10-24T00:00:00Z")).strip(),
                "extract_id": ext_id,
                "cross_check_source": None,
                "cross_check_value": np.nan,
                "cross_check_delta_inr_cr": np.nan,
                "notes": _with_extract_id_note(_clean_text(r.get("notes")), ext_id),
                "bronze_subtotal_ok": bool(r["subtotal_ok"]) if not pd.isna(r.get("subtotal_ok")) else None,
            }
        )

    # 4. XBRL (`xbrl_raw.parquet`)
    seen_xbrl_keys: Dict[Tuple[str, str, str, str, str], int] = {}
    for _, r in xb.iterrows():
        mapped_x = map_xbrl_row(r)
        if not mapped_x:
            continue
        stmt_x, ptype_x, lc_x = mapped_x
        nvint = normalize_vintage(r["report_vintage"])
        fy = str(r["fiscal_year"]).strip()
        scope = str(r["scope"]).strip()
        xkey = (nvint, fy, ptype_x, scope, lc_x)
        if xkey in seen_xbrl_keys:
            continue
        seen_xbrl_keys[xkey] = 1

        val = float(r["parsed_value"]) if r["parsed_value"] is not None and not pd.isna(r["parsed_value"]) else np.nan
        unit = str(r["unit"]).strip()
        val_cr = float(r["value_inr_cr"]) if r.get("value_inr_cr") is not None and not pd.isna(r.get("value_inr_cr")) else np.nan
        prec_cr = float(r["precision_inr_cr"]) if r.get("precision_inr_cr") is not None and not pd.isna(r.get("precision_inr_cr")) else 0.01
        ext_id = _clean_text(r.get("extract_id"))

        records.append(
            {
                "fiscal_year": fy,
                "period_type": ptype_x,
                "period_end": str(r["period_end"]).strip(),
                "scope": scope,
                "statement": stmt_x,
                "line_code": lc_x,
                "line_name_as_reported": str(r["raw_label"]).strip(),
                "value_native": val,
                "unit_native": unit,
                "value_inr_cr": round(val_cr, 6) if not pd.isna(val_cr) else np.nan,
                "value": val,
                "unit": unit,
                "precision_inr_cr": prec_cr,
                "is_restated": bool(r["is_restated"]) if not pd.isna(r["is_restated"]) else False,
                "raw_is_restated": bool(r["is_restated"]) if not pd.isna(r["is_restated"]) else False,
                "is_nil": bool(r["is_nil"]) if not pd.isna(r["is_nil"]) else False,
                "sign_convention": "as_reported",
                "source_system": "xbrl",
                "report_vintage": nvint,
                "source_doc": str(r["source_doc"]).strip(),
                "source_page": None,
                "source_page_label": None,
                "source_table": "xbrl_instance",
                "source_text_line": int(r["source_text_line"]) if "source_text_line" in r and not pd.isna(r["source_text_line"]) else None,
                "source_snippet": _make_snippet(r),
                "raw_label": str(r["raw_label"]).strip(),
                "raw_value_text": str(r["raw_value_text"]).strip(),
                "extraction_method": "xbrl",
                "extractor_version": str(r.get("extractor_version", "p1.4")).strip(),
                "extracted_at": str(r.get("extracted_at", "2026-10-24T00:00:00Z")).strip(),
                "extract_id": ext_id,
                "cross_check_source": None,
                "cross_check_value": np.nan,
                "cross_check_delta_inr_cr": np.nan,
                "notes": _with_extract_id_note(_clean_text(r.get("notes")), ext_id),
                "bronze_subtotal_ok": None,
            }
        )

    raw_gold = pd.DataFrame(records)
    raw_gold = compute_vintage_flags(raw_gold)
    dim_df = build_dim_financial_line(raw_gold)
    parent_map = dict(zip(dim_df["line_code"], dim_df["parent_line_code"]))
    order_map = dict(zip(dim_df["line_code"], dim_df["line_order"]))
    raw_gold["parent_line_code"] = raw_gold["line_code"].map(parent_map)
    raw_gold["line_order"] = raw_gold["line_code"].map(order_map).fillna(9999).astype("int64")
    gate_res = verify_gates(raw_gold, dim_df=dim_df)
    gold_out = gate_res.df.copy()
    gold_out["period_end"] = pd.to_datetime(gold_out["period_end"]).dt.date
    gold_out["source_page"] = pd.to_numeric(gold_out["source_page"], errors="coerce").astype("Int64")
    gold_out["source_text_line"] = pd.to_numeric(gold_out["source_text_line"], errors="coerce").astype("Int64")
    gold_out["line_order"] = pd.to_numeric(gold_out["line_order"], errors="coerce").fillna(9999).astype("int64")
    gate_res.df = gold_out

    # Also build combined bronze table fin_extract_raw.parquet (SPEC-01 §5.0)
    bronze_cols = [
        "extract_id",
        "source_system",
        "source_doc",
        "source_page",
        "source_page_label",
        "source_text_line",
        "raw_label",
        "raw_value_text",
        "parsed_value",
        "unit",
        "column_header",
        "scope",
        "statement_guess",
        "extractor_version",
        "extracted_at",
    ]
    bronze_parts = []
    for bdf in (st, ty, nt, xb):
        part = pd.DataFrame()
        for col in bronze_cols:
            if col in bdf.columns:
                part[col] = bdf[col]
            elif col == "statement_guess" and "statement" in bdf.columns:
                part[col] = bdf["statement"]
            else:
                part[col] = None
        bronze_parts.append(part)
    bronze_all = pd.concat(bronze_parts, ignore_index=True)
    bronze_all["source_page"] = pd.to_numeric(bronze_all["source_page"], errors="coerce").astype("Int64")
    bronze_all["source_text_line"] = pd.to_numeric(bronze_all["source_text_line"], errors="coerce").astype("Int64")
    bronze_all["parsed_value"] = pd.to_numeric(bronze_all["parsed_value"], errors="coerce")
    bronze_all.to_parquet(out_dir / "fin_extract_raw.parquet", index=False)

    return gold_out, dim_df, gate_res


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gold_df, dim_df, gate_res = build_gold_dataframe(OUT_DIR)

    # Save dim_financial_line.csv
    dim_df.to_csv(DIM_CSV_PATH, index=False)

    # Save fact_financial_statement_line.parquet and verified-only fact_snapshot.parquet
    fact_path = OUT_DIR / "fact_financial_statement_line.parquet"
    snap_path = OUT_DIR / "fact_snapshot.parquet"
    gate_run_path = OUT_DIR / "fin_gate_run.parquet"
    conflicts_path = OUT_DIR / "conflicts.csv"

    gold_df.to_parquet(fact_path, index=False)
    snap_df = gold_df[gold_df["verified"]].copy().reset_index(drop=True)
    snap_df.to_parquet(snap_path, index=False)
    gate_res.gate_run_rows().to_parquet(gate_run_path, index=False)
    gate_res.conflicts.to_csv(conflicts_path, index=False)

    utc_stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_md = gate_res.to_markdown()
    report_path = OUT_DIR / f"gate_report_{utc_stamp}.md"
    latest_report_path = OUT_DIR / "gate_report_latest.md"
    report_path.write_text(report_md, encoding="utf-8")
    latest_report_path.write_text(report_md, encoding="utf-8")

    print(f"Wrote dim_financial_line.csv: {len(dim_df):,} lines")
    print(f"Wrote fact_financial_statement_line.parquet: {len(gold_df):,} rows")
    print(f"Wrote fact_snapshot.parquet (verified=TRUE): {len(snap_df):,} rows ({len(snap_df)/len(gold_df)*100:.2f}%)")
    print(f"Wrote conflicts.csv: {len(gate_res.conflicts):,} rows")
    print(f"Wrote {report_path.name}")
    for gid, st in gate_res.gate_stats.items():
        print(f"  {gid}: checked={st['checked']:,}, passed={st['passed']:,}, failed={st['failed']:,}, max_delta={st['max_delta_inr_cr']:.3f} cr")


if __name__ == "__main__":
    main()
