import pytest
import sys
try:
    from app.coverage.manifest import get_coverage_manifest
    from app.intents.coverage import handle_coverage_query, is_coverage_query
except ImportError:
    from yukti.backend.app.coverage.manifest import get_coverage_manifest
    from yukti.backend.app.intents.coverage import handle_coverage_query, is_coverage_query

class MockGenaiModule:
    def __getattr__(self, name):
        raise RuntimeError("LLM should not be called for deterministic intents")

@pytest.fixture
def no_llm(monkeypatch):
    monkeypatch.setitem(sys.modules, "google.genai", MockGenaiModule())
    monkeypatch.setitem(sys.modules, "vertexai", MockGenaiModule())
    monkeypatch.setitem(sys.modules, "google.generativeai", MockGenaiModule())

def test_coverage_manifest_contains_fy17_fy26():
    manifest = get_coverage_manifest()
    
    statements = {f.statement: f for f in manifest.finance}
    
    for stmt in ["balance_sheet", "profit_and_loss", "cash_flow", "ratios"]:
        assert stmt in statements
        assert statements[stmt].fy_min == "FY17"
        assert statements[stmt].fy_max == "FY26"

def test_f47_general_coverage(no_llm):
    contract = handle_coverage_query("What data do you have?")
    assert contract["intent"] == "coverage"
    assert contract["confidence"] == "high"
    assert contract["visual"]["type"] == "table"
    assert "FY17" in contract["spoken_summary"]
    assert "FY26" in contract["spoken_summary"]
    assert contract["provenance"]["source_class"] == "coverage_manifest"

def test_f48_specific_coverage(no_llm):
    queries = [
        "Do you have the balance sheet for 2024?",
        "when you say upto 2026, 2024 is before 2026?"
    ]
    
    for query in queries:
        contract = handle_coverage_query(query)
        assert contract["intent"] == "coverage"
        assert "FY 2023-24 (FY24) is available" in contract["spoken_summary"]
        assert contract["visual"]["type"] == "table"
        assert len(contract["clarify"]) > 0
        assert contract["clarify"][0]["action"] == "drilldown"
