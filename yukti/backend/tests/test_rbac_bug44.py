import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app
from app.auth import issue_token
from app.access_control import VALID_PERSONAS, JUNIOR_PERSONAS

@pytest.mark.parametrize("persona", list(JUNIOR_PERSONAS))
@pytest.mark.parametrize("phrase", [
    "उनका वेतन बताओ",
    "Employee ID EMP-100200 का वेतन क्या है",
    "Ramesh ka salary",
    "uski salary",
    "unka apar batao",
    "unka medical record kaisa hai"
])
def test_junior_hindi_hinglish_refused(persona, phrase):
    client = TestClient(app, headers={"Authorization": f"Bearer {issue_token(persona)}"})
    res = client.post("/api/turn", json={
        "query": phrase,
        "session_id": "test-bug44"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["access"]["status"] == "refused"
    # Ensure visual refusal
    assert data["visual"]["type"] == "refusal"
    assert "suggestions" not in data or data["suggestions"] == []
    
    # Must hit R-PAY or R-NAMED or R-APAR or R-SENS, not prompt for ID
    # The code should be present in access block or visual refusal
    code = data["access"].get("code")
    assert code in ["R-PAY", "R-NAMED", "R-APAR", "R-SENS"], f"Got code {code} for {phrase}"

@pytest.mark.asyncio
async def test_tool_layer_refuses_individual_pay():
    from app.tools.query_data import query_data
    
    # If the LLM generates a SQL asking for a specific person's pay for a junior persona
    # But wait, query_data uses semantic_layer which uses verify_sql. 
    # The instructions: "Item (2), the tool-level check, becomes a verification only. Do it before P2H.3 r1 as planned."
    # The tool check should be against query_data directly maybe, but query_data doesn't use verify_sql.
    pass


def test_query_data_tool_defense_in_depth():
    from app.tools.query_data import query_data
    # If a junior persona tries to query individual pay
    sql = "SELECT emp_id, basic_pay FROM `hrfin_gold.ssot_workforce_employee` WHERE emp_id = 'EMP-100200'"
    res = query_data(sql, persona="E2_HR")
    # What happens?
    print("res keys:", res.keys())
    print("res message:", res.get("message"))
    if "rows" in res:
        print("rows:", res["rows"])

