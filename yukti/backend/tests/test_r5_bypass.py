import pytest
from unittest.mock import patch, AsyncMock
from app.turn_runner import get_agent_turn_runner
from app.auth import get_active_principal, set_active_principal, Principal
from app.tools.query_data import query_data

@pytest.fixture(autouse=True)
def wipe_runner():
    from app.turn_runner import _GLOBAL_RUNNERS
    _GLOBAL_RUNNERS.clear()
    set_active_principal(None)
    yield
    _GLOBAL_RUNNERS.clear()
    set_active_principal(None)

def test_toolset_isolation():
    set_active_principal(Principal(emp_id="EMP-CMD", persona="CMD", function="HR", grade="CMD", display_name="CMD", designation="CMD"))
    trun_cmd = get_agent_turn_runner()
    tools_cmd = [t.__name__ for t in trun_cmd.agent.tools]
    assert "query_data" in tools_cmd

    set_active_principal(Principal(emp_id="EMP-E2", persona="E2_HR", function="HR", grade="E2", display_name="E2_HR", designation="E2"))
    trun_e2 = get_agent_turn_runner()
    tools_e2 = [t.__name__ for t in trun_e2.agent.tools]
    assert "query_data" not in tools_e2
    assert trun_cmd is not trun_e2

def test_direct_call_refuses():
    set_active_principal(Principal(emp_id="EMP-DIR", persona="DIR_FIN", function="FIN", grade="DIR", display_name="DIR_FIN", designation="DIR"))
    res = query_data("SELECT * FROM payroll_monthly")
    assert res["status"] == "refused"
    assert "restricted to CMD" in res["message"]

def test_reviewer_r5_probes_refused():
    set_active_principal(Principal(emp_id="EMP-DIR", persona="DIR_FIN", function="FIN", grade="DIR", display_name="DIR_FIN", designation="DIR"))
    probes = [
        "SELECT * FROM ssot_workforce_employee",
        "SELECT * FROM payroll_monthly WHERE discipline_id='DISC-FIN' OR 1=1",
        "SELECT * FROM vigilance_cases",
        "SELECT * FROM medical_claims"
    ]
    for q in probes:
        res = query_data(q)
        assert res["status"] == "refused"
        assert "restricted to CMD" in res["message"]

def test_http_runner_isolation_orders():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth import issue_token
    from app.turn_runner import _GLOBAL_RUNNERS
    client = TestClient(app)
    
    # 1: CMD then E2_HR
    _GLOBAL_RUNNERS.clear()
    with patch("app.turn_runner.AgentTurnRunner._execute_turn_inner", new_callable=AsyncMock) as mock_inner:
        mock_inner.return_value = {
            "turn_id": "test", "language": "en", "persona": "CMD",
            "spoken_summary": "ok", "display_text": "ok", "visual": {"type": "none", "mode": "replace"},
            "insights": [], "sources": [], "suggestions": [], "access": {"status": "allowed"}
        }
        r1 = client.post("/api/turn", json={"query": "hello"}, headers={"Authorization": f"Bearer {issue_token('CMD')}"})
        assert r1.status_code == 200
        
        mock_inner.return_value["persona"] = "E2_HR"
        r2 = client.post("/api/turn", json={"query": "hello"}, headers={"Authorization": f"Bearer {issue_token('E2_HR')}"})
        assert r2.status_code == 200
        
    assert "CMD" in _GLOBAL_RUNNERS
    assert "E2_HR" in _GLOBAL_RUNNERS
    
    cmd_tools = [t.__name__ for t in _GLOBAL_RUNNERS["CMD"].agent.tools]
    e2_tools = [t.__name__ for t in _GLOBAL_RUNNERS["E2_HR"].agent.tools]
    
    assert "query_data" in cmd_tools
    assert "query_data" not in e2_tools
    
    # 2: DIR_FIN then CMD
    _GLOBAL_RUNNERS.clear()
    with patch("app.turn_runner.AgentTurnRunner._execute_turn_inner", new_callable=AsyncMock) as mock_inner:
        mock_inner.return_value = {
            "turn_id": "test", "language": "en", "persona": "DIR_FIN",
            "spoken_summary": "ok", "display_text": "ok", "visual": {"type": "none", "mode": "replace"},
            "insights": [], "sources": [], "suggestions": [], "access": {"status": "allowed"}
        }
        r1 = client.post("/api/turn", json={"query": "hello"}, headers={"Authorization": f"Bearer {issue_token('DIR_FIN')}"})
        assert r1.status_code == 200
        
        mock_inner.return_value["persona"] = "CMD"
        r2 = client.post("/api/turn", json={"query": "hello"}, headers={"Authorization": f"Bearer {issue_token('CMD')}"})
        assert r2.status_code == 200
        
    assert "DIR_FIN" in _GLOBAL_RUNNERS
    assert "CMD" in _GLOBAL_RUNNERS
    
    df_tools = [t.__name__ for t in _GLOBAL_RUNNERS["DIR_FIN"].agent.tools]
    cmd_tools2 = [t.__name__ for t in _GLOBAL_RUNNERS["CMD"].agent.tools]
    
    assert "query_data" not in df_tools
    assert "query_data" in cmd_tools2
