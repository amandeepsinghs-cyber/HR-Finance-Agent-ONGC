"""Tests for the AR 10-year table parser (P1.2). Offline: reads the checked-in AR text files."""
from __future__ import annotations

import pytest

from financial_ssot.common import numbers, pages
from financial_ssot.extract import ten_year as ty

AR26 = ty.TEXT_DIR / "ONGC_AR_FY2025-26.txt"
AR24 = ty.TEXT_DIR / "ONGC_AR_FY2023-24.txt"
AR22 = ty.TEXT_DIR / "ONGC_AR_FY2021-22.txt"


@pytest.fixture(scope="module")
def editions():
    by_ed, checks = ty.run_all()
    return by_ed, checks


def _get(rows, label, fy):
    hits = [r for r in rows if r["raw_label"] == label and r["fiscal_year"] == fy]
    assert len(hits) == 1, (label, fy, [(h["source_text_line"], h["parsed_value"]) for h in hits])
    return hits[0]


# ---------------------------------------------------------------- numbers / pages
@pytest.mark.parametrize("tok, expected", [
    ("1,325,081", (1325081.0, False, None)),
    ("(7,720)", (-7720.0, False, None)),
    ("-", (0.0, True, None)),
    ("1.66 : 1", (1.66, False, "ratio")),
    ("1.55:1", (1.55, False, "ratio")),
    ("20.9", (20.9, False, None)),
    ("17,988)", (-17988.0, False, None)),
    ("6,38,289.71", (638289.71, False, None)),
])
def test_parse_token(tok, expected):
    assert numbers.parse_token(tok) == expected


def test_parse_token_rejects_words():
    with pytest.raises(ValueError):
        numbers.parse_token("Overview")


def test_pages_and_folio():
    assert pages.page_of_line(AR26, 967) == 23  # Revenue from Operations
    assert pages.page_of_line(AR26, 1019) == 24  # "\fParticulars ..." starts PDF p.24
    assert pages.page_of_line(AR26, 1051) == 24  # Number of Employees
    assert pages.folio(AR26, 23) == "21"  # SPEC-01 §4.1: PDF p.23 = printed p.21
    assert pages.page_of_line(AR24, 881) == 23 and pages.folio(AR24, 23) == "21"


# ---------------------------------------------------------------- packet §6 examples
@pytest.mark.parametrize("label, fy, value, unit, extra", [
    ("Revenue from Operations", "FY26", 1325081, "INR_mn", {"source_page": 23, "source_text_line": 967}),
    ("Profit after Tax (PAT)", "FY26", 328940, "INR_mn", {"is_restated": False}),
    ("Profit after Tax (PAT)", "FY19", 267646, "INR_mn", {"is_restated": True, "column_header": "2018-19*"}),
    ("Royalty", "FY17", 115748, "INR_mn", {"parent_label": "Statutory Levies:"}),
    ("Other Expenses^", "FY24", -7720, "INR_mn", {}),
    ("Number of Employees", "FY26", 23117, "count", {"source_page": 24}),
    ("Return on Capital Employed (%) (ROCE)", "FY23", 39.82, "pct", {"is_restated": True}),
    ("Return on Capital Employed (%) (ROCE) -incl. exceptional items", "FY23", 33.84, "pct", {}),
    ("Current Ratio", "FY26", 1.66, "ratio", {}),
    ("Current Ratio", "FY17", 1.55, "ratio", {}),
    ("Earning Per Share (`)", "FY26", 26.15, "INR_per_share", {}),
    ("Exceptional items- Income (Expenses)", "FY24", 0, "INR_mn", {"is_nil": True}),
    ("Crude Oil (MMT)", "FY26", 18.79, "MMT", {"block": "physical"}),
    ("Natural Gas (BCM)", "FY26", 15.491, "BCM", {}),
    ("Value Added Product (kT)#", "FY26", 2468, "kT", {}),
    ("Debtors Turnover Ratio (Days)", "FY26", 32, "days", {}),
    ("Profit Before Interest, Depreciation & Tax (PBIDT)", "FY26", 720780, "INR_mn", {}),
    ("Depreciation, Depletion, Amortisation and Impairment", "FY26", 251338, "INR_mn", {}),
    ("Capital Employed", "FY17", 1185309, "INR_mn", {"block": "other_information"}),
])
def test_ar26_examples(editions, label, fy, value, unit, extra):
    r = _get(editions[0]["AR_FY2025-26"], label, fy)
    assert r["parsed_value"] == pytest.approx(value)
    assert r["unit"] == unit
    for k, v in extra.items():
        assert r[k] == v, (k, r[k], v)


def test_schema_keys(editions):
    r = editions[0]["AR_FY2025-26"][0]
    bronze = {"extract_id", "source_system", "source_doc", "source_page", "source_text_line", "raw_label",
              "raw_value_text", "parsed_value", "unit", "column_header", "scope", "statement_guess",
              "extractor_version", "extracted_at"}
    assert bronze | {"fiscal_year", "is_restated", "parent_label", "block"} <= set(r)
    assert r["block"] in {"physical", "financial_value", "financial_strength", "other_information", "ratio"}


def test_restated_columns(editions):
    for ed, marked in [("AR_FY2025-26", {"FY23", "FY20", "FY19"}),
                       ("AR_FY2023-24", {"FY23", "FY20", "FY19", "FY16"}),
                       ("AR_FY2021-22", {"FY20", "FY19", "FY16"})]:
        got = {r["fiscal_year"] for r in editions[0][ed] if r["is_restated"]}
        assert got == marked, ed


# ---------------------------------------------------------------- coverage
@pytest.mark.parametrize("ed, min_labels, fys", [
    ("AR_FY2025-26", 70, [f"FY{y}" for y in range(17, 27)]),
    ("AR_FY2023-24", 60, [f"FY{y}" for y in range(15, 25)]),
    ("AR_FY2021-22", 60, [f"FY{y}" for y in range(13, 23)]),
])
def test_coverage(editions, ed, min_labels, fys):
    rows = editions[0][ed]
    lines = {}
    for r in rows:
        lines.setdefault(r["source_text_line"], set()).add(r["fiscal_year"])
    full = [ln for ln, s in lines.items() if s == set(fys)]
    assert sorted({r["fiscal_year"] for r in rows}) == sorted(fys)
    assert len(full) >= min_labels, (ed, len(full))


# ---------------------------------------------------------------- MANIFEST_v3 §3 own-year values
OWN_YEAR = [  # (label in AR26, FY, own-year AR value ₹ mn)
    ("Revenue from Operations", "FY17", 779077.30), ("Revenue from Operations", "FY18", 850041.00),
    ("Revenue from Operations", "FY19", 1096545.50),
    ("Profit before Tax (PBT)", "FY17", 252155.13), ("Profit before Tax (PBT)", "FY18", 288924.74),
    ("Profit before Tax (PBT)", "FY19", 399540.25),
    ("Profit after Tax (PAT)", "FY17", 178999.77), ("Profit after Tax (PAT)", "FY18", 199452.60),
    ("Profit after Tax (PAT)", "FY19", 267157.89),
    ("Total Equity (Net Worth)", "FY17", 1855383.80), ("Total Equity (Net Worth)", "FY18", 1933846.81),
    ("Total Equity (Net Worth)", "FY19", 2029925.55),
]


@pytest.mark.parametrize("label, fy, own", OWN_YEAR)
def test_manifest_own_year(editions, label, fy, own):
    r = _get(editions[0]["AR_FY2025-26"], label, fy)
    assert abs(r["parsed_value"] - own) <= 1 or r["is_restated"], (label, fy, r["parsed_value"], own)


# ---------------------------------------------------------------- V09 cross-edition
def test_cross_check_threshold(editions):
    checks = editions[1]
    assert len(checks) > 500
    passed = sum(c["passed"] for c in checks)
    assert passed / len(checks) >= 0.95
    known = {(c["label"], c["fy"], c["vintage_a"], c["vintage_b"]) for c in KNOWN_UNFLAGGED_FAILURES}
    for c in checks:
        if not c["passed"] and not c["later_marked_restated"]:
            assert (c["label"], c["fy"], c["vintage_a"], c["vintage_b"]) in known, c


def test_known_restatement_fy24_other_income(editions):
    """SPEC-01 §6: AR FY24 other non-operating income 73,479 vs 73,052 in AR FY26 (reclassified)."""
    c = [c for c in editions[1] if c["label"] == "other non operating income" and c["fy"] == "FY24"]
    assert len(c) == 1 and c[0]["value_a"] == 73052 and c[0]["value_b"] == 73479 and not c[0]["passed"]


def test_total_expenses_definition_break(editions):
    """AR FY26 'Total Expenses' excludes DD&A; AR FY24 includes it (so the pair is never compared).

    Identity holds to the ₹ mn for FY17-FY23; FY24 differs by the 427 ₹ mn reclassification.
    """
    a26, a24 = editions[0]["AR_FY2025-26"], editions[0]["AR_FY2023-24"]
    for y in range(17, 25):
        fy = f"FY{y}"
        te26 = _get(a26, "Total Expenses", fy)["parsed_value"]
        dda26 = _get(a26, "Depreciation, Depletion, Amortisation and Impairment", fy)["parsed_value"]
        te24 = _get(a24, "Total Expenses", fy)["parsed_value"]
        assert te24 - (te26 + dda26) == (427 if fy == "FY24" else 0), fy


# Unflagged failures (later edition has no "*"), each explained in docs/reviews/P1.2_evidence.md §4:
# the FY24 427 ₹ mn reclassification between other income and provisions (SPEC-01 §6 V07 fixture).
KNOWN_UNFLAGGED_FAILURES: list[dict] = [
    {"label": lab, "fy": "FY24", "vintage_a": "AR_FY2025-26", "vintage_b": "AR_FY2023-24"}
    for lab in ("other non operating income", "total income", "provisions and write offs")
]
