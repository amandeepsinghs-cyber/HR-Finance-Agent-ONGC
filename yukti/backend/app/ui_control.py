"""Shared UI-control vocabulary and validator for Yukti AI (Voice + Text agents).

Ported directly from Urvi AI Agent (`wellpulse/backend/app/agent/ui_control.py`) and
adapted for ONGC's HR & Finance Command Center ("Yukti AI").

Gives both the Gemini Live voice session (`live_session.py`) and the text/REST
turn runner (`turn_runner.py`) a single, allow-listed `ui_control(action, value)`
tool that drives the front-end screen over WebSocket (`{"type": "ui_action", ...}`
and `{"type": "action", "kind": "ui_control", ...}`).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Single source of truth for what the agent is allowed to do to the Yukti screen.
UI_ACTIONS: Dict[str, Tuple[str, ...]] = {
    "theme": ("light", "dark"),
    "chart_kind": (
        "table", "bar", "hbar", "stacked_bar", "grouped_bar", "pie", "donut",
        "histogram", "line", "area", "combo", "scatter", "waterfall",
        "treemap", "heatmap", "bullet", "gauge", "funnel", "kpi", "map",
    ),
    "open_screen": (
        "home",
        "delhi_tenure",
        "field_profitability",
        "mou_scorecard",
        "lifting_cost",
        "ne_vacancies",
        "brent_what_if",
        "recruitment_freeze",
        "jrtp_policy",
        "board_note",
    ),
    "focus_location": (
        "Delhi",
        "Mumbai",
        "Dehradun",
        "Ahmedabad",
        "Mehsana",
        "Ankleshwar",
        "Cambay",
        "Assam",
        "Jorhat",
        "Tripura",
        "Rajahmundry",
        "Cauvery",
        "ALL",
    ),
    "grade_filter": ("ALL", "E5_PLUS", "E7_PLUS"),
    "breakdown": ("grade", "discipline"),
    "persona": (
        "CMD", "DIR_HR", "DIR_FIN",
        "E1_HR", "E2_HR", "E3_HR", "E4_HR",
        "E1_FIN", "E2_FIN", "E3_FIN", "E4_FIN",
    ),
    "language": ("en", "hi", "hi-en"),
    "panel": ("expand", "dock", "minimise", "close", "open_history"),
    "export": ("pdf", "xlsx", "docx", "sheets", "docs"),
    "history": ("back", "forward"),
}

# Canonical queries triggered when the user says "open <screen>" or focuses a location/filter
SCREEN_CANONICAL_QUERIES: Dict[str, str] = {
    "delhi_tenure": "How many executives have been posted in Delhi for 5 years or more? Break down by grade and discipline.",
    "field_profitability": "Which fields or assets were the most profitable and which made losses in FY26?",
    "mou_scorecard": "How are we tracking against our MoU targets with MoPNG/DPE for this year?",
    "lifting_cost": "Compare lifting cost per BOE across Western Offshore, Gujarat, and Assam for FY26.",
    "ne_vacancies": "What is the current executive vacancy position across North-East sector work centres?",
    "brent_what_if": "What is the impact on ONGC revenue and PAT if Brent crude drops to $60 per barrel?",
    "recruitment_freeze": "Simulate the impact of a 2-year executive recruitment freeze on headcount and retirements.",
    "jrtp_policy": "What are the station tenure norms and transfer rules under the Job Rotation and Transfer Policy (JRTP)?",
    "board_note": "Draft a Board Note on turnaround strategy for loss-making marginal fields in FY26.",
}

# Forgiving synonyms so the LLM (or deterministic parser) doesn't have to hit exact tokens.
_ALIASES: Dict[Tuple[str, str], Tuple[str, str]] = {
    # Legacy command names from control_screen
    ("set_theme", "dark"): ("theme", "dark"),
    ("set_theme", "light"): ("theme", "light"),
    ("set_chart_kind", "table"): ("chart_kind", "table"),
    ("set_chart_kind", "bar"): ("chart_kind", "bar"),
    ("set_chart_kind", "hbar"): ("chart_kind", "hbar"),
    ("set_chart_kind", "stacked_bar"): ("chart_kind", "stacked_bar"),
    ("set_chart_kind", "pie"): ("chart_kind", "pie"),
    ("set_chart_kind", "donut"): ("chart_kind", "donut"),
    ("set_chart_kind", "histogram"): ("chart_kind", "histogram"),
    ("set_chart_kind", "line"): ("chart_kind", "line"),
    ("set_chart_kind", "area"): ("chart_kind", "area"),
    ("set_chart_kind", "combo"): ("chart_kind", "combo"),
    ("set_chart_kind", "scatter"): ("chart_kind", "scatter"),
    ("set_chart_kind", "treemap"): ("chart_kind", "treemap"),
    ("set_chart_kind", "heatmap"): ("chart_kind", "heatmap"),
    ("set_chart_kind", "waterfall"): ("chart_kind", "waterfall"),
    ("set_chart_kind", "bullet"): ("chart_kind", "bullet"),
    ("set_chart_kind", "gauge"): ("chart_kind", "gauge"),
    ("set_chart_kind", "funnel"): ("chart_kind", "funnel"),
    ("set_persona", "cmd"): ("persona", "CMD"),
    ("set_persona", "dir_hr"): ("persona", "DIR_HR"),
    ("set_persona", "dir_fin"): ("persona", "DIR_FIN"),
    ("set_persona", "e1_hr"): ("persona", "E1_HR"),
    ("set_persona", "e2_hr"): ("persona", "E2_HR"),
    ("set_persona", "e3_hr"): ("persona", "E3_HR"),
    ("set_persona", "e4_hr"): ("persona", "E4_HR"),
    ("set_persona", "e1_fin"): ("persona", "E1_FIN"),
    ("set_persona", "e2_fin"): ("persona", "E2_FIN"),
    ("set_persona", "e3_fin"): ("persona", "E3_FIN"),
    ("set_persona", "e4_fin"): ("persona", "E4_FIN"),
    ("set_language", "en"): ("language", "en"),
    ("set_language", "hi"): ("language", "hi"),
    ("set_language", "hi-en"): ("language", "hi-en"),
    ("go_home", ""): ("open_screen", "home"),
    ("go_home", "home"): ("open_screen", "home"),
    ("navigate_history", "back"): ("history", "back"),
    ("navigate_history", "forward"): ("history", "forward"),
    # Theme aliases
    ("theme", "night"): ("theme", "dark"),
    ("theme", "dark_mode"): ("theme", "dark"),
    ("theme", "day"): ("theme", "light"),
    ("theme", "white"): ("theme", "light"),
    ("theme", "light_mode"): ("theme", "light"),
    # Chart kind aliases
    ("chart_kind", "pie_chart"): ("chart_kind", "pie"),
    ("chart_kind", "doughnut"): ("chart_kind", "donut"),
    ("chart_kind", "horizontal_bar"): ("chart_kind", "hbar"),
    ("chart_kind", "ranked_bar"): ("chart_kind", "hbar"),
    ("chart_kind", "grid"): ("chart_kind", "table"),
    # Screen aliases
    ("open_screen", "orb"): ("open_screen", "home"),
    ("open_screen", "greeting"): ("open_screen", "home"),
    ("open_screen", "clear"): ("open_screen", "home"),
    ("open_screen", "tenure"): ("open_screen", "delhi_tenure"),
    ("open_screen", "delhi"): ("open_screen", "delhi_tenure"),
    ("open_screen", "profitability"): ("open_screen", "field_profitability"),
    ("open_screen", "losses"): ("open_screen", "field_profitability"),
    ("open_screen", "loss_fields"): ("open_screen", "field_profitability"),
    ("open_screen", "pnl"): ("open_screen", "field_profitability"),
    ("open_screen", "mou"): ("open_screen", "mou_scorecard"),
    ("open_screen", "scorecard"): ("open_screen", "mou_scorecard"),
    ("open_screen", "lifting"): ("open_screen", "lifting_cost"),
    ("open_screen", "vacancies"): ("open_screen", "ne_vacancies"),
    ("open_screen", "brent"): ("open_screen", "brent_what_if"),
    ("open_screen", "what_if"): ("open_screen", "brent_what_if"),
    ("open_screen", "policy"): ("open_screen", "jrtp_policy"),
    ("open_screen", "jrtp"): ("open_screen", "jrtp_policy"),
    # Panel aliases
    ("panel", "fullscreen"): ("panel", "expand"),
    ("panel", "full_screen"): ("panel", "expand"),
    ("panel", "maximize"): ("panel", "expand"),
    ("panel", "normal"): ("panel", "dock"),
    ("panel", "restore"): ("panel", "dock"),
    ("panel", "minimize"): ("panel", "minimise"),
    ("panel", "hide"): ("panel", "minimise"),
    ("panel", "orb"): ("panel", "minimise"),
    # Persona aliases
    ("persona", "chairman"): ("persona", "CMD"),
    ("persona", "ceo"): ("persona", "CMD"),
    ("persona", "arun"): ("persona", "CMD"),
    ("persona", "director_hr"): ("persona", "DIR_HR"),
    ("persona", "hr_director"): ("persona", "DIR_HR"),
    ("persona", "manish"): ("persona", "DIR_HR"),
    ("persona", "director_finance"): ("persona", "DIR_FIN"),
    ("persona", "finance_director"): ("persona", "DIR_FIN"),
    ("persona", "cfo"): ("persona", "DIR_FIN"),
    ("persona", "anupam"): ("persona", "DIR_FIN"),
    ("persona", "pooja"): ("persona", "E2_HR"),
    ("persona", "lokesh"): ("persona", "E3_HR"),
    ("persona", "umesh"): ("persona", "E4_HR"),
    ("persona", "shailesh"): ("persona", "E3_FIN"),
    ("persona", "asha"): ("persona", "E3_FIN"),
    # Language aliases
    ("language", "english"): ("language", "en"),
    ("language", "hindi"): ("language", "hi"),
    ("language", "hinglish"): ("language", "hi-en"),
}

_LOCATIONS = {loc.lower(): loc for loc in UI_ACTIONS["focus_location"]}


def validate(action: str, value: str = "") -> Tuple[Optional[Dict[str, str]], Optional[str]]:
    """Return `(command, None)` if valid, else `(None, error_message)`."""
    a = (action or "").strip().lower().replace("-", "_").replace(" ", "_")
    v_raw = (value or "").strip()
    v_low = v_raw.lower().replace("-", "_").replace(" ", "_")

    if (a, v_low) in _ALIASES:
        a, v = _ALIASES[(a, v_low)]
    elif (a, v_raw) in _ALIASES:
        a, v = _ALIASES[(a, v_raw)]
    else:
        v = v_raw

    if a not in UI_ACTIONS:
        return None, f"Unknown action '{action}'. Valid actions: {sorted(UI_ACTIONS)}"

    if a == "focus_location":
        if v_raw.upper() in ("ALL", "CLEAR", "NONE", "*"):
            return {"action": "focus_location", "value": "ALL"}, None
        for key_low, canonical in _LOCATIONS.items():
            if key_low in v_raw.lower():
                return {"action": "focus_location", "value": canonical}, None
        return None, f"Unknown ONGC location '{value}'."

    if a == "persona":
        # P0.4 (BUG-06, SPEC-06 §4.4 rule 2): screen-control can never switch the persona. Identity comes from
        # the signed session token; the demo presenter's switch is handled by the turn runner + /api/auth.
        return None, ("R-ROLE: I can't change your access level from a conversation. "
                      "Use 'Sign in as…' in the top bar to start a session as another persona.")

    if a == "grade_filter":
        v_up = v.upper()
        if "7" in v_up:
            return {"action": "grade_filter", "value": "E7_PLUS"}, None
        if "5" in v_up:
            return {"action": "grade_filter", "value": "E5_PLUS"}, None
        return {"action": "grade_filter", "value": "ALL"}, None

    allowed = UI_ACTIONS[a]
    for candidate in (v, v.lower(), v.upper()):
        if candidate in allowed:
            return {"action": a, "value": candidate}, None

    return None, f"Invalid value '{value}' for '{a}'. Allowed: {list(allowed)}"


def to_legacy_ui_action(cmd: Dict[str, str]) -> Dict[str, str]:
    """Maps a canonical `{action, value}` command to `{command, value, action}` so both frontend handlers work."""
    act = cmd["action"]
    val = cmd["value"]
    legacy_map = {
        "theme": ("set_theme", val),
        "chart_kind": ("set_chart_kind", val),
        "persona": ("set_persona", val),
        "language": ("set_language", val),
        "export": ("export", val),
        "history": ("navigate_history", val),
        "panel": ("set_panel_mode", val),
        "open_screen": ("go_home", "") if val == "home" else ("open_screen", val),
        "focus_location": ("focus_location", val),
        "grade_filter": ("grade_filter", val),
        "breakdown": ("breakdown", val),
    }
    legacy_cmd, legacy_val = legacy_map.get(act, (act, val))
    return {
        "action": act,
        "command": legacy_cmd,
        "value": legacy_val,
    }


def detect_ui_control_intent(query: str) -> Optional[Dict[str, str]]:
    """Fast deterministic detector for single-clause voice or text UI commands."""
    q = (query or "").strip().lower().rstrip("?!.")
    if not q:
        return None

    # Do not intercept real analytical questions ("how many", "why", "what is the pat", etc.)
    if re.search(
        r"\b(how many|what is|what are|why|explain|calculate|compare|who is|when did|kitne|kya hai|kyun)\b",
        q,
    ) and not re.search(
        r"^(switch|change|set|show as|view as|open|go|turn on|enable|export|download)\b",
        q,
    ):
        return None

    # 1. Theme
    if any(p in q for p in ["dark mode", "dark theme", "night mode", "turn on dark", "डार्क मोड"]):
        return {"action": "theme", "value": "dark"}
    if any(p in q for p in ["light mode", "light theme", "day mode", "white mode", "turn on light", "लाइट मोड"]):
        return {"action": "theme", "value": "light"}

    # 2. Home / History / Panel
    if q in (
        "go home",
        "home",
        "home screen",
        "clear screen",
        "reset screen",
        "show orb",
        "back to home",
        "back to orb",
        "होम स्क्रीन",
    ):
        return {"action": "open_screen", "value": "home"}
    if q in ("go back", "previous chart", "previous visual", "previous screen", "back", "पीछे जाओ") or re.search(
        r"^(?:go\s+back|back|return|restore)\s+to\s+(?:all\s+|the\s+)?(?:delhi|mumbai|staff|employees|workforce|cohort|level|first|initial)",
        q,
    ):
        return {"action": "history", "value": "back"}
    if q in ("go forward", "next chart", "next screen", "forward"):
        return {"action": "history", "value": "forward"}
    if any(p in q for p in ["full screen", "fullscreen", "expand panel", "maximize chat", "फुल स्क्रीन"]):
        return {"action": "panel", "value": "expand"}
    if any(p in q for p in ["dock panel", "normal view", "exit full screen", "restore panel"]):
        return {"action": "panel", "value": "dock"}
    if any(p in q for p in ["minimise chat", "minimize chat", "hide chat", "close panel", "minimise panel", "collapse chat"]):
        return {"action": "panel", "value": "minimise"}

    # 3. Chart / Visual morphing (ONLY when it is a pure re-plot of current screen data, not a new data query)
    if not re.search(r"\b(excel|xlsx|xls|spreadsheet|csv|pdf|word|docx|export|download)\b", q, re.I):
        from app.tools.chart_rules import is_pure_replot_request
        is_replot, replot_kind = is_pure_replot_request(q)
        if is_replot and replot_kind:
            return {"action": "chart_kind", "value": replot_kind}

    # 4. Export
    if any(p in q for p in ["export to pdf", "download pdf", "export pdf", "save as pdf"]):
        return {"action": "export", "value": "pdf"}
    
    # Load shared patterns from export_intent.json
    try:
        intent_path = Path(__file__).parent.parent.parent / "contracts" / "intents" / "export_intent.json"
        with open(intent_path, encoding="utf-8") as f:
            export_intent_data = json.load(f)
            patterns = export_intent_data.get("patterns", [])
            neg_patterns = export_intent_data.get("negative_guard_patterns", [])
            pos_utterances = export_intent_data.get("positive_utterances", [])
            col_syns = export_intent_data.get("column_synonyms", {})

            has_file_fmt = bool(
                re.search(
                    r"\b(excel|xlsx|xls|spreadsheet|sheets?|workbook|csv|pdf|word|docx|doc|png|svg)\b|(एक्सेल|स्प्रेडशीट|शीट|पीडीएफ|वर्ड|सीएसवी)",
                    q,
                    re.I,
                )
            )
            is_neg = any(re.search(np, q, re.I) for np in neg_patterns) and not has_file_fmt
            is_export = False
            if not is_neg and has_file_fmt:
                is_export = any(re.search(pat, q, re.I) for pat in patterns)
                if not is_export:
                    for pu in pos_utterances:
                        pu_clean = pu.lower().strip("?!. ")
                        if q == pu_clean:
                            is_export = True
                            break

            if is_export:
                # Extract columns based on synonym map in the order mentioned by the user
                matched_with_pos = []
                for canonical, synonyms in col_syns.items():
                    best_pos = None
                    for s_syn in sorted(synonyms, key=len, reverse=True):
                        m_syn = re.search(rf"(?<!\w){re.escape(s_syn.lower())}(?!\w)", q)
                        if m_syn:
                            if best_pos is None or m_syn.start() < best_pos:
                                best_pos = m_syn.start()
                    if best_pos is not None:
                        matched_with_pos.append((best_pos, canonical))
                matched_with_pos.sort(key=lambda x: x[0])
                matched_cols = [c for _, c in matched_with_pos]
                fmt = "pdf" if re.search(r"\bpdf\b|पीडीएफ", q, re.I) else "xlsx"
                return {"action": "export", "value": fmt, "columns": ",".join(matched_cols)}
    except Exception as e:
        import logging
        logging.warning(f"Failed to load export_intent.json: {e}")
        
    if any(p in q for p in ["export to excel", "export to sheets", "download excel", "export xlsx"]):
        return {"action": "export", "value": "xlsx"}

    # 5. Persona & Language
    if any(p in q for p in ["switch role to director hr", "act as director hr", "persona director hr"]):
        return {"action": "persona", "value": "DIR_HR"}
    if any(p in q for p in ["switch role to director finance", "act as director finance", "persona director finance"]):
        return {"action": "persona", "value": "DIR_FIN"}
    if any(p in q for p in ["switch role to cmd", "act as cmd", "act as chairman", "persona cmd"]):
        return {"action": "persona", "value": "CMD"}
    if q in ("speak in hindi", "switch to hindi", "hindi mode", "हिंदी में बोलो", "हिंदी"):
        return {"action": "language", "value": "hi"}
    if q in ("speak in english", "switch to english", "english mode"):
        return {"action": "language", "value": "en"}
    if q in ("speak in hinglish", "switch to hinglish", "hinglish mode"):
        return {"action": "language", "value": "hi-en"}

    # 6. Open named screen directly by voice ("open field profitability", "open mou scorecard", "open delhi tenure")
    if re.search(r"\b(open|show|go to|load)\b.*\b(field profitability|loss making fields)\b", q):
        return {"action": "open_screen", "value": "field_profitability"}
    if re.search(r"\b(open|show|go to|load)\b.*\b(mou|mou scorecard|dpe target)\b", q):
        return {"action": "open_screen", "value": "mou_scorecard"}
    if re.search(r"\b(open|show|go to|load)\b.*\b(delhi tenure|delhi station|station tenure)\b", q):
        return {"action": "open_screen", "value": "delhi_tenure"}
    if re.search(r"\b(open|show|go to|load)\b.*\b(lifting cost)\b", q):
        return {"action": "open_screen", "value": "lifting_cost"}
    if re.search(r"\b(open|show|go to|load)\b.*\b(north east vacanc|ne vacanc)\b", q):
        return {"action": "open_screen", "value": "ne_vacancies"}
    if re.search(r"\b(open|show|go to|load)\b.*\b(brent|oil price shock)\b", q):
        return {"action": "open_screen", "value": "brent_what_if"}
    if re.search(r"\b(open|show|go to|load)\b.*\b(jrtp|transfer policy)\b", q):
        return {"action": "open_screen", "value": "jrtp_policy"}

    return None


def run(action: str, value: str = "", columns: str = "") -> Dict[str, Any]:
    """Validate and package a UI command for the frontend."""
    cmd, err = validate(action, value)
    if err:
        return {"status": "ERROR", "summary": err, "data": {"allowed": {k: list(v) for k, v in UI_ACTIONS.items()}}}
    assert cmd is not None
    return {
        "status": "OK",
        "summary": f"UI updated: {cmd['action']} → {cmd['value']}.",
        "data": {"command": cmd, "ui_action": to_legacy_ui_action(cmd)},
    }
