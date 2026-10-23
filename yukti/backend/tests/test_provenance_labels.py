"""P0.3 (BUG-02 labels, BUG-04): no false "Audited / Yahoo / Compiled SQL" provenance; honest local_snapshot.

Offline: BigQuery is forced to fail (the compiler's `_run_sync` raises RefreshError), so the compiler serves the
financial_build JSON snapshot. Each answer must say so: status.source == "local_snapshot", no SQL, a caveat that
contains "local snapshot", provenance.label == "local_snapshot", and no "Audited", "Yahoo", "ONGC.NS" or
"Compiled" text anywhere in the user-visible contract.
"""

import asyncio
import json
from pathlib import Path
import re
import subprocess
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.auth.exceptions import RefreshError  # noqa: E402

from app.brain.compiler import Compiler, get_compiler  # noqa: E402
from app.brain.pipeline import run_planner_turn  # noqa: E402
from app.brain.query_spec import Period, QuerySpec  # noqa: E402
from app.session_memory import get_session_manager  # noqa: E402

BRAIN = Path(__file__).resolve().parent.parent / "app" / "brain"
FALSE_LABELS = re.compile(r"Audited|Yahoo|ONGC\.NS|Compiled\b|dry-run")


def _visible_text(contract):
    """Every label a user can see (text, visual chrome, insights, sources, caveat, status events).

    Table row cells are data, not labels: the financial_build snapshot's own line names (e.g.
    "X. Consolidated Group PAT (ONGC.NS)") are replaced with AR-verified lines in P1 (SPEC-01), not here.
    """
    vis = dict(contract.get("visual") or {})
    if isinstance(vis.get("table"), dict):
        vis["table"] = {k: v for k, v in vis["table"].items() if k != "rows"}
    if isinstance(vis.get("chart"), dict):
        vis["chart"] = {k: v for k, v in vis["chart"].items() if k != "data"}
    keep = {k: contract.get(k) for k in ("display_text", "spoken_summary", "insights", "insights_v2",
                                          "sources", "caveat", "status_events", "provenance")}
    keep["visual"] = vis
    return json.dumps(keep, ensure_ascii=False)


@pytest.fixture()
def bq_down(monkeypatch):
    def boom(self, sql):
        raise RefreshError("Reauthentication is needed. Please run gcloud auth application-default login")

    monkeypatch.setattr(Compiler, "_run_sync", boom)
    yield


@pytest.mark.parametrize("metric", ["pnl_statement", "balance_sheet", "cash_flow_statement"])
def test_statement_fallback_is_labelled_local_snapshot(bq_down, metric):
    spec = QuerySpec(domain="finance", metric=metric, period=Period(fy="FY24"))
    sm = get_session_manager()
    st = sm.get_or_create(f"prov-{metric}-{time.time_ns()}", persona="CMD", language="en")
    res = asyncio.run(run_planner_turn("show the statement", st, "CMD", f"turn-prov-{metric}", "en",
                                       time.perf_counter(), spec_override=spec))
    assert res is not None, "fallback produced no answer"
    c = res["contract"] if "contract" in res else res
    assert c["status"]["source"] == "local_snapshot"
    assert c["status"]["sql"] is None
    assert c.get("generated_sql") is None
    assert c["provenance"]["label"] == "local_snapshot"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", c["provenance"]["snapshot_date"] or "")
    assert "local snapshot" in (c.get("caveat") or "").lower()
    assert c["caveat"].startswith("Shown from a local snapshot (")
    assert all("sql" not in s for s in c["sources"] if s.get("kind") == "data")
    hits = FALSE_LABELS.findall(_visible_text(c))
    assert not hits, f"false provenance text in {metric}: {hits}"
    assert c["visual"]["table"]["rows"], "the snapshot rows must still be shown"


def test_compiler_marks_fallback_result(bq_down):
    comp = get_compiler()
    compiled = comp.compile(QuerySpec(domain="finance", metric="balance_sheet", period=Period(fy="FY24")))
    res = asyncio.run(comp.execute(compiled))
    assert res.source == "local_snapshot" and res.snapshot_date
    assert res.dry_run_bytes == 0 and res.total_bytes == 0


def test_real_bigquery_path_keeps_sql_and_source(monkeypatch):
    from app.brain.compiler import QueryResult

    def fake_run(self, sql):
        return QueryResult(columns=["x"], rows=[{"x": 1}], total_bytes=10, latency_ms=1.0, dry_run_bytes=10)

    monkeypatch.setattr(Compiler, "_run_sync", fake_run)
    comp = get_compiler()
    compiled = comp.compile(QuerySpec(domain="finance", metric="balance_sheet", period=Period(fy="FY24")))
    res = asyncio.run(comp.execute(compiled))
    assert res.source == "bigquery" and res.snapshot_date is None


def test_no_false_label_strings_in_compiler_and_presenter():
    """Acceptance grep: 0 user-facing hits in compiler.py / presenter.py (comments are allowed)."""
    out = subprocess.run(["grep", "-nE", r"Audited|Yahoo|ONGC\.NS", str(BRAIN / "compiler.py"), str(BRAIN / "presenter.py")],
                         capture_output=True, text=True).stdout
    code_hits = [ln for ln in out.splitlines() if not ln.split(":", 2)[2].lstrip().startswith("#")]
    assert code_hits == [], code_hits


GUARDED_FILES = ["turn_runner.py", "agent.py", "tools/draft_document.py", "access_control.py",
                 "tools/certified_query.py", "brain/pipeline.py", "brain/insight_context.py",
                 "brain/compiler.py", "brain/presenter.py"]


def _string_literals_without_docstrings(path: Path):
    """All string constants in a module except docstrings (comments are not in the AST at all)."""
    import ast
    tree = ast.parse(path.read_text(encoding="utf-8"))
    doc_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant):
                doc_ids.add(id(first.value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in doc_ids:
            yield node.lineno, node.value


@pytest.mark.parametrize("rel", GUARDED_FILES)
def test_no_audited_claim_in_user_facing_strings(rel):
    """P0.3 r2 (G4 must-fix 1g): no string literal may claim 'audited' data (synthetic / unverified sources)."""
    path = BRAIN.parent / rel
    hits = [(ln, s[:80]) for ln, s in _string_literals_without_docstrings(path)
            if re.search(r"\baudited\b", s, re.I) and "persona_assertion_ignored" not in s]
    assert hits == [], f"{rel}: {hits}"


def test_cached_contracts_have_no_audited_claim():
    p = BRAIN.parent.parent / "certified" / "answer_cache_warmup.json"
    assert not re.search(r"\baudited\b|Yahoo|ONGC\.NS", p.read_text(encoding="utf-8"), re.I)


def test_insight_context_does_not_claim_annual_report_source():
    """P0.3 r2: generated financial_build context must not be labelled as Annual Report text (found in the P0.9 r2 run)."""
    hits = [(ln, s[:60]) for ln, s in _string_literals_without_docstrings(BRAIN / "insight_context.py")
            if re.search(r"Annual Report[^\n]{0,30}Context", s)]
    assert hits == [], hits
