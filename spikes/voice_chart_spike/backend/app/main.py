"""FastAPI backend application for ONGC Voice-to-Chart Spike.
Provides WebSocket /ws/live for ADK bidi-streaming, REST health checks, and direct tool test routes.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agent import DEFAULT_LIVE_MODEL, DEFAULT_VOICE
from app.live_session import LiveSessionManager
from app.tools.bq_headcount import query_headcount_tenure
from app.tools.policy_search import search_policy

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("voice_chart_spike.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ONGC HR & Finance Voice-Chart Spike Backend...")
    yield
    logger.info("Shutting down ONGC HR & Finance Voice-Chart Spike Backend...")


app = FastAPI(
    title="ONGC HR & Finance Voice-to-Chart Spike API",
    version="0.1.0",
    lifespan=lifespan
)

# Enable CORS for Next.js / React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ongc-voice-chart-spike-backend",
        "default_model": DEFAULT_LIVE_MODEL,
        "default_voice": DEFAULT_VOICE,
        "location": os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        "project": os.getenv("GOOGLE_CLOUD_PROJECT", "ongc-hr-finance-agent"),
    }


class HeadcountRequest(BaseModel):
    location: str = "Delhi"
    min_years: int = 5
    grade_filter: Optional[str] = None


@app.post("/api/tools/headcount")
async def test_headcount_tool(req: HeadcountRequest) -> Dict[str, Any]:
    """Direct REST test endpoint for query_headcount_tenure."""
    return query_headcount_tenure(
        location=req.location,
        min_years=req.min_years,
        grade_filter=req.grade_filter
    )


class PolicyRequest(BaseModel):
    query: str


@app.post("/api/tools/policy")
async def test_policy_tool(req: PolicyRequest) -> Dict[str, Any]:
    """Direct REST test endpoint for search_policy."""
    return search_policy(query=req.query)


@app.websocket("/ws/live")
async def websocket_live_endpoint(
    websocket: WebSocket,
    model: str = DEFAULT_LIVE_MODEL,
    voice: str = DEFAULT_VOICE,
    language: str = "en-IN"
):
    """Bidirectional WebSocket endpoint for the voice-to-chart agent."""
    await websocket.accept()
    logger.info(f"WebSocket client connected: model={model}, voice={voice}, language={language}")
    session_mgr = LiveSessionManager(
        websocket=websocket,
        model_name=model,
        voice=voice,
        language=language
    )
    await session_mgr.run()
