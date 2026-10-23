"""P0.7 (BUG-31, D-35): synthetic policy clauses carry provenance "illustrative" in data, contract and UI."""

import asyncio
import csv
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import RULEBOOKS_CSV_PATH  # noqa: E402
from app.tools.policy_search import PolicySearchEngine  # noqa: E402

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src"


def _rows():
    with open(RULEBOOKS_CSV_PATH, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_csv_every_row_has_provenance_and_no_jrtp_is_real():
    rows = _rows()
    assert len(rows) == 68
    assert all(r.get("provenance") in ("real", "illustrative") for r in rows), "missing/invalid provenance"
    assert not [r for r in rows if r["doc_id"] == "JRTP" and r["provenance"] == "real"]
    # R16 Gemini-generated rows (source_basis = generic "ONGC HR/Finance Policy Documents") are illustrative
    r16 = [r for r in rows if r["source_basis"] == "ONGC HR/Finance Policy Documents"]
    assert len(r16) == 12 and all(r["provenance"] == "illustrative" for r in r16)


def test_jrtp_clause_payload_is_illustrative():
    eng = PolicySearchEngine()
    hits = eng.search_local("JRTP clause 3.0 minimum station tenure rotation", top_k=3)
    assert hits, "no JRTP clause found"
    jrtp = [h for h in hits if "Clause 3.0" in h["clause_ref"]]
    assert jrtp and all(h["provenance"] == "illustrative" for h in jrtp)
    assert "3.2" in jrtp[0]["text"]  # JRTP Rev 4 cl. 3.2 lives in Clause 3.0


def test_search_results_always_carry_provenance():
    eng = PolicySearchEngine()
    for q in ("casual leave entitlement", "PRBS pension contribution", "post retirement medical 15 years",
              "promotion DPC norms", "delegation of powers"):
        for h in eng.search_local(q, top_k=3):
            assert h.get("provenance") in ("real", "illustrative"), (q, h.get("clause_ref"))


@pytest.mark.asyncio
async def test_casual_leave_answer_is_illustrative_and_has_no_jrtp_footer(monkeypatch):
    monkeypatch.setenv("YUKTI_PLANNER", "0")
    from app.turn_runner import AgentTurnRunner

    runner = AgentTurnRunner(model_name="gemini-2.5-flash")
    c = await runner.execute_turn_async("How many casual leaves can I take?", session_id="p07-casual-leave",
                                        persona="CMD")
    vis = c.get("visual") or {}
    assert vis.get("type") == "clause", f"expected a clause card, got {vis.get('type')}"
    clause = vis["clause"]
    assert clause["provenance"] == "illustrative"
    assert "JRTP" not in (clause.get("doc_title") or "") and "Job Rotation" not in (clause.get("doc_title") or "")
    assert "Statutory" not in (vis.get("subtitle") or "")


def test_clause_renderer_has_badge_and_no_hardcoded_jrtp_footer():
    src = (FRONTEND / "components" / "renderers" / "ClauseRenderer.tsx").read_text(encoding="utf-8")
    assert "'Job Rotation & Transfer Policy (JRTP)'" not in src  # the old hard-coded fallback title/footer
    assert "Illustrative" in src and "Synthetic clause for demo; ONGC's text is not public." in src
    assert "clause.provenance !== 'real'" in src  # default-safe: unknown provenance renders as Illustrative
