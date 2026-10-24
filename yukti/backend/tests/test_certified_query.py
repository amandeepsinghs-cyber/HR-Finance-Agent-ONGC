"""Tests for Phase 1 Certified Query Library and Semantic Router.
Verifies certified template execution, parameter overrides, routing accuracy,
and provenance integrity.
"""

import sys
from pathlib import Path
import pytest

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.router import get_semantic_router
from app.tools.certified_query import (
    get_certified_entry,
    list_certified_queries,
    run_certified_query,
)


def test_certified_library_loading():
    """Verifies that all 89 certified root queries are loaded with parameters and provenance."""
    queries = list_certified_queries()
    assert len(queries) == 101, f"Expected 101 queries, found {len(queries)}"

    entry_c1 = get_certified_entry("C1")
    assert entry_c1 is not None
    assert entry_c1["id"] == "C1"
    assert "wc_id" in entry_c1["params"]
    assert "min_stay_months" in entry_c1["params"]
    assert entry_c1["provenance"]["source_file"] == "data_bank/answer_key/sql/C1.sql"
    assert len(entry_c1["provenance"]["sha256"]) == 64


def test_certified_c1_execution():
    """Verifies C1 execution returns exact ground truth of 419 executives in Delhi."""
    res = run_certified_query("C1")
    assert res.get("type") == "certified_query_result"
    assert res.get("query_id") == "C1"
    assert res.get("row_count") == 71

    # Total executives should be exactly 419
    total_execs = sum(r.get("delhi_executives_ge_5yr", 0) for r in res.get("rows", []))
    assert total_execs == 419


def test_certified_c6_execution():
    """Verifies C6 execution returns Champang as the sole loss-making field in FY26."""
    res = run_certified_query("C6")
    assert res.get("type") == "certified_query_result"
    assert res.get("query_id") == "C6"
    assert res.get("row_count") == 53

    loss_fields = [r["field_name"] for r in res.get("rows", []) if r.get("is_loss_making")]
    assert loss_fields == ["Champang"], f"Expected only Champang loss-making, got: {loss_fields}"


def test_certified_parameter_override():
    """Verifies that parameter overrides work dynamically on certified queries."""
    # Test overriding fiscal_year to FY25 on C6
    res_fy25 = run_certified_query("C6", params={"fiscal_year": "FY25"})
    assert res_fy25.get("type") == "certified_query_result"
    assert res_fy25.get("params_applied", {}).get("fiscal_year") == "FY25"


def test_semantic_router_canonical_match():
    """Verifies that canonical questions route above threshold to certified queries."""
    router = get_semantic_router()
    decision = router.route("How many executives have been posted in the Delhi office for 5 years or more?")
    assert decision["route"] == "certified"
    assert decision["query_id"] == "C1"
    assert decision["score"] >= 0.70
    assert decision["extracted_params"].get("wc_id") == "WC-DEL"


def test_semantic_router_novel_prompt_fallback():
    """Verifies that an out-of-distribution exploratory prompt routes to live_nl_sql."""
    router = get_semantic_router()
    decision = router.route("What would happen to deepwater exploration if Brent rises to $150 and rig rates triple in 2035?")
    # Below threshold -> live_nl_sql
    assert decision["route"] == "live_nl_sql"
    assert decision["query_id"] is None
