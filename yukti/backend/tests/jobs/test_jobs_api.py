import json
import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.jobs.store import reset_store_for_tests, get_job_store
from app.jobs.executor import get_executor
from app.jobs.events import get_event_broker
from app.session_memory import get_session_manager

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup():
    reset_store_for_tests()
    get_event_broker().clear()
    executor = get_executor()
    executor.store = get_job_store()
    executor._running_tasks.clear()
    executor.step_delay_sec = 0.01
    sm = get_session_manager()
    sm.sessions.clear()
    yield


def test_create_job_idempotency_and_rbac_403_410_422():
    sm = get_session_manager()
    sess = sm.get_or_create("sess_1", persona="CMD")
    sess.pending_actions["pa_1"] = {
        "id": "pa_1",
        "agent": "dcf_agent",
        "requires_role": ["CMD", "DIR_FIN"],
        "inputs": {"wacc_pct": 10.5, "terminal_g_pct": 3.0},
        "editable_inputs": [
            {"key": "wacc_pct", "label": "WACC (%)", "type": "percent", "value": 10.5, "min": 6.0, "max": 16.0},
            {"key": "terminal_g_pct", "label": "Terminal g (%)", "type": "percent", "value": 3.0, "min": 0.0, "max": 6.0},
        ],
        "expires_at": "2099-01-01T00:00:00Z",
    }

    with TestClient(app) as live_client:
        resp = live_client.post("/api/jobs", json={
            "proposed_action_id": "pa_1",
            "session_id": "sess_1"
        })
        assert resp.status_code == 202
        job_id = resp.json()["job"]["id"]
        assert job_id.startswith("job_")

        # Repeat POST /api/jobs with same proposed_action_id -> 202 same job_id (idempotent)
        resp_repeat = live_client.post("/api/jobs", json={
            "proposed_action_id": "pa_1",
            "session_id": "sess_1"
        })
        assert resp_repeat.status_code == 202
        assert resp_repeat.json()["job"]["id"] == job_id

    # 403 Forbidden for E2_FIN, E1_HR, DIR_HR (SPEC-03 AC-03)
    for denied_persona in ("E2_FIN", "E1_HR", "DIR_HR"):
        sid = f"sess_{denied_persona}"
        s_denied = sm.get_or_create(sid, persona=denied_persona)
        s_denied.pending_actions["pa_denied"] = {
            "id": "pa_denied",
            "agent": "dcf_agent",
            "requires_role": ["CMD", "DIR_FIN"],
            "inputs": {},
        }
        r_denied = client.post("/api/jobs", json={
            "proposed_action_id": "pa_denied",
            "session_id": sid,
        })
        assert r_denied.status_code == 403

    # 410 Gone for expired proposal
    sess.pending_actions["pa_expired"] = {
        "id": "pa_expired",
        "agent": "dcf_agent",
        "requires_role": ["CMD", "DIR_FIN"],
        "inputs": {},
        "expires_at": "2020-01-01T00:00:00Z",
    }
    r_exp = client.post("/api/jobs", json={
        "proposed_action_id": "pa_expired",
        "session_id": "sess_1",
    })
    assert r_exp.status_code == 410

    # 422 Unprocessable Entity for out-of-range inputs_override
    sess.pending_actions["pa_override"] = {
        "id": "pa_override",
        "agent": "dcf_agent",
        "requires_role": ["CMD", "DIR_FIN"],
        "inputs": {"wacc_pct": 10.5},
        "editable_inputs": [
            {"key": "wacc_pct", "label": "WACC (%)", "type": "percent", "value": 10.5, "min": 6.0, "max": 16.0},
        ],
        "expires_at": "2099-01-01T00:00:00Z",
    }
    r_422 = client.post("/api/jobs", json={
        "proposed_action_id": "pa_override",
        "session_id": "sess_1",
        "inputs_override": {"wacc_pct": 25.0},
    })
    assert r_422.status_code == 422


def test_sse_events_and_rehydration():
    sm = get_session_manager()
    sess = sm.get_or_create("sess_1", persona="DIR_FIN")
    sess.pending_actions["pa_1"] = {
        "id": "pa_1",
        "agent": "dcf_agent",
        "requires_role": ["CMD", "DIR_FIN"],
        "inputs": {},
    }

    with TestClient(app) as live_client:
        resp = live_client.post("/api/jobs", json={
            "proposed_action_id": "pa_1",
            "session_id": "sess_1",
        })
        assert resp.status_code == 202
        job_id = resp.json()["job"]["id"]

        with live_client.stream("GET", f"/api/jobs/{job_id}/events") as sse_resp:
            assert sse_resp.status_code == 200
            event_types = []
            step_events = []
            for line in sse_resp.iter_lines():
                if line.startswith("event: "):
                    event_types.append(line[7:].strip())
                elif line.startswith("data: "):
                    payload = json.loads(line[6:])
                    if "step" in payload:
                        step_events.append(payload)

        # SPEC-03 AC-05: >= 1 event per step (8 DCF steps) and job.completed
        assert "job.completed" in event_types
        assert len(step_events) >= 8

        # Rehydration via GET /api/jobs?session_id= and GET /api/jobs/{id}/result (SPEC-03 AC-07)
        r_list = live_client.get("/api/jobs", params={"session_id": "sess_1"})
        assert r_list.status_code == 200
        jobs = r_list.json()["jobs"]
        assert len(jobs) == 1
        assert jobs[0]["id"] == job_id
        assert jobs[0]["status"] == "succeeded"

        r_res = live_client.get(f"/api/jobs/{job_id}/result")
        assert r_res.status_code == 200
        contract = r_res.json()
        assert contract["turn_id"] == f"job:{job_id}"
        assert contract["visual"]["type"] == "dcf_model"
        assert "Illustrative valuation, not investment advice." in contract["spoken_summary"]


def test_cancel_action_and_cancel_job():
    sm = get_session_manager()
    sess = sm.get_or_create("sess_cancel", persona="CMD")
    sess.pending_actions["pa_cancel"] = {
        "id": "pa_cancel",
        "agent": "dcf_agent",
        "requires_role": ["CMD", "DIR_FIN"],
        "inputs": {},
    }
    r_act = client.post("/api/actions/pa_cancel/cancel")
    assert r_act.status_code == 204
    assert "pa_cancel" not in sess.pending_actions

    sess.pending_actions["pa_job_cancel"] = {
        "id": "pa_job_cancel",
        "agent": "dcf_agent",
        "requires_role": ["CMD", "DIR_FIN"],
        "inputs": {},
    }
    store = get_job_store()
    store.create_job({
        "id": "job_manual_cancel",
        "session_id": "sess_cancel",
        "agent": "dcf_agent",
        "status": "running",
        "progress": 0.25,
    })
    r_jc = client.post("/api/jobs/job_manual_cancel/cancel")
    assert r_jc.status_code == 200
    assert r_jc.json()["job"]["status"] == "cancelled"
