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

from fastapi import FastAPI, HTTPException, Query, WebSocket, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.access_control import normalize_persona
from app.cache import get_demo_cache
from app.config import (
    DEFAULT_LIVE_MODEL,
    DEFAULT_TEXT_MODEL,
    DEFAULT_VOICE,
    EXPORTS_DIR,
    GCP_PROJECT,
    YUKTI_DEMO_CACHE,
)
from app.live_session import LiveSessionManager
from app.tools.export_tool import DocumentExporter
from app.turn_runner import get_agent_turn_runner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("yukti.server")

os.environ.setdefault("GOOGLE_CLOUD_PROJECT", GCP_PROJECT)
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")

app = FastAPI(
    title="Yukti AI Backend",
    version="1.0.0",
    description="Voice-First HR & Finance AI Agent for ONGC CMD & Leadership",
)

# CORS: explicitly allow localhost:3000 for Next.js frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singletons
turn_runner = get_agent_turn_runner()
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
        content={"type": "error", "message": str(exc), "retryable": True},
    )


@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting Yukti AI Backend. Project: {GCP_PROJECT} | Text Model: {DEFAULT_TEXT_MODEL} | Live Model: {DEFAULT_LIVE_MODEL}")

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
    persona: Optional[str] = "CMD"
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
    persona: Optional[str] = "CMD"
    language: Optional[str] = "en"
    transcript_hint: Optional[str] = None


class ExportRequest(BaseModel):
    format: str = "pdf"
    title: str = "Yukti_Export"
    content: Optional[str] = None
    columns: Optional[List[str]] = None
    rows: Optional[List[Dict[str, Any]]] = None


@app.get("/health")
def health() -> Dict[str, Any]:
    from app.answer_cache import get_answer_cache
    ac = get_answer_cache()
    return {
        "status": "healthy",
        "agent": "Yukti AI",
        "version": "1.0.0",
        "project": GCP_PROJECT,
        "text_model": DEFAULT_TEXT_MODEL,
        "live_model": DEFAULT_LIVE_MODEL,
        "default_voice": DEFAULT_VOICE,
        "answer_cache": ac.stats(),
        "demo_cache_enabled": YUKTI_DEMO_CACHE,
    }


@app.get("/admin/cache")
def admin_cache_stats() -> Dict[str, Any]:
    """Returns tool-result cache statistics."""
    from app.config import YUKTI_RESULT_CACHE
    from app.tool_cache import get_tool_cache
    tc = get_tool_cache()
    return {
        "status": "active",
        "cache_enabled": YUKTI_RESULT_CACHE,
        "stats": tc.stats(),
    }


@app.post("/admin/cache/clear")
def admin_cache_clear() -> Dict[str, Any]:
    """Clears the in-memory tool-result cache."""
    from app.tool_cache import get_tool_cache
    tc = get_tool_cache()
    tc.clear()
    return {"status": "cleared", "stats": tc.stats()}


@app.post("/api/turn")
async def execute_turn(req: TurnRequest) -> Dict[str, Any]:
    """Executes an agent turn through Google ADK (or demo cache if enabled)."""
    t0 = time.perf_counter()
    session_id = req.session_id or f"sess-{int(time.time() * 1000)}"
    persona = normalize_persona(req.persona)

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
        contract = await turn_runner.execute_turn_async(
            query=req.query,
            session_id=session_id,
            persona=persona,
            language=req.language or "en",
            voice_override=req.voice_override,
            history=req.history,
            ui_context=req.ui_context,
            spec_patch=req.spec_patch,
            base_spec=req.query_spec,
        )
        return contract
    except Exception as exc:
        logger.exception(f"Error executing turn: {exc}")
        raise HTTPException(
            status_code=500,
            detail={"type": "error", "message": f"Turn execution failed: {str(exc)}", "retryable": True},
        )


@app.post("/api/voice-turn")
async def execute_voice_turn(req: VoiceTurnRequest) -> Dict[str, Any]:
    """Transcribes browser audio via Gemini 2.5 Flash multimodal audio understanding and runs the turn."""
    import base64
    from google import genai
    from google.genai import types as gtypes

    session_id = req.session_id or f"sess-{int(time.time() * 1000)}"
    persona = normalize_persona(req.persona)
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

    contract = await turn_runner.execute_turn_async(
        query=transcript,
        session_id=session_id,
        persona=persona,
        language=req.language or "en",
    )
    return {
        "status": "ok",
        "transcript": transcript,
        "contract": contract,
    }


try:
    EXPORT_TTL_SECONDS = int(os.getenv("YUKTI_EXPORT_TTL_SECONDS", "3600"))
except ValueError:
    EXPORT_TTL_SECONDS = 3600


def _sweep_old_exports() -> None:
    """H1.3a: Cloud Run's filesystem is RAM — delete exports older than the TTL (default 1 h)."""
    cutoff = time.time() - EXPORT_TTL_SECONDS
    try:
        for f in EXPORTS_DIR.glob("*"):
            if f.is_file() and not f.name.startswith(".") and f.stat().st_mtime < cutoff:
                f.unlink(missing_ok=True)
    except Exception as exc:  # never fail an export because of housekeeping
        logger.warning(f"export sweep skipped: {exc}")


@app.post("/api/export")
def create_export(req: ExportRequest) -> Dict[str, Any]:
    """Generates an export file and returns {export_id, filename, format}."""
    fmt = req.format.lower().strip()
    # H1.3a: 128-bit random ids (unguessable — downloads are unauthenticated); old files are swept on each create
    export_id = f"exp_{uuid.uuid4().hex}"
    _sweep_old_exports()
    clean_title = re.sub(r"[^a-zA-Z0-9_\-]", "_", req.title or "Yukti_Export")
    
    try:
        if "word" in fmt or "docx" in fmt:
            filename = f"{clean_title}.docx"
            exporter.export_word(markdown_text=req.content or "", filename=f"{export_id}.docx")
            return {"export_id": export_id, "filename": filename, "format": "docx"}
        elif "pdf" in fmt:
            filename = f"{clean_title}.pdf"
            exporter.export_pdf(markdown_text=req.content or "", filename=f"{export_id}.pdf")
            return {"export_id": export_id, "filename": filename, "format": "pdf"}
        elif "xlsx" in fmt or "sheets" in fmt:
            filename = f"{clean_title}.xlsx"
            exporter.export_xlsx(columns=req.columns or [], rows=req.rows or [], filename=f"{export_id}.xlsx")
            return {"export_id": export_id, "filename": filename, "format": "xlsx"}
        elif "docs" in fmt:
            filename = f"{clean_title}.docx"
            res = exporter.export_google_docs(title=clean_title, markdown_text=req.content or "", file_id=export_id)
            return {"export_id": export_id, "filename": filename, "format": "docs", "url": res.get("url")}
        raise HTTPException(
            status_code=400,
            detail={"type": "error", "message": f"Unsupported export format: {req.format}", "retryable": False},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Export creation failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail={"type": "error", "message": "Export failed. Please try again.", "retryable": True},  # no internals
        )


@app.get("/api/export/{export_id}")
def download_export(export_id: str):
    """Downloads an exported file securely from the exports directory only."""
    # H1.3a: only ids we mint (exp_<32 hex>) are servable; anything else is a 404 (no globbing on user input)
    if not re.fullmatch(r"exp_[0-9a-f]{32}", export_id or ""):
        raise HTTPException(
            status_code=404,
            detail={"type": "error", "message": "Export not found.", "retryable": False},
        )
    root = EXPORTS_DIR.resolve()
    matches = [p for p in EXPORTS_DIR.glob(f"{export_id}.*") if p.resolve().parent == root and p.suffix.lower() in (".docx", ".xlsx", ".pdf", ".csv")]
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
        ".csv": "text/csv",
    }
    media_type = media_types.get(ext, "application/octet-stream")
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type=media_type,
    )


@app.websocket("/ws/live")
async def websocket_live_endpoint(
    websocket: WebSocket,
    session_id: Optional[str] = Query(None),
    persona: Optional[str] = Query("CMD"),
    model: Optional[str] = Query(DEFAULT_LIVE_MODEL),
    voice: Optional[str] = Query(DEFAULT_VOICE),
    language: Optional[str] = Query("en"),
):
    await websocket.accept()
    sess_id = session_id or f"live-sess-{int(time.time() * 1000)}"
    manager = LiveSessionManager(
        websocket=websocket,
        session_id=sess_id,
        persona=normalize_persona(persona),
        model_name=model or DEFAULT_LIVE_MODEL,
        voice=voice or DEFAULT_VOICE,
        language=language or "en",
    )
    await manager.run()
