"""P1.4 NSE XBRL parser tests (offline).  Packet §6 examples, §7 acceptance, MANIFEST_v3 §3 anchors."""
from __future__ import annotations

from pathlib import Path

import pytest

from financial_ssot.extract import xbrl

FIXTURE = Path(__file__).parent / "fixtures" / "xbrl_fy21_s_subset.xml"
FY21_S = "NSE_XBRL_ONGC_FY2020-21_Standalone__INDAS_71833_464219_25062021060824_WEB.xml"
FILES = xbrl.xbrl_files()
needs_files = pytest.mark.skipif(len(FILES) != 12, reason="12 local NSE XBRL files not present")


def _fact(rows, tag, ctx="FourD", nth=0):
    hits = [r for r in rows if r["xbrl_tag"] == tag and r["context_ref"] == ctx]
    return hits[nth]


@pytest.fixture(scope="module")
def fixture_rows():
    return xbrl.parse(FIXTURE, "2026-10-23T00:00:00Z", source_name=FY21_S)


@pytest.fixture(scope="module")
def all_rows():
    return {f.name: xbrl.parse(f, "2026-10-23T00:00:00Z") for f in FILES}


# ---------------------------------------------------------------- unit: naming rules
def test_file_meta():
    m = xbrl.file_meta(FY21_S)
    assert (m["fiscal_year"], m["scope"], m["period_end"]) == ("FY21", "standalone", "2021-03-31")
    assert xbrl.file_meta("NSE_XBRL_ONGC_FY2017-18_Consolidated__X.xml")["scope"] == "consolidated"
    with pytest.raises(ValueError):
        xbrl.file_meta("random.xml")


@pytest.mark.parametrize("ctx,ptype,dim", [
    ("FourD", "annual", False), ("OneD", "quarter", False), ("OneI", "instant", False),
    ("FourReportableSegmentRevenue01D", "annual", True), ("OneReportableSegmentLiabilities02I", "instant", True),
])
def test_context_info(ctx, ptype, dim):
    ci = xbrl.context_info(ctx)
    assert (ci["period_type"], ci["dimensional"]) == (ptype, dim)


def test_unknown_context_naming_raises():
    with pytest.raises(ValueError):
        xbrl.context_info("D2024")


# ---------------------------------------------------------------- packet §6 examples (fixture)
@pytest.mark.parametrize("tag,ctx,inr,cr", [
    ("RevenueFromOperations", "FourD", 681410900000.0, 68141.09),
    ("ProfitLossForPeriod", "FourD", 112464400000.0, 11246.44),
    ("FinanceCosts", "FourD", 22145400000.0, 2214.54),
    ("RevenueFromOperations", "OneD", 211889100000.0, 21188.91),
])
def test_packet_examples(fixture_rows, tag, ctx, inr, cr):
    r = _fact(fixture_rows, tag, ctx)
    assert r["value_inr"] == inr
    assert r["value_inr_cr"] == pytest.approx(cr, abs=1e-9)
    assert r["value_inr_mn"] == pytest.approx(cr * 10, abs=1e-6)
    assert r["precision_inr_cr"] == 1.0 and r["decimals"] == "-7"
    assert r["period_type"] == ("annual" if ctx == "FourD" else "quarter")
    assert (r["fiscal_year"], r["scope"], r["source_system"], r["extraction_method"]) == \
        ("FY21", "standalone", "xbrl", "xbrl")


def test_bronze_schema_columns(fixture_rows):
    need = {"extract_id", "source_system", "source_doc", "source_page", "source_text_line", "raw_label",
            "raw_value_text", "parsed_value", "unit", "column_header", "scope", "statement_guess",
            "extractor_version", "extracted_at", "fiscal_year", "xbrl_tag", "context_ref", "period_type",
            "segment_member", "decimals", "value_inr", "value_inr_cr", "precision_inr_cr",
            "extraction_method"}
    assert need <= set(fixture_rows[0])
    assert len({r["extract_id"] for r in fixture_rows}) == len(fixture_rows)


def test_non_inr_units_have_no_crore(fixture_rows):
    eps = _fact(fixture_rows, "BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations")
    assert eps["unit"] == "INRPerShare" and eps["value_inr_cr"] is None and eps["precision_inr_cr"] is None


def test_segment_members(fixture_rows):
    seg = [r for r in fixture_rows if r["context_ref"].startswith("FourReportableSegmentRevenue")]
    assert {r["segment_member"] for r in seg} == {"a) Offshore", "b) Onshore"}
    liab = [r for r in fixture_rows if r["context_ref"] == "OneReportableSegmentLiabilities01I"]
    assert liab and all(r["segment_member"] == "a) Offshore" for r in liab)  # description from the ...01D twin


def test_text_facts_separate(fixture_rows):
    text = xbrl.parse_text_facts(FIXTURE, source_name=FY21_S)
    tags = {t["xbrl_tag"] for t in text}
    assert "NatureOfReportStandaloneConsolidated" in tags and "DescriptionOfReportableSegment" in tags
    numeric_tags = {r["xbrl_tag"] for r in fixture_rows}
    assert not numeric_tags & {"NatureOfReportStandaloneConsolidated", "DescriptionOfReportableSegment",
                               "DateOfEndOfReportingPeriod"}
    assert all(r["unit"] for r in fixture_rows)


def test_fy21_cash_flow_is_annual_and_cce_split(fixture_rows):
    cfo = _fact(fixture_rows, "CashFlowsFromUsedInOperatingActivities", "OneD")
    assert cfo["period_type"] == "annual" and cfo["statement_guess"] == "cash_flow"
    op, cl = (_fact(fixture_rows, xbrl.CF_CCE_TAG, "OneD", i) for i in (0, 1))
    assert (op["proposed_line_code"], cl["proposed_line_code"]) == ("CF.CCE_OPEN", "CF.CCE_CLOSE")
    assert (op["value_inr_cr"], cl["value_inr_cr"]) == pytest.approx((96.02, 119.90))


# ---------------------------------------------------------------- §7 acceptance (12 local files)
@needs_files
def test_all_12_files_parse_with_40_fourd(all_rows):
    assert len(all_rows) == 12
    for name, rows in all_rows.items():
        n = sum(1 for r in rows if r["context_ref"] == "FourD")
        assert n >= 40, (name, n)
    fys = {(r["fiscal_year"], r["scope"]) for rows in all_rows.values() for r in rows}
    assert len(fys) == 12


@needs_files
def test_own_year_ar_anchors_exact(all_rows):
    """MANIFEST_v3 §3: XBRL = own-year AR for FY18/FY19 revenue & PAT (₹ mn, AR 2 dp)."""
    rows = [r for rs in all_rows.values() for r in rs if r["scope"] == "standalone" and r["context_ref"] == "FourD"]
    anchors = {("FY18", "RevenueFromOperations"): 850041.00, ("FY18", "ProfitLossForPeriod"): 199452.60,
               ("FY19", "RevenueFromOperations"): 1096545.50, ("FY19", "ProfitLossForPeriod"): 267157.89,
               ("FY18", "Income"): 928876.48, ("FY18", "ProfitBeforeTax"): 288924.74,
               ("FY19", "ProfitBeforeTax"): 399540.25}
    for (fy, tag), ar_mn in anchors.items():
        x = next(r for r in rows if r["fiscal_year"] == fy and r["xbrl_tag"] == tag)
        assert abs(x["value_inr_cr"] - ar_mn / 10) <= 0.5 * x["precision_inr_cr"] + 1e-9, (fy, tag)


@needs_files
def test_fy24_cce_closing_ties_to_ar(all_rows):
    rows = next(rs for n, rs in all_rows.items() if "FY2023-24_Standalone" in n)
    cl = next(r for r in rows if r["proposed_line_code"] == "CF.CCE_CLOSE")
    assert cl["value_inr_cr"] == pytest.approx(34.55)  # AR FY24 CF closing C&CE 345.48 ₹ mn


@needs_files
def test_crosscheck_core_lines(all_rows):
    pd = pytest.importorskip("pandas")
    if not xbrl.TEN_YEAR.exists():
        pytest.skip("P1.2 ten_year_raw.parquet not built")
    ty = pd.read_parquet(xbrl.TEN_YEAR).to_dict("records")
    checks = xbrl.cross_check([r for rs in all_rows.values() for r in rs], ty)
    core = {"RevenueFromOperations", "FinanceCosts", "ProfitBeforeTax", "ProfitLossForPeriod"}
    got = [c for c in checks if c["xbrl_tag"] in core]
    assert {c["fiscal_year"] for c in got} == {"FY18", "FY19", "FY20", "FY21", "FY23", "FY24"}
    for c in got:
        # every core comparison passes, or is a restatement the 10-yr table marks '*'
        assert c["status"] in ("pass", "restated"), c
        if c["status"] == "restated":
            assert c["fiscal_year"] in ("FY19", "FY20", "FY23") and c["explanation"].startswith("restated")
    # revenue never restated; FY18/FY21/FY24 core lines all pass
    assert all(c["status"] == "pass" for c in got if c["xbrl_tag"] == "RevenueFromOperations")
    assert all(c["status"] == "pass" for c in got if c["fiscal_year"] in ("FY18", "FY21", "FY24"))
    # only unmarked difference: FY24 total income vs AR FY26 (documented reclassification)
    mism = [(c["fiscal_year"], c["xbrl_tag"], c["ten_year_vintage"]) for c in checks if c["status"] == "mismatch"]
    assert mism == [("FY24", "Income", "AR_FY2025-26")]


# ---------------------------------------------------------------- G4 r2 fixes
@needs_files
def test_fy23_s_cce_filing_defect_flagged(all_rows):
    """M1: FY23 S files C&CE opening 0.00 / closing 27.08 ₹ cr (= net change); AR FY23 is 50.11 -> 77.19."""
    rows = next(rs for n, rs in all_rows.items() if "FY2022-23_Standalone" in n)
    cce = [r for r in rows if r["xbrl_tag"] == xbrl.CF_CCE_TAG]
    assert [r["value_inr_cr"] for r in cce] == pytest.approx([0.0, 27.08])
    assert all(r["proposed_line_code"] is None and "cf_cce_filing_defect" in r["notes"] for r in cce)
    # no other file trips the rule; FY24 S keeps clean codes (77.19 -> 34.55 = AR FY24)
    flagged = {n for n, rs in all_rows.items() for r in rs if "cf_cce_filing_defect" in (r["notes"] or "")}
    assert flagged == {n for n in all_rows if "FY2022-23_Standalone" in n}
    fy24 = next(rs for n, rs in all_rows.items() if "FY2023-24_Standalone" in n)
    op = next(r for r in fy24 if r["proposed_line_code"] == "CF.CCE_OPEN")
    assert op["value_inr_cr"] == pytest.approx(77.19)


@needs_files
def test_segment_assets_instant_and_paid_up_code(all_rows):
    rows = [r for rs in all_rows.values() for r in rs]
    seg_assets = [r for r in rows if r["xbrl_tag"] == "SegmentAssets"]
    assert seg_assets and all(r["period_type"] == "instant" for r in seg_assets)
    paid = [r for r in rows if r["xbrl_tag"] == "PaidUpValueOfEquityShareCapital"]
    assert paid and all(r["proposed_line_code"] == "OTH.PAID_UP_CAPITAL" for r in paid)


@needs_files
def test_consolidated_pat_includes_nci_note(all_rows):
    rows = [r for rs in all_rows.values() for r in rs if r["proposed_line_code"] == "PL.PAT"]
    for r in rows:
        assert ("includes_nci" in (r["notes"] or "")) == (r["scope"] == "consolidated")
    c24 = next(r for r in rows if r["scope"] == "consolidated" and r["fiscal_year"] == "FY24" and r["context_ref"] == "FourD")
    assert c24["value_inr_cr"] == pytest.approx(57100.84)


@needs_files
def test_restated_delta_size_flag(all_rows):
    pd = pytest.importorskip("pandas")
    if not xbrl.TEN_YEAR.exists():
        pytest.skip("P1.2 ten_year_raw.parquet not built")
    checks = xbrl.cross_check([r for rs in all_rows.values() for r in rs],
                              pd.read_parquet(xbrl.TEN_YEAR).to_dict("records"))
    get = {(c["fiscal_year"], c["xbrl_tag"], c["ten_year_vintage"]): c for c in checks}
    fin20 = get[("FY20", "FinanceCosts", "AR_FY2025-26")]
    assert fin20["delta_pct"] == pytest.approx(14.685, abs=0.01) and fin20["review_flag"] == "P1.6_review_restated_gt_1pct"
    pat19 = get[("FY19", "ProfitLossForPeriod", "AR_FY2025-26")]
    assert pat19["delta_pct"] < 1 and pat19["review_flag"] is None
    assert get[("FY24", "Income", "AR_FY2025-26")]["review_flag"] == "P1.6_conflict_candidate"
    assert all(c["review_flag"] is None for c in checks if c["status"] == "pass")
