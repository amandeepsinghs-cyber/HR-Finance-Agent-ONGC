"""Session Memory and Multi-Turn Conversation State Manager for Yukti AI.
Implements UX Spec §4: tracks running thread, visual history, active topic,
entity context ('those officers', 'same for Mumbai'), and visual mode transitions
(replace, refine, compare, restore).
"""

from dataclasses import dataclass, field
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("yukti.session_memory")


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
    last_turn_time: float = field(default_factory=time.time)

    def record_turn(self, turn_contract: Dict[str, Any]) -> None:
        """Records an emitted turn contract into the session history."""
        self.turns.append(turn_contract)
        visual = turn_contract.get("visual")
        if visual and isinstance(visual, dict):
            self.visual_history.append(visual)
        self.last_turn_time = time.time()

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

        # 1. Restore mode
        if any(w in q_low for w in ["go back", "restore", "previous visual", "previous chart", "back to"]):
            return "restore"

        # 2. Compare mode
        if any(w in q_low for w in ["compare", "versus", "vs", "difference", "comparison"]):
            return "compare"

        # If it's a known follow-up ID
        if entry_id and "__" in entry_id:
            kind = entry_id.split("__")[1]
            if kind == "drill_down":
                return "refine"
            elif kind == "compare_or_so_what":
                return "compare"
            elif kind == "why":
                return "refine"

        # If it's a new root topic
        root_id = entry_id.split("__")[0] if entry_id else None
        if root_id and root_id != self.current_root_id:
            return "replace"

        # Filter refinements in place (e.g. 'only E5 and above', 'show by discipline')
        if any(w in q_low for w in ["only", "filter", "breakdown", "discipline", "grade", "just"]):
            return "refine"

        return "replace"

    def resolve_query_context(self, query: str) -> Tuple[str, Dict[str, Any]]:
        """Resolves anaphoric expressions (e.g. 'those officers', 'same for Mumbai')."""
        q_low = query.lower()
        extracted = dict(self.active_entities)

        if "delhi" in q_low:
            extracted["location"] = "Delhi"
            extracted["wc_id"] = "WC-DEL"
        elif "mumbai" in q_low:
            extracted["location"] = "Mumbai"
            extracted["wc_id"] = "WC-MUM"
        elif "dehradun" in q_low:
            extracted["location"] = "Dehradun"
            extracted["wc_id"] = "WC-DDN"
        elif "assam" in q_low:
            extracted["location"] = "Assam"
            extracted["wc_id"] = "WC-ASM"

        if "e5 and above" in q_low or "e5+" in q_low:
            extracted["grade_filter"] = "E5 and above"

        # Save back updated active entities
        self.active_entities.update(extracted)
        return query, extracted


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
            # Update persona/language if explicitly passed
            if persona:
                self.sessions[session_id].persona = persona
            if language:
                self.sessions[session_id].language = language
        return self.sessions[session_id]


_GLOBAL_SESSION_MANAGER = SessionManager()


def get_session_manager() -> SessionManager:
    return _GLOBAL_SESSION_MANAGER
