import pytest
import os
from app.brain.compiler import Compiler
from app.brain.query_spec import QuerySpec, Filter
from app.brain.presenter import build_visual
from app.brain.query_spec import Period

@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    monkeypatch.setenv("YUKTI_CONTRACT_V3_FIELDS", "statement")
    monkeypatch.setenv("YUKTI_FIN_SSOT_V3", "1")
    monkeypatch.setenv("YUKTI_FORCE_BQ_FAIL", "1")

def get_row(st, line_code):
    for sec in st.get("sections", []):
        for r in sec.get("rows", []):
            if r.get("line_code") == line_code:
                return r
    return None

@pytest.mark.asyncio
async def test_multiyear_pnl_statement_5_year():
    spec = QuerySpec(
        metric="pnl_statement",
        period=Period(from_="FY22", to="FY26"),
        filters=[
            Filter(field="scope", op="=", value="standalone")
        ]
    )
    compiler = Compiler()
    compiled = compiler.compile(spec)
    assert compiled.metric == "pnl_statement"
    
    result = await compiler.execute(compiled)
    assert result.rows is not None
    
    vis = build_visual(
        spec=spec,
        compiled=compiled,
        columns=result.columns,
        rows=result.rows,
        chart_kind=None,
        title="P&L",
        subtitle="",
        mode="test"
    )
    
    st = vis.get("statement")
    assert st is not None
    assert st["statement"] == "pnl"
    assert st["periods"] == ["FY26", "FY25", "FY24", "FY23", "FY22"]
    
    rev_ops = get_row(st, "PL.REV_OPS")
    assert rev_ops is not None
    assert [round(rev_ops["values"][p], 1) if rev_ops["values"].get(p) is not None else None for p in st["periods"]] == [132508.1, 137846.3, 138402.1, 155517.3, 110345.4]
    
    other_inc = get_row(st, "PL.OTHER_INCOME")
    assert other_inc is not None
    assert round(other_inc["values"]["FY24"], 1) == 10735.5
    
@pytest.mark.asyncio
async def test_multiyear_pnl_statement_10_year():
    spec = QuerySpec(
        metric="pnl_statement",
        period=Period(from_="FY17", to="FY26"),
        filters=[
            Filter(field="scope", op="=", value="standalone")
        ]
    )
    compiler = Compiler()
    compiled = compiler.compile(spec)
    result = await compiler.execute(compiled)
    
    vis = build_visual(
        spec=spec,
        compiled=compiled,
        columns=result.columns,
        rows=result.rows,
        chart_kind=None,
        title="P&L",
        subtitle="",
        mode="test"
    )
    
    st = vis.get("statement")
    assert st["periods"] == ["FY26", "FY25", "FY24", "FY23", "FY22", "FY21", "FY20", "FY19", "FY18", "FY17"]
    
    pat = get_row(st, "PL.PAT")
    assert pat is not None
    assert round(pat["values"]["FY19"], 1) == 26764.6

@pytest.mark.asyncio
async def test_multiyear_balance_sheet():
    spec = QuerySpec(
        metric="balance_sheet",
        period=Period(from_="FY24", to="FY26"),
        filters=[]
    )
    compiler = Compiler()
    compiled = compiler.compile(spec)
    assert compiled.metric == "balance_sheet"
    result = await compiler.execute(compiled)
    vis = build_visual(spec, compiled, result.columns, result.rows, None, "BS", "", "test")
    assert vis["statement"]["statement"] == "balance_sheet"

@pytest.mark.asyncio
async def test_multiyear_cash_flow():
    spec = QuerySpec(
        metric="cash_flow_statement",
        period=Period(from_="FY24", to="FY26"),
        filters=[]
    )
    compiler = Compiler()
    compiled = compiler.compile(spec)
    assert compiled.metric == "cash_flow_statement"
    result = await compiler.execute(compiled)
    vis = build_visual(spec, compiled, result.columns, result.rows, None, "CF", "", "test")
    assert vis["statement"]["statement"] == "cash_flow"
