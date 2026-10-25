import base64
import json
import time
import pytest
from fastapi.testclient import TestClient
from app import auth
from app.main import app
from app.jobs.store import reset_store_for_tests, get_job_store
from app.jobs.executor import get_executor
from app.jobs.events import get_event_broker
from app.session_memory import get_session_manager

client = TestClient(app)


def _auth_headers(persona: str) -> dict:
    return {"Authorization": f"Bearer {auth.issue_token(persona)}"}


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
    cmd_headers = _auth_headers("CMD")
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
        resp = live_client.post(
            "/api/jobs",
            json={"proposed_action_id": "pa_1", "session_id": "sess_1"},
            headers=cmd_headers,
        )
        assert resp.status_code == 202
        job_id = resp.json()["job"]["id"]
        assert job_id.startswith("job_")

        # Repeat POST /api/jobs with same proposed_action_id -> 202 same job_id (idempotent)
        resp_repeat = live_client.post(
            "/api/jobs",
            json={"proposed_action_id": "pa_1", "session_id": "sess_1"},
            headers=cmd_headers,
        )
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
        r_denied = client.post(
            "/api/jobs",
            json={"proposed_action_id": "pa_denied", "session_id": sid},
            headers=_auth_headers(denied_persona),
        )
        assert r_denied.status_code == 403

    # 410 Gone for expired proposal
    sess.pending_actions["pa_expired"] = {
        "id": "pa_expired",
        "agent": "dcf_agent",
        "requires_role": ["CMD", "DIR_FIN"],
        "inputs": {},
        "expires_at": "2020-01-01T00:00:00Z",
    }
    r_exp = client.post(
        "/api/jobs",
        json={"proposed_action_id": "pa_expired", "session_id": "sess_1"},
        headers=cmd_headers,
    )
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
    r_422 = client.post(
        "/api/jobs",
        json={
            "proposed_action_id": "pa_override",
            "session_id": "sess_1",
            "inputs_override": {"wacc_pct": 25.0},
        },
        headers=cmd_headers,
    )
    assert r_422.status_code == 422


def test_sse_events_and_rehydration():
    sm = get_session_manager()
    sess = sm.get_or_create("sess_1", persona="DIR_FIN")
    dir_fin_headers = _auth_headers("DIR_FIN")
    sess.pending_actions["pa_1"] = {
        "id": "pa_1",
        "agent": "dcf_agent",
        "requires_role": ["CMD", "DIR_FIN"],
        "inputs": {},
    }

    with TestClient(app) as live_client:
        resp = live_client.post(
            "/api/jobs",
            json={"proposed_action_id": "pa_1", "session_id": "sess_1"},
            headers=dir_fin_headers,
        )
        assert resp.status_code == 202
        job_id = resp.json()["job"]["id"]

        with live_client.stream("GET", f"/api/jobs/{job_id}/events", headers=dir_fin_headers) as sse_resp:
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
        r_list = live_client.get("/api/jobs", params={"session_id": "sess_1"}, headers=dir_fin_headers)
        assert r_list.status_code == 200
        jobs = r_list.json()["jobs"]
        assert len(jobs) == 1
        assert jobs[0]["id"] == job_id
        assert jobs[0]["status"] == "succeeded"

        r_res = live_client.get(f"/api/jobs/{job_id}/result", headers=dir_fin_headers)
        assert r_res.status_code == 200
        contract = r_res.json()
        assert contract["turn_id"] == f"job:{job_id}"
        assert contract["visual"]["type"] == "dcf_model"
        # P5.6 D2 contract check: visual.dcf_model must be populated for AnswerCard.tsx:625 -> DcfModelCard
        dcf_model = contract["visual"].get("dcf_model")
        assert isinstance(dcf_model, dict)
        assert "per_share" in dcf_model and dcf_model["per_share"]["intrinsic_inr"] > 0
        assert "wacc_build" in dcf_model and abs(dcf_model["wacc_build"]["wacc_pct"] - 11.6556) < 1e-3
        assert "forecast" in dcf_model and "years" in dcf_model["forecast"] and "lines" in dcf_model["forecast"]
        assert len(dcf_model["forecast"]["lines"]["pv_fcff"]) == len(dcf_model["forecast"]["years"])
        assert "terminal" in dcf_model and "pv_tv_inr_cr" in dcf_model["terminal"]
        assert "bridge" in dcf_model and isinstance(dcf_model["bridge"], list)
        assert "sensitivity_grid" in dcf_model and "cells" in dcf_model["sensitivity_grid"]
        assert "tornado" in dcf_model and "bars" in dcf_model["tornado"]
        assert "Illustrative valuation, not investment advice." in contract["spoken_summary"]


def test_cancel_action_and_cancel_job():
    sm = get_session_manager()
    sess = sm.get_or_create("sess_cancel", persona="CMD")
    cmd_headers = _auth_headers("CMD")
    sess.pending_actions["pa_cancel"] = {
        "id": "pa_cancel",
        "agent": "dcf_agent",
        "requires_role": ["CMD", "DIR_FIN"],
        "inputs": {},
    }
    r_act = client.post("/api/actions/pa_cancel/cancel", headers=cmd_headers)
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
        "owner_persona": "CMD",
        "agent": "dcf_agent",
        "status": "running",
        "progress": 0.25,
    })
    r_jc = client.post("/api/jobs/job_manual_cancel/cancel", headers=cmd_headers)
    assert r_jc.status_code == 200
    assert r_jc.json()["job"]["status"] == "cancelled"


def test_s2_security_attacks_and_session_ownership():
    """P5.6 S2: forged bearer -> 401; E1_HR on CMD pending action -> 403; E1_HR reading/cancelling CMD job -> 403; persona switch clears state."""
    sm = get_session_manager()
    cmd_principal = auth.verify_token(auth.issue_token("CMD"))
    cmd_sess = sm.get_or_create("sess_cmd", persona="CMD")
    cmd_sess.ensure_principal("CMD", cmd_principal.emp_id)
    cmd_sess.pending_actions["pa_cmd"] = {
        "id": "pa_cmd",
        "agent": "dcf_agent",
        "requires_role": ["CMD", "DIR_FIN"],
        "inputs": {},
        "expires_at": "2099-01-01T00:00:00Z",
    }

    # 1. Forged or missing bearer on POST /api/jobs -> 401 (never falls back to session.persona)
    r_no_auth = client.post("/api/jobs", json={"proposed_action_id": "pa_cmd", "session_id": "sess_cmd"})
    assert r_no_auth.status_code == 401

    r_forged = client.post(
        "/api/jobs",
        json={"proposed_action_id": "pa_cmd", "session_id": "sess_cmd"},
        headers={"Authorization": "Bearer forged.invalid.token"},
    )
    assert r_forged.status_code == 401

    # 2. E1_HR on CMD's pending action -> 403
    e1_hr_headers = _auth_headers("E1_HR")
    r_e1_post = client.post(
        "/api/jobs",
        json={"proposed_action_id": "pa_cmd", "session_id": "sess_cmd"},
        headers=e1_hr_headers,
    )
    assert r_e1_post.status_code == 403

    # Non-owner cancel of CMD's pending action -> 403 (with or without session_id)
    r_e1_cancel_act_no_sid = client.post("/api/actions/pa_cmd/cancel", headers=e1_hr_headers)
    assert r_e1_cancel_act_no_sid.status_code == 403
    r_e1_cancel_act_with_sid = client.post(
        "/api/actions/pa_cmd/cancel",
        params={"session_id": "sess_cmd"},
        headers=e1_hr_headers,
    )
    assert r_e1_cancel_act_with_sid.status_code == 403
    assert "pa_cmd" in cmd_sess.pending_actions

    # Create job as legitimate owner (CMD via same-origin cookie + Cloud Run RS256 bearer)
    rs256_hdr = base64.urlsafe_b64encode(json.dumps({"alg": "RS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    rs256_pay = base64.urlsafe_b64encode(json.dumps({"sub": "proxy", "iat": int(time.time()), "exp": int(time.time()) + 3600}).encode()).rstrip(b"=").decode()
    cmd_cookie = auth.issue_token("CMD")
    cmd_cookie_headers = {
        "Authorization": f"Bearer {rs256_hdr}.{rs256_pay}.sig",
        "Cookie": f"{auth.COOKIE_NAME}={cmd_cookie}",
    }

    with TestClient(app) as live_client:
        r_ok = live_client.post(
            "/api/jobs",
            json={"proposed_action_id": "pa_cmd", "session_id": "sess_cmd"},
            headers=cmd_cookie_headers,
        )
        assert r_ok.status_code == 202
        job_id = r_ok.json()["job"]["id"]

        # 3. E1_HR reading CMD's job, with or without session_id -> 403
        for params in ({}, {"session_id": "sess_cmd"}):
            assert live_client.get(f"/api/jobs/{job_id}", params=params, headers=e1_hr_headers).status_code == 403
            assert live_client.get(f"/api/jobs/{job_id}/result", params=params, headers=e1_hr_headers).status_code == 403
            assert live_client.get(f"/api/jobs/{job_id}/events", params=params, headers=e1_hr_headers).status_code == 403

        assert live_client.get("/api/jobs", params={"session_id": "sess_cmd"}, headers=e1_hr_headers).status_code == 403

        # 4. Cancel job by non-owner (E1_HR), with or without session_id -> 403
        for params in ({}, {"session_id": "sess_cmd"}):
            assert live_client.post(f"/api/jobs/{job_id}/cancel", params=params, headers=e1_hr_headers).status_code == 403

    # 5. SessionState.ensure_principal() clears pending_actions and jobs on persona switch
    cmd_sess.pending_actions["pa_leftover"] = {"id": "pa_leftover", "agent": "dcf_agent"}
    cmd_sess.jobs = {"job_leftover": {"id": "job_leftover"}}
    cmd_sess.last_agent_result = {"turn_id": "job:job_leftover"}
    assert len(cmd_sess.pending_actions) > 0
    assert len(cmd_sess.jobs) > 0
    cmd_sess.ensure_principal("E1_HR", "EMP-000004")
    assert len(cmd_sess.pending_actions) == 0
    assert len(cmd_sess.jobs) == 0
    assert cmd_sess.last_agent_result is None

