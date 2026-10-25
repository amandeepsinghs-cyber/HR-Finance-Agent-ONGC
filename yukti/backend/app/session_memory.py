"""Session Memory and Multi-Turn Conversation State Manager for Yukti AI.
Implements UX Spec §4: tracks running thread, visual history, active topic,
entity context ('those officers', 'same for Mumbai', 'there', 'their age'),
active dataset (`last_rows`, `last_columns`, `last_sql`), and visual mode transitions
(replace, refine, compare, restore).
"""

from dataclasses import dataclass, field
import logging
import re
from app.brain.semantic_model import get_semantic_model
import time
from typing import Any, Dict, List, Optional, Tuple

from app.semantic.entities import CODE_RE, get_entities

logger = logging.getLogger("yukti.session_memory")

MAX_SESSION_TURNS = 50
MAX_VISUAL_HISTORY = 20
MAX_SPEC_HISTORY = 20
MAX_COHORTS = 50
MAX_SESSIONS = 200
SESSION_TTL_SECONDS = 3600


def _emp_id_for_persona(persona: str) -> str:
    try:
        from app.auth import PERSONA_DIRECTORY
        return str((PERSONA_DIRECTORY.get(persona) or {}).get("emp_id") or "")
    except Exception:
        return ""


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
    pending_actions: Dict[str, Any] = field(default_factory=dict)
    jobs: List[Dict[str, Any]] = field(default_factory=list)
    last_agent_result: Optional[Dict[str, Any]] = None
    # SPEC-07 §4.6: Session cohort store (C-1 through C-8; bounded LRU <= 50)
    cohorts: List[Dict[str, Any]] = field(default_factory=list)
    active_cohort_id: Optional[str] = None
    principal_emp_id: Optional[str] = None

    def ensure_principal(self, persona: str, emp_id: Optional[str] = None) -> None:
        """C-8: Tag cohorts with `principal.emp_id`; clear cohorts and active dataset when persona/login changes."""
        eff_emp = emp_id if emp_id is not None else _emp_id_for_persona(persona)
        persona_changed = bool(self.persona and persona and self.persona != persona)
        emp_changed = bool(self.principal_emp_id and eff_emp and self.principal_emp_id != eff_emp)
        if persona_changed or emp_changed:
            self.cohorts.clear()
            self.active_cohort_id = None
            self.last_rows.clear()
            self.last_columns.clear()
            self.spec_history.clear()
            self.pending_actions.clear()
            self.jobs.clear()
            self.last_agent_result = None
        if persona:
            self.persona = persona
        if eff_emp:
            self.principal_emp_id = eff_emp

    def get_cohort(self, cohort_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not cohort_id:
            return None
        for c in reversed(self.cohorts):
            if c.get("cohort_id") == cohort_id:
                return c
        return None

    def get_active_cohort(self) -> Optional[Dict[str, Any]]:
        return self.get_cohort(self.active_cohort_id)

    def restore_cohort(self, query: str = "") -> Optional[Dict[str, Any]]:
        """C-2: Re-activates the parent/root cohort (e.g. 'go back to all Delhi staff' -> C0)."""
        if not self.cohorts:
            return None
        q_low = (query or "").lower()
        target: Optional[Dict[str, Any]] = None
        if "all delhi" in q_low or "all staff" in q_low or "c0" in q_low:
            target = self.get_cohort("C0") or self.cohorts[0]
        if target is None:
            active = self.get_active_cohort()
            if active and active.get("parent_cohort_id"):
                target = self.get_cohort(active.get("parent_cohort_id"))
        if target is None and len(self.cohorts) >= 2:
            target = self.cohorts[-2]
        if target is None:
            target = self.cohorts[0]
        self.active_cohort_id = target["cohort_id"]
        if target.get("rows") and target.get("columns"):
            self.last_rows = list(target["rows"])[:2000]
            self.last_columns = list(target["columns"])
        if target.get("spec"):
            self.spec_history.append(dict(target["spec"]))
            if len(self.spec_history) > MAX_SPEC_HISTORY:
                self.spec_history[:] = self.spec_history[-MAX_SPEC_HISTORY:]
        return target

    def _record_cohort(
        self,
        turn_contract: Dict[str, Any],
        all_rows: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """SPEC-07 §4.6 C-1..C-8: Creates or updates the session cohort entry for data turns."""
        # C-3: Visual re-plots or UI commands never change the active cohort
        ui_cmd = (turn_contract.get("ui_action") or {}).get("command")
        if turn_contract.get("replot") or ui_cmd in (
            "set_chart_kind",
            "set_theme",
            "set_language",
            "set_panel_mode",
            "export",
            "navigate_history",
            "go_home",
        ):
            return
        vis = turn_contract.get("visual")
        if not isinstance(vis, dict) or vis.get("type") not in ("chart", "table", "kpi"):
            return
        if vis.get("mode") == "restore":
            return
        acc = turn_contract.get("access") or {}
        if acc.get("status") == "refused":
            return

        tbl = vis.get("table") if isinstance(vis.get("table"), dict) else {}
        cols = list(tbl.get("columns") or [])
        rows = list(
            tbl.get("rows")
            if (isinstance(tbl.get("rows"), list) and tbl.get("rows"))
            else (all_rows or (vis.get("chart") or {}).get("data") or [])
        )[:2000]
        if not cols and rows and isinstance(rows[0], dict):
            cols = list(rows[0].keys())
        if not rows and not vis.get("kpis"):
            return

        qspec = dict(turn_contract.get("query_spec") or {})
        def_id = turn_contract.get("definition_id")
        if not def_id and qspec:
            flts = qspec.get("filters") or []
            has_tenure = any(
                isinstance(f, dict) and f.get("field") in ("station_tenure_years", "delhi_tenure_years")
                for f in flts
            )
            if has_tenure:
                wc_vals = [
                    f.get("value")
                    for f in flts
                    if isinstance(f, dict) and f.get("field") == "wc"
                ]
                def_id = "DELHI_GT5_CONT_V1" if (not wc_vals or wc_vals[0] in ("WC-DEL", ["WC-DEL"])) else "STATION_GT5_CONT_V1"

        kpis = vis.get("kpis") or []
        kpi_val = kpis[0].get("value") if (kpis and isinstance(kpis[0], dict) and isinstance(kpis[0].get("value"), int)) else None
        if qspec.get("grain") == "row":
            row_count = int(tbl.get("total_rows") if tbl.get("total_rows") is not None else len(rows))
        elif kpi_val is not None:
            row_count = int(kpi_val)
        else:
            row_count = int(tbl.get("total_rows") if tbl.get("total_rows") is not None else len(rows))

        mask_lvl = (tbl.get("masking") or {}).get("level") if isinstance(tbl.get("masking"), dict) else None
        rbac_dec = "aggregate" if mask_lvl == "aggregate" else ("allow" if acc.get("status") == "allowed" else str(acc.get("status") or "allow"))
        emp_id = self.principal_emp_id or _emp_id_for_persona(self.persona)

        active = self.get_active_cohort()
        is_all_cadres = any(
            isinstance(f, dict) and f.get("field") == "cadre" and str(f.get("value")).lower() in ("all", "all_cadres")
            for f in (qspec.get("filters") or [])
        )

        # Case 1: T3 row expansion of the active cohort (same definition, aggregate -> row)
        if (
            active is not None
            and def_id is not None
            and active.get("definition_id") == def_id
            and (active.get("spec") or {}).get("grain") == "aggregate"
            and qspec.get("grain") == "row"
        ):
            active["turn_id"] = turn_contract.get("turn_id")
            active["spec"] = qspec
            active["row_count"] = row_count
            active["columns"] = cols
            active["rows"] = rows
            active["rbac_decision"] = rbac_dec
            active["visual"] = dict(vis)
            return

        # Case 2: Determine cohort_id and parent_cohort_id
        if not self.cohorts:
            cid = "C0"
            parent_id = None
        elif active is not None and def_id is not None and active.get("definition_id") == def_id and is_all_cadres:
            cid = f"{active['cohort_id'].rstrip(chr(39))}'"
            parent_id = active.get("parent_cohort_id") or "C0"
        elif active is not None and (vis.get("mode") in ("refine", "compare") or def_id is not None):
            base_idx = sum(1 for c in self.cohorts if not str(c.get("cohort_id", "")).endswith("'"))
            cid = f"C{base_idx}"
            parent_id = "C0" if any(c.get("cohort_id") == "C0" for c in self.cohorts) else active.get("cohort_id")
        else:
            base_idx = sum(1 for c in self.cohorts if not str(c.get("cohort_id", "")).endswith("'"))
            cid = "C0" if base_idx == 0 else f"C{base_idx}"
            parent_id = None

        entry: Dict[str, Any] = {
            "cohort_id": cid,
            "parent_cohort_id": parent_id,
            "turn_id": turn_contract.get("turn_id"),
            "definition_id": def_id,
            "spec": qspec,
            "row_count": row_count,
            "columns": cols,
            "rows": rows,
            "level_rows": list(rows) if "grade" in cols else (list(active.get("level_rows") or []) if active else []),
            "rbac_decision": rbac_dec,
            "as_of": str(tbl.get("as_of") or get_semantic_model().anchor_date),
            "emp_id": emp_id,
            "artifacts": [],
            "visual": dict(vis),
        }
        # Replace in-place if same cohort_id exists, otherwise append
        replaced = False
        for idx, existing in enumerate(self.cohorts):
            if existing.get("cohort_id") == cid:
                entry["artifacts"] = list(existing.get("artifacts") or [])
                self.cohorts[idx] = entry
                replaced = True
                break
        if not replaced:
            self.cohorts.append(entry)
        if len(self.cohorts) > MAX_COHORTS:
            self.cohorts[:] = self.cohorts[-MAX_COHORTS:]
        self.active_cohort_id = cid

    def record_turn(
        self,
        turn_contract: Dict[str, Any],
        user_query: Optional[str] = None,
        all_rows: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Records an emitted turn contract into the session history and updates active dataset/entity state."""
        enriched = dict(turn_contract)
        enriched.pop("all_rows", None)
        if user_query:
            enriched["user_query"] = user_query
            self.last_user_query = user_query
            self._extract_entities_from_text(user_query)

        visual = turn_contract.get("visual")
        if visual and isinstance(visual, dict):
            vis_stored = dict(visual)
            tbl = visual.get("table") or {}
            cols = tbl.get("columns") or []
            rows = all_rows or tbl.get("rows") or (visual.get("chart") or {}).get("data") or []
            if cols and rows:
                self.last_columns = list(cols)
                self.last_rows = list(rows)[:2000]  # rosters up to 2,000 rows (B3.5 transfer note "for them")
            if isinstance(tbl, dict) and isinstance(tbl.get("rows"), list) and len(tbl["rows"]) > 50:
                tbl_stored = dict(tbl)
                tbl_stored["rows"] = tbl["rows"][:50]
                vis_stored["table"] = tbl_stored
            enriched["visual"] = vis_stored
            self.visual_history.append(vis_stored)
            if len(self.visual_history) > MAX_VISUAL_HISTORY:
                self.visual_history[:] = self.visual_history[-MAX_VISUAL_HISTORY:]
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

        self._record_cohort(turn_contract, all_rows=all_rows)

        self.turns.append(enriched)
        if len(self.turns) > MAX_SESSION_TURNS:
            self.turns[:] = self.turns[-MAX_SESSION_TURNS:]
        if len(self.spec_history) > MAX_SPEC_HISTORY:
            self.spec_history[:] = self.spec_history[-MAX_SPEC_HISTORY:]
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
    """Bounded in-memory multi-session registry with LRU + TTL eviction (H1.3b)."""

    def __init__(self, max_sessions: int = MAX_SESSIONS, ttl_seconds: int = SESSION_TTL_SECONDS):
        self.max_sessions = max_sessions
        self.ttl_seconds = ttl_seconds
        self.sessions: Dict[str, SessionState] = {}

    def _evict(self) -> None:
        now = time.time()
        expired = [
            sid for sid, st in list(self.sessions.items())
            if now - st.last_turn_time > self.ttl_seconds
        ]
        for sid in expired:
            self.sessions.pop(sid, None)
        while len(self.sessions) >= self.max_sessions:
            oldest_sid = min(self.sessions, key=lambda k: self.sessions[k].last_turn_time)
            self.sessions.pop(oldest_sid, None)

    def get_or_create(
        self,
        session_id: str,
        persona: Optional[str] = None,
        language: Optional[str] = None,
        emp_id: Optional[str] = None,
    ) -> SessionState:
        if session_id not in self.sessions:
            self._evict()
            eff_persona = persona or "CMD"
            st = SessionState(
                session_id=session_id,
                persona=eff_persona,
                language=language or "en",
                principal_emp_id=emp_id or _emp_id_for_persona(eff_persona),
            )
            self.sessions[session_id] = st
        else:
            st = self.sessions[session_id]
            st.last_turn_time = time.time()
            if persona:
                st.ensure_principal(persona, emp_id=emp_id)
            if language:
                st.language = language
        return self.sessions[session_id]


_GLOBAL_SESSION_MANAGER = SessionManager()


def get_session_manager() -> SessionManager:
    return _GLOBAL_SESSION_MANAGER
