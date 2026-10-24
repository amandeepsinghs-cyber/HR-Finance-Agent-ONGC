"""Unit tests for the top-5 action generator and safe expr evaluator (P2F.6, SPEC-08 §7)."""

from pathlib import Path
import sys

# Ensure yukti/backend is on sys.path regardless of execution cwd
_backend_dir = Path(__file__).resolve().parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

import jsonschema
import pandas as pd
import pytest

from app.agents.fin_diagnostics.actions import generate_actions
from app.agents.fin_diagnostics.expr import ExprError, evaluate

FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEN_YEAR_CSV = FIXTURES_DIR / "ten_year_fy25_fy26.csv"
LEVERS_FIXTURE_YAML = FIXTURES_DIR / "levers_fixture.yaml"
FULL_LEVERS_YAML = _backend_dir / "app" / "agents" / "fin_diagnostics" / "levers.yaml"

SPEC08_ACTIONS_SCHEMA = {
    "type": "object",
    "required": ["fy", "items", "delegation_table"],
    "properties": {
        "fy": {"type": "string"},
        "note": {"type": "string"},
        "items": {
            "type": "array",
            "maxItems": 5,
            "items": {
                "type": "object",
                "required": [
                    "rank",
                    "lever_id",
                    "title",
                    "what_to_do",
                    "impact",
                    "owner",
                    "kpi",
                    "evidence",
                    "confidence",
                ],
                "properties": {
                    "rank": {"type": "integer"},
                    "lever_id": {"type": "string"},
                    "title": {"type": "string"},
                    "what_to_do": {"type": "string"},
                    "impact": {
                        "type": "object",
                        "required": ["low", "mid", "high", "unit", "kind", "label"],
                        "properties": {
                            "low": {"type": "number"},
                            "mid": {"type": "number"},
                            "high": {"type": "number"},
                            "unit": {"const": "INR_cr"},
                            "kind": {"enum": ["one_off", "annual"]},
                            "label": {"const": "Modelled estimate"},
                        },
                    },
                    "owner": {"enum": ["CMD", "DIR_FIN", "DIR_HR", "for discussion"]},
                    "horizon_days": {"enum": [30, 90, 180]},
                    "kpi": {"type": "string"},
                    "evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["type", "ref"],
                            "properties": {
                                "type": {"enum": ["data", "ar"]},
                                "ref": {"type": "string"},
                            },
                        },
                    },
                    "confidence": {"type": "number"},
                },
            },
        },
        "delegation_table": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["owner", "ask", "by_when", "kpi", "evidence"],
                "properties": {
                    "owner": {"type": "string"},
                    "ask": {"type": "string"},
                    "by_when": {"type": "string"},
                    "kpi": {"type": "string"},
                    "evidence": {"type": "string"},
                },
            },
        },
    },
}


@pytest.fixture
def df_full_suite() -> pd.DataFrame:
    """Load base fixture and augment with debtor days and multi-year rows."""
    base_df = pd.read_csv(TEN_YEAR_CSV)

    extra_rows = [
        # Debtor days (L02)
        {"line_code": "RATIO.DEBTOR_DAYS", "fiscal_year": "FY25", "value_inr_cr": 29.0, "source_doc": "AR_FY26", "source_page_label": "p.22"},
        {"line_code": "RATIO.DEBTOR_DAYS", "fiscal_year": "FY26", "value_inr_cr": 32.0, "source_doc": "AR_FY26", "source_page_label": "p.22"},
        # Employee benefit (L07)
        {"line_code": "PL.EMP_BENEFIT", "fiscal_year": "FY25", "value_inr_cr": 10000.0, "source_doc": "AR_FY26", "source_page_label": "p.23"},
        {"line_code": "PL.EMP_BENEFIT", "fiscal_year": "FY26", "value_inr_cr": 10720.5, "source_doc": "AR_FY26", "source_page_label": "p.23"},
        # Multi-year exploratory wells (L06)
        {"line_code": "PL.EXPL_WELL", "fiscal_year": "FY22", "value_inr_cr": 5000.0, "source_doc": "AR_FY26", "source_page_label": "p.24"},
        {"line_code": "PL.EXPL_WELL", "fiscal_year": "FY23", "value_inr_cr": 5500.0, "source_doc": "AR_FY26", "source_page_label": "p.24"},
        {"line_code": "PL.EXPL_WELL", "fiscal_year": "FY24", "value_inr_cr": 6000.0, "source_doc": "AR_FY26", "source_page_label": "p.24"},
    ]

    extra_df = pd.DataFrame(extra_rows)
    return pd.concat([base_df, extra_df], ignore_index=True)


# ---------------------------------------------------------------------------
# 1. expr.py unit tests (acceptance criteria: math, security rejections, window)
# ---------------------------------------------------------------------------

def test_expr_safe_evaluation():
    """Assert arithmetic, comparison, logic and math built-ins evaluate correctly."""
    assert evaluate("10 + 20 * 2") == 50
    assert evaluate("(10 + 20) * 2") == 60
    assert evaluate("100 / 4 - 5") == 20.0
    assert evaluate("10 > 5 and 5 < 8") is True
    assert evaluate("not (10 == 20)") is True
    assert evaluate("abs(-45.5)") == 45.5
    assert evaluate("min(10, 20, 5)") == 5
    assert evaluate("max(10, 20, 5)") == 20


def test_expr_security_rejections():
    """Assert expr.py strictly rejects attribute access, unwhitelisted calls, and unknown names."""
    # Attribute access
    class Dummy:
        attr = "val"

    with pytest.raises(ExprError):
        evaluate("obj.attr", {"obj": Dummy()})

    with pytest.raises(ExprError):
        evaluate("os.system('rm -rf /')", {})

    with pytest.raises(ExprError):
        evaluate("'hello'.upper()", {})

    # Unwhitelisted function calls
    with pytest.raises(ExprError):
        evaluate("eval('1 + 1')", {})

    with pytest.raises(ExprError):
        evaluate("exec('x = 1')", {})

    with pytest.raises(ExprError):
        evaluate("open('/etc/passwd')", {})

    with pytest.raises(ExprError):
        evaluate("__import__('os')", {})

    # Unknown names
    with pytest.raises(ExprError):
        evaluate("undeclared_var + 10", {"declared_var": 5})


def test_expr_history_functions():
    """Assert prior, yoy, avg5, median5 evaluate historical windows correctly."""
    history = {
        "FY26": {"VAL": 120.0},
        "FY25": {"VAL": 100.0},
        "FY24": {"VAL": 80.0},
        "FY23": {"VAL": 60.0},
        "FY22": {"VAL": 40.0},
    }

    def hist_fn(y):
        return history.get(y, {})

    ctx = {"VAL": 120.0}
    inputs = ["VAL"]

    # prior(VAL) = 100.0
    assert evaluate("prior(VAL)", ctx, history_fn=hist_fn, current_fy="FY26", inputs=inputs) == 100.0

    # yoy(VAL) = (120 - 100) / 100 = 0.20
    assert evaluate("yoy(VAL)", ctx, history_fn=hist_fn, current_fy="FY26", inputs=inputs) == pytest.approx(0.20)

    # avg5(VAL) = (120 + 100 + 80 + 60 + 40) / 5 = 80.0
    assert evaluate("avg5(VAL)", ctx, history_fn=hist_fn, current_fy="FY26", inputs=inputs) == pytest.approx(80.0)

    # median5(VAL) = 80.0
    assert evaluate("median5(VAL)", ctx, history_fn=hist_fn, current_fy="FY26", inputs=inputs) == pytest.approx(80.0)


# ---------------------------------------------------------------------------
# 2. Lever Evaluation Tests (packet §6 examples and triggers)
# ---------------------------------------------------------------------------

def test_l02_l08_l09_fire_fy26(df_full_suite: pd.DataFrame):
    """Assert L02, L08, L09 fire with exact values from packet §6."""
    res = generate_actions(df_full_suite, "FY26", persona="CMD", levers_path=FULL_LEVERS_YAML)
    by_id = {item["lever_id"]: item for item in res["items"]}

    # L02: debtor days 32 vs 29 -> release = (32 - 29) * 132,508.1 / 365 = ₹1,089.1 cr one-off
    assert "L02" in by_id
    l02 = by_id["L02"]
    assert l02["owner"] == "DIR_FIN"
    assert l02["kpi"] == "Debtor days"
    assert l02["impact"]["kind"] == "one_off"
    assert l02["impact"]["mid"] == pytest.approx(1089.1, abs=0.1)
    assert "Bring debtor days from 32 back to 29" in l02["what_to_do"]

    # L08: exchange loss 2,698.9 vs 767.2 -> fires (> 1,000 and > 2x prior)
    assert "L08" in by_id
    l08 = by_id["L08"]
    assert l08["owner"] == "DIR_FIN"
    assert l08["kpi"] == "FX loss ₹ cr"
    assert l08["confidence"] == pytest.approx(0.70)  # assumption used
    assert l08["impact"]["mid"] == pytest.approx(2698.9 * 0.50, abs=0.1)

    # L09: provisions 3,947.6 vs 2,805.2 (+40.7%) -> fires
    assert "L09" in by_id
    l09 = by_id["L09"]
    assert l09["owner"] == "DIR_FIN"
    assert l09["kpi"] == "Provisions ₹ cr"
    assert l09["impact"]["mid"] == pytest.approx(3947.6 - 2805.2, abs=0.1)


def test_l06_exploration_fires_if_above_avg5(df_full_suite: pd.DataFrame):
    """Assert L06 fires when exploratory wells write-off exceeds 5-year average by > 20% (packet §6)."""
    res = generate_actions(df_full_suite, "FY26", persona="CMD", levers_path=FULL_LEVERS_YAML)
    by_id = {item["lever_id"]: item for item in res["items"]}

    # Wells write-offs FY26 = 8,236.0 vs avg5 (5000+5500+6000+7480+8236)/5 = 6443.2
    # 8236.0 > 1.20 * 6443.2 (7731.8) -> fires
    assert "L06" in by_id
    l06 = by_id["L06"]
    assert l06["owner"] == "CMD"
    assert l06["kpi"] == "Dry-well cost ₹ cr"
    expected_mid = round(8236.0 - 6443.2, 1)
    assert l06["impact"]["mid"] == pytest.approx(expected_mid, abs=0.2)


def test_owner_diversity_rule(df_full_suite: pd.DataFrame):
    """Assert that no single owner receives more than 3 actions in the top-5 (packet §5)."""
    res = generate_actions(df_full_suite, "FY26", persona="CMD", levers_path=FULL_LEVERS_YAML)
    owner_counts = {}
    for item in res["items"]:
        owner = item["owner"]
        owner_counts[owner] = owner_counts.get(owner, 0) + 1

    for owner, count in owner_counts.items():
        assert count <= 3, f"Owner {owner} exceeded max 3 items: got {count}"


def test_dir_hr_persona_includes_l07(df_full_suite: pd.DataFrame):
    """Assert DIR_HR persona always includes L07 when it triggers (packet §5)."""
    res = generate_actions(df_full_suite, "FY26", persona="DIR_HR", levers_path=FULL_LEVERS_YAML)
    lever_ids = [item["lever_id"] for item in res["items"]]
    assert "L07" in lever_ids

    # For DIR_HR, HR levers are presented first
    assert res["items"][0]["lever_id"] == "L07"
    assert res["items"][0]["owner"] == "DIR_HR"


def test_e_level_persona_for_discussion(df_full_suite: pd.DataFrame):
    """Assert E1–E4 personas have owner set to 'for discussion' in items and delegation_table (packet §5)."""
    for persona in ("E1_FIN", "E2_HR", "E4_FIN"):
        res = generate_actions(df_full_suite, "FY26", persona=persona, levers_path=FULL_LEVERS_YAML)
        for item in res["items"]:
            assert item["owner"] == "for discussion"
        for row in res["delegation_table"]:
            assert row["owner"] == "for discussion"


def test_ar_evidence_injection(df_full_suite: pd.DataFrame):
    """Assert ar_evidence_fn stub injects {type: 'ar'} evidence (packet §5)."""
    def stub_ar_fn(lever_id: str, fy: str):
        if lever_id == "L02":
            return [{"ref": "AR FY26 MD&A p.98"}]
        return []

    res = generate_actions(
        df_full_suite,
        "FY26",
        persona="CMD",
        levers_path=FULL_LEVERS_YAML,
        ar_evidence_fn=stub_ar_fn,
    )
    l02 = next(item for item in res["items"] if item["lever_id"] == "L02")
    ar_refs = [e["ref"] for e in l02["evidence"] if e["type"] == "ar"]
    assert "AR FY26 MD&A p.98" in ar_refs


def test_fewer_than_5_note_with_fixture(df_full_suite: pd.DataFrame):
    """Assert note is added when fewer than 5 levers trigger (packet §5, levers_fixture.yaml)."""
    res = generate_actions(df_full_suite, "FY26", persona="CMD", levers_path=LEVERS_FIXTURE_YAML)
    assert len(res["items"]) == 3
    assert res["note"] == "Only 3 levers are triggered by FY26 data"


def test_jsonschema_validation(df_full_suite: pd.DataFrame):
    """Assert generated actions payload strictly conforms to SPEC-08 §7.3 JSON schema."""
    res = generate_actions(df_full_suite, "FY26", persona="CMD", levers_path=FULL_LEVERS_YAML)
    jsonschema.validate(instance=res, schema=SPEC08_ACTIONS_SCHEMA)


def test_determinism(df_full_suite: pd.DataFrame):
    """Assert repeated execution produces byte-identical results (packet §5)."""
    r1 = generate_actions(df_full_suite, "FY26", persona="CMD", levers_path=FULL_LEVERS_YAML)
    r2 = generate_actions(df_full_suite, "FY26", persona="CMD", levers_path=FULL_LEVERS_YAML)
    assert r1 == r2


def test_p2f6_b1_b2_fact_snapshot_real_data():
    """Assert real fact_snapshot.parquet compatibility (P2F6-B1, P2F6-B2)."""
    parquet_path = _backend_dir.parent.parent / "financial_ssot" / "out" / "fact_snapshot.parquet"
    if not parquet_path.exists():
        pytest.skip(f"Parquet {parquet_path} not found")

    df = pd.read_parquet(parquet_path)
    res = generate_actions(df, "FY26", persona="CMD", levers_path=FULL_LEVERS_YAML)
    by_id = {item["lever_id"]: item for item in res["items"]}

    # P2F6-B1: L02 triggers on real parquet with debtor days 32 back to 29 and ~1,089.1 cr impact
    assert "L02" in by_id
    l02 = by_id["L02"]
    assert "32" in l02["what_to_do"] and "29" in l02["what_to_do"]
    assert l02["impact"]["mid"] == pytest.approx(1089.1, abs=1.0)

    # P2F6-B1: L03 triggers with synthesized PROD.TOTAL_BOE (40.5 MMBOE)
    assert "L03" in by_id
    assert "40.5" in by_id["L03"]["what_to_do"]

    # P2F6-B2: Multi-year evidence assertions
    # L06 uses avg5 -> evidence must include all 5 years
    l06 = by_id["L06"]
    l06_evidence_fys = {e["ref"].split()[1] for e in l06["evidence"] if e["type"] == "data"}
    assert {"FY22", "FY23", "FY24", "FY25", "FY26"}.issubset(l06_evidence_fys)

    # L02 uses prior -> evidence must include FY25 and FY26
    l02_evidence_fys = {e["ref"].split()[1] for e in l02["evidence"] if e["type"] == "data"}
    assert {"FY25", "FY26"}.issubset(l02_evidence_fys)


def test_p2f6_b3_expr_call_and_arity_guards():
    """Assert expr.py keyword args, arity guards, _VAR_ check, and package exports (P2F6-B3)."""
    from app.agents.fin_diagnostics import ExprError, evaluate, generate_actions as gen_act

    assert ExprError is not None
    assert evaluate is not None
    assert gen_act is not None

    # Keyword arguments forbidden
    with pytest.raises(ExprError, match="Keyword arguments"):
        evaluate("abs(x=1)")

    # Arity check on prior()
    with pytest.raises(ExprError, match="takes exactly 1 argument"):
        evaluate("prior()")

    # Arity check on yoy()
    with pytest.raises(ExprError, match="takes exactly 1 argument"):
        evaluate("yoy()")

    # Internal _VAR_ prefix forbidden
    with pytest.raises(ExprError, match="_VAR_"):
        evaluate("_VAR_0_ + 1")
