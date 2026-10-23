"""Tests for the AR notes parser (P1.3). Offline: checked-in AR text files."""
from __future__ import annotations

import re

import pytest

from financial_ssot.extract import notes as nt
from financial_ssot.extract import statements as st


@pytest.fixture(scope="module")
def by_vintage():
    pm = st.load_page_map()
    out = {}
    for v in ("AR_FY2024-25", "AR_FY2025-26"):
        rows, issues, found = nt.parse_with_issues(st.TEXT_DIR / pm["editions"][v]["file"], v, pm)
        out[v] = (rows, issues, found)
    return out


def _one(rows, table_rx, label_rx, fy, group=None, unit=None):
    hits = [r for r in rows if re.match(table_rx, r["source_table"]) and re.search(label_rx, r["raw_label"])
            and r["fiscal_year"] == fy and (group is None or r.get("column_group") == group)
            and (unit is None or r["unit"] == unit)]
    assert len(hits) == 1, (table_rx, label_rx, fy, [(h["raw_label"], h["raw_value_text"]) for h in hits])
    return hits[0]


def test_note_numbers_located(by_vintage):
    _, _, f26 = by_vintage["AR_FY2025-26"]
    assert {k: v[0] for k, v in f26.items()} == {
        "revenue": "30", "other_income": "31", "opex": "35", "finance_cost": "36", "dda": "37", "tax": "39",
        "lease": "22", "provisions": "24", "investments": "11", "segment": "44"}
    assert f26["provisions"][1] == 345 and f26["lease"][1] == 344


@pytest.mark.parametrize("fy, lease, decom, fin_total", [
    ("FY26", 15354.99, 30539.42, 45292.61),
    ("FY25", 16351.36, 28987.14, 46039.70),
])
def test_ar26_finance_cost_components(by_vintage, fy, lease, decom, fin_total):
    rows, _, _ = by_vintage["AR_FY2025-26"]
    r = _one(rows, r"note_22_1$", r"^Unwinding of discount on lease liabilities$", fy)
    assert r["parsed_value"] == lease and r["source_page"] == 344
    d = _one(rows, r"note_24", r"^Unwinding of discount$", fy, group="Provision for decommissioning")
    assert d["parsed_value"] == decom and d["source_page"] == 345
    assert _one(rows, r"note_36$", r"^Total$", fy)["parsed_value"] == fin_total


@pytest.mark.parametrize("vintage, fy, shares, amount", [
    ("AR_FY2025-26", "FY26", 1168.27, 369150.00),
    ("AR_FY2025-26", "FY25", 1168.27, 369150.00),
    ("AR_FY2024-25", "FY25", 1168.27, 369150.00),
    ("AR_FY2024-25", "FY24", 778.85, 369150.00),
])
def test_investments_with_shares_held(by_vintage, vintage, fy, shares, amount):
    rows, _, _ = by_vintage[vintage]
    s = _one(rows, r"note_11_1$", r"Hindustan Petroleum", fy, unit="mn_shares")
    assert s["parsed_value"] == shares and s["raw_label"].endswith("[no. of shares, million]")
    assert _one(rows, r"note_11_1$", r"Hindustan Petroleum", fy, unit="INR_mn")["parsed_value"] == amount


def test_ar25_lease_and_decom_present(by_vintage):
    rows, _, _ = by_vintage["AR_FY2024-25"]
    assert _one(rows, r"note_22_1$", r"^Unwinding of discount on lease liabilities$", "FY25")["parsed_value"] == 16351.36
    assert _one(rows, r"note_24", r"^Unwinding of discount$", "FY25",
                group="Provision for decommissioning")["parsed_value"] == 28987.14
    assert _one(rows, r"note_36$", r"^Total$", "FY25")["parsed_value"] == 46039.70


def test_ar26_spec05_anchors(by_vintage):
    rows, _, _ = by_vintage["AR_FY2025-26"]
    assert _one(rows, r"note_35$", r"^Staff Expenditure$", "FY26")["parsed_value"] == 26521.21  # N35.STAFF_EXP
    emp = _one(rows, r"note_35_1$", r"^Sub Total:$", "FY26")  # N351.EMP_TOTAL
    assert (emp["parsed_value"], emp["source_page"]) == (102107.09, 354)
    assert _one(rows, r"note_37$", r"^Total$", "FY26")["parsed_value"] == 251338.23
    imp = _one(rows, r"note_37$", r"Impairment Loss", "FY26")  # N37.IMPAIRMENT_NET (printed block total)
    assert imp["parsed_value"] == -2879.69 and imp["notes"] == "unlabelled_block_subtotal"


@pytest.mark.parametrize("label, group, value", [
    ("Offshore", "Segment revenue", 924063.07),
    ("Onshore", "Segment revenue", 401018.29),
    ("Offshore", "Segment profit/(loss)", 343846.53),
    ("Onshore", "Segment profit/(loss)", 62456.98),
    ("Unallocated corporate expense", "Segment profit/(loss)", -25438.33),
    ("Interest/Dividend income", "Segment profit/(loss)", 88576.32),
])
def test_ar26_segment_44_2(by_vintage, label, group, value):
    rows, _, _ = by_vintage["AR_FY2025-26"]
    r = _one(rows, r"note_44_2$", "^" + re.escape(label), "FY26", group=group)
    assert r["parsed_value"] == value and r["source_page"] == 368


@pytest.mark.parametrize("label, value", [
    ("Crude Oil Production (MMT) [ONGC]", 19.332), ("Crude Oil Production (MMT) [JV share]", 1.170),
    ("Natural Gas Production (BCM) [ONGC]", 19.533), ("Natural Gas Production (BCM) [JV share]", 0.434),
])
def test_ar26_production_table(by_vintage, label, value):
    rows, _, _ = by_vintage["AR_FY2025-26"]
    r = _one(rows, r"production_table$", "^" + re.escape(label) + "$", "FY26")
    assert r["parsed_value"] == value and r["source_page"] == 55 and r["unit"] in ("MMT", "BCM")


def test_note_rows_have_lineage(by_vintage):
    for rows, _, _ in by_vintage.values():
        for r in rows:
            assert r["source_doc"] and r["source_page"] and r["source_text_line"] and r["source_text"]
            assert r["source_table"].startswith(("note_", "production_table"))
            assert r["extraction_method"] == "text_parse"
