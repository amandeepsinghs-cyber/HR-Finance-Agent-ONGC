import asyncio
import pytest
from tests.test_v19_chain import v19_runner
from app.auth import principal_for_persona

ALL_11_PERSONAS = [
    "CMD", "DIR_HR", "DIR_FIN",
    "E1_HR", "E2_HR", "E3_HR", "E4_HR",
    "E1_FIN", "E2_FIN", "E3_FIN", "E4_FIN"
]

@pytest.mark.parametrize("persona", ALL_11_PERSONAS)
@pytest.mark.parametrize("turn_step", ["T1", "T2", "T3", "T4", "T5"])
def test_v19_rbac_matrix_55_cases(v19_runner, persona: str, turn_step: str):
    sid = f"v19-rbac-{persona}-{turn_step}"
    principal = principal_for_persona(persona)
    
    # T1
    c1 = asyncio.run(v19_runner.execute_turn_async("How many employees are here in Delhi across different levels? Draw a histogram", session_id=sid, persona=persona, principal=principal))
    if turn_step == "T1":
        assert c1["access"]["status"] in ("allowed", "partial")
        return

    # T2
    c2 = asyncio.run(v19_runner.execute_turn_async("how many of these employees are here in Delhi for more than five years?", session_id=sid, persona=persona, principal=principal))
    if turn_step == "T2":
        assert c2["access"]["status"] in ("allowed", "partial")
        return

    # T3
    c3 = asyncio.run(v19_runner.execute_turn_async("give me the name of those employees and their tenure in Delhi", session_id=sid, persona=persona, principal=principal))
    if turn_step == "T3":
        assert c3["access"]["status"] in ("allowed", "partial")
        if persona.startswith("E"):
            assert c3["visual"]["table"]["columns"][0] != "Name"
        return

    # T4
    c4 = asyncio.run(v19_runner.execute_turn_async("export this as an Excel file? Their names, designations, ranks E1 and tenure in Delhi", session_id=sid, persona=persona, principal=principal))
    if turn_step == "T4":
        assert c4["artifacts"]
        assert c4["artifacts"][0]["kind"] == "xlsx"
        if persona.startswith("E"):
            assert "_aggregate" in c4["artifacts"][0]["filename"]
        return

    # T5
    c5 = asyncio.run(v19_runner.execute_turn_async("draft an email to the Director HR highlighting the cohort", session_id=sid, persona=persona, principal=principal))
    if turn_step == "T5":
        if persona.startswith("E") and "FIN" in persona:
            assert c5["access"]["status"] == "refused"
        else:
            assert c5["visual"]["type"] == "email_draft"
            if persona == "DIR_FIN" or persona.startswith("E"):
                assert not c5["visual"]["email_draft"].get("attachments")
            else:
                assert c5["visual"]["email_draft"].get("attachments")
