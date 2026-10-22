"""Unit tests for DocumentDraftingEngine.draft() using SSOT work centre columns (Packet B4.4)."""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.tools.draft_document import DocumentDraftingEngine


def test_real_columns_rendered():
    engine = DocumentDraftingEngine()
    profile = {
        "active_headcount": 948,
        "executive_headcount": 692,
        "non_executive_headcount": 256,
        "sanctioned_strength_fy26": 1000,
        "vacancy_count_fy26": 52,
        "contractor_headcount_fy26": 120,
        "payroll_gross_inr_cr_fy26": 245.5,
        "continuous_stay_5yr_plus_execs": 419,
        "retiring_within_3yr_count": 40,
    }
    context_data = {
        "wc_profile": profile,
        "wc_name": "Delhi HQ",
        "wc_id": "WC-DEL",
        "rows": [{"col1": "val1"}],
    }
    res = engine.draft(
        doc_type="",
        query="Draft a briefing note on this",
        context_data=context_data,
    )
    md = res["markdown"]

    # Verify indicators section exists
    assert "### 2. Work Centre 360° Key Indicators (Delhi HQ · `WC-DEL`)" in md

    # Check expected formatted values appear
    assert "1,000" in md
    assert "52" in md
    assert "120" in md
    assert "245.50" in md
    assert "419" in md
    assert "40" in md

    # Ensure no **0** in markdown
    assert "**0**" not in md

    # Verify renamed payroll label
    assert "FY26 Gross Payroll" in md
    assert "₹245.50 Crore" in md


def test_missing_column_renders_na():
    engine = DocumentDraftingEngine()
    profile = {
        "active_headcount": 948,
        "executive_headcount": 692,
        "non_executive_headcount": 256,
        "sanctioned_strength_fy26": 1000,
        # vacancy_count_fy26 missing
        "contractor_headcount_fy26": 120,
        "payroll_gross_inr_cr_fy26": 245.5,
        "continuous_stay_5yr_plus_execs": 419,
        "retiring_within_3yr_count": 40,
    }
    context_data = {
        "wc_profile": profile,
        "wc_name": "Delhi HQ",
        "wc_id": "WC-DEL",
        "rows": [{"col1": "val1"}],
    }
    res = engine.draft(
        doc_type="",
        query="Draft a briefing note on this",
        context_data=context_data,
    )
    md = res["markdown"]
    assert "n/a" in md
    assert "(**n/a** Vacancies)" in md


def test_backward_compatibility_old_keys():
    engine = DocumentDraftingEngine()
    profile = {
        "active_headcount": 800,
        "executive_headcount": 500,
        "non_executive_headcount": 300,
        "sanctioned_strength": 900,
        "vacancy_count": 100,
        "contract_workforce_headcount": 50,
        "fy26_total_payroll_cr": 150.0,
        "execs_stay_ge_5yr": 200,
        "retiring_3yr_count": 30,
    }
    context_data = {
        "wc_profile": profile,
        "wc_name": "Assam Asset",
        "wc_id": "WC-ASM",
        "rows": [{"col": "v"}],
    }
    res = engine.draft(
        doc_type="",
        query="Draft a briefing note on this",
        context_data=context_data,
    )
    md = res["markdown"]
    assert "900" in md
    assert "100" in md
    assert "50" in md
    assert "150.00" in md
    assert "200" in md
    assert "30" in md


def test_real_zero_renders_as_zero():
    engine = DocumentDraftingEngine()
    profile = {
        "active_headcount": 100,
        "executive_headcount": 100,
        "non_executive_headcount": 0,
        "sanctioned_strength_fy26": 100,
        "vacancy_count_fy26": 0,
        "contractor_headcount_fy26": 0,
        "payroll_gross_inr_cr_fy26": 20.0,
        "continuous_stay_5yr_plus_execs": 0,
        "retiring_within_3yr_count": 0,
    }
    context_data = {
        "wc_profile": profile,
        "wc_name": "Tripura Asset",
        "wc_id": "WC-TRP",
        "rows": [{"col": "v"}],
    }
    res = engine.draft(
        doc_type="",
        query="Draft a briefing note on this",
        context_data=context_data,
    )
    md = res["markdown"]
    # 0 vacancies should be rendered as **0** Vacancies, not n/a
    assert "(**0** Vacancies)" in md
