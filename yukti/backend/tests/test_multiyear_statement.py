import pytest
import os
from app.brain.compiler import Compiler
from app.brain.query_spec import QuerySpec, Filter
from app.brain.presenter import build_visual

@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    monkeypatch.setenv("YUKTI_CONTRACT_V3_FIELDS", "statement")
    monkeypatch.setenv("YUKTI_FIN_SSOT_V3", "1")

def test_multiyear_pnl_statement():
    spec = QuerySpec(
        metric="pnl_statement",
        period=None,
        filters=[
            Filter(field="scope", op="=", value="standalone"),
            Filter(field="fiscal_year", op="between", value=["FY24", "FY26"])
        ]
    )
    
    compiler = Compiler()
    compiled = compiler.compile(spec)
    
    rows = [
        {"fiscal_year": "FY26", "line_code": "PL.REV_OPS", "amount_cr": 1000},
        {"fiscal_year": "FY25", "line_code": "PL.REV_OPS", "amount_cr": 900},
        {"fiscal_year": "FY26", "line_code": "PL.PAT", "amount_cr": 100},
        {"fiscal_year": "FY25", "line_code": "PL.PAT", "amount_cr": 90},
    ]
    
    vis = build_visual(
        spec=spec,
        compiled=compiled,
        columns=["fiscal_year", "line_code", "amount_cr"],
        rows=rows,
        chart_kind=None,
        title="P&L",
        subtitle="",
        mode="test"
    )
    
    assert vis["type"] == "statement"
    assert "statement" in vis
    st = vis["statement"]
    assert st["statement"] == "pnl"
    assert "FY26" in st["periods"]
    assert "FY25" in st["periods"]
