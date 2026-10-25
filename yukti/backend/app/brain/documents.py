"""Data-backed documents from planner results (B3.5 transfer note).

The transfer note lists exactly the selected roster rows. Rows are never trusted from the
client: the selected `emp_id`s are re-fetched from BigQuery with the roster columns, so the
document shows audited values, and RBAC is checked before anything is drafted.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional

from app.brain.compiler import _lit, _q, get_compiler
from app.brain.rbac import decide
from app.brain.semantic_model import get_semantic_model

_TRANSFER_RE = re.compile(r"\btransfer\s+(note|order)s?\b", re.I)  # not "transfer policy" (G4 B3 I-6)
_EMP_ID_RE = re.compile(r"^EMP-\d{3,9}$")


def is_transfer_note_request(query: str) -> bool:
    return bool(_TRANSFER_RE.search(query or ""))


def _roster_sql(emp_ids: List[str], emp_names: Optional[List[str]] = None) -> str:
    s = get_semantic_model().subjects["workforce"]
    cols = ", ".join(f"{rc['expr']} AS {rc['as']}" for rc in s.row_columns)
    if emp_ids:
        cond = f"emp_id IN ({', '.join(_lit(e) for e in emp_ids)})"
    else:
        cond = f"emp_name IN ({', '.join(_lit(n) for n in emp_names or [])})"
    return (f"SELECT {cols} FROM {_q(s.table)} WHERE {s.base_filter} AND {cond} "
            f"ORDER BY continuous_stay_years DESC LIMIT 2000")


def patch_selection(spec_patch: Optional[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Row-action selection sent by the UI as a spec_patch: add_filters emp_id|emp_name in [...] (U5)."""
    out: Dict[str, List[str]] = {"emp_id": [], "emp_name": []}
    for f in (spec_patch or {}).get("add_filters") or []:
        if isinstance(f, dict) and f.get("field") in out and f.get("op") in ("in", "="):
            vals = f.get("value") if isinstance(f.get("value"), list) else [f.get("value")]
            out[f["field"]] += [str(v) for v in vals if isinstance(v, (str, int))]
    out["emp_id"] = [e for e in out["emp_id"] if _EMP_ID_RE.match(e)]
    out["emp_name"] = [n for n in out["emp_name"] if 0 < len(n) <= 80]
    return out


def selected_emp_ids(ui_context: Optional[Dict[str, Any]], session_state: Any,
                     spec_patch: Optional[Dict[str, Any]] = None) -> List[str]:
    """Selected rows from the UI (row action: spec_patch or ui_context) or the whole roster on screen."""
    ids: List[str] = list(dict.fromkeys(patch_selection(spec_patch)["emp_id"]))
    if ids:
        return ids[:2000]
    ctx = ui_context or {}
    for key in ("selected_emp_ids", "selected_rows"):
        for v in ctx.get(key) or []:
            e = v.get("emp_id") if isinstance(v, dict) else v
            if isinstance(e, str) and _EMP_ID_RE.match(e) and e not in ids:
                ids.append(e)
    if not ids:
        for r in getattr(session_state, "last_rows", None) or []:
            e = r.get("emp_id") if isinstance(r, dict) else None
            if isinstance(e, str) and _EMP_ID_RE.match(e) and e not in ids:
                ids.append(e)
    return ids[:2000]


async def roster_ids_from_spec_history(session_state: Any) -> List[str]:
    """No roster on screen: re-run the latest workforce spec at row grain (current snapshot)."""
    from app.brain.query_spec import QuerySpec
    for raw in reversed(getattr(session_state, "spec_history", None) or []):
        if not raw:
            continue
        try:
            spec = QuerySpec.from_contract(raw)
        except Exception:
            return []
        subject, _, _ = get_semantic_model().resolve_metric(spec.metric)
        if subject is None or subject.name != "workforce":
            return []
        data = spec.model_dump(by_alias=True)
        data.update({"grain": "row", "dimensions": [], "period": None, "limit": 2000})
        # a side-by-side comparison selects everyone in the compared work centres
        cq = get_compiler().compile(QuerySpec.model_validate(data))
        res = await get_compiler().execute(cq)
        return [r["emp_id"] for r in res.rows if isinstance(r.get("emp_id"), str)]
    return []


async def transfer_note_contract(query: str, session_state: Any, persona: str, turn_id: str, language: str,
                                 t0: float, ui_context: Optional[Dict[str, Any]] = None,
                                 spec_patch: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Returns a document contract, a refusal contract, or None (no roster to draft from)."""
    from app.tools.draft_document import DocumentDraftingEngine

    decision = decide(persona, ["named"], query)
    names = patch_selection(spec_patch)["emp_name"]
    if names:
        # A name selection is resolved only against the roster on screen (no namesakes, G4 B3 I-6).
        on_screen = {str(r.get("name")): r.get("emp_id") for r in getattr(session_state, "last_rows", None) or []
                     if isinstance(r, dict) and r.get("emp_id")}
        ids_from_names = [on_screen[n] for n in names if n in on_screen]
        names = []
        spec_patch = {"add_filters": [{"field": "emp_id", "op": "in", "value": ids_from_names}]} if ids_from_names else None
    ids = selected_emp_ids(ui_context, session_state, spec_patch) if decision.action == "allow" else ["-"]
    if not ids and not names and decision.action == "allow":
        ids = await roster_ids_from_spec_history(session_state)
    if not ids and not names:
        return None
    if decision.action != "allow":
        reason = "Transfer notes name individual employees, which E1–E4 officers cannot access (D-11)."
        return {
            "turn_id": turn_id, "language": language, "persona": persona,
            "spoken_summary": "I can't draft a named transfer note for your role. I can show aggregate counts by grade or discipline instead.",
            "display_text": reason,
            "visual": {"type": "refusal", "mode": "replace", "title": "Access restricted (named employee data)",
                       "table": {"columns": [], "rows": [], "masking": {"level": "refused", "reason": reason, "rule_ref": "D-11"}}},
            "insights": [reason], "sources": [{"kind": "policy", "title": "D-11 (RBAC policy)"}],
            "suggestions": [], "access": {"status": "refused", "reason": reason, "rule_ref": decision.rule_ref or "D-11"},
            "export_options": [], "status_events": ["RBAC: named data refused for junior persona"],
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2), "contract_version": 2,
        }
    compiler = get_compiler()
    from app.brain.compiler import CompiledQuery
    sql = _roster_sql(ids, names)
    result = await compiler.execute(
        CompiledQuery(
            sql=sql,
            subject="workforce",
            metric="headcount",
            metric_label="Employees",
            unit="employees",
            source="generated",
            tables=["hrfin_gold.ssot_workforce_employee"],
            grain="row",
        )
    )
    rows = result.rows
    if not rows:
        return None
    doc = DocumentDraftingEngine().draft_transfer_note(rows, context={"requested_by": persona})
    n = doc["employee_count"]
    caveat = None
    if len(ids) and ids != ["-"] and n != len(ids):
        caveat = f"{len(ids) - n} of {len(ids)} selected employees were not found among active employees"
    if len(ids) >= 2000:
        caveat = ((caveat + "; ") if caveat else "") + "selection capped at 2,000 employees"
    spoken = (f"I've drafted a transfer note for {n} employee{'s' if n != 1 else ''}, re-checked against the HR master. "
              f"It is on screen for review and export.")
    cols = list(rows[0].keys())
    return {
        "turn_id": turn_id, "language": language, "persona": persona,
        "spoken_summary": spoken, "display_text": spoken,
        "visual": {"type": "document", "mode": "replace", "title": doc["title"],
                   "document": {"doc_type": "transfer_note", "title": doc["title"], "markdown": doc["markdown"],
                                "template_id": doc["template_id"], "version": doc["version"]},
                   "table": {"columns": cols, "rows": rows, "total_rows": len(rows)}},
        "insights": [f"{n} employees listed (selected rows re-fetched by employee id)"],
        "sources": [{"kind": "data", "object": "hrfin_gold.ssot_workforce_employee", "sql": sql},
                    {"kind": "document", "title": doc["template_id"]}],
        "suggestions": [], "access": {"status": "allowed"},
        "export_options": ["word", "pdf", "docs", "xlsx"],
        "status_events": [f"Re-fetched {n} selected employees by emp_id", "Drafted transfer note"],
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2), "contract_version": 2,
        **({"caveat": caveat} if caveat else {}),
    }
