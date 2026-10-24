"""Unit and integration tests for P1.6 verification gates V01–V12 and gold SSOT build.

Covers:
1. All 7 synthetic gate fixtures required by Packet P1.6 §6 (V02, V03, V04 pass/fail, V07, V09, V10).
2. Full offline Gold SSOT invariants (`fact_financial_statement_line.parquet`, `fact_snapshot.parquet`,
   `dim_financial_line.csv`, `conflicts.csv`, `fin_gate_run.parquet`).
3. 12 golden values across standalone and consolidated statements, 10-yr summaries, notes, and vintages.
4. BUG-39 regression check (clean human-readable `line_name` values in `dim_financial_line.csv`).
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from financial_ssot.build_gold import DIM_COLUMNS, DIM_CSV_PATH, OUT_DIR
from financial_ssot.gates.verify_gates import verify_gates


# ---------------------------------------------------------------------------
# Part 1: Packet P1.6 §6 Synthetic Gate Fixtures
# ---------------------------------------------------------------------------
def test_v04_cash_tie_pass():
    df = pd.DataFrame(
        [
            {"fiscal_year": "FY26", "scope": "standalone", "statement": "cash_flow", "line_code": "CF.CCE_CLOSE", "value": 3289.10, "unit": "INR_mn"},
            {"fiscal_year": "FY26", "scope": "standalone", "statement": "balance_sheet", "line_code": "BS.CCE", "value": 3289.10, "unit": "INR_mn"},
        ]
    )
    out, conflicts = verify_gates(df)
    assert out["verified"].all()
    assert all("V04" in rules for rules in out["verified_rule_ids"])
    assert conflicts.empty


def test_v04_cash_tie_fail_populates_failed_rule_ids_and_conflicts():
    df = pd.DataFrame(
        [
            {"fiscal_year": "FY26", "scope": "standalone", "statement": "cash_flow", "line_code": "CF.CCE_CLOSE", "value": 3289.10, "unit": "INR_mn"},
            {"fiscal_year": "FY26", "scope": "standalone", "statement": "balance_sheet", "line_code": "BS.CCE", "value": 9999.00, "unit": "INR_mn"},
        ]
    )
    out, conflicts = verify_gates(df)
    assert not out["verified"].any()
    assert all("V04" in rules for rules in out["failed_rule_ids"])
    assert len(conflicts) == 1
    assert conflicts.iloc[0]["rule_id"] == "V04"
    assert conflicts.iloc[0]["status"] == "open"


def test_v07_prior_year_restatement():
    df = pd.DataFrame(
        [
            {"fiscal_year": "FY24", "report_vintage": "AR_FY24", "line_code": "PL.REV_OPS", "value": 1384021.30, "unit": "INR_mn", "is_restated": False},
            {"fiscal_year": "FY24", "report_vintage": "AR_FY25", "line_code": "PL.REV_OPS", "value": 1384500.00, "unit": "INR_mn", "is_restated": True},
        ]
    )
    res = verify_gates(df)
    out = res.df
    assert int(res.gate_stats["V07"]["failed"]) == 0
    assert bool(out.loc[out["report_vintage"] == "AR_FY24", "is_own_vintage"].iloc[0]) is True
    assert bool(out.loc[out["report_vintage"] == "AR_FY25", "is_latest_vintage"].iloc[0]) is True
    assert bool(out.loc[out["report_vintage"] == "AR_FY25", "is_restated"].iloc[0]) is True
    assert out["verified"].all()


def test_v07_unflagged_mismatch_fails():
    df = pd.DataFrame(
        [
            {"fiscal_year": "FY24", "report_vintage": "AR_FY24", "line_code": "PL.OTHER_INCOME", "value": 107781.88, "unit": "INR_mn", "is_restated": False},
            {"fiscal_year": "FY24", "report_vintage": "AR_FY25", "line_code": "PL.OTHER_INCOME", "value": 107355.17, "unit": "INR_mn", "is_restated": False},
        ]
    )
    res = verify_gates(df)
    assert int(res.gate_stats["V07"]["failed"]) == 1
    assert len(res.conflicts) == 1
    c = res.conflicts.iloc[0]
    assert c["rule_id"] == "V07"
    assert c["status"] == "open"
    assert pd.isna(c["resolved_by"])


def test_v08_same_vintage_mismatch_fails():
    df = pd.DataFrame(
        [
            {"fiscal_year": "FY24", "report_vintage": "AR_FY24", "source_table": "statement_of_profit_and_loss", "line_code": "PL.REV_OPS", "value": 1384021.30, "unit": "INR_mn", "is_restated": False},
            {"fiscal_year": "FY24", "report_vintage": "AR_FY24", "source_table": "ten_year_summary", "line_code": "PL.REV_OPS", "value": 1384050.00, "unit": "INR_mn", "is_restated": False},
        ]
    )
    res = verify_gates(df)
    assert int(res.gate_stats["V08"]["failed"]) == 1
    assert not res.conflicts.empty
    c = res.conflicts[res.conflicts["rule_id"] == "V08"].iloc[0]
    assert c["status"] == "open"
    assert pd.isna(c["resolved_by"])


def test_v09_ten_year_restatement():
    df = pd.DataFrame(
        [
            {
                "fiscal_year": "FY24",
                "report_vintage": "AR_FY24",
                "source_table": "ten_year_summary",
                "line_code": "PL.OTHER_NON_OP_INCOME_10YR",
                "value": 73479.0,
                "unit": "INR_mn",
                "is_restated": False,
            },
            {
                "fiscal_year": "FY24",
                "report_vintage": "AR_FY26",
                "source_table": "ten_year_summary",
                "line_code": "PL.OTHER_NON_OP_INCOME_10YR",
                "value": 73052.0,
                "unit": "INR_mn",
                "is_restated": False,
            },
        ]
    )
    res = verify_gates(df)
    out = res.df
    conflicts = res.conflicts
    assert int(res.gate_stats["V09"]["failed"]) == 1
    assert bool(out.loc[out["report_vintage"] == "AR_FY26", "is_restated"].iloc[0]) is True
    assert out["verified"].all()
    assert not conflicts.empty
    c = conflicts[conflicts["rule_id"] == "V09"].iloc[0]
    assert c["status"] == "open"
    assert pd.isna(c["resolved_by"])
    assert "7347.90" in c["resolution"] and "7305.20" in c["resolution"]


def test_v02_no_plug_rejects_computed():
    df = pd.DataFrame(
        [
            {"fiscal_year": "FY26", "line_code": "PL.OTHER_EXP", "value": 100.0, "unit": "INR_mn", "extraction_method": "computed"},
        ]
    )
    out, conflicts = verify_gates(df)
    assert not out["verified"].any()
    assert "V02" in out.iloc[0]["failed_rule_ids"]
    assert len(conflicts) == 1
    assert conflicts.iloc[0]["rule_id"] == "V02"


def test_v03_bs_identity():
    df = pd.DataFrame(
        [
            {"fiscal_year": "FY26", "statement": "balance_sheet", "line_code": "BS.TOTAL_ASSETS", "value": 4842671.50, "unit": "INR_mn"},
            {"fiscal_year": "FY26", "statement": "balance_sheet", "line_code": "BS.EQUITY.TOTAL", "value": 3187542.10, "unit": "INR_mn"},
            {"fiscal_year": "FY26", "statement": "balance_sheet", "line_code": "BS.LIAB.NON_CURRENT.TOTAL", "value": 1024129.40, "unit": "INR_mn"},
            {"fiscal_year": "FY26", "statement": "balance_sheet", "line_code": "BS.LIAB.CURRENT.TOTAL", "value": 631000.00, "unit": "INR_mn"},
        ]
    )
    out, conflicts = verify_gates(df)
    assert out["verified"].all()
    assert all("V03" in rules for rules in out["verified_rule_ids"])
    assert conflicts.empty


def test_v10_xbrl_cross_check():
    df = pd.DataFrame(
        [
            {"fiscal_year": "FY24", "source_system": "ar", "report_vintage": "AR_FY24", "line_code": "PL.REV_OPS", "value": 1384021.30, "unit": "INR_mn"},
            {"fiscal_year": "FY24", "source_system": "xbrl", "report_vintage": "XBRL_FY24", "line_code": "PL.REV_OPS", "value": 1384021300000.0, "unit": "INR"},
        ]
    )
    out, conflicts = verify_gates(df)
    assert out["verified"].all()
    assert all("V10" in rules for rules in out["verified_rule_ids"])
    assert conflicts.empty


def test_v10_same_vintage_mismatch_fails():
    df = pd.DataFrame(
        [
            {"fiscal_year": "FY24", "source_system": "ar", "report_vintage": "AR_FY24", "line_code": "PL.REV_OPS", "value": 1384021.30, "unit": "INR_mn"},
            {"fiscal_year": "FY24", "source_system": "xbrl", "report_vintage": "XBRL_FY24", "line_code": "PL.REV_OPS", "value": 1384999900000.0, "unit": "INR"},
        ]
    )
    res = verify_gates(df)
    assert int(res.gate_stats["V10"]["failed"]) == 1
    xbrl_row = res.df[res.df["source_system"] == "xbrl"].iloc[0]
    assert bool(xbrl_row["v10_xbrl_match"]) is False
    assert bool(xbrl_row["verified"]) is False
    assert not res.conflicts.empty
    c = res.conflicts[res.conflicts["rule_id"] == "V10"].iloc[0]
    assert c["status"] == "open"
    assert pd.isna(c["resolved_by"])


# ---------------------------------------------------------------------------
# Part 2: Full Offline Gold SSOT Invariants & Golden Values
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def gold_artifacts():
    fact_path = OUT_DIR / "fact_financial_statement_line.parquet"
    snap_path = OUT_DIR / "fact_snapshot.parquet"
    gate_run_path = OUT_DIR / "fin_gate_run.parquet"
    conflicts_path = OUT_DIR / "conflicts.csv"
    assert fact_path.exists(), "Run `python -m financial_ssot.build_gold` first"
    assert snap_path.exists()
    assert DIM_CSV_PATH.exists()
    return {
        "fact": pd.read_parquet(fact_path),
        "snap": pd.read_parquet(snap_path),
        "dim": pd.read_csv(DIM_CSV_PATH),
        "gates": pd.read_parquet(gate_run_path),
        "conflicts": pd.read_csv(conflicts_path),
    }


def test_gold_parquet_100_percent_verified(gold_artifacts):
    fact = gold_artifacts["fact"]
    snap = gold_artifacts["snap"]
    assert len(fact) >= 7500
    assert bool(fact["verified"].all()) is True, f"Unverified rows found: {len(fact[~fact['verified']])}"
    assert len(snap) == len(fact)
    assert list(snap.columns) == list(fact.columns)
    assert all(len(x) == 0 for x in fact["failed_rule_ids"])
    assert all(len(x) >= 1 for x in fact["verified_rule_ids"])


def test_gates_v01_to_v12_non_tautological_and_core_zero_failures(gold_artifacts):
    gates = gold_artifacts["gates"].set_index("gate_id")
    assert set(gates.index) == {f"V{i:02d}" for i in range(1, 13)}
    # Every gate V01-V12 must have checked rows > 0
    assert (gates["rows_checked"] > 0).all(), gates[gates["rows_checked"] == 0].to_dict("records")
    # Core internal tie-out gates must have zero failures
    for gid in ("V01", "V02", "V03", "V04", "V05", "V06", "V11"):
        assert int(gates.loc[gid, "rows_failed"]) == 0, f"{gid} had unexpected failures: {gates.loc[gid].to_dict()}"
    # Cross-vintage / cross-table / coverage gates must honestly report real corpus diffs & gaps (B2)
    for gid in ("V07", "V08", "V09", "V10", "V12"):
        assert int(gates.loc[gid, "rows_failed"]) > 0, f"{gid} should report non-zero corpus failures/gaps"


def test_dim_financial_line_schema_and_bug39_no_artificial_prefixes(gold_artifacts):
    fact = gold_artifacts["fact"]
    dim = gold_artifacts["dim"]
    assert list(dim.columns) == DIM_COLUMNS
    assert dim["line_code"].is_unique

    missing_codes = set(fact["line_code"].unique()) - set(dim["line_code"].unique())
    assert not missing_codes, f"Fact codes missing from dim_financial_line.csv: {missing_codes}"

    # Consolidated-only lines must carry scope_applicability == 'consolidated_only' (M1)
    pat_owners = dim[dim["line_code"] == "PL.PAT_OWNERS"].iloc[0]
    assert pat_owners["scope_applicability"] == "consolidated_only"

    # BUG-39: No artificial bs_/pl_/cf_ prefixes or raw snake_case identifiers in line_name
    bad_names = [
        name
        for name in dim["line_name"].astype(str)
        if re.match(r"^(bs_|pl_|cf_|unmapped)", name.strip(), flags=re.IGNORECASE)
    ]
    assert not bad_names, f"Artificial prefixes in dim_financial_line.line_name: {bad_names}"


def test_conflicts_table_contains_fy24_reclass_and_restatements(gold_artifacts):
    conflicts = gold_artifacts["conflicts"]
    assert len(conflicts) >= 20
    # B1: Unflagged mismatches and >1% restatements must never be auto-resolved by verify_gates.py
    assert (conflicts["status"] == "open").all(), "Conflicts must be written with status='open'"
    assert conflicts["resolved_by"].isna().all(), "Open conflicts must have resolved_by=NULL"
    resolved_rows = conflicts[conflicts["status"] == "resolved"]
    if not resolved_rows.empty:
        assert resolved_rows["resolved_by"].notna().all()
        assert resolved_rows["resolved_at"].notna().all()

    # Must contain the FY24 ₹42.7 cr (427 ₹ mn) Other Income / Provisions reclassification
    fy24_reclass = conflicts[
        (conflicts["fiscal_year"] == "FY24")
        & (conflicts["line_code"].isin(["PL.OTHER_INCOME", "PL.TOTAL_INCOME", "PL.OTHER_NON_OP_INCOME_10YR", "PL.PROVISIONS_WRITEOFF"]))
        & (conflicts["delta_inr_cr"].abs().between(42.5, 42.9))
    ]
    assert len(fy24_reclass) >= 4, "FY24 ₹42.7 cr reclassification must be logged in conflicts.csv across V07/V08/V09"
    v09_fy24 = fy24_reclass[fy24_reclass["rule_id"] == "V09"].iloc[0]
    assert v09_fy24["line_code"] == "PL.OTHER_NON_OP_INCOME_10YR"
    assert abs(float(v09_fy24["value_a"]) - 7347.90) < 0.05
    assert abs(float(v09_fy24["value_b"]) - 7305.20) < 0.05


def test_views_unique_per_fy_scope_line_and_strict_own_vintage(gold_artifacts):
    fact = gold_artifacts["fact"]

    # B3: Quarterly rows must never carry is_own_vintage or is_latest_vintage
    q_rows = fact[fact["period_type"] != "annual"]
    assert not q_rows.empty
    assert not q_rows["is_own_vintage"].any()
    assert not q_rows["is_latest_vintage"].any()

    # I1: is_own_vintage is strictly True only when report_vintage matches fiscal_year
    own_rows = fact[fact["is_own_vintage"]]
    for _, row in own_rows.iterrows():
        fy_digits = row["fiscal_year"][2:]
        assert row["report_vintage"].endswith(f"FY{fy_digits}"), f"Non-matching own_vintage: {row.to_dict()}"

    # B3: v_fin_statement_as_reported filter must yield 0 duplicate (fiscal_year, scope, line_code) keys
    as_rep = fact[
        fact["verified"]
        & (fact["period_type"] == "annual")
        & fact["is_own_vintage"]
        & ((fact["source_system"] == "ar") | (fact["fiscal_year"] == "FY20"))
    ]
    dup_as_rep = as_rep.groupby(["fiscal_year", "scope", "line_code"]).size()
    assert (dup_as_rep == 1).all(), f"Duplicate keys in v_fin_statement_as_reported: {dup_as_rep[dup_as_rep > 1]}"

    # B3: v_fin_trend_latest filter must yield 0 duplicate (fiscal_year, scope, line_code) keys
    trend = fact[
        fact["verified"]
        & (fact["period_type"] == "annual")
        & fact["is_latest_vintage"]
    ]
    dup_trend = trend.groupby(["fiscal_year", "scope", "line_code"]).size()
    assert (dup_trend == 1).all(), f"Duplicate keys in v_fin_trend_latest: {dup_trend[dup_trend > 1]}"


def test_twelve_golden_values(gold_artifacts):
    fact = gold_artifacts["fact"]

    def get_val(fy: str, scope: str, lc: str, own: bool = True, vintage: str | None = None) -> float:
        sub = fact[(fact["fiscal_year"] == fy) & (fact["scope"] == scope) & (fact["line_code"] == lc) & (fact["period_type"] == "annual")]
        if vintage is not None:
            sub = sub[sub["report_vintage"] == vintage]
        elif own:
            sub = sub[sub["is_own_vintage"]]
        else:
            sub = sub[sub["is_latest_vintage"]]
        assert not sub.empty, f"Missing row for {fy} {scope} {lc} (own={own}, vintage={vintage})"
        return float(sub.iloc[0]["value_inr_cr"])

    # 1. FY24 Standalone Total Assets (AR FY24, p.245) = ₹4,46,020.89 cr (XBRL ₹4,46,020.90 cr)
    assert abs(get_val("FY24", "standalone", "BS.TOTAL_ASSETS") - 446020.890) < 0.05
    # 2. FY24 Standalone Revenue from Operations (AR FY24, p.247) = ₹1,38,402.13 cr
    assert abs(get_val("FY24", "standalone", "PL.REV_OPS") - 138402.131) < 0.05
    # 3. FY24 Standalone PAT (AR FY24, p.247) = ₹40,525.97 cr
    assert abs(get_val("FY24", "standalone", "PL.PAT") - 40525.970) < 0.05
    # 4. FY24 Standalone Other Income own-vintage (AR FY24, p.247) = ₹10,778.19 cr vs restated comparative (AR FY25, p.273) = ₹10,735.52 cr
    assert abs(get_val("FY24", "standalone", "PL.OTHER_INCOME", own=True) - 10778.188) < 0.05
    assert abs(get_val("FY24", "standalone", "PL.OTHER_INCOME", own=False) - 10735.517) < 0.05
    # 5. FY24 Standalone Statutory Levies Total (10-yr table, p.23) = ₹36,797.50 cr
    assert abs(get_val("FY24", "standalone", "LEVY.TOTAL", vintage="AR_FY24") - 36797.500) < 0.10
    # 6. FY26 Standalone Revenue from Operations (AR FY26, p.297) = ₹1,32,508.14 cr
    assert abs(get_val("FY26", "standalone", "PL.REV_OPS") - 132508.136) < 0.05
    # 7. FY26 Standalone PAT (AR FY26, p.297) = ₹32,894.02 cr
    assert abs(get_val("FY26", "standalone", "PL.PAT") - 32894.022) < 0.05
    # 8. FY26 Standalone Total Assets (AR FY26, p.295) = ₹4,61,276.20 cr
    assert abs(get_val("FY26", "standalone", "BS.TOTAL_ASSETS") - 461276.200) < 0.05
    # 9. FY26 Standalone Cash & Cash Equivalents tie-out (CF.CCE_CLOSE == BS.CCE = ₹83.51 cr, pp.295 & 301)
    assert abs(get_val("FY26", "standalone", "BS.CCE") - 83.511) < 0.05
    assert abs(get_val("FY26", "standalone", "CF.CCE_CLOSE") - 83.511) < 0.05
    # 10. FY26 Consolidated Revenue from Operations (AR FY26, p.434) = ₹6,62,247.32 cr
    assert abs(get_val("FY26", "consolidated", "PL.REV_OPS") - 662247.317) < 0.05
    # 11. FY26 Consolidated PAT (AR FY26, p.434) = ₹49,793.10 cr
    assert abs(get_val("FY26", "consolidated", "PL.PAT") - 49793.104) < 0.05
    # 12. FY26 Consolidated Total Assets (AR FY26, p.432) = ₹7,91,905.18 cr
    assert abs(get_val("FY26", "consolidated", "BS.TOTAL_ASSETS") - 791905.180) < 0.05
