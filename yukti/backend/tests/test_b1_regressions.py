"""Unit tests for B1 regressions (Task Packet B1.3 §5.4)."""

from pathlib import Path
import sys
import pytest

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.turn_runner import AgentTurnRunner, make_clean_title_and_subtitle
from app.tools.chart_rules import select_chart_kind


def test_title_and_subtitle_b1_2_mumbai():
    title, subtitle = make_clean_title_and_subtitle("Mumbai mein 5 saal se zyada kitne executives hain?")
    assert title.startswith("Mumbai: Executives with ≥5 Years' Continuous Stay")
    assert "Mumbai High Asset" in subtitle
    assert "RO Mumbai" in subtitle
    assert "WC-" not in title
    assert "WC-" not in subtitle


def test_title_and_subtitle_b1_2_tripura_params():
    title, subtitle = make_clean_title_and_subtitle("executives with long stay", params={"wc_id": "WC-TRI"})
    assert title.startswith("Tripura Asset:")
    assert "Station Category C" in subtitle
    assert "WC-" not in title
    assert "WC-" not in subtitle


def test_index_error_regression_gate_u0():
    assert select_chart_kind(columns=[], rows=[]) == "table"
    assert select_chart_kind(columns=["a"], rows=[]) == "table"


def test_answer_cache_poisoning_audit_2_6():
    route = {
        "query_id": "C1",
        "extracted_params": {"wc_id": "WC-DEL", "min_stay_months": 60},
    }

    # 1. certified C1 response with params_applied={"wc_id":"WC-DEL","min_stay_months":60}, row_count=71 -> True
    resp_valid = [
        {
            "name": "run_certified_query",
            "response": {
                "query_id": "C1",
                "params_applied": {"wc_id": "WC-DEL", "min_stay_months": 60},
                "row_count": 71,
                "rows": [{"dummy": 1}],
            },
        }
    ]
    assert AgentTurnRunner._answer_is_cacheable(route, resp_valid) is True

    # 2. same but params_applied={"wc_id":"WC-MUM", ...} -> False
    resp_wrong_params = [
        {
            "name": "run_certified_query",
            "response": {
                "query_id": "C1",
                "params_applied": {"wc_id": "WC-MUM", "min_stay_months": 60},
                "row_count": 71,
                "rows": [{"dummy": 1}],
            },
        }
    ]
    assert AgentTurnRunner._answer_is_cacheable(route, resp_wrong_params) is False

    # 3. only a query_data response -> False
    resp_only_query_data = [
        {
            "name": "query_data",
            "response": {
                "query_id": "C1",
                "params_applied": {"wc_id": "WC-DEL", "min_stay_months": 60},
                "row_count": 71,
                "rows": [{"dummy": 1}],
            },
        }
    ]
    assert AgentTurnRunner._answer_is_cacheable(route, resp_only_query_data) is False

    # 4. certified C6 response -> False
    resp_wrong_qid = [
        {
            "name": "run_certified_query",
            "response": {
                "query_id": "C6",
                "params_applied": {"wc_id": "WC-DEL", "min_stay_months": 60},
                "row_count": 71,
                "rows": [{"dummy": 1}],
            },
        }
    ]
    assert AgentTurnRunner._answer_is_cacheable(route, resp_wrong_qid) is False

    # 5. certified C1 with row_count=0 and rows=[] -> False
    resp_empty_rows = [
        {
            "name": "run_certified_query",
            "response": {
                "query_id": "C1",
                "params_applied": {"wc_id": "WC-DEL", "min_stay_months": 60},
                "row_count": 0,
                "rows": [],
            },
        }
    ]
    assert AgentTurnRunner._answer_is_cacheable(route, resp_empty_rows) is False

    # 6. empty responses list -> False
    assert AgentTurnRunner._answer_is_cacheable(route, []) is False


def test_no_duplicate_maps():
    base_dir = Path(__file__).resolve().parent.parent
    files_to_check = [
        base_dir / "app" / "router.py",
        base_dir / "app" / "session_memory.py",
        base_dir / "app" / "turn_runner.py",
        base_dir / "app" / "tools" / "query_data.py",
        base_dir / "app" / "tools" / "certified_query.py",
    ]
    banned_tokens = [
        "WC_SYNONYMS = {",
        "WC_NAME_MAP",
        "FRIENDLY_NAMES = {",
        "DISCIPLINE_NAMES = {",
        "WORK_CENTRE_NAMES = {",
        "FY_SYNONYMS = {",
    ]
    for file_path in files_to_check:
        assert file_path.exists(), f"Target file does not exist: {file_path}"
        source_text = file_path.read_text(encoding="utf-8")
        for banned in banned_tokens:
            assert banned not in source_text, f"Found deprecated duplicate map token '{banned}' in {file_path}"


# ---------------------------------------------------------------------------
# G4 B1 review r1 regressions (added by Opus)
# ---------------------------------------------------------------------------
def test_normaliser_runs_in_live_query_path():
    """F-1: apply_query_craft_rules must case-correct literals for bare and qualified table names."""
    from app.tools.semantic_layer import SemanticLayer
    sl = SemanticLayer()
    for sql in (
        "SELECT COUNT(*) FROM hrfin_gold.ssot_workforce_employee WHERE employment_status = 'active'",
        "SELECT COUNT(*) FROM `ongc-hr-finance-agent`.hrfin_gold.ssot_workforce_employee WHERE employment_status = 'active'",
        "SELECT COUNT(*) FROM `ongc-hr-finance-agent.hrfin_gold.ssot_workforce_employee` WHERE employment_status = 'active'",
    ):
        out = sl.apply_query_craft_rules(sql)
        assert "employment_status = 'Active'" in out, out


def test_in_rewrite_guards_foreign_functions_and_lowers_literals():
    from app.semantic.normalize import normalize_categorical_filters as norm
    cat = {"tables": {"hrfin_gold.ssot_workforce_employee": {"columns": {
        "cadre": {"type": "STRING", "values": ["executive", "non_executive", "board"]}}}}}
    base = "SELECT 1 FROM hrfin_gold.ssot_workforce_employee WHERE "
    s1 = base + "UPPER(cadre) IN ('EXECUTIVE')"
    assert norm(s1, cat) == s1  # untouched, no dropped parenthesis
    assert "LOWER(cadre) IN ('executive')" in norm(base + "LOWER(cadre) IN ('Executive')", cat)


def test_fy_dash_forms_and_over_n_years():
    from app.semantic.normalize import resolve_fy
    assert resolve_fy("revenue FY24-25") == {"fy": "FY25"}
    assert resolve_fy("fy 24-25 opex") == {"fy": "FY25"}
    assert resolve_fy("as of 2026-10-19, compare 2024-25") == {"fy": "FY25"}
    assert resolve_fy("officers posted over 5 years in Delhi") is None
    assert resolve_fy("over the last 5 years") == {"from": "FY22", "to": "FY26", "n_years": 5}


def test_western_offshore_is_a_region_not_the_basin_office():
    from app.semantic.entities import get_entities
    e = get_entities()
    assert e.resolve_wc("Western Offshore vacancies") is None
    name, codes = e.resolve_region("Western Offshore vacancies")
    assert name == "western offshore" and set(codes) == {"WC-MUM", "WC-NEH", "WC-BAS"}
    assert e.resolve_wc("Western Offshore Basin office") == "WC-WOB"


def test_devanagari_alias_has_word_boundary():
    from app.semantic.entities import get_entities
    e = get_entities()
    assert e.resolve_wc("असम में कर्मचारी") == "WC-ASM"
    assert e.resolve_wc("असमानता पर रिपोर्ट") is None
