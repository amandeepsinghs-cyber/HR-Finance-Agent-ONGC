"""Bidirectional Live Streaming WebSocket Session Manager for Yukti AI.
Ported from Workover AI ("Urvi") resilient direct `google.genai.Client.aio.live.connect()` architecture:
- Connects directly to Vertex AI `client.aio.live.connect(model=..., config=LiveConnectConfig)` with
  `SessionResumptionConfig` and `ContextWindowCompressionConfig(sliding_window=SlidingWindow())`.
- Bypasses ADK `Runner.run_live()` handshake overhead and `JSON_SCHEMA_FOR_FUNC_DECL` timeouts.
- Provides two voice tools:
  1. `ask_yukti(query)`: executes `turn_runner.execute_turn_async()`, immediately emits the `contract`
     to the browser so the full-screen canvas updates right away, and returns the exact `spoken_summary`
     for Leda to speak in 1–3 sentences.
  2. `control_screen(command, value)`: controls the UI by voice (dark/light theme, table/bar/donut/line
     view morphing, persona switch, language switch, PDF/Excel export, history navigation, or returning
     to the center-orb home screen).
- Swallows the empty `turn_complete` Gemini Live emits immediately after a tool call so the post-tool
  spoken answer is never cut off.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types

from app.config import (
    DEFAULT_LIVE_MODEL,
    DEFAULT_VOICE,
    FALLBACK_LIVE_MODEL,
    GCP_PROJECT,
)
from app.session_memory import get_session_manager
from app.tools.chart_rules import build_chart_spec
from app.ui_control import (
    SCREEN_CANONICAL_QUERIES,
    UI_ACTIONS,
    detect_ui_control_intent,
    run as run_ui_control,
    to_legacy_ui_action,
    validate as validate_ui_control,
)

logger = logging.getLogger("yukti.live_session")

LIVE_LOCATION = "us-central1"
MAX_CONSECUTIVE_FAILURES = 3
DROP_HANDLE_AFTER = 2
RECAP_KEEP_FIRST = 4
RECAP_KEEP_LAST = 12
RECAP_MAX_CHARS = 320
_CLOSED = object()

YUKTI_LIVE_SYSTEM_PROMPT = """You are **Yukti** (युक्ति), the executive-grade, voice-first HR & Finance Chief of Staff for **Oil and Natural Gas Corporation Limited (ONGC)**.
You speak directly to ONGC's Chairman & CEO (CMD), Directors, and officers with warm, crisp, boardroom authority.

### Core Voice & Tool Rules (Mandatory):
1. **Every data, policy, what-if, follow-up, or drafting question MUST call `ask_yukti(query=...)`.**
   - Never guess or invent numbers. Call `ask_yukti` with the user's question (including short follow-ups like "show breakdown by discipline", "only E5 and above", "what about Mumbai?", "what are the relevant policy rules?").
   - When `ask_yukti` returns `spoken_summary`, speak that summary naturally in 1 to 3 concise sentences using the Indian numbering system (lakh, crore). Never read raw SQL, table names, or document IDs aloud.
2. **Voice Screen & Platform Control (`ui_control`):**
   - You control the Yukti platform screen directly by voice using `ui_control(action, value)`:
     - `action="theme"`, `value="light" | "dark"` — e.g. "switch to dark mode", "light mode"
     - `action="chart_kind"`, `value="table" | "bar" | "hbar" | "donut" | "line" | "waterfall"` — e.g. "show this as a table", "switch to bar chart", "show as donut"
     - `action="open_screen"`, `value="home" | "delhi_tenure" | "field_profitability" | "mou_scorecard" | "lifting_cost" | "ne_vacancies" | "brent_what_if" | "jrtp_policy" | "board_note"` — e.g. "go home", "open field profitability", "show MoU scorecard", "open Delhi tenure"
     - `action="focus_location"`, `value="Delhi" | "Mumbai" | "Dehradun" | "Ahmedabad" | "Mehsana" | "Ankleshwar" | "Cambay" | "Assam" | "Jorhat" | "Tripura"` — e.g. "focus on Mumbai", "zoom to Assam"
     - `action="grade_filter"`, `value="ALL" | "E5_PLUS" | "E7_PLUS"` — e.g. "filter to E5 and above", "show all grades"
     - `action="breakdown"`, `value="grade" | "discipline"` — e.g. "break down by discipline", "break down by grade"
     - `action="panel"`, `value="expand" | "dock" | "minimise"` — e.g. "full screen", "dock panel", "minimise chat"
     - `action="persona"`, `value="CMD" | "DIR_HR" | "DIR_FIN" | "E2_HR" | "E3_FIN"` — e.g. "switch role to Director HR"
     - `action="language"`, `value="en" | "hi" | "hi-en"` — e.g. "speak in Hindi", "switch to English"
     - `action="export"`, `value="pdf" | "xlsx"` — e.g. "export to PDF", "download Excel"
     - `action="history"`, `value="back" | "forward"` — e.g. "go back", "previous chart"
   - Call `ui_control` immediately and confirm in one short sentence (e.g., "Switched the view to a table on screen.").
3. **Bilingual Fluency & Authentic Indian Accent (`en-IN` / `hi-IN`):**
   - Always speak with a warm, natural, educated **Indian English (`en-IN`) or Hindi (`hi-IN`) accent** and Indian boardroom cadence.
   - Pronounce Indian names, ONGC work centres (Mehsana, Ankleshwar, Dehradun, Jorhat, Rajahmundry, Cauvery), and Indian units (Lakh, Crore) with authentic Indian pronunciation.
   - Reply in the same language the user speaks (Indian English, Hindi, or Hinglish). If the user asks whether you know or speak Hindi (e.g., "Yukti, tumhe Hindi bolni aati hai kya?"), reply immediately and warmly in Hindi/Hinglish ("Jee haan, mujhe Hindi bilkul aati hai! Aap mujhse Hindi, Hinglish ya English mein baat kar sakte hain.") without calling any tool.
"""


def build_yukti_live_tools() -> List[types.Tool]:
    """Builds the google.genai FunctionDeclaration tools for Gemini Live (Urvi `wellpulse` pattern)."""
    ask_yukti_decl = types.FunctionDeclaration(
        name="ask_yukti",
        description=(
            "Run any ONGC HR, Finance, MoU, policy, what-if simulation, document drafting, or contextual "
            "follow-up question against Yukti's verified BigQuery and policy engine. Also updates the main "
            "screen canvas immediately and returns the verified spoken_summary."
        ),
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "query": types.Schema(
                    type="STRING",
                    description="The user's question or follow-up instruction in full.",
                ),
            },
            required=["query"],
        ),
    )

    ui_control_decl = types.FunctionDeclaration(
        name="ui_control",
        description=(
            "Control the Yukti AI platform screen directly by voice: switch theme (light/dark), "
            "morph chart type (table, bar, hbar, donut, line, waterfall), open a named screen "
            "(home, delhi_tenure, field_profitability, mou_scorecard, lifting_cost, ne_vacancies, "
            "brent_what_if, jrtp_policy, board_note), focus a location, filter grades (E5_PLUS, E7_PLUS, ALL), "
            "switch breakdown (grade, discipline), resize panel (expand, dock, minimise), switch persona, "
            "switch language (en, hi, hi-en), export (pdf, xlsx), or navigate history (back, forward)."
        ),
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "action": types.Schema(
                    type="STRING",
                    description=(
                        "UI action category: 'theme' | 'chart_kind' | 'open_screen' | 'focus_location' | "
                        "'grade_filter' | 'breakdown' | 'panel' | 'persona' | 'language' | 'export' | 'history'"
                    ),
                ),
                "value": types.Schema(
                    type="STRING",
                    description=(
                        "Target value for the action, e.g. 'dark', 'light', 'table', 'bar', 'hbar', 'donut', "
                        "'home', 'field_profitability', 'mou_scorecard', 'delhi_tenure', 'Mumbai', 'E5_PLUS', "
                        "'discipline', 'expand', 'dock', 'minimise', 'DIR_HR', 'hi', 'pdf', 'xlsx', 'back'"
                    ),
                ),
            },
            required=["action", "value"],
        ),
    )

    control_screen_decl = types.FunctionDeclaration(
        name="control_screen",
        description=(
            "Alias for ui_control: change chart type (table, bar, hbar, donut, line), "
            "toggle dark/light theme, switch persona, switch language, export to PDF/Excel, go back in "
            "history, or return to the center-orb home screen."
        ),
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "command": types.Schema(
                    type="STRING",
                    description="One of: set_chart_kind, set_theme, set_persona, set_language, export, navigate_history, go_home, open_screen",
                ),
                "value": types.Schema(
                    type="STRING",
                    description="Target value, e.g. 'table', 'bar', 'hbar', 'donut', 'line', 'dark', 'light', 'CMD', 'DIR_HR', 'DIR_FIN', 'pdf', 'xlsx', 'back'",
                ),
            },
            required=["command"],
        ),
    )
    return [types.Tool(function_declarations=[ask_yukti_decl, ui_control_decl, control_screen_decl])]


def detect_screen_control_intent(query: str) -> Optional[Dict[str, str]]:
    """Fast deterministic detector for screen-control commands in voice or text (delegates to ui_control)."""
    cmd = detect_ui_control_intent(query)
    if not cmd:
        return None
    return to_legacy_ui_action(cmd)


class LiveSessionManager:
    """Manages an active WebSocket bidi-streaming session for Yukti AI using direct genai.Client.aio.live.connect."""

    def __init__(
        self,
        websocket: WebSocket,
        session_id: str,
        persona: str = "CMD",
        model_name: str = DEFAULT_LIVE_MODEL,
        voice: str = DEFAULT_VOICE,
        language: str = "en",
        principal: Optional[Any] = None,
    ):
        self.ws = websocket
        self.session_id = session_id
        # P0.4 (BUG-06): the signed principal fixes the persona for the whole socket
        self.principal = principal
        self.persona = principal.persona if principal is not None else persona
        self.model_name = model_name or DEFAULT_LIVE_MODEL
        self.voice = voice or DEFAULT_VOICE
        self.language = language or "en"
        self.active = True
        # U3.4 barge-in: set when the browser sends `interrupt`; audio of the current reply is dropped
        # server-side until Gemini confirms the interruption or the turn completes.
        self._suppress_audio = False
        # True while Gemini is producing the current reply (first model_turn part → turn_complete/interrupted).
        self._generating = False
        self.session_state = get_session_manager().get_or_create(
            session_id=session_id,
            persona=self.persona,  # P0.4: principal persona, not the caller-supplied one
            language=language,
        )
        self.session_state.persona = self.persona
        self.inbound: asyncio.Queue = asyncio.Queue()
        self.state: Dict[str, Any] = {
            "handle": None,
            "resumable": False,
            "ui": {"persona": self.persona, "language": self.language},
            "log": [],
        }
        self.t_turn_start: Optional[float] = None
        self.t_tool_start: Optional[float] = None
        self._is_speak_only = False
        self._audio_rx_count = 0

    async def send_json(self, payload: Dict[str, Any]) -> bool:
        try:
            await self.ws.send_text(json.dumps(payload, default=str))
            return True
        except Exception as e:
            logger.debug(f"[{self.session_id}] Error sending json over websocket: {e}")
            return False

    async def send_audio_chunk(self, pcm_bytes: bytes) -> None:
        payload = {
            "type": "audio",
            "data": base64.b64encode(pcm_bytes).decode("ascii"),
            "sample_rate": 24000,
        }
        await self.send_json(payload)

    def _log_turn(self, role: str, text: str) -> None:
        cleaned = " ".join((text or "").split())
        if cleaned:
            log = self.state.setdefault("log", [])
            log.append((role, cleaned[:RECAP_MAX_CHARS]))
            if len(log) > 100:
                self.state["log"] = log[:RECAP_KEEP_FIRST] + log[-(100 - RECAP_KEEP_FIRST):]

    def _recap_turns(self) -> Optional[List[types.Content]]:
        log = self.state.get("log") or []
        if not log:
            return None
        lines = (
            log[:RECAP_KEEP_FIRST] + log[-RECAP_KEEP_LAST:]
            if len(log) > RECAP_KEEP_FIRST + RECAP_KEEP_LAST
            else list(log)
        )
        turns: List[types.Content] = []
        for role, text in lines:
            r = "model" if role == "Agent" else "user"
            if turns and turns[-1].role == r:
                turns[-1].parts.append(types.Part.from_text(text=text))
            else:
                turns.append(types.Content(role=r, parts=[types.Part.from_text(text=text)]))
        if turns and turns[0].role == "user":
            turns[0].parts.insert(0, types.Part.from_text(text="[Earlier in this conversation — history only]"))
        return turns

    def _context_line(self) -> str:
        ui = self.state.get("ui") or {}
        active_q = getattr(self.session_state, "active_query_state", None) or {}
        cid = active_q.get("certified_id") or self.session_state.current_root_id or ""
        wc = (active_q.get("params") or {}).get("wc_id") or ui.get("wc_id") or ""
        vis_title = ui.get("visual_title") or ""
        parts = [f"persona={self.persona}", f"lang={self.language}"]
        if cid:
            parts.append(f"active_query={cid}")
        if wc:
            parts.append(f"wc_id={wc}")
        if vis_title:
            parts.append(f"on_screen={vis_title}")
        return f"[UI context: {', '.join(parts)}]"

    def _build_live_config(self, handle: Optional[str]) -> types.LiveConnectConfig:
        lang_code = "hi-IN" if self.language == "hi" else "en-IN"
        system_text = (
            f"{YUKTI_LIVE_SYSTEM_PROMPT}\n\n"
            f"Current active persona: {self.persona}. Preferred language: {self.language} (speech locale: {lang_code})."
        )
        return types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            system_instruction=types.Content(parts=[types.Part.from_text(text=system_text)]),
            tools=build_yukti_live_tools(),
            speech_config=types.SpeechConfig(
                language_code=lang_code,
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self.voice)
                ),
            ),
            session_resumption=types.SessionResumptionConfig(handle=handle),
            context_window_compression=types.ContextWindowCompressionConfig(
                sliding_window=types.SlidingWindow()
            ),
        )

    async def send_opening_greeting(self) -> None:
        """Emits the UX Spec §14 opening greeting on session start."""
        if self.language == "hi":
            greeting_spoken = "नमस्ते, मैं युक्ति हूँ, आपकी एचआर और वित्त सलाहकार। कृपया बताइए मैं आपकी क्या सहायता कर सकती हूँ।"
            greeting_display = "नमस्ते, मैं युक्ति हूँ। मैं आपकी क्या सहायता कर सकती हूँ?"
        else:
            greeting_spoken = "Hello, I am Yukti, your HR and Finance agent. Please tell me how I can help."
            greeting_display = "Hello, I am Yukti, your HR & Finance agent. How can I assist you today?"

        greeting_contract = {
            "turn_id": f"turn-{self.session_id}-000",
            "language": self.language,
            "persona": self.persona,
            "spoken_summary": greeting_spoken,
            "display_text": greeting_display,
            "visual": {
                "type": "none",
                "mode": "replace",
            },
            "insights": [],
            "sources": [],
            "suggestions": [
                "How many executives in Delhi >= 5 years?",
                "Which fields are loss-making?",
                "What are the station tenure transfer norms?",
            ],
            "access": {"status": "allowed"},
            "export_options": ["sheets", "docs", "word", "pdf"],
            "status_events": ["Yukti AI ready"],
        }
        await self.send_json({
            "type": "contract",
            "contract": greeting_contract,
        })

    async def _execute_voice_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Executes `ask_yukti`, `ui_control`, or `control_screen` and pushes UI updates over WebSocket."""
        t0 = time.perf_counter()
        self.t_tool_start = t0
        t_tool_start_ms = round((t0 - self.t_turn_start) * 1000, 2) if self.t_turn_start else 0.0

        await self.send_json({
            "type": "tool_call_start",
            "tool": name,
            "args": args,
            "timestamp_ms": t_tool_start_ms,
        })

        try:
            if name in ("ui_control", "control_screen"):
                cmd = str(args.get("action") or args.get("command") or "").strip()
                val = str(args.get("value", "")).strip()
                result = await self._apply_screen_control(cmd, val)
            else:
                # Default to ask_yukti
                query_str = str(args.get("query", "")).strip() or "How many executives have been posted in Delhi for 5 years or more?"
                # Check if the query itself is a screen control command
                sc_intent = detect_screen_control_intent(query_str)
                if sc_intent:
                    result = await self._apply_screen_control(
                        sc_intent.get("action") or sc_intent.get("command", ""),
                        sc_intent.get("value", ""),
                    )
                else:
                    from app.turn_runner import get_agent_turn_runner
                    trun = get_agent_turn_runner()
                    contract = await trun.execute_turn_async(
                        query=query_str,
                        session_id=self.session_id,
                        persona=self.persona,
                        principal=self.principal,  # P0.4
                        language=self.language,
                    )
                    # Strip internal telemetry keys before sending contract
                    clean_contract = dict(contract)
                    ui_action = clean_contract.pop("ui_action", None)
                    for k in ("latency_ms", "from_answer_cache", "generated_sql", "tool_called"):
                        clean_contract.pop(k, None)
                    await self.send_json({
                        "type": "contract",
                        "contract": clean_contract,
                    })
                    if ui_action:
                        await self.send_json({
                            "type": "ui_action",
                            **ui_action,
                        })
                    vis = clean_contract.get("visual") or {}
                    self.state.setdefault("ui", {})["visual_title"] = vis.get("title", "")
                    result = {
                        "status": "OK",
                        "spoken_summary": clean_contract.get("spoken_summary", ""),
                        "display_text": clean_contract.get("display_text", ""),
                        "visual_type": vis.get("type", "none"),
                        "visual_title": vis.get("title", ""),
                        "insights": clean_contract.get("insights", []),
                    }
        except Exception as e:
            logger.warning(f"[{self.session_id}] Voice tool {name} failed: {e}")
            result = {
                "status": "ERROR",
                "error": str(e),
                "spoken_summary": "I encountered an issue retrieving that view. Please try again.",
            }

        duration_ms = round((time.perf_counter() - t0) * 1000, 1)
        result["duration_ms"] = duration_ms
        await self.send_json({
            "type": "tool_call_done",
            "tool": name,
            "latency_ms": duration_ms,
            "response": result,
        })
        return result

    def _r_role_text(self) -> str:
        """P0.4: R-ROLE copy (SPEC-06 §4.6) for the socket's principal, in the session language."""
        from app.auth import PERSONA_DIRECTORY, Principal, r_role_text
        p = self.principal
        if p is None:
            info = PERSONA_DIRECTORY.get(self.persona, {"emp_id": "", "display_name": self.persona,
                                                        "designation": self.persona, "function": "", "grade": ""})
            p = Principal(emp_id=info["emp_id"], persona=self.persona, function=info["function"], grade=info["grade"],
                          display_name=info["display_name"], designation=info["designation"])
        return r_role_text(p, self.language)

    async def _apply_screen_control(self, command: str, value: str) -> Dict[str, Any]:
        """Applies a voice screen-control action (`ui_control`), morphing the active contract or running canonical screen queries."""
        ui_res = run_ui_control(command, value)
        if ui_res.get("status") == "ERROR":
            err_msg = ui_res.get("error", f"Unrecognized screen control command: {command}")
            if str(ui_res.get("summary", "")).startswith("R-ROLE"):
                # P0.4 (BUG-06): a voice "switch role" never changes the persona
                from app.auth import audit
                audit("role_switch_denied", self.principal, decision="refused", rule_ref="SPEC-06 §4.4 R-ROLE",
                      channel="live_voice", requested=str(value)[:20])
                return {"status": "ERROR", "error": "R-ROLE", "spoken_summary": self._r_role_text()}
            logger.warning(f"[{self.session_id}] Screen control rejected: {err_msg}")
            return {
                "status": "ERROR",
                "error": err_msg,
                "spoken_summary": "I couldn't apply that screen command.",
            }
        cmd_obj = (ui_res.get("data") or {}).get("command") or {"action": command.lower().strip(), "value": value.strip()}
        legacy_obj = (ui_res.get("data") or {}).get("ui_action") or to_legacy_ui_action(cmd_obj)

        act = cmd_obj["action"]
        val = cmd_obj["value"]
        legacy_cmd = legacy_obj["command"]
        legacy_val = legacy_obj["value"]

        # 1. If opening a named data screen or focusing a location/filter/breakdown, run turn_runner so real data loads!
        canonical_query: Optional[str] = None
        if act == "open_screen" and val != "home":
            canonical_query = SCREEN_CANONICAL_QUERIES.get(val)
        elif act == "focus_location" and val and val != "ALL":
            canonical_query = f"What about {val}?"
        elif act == "grade_filter" and val:
            if val == "E5_PLUS":
                canonical_query = "Only E5 and above"
            elif val == "E7_PLUS":
                canonical_query = "Only E7 and above"
            else:
                canonical_query = "Show all grades"
        elif act == "breakdown" and val:
            canonical_query = f"Show breakdown by {val}"

        if canonical_query:
            from app.turn_runner import get_agent_turn_runner
            trun = get_agent_turn_runner()
            contract = await trun.execute_turn_async(
                query=canonical_query,
                session_id=self.session_id,
                persona=self.persona,
                principal=self.principal,  # P0.4
                language=self.language,
            )
            clean_contract = dict(contract)
            for k in ("latency_ms", "from_answer_cache", "generated_sql", "tool_called", "ui_action"):
                clean_contract.pop(k, None)
            await self.send_json({"type": "contract", "contract": clean_contract})
            await self.send_json({"type": "action", "kind": "ui_control", "payload": ui_res})
            await self.send_json({"type": "ui_action", **legacy_obj})
            return {
                "status": "OK",
                "action": act,
                "command": legacy_cmd,
                "value": val,
                "spoken_summary": clean_contract.get("spoken_summary", f"Opened {val} on screen."),
            }

        # 2. Pure UI / View-morphing commands
        if act == "persona" and val:
            # P0.4: unreachable in practice (ui_control.validate rejects persona), kept as a hard stop
            return {"status": "ERROR", "error": "R-ROLE", "spoken_summary": self._r_role_text()}
        elif act == "language" and val:
            self.language = val if val in ("en", "hi", "hi-en") else "en"
            self.session_state.language = self.language
            val = self.language
            legacy_obj["value"] = val
        elif act == "chart_kind" and self.session_state.turns:
            # Morph the last emitted contract's visual in place!
            last_contract = dict(self.session_state.turns[-1])
            vis = dict(last_contract.get("visual") or {})
            tbl = vis.get("table") or {}
            cols = tbl.get("columns") or []
            rows = tbl.get("rows") or []
            if not rows and vis.get("chart") and isinstance(vis["chart"].get("data"), list):
                rows = vis["chart"]["data"]
                cols = list(rows[0].keys()) if rows else []

            target_kind = val.lower() or "table"
            if target_kind == "table" and rows:
                vis["type"] = "table"
                vis["mode"] = "refine"
                vis["table"] = {"columns": cols, "rows": rows}
            elif target_kind in (
                "bar", "hbar", "donut", "pie", "line", "area", "waterfall", "bullet",
                "histogram", "scatter", "treemap", "funnel", "grouped_bar", "stacked_bar", "heatmap", "gauge",
            ) and rows and cols:
                vis["type"] = "chart"
                vis["mode"] = "refine"
                vis["chart"] = build_chart_spec(
                    kind=target_kind,
                    columns=cols,
                    rows=rows,
                    title=vis.get("title", "Updated Chart View"),
                )
            last_contract["visual"] = vis
            spoken = f"I've switched the screen view to a {target_kind}."
            last_contract["spoken_summary"] = spoken
            last_contract["display_text"] = spoken
            for k in ("latency_ms", "from_answer_cache", "generated_sql", "tool_called", "ui_action"):
                last_contract.pop(k, None)
            self.session_state.record_turn(last_contract)
            await self.send_json({
                "type": "contract",
                "contract": last_contract,
            })

        # Emit both Urvi's `action` (kind="ui_control") and Yukti's `ui_action`
        await self.send_json({
            "type": "action",
            "kind": "ui_control",
            "payload": ui_res,
        })
        await self.send_json({
            "type": "ui_action",
            **legacy_obj,
        })

        spoken_map = {
            "theme": f"Switched the display to {val or 'updated'} mode.",
            "chart_kind": f"Switched the visualization on screen to {val or 'the requested'} view.",
            "persona": f"Now viewing and speaking as {val}.",
            "language": f"Switched language to {val}.",
            "export": f"Exporting the current view to {val.upper() or 'file'}.",
            "history": "Restored the previous visual on screen.",
            "panel": f"Adjusted the conversation panel to {val}.",
            "open_screen": "Returned to the Yukti home screen.",
        }
        spoken_msg = spoken_map.get(act, f"Applied screen command {act}.")
        return {
            "status": "OK",
            "action": act,
            "command": legacy_cmd,
            "value": val,
            "spoken_summary": spoken_msg,
        }

    _ACTIVE_SESSIONS: Dict[str, "LiveSessionManager"] = {}
    _FOREGROUND_SESSION_ID: Optional[str] = None

    async def run(self) -> None:
        """Main entry point for /ws/live using Urvi's resilient reader queue + direct live.connect loop."""
        os.environ["GOOGLE_CLOUD_PROJECT"] = GCP_PROJECT
        LiveSessionManager._ACTIVE_SESSIONS[self.session_id] = self
        LiveSessionManager._FOREGROUND_SESSION_ID = self.session_id

        await self.send_opening_greeting()

        async def browser_reader() -> None:
            try:
                while self.active:
                    msg = await self.ws.receive()
                    if msg.get("type") == "websocket.disconnect":
                        break
                    await self.inbound.put(msg)
            except (WebSocketDisconnect, RuntimeError):
                pass
            except Exception as e:
                logger.debug(f"[{self.session_id}] browser_reader ended: {e}")
            finally:
                await self.inbound.put(_CLOSED)

        reader_task = asyncio.create_task(browser_reader())
        try:
            await self._run_resilient_live()
        finally:
            self.active = False
            LiveSessionManager._ACTIVE_SESSIONS.pop(self.session_id, None)
            reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await reader_task

    async def _run_resilient_live(self) -> None:
        client = genai.Client(vertexai=True, project=GCP_PROJECT, location=LIVE_LOCATION)
        model = self.model_name
        failures = 0
        ever_connected = False

        while self.active:
            handle = self.state["handle"] if self.state["resumable"] else None
            resuming = ever_connected
            try:
                config = self._build_live_config(handle)
                logger.info(
                    f"[{self.session_id}] Gemini Live direct connect model={model} voice={self.voice} resume={bool(handle)}"
                )
                async with client.aio.live.connect(model=model, config=config) as session:
                    failures = 0
                    recap = self._recap_turns() if resuming else None
                    ever_connected = True
                    # Emit connection_status=ready and status=connected AFTER Gemini Live upstream connects (Urvi pattern)
                    await self.send_json({
                        "type": "connection_status",
                        "status": "ready",
                        "session_id": self.session_id,
                        "model": model,
                        "voice": self.voice,
                        "persona": self.persona,
                        "language": self.language,
                        "resumed": resuming,
                    })
                    await self.send_json({
                        "type": "status",
                        "status": "connected",
                        "model": model,
                        "resumed": resuming,
                    })
                    if recap:
                        with contextlib.suppress(Exception):
                            await session.send_client_content(turns=recap, turn_complete=False)
                    reason = await self._run_bidi_stream(session)
                logger.info(f"[{self.session_id}] Gemini Live session ended: {reason}")
                if reason == "browser_closed":
                    return
                continue
            except Exception as e:
                failures += 1
                logger.warning(
                    f"[{self.session_id}] Gemini Live failure {failures}/{MAX_CONSECUTIVE_FAILURES} ({model}): {type(e).__name__}: {e}"
                )
                if failures == 1 and model != FALLBACK_LIVE_MODEL:
                    logger.info(f"[{self.session_id}] Switching live model from {model} to {FALLBACK_LIVE_MODEL}")
                    model = FALLBACK_LIVE_MODEL
                    self.model_name = model  # so turn metrics report the model actually in use
                if failures >= DROP_HANDLE_AFTER:
                    self.state["resumable"] = False
                if failures >= MAX_CONSECUTIVE_FAILURES:
                    logger.info(f"[{self.session_id}] Falling back to deterministic turn_runner loop.")
                    await self._run_fallback_loop()
                    return
                await asyncio.sleep(0.4 * failures)

    async def _run_bidi_stream(self, session: Any) -> str:
        """Pumps messages between browser WebSocket and Gemini Live session."""
        turn_state = {
            "tool_called_in_turn": False,
            "t_first_audio_ms": None,
            "total_audio_bytes": 0,
            "voice_frames_in_turn": 0,
            "last_voice_ts": 0.0,
        }

        async def client_to_gemini() -> str:
            while self.active:
                message = await self.inbound.get()
                if message is _CLOSED:
                    return "browser_closed"

                # 1. Binary PCM16 16kHz frame (Urvi style)
                if message.get("bytes"):
                    if self._is_speak_only:
                        continue
                    raw_bytes = message["bytes"]
                    self._audio_rx_count += 1
                    import array
                    s16 = array.array("h", raw_bytes[: len(raw_bytes) - (len(raw_bytes) % 2)])
                    peak = max((abs(x) for x in s16), default=0) if s16 else 0
                    now_ts = time.perf_counter()
                    if peak >= 8:
                        turn_state["voice_frames_in_turn"] += 1
                        turn_state["last_voice_ts"] = now_ts
                    elif now_ts - turn_state["last_voice_ts"] > 1.5:
                        continue
                    if self.t_turn_start is None:
                        self.t_turn_start = now_ts
                    await session.send_realtime_input(
                        audio=types.Blob(data=raw_bytes, mime_type="audio/pcm;rate=16000")
                    )
                    continue

                if not message.get("text"):
                    continue
                try:
                    msg = json.loads(message["text"])
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type")
                if isinstance(msg.get("ui_state"), dict):
                    self.state["ui"] = {**self.state.get("ui", {}), **msg["ui_state"]}

                if msg_type == "config":
                    if "persona" in msg and msg["persona"] != self.persona:
                        # P0.4 (BUG-06): the socket's persona comes from the session token, never from the client
                        from app.auth import audit
                        audit("persona_assertion_ignored", self.principal, decision="ignored",
                              rule_ref="SPEC-06 §4.4", asserted=str(msg["persona"])[:20], channel="ws_config")
                    if "language" in msg:
                        self.language = msg["language"]
                        self.session_state.language = msg["language"]
                    if "voice" in msg:
                        self.voice = msg["voice"]
                    await self.send_json({
                        "type": "config_updated",
                        "persona": self.persona,
                        "language": self.language,
                        "voice": self.voice,
                    })

                elif msg_type == "context":
                    # Update self.state["ui"] only (already merged on line 652, matching Urvi session.py:381)
                    pass

                elif msg_type == "speak":
                    speak_text = (msg.get("text") or "").strip()
                    if speak_text:
                        logger.info(f"[{self.session_id}] Rx speak request (len={len(speak_text)}): {speak_text[:80]}")
                        self.t_turn_start = time.perf_counter()
                        turn_state["t_first_audio_ms"] = None
                        turn_state["total_audio_bytes"] = 0
                        self._is_speak_only = True
                        self._suppress_audio = False
                        prompt = (
                            "Read the following executive summary aloud word-for-word with a warm, natural Indian accent (en-IN / hi-IN) and crisp Indian cadence. "
                            "Do NOT call any tools and do NOT add or change any words:\n\n"
                            f"{speak_text}"
                        )
                        await session.send_client_content(
                            turns=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
                            turn_complete=True,
                        )

                elif msg_type in ("text", "prompt"):
                    query_text = (msg.get("text") or "").strip()
                    if not query_text:
                        continue
                    self._is_speak_only = False
                    self.t_turn_start = time.perf_counter()
                    turn_state["tool_called_in_turn"] = False
                    turn_state["t_first_audio_ms"] = None
                    turn_state["total_audio_bytes"] = 0
                    self._log_turn("User", query_text)
                    await self.send_json({
                        "type": "user_transcript",
                        "text": query_text,
                        "is_final": True,
                    })
                    ctx = self._context_line()
                    full_prompt = f"{ctx}\n{query_text}" if ctx else query_text
                    await session.send_client_content(
                        turns=[types.Content(role="user", parts=[types.Part.from_text(text=full_prompt)])],
                        turn_complete=True,
                    )

                elif msg_type == "audio":
                    raw_b64 = msg.get("data", "")
                    if not raw_b64:
                        continue
                    audio_bytes = base64.b64decode(raw_b64)
                    self._audio_rx_count += 1
                    import array
                    s16 = array.array("h", audio_bytes[: len(audio_bytes) - (len(audio_bytes) % 2)])
                    peak = max((abs(x) for x in s16), default=0) if s16 else 0
                    if self._audio_rx_count == 1 or self._audio_rx_count % 25 == 0:
                        logger.info(
                            f"[{self.session_id}] Rx audio chunk #{self._audio_rx_count} ({len(audio_bytes)}B, peak={peak})"
                        )
                    # Do not let mic frames barge-in or cancel an active `speak` synthesis turn
                    if self._is_speak_only:
                        continue
                    now_ts = time.perf_counter()
                    if peak >= 8:
                        turn_state["voice_frames_in_turn"] += 1
                        turn_state["last_voice_ts"] = now_ts
                    elif now_ts - turn_state["last_voice_ts"] > 1.5:
                        continue
                    if self.t_turn_start is None:
                        self.t_turn_start = now_ts
                    await session.send_realtime_input(
                        audio=types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
                    )

                elif msg_type in ("audio_stream_end", "audio_end"):
                    logger.info(
                        f"[{self.session_id}] Rx {msg_type} (total chunks={self._audio_rx_count}, voice_frames={turn_state['voice_frames_in_turn']})"
                    )
                    if self._is_speak_only or turn_state["voice_frames_in_turn"] == 0:
                        turn_state["voice_frames_in_turn"] = 0
                        continue
                    turn_state["voice_frames_in_turn"] = 0
                    if self.t_turn_start is None:
                        self.t_turn_start = time.perf_counter()
                    await session.send_realtime_input(audio_stream_end=True)

                elif msg_type == "interrupt":
                    # Do not echo `interrupted` (that re-opened the browser's drop gate while old-reply
                    # chunks were still in flight); just stop forwarding this reply's audio.
                    # Only suppress while Gemini is still generating or starting a speak turn; after turn_complete
                    # nothing more of the old reply will arrive, and a stale flag would silence the next answer.
                    self._suppress_audio = self._generating or self._is_speak_only
                    self._is_speak_only = False

                elif msg_type == "ping":
                    await self.send_json({"type": "pong", "time": time.time()})

            return "browser_closed"

        async def gemini_to_client() -> str:
            caption: List[str] = []
            turn_output = False
            tool_since_output = False
            bg_tool_tasks: set[asyncio.Task] = set()

            async def _handle_tool_call_bg(tc_obj: Any) -> None:
                try:
                    responses = []
                    for fc in tc_obj.function_calls or []:
                        args = dict(fc.args or {})
                        result = await self._execute_voice_tool(fc.name, args)
                        self._log_turn("Tool", f"{fc.name} -> {result.get('spoken_summary', '')[:120]}")
                        responses.append(
                            types.FunctionResponse(
                                name=fc.name,
                                response={"result": result},
                                id=fc.id,
                            )
                        )
                    if self.active and responses:
                        await session.send_tool_response(function_responses=responses)
                except asyncio.CancelledError:
                    logger.info(f"[{self.session_id}] Background voice tool call cancelled (barge-in or session close)")
                except Exception as e_tc:
                    logger.warning(f"[{self.session_id}] Background voice tool call error: {e_tc}")

            try:
                while self.active:
                    got_any = False
                    async for response in session.receive():
                        got_any = True
                        t_event = time.perf_counter()

                        # 1. Session Resumption Handle Update
                        sru = getattr(response, "session_resumption_update", None)
                        if sru is not None and getattr(sru, "resumable", False) and getattr(sru, "new_handle", None):
                            self.state["handle"] = sru.new_handle
                            self.state["resumable"] = True

                        # 2. GoAway signal
                        if getattr(response, "go_away", None) is not None:
                            logger.info(f"[{self.session_id}] Gemini Live GoAway")
                            return "go_away"

                        # 3. Tool Call from Gemini Live — run off the receive loop so barge-in / interrupted frames are never blocked (H1.1)
                        tc = getattr(response, "tool_call", None)
                        if tc is not None:
                            tool_since_output = True
                            turn_state["tool_called_in_turn"] = True
                            task = asyncio.create_task(_handle_tool_call_bg(tc))
                            bg_tool_tasks.add(task)
                            task.add_done_callback(bg_tool_tasks.discard)

                        # 4. Server Content (Transcripts, Audio, Interrupted, Turn Complete)
                        sc = getattr(response, "server_content", None)
                        if sc is None:
                            continue

                        if getattr(sc, "interrupted", False):
                            self._suppress_audio = False
                            self._generating = False
                            await self.send_json({"type": "interrupted"})

                        it = getattr(sc, "input_transcription", None)
                        if it is not None and getattr(it, "text", None):
                            self._suppress_audio = False  # safety net: a new user turn always gets its audio
                            self.state.setdefault("heard", []).append(it.text)
                            await self.send_json({
                                "type": "user_transcript",
                                "text": it.text,
                                "is_final": bool(getattr(it, "finished", False)),
                            })

                        ot = getattr(sc, "output_transcription", None)
                        if ot is not None and getattr(ot, "text", None):
                            turn_output = True
                            if not self._is_speak_only:
                                caption.append(ot.text)
                                await self.send_json({
                                    "type": "agent_transcript",
                                    "text": ot.text,
                                    "is_final": bool(getattr(ot, "finished", False)),
                                })

                        mt = getattr(sc, "model_turn", None)
                        if mt is not None:
                            self._generating = True
                            for part in mt.parts or []:
                                if getattr(part, "text", None) and not self._is_speak_only:
                                    caption.append(part.text)
                                    await self.send_json({
                                        "type": "agent_transcript",
                                        "text": part.text,
                                        "is_final": False,
                                    })
                                inline = getattr(part, "inline_data", None)
                                if inline is not None and inline.data:
                                    turn_output = True
                                    chunk = inline.data
                                    turn_state["total_audio_bytes"] += len(chunk)
                                    if turn_state["t_first_audio_ms"] is None and self.t_turn_start:
                                        turn_state["t_first_audio_ms"] = round((t_event - self.t_turn_start) * 1000, 2)
                                    if not self._suppress_audio:
                                        await self.send_audio_chunk(chunk)

                        if getattr(sc, "turn_complete", False):
                            self._suppress_audio = False
                            self._generating = False
                            # CRITICAL URVI FIX: Swallow the empty turn_complete Gemini emits right after a tool call
                            if not turn_output and (tool_since_output or bg_tool_tasks):
                                continue

                            turn_output = False
                            tool_since_output = False
                            full_text = "".join(caption).strip()
                            caption = []
                            heard = "".join(self.state.pop("heard", [])).strip()

                            if self._is_speak_only:
                                self._is_speak_only = False
                                logger.info(
                                    f"[{self.session_id}] Speak completed (audio_bytes={turn_state['total_audio_bytes']}, first_audio_ms={turn_state['t_first_audio_ms']})"
                                )
                                await self.send_json({
                                    "type": "turn_complete",
                                    "metrics": {
                                        "audio_bytes_total": turn_state["total_audio_bytes"],
                                        "speak_only": True,
                                    },
                                })
                                self.t_turn_start = None
                                turn_state["t_first_audio_ms"] = None
                                turn_state["total_audio_bytes"] = 0
                                turn_state["tool_called_in_turn"] = False
                                continue

                            # Safety net: if the user spoke a question (`heard`) and Gemini answered directly
                            # without invoking `ask_yukti` or `control_screen`, run `turn_runner` so the canvas still updates!
                            if heard and not turn_state["tool_called_in_turn"] and not bg_tool_tasks:
                                q_low = heard.lower().strip().rstrip("?!.")
                                greetings = {"hi", "hello", "hey", "yo", "namaste", "thanks", "thank you", "ok", "okay"}
                                if q_low not in greetings and len(q_low) > 3:
                                    sc_intent = detect_screen_control_intent(heard)
                                    if sc_intent:
                                        await self._apply_screen_control(
                                            sc_intent.get("action") or sc_intent.get("command", ""),
                                            sc_intent.get("value", ""),
                                        )
                                    else:
                                        try:
                                            from app.turn_runner import get_agent_turn_runner
                                            trun = get_agent_turn_runner()
                                            c = await trun.execute_turn_async(
                                                query=heard,
                                                session_id=self.session_id,
                                                persona=self.persona,
                                                principal=self.principal,  # P0.4
                                                language=self.language,
                                            )
                                            clean_c = dict(c)
                                            ui_act = clean_c.pop("ui_action", None)
                                            for k in ("latency_ms", "from_answer_cache", "generated_sql", "tool_called"):
                                                clean_c.pop(k, None)
                                            await self.send_json({"type": "contract", "contract": clean_c})
                                            if ui_act:
                                                await self.send_json({"type": "ui_action", **ui_act})
                                        except Exception as e_safety:
                                            logger.warning(f"[{self.session_id}] Safety-net turn_runner failed for heard={heard!r}: {e_safety}")

                            if heard:
                                self._log_turn("User", heard)
                            if full_text:
                                self._log_turn("Agent", full_text)

                            t_complete_ms = (
                                round((t_event - self.t_turn_start) * 1000, 2) if self.t_turn_start else None
                            )
                            await self.send_json({
                                "type": "turn_complete",
                                "full_text": full_text,
                                "metrics": {
                                    "ttfb_audio_ms": turn_state["t_first_audio_ms"],
                                    "turn_total_ms": t_complete_ms,
                                    "audio_bytes_total": turn_state["total_audio_bytes"],
                                    "model_used": self.model_name,
                                },
                            })
                            self.t_turn_start = None
                            turn_state["t_first_audio_ms"] = None
                            turn_state["total_audio_bytes"] = 0
                            turn_state["tool_called_in_turn"] = False

                    if not got_any:
                        return "server_closed"
                return "browser_closed"
            finally:
                for t_bg in list(bg_tool_tasks):
                    t_bg.cancel()
                if bg_tool_tasks:
                    await asyncio.gather(*bg_tool_tasks, return_exceptions=True)

        async def guarded() -> str:
            try:
                return await gemini_to_client()
            except Exception as e:
                if " 1000 " in f" {e} " or " 1001 " in f" {e} ":
                    return "server_closed"
                raise

        t1 = asyncio.create_task(client_to_gemini())
        t2 = asyncio.create_task(guarded())
        done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
        for p in pending:
            p.cancel()
        for p in pending:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await p
        return done.pop().result()

    async def _run_fallback_loop(self) -> None:
        """Deterministic fallback loop if Gemini Live is unreachable."""
        from app.turn_runner import get_agent_turn_runner
        trun = get_agent_turn_runner()
        # Tell the browser voice is down so the UI doesn't sit in "connecting" with a dead mic.
        with contextlib.suppress(Exception):
            await self.send_json({
                "type": "connection_status",
                "status": "degraded",
                "session_id": self.session_id,
                "mode": "text_fallback",
            })
            await self.send_json({
                "type": "error",
                "message": "Live voice is unavailable right now. Yukti is running in text mode - please type your question.",
                "retryable": True,
            })
        while self.active:
            msg = await self.inbound.get()
            if msg is _CLOSED:
                return
            if not msg.get("text"):
                continue
            try:
                data = json.loads(msg["text"])
            except json.JSONDecodeError:
                continue
            if data.get("type") not in ("text", "prompt"):
                continue
            text = (data.get("text") or "").strip()
            if not text:
                continue
            await self.send_json({"type": "user_transcript", "text": text, "is_final": True})
            try:
                contract = await trun.execute_turn_async(
                    query=text,
                    session_id=self.session_id,
                    persona=self.persona,
                    principal=self.principal,  # P0.4
                    language=self.language,
                )
            except Exception as exc:  # keep the socket alive; report the failure to the UI
                logger.exception(f"[{self.session_id}] Fallback turn failed: {exc}")
                from app.turn_runner import safe_error_copy  # P0.1 (BUG-33): no exception text to the UI
                await self.send_json({"type": "error", "message": safe_error_copy(exc, self.language), "retryable": True})
                await self.send_json({"type": "turn_complete", "full_text": "", "metrics": {"audio_bytes_total": 0}})
                continue
            clean_c = dict(contract)
            ui_act = clean_c.pop("ui_action", None)
            for k in ("latency_ms", "from_answer_cache", "generated_sql", "tool_called"):
                clean_c.pop(k, None)
            await self.send_json({"type": "contract", "contract": clean_c})
            if ui_act:
                await self.send_json({"type": "ui_action", **ui_act})
            spoken = clean_c.get("spoken_summary") or clean_c.get("display_text") or ""
            await self.send_json({"type": "agent_transcript", "text": spoken, "is_final": True})
            await self.send_json({"type": "turn_complete", "full_text": spoken, "metrics": {"audio_bytes_total": 0}})
