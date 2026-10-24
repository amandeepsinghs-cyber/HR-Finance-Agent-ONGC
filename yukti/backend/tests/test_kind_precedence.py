"""P4.1 Backend Tests: Chart-Kind Precedence (30/30 Shared Fixture) & Zero Synthesis Guard.

Covers SPEC-09 §4.4, BUG-09, and BUG-22.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
YUKTI_ROOT = BACKEND_ROOT.parent
CONTRACTS_DIR = YUKTI_ROOT / "contracts"
PRECEDENCE_FIXTURE = CONTRACTS_DIR / "fixtures" / "kind_precedence_30.json"

sys.path.insert(0, str(BACKEND_ROOT))

from app.brain.chart_rules import (  # noqa: E402
    build_chart_spec,
    extract_requested_chart_kind,
    is_pbt_column,
    is_pure_replot_request,
    resolve_kind,
    select_chart_kind,
)


def _load_precedence_cases() -> List[Dict[str, Any]]:
    with PRECEDENCE_FIXTURE.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data["cases"]


_CASES = _load_precedence_cases()


def test_precedence_fixture_has_30_cases() -> None:
    assert len(_CASES) == 30


@pytest.mark.parametrize("case", _CASES, ids=[c["id"] for c in _CASES])
def test_kind_precedence_30_utterances(case: Dict[str, Any]) -> None:
    utterance = case["utterance"]
    expected = case["expected_kind"]

    assert resolve_kind(utterance) == expected, (
        f"{case['id']} ({utterance!r}): expected {expected!r}, got {resolve_kind(utterance)!r}"
    )
    assert extract_requested_chart_kind(utterance) == expected

    # Verify select_chart_kind honors utterance precedence even when rows look like time-series or revenue+profit
    sample_rows = [
        {"fiscal_year": "FY24", "revenue_cr": 138402.13, "profit_cr": 40525.96},
        {"fiscal_year": "FY25", "revenue_cr": 137846.29, "profit_cr": 36236.20},
    ]
    selected = select_chart_kind(
        columns=["fiscal_year", "revenue_cr", "profit_cr"],
        rows=sample_rows,
        utterance=utterance,
    )
    assert selected == expected


def test_pbt_regex_never_matches_pat_or_generic_profit() -> None:
    assert is_pbt_column("pbt_cr") is True
    assert is_pbt_column("pbt_inr_cr") is True
    assert is_pbt_column("profit_before_tax_cr") is True
    assert is_pbt_column("Profit Before Tax") is True

    assert is_pbt_column("pat_cr") is False
    assert is_pbt_column("pat_inr_cr") is False
    assert is_pbt_column("profit_after_tax") is False
    assert is_pbt_column("net_profit_cr") is False
    assert is_pbt_column("profit_cr") is False
    assert is_pbt_column("profit") is False


def test_no_ebitda_or_opex_synthesis_in_chart_rules() -> None:
    """P4.1.md §8 Check 2: grep finds 0 matches for 0.68 / rev*0. / (rev+pbt)/2 in chart_rules.py."""
    synth_re = re.compile(r"0\.68|rev\s*\*\s*0\.|\(rev\s*\+\s*pbt\)\s*/\s*2|OPEX\s*&\s*Levies")
    for rel in ("app/brain/chart_rules.py", "app/tools/chart_rules.py"):
        src = (BACKEND_ROOT / rel).read_text(encoding="utf-8")
        hits = synth_re.findall(src)
        assert hits == [], f"Forbidden synthesis pattern in {rel}: {hits}"

    # Verify runtime behavior on a 1-row asset table with revenue and PBT
    spec = build_chart_spec(
        kind="waterfall",
        columns=["asset", "revenue_cr", "pbt_cr"],
        rows=[{"asset": "Ankleshwar", "revenue_cr": 3098.48, "pbt_cr": 1412.10}],
    )
    labels = [str(r.get("metric") or r.get("step") or "") for r in spec.get("data", [])]
    assert not any("ebitda" in lbl.lower() or "opex" in lbl.lower() or "dd&a" in lbl.lower() for lbl in labels)


@pytest.mark.parametrize(
    "utterance,expected_kind",
    [
        ("Can you express it as a waterfall?", "waterfall"),
        ("इसे वॉटरफॉल में दिखाओ", "waterfall"),
        ("इसे कॉलम चार्ट में दिखाओ", "bar"),
        ("इसे टेबल में दिखाओ", "table"),
        ("एसेट डेटा को पाई चार्ट में दिखाओ", "pie"),
        ("एसेट डेटा को डोनट चार्ट में बदलो", "donut"),
    ],
)
def test_bilingual_replot_detection(utterance: str, expected_kind: str) -> None:
    is_rep, kind = is_pure_replot_request(utterance)
    assert is_rep is True
    assert kind == expected_kind
