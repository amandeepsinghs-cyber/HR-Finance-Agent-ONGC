import pytest
from unittest.mock import patch, AsyncMock
from app.turn_runner import get_agent_turn_runner
from app.auth import get_active_principal, set_active_principal, Principal
from app.tools.query_data import query_data

@pytest.fixture(autouse=True)
def wipe_runner():
    from app.turn_runner import _GLOBAL_RUNNERS
    _GLOBAL_RUNNERS.clear()
    yield
    _GLOBAL_RUNNERS.clear()

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
