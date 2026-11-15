"""Access requests (15-Nov, sponsor demo): an E1–E4 officer whose answer was refused or reduced to aggregates
(`access.status` refused / partial) can ask the function's Director / Executive Director for access.

Demo scope (sponsor decision 15-Nov): the request and the decision are real and audited, but an approval does NOT
unlock the restricted data in Yukti — it records the decision and tells the officer that the data will be shared
through the official HR / Finance channel. Names stay masked for E1–E4 in every case (D-11).

Routing: HR officers -> Director (HR) / Executive Director (HR); Finance officers -> Director (Finance) /
Executive Director (Finance). CMD can see and decide every request. The store is in memory (Cloud Run runs a single
instance, `--max-instances=1`); requests are cleared when the service restarts.
"""

from __future__ import annotations

import hashlib
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Request

from app.auth import Principal, audit, require_principal

router = APIRouter()

APPROVER_PERSONAS: Dict[str, List[str]] = {"HR": ["DIR_HR"], "FIN": ["DIR_FIN"]}
APPROVER_LABEL: Dict[str, str] = {
    "HR": "Director (HR) / Executive Director (HR)",
    "FIN": "Director (Finance) / Executive Director (Finance)",
}
JUNIOR_PREFIXES = ("E1_", "E2_", "E3_", "E4_")
MAX_REQUESTS = 500

_LOCK = threading.Lock()
_STORE: Dict[str, Dict[str, Any]] = {}


def _function_of(p: Principal) -> str:
    fn = (p.function or "").upper()
    if fn in APPROVER_LABEL:
        return fn
    return "FIN" if p.persona.upper().endswith("_FIN") else "HR"


def _is_junior(p: Principal) -> bool:
    return p.persona.upper().startswith(JUNIOR_PREFIXES)


def _can_decide(p: Principal, req: Dict[str, Any]) -> bool:
    persona = p.persona.upper()
    if persona == "CMD":
        return True
    return persona in APPROVER_PERSONAS.get(req["function"], [])


def _clip(v: Any, n: int) -> str:
    return str(v or "").strip()[:n]


def _view(req: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in req.items() if not k.startswith("_")}


@router.post("/api/access-requests", status_code=201)
def create_access_request(request: Request, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    p = require_principal(request)
    if not _is_junior(p):
        raise HTTPException(status_code=400, detail={"type": "error", "message": "Your role already has this access."})
    fn = _function_of(p)
    turn_id = _clip(body.get("turn_id"), 120)
    with _LOCK:
        # one open request per answer card: a second click returns the existing request
        for r in _STORE.values():
            if r["requester"]["emp_id"] == p.emp_id and r["turn_id"] == turn_id and turn_id and r["status"] == "pending":
                return _view(r)
        rid = f"AR-{uuid.uuid4().hex[:6].upper()}"
        now = time.time()
        req = {
            "id": rid,
            "status": "pending",
            "created_at": now,
            "decided_at": None,
            "function": fn,
            "approver_label": APPROVER_LABEL[fn],
            "requester": {
                "emp_id": p.emp_id,
                "persona": p.persona,
                "display_name": p.display_name,
                "designation": p.functional_designation or p.designation,
            },
            "turn_id": turn_id,
            "question": _clip(body.get("question"), 400),
            "subject": _clip(body.get("subject"), 200),
            "code": _clip(body.get("code"), 40),
            "rule_ref": _clip(body.get("rule_ref"), 300),
            "reason": _clip(body.get("reason"), 400),
            "decided_by": None,
            "note": "",
            "outcome": f"Waiting for {APPROVER_LABEL[fn]}.",
        }
        _STORE[rid] = req
        if len(_STORE) > MAX_REQUESTS:
            for old in sorted(_STORE.values(), key=lambda r: r["created_at"])[: len(_STORE) - MAX_REQUESTS]:
                _STORE.pop(old["id"], None)
    audit("access_request_created", p, turn_id=turn_id, decision="pending", rule_ref=req["rule_ref"],
          request_id=rid, code=req["code"], approver=req["approver_label"],
          question_sha256=hashlib.sha256(req["question"].encode("utf-8")).hexdigest()[:16])
    return _view(req)


@router.get("/api/access-requests")
def list_access_requests(request: Request) -> Dict[str, Any]:
    p = require_principal(request)
    with _LOCK:
        items = list(_STORE.values())
    if _is_junior(p):
        mine = [r for r in items if r["requester"]["emp_id"] == p.emp_id]
        role = "requester"
    else:
        mine = [r for r in items if _can_decide(p, r)]
        role = "approver"
    mine.sort(key=lambda r: r["created_at"], reverse=True)
    return {
        "role": role,
        "pending": sum(1 for r in mine if r["status"] == "pending"),
        "requests": [_view(r) for r in mine[:50]],
    }


@router.post("/api/access-requests/{request_id}/decision")
def decide_access_request(request_id: str, request: Request, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    p = require_principal(request)
    decision = str(body.get("decision") or "").lower()
    if decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail={"type": "error", "message": "Decision must be 'approved' or 'rejected'."})
    note = _clip(body.get("note"), 300)
    with _LOCK:
        req = _STORE.get(request_id)
        if req is None:
            raise HTTPException(status_code=404, detail={"type": "error", "message": "Request not found."})
        if not _can_decide(p, req):
            raise HTTPException(status_code=403, detail={"type": "error", "message": "Only the Director / Executive Director of this function or the CMD can decide this request."})
        if req["status"] != "pending":
            return _view(req)
        who = f"{p.display_name}, {p.functional_designation or p.designation}"
        req["status"] = decision
        req["decided_at"] = time.time()
        req["decided_by"] = {"emp_id": p.emp_id, "persona": p.persona, "display_name": p.display_name,
                             "designation": p.functional_designation or p.designation}
        req["note"] = note
        channel = "HR" if req["function"] == "HR" else "Finance"
        req["outcome"] = (
            f"Approved by {who}. The requested details will be shared with you through the official {channel} "
            f"channel; Yukti keeps names hidden at your access level."
            if decision == "approved"
            else f"Rejected by {who}." + (f" Note: {note}" if note else "")
        )
        out = _view(req)
    audit("access_request_decided", p, turn_id=req.get("turn_id", ""), decision=decision,
          rule_ref=req.get("rule_ref", ""), request_id=request_id, requester=req["requester"]["emp_id"])
    return out


def reset_store_for_tests() -> None:
    with _LOCK:
        _STORE.clear()
