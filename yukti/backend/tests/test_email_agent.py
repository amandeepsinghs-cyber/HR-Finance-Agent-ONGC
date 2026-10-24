import pytest
from app.brain.email_agent import build_email_draft

class MockSessionState:
    def __init__(self):
        self.turns = [{"visual": {"table": {"rows": [
            {"grade": "E1", "exemption_tag": None},
            {"grade": "E2", "exemption_tag": "Medical"},
            {"grade": "E3", "exemption_tag": None},
            {"grade": "S1", "exemption_tag": None}
        ]}}}]
        self.last_rows = self.turns[0]["visual"]["table"]["rows"]

def test_email_agent_cmd():
    session = MockSessionState()
    contract = build_email_draft("draft email to director hr", session, "CMD", "T5", "en")
    assert contract["visual"]["type"] == "email_draft"
    assert "3 executives" in contract["visual"]["email_draft"]["body_md"]
    assert "1 non-executive staff" in contract["visual"]["email_draft"]["body_md"]
    assert "1 carry a recorded exemption" in contract["visual"]["email_draft"]["body_md"]
    assert "JRTP Rev 4" in contract["visual"]["email_draft"]["body_md"]
    assert len(contract["artifacts"]) > 0

def test_email_agent_dir_hr():
    session = MockSessionState()
    contract = build_email_draft("draft email to director hr", session, "DIR_HR", "T5", "en")
    assert "CMD" in contract["chips"]
    assert "Transfer Board" in contract["chips"]

def test_email_agent_junior_fin():
    session = MockSessionState()
    contract = build_email_draft("draft email to director hr", session, "E2_FIN", "T5", "en")
    assert contract["access"]["status"] == "refused"
    assert "Transfer reviews are raised by HR" in contract["display_text"]

def test_email_agent_junior_hr():
    session = MockSessionState()
    contract = build_email_draft("draft email to director hr", session, "E2_HR", "T5", "en")
    assert contract["visual"]["type"] == "email_draft"
    assert "Counts only" in contract["visual"]["email_draft"]["body_md"]
    assert len(contract["visual"]["email_draft"]["attachments"]) == 0
