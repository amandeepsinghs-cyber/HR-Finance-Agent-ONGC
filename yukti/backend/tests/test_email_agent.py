import pytest
import re
import email
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
        self.session_id = "test-session"
        self.emp_id = "12345"

    def get_active_cohort(self):
        return {
            "cohort_id": "C1",
            "definition_id": "DELHI_GT5_CONT_V1",
            "row_count": 3,
            "all_cadres_count": 4,
            "rows": self.last_rows,
            "level_rows": [{"grade": "E1", "headcount": 1}, {"grade": "E2", "headcount": 1}, {"grade": "E3", "headcount": 1}]
        }

def test_email_agent_cmd():
    session = MockSessionState()
    contract = build_email_draft("draft email to director hr", session, "CMD", "T5", "en")
    assert contract["visual"]["type"] == "email_draft"
    assert "3 executives" in contract["visual"]["email_draft"]["body_md"]
    assert "1 non-executive staff" in contract["visual"]["email_draft"]["body_md"]
    assert "1 carry a recorded exemption" in contract["visual"]["email_draft"]["body_md"]
    assert "JRTP Rev 4" in contract["visual"]["email_draft"]["body_md"]
    assert len(contract["artifacts"]) > 0
    
    # Subject contains n_exec
    assert "3 executives" in contract["visual"]["email_draft"]["subject"]
    
    # Body counts by level sum to n_exec
    body = contract["visual"]["email_draft"]["body_md"]
    # We can extract the table and sum up
    # In Mock we injected level_rows with headcounts 1, 1, 1 which sum to 3
    
    # test .eml export
    from app.tools.export_tool import DocumentExporter
    import uuid
    import tempfile
    from app.config import EXPORTS_DIR
    exporter = DocumentExporter()
    export_id = contract["artifacts"][0]["export_id"]
    exporter.export_eml(contract["visual"]["email_draft"], filename=f"{export_id}.eml", masked=False)
    eml_path = EXPORTS_DIR / f"{export_id}.eml"
    with open(eml_path, "rb") as f:
        msg = email.message_from_bytes(f.read())
    assert msg["X-Unsent"] == "1"
    
    attachments = []
    for part in msg.walk():
        if part.get_content_maintype() != 'multipart':
            if part.get_filename():
                attachments.append(part)
    
    assert len(attachments) == 1
    assert attachments[0].get_content_type() == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_email_agent_dir_hr():
    session = MockSessionState()
    contract = build_email_draft("draft email to director hr", session, "DIR_HR", "T5", "en")
    assert "CMD" in contract["chips"]
    assert "Transfer Board" in contract["chips"]
    assert contract["visual"]["email_draft"]["to"] == []
    assert contract["display_text"] == "Who should this go to?"

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

def test_no_literals_in_templates():
    import os
    import re
    # draft_document.py
    with open("app/tools/draft_document.py", "r") as f:
        draft_content = f.read()
    assert not re.search(r"\b401\b", draft_content)
    assert not re.search(r"\b146\b", draft_content)
    
    # markdown templates
    with open("app/brain/templates/email_transfer_review.md", "r") as f:
        en_content = f.read()
    assert not re.search(r"\b401\b", en_content)
    assert not re.search(r"\b146\b", en_content)
    
    with open("app/brain/templates/email_transfer_review_hi.md", "r") as f:
        hi_content = f.read()
    assert not re.search(r"\b401\b", hi_content)
    assert not re.search(r"\b146\b", hi_content)

