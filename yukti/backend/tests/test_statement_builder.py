"""Unit and integration tests for P4.2 (`visual.type="statement"` contract + presenter emit).

Covers:
1. Schema validation & invariants of synthetic fixtures (`pnl_synthetic.json`, `bs_synthetic.json`, `cf_synthetic.json`).
2. SSOT `line_order` (`order`) 100% preservation across P&L, Balance Sheet, and Cash Flow.
3. Label cleaning (strips `"A1."`, `"I."`, `"   — "`, `"Less: "`, `"Add/(Less): "`, and `"(I + II)"` suffixes).
4. `verified=TRUE` filter, omitted period caveat footnote, and `None`/`null` preservation (never coerced to `0`).
5. `yoy_pct` computation and suppression on `subtotal`/`total` rows when base <= 0 (SPEC-09 §4.1).
6. `totals_check` validation for P&L, Balance Sheet (`A = E + L`), and Cash Flow (`Closing Cash = Opening Cash + Net Cash Change` + BS cash tie-out).
7. P4.1 `bridge()` consumption of emitted P&L `StatementSpec` unchanged.
8. `presenter.build_visual` gating behind `YUKTI_CONTRACT_V3_FIELDS=statement` (SPEC-03 §5.1).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import pytest
import jsonschema

from app.brain.statement_builder import (
    build_statement_spec,
    clean_statement_label,
    sort_periods_latest_first,
    v3_field_enabled,
)
from app.brain.bridge import bridge, BridgeOk
from app.brain.presenter import build_visual
from app.brain.query_spec import QuerySpec
from app.brain.compiler import CompiledQuery

BASE_DIR = Path(__file__).resolve().parents[3]
SCHEMA_PATH = BASE_DIR / "yukti" / "contracts" / "answer_contract.schema.json"
STATEMENT_FIXTURES_DIR = BASE_DIR / "yukti" / "contracts" / "fixtures" / "statement"

with open(SCHEMA_PATH, "r", encoding="utf-8") as _f:
    CONTRACT_SCHEMA = json.load(_f)

CONTRACT_VALIDATOR = jsonschema.Draft202012Validator(CONTRACT_SCHEMA)
STATEMENT_SPEC_VALIDATOR = jsonschema.Draft202012Validator(
    {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": CONTRACT_SCHEMA["$defs"],
        "$ref": "#/$defs/statement_spec",
    }
)


def _load_fixture(name: str) -> dict:
    with open(STATEMENT_FIXTURES_DIR / name, "r", encoding="utf-8") as fh:
        return json.load(fh)


def test_pnl_bs_cf_synthetic_fixtures_structure_and_schema():
    """All 3 statement fixtures validate against schema and satisfy P4.2 §6–7 invariants."""
    pnl = _load_fixture("pnl_synthetic.json")
    bs = _load_fixture("bs_synthetic.json")
    cf = _load_fixture("cf_synthetic.json")

    for name, doc in [("pnl", pnl), ("bs", bs), ("cf", cf)]:
        errs = list(CONTRACT_VALIDATOR.iter_errors(doc))
        assert not errs, f"{name} schema errors: {[e.message for e in errs]}"
        assert doc["contract_version"] == 2
        assert doc["visual"]["type"] == "statement"
        stmt = doc["visual"]["statement"]
        assert stmt["periods"] == ["FY26", "FY25", "FY24", "FY23", "FY22"]
        assert stmt["totals_check"]["passed"] is True
        assert stmt["totals_check"]["max_abs_delta_cr"] == 0.0
        assert stmt["synthetic"] is True

    # P&L specific checks (P4.2 §6): sections [income, expenses, profit], PAT kind "total"
    pnl_stmt = pnl["visual"]["statement"]
    assert [s["id"] for s in pnl_stmt["sections"]] == ["income", "expenses", "profit"]
    pat_rows = [
        r
        for s in pnl_stmt["sections"]
        for r in s["rows"]
        if r.get("line_code") in ("PAT", "PL.PAT", "pat_inr_cr")
    ]
    assert len(pat_rows) == 1
    assert pat_rows[0]["kind"] == "total"
    assert pat_rows[0]["level"] == 0

    # BS specific checks: identity "A = E + L"
    bs_stmt = bs["visual"]["statement"]
    assert bs_stmt["totals_check"]["identity"] == "A = E + L"

    # CF specific checks: identity "Closing Cash = Opening Cash + Net Cash Change"
    cf_stmt = cf["visual"]["statement"]
    assert cf_stmt["totals_check"]["identity"] == "Closing Cash = Opening Cash + Net Cash Change"


def test_ssot_line_order_preserved_100_percent():
    """Row order across sections must preserve 100% of SSOT `line_order` (`order`) (F4)."""
    shuffled_rows = [
        {"line_code": "PAT", "label": "Profit for the year (PAT)", "line_order": 60, "fiscal_year": "FY26", "value_inr_cr": 38348.07, "verified": True},
        {"line_code": "REV_OPS", "label": "Revenue from operations", "line_order": 10, "fiscal_year": "FY26", "value_inr_cr": 132508.14, "verified": True},
        {"line_code": "TAX_EXP", "label": "Tax expense", "line_order": 50, "fiscal_year": "FY26", "value_inr_cr": 12318.00, "verified": True},
        {"line_code": "TOT_INC", "label": "Total income", "line_order": 30, "fiscal_year": "FY26", "value_inr_cr": 143150.22, "verified": True},
        {"line_code": "OTHER_INC", "label": "Other income", "line_order": 20, "fiscal_year": "FY26", "value_inr_cr": 10642.08, "verified": True},
        {"line_code": "PBT", "label": "Profit before tax (PBT)", "line_order": 40, "fiscal_year": "FY26", "value_inr_cr": 50666.07, "verified": True},
    ]
    spec = build_statement_spec("pnl", shuffled_rows, periods=["FY26"])
    emitted_codes = [r["line_code"] for sec in spec["sections"] for r in sec["rows"]]
    assert emitted_codes == ["REV_OPS", "OTHER_INC", "TOT_INC", "PBT", "TAX_EXP", "PAT"]


@pytest.mark.parametrize(
    "raw_label,expected",
    [
        ("I. Gross Revenue from Operations", "Gross Revenue from Operations"),
        ("   — Crude Oil Revenue", "Crude Oil Revenue"),
        ("III. Total Income (I + II)", "Total Income"),
        ("Less: IV. Statutory Levies (Royalty, OIDB Cess, SAED)", "Statutory Levies (Royalty, OIDB Cess, SAED)"),
        ("Add/(Less): IX. Exceptional Items", "Exceptional Items"),
        ("A1. Oil & Gas Producing Properties (Net Block)", "Oil & Gas Producing Properties (Net Block)"),
        ("A8. Total Non-Current Assets (A1 to A7)", "Total Non-Current Assets"),
        ("Memo: Consolidated Group PAT", "Consolidated Group PAT"),
    ],
)
def test_clean_statement_label_strips_artificial_prefixes_and_formulas(raw_label: str, expected: str):
    """Invented prefixes ('A1.', 'I.', '   — ', 'Less:') and formula suffixes ('(I + II)') are stripped (BUG-39)."""
    assert clean_statement_label(raw_label) == expected


def test_verified_filter_omits_unverified_period_with_caveat_and_preserves_null():
    """Unverified rows are excluded, missing/unverified periods are omitted with a footnote, and None is never 0."""
    rows = [
        # FY26 verified, with OTHER_INC = None (must stay None, not 0)
        {"line_code": "REV_OPS", "label": "Revenue from operations", "line_order": 1, "fiscal_year": "FY26", "value_inr_cr": 132508.14, "verified": True},
        {"line_code": "OTHER_INC", "label": "Other income", "line_order": 2, "fiscal_year": "FY26", "value_inr_cr": None, "verified": True},
        {"line_code": "PAT", "label": "Profit for the year", "line_order": 3, "fiscal_year": "FY26", "value_inr_cr": 38348.07, "verified": True},
        # FY25 unverified -> must be excluded and FY25 omitted from periods with caveat
        {"line_code": "REV_OPS", "label": "Revenue from operations", "line_order": 1, "fiscal_year": "FY25", "value_inr_cr": 137846.29, "verified": False},
        {"line_code": "OTHER_INC", "label": "Other income", "line_order": 2, "fiscal_year": "FY25", "value_inr_cr": 9580.15, "verified": False},
        {"line_code": "PAT", "label": "Profit for the year", "line_order": 3, "fiscal_year": "FY25", "value_inr_cr": 35610.32, "verified": False},
    ]
    spec = build_statement_spec("pnl", rows, periods=["FY26", "FY25", "FY24"])
    assert spec["periods"] == ["FY26"]
    assert any("FY25 omitted" in fn and "verified=FALSE" in fn for fn in spec["footnotes"])
    assert any("FY24 omitted" in fn for fn in spec["footnotes"])

    all_rows = {r["line_code"]: r for s in spec["sections"] for r in s["rows"]}
    assert all_rows["OTHER_INC"]["values"]["FY26"] is None


def test_yoy_omitted_for_subtotal_or_total_when_base_non_positive():
    """SPEC-09 §4.1: `yoy_pct` is omitted for subtotals/totals when the prior period value <= 0."""
    rows = [
        {"line_code": "REV_OPS", "label": "Revenue", "line_order": 1, "kind": "line", "values": {"FY26": 110.0, "FY25": 100.0}, "verified": True},
        {"line_code": "PBT", "label": "Profit before tax", "line_order": 2, "kind": "subtotal", "values": {"FY26": 20.0, "FY25": -10.0}, "verified": True},
        {"line_code": "PAT", "label": "Profit after tax", "line_order": 3, "kind": "total", "values": {"FY26": 15.0, "FY25": 0.0}, "verified": True},
    ]
    spec = build_statement_spec("pnl", rows, periods=["FY26", "FY25"])
    by_code = {r["line_code"]: r for s in spec["sections"] for r in s["rows"]}
    assert by_code["REV_OPS"]["yoy_pct"] == 10.0
    assert "yoy_pct" not in by_code["PBT"]
    assert "yoy_pct" not in by_code["PAT"]


def test_totals_check_detects_corrupted_balance_sheet_and_cash_flow():
    """Corrupting Total Assets or Closing Cash beyond ₹0.5 cr sets `totals_check.passed = False`."""
    bs = _load_fixture("bs_synthetic.json")["visual"]["statement"]
    bs_rows = []
    for sec in bs["sections"]:
        for r in sec["rows"]:
            rc = copy.deepcopy(r)
            if rc["line_code"] == "total_assets_inr_cr":
                rc["values"]["FY26"] = rc["values"]["FY26"] + 5.0
            bs_rows.append(rc)
    bad_bs = build_statement_spec("balance_sheet", bs_rows, periods=bs["periods"])
    assert bad_bs["totals_check"]["passed"] is False
    assert bad_bs["totals_check"]["max_abs_delta_cr"] == 5.0

    cf = _load_fixture("cf_synthetic.json")["visual"]["statement"]
    cf_rows = [copy.deepcopy(r) for sec in cf["sections"] for r in sec["rows"]]
    # Corrupt BS cash tie-out
    bad_cf = build_statement_spec(
        "cash_flow",
        cf_rows,
        periods=cf["periods"],
        bs_cash_by_period={"FY26": 99999.0},
    )
    assert bad_cf["totals_check"]["passed"] is False
    assert bad_cf["totals_check"]["max_abs_delta_cr"] > 0.5


def test_bridge_consumes_emitted_pnl_statement_spec_unchanged():
    """P4.2 §5.5: P4.1 `bridge()` consumes the emitted `StatementSpec` unchanged across all 5 periods."""
    pnl_stmt = _load_fixture("pnl_synthetic.json")["visual"]["statement"]
    for fy in ["FY26", "FY25", "FY24", "FY23", "FY22"]:
        res = bridge(pnl_stmt, period=fy)
        assert isinstance(res, BridgeOk), f"Expected BridgeOk for {fy}, got {res}"
        chart_spec = res.to_chart_spec()
        assert chart_spec["kind"] == "waterfall"
        assert chart_spec["data"][0]["type"] == "total"
        assert chart_spec["data"][-1]["type"] == "total"


def test_presenter_flag_gating_for_statement_visual(monkeypatch):
    """SPEC-03 §5.1: `presenter.build_visual` emits `statement` only when `YUKTI_CONTRACT_V3_FIELDS` includes `statement`."""
    sample_rows = [
        {"line_order": 1, "line_code": "REV_OPS", "line_item": "I. Revenue from operations", "amount_cr": 132508.14, "prior_fy_cr": 137846.29},
        {"line_order": 2, "line_code": "OTHER_INC", "line_item": "II. Other income", "amount_cr": 10642.08, "prior_fy_cr": 9580.15},
        {"line_order": 3, "line_code": "TOT_INC", "line_item": "III. Total income (I + II)", "amount_cr": 143150.22, "prior_fy_cr": 147426.44},
        {"line_order": 4, "line_code": "STAT_LEVIES", "line_item": "Less: IV. Statutory levies", "amount_cr": 27820.12, "prior_fy_cr": 32450.18},
        {"line_order": 5, "line_code": "PROD_EXP", "line_item": "V. Production & operating expenditure", "amount_cr": 29354.03, "prior_fy_cr": 28640.22},
        {"line_order": 6, "line_code": "EMP_BENEFIT", "line_item": "VI. Employee benefits expense", "amount_cr": 7820.00, "prior_fy_cr": 7540.00},
        {"line_order": 7, "line_code": "EXPL_WRITEOFF", "line_item": "VII. Exploration costs written off", "amount_cr": 4780.00, "prior_fy_cr": 6120.00},
        {"line_order": 8, "line_code": "DDA", "line_item": "VIII. Depletion, depreciation & amortisation", "amount_cr": 18250.00, "prior_fy_cr": 19610.00},
        {"line_order": 9, "line_code": "FIN_COST", "line_item": "IX. Finance costs", "amount_cr": 4120.00, "prior_fy_cr": 4080.00},
        {"line_order": 10, "line_code": "OTHER_EXP", "line_item": "X. Other expenses", "amount_cr": 1860.00, "prior_fy_cr": 2163.97},
        {"line_order": 11, "line_code": "EXCEPTIONAL", "line_item": "XI. Exceptional items", "amount_cr": 1520.00, "prior_fy_cr": 460.00},
        {"line_order": 12, "line_code": "PBT", "line_item": "XII. Profit before tax", "amount_cr": 50666.07, "prior_fy_cr": 47282.07},
        {"line_order": 13, "line_code": "TAX_EXP", "line_item": "XIII. Tax expense", "amount_cr": 12318.00, "prior_fy_cr": 11671.75},
        {"line_order": 14, "line_code": "PAT", "line_item": "XIV. Profit for the year (PAT)", "amount_cr": 38348.07, "prior_fy_cr": 35610.32},
    ]

    spec = QuerySpec(
        domain="finance",
        metric="pnl_statement",
        aggregation="sum",
        dimensions=["line_item"],
        period={"fy": "FY26"},
    )
    compiled = CompiledQuery(
        sql="SELECT 1",
        subject="pnl",
        metric="pnl_statement",
        metric_label="Profit & Loss Statement",
        unit="inr_cr",
        source="certified:pnl",
        tables=["hrfin_gold.fact_financial_statement_line"],
        dims=[("line_item", "line_item")],
        value_columns=["amount_cr"],
        effective_period={"fy": "FY26"},
        grain="aggregate",
        aggregation="sum",
    )
    cols = ["line_order", "line_code", "line_item", "amount_cr", "prior_fy_cr"]

    # 1. Flag unset -> legacy v2 `table` visual
    monkeypatch.delenv("YUKTI_CONTRACT_V3_FIELDS", raising=False)
    assert v3_field_enabled("statement") is False
    vis_legacy = build_visual(
        spec,
        compiled,
        cols,
        sample_rows,
        None,
        "Statement of Profit & Loss",
        "FY26",
        "replace",
    )
    assert vis_legacy["type"] == "table"
    assert "statement" not in vis_legacy

    # 2. Flag enabled -> `statement` visual emitted, validates against statement_spec, KPIs capped at 3
    monkeypatch.setenv("YUKTI_CONTRACT_V3_FIELDS", "statement")
    assert v3_field_enabled("statement") is True
    vis_v3 = build_visual(
        spec,
        compiled,
        cols,
        sample_rows,
        None,
        "Statement of Profit & Loss",
        "FY26",
        "replace",
    )
    assert vis_v3["type"] == "statement"
    assert "statement" in vis_v3
    assert len(vis_v3["kpis"]) <= 3
    errs = list(STATEMENT_SPEC_VALIDATOR.iter_errors(vis_v3["statement"]))
    assert not errs, f"Presenter statement_spec validation errors: {[e.message for e in errs]}"
    assert vis_v3["statement"]["periods"] == ["FY26", "FY25"]
    assert vis_v3["statement"]["totals_check"]["passed"] is True

    # 3. Explicit waterfall request with flag enabled -> `chart` (waterfall) wins while preserving `statement`
    vis_wf = build_visual(
        spec,
        compiled,
        cols,
        sample_rows,
        "waterfall",
        "Statement of Profit & Loss",
        "FY26",
        "replace",
    )
    assert vis_wf["type"] == "chart"
    assert vis_wf["chart"]["kind"] == "waterfall"
    assert "statement" in vis_wf


def test_sort_periods_latest_first():
    """Periods are always deduplicated and sorted latest-first."""
    assert sort_periods_latest_first(["FY22", "FY26", "FY24", "FY25", "FY23", "FY26"]) == [
        "FY26",
        "FY25",
        "FY24",
        "FY23",
        "FY22",
    ]
