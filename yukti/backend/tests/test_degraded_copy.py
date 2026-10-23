"""P0.1 (BUG-01, BUG-33): /health auth status and safe user-facing error copy.

Offline: no ADC, BigQuery or Gemini call is made (the ADK runner is replaced by a stub that raises).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.auth.exceptions import DefaultCredentialsError, RefreshError  # noqa: E402

from app.turn_runner import E_AUTH_COPY, GENERIC_ERROR_COPY, AgentTurnRunner, safe_error_copy  # noqa: E402

LEAK_MARKERS = ("Reauthentication", "RefreshError", "Traceback", "secret-project-123", "ongc-hr-finance-agent")


def _assert_no_leak(text: str) -> None:
    for marker in LEAK_MARKERS:
        assert marker not in text, f"leaked {marker!r} in {text!r}"


@pytest.mark.parametrize("lang", ["en", "hi", "hi-en"])
def test_refresh_error_maps_to_e_auth(lang):
    txt = safe_error_copy(RefreshError("Reauthentication is needed. Please run `gcloud auth application-default login`"), lang)
    assert txt == (E_AUTH_COPY["hi"] if lang == "hi" else E_AUTH_COPY["en"])
    _assert_no_leak(txt)


def test_chained_and_other_auth_errors_map_to_e_auth():
    from google.api_core.exceptions import Forbidden, ServiceUnavailable, Unauthorized

    for exc in (DefaultCredentialsError("no ADC"), Forbidden("403 project ongc-hr-finance-agent"),
                Unauthorized("401"), ServiceUnavailable("503")):
        assert safe_error_copy(exc) == E_AUTH_COPY["en"]
    try:
        try:
            raise RefreshError("Reauthentication is needed")
        except RefreshError as inner:
            raise RuntimeError("wrapped") from inner
    except RuntimeError as outer:
        assert safe_error_copy(outer) == E_AUTH_COPY["en"]


def test_generic_error_never_echoes_message():
    txt = safe_error_copy(ValueError("secret-project-123"), "en")
    assert txt == GENERIC_ERROR_COPY["en"]
    _assert_no_leak(txt)
    assert safe_error_copy(ValueError("secret-project-123"), "hi") == GENERIC_ERROR_COPY["hi"]


def _raising_run_async(exc):
    def run_async(**_kwargs):
        async def _gen():
            raise exc
            yield  # pragma: no cover

        return _gen()

    return run_async


@pytest.mark.asyncio
@pytest.mark.parametrize("exc,expected", [
    (RefreshError("Reauthentication is needed. Please run gcloud auth"), E_AUTH_COPY["en"]),
    (ValueError("secret-project-123"), GENERIC_ERROR_COPY["en"]),
])
async def test_turn_contract_uses_safe_copy(monkeypatch, exc, expected):
    monkeypatch.setenv("YUKTI_PLANNER", "0")
    runner = AgentTurnRunner(model_name="gemini-2.5-flash")
    monkeypatch.setattr(runner.runner, "run_async", _raising_run_async(exc))
    res = await runner.execute_turn_async(
        "Explain the philosophy behind our quarterly review rituals in one line",
        session_id=f"test-degraded-{type(exc).__name__}", persona="CMD",
    )
    assert "Execution error in BigQuery tool" in res["status_events"]  # the ADK error path was taken
    assert res["display_text"] == expected
    assert res["spoken_summary"] == expected
    for field in ("display_text", "spoken_summary"):
        _assert_no_leak(str(res.get(field, "")))


def test_health_reports_auth_fields_without_error_text(monkeypatch):
    from fastapi.testclient import TestClient

    from app import main

    monkeypatch.setenv("YUKTI_FORCE_ADC_FAIL", "1")
    client = TestClient(main.app)
    body = client.get("/health").json()
    assert body["auth_ok"] is False
    assert body["auth_mode"] == "demo"
    _assert_no_leak({k: v for k, v in body.items() if k != "project"}.__repr__())

    # Cached success path: no exception text either way
    monkeypatch.delenv("YUKTI_FORCE_ADC_FAIL")
    main._auth_cache.update({"ok": True, "ts": __import__("time").monotonic()})
    body = client.get("/health").json()
    assert body["auth_ok"] is True


@pytest.mark.asyncio
async def test_voice_tool_failure_never_leaks_exception_text(monkeypatch):
    """P0.1 r2 (G4 must-fix 1): a failing Gemini Live tool sends safe copy to the UI socket and the model."""
    import json as _json

    import app.turn_runner as tr
    from app.live_session import LiveSessionManager

    class _Boom:
        async def execute_turn_async(self, **_kw):
            raise RefreshError("Reauthentication is needed. Please run gcloud auth application-default login")

    monkeypatch.setattr(tr, "get_agent_turn_runner", lambda *a, **k: _Boom())
    sent = []

    class DummyWS:
        async def send_text(self, text: str) -> None:
            sent.append(_json.loads(text))

    mgr = LiveSessionManager(DummyWS(), session_id="p01-voice-tool-err")
    res = await mgr._execute_voice_tool("ask_yukti", {"query": "How many executives are posted in Delhi?"})
    assert res["status"] == "ERROR" and res["error"] == "E-AUTH"
    assert res["spoken_summary"] == E_AUTH_COPY["en"]
    _assert_no_leak(_json.dumps(res))
    _assert_no_leak(_json.dumps(sent))
