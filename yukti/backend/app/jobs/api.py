from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import logging
from fastapi import APIRouter, HTTPException, Header, Request, Query, Body
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
import json

from app.jobs.executor import get_executor
from app.jobs.store import get_job_store
from app.jobs.events import get_event_broker
from app.session_memory import get_session_manager

logger = logging.getLogger("yukti.jobs.api")
router = APIRouter()


class CreateJobRequest(BaseModel):
    proposed_action_id: str
    session_id: Optional[str] = None
    inputs_override: Optional[Dict[str, Any]] = None


def _validate_inputs_override(
    editable_inputs: List[Dict[str, Any]],
    overrides: Dict[str, Any],
) -> None:
    if not overrides:
        return
    spec_by_key = {item["key"]: item for item in (editable_inputs or []) if "key" in item}
    for key, val in overrides.items():
        if spec_by_key and key not in spec_by_key:
            raise HTTPException(status_code=422, detail=f"Input '{key}' is not editable")
        spec = spec_by_key.get(key)
        if not spec:
            continue
        inp_type = spec.get("type")
        if inp_type in ("number", "percent"):
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise HTTPException(status_code=422, detail=f"Input '{key}' must be numeric")
            if spec.get("min") is not None and float(val) < float(spec["min"]):
                raise HTTPException(status_code=422, detail=f"Input '{key}' below minimum {spec['min']}")
            if spec.get("max") is not None and float(val) > float(spec["max"]):
                raise HTTPException(status_code=422, detail=f"Input '{key}' above maximum {spec['max']}")
        elif inp_type == "enum" and spec.get("options"):
            if val not in spec["options"]:
                raise HTTPException(status_code=422, detail=f"Input '{key}' not in allowed options")


def _is_expired(expires_at: Optional[str]) -> bool:
    if not expires_at:
        return False
    try:
        dt = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt <= datetime.now(timezone.utc)
    except ValueError:
        return False


def _find_session_for_action(sm, action_id: str, session_id: Optional[str] = None):
    if session_id and session_id in sm.sessions:
        return sm.sessions[session_id]
    for sess in sm.sessions.values():
        if action_id in getattr(sess, "pending_actions", {}):
            return sess
    if session_id:
        return sm.get_or_create(session_id)
    return None


@router.post("/api/jobs", status_code=202)
async def create_job(req: CreateJobRequest, request: Request):
    sm = get_session_manager()
    session = _find_session_for_action(sm, req.proposed_action_id, req.session_id)
    if session is None:
        raise HTTPException(status_code=410, detail="Proposal not found or expired")

    pa = session.pending_actions.get(req.proposed_action_id)
    if not pa:
        raise HTTPException(status_code=410, detail="Proposal not found or expired")

    if _is_expired(pa.get("expires_at")):
        raise HTTPException(status_code=410, detail="Proposal expired")

    # Server-side RBAC re-check: persona comes strictly from server session (never request body)
    server_persona = str(getattr(session, "persona", "E2_HR") or "E2_HR").upper()
    requires_role = [str(r).upper() for r in (pa.get("requires_role") or [])]
    if requires_role and server_persona not in requires_role:
        logger.warning(
            "RBAC 403 on POST /api/jobs: session=%s persona=%s proposed_action_id=%s requires_role=%s",
            session.session_id,
            server_persona,
            req.proposed_action_id,
            requires_role,
        )
        raise HTTPException(status_code=403, detail="Current role is not authorised to run this agent")

    if req.inputs_override is not None:
        _validate_inputs_override(pa.get("editable_inputs") or [], req.inputs_override)

    executor = get_executor()
    try:
        pa_to_run = dict(pa)
        base_inputs = dict(pa.get("inputs") or {})
        if req.inputs_override:
            base_inputs.update(req.inputs_override)
        pa_to_run["inputs"] = base_inputs
        job = await executor.submit_job(pa_to_run, session.session_id)
        return {"job": job}
    except ValueError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception:
        logger.exception("Failed to submit job for proposal %s", req.proposed_action_id)
        raise HTTPException(status_code=500, detail="Could not start background job. Please try again.")


@router.get("/api/jobs/{job_id}")
async def get_job(job_id: str, session_id: Optional[str] = Query(default=None)):
    store = get_job_store()
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if session_id and job.get("session_id") and job.get("session_id") != session_id:
        sm = get_session_manager()
        caller_sess = sm.sessions.get(session_id)
        if not caller_sess or getattr(caller_sess, "persona", "") != "CMD":
            raise HTTPException(status_code=403, detail="Forbidden")
    return {"job": job}


@router.get("/api/jobs/{job_id}/events")
async def get_job_events(
    job_id: str,
    request: Request,
    last_event_id: Optional[str] = Header(default=None, alias="Last-Event-ID"),
):
    store = get_job_store()
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    broker = get_event_broker()

    async def event_generator():
        async for msg in broker.subscribe(job_id, last_event_id=last_event_id):
            if "comment" in msg:
                yield f": {msg['comment']}\n\n"
            else:
                ev_id = msg.get("id")
                id_line = f"id: {ev_id}\n" if ev_id else ""
                yield f"{id_line}event: {msg['event']}\ndata: {json.dumps(msg['data'])}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    store = get_job_store()
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    executor = get_executor()
    executor.cancel_job(job_id)
    return {"job": store.get_job(job_id)}


@router.get("/api/jobs")
async def list_jobs(session_id: str = Query(...)):
    store = get_job_store()
    jobs = store.list_jobs(session_id)
    return {"jobs": jobs}


@router.get("/api/jobs/{job_id}/result")
async def get_job_result(job_id: str):
    store = get_job_store()
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = job.get("result")
    if not result:
        raise HTTPException(status_code=404, detail="Result not found or job not finished")
    return result


@router.post("/api/actions/{action_id}/cancel", status_code=204)
async def cancel_action(
    action_id: str,
    session_id: Optional[str] = Query(default=None),
    body: Optional[Dict[str, Any]] = Body(default=None),
):
    sm = get_session_manager()
    sid = session_id or (body.get("session_id") if isinstance(body, dict) else None)
    session = _find_session_for_action(sm, action_id, sid)
    if session and action_id in session.pending_actions:
        del session.pending_actions[action_id]
    return Response(status_code=204)
