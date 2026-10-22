"""Tests for DocumentDraftingEngine.draft_transfer_note (Packet B3.5)."""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.tools.draft_document import DocumentDraftingEngine


def test_example_two_rows():
    engine = DocumentDraftingEngine()
    employees = [
        {
            "emp_id": "EMP-1",
            "name": "A B",
            "work_centre": "Delhi HQ",
            "station_tenure_years": 8.44,
            "retiring_within_3yr": True,
        },
        {
            "emp_id": "EMP-2",
            "name": "C D",
            "work_centre": "Delhi HQ",
            "station_tenure_years": 5.0,
        },
    ]
    res = engine.draft_transfer_note(employees)
    assert res["doc_type"] == "transfer_note"
    assert res["template_id"] == "template_transfer_note.docx"
    assert res["version"] == 1
    assert res["employee_count"] == 2
    assert res["emp_ids"] == ["EMP-1", "EMP-2"]
    assert res["title"] == "Draft Transfer Note: 2 Executive(s) — Delhi HQ"

    md = res["markdown"]
    # Headings check
    assert "# OIL AND NATURAL GAS CORPORATION LIMITED" in md
    assert "## CORPORATE HUMAN RESOURCES | DRAFT TRANSFER NOTE" in md
    assert "**Classification:** CONFIDENTIAL — DELIBERATIVE DRAFT (JRTP Clause 11.0)" in md
    assert "### 1. Purpose" in md
    assert "### 2. Employees Proposed for Transfer (2)" in md
    assert "### 3. Policy Basis" in md
    assert "### 4. Exemptions to Verify" in md
    assert "### 5. Proposed Destination" in md
    assert "*Prepared by:* Yukti AI for Director (HR) review" in md

    # Table rows
    assert "| 1 | A B | EMP-1 | — | — | — | Delhi HQ | 8.4 | — | — |" in md
    assert "| 2 | C D | EMP-2 | — | — | — | Delhi HQ | 5.0 | — | — |" in md
    assert "8.4" in md

    # Section 4 listing "A B"
    sec4 = md.split("### 4. Exemptions to Verify")[1].split("### 5. Proposed Destination")[0]
    assert "A B" in sec4
    assert "C D" not in sec4


def test_large_roster_419_rows():
    engine = DocumentDraftingEngine()
    employees = [
        {
            "emp_id": f"EMP-{i}",
            "name": f"Executive {i}",
            "designation": "Chief Engineer",
            "grade": "E5",
            "discipline": "Production",
            "work_centre": "Delhi HQ",
            "ongc_tenure_years": 15.2,
            "station_tenure_years": 5.5,
            "years_to_retirement": 10.0,
            "retiring_within_3yr": False,
            "exemption": None,
        }
        for i in range(1, 420)
    ]
    res = engine.draft_transfer_note(employees)
    assert res["employee_count"] == 419
    assert len(res["emp_ids"]) == 419
    assert res["title"] == "Draft Transfer Note: 419 Executive(s) — Delhi HQ"

    md = res["markdown"]
    sec2 = md.split("### 2. Employees Proposed for Transfer (419)")[1].split("### 3. Policy Basis")[0]
    table_rows = [
        line for line in sec2.strip().splitlines()
        if line.startswith("|") and not line.startswith("| S.No") and not line.startswith("|---") and not line.startswith("| ---")
    ]
    assert len(table_rows) == 419


def test_mixed_work_centres():
    engine = DocumentDraftingEngine()
    employees = [
        {
            "emp_id": "EMP-1",
            "name": "Exec One",
            "work_centre": "Delhi HQ",
        },
        {
            "emp_id": "EMP-2",
            "name": "Exec Two",
            "work_centre": "Assam Asset",
        },
    ]
    res = engine.draft_transfer_note(employees)
    assert res["title"] == "Draft Transfer Note: 2 Executive(s) — Multiple Work Centres"


def test_empty_employees_raises():
    engine = DocumentDraftingEngine()
    with pytest.raises(ValueError, match="no employees selected"):
        engine.draft_transfer_note([])


def test_missing_keys_renders_em_dash():
    engine = DocumentDraftingEngine()
    employees = [{}]
    res = engine.draft_transfer_note(employees)
    assert res["employee_count"] == 1
    assert res["emp_ids"] == [None]
    assert res["title"] == "Draft Transfer Note: 1 Executive(s) — Multiple Work Centres"
    md = res["markdown"]
    assert "| 1 | — | — | — | — | — | — | — | — | — |" in md
    assert "No exemption flags among the selected employees." in md
