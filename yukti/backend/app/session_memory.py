"""Session Memory and Multi-Turn Conversation State Manager for Yukti AI.
Implements UX Spec §4: tracks running thread, visual history, active topic,
entity context ('those officers', 'same for Mumbai', 'there', 'their age'),
active dataset (`last_rows`, `last_columns`, `last_sql`), and visual mode transitions
(replace, refine, compare, restore).
"""

from dataclasses import dataclass, field
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from app.semantic.entities import CODE_RE, get_entities

logger = logging.getLogger("yukti.session_memory")


# Work-centre names/aliases come from the single entity dictionary (B1.2).


@dataclass
class SessionState:
    session_id: str
    persona: str = "CMD"
    language: str = "en"
    current_root_id: Optional[str] = None
    turns: List[Dict[str, Any]] = field(default_factory=list)
    visual_history: List[Dict[str, Any]] = field(default_factory=list)
    draft_documents: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    active_entities: Dict[str, Any] = field(default_factory=dict)
    active_query_state: Optional[Dict[str, Any]] = None
    last_rows: List[Dict[str, Any]] = field(default_factory=list)
    last_columns: List[str] = field(default_factory=list)
    last_sql: Optional[str] = None
    last_user_query: Optional[str] = None
    last_turn_time: float = field(default_factory=time.time)
    # B2.5: QuerySpec history (contract-v2 `query_spec` dicts), newest last; follow-ups patch [-1].
    spec_history: List[Dict[str, Any]] = field(default_factory=list)

    def record_turn(
        self,
        turn_contract: Dict[str, Any],
        user_query: Optional[str] = None,
        all_rows: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Records an emitted turn contract into the session history and updates active dataset/entity state."""
        enriched = dict(turn_contract)
        if user_query:
            enriched["user_query"] = user_query
            self.last_user_query = user_query
            self._extract_entities_from_text(user_query)

        visual = turn_contract.get("visual")
        if visual and isinstance(visual, dict):
            self.visual_history.append(visual)
            tbl = visual.get("table") or {}
            cols = tbl.get("columns") or []
            rows = all_rows or tbl.get("rows") or (visual.get("chart") or {}).get("data") or []
            if cols and rows:
                self.last_columns = list(cols)
                self.last_rows = list(rows)[:200]
            title_sub = f"{visual.get('title', '')} {visual.get('subtitle', '')}"
            self._extract_entities_from_text(title_sub)

        sources = turn_contract.get("sources") or []
        for s in sources:
            if s.get("sql"):
                self.last_sql = s["sql"]
                self._extract_entities_from_sql(s["sql"])
                break
        if turn_contract.get("generated_sql"):
            self.last_sql = turn_contract["generated_sql"]
            self._extract_entities_from_sql(self.last_sql)

        self.turns.append(enriched)
        self.last_turn_time = time.time()

    def _extract_entities_from_text(self, text: str) -> None:
        if not text:
            return
        t_low = text.lower()
        ents = get_entities()
        wc_id = ents.resolve_wc(t_low)
        if wc_id:
            wc_label = ents.wc_name(wc_id, short=False)
            self.active_entities["wc_id"] = wc_id
            self.active_entities["wc_name"] = wc_label
            self.active_entities["location"] = wc_label

        for m in CODE_RE.finditer(text):
            code = m.group(1)
            if code in ents.work_centres:
                self.active_entities["wc_id"] = code
                break

        fy_match = re.search(r"\b(FY2[0-9])\b", text, re.IGNORECASE)
        if fy_match:
            self.active_entities["fiscal_year"] = fy_match.group(1).upper()

        if "e5 and above" in t_low or "e5+" in t_low:
            self.active_entities["grade_filter"] = "E5 and above"
        elif "e7 and above" in t_low or "e7+" in t_low:
            self.active_entities["grade_filter"] = "E7 and above"
        elif "non-executive" in t_low or "non executive" in t_low:
            self.active_entities["cadre"] = "non_executive"
        elif "executive" in t_low:
            self.active_entities["cadre"] = "executive"

    def _extract_entities_from_sql(self, sql: str) -> None:
        if not sql:
            return
        m_wc = re.search(r"wc_id\s*=\s*['\"](WC-[A-Z0-9]+(?:-[A-Z0-9]+)?)['\"]", sql, re.IGNORECASE)
        if m_wc:
            self.active_entities["wc_id"] = m_wc.group(1).upper()
        m_fld = re.search(r"field_id\s*=\s*['\"](FLD-[A-Z0-9]+)['\"]", sql, re.IGNORECASE)
        if m_fld:
            self.active_entities["field_id"] = m_fld.group(1).upper()
        m_fy = re.search(r"fiscal_year\s*=\s*['\"](FY\d{2})['\"]", sql, re.IGNORECASE)
        if m_fy:
            self.active_entities["fiscal_year"] = m_fy.group(1).upper()

    def hydrate_from_client_history(
        self,
        history: Optional[List[Dict[str, Any]]] = None,
        ui_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Restores conversational context from the frontend message history if the backend session is empty."""
        if ui_context and isinstance(ui_context, dict):
            if ui_context.get("title"):
                self._extract_entities_from_text(str(ui_context["title"]))
            if ui_context.get("subtitle"):
                self._extract_entities_from_text(str(ui_context["subtitle"]))
            if ui_context.get("columns") and ui_context.get("rows") and not self.last_rows:
                self.last_columns = list(ui_context["columns"])
                self.last_rows = list(ui_context["rows"])[:200]
            if ui_context.get("sql") and not self.last_sql:
                self.last_sql = str(ui_context["sql"])
                self._extract_entities_from_sql(self.last_sql)

        if not history or self.turns:
            return

        # Pair up user/agent messages from client history into synthetic turns
        pending_user = None
        for msg in history[-10:]:
            role = (msg.get("role") or "").lower()
            text = (msg.get("text") or "").strip()
            if not text:
                continue
            self._extract_entities_from_text(text)
            if role == "user":
                pending_user = text
                self.last_user_query = text
            elif role == "agent":
                self.turns.append({
                    "user_query": pending_user or "",
                    "spoken_summary": text,
                    "display_text": text,
                })
                pending_user = None

    def build_conversation_context_prompt(self, current_query: str) -> str:
        """Builds a compact, high-signal multi-turn context block for the ADK LLM."""
        if not self.turns and not self.active_entities and not self.last_sql:
            return ""

        lines: List[str] = ["[CONVERSATION MEMORY & ACTIVE CONTEXT]"]
        if self.active_entities:
            ent_str = ", ".join(f"{k}={v}" for k, v in self.active_entities.items() if v)
            lines.append(f"• Active Entities / Filters in Session: {ent_str}")

        recent_turns = self.turns[-4:]
        if recent_turns:
            lines.append("• Recent Conversation Turns:")
            for idx, t in enumerate(recent_turns, 1):
                uq = t.get("user_query") or "(Prior turn)"
                ans = (t.get("spoken_summary") or t.get("display_text") or "")[:220]
                vis_title = (t.get("visual") or {}).get("title") or ""
                lines.append(f"  Turn -{len(recent_turns) - idx + 1}: User asked: {uq!r} -> Agent answered: {ans!r} (Visual: {vis_title!r})")

        if self.last_sql:
            lines.append(f"• Last Executed BigQuery SQL: `{self.last_sql}`")
        if self.last_columns:
            lines.append(f"• Current Visual Table Columns: {self.last_columns} ({len(self.last_rows)} rows in memory)")

        lines.append(
            "• FOLLOW-UP RESOLUTION RULE: If the user's new question uses pronouns or relative references "
            "('there', 'their', 'those', 'them', 'this work centre', 'same for Mumbai', 'only executives', "
            "'break it down by discipline', 'plot this as a pie chart', 'draw a histogram of their age'), "
            "ALWAYS resolve them using the Active Entities and Last Executed BigQuery SQL above!\n"
        )
        return "\n".join(lines) + "\n"

    def get_last_visual(self) -> Optional[Dict[str, Any]]:
        """Returns the most recent visual from history."""
        return self.visual_history[-1] if self.visual_history else None

    def resolve_visual_mode(
        self,
        entry_id: Optional[str],
        query: str,
        q_type: str = "data"
    ) -> str:
        """Resolves whether visual mode should be replace, refine, compare, or restore per UX Spec §4."""
        q_low = query.lower()

        if any(w in q_low for w in ["go back", "restore", "previous visual", "previous chart", "back to"]):
            return "restore"

        if any(w in q_low for w in ["compare", "versus", "vs", "difference", "comparison"]):
            return "compare"

        if entry_id and "__" in entry_id:
            kind = entry_id.split("__")[1]
            if kind == "drill_down":
                return "refine"
            elif kind == "compare_or_so_what":
                return "compare"
            elif kind == "why":
                return "refine"

        root_id = entry_id.split("__")[0] if entry_id else None
        if root_id and root_id != self.current_root_id:
            return "replace"

        if any(w in q_low for w in ["only", "filter", "breakdown", "discipline", "grade", "just", "pie", "donut", "histogram", "bar", "plot", "chart"]):
            return "refine"

        return "replace"

    def resolve_query_context(self, query: str) -> Tuple[str, Dict[str, Any]]:
        """Resolves anaphoric expressions (e.g. 'those officers', 'same for Mumbai')."""
        self._extract_entities_from_text(query)
        return query, dict(self.active_entities)


class SessionManager:
    """In-memory multi-session registry."""

    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}

    def get_or_create(
        self,
        session_id: str,
        persona: str = "CMD",
        language: str = "en",
    ) -> SessionState:
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionState(
                session_id=session_id,
                persona=persona,
                language=language,
            )
        else:
            if persona:
                self.sessions[session_id].persona = persona
            if language:
                self.sessions[session_id].language = language
        return self.sessions[session_id]


_GLOBAL_SESSION_MANAGER = SessionManager()


def get_session_manager() -> SessionManager:
    return _GLOBAL_SESSION_MANAGER
