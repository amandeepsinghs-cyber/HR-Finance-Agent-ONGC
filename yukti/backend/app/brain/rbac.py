"""RBAC policy engine (B3.3/B3.4, FEAT-010).

`rbac_policy.yaml` maps persona class x data class -> allow | mask | aggregate | refuse.
- Pre-query: `decide()` looks at the compiled QuerySpec's data classes (metric, roster
  columns) and the question's topic (pay / APAR / vigilance ...) and returns the most
  restrictive action. `to_aggregate()` turns a roster request into counts.
- Post-query: `suppress_small_cells()` hides counts below the threshold for junior personas;
  `enforce_contract()` runs on EVERY contract (planner and legacy paths) and guarantees the
  consistency rule: access.status, the spoken text and the visual agree, and a junior never
  receives named / pay / APAR columns.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import re
from functools import lru_cache
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

import yaml

from app.brain.query_spec import QuerySpec

POLICY_PATH = Path(__file__).resolve().parent / "rbac_policy.yaml"
_ORDER = {"allow": 0, "mask": 1, "aggregate": 2, "refuse": 3}
_COUNT_COL = re.compile(r"(headcount|employees|executives|officers|count|num_|staff|people|personnel)", re.I)


@lru_cache(maxsize=1)
def load_policy() -> Dict[str, Any]:
    return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))


def persona_class(persona: str) -> str:
    for cls, members in load_policy()["persona_classes"].items():
        if persona in members:
            return cls
    return "junior"  # unknown personas get the most restrictive class


def action_for(persona: str, data_class: str) -> str:
    return load_policy()["matrix"][persona_class(persona)].get(data_class, "refuse")


@dataclass
class PolicyDecision:
    action: str
    persona_class: str
    data_classes: List[str] = field(default_factory=list)
    trigger: Optional[str] = None           # data class that decided the action
    rule_ref: Optional[str] = None
    reason: Optional[str] = None


def topic_classes(question: str) -> List[str]:
    """Sensitive topics in the question (word-boundary match; 'apar' never matches 'apart')."""
    q = (question or "").lower()
    out = []
    for cls, words in (load_policy().get("topic_keywords") or {}).items():
        if any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", q) for w in words):
            out.append(cls)
    return out


def decide(persona: str, data_classes: List[str], question: str = "") -> PolicyDecision:
    pc = persona_class(persona)
    classes = sorted(set(data_classes or ["general"]) | (set(topic_classes(question)) if pc == "junior" else set()))
    worst, trigger = "allow", None
    for c in classes:
        a = action_for(persona, c)
        if _ORDER[a] > _ORDER[worst]:
            worst, trigger = a, c
    refs = load_policy().get("rule_refs", {})
    ref = refs.get("D-11") if pc == "junior" and worst != "allow" else (refs.get("D-10") if pc != "junior" else None)
    reason = None
    if worst == "aggregate":
        reason = "Individual names and postings are restricted for E1–E4 officers; showing aggregate counts instead."
    elif worst == "refuse":
        reason = {"pay": "Pay and compensation records", "apar": "APAR ratings and scores",
                  "sensitive": "Vigilance, POSH and medical records"}.get(trigger or "", "These records") + \
            " are confidential for E1–E4 officers."
    return PolicyDecision(action=worst, persona_class=pc, data_classes=classes, trigger=trigger, rule_ref=ref, reason=reason)


def to_aggregate(spec: QuerySpec) -> QuerySpec:
    """Roster -> counts (by grade unless the spec already has a breakdown)."""
    data = spec.model_dump(by_alias=True)
    data["grain"] = "aggregate"
    if not data.get("dimensions"):
        data["dimensions"] = [load_policy().get("aggregate_dimension_default", "grade")]
    return QuerySpec.model_validate(data)


def suppress_small_cells(rows: List[Dict[str, Any]], value_columns: List[str], threshold: Optional[int] = None,
                         by_name: bool = True, cell_count_col: Optional[str] = None,
                         value_check: bool = True) -> Tuple[List[Dict[str, Any]], int]:
    """Counts below the threshold become "<5" (D-11).

    `by_name=False`: `value_columns` are known count columns (from the semantic model), suppressed
    whatever their name. `cell_count_col`: a per-row population count (e.g. `_n`); when it is below
    the threshold every value in the row is suppressed (averages/ratios over < 5 people).
    """
    t = threshold or int(load_policy().get("small_cell_threshold", 5))
    out, n = [], 0
    for r in rows:
        r2 = dict(r)
        small_cell = cell_count_col is not None and isinstance(r2.get(cell_count_col), (int, float)) \
            and 0 < r2[cell_count_col] < t
        for c in value_columns:
            v = r2.get(c)
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                continue
            if small_cell or (value_check and 0 < v < t and (not by_name or _COUNT_COL.search(c))):
                r2[c] = f"<{t}"
                n += 1
        if cell_count_col:
            r2.pop(cell_count_col, None)
        out.append(r2)
    return out, n


def column_class(col: str) -> Optional[str]:
    """Exact column list first, then patterns (legacy SQL aliases like avg_salary, gross_pay, apar)."""
    pol = load_policy()
    for cls, cols in (pol.get("column_classes") or {}).items():
        if col in cols:
            return cls
    for cls, pats in (pol.get("column_patterns") or {}).items():
        if any(re.search(p, col or "", re.I) for p in pats):
            return cls
    return None


def row_actions(persona: str, subject: Optional[str]) -> List[Dict[str, Any]]:
    pc = persona_class(persona)
    if pc == "junior":
        return []
    out = []
    for ra in load_policy().get("row_actions") or []:
        if subject in (ra.get("subjects") or []):
            # min_role is not emitted: under D-10 every leadership/director persona may use the action.
            out.append({k: ra[k] for k in ("id", "label", "action", "question_template") if k in ra})
    return out


def _strip_columns(table: Dict[str, Any], masked: List[str]) -> None:
    cols = table.get("columns") or []
    table["columns"] = [c for c in cols if c not in masked]
    rows = table.get("rows") or []
    new_rows = []
    for r in rows:
        if isinstance(r, dict):
            new_rows.append({k: v for k, v in r.items() if k not in masked})
        elif isinstance(r, list) and cols:
            new_rows.append([v for c, v in zip(cols, r) if c not in masked])
        else:
            new_rows.append(r)
    table["rows"] = new_rows


def enforce_contract(contract: Dict[str, Any], persona: str) -> Dict[str, Any]:
    """Post-query guard on any contract (planner or legacy). Idempotent."""
    c = contract
    pc = persona_class(persona)
    vis = c.get("visual") or {}
    access = c.setdefault("access", {"status": "allowed"})

    # Consistency rule: a refusal never ships a granular visual.
    if access.get("status") == "refused":
        if vis.get("type") not in ("refusal", "none", None):
            vis["type"] = "refusal"
        vis.pop("chart", None)
        vis.pop("compare", None)
        vis.pop("document", None)
        tbl = vis.get("table")
        if isinstance(tbl, dict):
            granular = [col for col in (tbl.get("columns") or []) if column_class(col)]
            if granular:
                _strip_columns(tbl, granular)
            tbl.setdefault("masking", {"level": "refused", "reason": access.get("reason") or "Restricted",
                                       "rule_ref": access.get("rule_ref") or "D-11"})

    if pc != "junior":
        return c

    threshold = int(load_policy().get("small_cell_threshold", 5))
    masked_all: List[str] = []
    masked_values: List[str] = []
    suppressed = 0
    for tbl in [vis.get("table")] + [it for it in ((vis.get("compare") or {}).get("items") or [])]:
        if not isinstance(tbl, dict) or "columns" not in tbl:
            continue
        masked = [col for col in (tbl.get("columns") or []) if column_class(col) in ("named", "pay", "apar", "sensitive")]
        if masked:
            for r in tbl.get("rows") or []:
                if isinstance(r, dict):
                    masked_values += [str(r[m]) for m in masked if isinstance(r.get(m), str) and len(str(r[m])) > 2]
            _strip_columns(tbl, masked)
            masked_all += masked
        if access.get("status") != "refused":
            rows = tbl.get("rows") or []
            if rows and isinstance(rows[0], dict):
                tbl["rows"], n_s = suppress_small_cells(rows, list(rows[0].keys()), threshold)
                suppressed += n_s
    if vis.get("chart") and isinstance(vis["chart"].get("data"), list):
        data = vis["chart"]["data"]
        if data and isinstance(data[0], dict):
            if any(column_class(k) in ("named", "pay", "apar", "sensitive") for k in data[0].keys()):
                vis.pop("chart", None)
                vis["type"] = "table" if vis.get("table") else "none"
            else:
                vis["chart"]["data"], _ = suppress_small_cells(data, list(data[0].keys()), threshold)
    # Personal values must not survive in any text field or document (G4 B3 B-3).
    if masked_all:
        texts = [c.get("spoken_summary") or "", c.get("display_text") or "", c.get("caveat") or ""] + \
            [str(i) for i in c.get("insights") or []] + [str((vis.get("document") or {}).get("markdown") or "")]
        leaked = any(v and v in t for v in set(masked_values) for t in texts)
        if leaked or vis.get("type") == "document":
            safe = ("This answer contains personal details that are restricted for your role (D-11), "
                    "so only the permitted summary is shown.")
            c["spoken_summary"] = safe
            c["display_text"] = safe
            c["insights"] = [safe]
            c.pop("insights_v2", None)
            c.pop("caveat", None)
            if vis.get("type") == "document":
                vis["type"] = "table" if vis.get("table") else "none"
                vis.pop("document", None)
    if suppressed and access.get("status") == "allowed" and not masked_all:
        access["status"] = "partial"
        access["reason"] = f"{suppressed} cell(s) below {threshold} shown as <{threshold} for E1–E4 officers"
        access["rule_ref"] = load_policy().get("rule_refs", {}).get("D-11")
        tbl = vis.get("table")
        if isinstance(tbl, dict):
            tbl.setdefault("masking", {"level": "aggregate", "reason": access["reason"], "rule_ref": "D-11"})
    if masked_all and access.get("status") == "allowed":
        refs = load_policy().get("rule_refs", {})
        access["status"] = "partial"
        access["reason"] = "Personal columns hidden for E1–E4 officers: " + ", ".join(sorted(set(masked_all)))
        access["rule_ref"] = refs.get("D-11")
        tbl = vis.get("table")
        if isinstance(tbl, dict):
            tbl["masking"] = {"level": "partial", "masked_columns": sorted(set(masked_all)),
                              "reason": access["reason"], "rule_ref": "D-11"}
        note = "Some personal details are hidden for your role."
        if note not in (c.get("spoken_summary") or ""):
            c["spoken_summary"] = (c.get("spoken_summary") or "").rstrip() + " " + note
            c["display_text"] = c["spoken_summary"][:590]
    return c
