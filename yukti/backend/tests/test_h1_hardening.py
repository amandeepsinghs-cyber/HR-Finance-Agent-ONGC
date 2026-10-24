"""H1 Hardening Regression & Soak Tests (H1.1, H1.2, H1.3b).

Covers:
- H1.1: Async BigQuery/embeddings/tools off the event loop (< 100 ms max stall under 3 concurrent sessions)
        + Gemini Live voice tool calls off the receive loop so barge-in (`interrupted`) is never blocked.
- H1.2: Hardened SQL allow-list (backtick cross-project, multi-statement, comment-hidden tokens, CTEs),
        re-validation of repaired SQL in `query_data`, parameterised + validated `run_certified_query`,
        and zero hardcoded project IDs in `turn_runner.py` / `access_control.py`.
- H1.3b: Contract validation repair (`validate_and_repair_contract`), cache immutability (`ToolResultCache`,
         `VerifiedAnswerCache`, `DemoCache`), and memory bounds over a 200-turn soak + 250-session eviction test.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import time
import tracemalloc
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from app.answer_cache import InMemoryAnswerCache, VerifiedAnswerCache
from app.answer_composer import get_contract_validator, validate_and_repair_contract
from app.cache import DemoCache
from app.session_memory import (
    MAX_SESSION_TURNS,
    MAX_SESSIONS,
    MAX_SPEC_HISTORY,
    MAX_VISUAL_HISTORY,
    SessionManager,
    SessionState,
)
from app.tool_cache import ToolResultCache
from app.tools.certified_query import run_certified_query
from app.tools.query_data import query_data
from app.tools.semantic_layer import SemanticLayer


# ==============================================================================
# H1.2: SQL Safety — Hardened Allow-list, Repaired SQL Re-validation, Params
# ==============================================================================


def test_h1_2_sql_safety_hardened_allowlist():
    sl = SemanticLayer(project_id="ongc-hr-finance-agent")

    # 1. Valid queries (qualified 2-part, 3-part, CTEs, EXTRACT(... FROM ...))
    valid_queries = [
        "SELECT wc_id, COUNT(*) FROM hrfin_gold.v_continuous_stay GROUP BY 1",
        "SELECT * FROM `ongc-hr-finance-agent.hrfin_silver.employee_master` LIMIT 10",
        "SELECT * FROM `ongc-hr-finance-agent`.hrfin_gold.ssot_workforce_employee LIMIT 10",
        "WITH cte AS (SELECT emp_id, doj FROM hrfin_silver.employee_master) SELECT EXTRACT(YEAR FROM doj) AS yr FROM cte",
        "SELECT name FROM hrfin_silver.employee_master WHERE name LIKE '%DROP%' -- harmless literal",
    ]
    for q in valid_queries:
        ok, err = sl.validate_sql_safety(q)
        assert ok, f"Expected valid query to pass: {q} (err={err})"

    # 2. Cross-project & unauthorized dataset bypasses (including backtick splitting)
    blocked_queries = [
        "SELECT * FROM `other-project.hrfin_gold.v_continuous_stay`",
        "SELECT * FROM `other-project`.hrfin_gold.v_continuous_stay",
        "SELECT * FROM `other-project`.`hrfin_gold`.`v_continuous_stay`",
        "SELECT * FROM other_project.hrfin_gold.v_continuous_stay",
        "SELECT * FROM `ongc-hr-finance-agent.hrfin_secret.salaries`",
        "SELECT * FROM hrfin_raw.employee_master",
        "SELECT * FROM employee_master",  # unqualified non-CTE table
        "SELECT 1 FROM hrfin_gold.v_field_pnl; SELECT * FROM hrfin_silver.employee_master",
        "SELECT 1 FROM hrfin_gold.v_field_pnl; DROP TABLE hrfin_gold.v_field_pnl",
        "DROP TABLE hrfin_gold.v_field_pnl",
        "SELECT * FROM hrfin_gold.v_field_pnl UNION ALL SELECT * FROM `evil-proj`.hrfin_gold.v_field_pnl",
        "SELECT * FROM hrfin_gold.INFORMATION_SCHEMA.TABLES",
        "SELECT EXTERNAL_QUERY('conn', 'SELECT 1') FROM hrfin_gold.v_field_pnl",
        "EXPORT DATA OPTIONS(uri='gs://bucket/*.csv') AS SELECT * FROM hrfin_gold.v_field_pnl",
    ]
    for q in blocked_queries:
        ok, err = sl.validate_sql_safety(q)
        assert not ok, f"Expected unsafe query to be blocked: {q}"
        assert err


def test_h1_2_repaired_sql_is_revalidated_before_execution():
    """Audit 2.13: If `repair_sql` produces an unsafe query, `query_data` must block it before executing."""
    mock_client = MagicMock()

    def side_effect_query(sql: str, job_config: Any = None):
        if getattr(job_config, "dry_run", False):
            job = MagicMock()
            job.total_bytes_processed = 1024
            return job
        # First execution fails so self-repair is triggered
        raise RuntimeError("Simulated syntax error in initial SQL")

    mock_client.query.side_effect = side_effect_query

    mock_gen = MagicMock()
    mock_gen.repair_sql.return_value = "SELECT * FROM `evil-proj`.hrfin_gold.v_field_pnl"

    with patch.object(SemanticLayer, "client", new_callable=lambda: property(lambda self: mock_client)):
        with patch("app.tools.sql_generator.get_sql_generator", return_value=mock_gen):
            res = query_data(
                "SELECT bad_col FROM `ongc-hr-finance-agent.hrfin_gold.v_field_pnl`",
                persona="CMD",
            )
            assert res["status"] == "error"
            # Verify that the malicious repaired query was NEVER sent to client.query()
            executed_sqls = [call.args[0] for call in mock_client.query.call_args_list]
            assert not any("evil-proj" in s for s in executed_sqls)


def test_h1_2_certified_query_parameter_injection_blocked():
    """Audit 2.13: Certified query parameters are validated against SQL injection tokens."""
    inj_attempts = [
        {"wc_id": "WC-DEL' OR '1'='1"},
        {"wc_id": "WC-DEL; DROP TABLE hrfin_silver.employee_master--"},
        {"wc_id": "WC-DEL UNION SELECT * FROM hrfin_silver.employee_master"},
        {"wc_id": "WC-DEL /* comment */"},
        {"bad;param": "WC-DEL"},
    ]
    for bad_params in inj_attempts:
        res = run_certified_query("C1", params=bad_params)
        assert res.get("type") == "error", f"Expected injection params {bad_params} to be rejected"


def test_h1_2_no_hardcoded_project_id_in_turn_runner_or_access_control():
    """Audit 2.15: Fast-path and refusal SQL strings use GCP_PROJECT from app.config."""
    backend_root = Path(__file__).resolve().parent.parent
    for rel in ("app/turn_runner.py", "app/access_control.py"):
        text = (backend_root / rel).read_text(encoding="utf-8")
        assert "ongc-hr-finance-agent" not in text, f"Found hardcoded project ID in {rel}"


# ==============================================================================
# H1.3b: Contract Validation Repair, Cache Immutability, Memory Bounds & Soak
# ==============================================================================


def test_h1_3b_contract_validation_repair():
    """Audit 2.14: Minor schema drift (e.g. language='en-IN', missing arrays) is repaired instead of raising 500."""
    drifted_contract = {
        "turn_id": "turn-test-001",
        "language": "en-IN",  # invalid enum in raw schema
        "persona": "chairman",  # unnormalized alias
        "spoken_summary": "419 executives in Delhi have stayed 5+ years.",
        "display_text": "419 executives in Delhi have stayed 5+ years. " * 20,  # > 600 chars
        "visual": {"type": "unknown_type", "mode": "bad_mode"},
        "insights": None,
        "sources": "not-a-list",
        "suggestions": None,
        "access": {"status": "invalid"},
    }
    repaired = validate_and_repair_contract(drifted_contract)
    assert repaired["language"] == "en"
    assert repaired["persona"] == "CMD"
    assert len(repaired["display_text"]) <= 600
    assert repaired["visual"]["type"] == "none"
    assert repaired["visual"]["mode"] == "replace"
    assert isinstance(repaired["insights"], list)
    assert isinstance(repaired["sources"], list)
    assert repaired["access"]["status"] == "allowed"
    # Must pass strict JSON Schema validator after repair
    get_contract_validator().validate(repaired)


def test_h1_3b_cache_immutability():
    """Audit 2.16: Mutating returned or input dicts must never corrupt cached entries."""
    # 1. ToolResultCache
    tc = ToolResultCache()
    orig_sql_res = {"status": "success", "rows": [{"a": 1}], "columns": ["a"]}
    tc.set_sql("SELECT 1", "CMD", orig_sql_res)
    orig_sql_res["rows"].append({"a": 999})  # mutate caller input after set

    fetched1 = tc.get_sql("SELECT 1", "CMD")
    assert fetched1 is not None
    assert len(fetched1["rows"]) == 1
    fetched1["rows"][0]["a"] = 42  # mutate returned dict
    fetched2 = tc.get_sql("SELECT 1", "CMD")
    assert fetched2["rows"][0]["a"] == 1

    # 2. VerifiedAnswerCache / InMemoryAnswerCache
    ac = VerifiedAnswerCache()
    ac.backend = InMemoryAnswerCache()
    sample_contract = {
        "turn_id": "t1",
        "language": "en",
        "persona": "CMD",
        "spoken_summary": "Original summary.",
        "display_text": "Original summary.",
        "visual": {"type": "table", "mode": "replace", "table": {"columns": ["x"], "rows": [{"x": 10}]}},
        "insights": ["i1"],
        "sources": [],
        "suggestions": [],
        "access": {"status": "allowed"},
        "export_options": ["pdf"],
        "status_events": ["ok"],
    }
    ac.set_answer("C1", {"wc_id": "WC-DEL"}, "CMD", sample_contract)
    sample_contract["visual"]["table"]["rows"][0]["x"] = 999
    c1 = ac.get_answer("C1", {"wc_id": "WC-DEL"}, "CMD")
    assert c1["visual"]["table"]["rows"][0]["x"] == 10
    c1["visual"]["table"]["rows"][0]["x"] = 777
    c2 = ac.get_answer("C1", {"wc_id": "WC-DEL"}, "CMD")
    assert c2["visual"]["table"]["rows"][0]["x"] == 10

    # 3. DemoCache
    dc = DemoCache()
    dc.is_enabled = True
    dc._is_loaded = True
    dc.query_to_id["test question"] = "C1"
    dc.root_entries["C1"] = {"id": "C1", "question": "Test question", "data": {"rows": [{"k": "v"}]}, "type": "data"}
    d1 = dc.match_root("Test question")
    assert d1 is not None
    d1["data"]["rows"][0]["k"] = "mutated"
    d2 = dc.match_root("Test question")
    assert d2["data"]["rows"][0]["k"] == "v"


def test_h1_3b_memory_bounds_200_turn_soak():
    """H1.3b Acceptance Criterion: Memory flat over a 200-turn soak; session/turn/visual/ADK bounds enforced."""
    sm = SessionManager(max_sessions=MAX_SESSIONS, ttl_seconds=3600)

    # 1. Create 250 sessions -> bounded at MAX_SESSIONS (200)
    for i in range(250):
        sm.get_or_create(f"sess-{i:04d}", persona="CMD", language="en")
    assert len(sm.sessions) <= MAX_SESSIONS

    # 2. 200-turn soak on a single session with large 500-row tables per turn
    tracemalloc.start()
    st: SessionState = sm.get_or_create("soak-session", persona="CMD", language="en")

    snapshot_after_warmup = None
    for turn_idx in range(1, 201):
        big_rows = [{"emp_id": f"EMP-{r:05d}", "name": f"Officer {r}", "stay": 6.5} for r in range(500)]
        contract = {
            "turn_id": f"turn-soak-{turn_idx:03d}",
            "language": "en",
            "persona": "CMD",
            "spoken_summary": f"Turn {turn_idx} summary.",
            "display_text": f"Turn {turn_idx} summary.",
            "visual": {
                "type": "table",
                "mode": "replace",
                "title": f"Turn {turn_idx} Roster",
                "table": {"columns": ["emp_id", "name", "stay"], "rows": big_rows},
            },
            "insights": ["Insight 1"],
            "sources": [{"kind": "data", "object": "hrfin_gold.ssot_workforce_employee", "sql": "SELECT 1"}],
            "suggestions": [],
            "access": {"status": "allowed"},
            "export_options": ["pdf"],
            "status_events": ["ok"],
            "all_rows": big_rows,
        }
        st.spec_history.append({"metric": "headcount", "turn": turn_idx})
        st.record_turn(contract, user_query=f"Question {turn_idx} in Delhi", all_rows=big_rows)
        # Caller's original contract visual.table.rows must NOT be mutated
        assert len(contract["visual"]["table"]["rows"]) == 500

        if turn_idx == 60:
            snapshot_after_warmup = tracemalloc.take_snapshot()

    current_mem, _peak_mem = tracemalloc.get_traced_memory()
    snapshot_end = tracemalloc.take_snapshot()
    tracemalloc.stop()

    assert len(st.turns) == MAX_SESSION_TURNS
    assert len(st.visual_history) == MAX_VISUAL_HISTORY
    assert len(st.spec_history) == MAX_SPEC_HISTORY
    # Stored turns have `all_rows` stripped and table rows capped at 50
    for stored_turn in st.turns:
        assert "all_rows" not in stored_turn
        assert len(stored_turn["visual"]["table"]["rows"]) <= 50

    # Memory growth between turn 60 (Once ring buffers are full at 50 turns) and turn 200 must be near zero (< 1 MB)
    assert snapshot_after_warmup is not None
    stats = snapshot_end.compare_to(snapshot_after_warmup, "lineno")
    net_growth_bytes = sum(s.size_diff for s in stats)
    assert net_growth_bytes < 1_000_000, f"Memory grew by {net_growth_bytes} bytes between turn 60 and 200"


# ==============================================================================
# H1.1: Async Execution & Voice Tool Calls Off the Receive Loop (< 100 ms stall)
# ==============================================================================


@pytest.mark.asyncio
async def test_h1_1_async_no_event_loop_blocking_under_3_concurrent_sessions():
    """H1.1 Acceptance Criterion: No event-loop blocking > 100 ms under 3 concurrent sessions."""
    from app.turn_runner import AgentTurnRunner

    runner = AgentTurnRunner()

    def slow_blocking_query(sql: str, title: str = "", **kwargs) -> Dict[str, Any]:
        # Simulate a 200 ms synchronous BigQuery call inside a worker thread
        time.sleep(0.20)
        return {
            "status": "success",
            "sql": sql,
            "columns": ["grade_id", "cadre", "employees"],
            "rows": [{"grade_id": "E5", "cadre": "Executive", "employees": 120}],
            "all_rows": [{"grade_id": "E5", "cadre": "Executive", "employees": 120}],
        }

    max_loop_stall_ms = 0.0
    stop_monitor = False

    async def loop_lag_monitor():
        nonlocal max_loop_stall_ms
        interval = 0.010  # 10 ms tick
        last = time.perf_counter()
        while not stop_monitor:
            await asyncio.sleep(interval)
            now = time.perf_counter()
            stall_ms = max(0.0, (now - last - interval) * 1000.0)
            if stall_ms > max_loop_stall_ms:
                max_loop_stall_ms = stall_ms
            last = now

    monitor_task = asyncio.create_task(loop_lag_monitor())
    try:
        with patch("app.turn_runner.planner_enabled", return_value=False):
            with patch("app.tools.query_data.query_data", side_effect=slow_blocking_query):
                t_start = time.perf_counter()
                results = await asyncio.gather(
                    runner.execute_turn_async("How many employees are in Ahmedabad?", session_id="conc-1", persona="CMD"),
                    runner.execute_turn_async("How many employees are in Mumbai?", session_id="conc-2", persona="DIR_HR"),
                    runner.execute_turn_async("How many employees are in Dehradun?", session_id="conc-3", persona="DIR_FIN"),
                )
                elapsed_s = time.perf_counter() - t_start
    finally:
        stop_monitor = True
        await monitor_task

    assert len(results) == 3
    for r in results:
        assert r["visual"]["type"] in ("chart", "table", "kpi")
    # Because all 3 sessions run their 2x 200ms queries via asyncio.to_thread + asyncio.gather,
    # total wall time is ~0.25s instead of 1.2s, and max event-loop stall is well below 100 ms.
    assert max_loop_stall_ms < 100.0, f"Event loop blocked for {max_loop_stall_ms:.1f} ms (> 100 ms limit)"
    assert elapsed_s < 0.80, f"3 concurrent sessions took {elapsed_s:.2f}s (expected parallel execution < 0.8s)"


@pytest.mark.asyncio
async def test_h1_1_voice_tool_call_off_receive_loop_allows_immediate_barge_in():
    """H1.1 / Audit 2.11: A slow voice tool call does not block `session.receive()` from processing `interrupted`."""
    from app.live_session import LiveSessionManager

    sent_messages: List[Dict[str, Any]] = []

    class DummyWebSocket:
        async def send_text(self, text: str) -> None:
            import json
            sent_messages.append(json.loads(text))

    mgr = LiveSessionManager(DummyWebSocket(), session_id="voice-h1-test")

    tool_started = asyncio.Event()
    interrupted_sent = asyncio.Event()

    async def slow_voice_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        tool_started.set()
        await asyncio.sleep(0.35)  # 350 ms tool call
        return {"status": "OK", "spoken_summary": "Done"}

    mgr._execute_voice_tool = slow_voice_tool  # type: ignore[method-assign]

    # Build a mock Gemini Live session whose receive() yields a tool_call and then an interrupted frame 20ms later
    class FakeLiveSession:
        def __init__(self):
            self.tool_responses = []

        async def send_tool_response(self, function_responses: Any) -> None:
            self.tool_responses.append(function_responses)

        async def receive(self):
            fc = SimpleNamespace(name="ask_yukti", args={"query": "Delhi tenure"}, id="fc-1")
            yield SimpleNamespace(
                session_resumption_update=None,
                go_away=None,
                tool_call=SimpleNamespace(function_calls=[fc]),
                server_content=None,
            )
            await tool_started.wait()
            await asyncio.sleep(0.02)
            yield SimpleNamespace(
                session_resumption_update=None,
                go_away=None,
                tool_call=None,
                server_content=SimpleNamespace(
                    interrupted=True,
                    input_transcription=None,
                    output_transcription=None,
                    model_turn=None,
                    turn_complete=False,
                ),
            )
            # Keep session open briefly then close
            await asyncio.sleep(0.05)
            mgr.active = False

    orig_send_json = mgr.send_json
    t_interrupted_at: float = 0.0

    async def tracked_send_json(payload: Dict[str, Any]) -> bool:
        nonlocal t_interrupted_at
        if payload.get("type") == "interrupted":
            t_interrupted_at = time.perf_counter()
            interrupted_sent.set()
        return await orig_send_json(payload)

    mgr.send_json = tracked_send_json  # type: ignore[method-assign]

    t0 = time.perf_counter()
    fake_session = FakeLiveSession()
    await mgr._run_bidi_stream(fake_session)

    assert interrupted_sent.is_set(), "Expected `interrupted` message to be forwarded to client"
    latency_to_interrupt_ms = (t_interrupted_at - t0) * 1000.0
    # Because the tool call (350 ms) runs in a background task, `interrupted` arrives in ~25 ms (< 100 ms)!
    assert latency_to_interrupt_ms < 100.0, (
        f"`interrupted` frame was delayed by {latency_to_interrupt_ms:.1f} ms (tool call blocked receive loop!)"
    )


@pytest.mark.asyncio
async def test_h1_1_apply_screen_control_checks_error_status():
    """Audit 2.12: `_apply_screen_control` returns ERROR without emitting bogus ui_action when run_ui_control fails."""
    from app.live_session import LiveSessionManager

    sent: List[Dict[str, Any]] = []

    class DummyWS:
        async def send_text(self, text: str) -> None:
            import json
            sent.append(json.loads(text))

    mgr = LiveSessionManager(DummyWS(), session_id="sc-err-test")
    res = await mgr._apply_screen_control("nonexistent_command_xyz", "foo")
    assert res["status"] == "ERROR"
    assert not any(m.get("type") == "ui_action" for m in sent)
