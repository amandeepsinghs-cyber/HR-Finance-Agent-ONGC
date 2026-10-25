"""FastAPI Application Server for Yukti AI.
Exposes:
- /health: Health check endpoint
- /api/turn: Real ADK Agent turn execution (Gemini + live BigQuery/Vertex AI Search)
- /ws/live: Bidirectional WebSocket audio & text streaming
- /api/export: Document and data export endpoints (POST create, GET download)
"""

import asyncio
import json
import logging
import os
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional
import uuid

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, WebSocket, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.access_control import UnknownPersona, normalize_persona
from app import auth as yauth
from app.auth import Principal, require_principal
from app.cache import get_demo_cache
from app.config import (
    DEFAULT_LIVE_MODEL,
    DEFAULT_TEXT_MODEL,
    DEFAULT_VOICE,
    EXPORTS_DIR,
    GCP_PROJECT,
    YUKTI_DEMO_CACHE,
    YUKTI_ENABLE_ADMIN,
    YUKTI_ENV,
    allowed_origins,
)
from app.live_session import LiveSessionManager
from app.export_audit import (
    DEFAULT_EXPORT_TTL_SECONDS,
    TurnOwnershipError,
    enforce_export_rbac,
    filename_from_contract,
    register_artifact,
    register_turn_contract,
    resolve_turn_contract,
    sweep_expired_exports,
    verify_artifact_access,
    write_export_audit,
)
from app.tools.export_tool import DOCS_TOAST, SHEETS_TOAST, DocumentExporter
from app.turn_runner import get_agent_turn_runner
from app.jobs.api import router as jobs_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("yukti.server")

os.environ.setdefault("GOOGLE_CLOUD_PROJECT", GCP_PROJECT)
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")

_IS_PROD = YUKTI_ENV == "prod"
app = FastAPI(
    title="Yukti AI Backend",
    version="1.0.0",
    description="Voice-First HR & Finance AI Agent for ONGC CMD & Leadership",
    # P0.5 (SPEC-06 §4.7): no interactive docs / schema on Cloud Run
    docs_url=None if _IS_PROD else "/docs",
    redoc_url=None if _IS_PROD else "/redoc",
    openapi_url=None if _IS_PROD else "/openapi.json",
)

app.include_router(jobs_router)

# CORS (P0.5, BUG-32): only configured origins (YUKTI_ALLOWED_ORIGINS), never "*" with credentials.
# The UI normally talks to the backend through its single-origin proxy (server.js), so browsers never preflight.
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# Singletons

demo_cache = get_demo_cache()
exporter = DocumentExporter()


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "type" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"type": "error", "message": str(detail), "retryable": exc.status_code >= 500},
    )


@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"type": "error", "message": "Resource not found.", "retryable": False},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    logger.exception(f"Unhandled server exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"type": "error", "message": "Something went wrong answering that. Please try again.", "retryable": True},  # P0.1: no internals
    )


@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting Yukti AI Backend. Project: {GCP_PROJECT} | Text Model: {DEFAULT_TEXT_MODEL} | Live Model: {DEFAULT_LIVE_MODEL}")
    # P0.4 r2: surface a missing/short signing key at startup (prod fails closed: every protected route -> 401)
    if not yauth.signing_key_ok():
        logger.error("Persona signing key unavailable: sessions cannot be issued or verified (set YUKTI_PERSONA_SIGNING_KEY)")

    # Hydrate Verified Answer Cache from snapshot
    from app.answer_cache import get_answer_cache
    ans_cache = get_answer_cache()
    snapshot_path = Path(__file__).resolve().parent.parent / "certified" / "answer_cache_warmup.json"
    if snapshot_path.exists():
        try:
            with open(snapshot_path, "r", encoding="utf-8") as f:
                entries = json.load(f)
                for k, v in entries.items():
                    ans_cache.backend.set(k, v)
            logger.info(f"Hydrated {len(entries)} verified Answer Contracts into {ans_cache.backend_type} cache.")
        except Exception as e:
            logger.warning(f"Could not load answer cache snapshot: {e}")

    if YUKTI_DEMO_CACHE:
        logger.info("YUKTI_DEMO_CACHE=1 is enabled. Pre-warming root-only demo cache...")
        demo_cache.load()
    else:
        logger.info("YUKTI_DEMO_CACHE=0 (Default). All turns run through real Gemini LLM + BigQuery tools.")


class TurnRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    # P0.4 (BUG-06): ignored for authorisation; the persona comes from the signed session token. A mismatch
    # is audited as `persona_assertion_ignored`.
    persona: Optional[str] = None
    language: Optional[str] = "en"
    voice_override: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None
    ui_context: Optional[Dict[str, Any]] = None
    # Contract v2 drill-down (B2.5/B4.2): a chip sends its spec_patch plus the card's query_spec.
    spec_patch: Optional[Dict[str, Any]] = None
    query_spec: Optional[Dict[str, Any]] = None


class VoiceTurnRequest(BaseModel):
    audio_base64: str
    mime_type: Optional[str] = "audio/webm"
    session_id: Optional[str] = None
    persona: Optional[str] = None  # P0.4: ignored (see TurnRequest)
    language: Optional[str] = "en"
    transcript_hint: Optional[str] = None


class SessionRequest(BaseModel):
    persona_id: str
    passphrase: Optional[str] = None
    acting_persona: Optional[str] = None  # DEMO_ADMIN only: persona the presenter starts as (default CMD)


def _note_persona_assertion(asserted: Optional[str], principal: Principal, channel: str) -> None:
    """P0.4: a client-asserted persona that differs from the token is ignored and audited (SPEC-06 §4.4)."""
    if not asserted:
        return
    try:
        a = normalize_persona(asserted)
    except UnknownPersona:
        a = str(asserted)[:20]
    if a != principal.persona:
        yauth.audit("persona_assertion_ignored", principal, decision="ignored", rule_ref="SPEC-06 §4.4",
                    asserted=a, channel=channel)


class ExportRequest(BaseModel):
    turn_id: Optional[str] = None
    session_id: Optional[str] = None
    format: str = "pdf"
    title: str = "Yukti_Export"
    content: Optional[str] = None
    columns: Optional[List[str]] = None
    rows: Optional[List[Dict[str, Any]]] = None
    chart_png: Optional[str] = None
    chart_svg: Optional[str] = None
    email_draft: Optional[Dict[str, Any]] = None
    masked: Optional[bool] = False


class ExportAuditRequest(BaseModel):
    turn_id: str = ""
    session_id: Optional[str] = None
    format: str = "png"
    filename: Optional[str] = None
    rows: int = 0
    columns: Optional[List[str]] = None
    masked: bool = False


# P0.1 (BUG-01): ADC health, cached for 60 s so /health polling never hammers the token endpoint.
_AUTH_CACHE_TTL_S = 60.0
_auth_cache: Dict[str, Any] = {"ok": None, "ts": 0.0}


def _check_auth_ok() -> bool:
    """True when Application Default Credentials can mint a token. Never raises, never exposes error text."""
    if os.getenv("YUKTI_FORCE_ADC_FAIL", "0") in ("1", "true", "yes"):  # BEH-07 forced-failure test flag
        return False
    now = time.monotonic()
    if _auth_cache["ok"] is not None and now - _auth_cache["ts"] < _AUTH_CACHE_TTL_S:
        return bool(_auth_cache["ok"])
    ok = False
    try:
        import google.auth
        from google.auth.transport.requests import Request

        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        creds.refresh(Request())
        ok = True
    except Exception as exc:  # any failure -> not authorised; details only in the server log
        logger.warning(f"ADC health check failed ({type(exc).__name__})")
        ok = False
    _auth_cache["ok"], _auth_cache["ts"] = ok, now
    return ok


@app.get("/health")
def health() -> Dict[str, Any]:
    from app.answer_cache import get_answer_cache
    from app.coverage.manifest import get_coverage_manifest
    ac = get_answer_cache()
    manifest = get_coverage_manifest()
    return {
        "auth_ok": _check_auth_ok(),
        "auth_mode": yauth.auth_mode(),  # P0.1 r2: same normalisation as app.auth
        "status": "healthy",
        "agent": "Yukti AI",
        "version": "1.0.0",
        "project": GCP_PROJECT,
        "text_model": DEFAULT_TEXT_MODEL,
        "live_model": DEFAULT_LIVE_MODEL,
        "default_voice": DEFAULT_VOICE,
        "answer_cache": ac.stats(),
        "demo_cache_enabled": YUKTI_DEMO_CACHE,
        "coverage_generated_at": manifest.generated_at,
        "snapshot_date": "2026-10-19" if manifest.source == "snapshot" else None,
    }


# ---------------------------------------------------------------- P0.4 identity (SPEC-06 §4.4)
@app.get("/api/auth/personas")
def auth_personas() -> Dict[str, Any]:
    """Demo login picker: the personas a session can be started as (no secrets)."""
    return {"auth_mode": yauth.auth_mode(), "personas": yauth.personas_public()}


@app.post("/api/auth/session")
def auth_session(req: SessionRequest, response: Response) -> Dict[str, Any]:
    """Starts a demo session: signs a persona token and sets the HttpOnly `yk_session` cookie."""
    if yauth.auth_mode() != "demo":
        raise HTTPException(status_code=404, detail={"type": "error", "message": "Not available.", "retryable": False})
    pid = (req.persona_id or "").strip().upper()
    if pid == yauth.ADMIN_PERSONA_ID:
        if not yauth.admin_passphrase_ok(req.passphrase):
            yauth.audit("admin_session_denied", None, decision="refused", rule_ref="SPEC-06 §4.4")
            raise HTTPException(status_code=401, detail={"type": "error", "message": "Presenter sign-in failed.", "retryable": False})
        acting = (req.acting_persona or yauth.ADMIN_DEFAULT_ACTING_PERSONA).strip().upper()
        try:
            token = yauth.issue_token(acting, is_admin=True)
        except yauth.AuthError:
            raise HTTPException(status_code=401, detail={"type": "error", "message": "Unknown persona.", "retryable": False})
    else:
        try:
            token = yauth.issue_token(pid)
        except yauth.AuthError:
            raise HTTPException(status_code=401, detail={"type": "error", "message": "Unknown persona.", "retryable": False})
    principal = yauth.verify_token(token)
    yauth.set_session_cookie(response, token)
    yauth.audit("session_start", principal, decision="allowed", rule_ref="SPEC-06 §4.4")
    return {"principal": principal.public(), "expires_at": principal.exp}


@app.get("/api/auth/me")
def auth_me(principal: Principal = Depends(require_principal)) -> Dict[str, Any]:
    """Who the server thinks you are (the persona chip reads this, never the contract)."""
    return {"principal": principal.public(), "auth_mode": yauth.auth_mode()}


def _apply_admin_switch(contract: Dict[str, Any], principal: Principal, response: Response, query: str = "") -> None:
    """DEMO_ADMIN only: a `set_persona` ui_action from the deterministic role-switch handler becomes a new
    signed session for the target persona (audited). For everyone else any `set_persona` is stripped."""
    ui_act = contract.get("ui_action") or {}
    if (ui_act.get("command") or ui_act.get("action")) not in ("set_persona", "persona"):
        return
    target = str(ui_act.get("value") or "").upper()
    if principal.is_admin and target in yauth.PERSONA_DIRECTORY:
        token = yauth.issue_token(target, is_admin=True)
        yauth.set_session_cookie(response, token)
        yauth.audit("admin_persona_switch", principal, decision="allowed", rule_ref="SPEC-06 §4.4",
                    query=query or None, to_persona=target)
        return
    contract.pop("ui_action", None)  # defence in depth: never let a non-admin contract switch the UI persona
    contract["persona"] = principal.persona


def admin_cache_stats(principal: Principal = Depends(yauth.require_admin)) -> Dict[str, Any]:
    """Returns tool-result cache statistics."""
    from app.config import YUKTI_RESULT_CACHE
    from app.tool_cache import get_tool_cache
    tc = get_tool_cache()
    return {
        "status": "active",
        "cache_enabled": YUKTI_RESULT_CACHE,
        "stats": tc.stats(),
    }


def admin_cache_clear(principal: Principal = Depends(yauth.require_admin)) -> Dict[str, Any]:
    """Clears the in-memory tool-result cache."""
    from app.tool_cache import get_tool_cache
    tc = get_tool_cache()
    tc.clear()
    yauth.audit("admin_cache_clear", principal, decision="allowed", rule_ref="SPEC-06 §4.7")
    return {"status": "cleared", "stats": tc.stats()}


# P0.5 (BUG-32): /admin/* exist only when YUKTI_ENABLE_ADMIN=1 (default off; 404 otherwise) and need an admin token.
if YUKTI_ENABLE_ADMIN:
    app.get("/admin/cache")(admin_cache_stats)
    app.post("/admin/cache/clear")(admin_cache_clear)


@app.post("/api/turn")
async def execute_turn(req: TurnRequest, response: Response, principal: Principal = Depends(require_principal)) -> Dict[str, Any]:
    """Executes an agent turn through Google ADK (or demo cache if enabled)."""
    t0 = time.perf_counter()
    session_id = req.session_id or f"sess-{int(time.time() * 1000)}"
    _note_persona_assertion(req.persona, principal, "api_turn")
    persona = principal.persona  # P0.4: the signed token is the only source of the persona

    # 1. Check optional demo cache (ONLY if YUKTI_DEMO_CACHE=1)
    if YUKTI_DEMO_CACHE:
        matched_root = demo_cache.match_root(req.query)
        if matched_root:
            from app.answer_composer import get_contract_validator
            contract = {
                "turn_id": f"turn-{session_id}-001",
                "language": req.language or "en",
                "persona": persona,
                "spoken_summary": f"According to verified enterprise records: {matched_root.get('question')}. Please review the canvas visual.",
                "display_text": f"Grounded in verified enterprise records [1].",
                "visual": {
                    "type": "table",
                    "mode": "replace",
                    "title": matched_root.get("question"),
                    "table": {
                        "columns": matched_root.get("data", {}).get("columns", []),
                        "rows": matched_root.get("data", {}).get("rows", [])[:20],
                    },
                },
                "insights": ["Served from verified demo cache"],
                "sources": [{"kind": "data", "object": "hrfin_gold"}],
                "suggestions": ["Show by discipline", "What are the policy guidelines?"],
                "access": {"status": "allowed"},
                "export_options": ["sheets", "xlsx", "pdf"],
                "status_events": ["Served from verified demo cache"],
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            }
            get_contract_validator().validate(contract)
            return contract

    # 2. Standard Real Agent Path: Google ADK Runner + Gemini
    try:
        contract = await get_agent_turn_runner(principal=principal).execute_turn_async(
            query=req.query,
            session_id=session_id,
            persona=persona,
            language=req.language or "en",
            voice_override=req.voice_override,
            history=req.history,
            ui_context=req.ui_context,
            spec_patch=req.spec_patch,
            base_spec=req.query_spec,
            principal=principal,
        )
        _apply_admin_switch(contract, principal, response, query=req.query)
        register_turn_contract(
            turn_id=str(contract.get("turn_id") or ""),
            contract=contract,
            emp_id=principal.emp_id,
            persona=principal.persona,
            session_id=session_id,
        )
        return contract
    except Exception as exc:
        logger.exception(f"Error executing turn: {exc}")
        raise HTTPException(
            status_code=500,
            detail={"type": "error", "message": "Something went wrong answering that. Please try again.", "retryable": True},  # P0.1: no internals
        )


@app.post("/api/voice-turn")
async def execute_voice_turn(req: VoiceTurnRequest, response: Response, principal: Principal = Depends(require_principal)) -> Dict[str, Any]:
    """Transcribes browser audio via Gemini 2.5 Flash multimodal audio understanding and runs the turn."""
    import base64
    from google import genai
    from google.genai import types as gtypes

    session_id = req.session_id or f"sess-{int(time.time() * 1000)}"
    _note_persona_assertion(req.persona, principal, "api_voice_turn")
    persona = principal.persona  # P0.4
    transcript = (req.transcript_hint or "").strip()

    if not transcript and req.audio_base64:
        try:
            audio_bytes = base64.b64decode(req.audio_base64)
            mime = (req.mime_type or "audio/webm").split(";")[0].strip() or "audio/webm"
            logger.info(f"[{session_id}] /api/voice-turn received {len(audio_bytes)}B ({mime})")
            if len(audio_bytes) > 400:
                client = genai.Client(vertexai=True, project=GCP_PROJECT, location="us-central1")
                resp = await asyncio.to_thread(
                    client.models.generate_content,
                    model=DEFAULT_TEXT_MODEL,
                    contents=[
                        gtypes.Part.from_bytes(data=audio_bytes, mime_type=mime),
                        gtypes.Part.from_text(
                            text=(
                                "Transcribe the user's spoken question or greeting into exact plain text "
                                "(English, Hindi, or Hinglish as spoken). If there is no intelligible speech "
                                "or only background noise/silence, output ONLY the word SILENCE."
                            )
                        ),
                    ],
                )
                raw_tx = (resp.text or "").strip().strip('"').strip("'")
                logger.info(f"[{session_id}] /api/voice-turn Gemini raw transcription: {raw_tx!r}")
                if raw_tx and raw_tx.upper() != "SILENCE" and len(raw_tx) >= 2:
                    transcript = raw_tx
        except Exception as e:
            logger.warning(f"[{session_id}] /api/voice-turn transcription error: {e}")

    if not transcript:
        return {"status": "silence", "transcript": ""}

    contract = await get_agent_turn_runner(principal=principal).execute_turn_async(
        query=transcript,
        session_id=session_id,
        persona=persona,
        language=req.language or "en",
        principal=principal,
    )
    _apply_admin_switch(contract, principal, response, query=transcript)
    register_turn_contract(
        turn_id=str(contract.get("turn_id") or ""),
        contract=contract,
        emp_id=principal.emp_id,
        persona=principal.persona,
        session_id=session_id,
    )
    return {
        "status": "ok",
        "transcript": transcript,
        "contract": contract,
    }


try:
    EXPORT_TTL_SECONDS = int(os.getenv("YUKTI_EXPORT_TTL_SECONDS", str(DEFAULT_EXPORT_TTL_SECONDS)))
except ValueError:
    EXPORT_TTL_SECONDS = DEFAULT_EXPORT_TTL_SECONDS


def _sweep_old_exports() -> None:
    """M5 / H1.3a: Cloud Run's filesystem is RAM — sweep expired exports and `.exp_*.meta.json` sidecars (24 h TTL)."""
    try:
        sweep_expired_exports(exports_dir=EXPORTS_DIR, ttl_seconds=EXPORT_TTL_SECONDS)
    except Exception as exc:  # never fail an export because of housekeeping
        logger.warning(f"export sweep skipped: {exc}")


@app.post("/api/export")
def create_export(
    req: ExportRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
) -> Dict[str, Any]:
    """Generates an RBAC-masked, audit-logged export file and returns `{artifact, toast?, ...}` (SPEC-10 §5)."""
    fmt = (req.format or "pdf").lower().strip()
    export_id = f"exp_{uuid.uuid4().hex}"
    _sweep_old_exports()

    # 1. Resolve format & honest Sheets/Docs toast (SPEC-10 §4.7 / BUG-25)
    toast_parts: List[str] = []
    if fmt in ("sheets", "google_sheets", "gsheet"):
        kind, ext = "xlsx", "xlsx"
        toast_parts.append(SHEETS_TOAST)
    elif fmt in ("xlsx", "excel", "xls"):
        kind, ext = "xlsx", "xlsx"
    elif fmt == "csv":
        kind, ext = "csv", "csv"
    elif fmt == "pdf":
        kind, ext = "pdf", "pdf"
    elif fmt in ("docs", "google_docs", "gdoc"):
        kind, ext = "docx", "docx"
        toast_parts.append(DOCS_TOAST)
    elif fmt in ("docx", "word", "doc"):
        kind, ext = "docx", "docx"
    elif fmt in ("eml", "email"):
        kind, ext = "eml", "eml"
    else:
        raise HTTPException(
            status_code=400,
            detail={"type": "error", "message": f"Unsupported export format: {req.format}", "retryable": False},
        )

    # 2. Resolve source contract for (session, turn_id, principal) — M1 & M6
    session_id = req.session_id or ""
    base_contract: Optional[Dict[str, Any]] = None
    is_client_supplied = False

    def _refuse_export_403(msg: str, t_id: str = "") -> None:
        write_export_audit(
            emp_id=principal.emp_id,
            persona=principal.persona,
            session_id=session_id,
            turn_id=t_id,
            fmt=kind,
            filename="forbidden",
            sha256="",
            rows=0,
            columns=[],
            data_classes=["restricted"],
            masked=True,
            delivery="download",
            client_ip=request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=403,
            detail={"type": "error", "message": msg, "retryable": False},
        )

    if req.turn_id and req.turn_id.strip():
        clean_tid = req.turn_id.strip()
        try:
            resolved = resolve_turn_contract(clean_tid, principal.emp_id, principal.persona)
        except TurnOwnershipError:
            _refuse_export_403("You do not have permission to export another user's turn.", clean_tid)
        if resolved is None:
            # M1 Probe 1d: unknown turn_id must NEVER fall back to client rows/content
            _refuse_export_403(f"Turn '{clean_tid}' could not be verified for this principal.", clean_tid)
        base_contract, resolved_sid = resolved
        if not session_id:
            session_id = resolved_sid
        if base_contract.get("_session_row_cap"):
            toast_parts.append(
                f"Export capped at {base_contract['_session_row_cap']} rows from session memory."
            )
    else:
        # M1: turn_id is missing -> client-supplied data is untrusted
        is_client_supplied = True
        norm_p = (principal.persona or "").strip().upper()
        if not req.rows and not req.content and not req.email_draft:
            _refuse_export_403("Export requires a verified turn_id or policy-compliant payload.")
        if norm_p not in ("CMD", "DIR_HR"):
            # Non-CMD/DIR_HR may only export client rows that enforce_export_rbac can verify and collapse
            if not req.rows or req.content or req.email_draft:
                _refuse_export_403(
                    f"Client-supplied content requires a verified turn_id for access level {norm_p}."
                )
        base_contract = {
            "turn_id": "",
            "persona": principal.persona,
            "visual": {
                "type": "table",
                "mode": "replace",
                "title": req.title or "Yukti_Export",
                "table": {
                    "columns": list(req.columns or []),
                    "rows": list(req.rows or []),
                },
            },
        }
        if req.email_draft and norm_p in ("CMD", "DIR_HR"):
            base_contract["email_draft"] = req.email_draft

    # 3. Enforce RBAC & column intersection on contract
    try:
        masked_contract, masked_flag, is_aggregate, data_classes, dropped_cols = enforce_export_rbac(
            base_contract,
            principal.persona,
            requested_columns=req.columns if not is_client_supplied else None,
            is_client_supplied=is_client_supplied,
        )
    except TurnOwnershipError as exc_rbac:
        _refuse_export_403(str(exc_rbac), req.turn_id or "")

    if is_client_supplied and "client_supplied" not in data_classes:
        data_classes.append("client_supplied")

    if dropped_cols:
        toast_parts.append(
            f"Dropped restricted or unknown column(s) for {principal.persona}: {', '.join(dropped_cols)}."
        )

    vis = masked_contract.get("visual") if isinstance(masked_contract.get("visual"), dict) else {}
    stmt = vis.get("statement") if isinstance(vis.get("statement"), dict) else None
    tbl = vis.get("table") if isinstance(vis.get("table"), dict) else {}
    comp_items = (
        ((vis.get("compare") or {}).get("items") or [])
        if isinstance(vis.get("compare"), dict)
        else (vis.get("tables") if isinstance(vis.get("tables"), list) else [])
    )
    eff_cols = list(tbl.get("columns") or [])
    eff_rows = list(tbl.get("rows") or [])
    if stmt:
        eff_cols = ["label"] + list(stmt.get("periods") or [])
        eff_rows = [r for sec in (stmt.get("sections") or []) for r in (sec.get("rows") or [])]

    # S7: Multi-table compare on CSV exports as a .zip of UTF-8 BOM CSVs
    if kind == "csv" and len(comp_items) >= 2:
        ext = "zip"

    title_override = req.title if (req.title and req.title != "Yukti_Export") else None
    canonical_filename = filename_from_contract(
        masked_contract,
        ext=ext,
        persona=principal.persona,
        is_aggregate=is_aggregate,
        title_override=title_override,
    )

    # M1: Only use req.content when CMD/DIR_HR explicitly exports client markdown without turn_id
    safe_md = (
        (req.content or "")
        if (is_client_supplied and (principal.persona or "").upper() in ("CMD", "DIR_HR"))
        else str(masked_contract.get("display_text") or "")
    )

    try:
        disk_name = f"{export_id}.{ext}"
        if kind == "xlsx":
            out_path = exporter.export_xlsx(
                columns=eff_cols,
                rows=eff_rows,
                filename=disk_name,
                contract=masked_contract,
                persona=principal.persona,
                masked=masked_flag,
                is_aggregate=is_aggregate,
            )
        elif kind == "csv":
            out_path = exporter.export_csv(
                columns=eff_cols,
                rows=eff_rows,
                filename=disk_name,
                contract=masked_contract,
            )
        elif kind == "pdf":
            out_path = exporter.export_pdf(
                markdown_text=safe_md,
                filename=disk_name,
                contract=masked_contract,
                title=title_override,
                columns=eff_cols,
                rows=eff_rows,
                chart_png=req.chart_png,
                persona=principal.persona,
                masked=masked_flag,
                is_aggregate=is_aggregate,
            )
        elif kind == "docx":
            out_path = exporter.export_word(
                markdown_text=safe_md,
                filename=disk_name,
                contract=masked_contract,
                title=title_override,
                columns=eff_cols,
                rows=eff_rows,
                chart_png=req.chart_png,
                email_draft=req.email_draft if is_client_supplied else masked_contract.get("email_draft"),
                persona=principal.persona,
                masked=masked_flag,
                is_aggregate=is_aggregate,
            )
        elif kind == "eml":
            att_canonical = canonical_filename.rsplit(".", 1)[0] + ".xlsx"
            out_path = exporter.export_eml(
                email_draft=req.email_draft if is_client_supplied else masked_contract.get("email_draft"),
                filename=disk_name,
                contract=masked_contract,
                attachment_filename=att_canonical,
                persona=principal.persona,
                masked=masked_flag,
                is_aggregate=is_aggregate,
            )
        else:
            raise ValueError(f"Unhandled export kind {kind}")

        rec = register_artifact(
            export_id=export_id,
            kind=kind,
            filename=canonical_filename,
            disk_path=out_path,
            rows=len(eff_rows),
            columns=eff_cols,
            masked=masked_flag,
            is_aggregate=is_aggregate,
            emp_id=principal.emp_id,
            persona=principal.persona,
            session_id=session_id,
            turn_id=str(req.turn_id or masked_contract.get("turn_id") or ""),
            ttl_seconds=EXPORT_TTL_SECONDS,
        )

        write_export_audit(
            emp_id=principal.emp_id,
            persona=principal.persona,
            session_id=session_id,
            turn_id=str(req.turn_id or masked_contract.get("turn_id") or ""),
            fmt=kind,
            filename=canonical_filename,
            sha256=rec.sha256,
            rows=len(eff_rows),
            columns=eff_cols,
            data_classes=data_classes,
            masked=masked_flag,
            delivery="eml" if kind == "eml" else "download",
            client_ip=request.client.host if request.client else None,
        )

        artifact_dict = rec.public_artifact()
        resp_payload: Dict[str, Any] = {
            **artifact_dict,
            "format": kind,
            "artifact": artifact_dict,
        }
        if toast_parts:
            resp_payload["toast"] = " ".join(toast_parts)
        return resp_payload
    except HTTPException:
        raise
    except ValueError as exc_val:
        if "Invalid CR/LF in email header" in str(exc_val):
            raise HTTPException(
                status_code=400,
                detail={"type": "error", "message": "Invalid characters in email header.", "retryable": False},
            )
        logger.exception(f"Export validation failed: {exc_val}")
        raise HTTPException(
            status_code=500,
            detail={"type": "error", "message": "Export failed. Please try again.", "retryable": True},
        )
    except Exception as exc:
        logger.exception(f"Export creation failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail={"type": "error", "message": "Export failed. Please try again.", "retryable": True},  # no internals
        )


@app.post("/api/export/audit")
def create_export_audit_event(
    req: ExportAuditRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
) -> Dict[str, Any]:
    """Audit endpoint for client-side PNG/SVG exports (SPEC-10 §4.4, §5).
    S8: Verifies turn ownership when `turn_id` is registered and derives `masked` server-side.
    """
    from app.brain.rbac import persona_class

    fmt = (req.format or "png").lower().strip()
    if fmt not in ("png", "svg"):
        fmt = "png"

    resolved_contract: Optional[Dict[str, Any]] = None
    session_id = req.session_id or ""
    if req.turn_id and req.turn_id.strip():
        try:
            res = resolve_turn_contract(req.turn_id.strip(), principal.emp_id, principal.persona)
        except TurnOwnershipError:
            raise HTTPException(
                status_code=403,
                detail={"type": "error", "message": "You do not have permission to audit another user's turn.", "retryable": False},
            )
        if res is not None:
            resolved_contract, resolved_sid = res
            if not session_id:
                session_id = resolved_sid

    if resolved_contract is not None:
        _, server_masked, server_agg, data_classes, _ = enforce_export_rbac(resolved_contract, principal.persona)
    else:
        server_masked = bool(req.masked) or (persona_class(principal.persona) == "junior")
        server_agg = server_masked
        data_classes = ["general"]

    fname = filename_from_contract(
        resolved_contract or {"turn_id": req.turn_id},
        ext=fmt,
        persona=principal.persona,
        is_aggregate=server_agg,
    )
    row = write_export_audit(
        emp_id=principal.emp_id,
        persona=principal.persona,
        session_id=session_id,
        turn_id=req.turn_id or "",
        fmt=fmt,
        filename=fname,
        sha256="client_rendered",
        rows=int(req.rows or 0),
        columns=list(req.columns or []),
        data_classes=data_classes,
        masked=server_masked,
        delivery="download",
        client_ip=request.client.host if request.client else None,
    )
    return {"status": "ok", "filename": fname, "audit": row}


@app.get("/api/export/{export_id}")
@app.get("/api/download/{export_id}")
def download_export(export_id: str, principal: Principal = Depends(require_principal)):
    """Downloads an exported file securely from the exports directory only.
    M2: Fails closed! Requires an active artifact record (404 if missing or expired) and creator-principal match (403 on mismatch).
    """
    # H1.3a: only ids we mint (exp_<32 hex>) are servable; anything else is a 404 (no globbing on user input)
    if not re.fullmatch(r"exp_[0-9a-f]{32}", export_id or ""):
        raise HTTPException(
            status_code=404,
            detail={"type": "error", "message": "Export not found.", "retryable": False},
        )

    try:
        rec = verify_artifact_access(
            export_id=export_id,
            principal_emp_id=principal.emp_id,
            principal_persona=principal.persona,
            exports_dir=EXPORTS_DIR,
        )
    except TurnOwnershipError:
        raise HTTPException(
            status_code=403,
            detail={"type": "error", "message": "You do not have permission to download another user's export.", "retryable": False},
        )

    if rec is None:
        raise HTTPException(
            status_code=404,
            detail={"type": "error", "message": f"Export ID '{export_id}' not found or expired.", "retryable": False},
        )

    root = EXPORTS_DIR.resolve()
    allowed_exts = (".docx", ".xlsx", ".pdf", ".csv", ".eml", ".zip")
    matches = [
        p
        for p in EXPORTS_DIR.glob(f"{export_id}.*")
        if p.resolve().parent == root and p.suffix.lower() in allowed_exts
    ]
    if not matches:
        raise HTTPException(
            status_code=404,
            detail={"type": "error", "message": f"Export ID '{export_id}' not found.", "retryable": False},
        )
    file_path = matches[0]
    ext = file_path.suffix.lower()
    media_types = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pdf": "application/pdf",
        ".csv": "text/csv; charset=utf-8",
        ".eml": "message/rfc822",
        ".zip": "application/zip",
    }
    media_type = media_types.get(ext, "application/octet-stream")
    download_filename = rec.filename if rec.filename else file_path.name
    return FileResponse(
        path=file_path,
        filename=download_filename,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{download_filename}"'},
    )


@app.websocket("/ws/live")
async def websocket_live_endpoint(
    websocket: WebSocket,
    session_id: Optional[str] = Query(None),
    persona: Optional[str] = Query(None),
    model: Optional[str] = Query(DEFAULT_LIVE_MODEL),
    voice: Optional[str] = Query(DEFAULT_VOICE),
    language: Optional[str] = Query("en"),
):
    await websocket.accept()
    # P0.4 (SPEC-06 §4.4): the socket's principal comes from the session cookie / bearer on the upgrade, or
    # from a first frame {"type": "auth", "token": ...}. No valid token -> close 4401. `persona` is ignored.
    principal: Optional[Principal] = None
    try:
        if yauth.auth_mode() == "iap":
            principal = yauth.verify_iap_assertion(websocket.headers.get("x-goog-iap-jwt-assertion", ""))
        else:
            tok = yauth.token_from_headers(websocket.headers, websocket.cookies)
            if not tok:
                first = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                msg = json.loads(first) if first else {}
                tok = msg.get("token") if isinstance(msg, dict) and msg.get("type") == "auth" else None
            try:
                principal = yauth.verify_token(tok or "")
            except yauth.AuthError:
                cookie_tok = websocket.cookies.get(yauth.SESSION_COOKIE_NAME)
                if cookie_tok and cookie_tok != tok:
                    principal = yauth.verify_token(cookie_tok)
                else:
                    raise
    except Exception as exc:  # noqa: BLE001 - any auth failure closes the socket
        logger.info(f"/ws/live rejected: {type(exc).__name__}")
        await websocket.send_json({"type": "error", "message": "Please sign in again to continue.", "retryable": False})
        await websocket.close(code=4401)
        return
    _note_persona_assertion(persona, principal, "ws_query")
    sess_id = session_id or f"live-sess-{int(time.time() * 1000)}"
    manager = LiveSessionManager(
        websocket=websocket,
        session_id=sess_id,
        persona=principal.persona,
        model_name=model or DEFAULT_LIVE_MODEL,
        voice=voice or DEFAULT_VOICE,
        language=language or "en",
        principal=principal,
    )
    await manager.run()
