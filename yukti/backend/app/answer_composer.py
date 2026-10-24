"""Answer Composer & Validator for Yukti AI.
Provides contract validation against answer_contract.schema.json,
SPEC-06 §4.6 bilingual refusal copy rendering (from `refusal_copy.yaml`),
11-persona display strings (from `app_users.yaml`),
language code-switching detection, and Indian number system formatting.
"""

from __future__ import annotations

from functools import lru_cache
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import jsonschema
import yaml

from app.config import CONTRACT_SCHEMA_PATH

logger = logging.getLogger("yukti.answer_composer")

_CONTRACT_VALIDATOR: Optional[jsonschema.Draft202012Validator] = None

APP_USERS_YAML_PATH = Path(__file__).resolve().parent / "brain" / "app_users.yaml"
REFUSAL_COPY_YAML_PATH = Path(__file__).resolve().parent / "brain" / "refusal_copy.yaml"

REFUSAL_CODES_9: tuple[str, ...] = (
    "R-NAMED",
    "R-PAY",
    "R-APAR",
    "R-SENS",
    "R-FUNC",
    "R-BOARD",
    "R-ROLE",
    "R-K5",
    "E-AUTH",
)


def get_contract_validator() -> jsonschema.Draft202012Validator:
    global _CONTRACT_VALIDATOR
    if _CONTRACT_VALIDATOR is None:
        if CONTRACT_SCHEMA_PATH.exists():
            schema_data = json.loads(CONTRACT_SCHEMA_PATH.read_text(encoding="utf-8"))
            _CONTRACT_VALIDATOR = jsonschema.Draft202012Validator(schema_data)
        else:
            raise FileNotFoundError(f"Contract schema not found at {CONTRACT_SCHEMA_PATH}")
    return _CONTRACT_VALIDATOR


@lru_cache(maxsize=1)
def _load_app_users_display() -> Dict[str, Dict[str, Any]]:
    if APP_USERS_YAML_PATH.exists():
        raw = yaml.safe_load(APP_USERS_YAML_PATH.read_text(encoding="utf-8")) or {}
        personas = raw.get("personas") or {}
        if personas:
            out: Dict[str, Dict[str, Any]] = {}
            for pid, info in personas.items():
                desig = info.get("functional_designation") or info.get("designation") or pid
                disp_name = info.get("display_name") or pid
                out[pid] = {
                    "persona_id": pid,
                    "emp_id": info.get("emp_id", ""),
                    "display_name": disp_name,
                    "designation": desig,
                    "functional_designation": desig,
                    "grade": info.get("grade", ""),
                    "function": info.get("function", ""),
                    "wc_id": info.get("wc_id", "WC-DEL"),
                    "work_centre": info.get("work_centre", "Delhi HQ"),
                    "display_string": f"{disp_name}, {desig}",
                }
            return out
    return {}


# P2H.2: 11 persona display strings loaded from app_users.yaml
PERSONA_DISPLAY: Dict[str, Dict[str, Any]] = _load_app_users_display()
PERSONA_DISPLAY_STRINGS: Dict[str, str] = {
    pid: meta["display_string"] for pid, meta in PERSONA_DISPLAY.items()
}

_VALID_LANGUAGES = {"en", "hi", "hi-en"}
_VALID_PERSONAS = set(PERSONA_DISPLAY.keys()) or {
    "CMD",
    "DIR_HR",
    "DIR_FIN",
    "E1_HR",
    "E2_HR",
    "E3_HR",
    "E4_HR",
    "E1_FIN",
    "E2_FIN",
    "E3_FIN",
    "E4_FIN",
}
_VALID_VISUAL_TYPES = {"kpi", "chart", "table", "clause", "document", "email_draft", "map", "refusal", "none"}
_VALID_VISUAL_MODES = {"replace", "refine", "compare", "restore"}


@lru_cache(maxsize=1)
def load_refusal_copy() -> Dict[str, Dict[str, Any]]:
    """Load the 9 refusal codes and EN/HI templates from `app/brain/refusal_copy.yaml`."""
    if not REFUSAL_COPY_YAML_PATH.exists():
        raise FileNotFoundError(f"Missing refusal copy YAML at {REFUSAL_COPY_YAML_PATH}")
    data = yaml.safe_load(REFUSAL_COPY_YAML_PATH.read_text(encoding="utf-8")) or {}
    return data.get("codes") or {}


def persona_display_info(persona: Optional[str]) -> Dict[str, Any]:
    """Return `{display_name, designation, functional_designation, grade, function, wc_id, display_string}` for `persona`.

    Uses a neutral fallback (never a seeded person's name like Pooja Verma) when `persona` is unknown or omitted.
    """
    from app.access_control import UnknownPersona, normalize_persona

    try:
        canon = normalize_persona(persona)
    except UnknownPersona:
        return {
            "persona_id": str(persona or "UNKNOWN").strip().upper() or "UNKNOWN",
            "emp_id": "",
            "display_name": "Signed-in User",
            "designation": "Current Role",
            "functional_designation": "Current Role",
            "grade": "E2",
            "function": "HR",
            "wc_id": "WC-DEL",
            "work_centre": "Delhi HQ",
            "display_string": "Signed-in User, Current Role",
        }
    return dict(PERSONA_DISPLAY[canon])


def render_refusal_copy(
    code: str,
    lang: str = "en",
    persona: Optional[str] = None,
    *,
    grade_num: Optional[str] = None,
    display_name: Optional[str] = None,
    designation: Optional[str] = None,
) -> Dict[str, Any]:
    """Render SPEC-06 §4.6 copy + alternative for `(code, lang, persona)`.

    Note on R-PAY `{n}`: defaults to the requester's grade (`p_info["grade"]`) so a refusal never
    discloses a restricted target employee's grade; callers may pass `grade_num` explicitly when
    the target grade was already in the user's question.

    Returns:
        `{code, text, rule_ref, auto_answer, alternative, alternatives}` where `alternative` is
        `{"label": ..., "question": ...}` (or `None` for `E-AUTH`) and `alternatives` contains
        only non-duplicate additional chips with `label_hi` and `question_hi` populated.
    """
    codes = load_refusal_copy()
    norm_code = (code or "R-NAMED").strip().upper()
    if norm_code not in codes:
        norm_code = "R-NAMED"
    entry = codes[norm_code]

    p_info = persona_display_info(persona)
    disp = display_name or p_info["display_name"]
    desig = designation or p_info["designation"]
    raw_grade = str(p_info.get("grade") or "E2")
    m_g = re.search(r"([1-9])", str(grade_num or raw_grade))
    n_val = m_g.group(1) if m_g else "2"

    is_hi = str(lang or "en").strip().lower() == "hi"
    lang_key = "hi" if is_hi else "en"
    tpl = str(entry.get(lang_key) or entry.get("en") or "")
    text = tpl.format(display_name=disp, designation=desig, n=n_val, grade_num=n_val)

    raw_alt = entry.get("alternative")
    alt_out: Optional[Dict[str, str]] = None
    if isinstance(raw_alt, dict):
        lbl_tpl = raw_alt.get("label_hi" if is_hi and raw_alt.get("label_hi") else "label") or ""
        q_tpl = raw_alt.get("question_hi" if is_hi and raw_alt.get("question_hi") else "question") or ""
        alt_out = {
            "label": lbl_tpl.format(display_name=disp, designation=desig, n=n_val, grade_num=n_val),
            "question": q_tpl.format(display_name=disp, designation=desig, n=n_val, grade_num=n_val),
        }

    alts_out: List[Dict[str, str]] = []
    seen_labels = {(alt_out["label"].strip().lower()) for _ in [1] if alt_out}
    seen_questions = {(alt_out["question"].strip().lower()) for _ in [1] if alt_out}
    for item in entry.get("alternatives") or []:
        if isinstance(item, dict):
            lbl_en = (item.get("label") or "").format(display_name=disp, designation=desig, n=n_val, grade_num=n_val)
            lbl_hi = (item.get("label_hi") or lbl_en).format(display_name=disp, designation=desig, n=n_val, grade_num=n_val)
            q_en = (item.get("question") or "").format(display_name=disp, designation=desig, n=n_val, grade_num=n_val)
            q_hi = (item.get("question_hi") or q_en).format(display_name=disp, designation=desig, n=n_val, grade_num=n_val)
            lbl_cur = lbl_hi if is_hi else lbl_en
            q_cur = q_hi if is_hi else q_en
            if lbl_cur.strip().lower() in seen_labels or q_cur.strip().lower() in seen_questions:
                continue
            seen_labels.add(lbl_cur.strip().lower())
            seen_questions.add(q_cur.strip().lower())
            alts_out.append(
                {
                    "label": lbl_cur,
                    "question": q_cur,
                    "label_hi": lbl_hi,
                    "question_hi": q_hi,
                }
            )

    return {
        "code": norm_code,
        "text": text,
        "rule_ref": str(entry.get("rule_ref") or "D-11"),
        "auto_answer": bool(entry.get("auto_answer", False)),
        "alternative": alt_out,
        "alternatives": alts_out,
    }


def build_refusal_contract(
    code: str,
    persona: str,
    turn_id: str,
    language: str = "en",
    *,
    rule_ref: Optional[str] = None,
    grade_num: Optional[str] = None,
    display_name: Optional[str] = None,
    designation: Optional[str] = None,
    auto_answer_visual: Optional[Dict[str, Any]] = None,
    auto_answer_turn_id: Optional[str] = None,
    query_spec: Optional[Dict[str, Any]] = None,
    latency_ms: float = 0.0,
) -> Dict[str, Any]:
    """Build a SPEC-06 §4.6 / P2H.2 refusal (or auto-answer aggregate) contract."""
    rendered = render_refusal_copy(
        code=code,
        lang=language,
        persona=persona,
        grade_num=grade_num,
        display_name=display_name,
        designation=designation,
    )
    eff_rule_ref = rule_ref or rendered["rule_ref"]
    headline = rendered["text"]
    alt = rendered["alternative"]
    alts = rendered["alternatives"]

    if auto_answer_visual is not None and rendered["auto_answer"]:
        vis = dict(auto_answer_visual)
        tbl = vis.get("table")
        if isinstance(tbl, dict):
            tbl.setdefault(
                "masking",
                {
                    "level": "aggregate",
                    "code": rendered["code"],
                    "reason": headline,
                    "rule_ref": eff_rule_ref,
                },
            )
        access_status = "partial"
    else:
        vis = {
            "type": "refusal",
            "mode": "replace",
            "title": "Access restricted",
            "code": rendered["code"],
            "rule_ref": eff_rule_ref,
            "alternative": alt,
            "alternatives": alts,
            "auto_answer_turn_id": auto_answer_turn_id,
            "table": {
                "columns": [],
                "rows": [],
                "masking": {
                    "level": "refused",
                    "code": rendered["code"],
                    "reason": headline,
                    "rule_ref": eff_rule_ref,
                },
            },
        }
        access_status = "refused"

    suggestions = []
    if access_status != "refused":
        if alt:
            suggestions.append(alt["question"])
        for a in alts:
            if a["question"] not in suggestions:
                suggestions.append(a["question"])
        suggestions = suggestions[:3]
    contract: Dict[str, Any] = {
        "turn_id": turn_id,
        "language": language if language in _VALID_LANGUAGES else "en",
        "persona": persona,
        "spoken_summary": headline,
        "display_text": headline[:600],
        "visual": vis,
        "insights": [headline],
        "sources": [{"kind": "policy", "title": eff_rule_ref}],
        "suggestions": suggestions,
        "access": {
            "status": access_status,
            "code": rendered["code"],
            "reason": headline,
            "rule_ref": eff_rule_ref,
            "alternative": alt,
            "alternatives": alts,
        },
        "export_options": ["pdf", "xlsx"] if auto_answer_visual is not None else ["pdf"],
        "status_events": [f"RBAC: {rendered['code']} ({eff_rule_ref})"],
        "latency_ms": round(latency_ms, 2),
        "contract_version": 2,
    }
    if query_spec is not None:
        contract["query_spec"] = query_spec
    return contract


def _infer_refusal_code(access: Dict[str, Any]) -> str:
    if access.get("code") in REFUSAL_CODES_9:
        return str(access["code"])
    rr = str(access.get("rule_ref") or "").upper()
    reason = str(access.get("reason") or "").lower()
    if "R-ROLE" in rr or re.search(r"\b(access\s+level|change\s+your\s+role)\b", reason):
        return "R-ROLE"
    if "R-BOARD" in rr or "P20" in rr or re.search(r"\b(board\s+agenda|board\s+note|board\s+memoranda|divestment)\b", reason):
        return "R-BOARD"
    if "R-SENS" in rr or "R-POSH" in rr or "R-MED" in rr or re.search(r"\b(posh|vigilance|medical|harassment)\b", reason):
        return "R-SENS"
    if "R-APAR" in rr or "D3" in rr or re.search(r"\b(apar|appraisal|promotion\s+committee|dpc)\b", reason):
        return "R-APAR"
    if "R-PAY" in rr or "D1" in rr or re.search(r"\b(pay|salary|compensation|allowances|ctc|payslip)\b", reason):
        return "R-PAY"
    if "R-K5" in rr or re.search(r"\b(below\s+5|too\s+small|under\s+5)\b", reason):
        return "R-K5"
    if "R-FUNC" in rr or "D-43" in rr or re.search(r"\b(finance\s+team|cross-functional|field-level\s+profitability|delegated\s+powers|bdp)\b", reason):
        return "R-FUNC"
    return "R-NAMED"


def validate_and_repair_contract(contract: Dict[str, Any]) -> Dict[str, Any]:
    """Validates an Answer Contract against answer_contract.schema.json, repairing common
    drift (e.g. language='en-IN' -> 'en', missing defaults, overlong strings) so schema
    validation never crashes a turn with an unhandled HTTP 500 (H1.3b / Audit 2.14).
    """
    # Normalize language (e.g., 'en-IN', 'en-US' -> 'en'; 'hi-IN' -> 'hi')
    lang = str(contract.get("language") or "en").strip().lower()
    if lang not in _VALID_LANGUAGES:
        if lang.startswith("hi") and "en" in lang:
            contract["language"] = "hi-en"
        elif lang.startswith("hi"):
            contract["language"] = "hi"
        else:
            contract["language"] = "en"

    # Normalize persona across all 11 canonical personas
    persona = str(contract.get("persona") or "CMD").strip().upper()
    if persona not in _VALID_PERSONAS:
        from app.access_control import UnknownPersona, normalize_persona
        try:
            contract["persona"] = normalize_persona(persona)
        except UnknownPersona:  # P0.4: repair only; the turn runner re-stamps the principal's persona
            contract["persona"] = "E2_HR"

    # Ensure required string fields
    if not contract.get("turn_id") or not isinstance(contract.get("turn_id"), str):
        contract["turn_id"] = "turn-repaired-001"
    spoken = str(contract.get("spoken_summary") or "Details are on screen.").strip()
    contract["spoken_summary"] = spoken or "Details are on screen."
    display = str(contract.get("display_text") or contract["spoken_summary"]).strip()
    contract["display_text"] = (display or contract["spoken_summary"])[:600]

    # Ensure visual structure
    vis = contract.get("visual")
    if not isinstance(vis, dict):
        vis = {"type": "none", "mode": "replace"}
        contract["visual"] = vis
    if vis.get("type") not in _VALID_VISUAL_TYPES:
        vis["type"] = "none"
    if vis.get("mode") not in _VALID_VISUAL_MODES:
        vis["mode"] = "replace"

    # Ensure required arrays & objects
    if not isinstance(contract.get("insights"), list):
        contract["insights"] = []
    if not isinstance(contract.get("sources"), list):
        contract["sources"] = []
    if not isinstance(contract.get("suggestions"), list):
        contract["suggestions"] = []
    if not isinstance(contract.get("export_options"), list):
        contract["export_options"] = ["pdf"]
    if not isinstance(contract.get("status_events"), list):
        contract["status_events"] = ["Completed"]
    if not isinstance(contract.get("access"), dict) or contract["access"].get("status") not in ("allowed", "refused", "partial"):
        contract["access"] = {"status": "allowed"}

    # P2H.2 (M1): ensure every refusal carries SPEC-06 copy, access.code, access.rule_ref, and non-duplicate alternatives
    access = contract["access"]
    if access.get("status") == "refused":
        code = _infer_refusal_code(access)
        rendered = render_refusal_copy(code, lang=contract.get("language", "en"), persona=contract.get("persona"))
        access["code"] = code
        access.setdefault("rule_ref", rendered["rule_ref"])
        access["reason"] = rendered["text"]
        if not isinstance(access.get("alternative"), dict) and rendered["alternative"] is not None:
            access["alternative"] = rendered["alternative"]
        access["alternatives"] = rendered["alternatives"]
        
        # Overwrite refusal headlines / titles that leak rule IDs (BEH-01.60) or miss standard translation
        contract["spoken_summary"] = rendered["text"]
        contract["display_text"] = rendered["text"][:600]
        contract["suggestions"] = []
        
        if isinstance(vis, dict):
            vis["type"] = "refusal"
            if re.search(r"\([A-Z]\d+\)|Access\s+Restricted\s*\(", str(vis.get("title") or "")):
                vis["title"] = "Access restricted"
            elif not vis.get("title") or vis.get("type") == "none":
                vis["title"] = "Access restricted"
            vis.setdefault("code", code)
            vis.setdefault("rule_ref", rendered["rule_ref"])
            vis.setdefault("alternative", rendered["alternative"])
            vis.setdefault("alternatives", rendered["alternatives"])
            vis.setdefault("rule_ref", access["rule_ref"])
            vis["alternative"] = access.get("alternative")
            vis["alternatives"] = access.get("alternatives", [])

    validator = get_contract_validator()
    try:
        validator.validate(contract)
        return contract
    except jsonschema.ValidationError as first_err:
        logger.warning(f"Contract validation warning (repairing): {first_err.message}")
        for opt_key in ("insights_v2", "drilldowns", "context_chips", "query_spec"):
            if opt_key in list(first_err.absolute_path):
                contract.pop(opt_key, None)
    return contract


def detect_language(text: str, default: str = "en") -> str:
    """Detects whether user query is English (en), Hindi (hi), or Hinglish (hi-en)."""
    if not text:
        return default
    # 1. Check for Devanagari script
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    # 2. Check for common Romanized Hindi / Hinglish keywords
    hinglish_terms = {
        "mein", "me", "kitne", "kitna", "kahan", "kaun", "kaise", "hoga",
        "batao", "saal", "zyada", "pichle", "zara", "dikhana", "bhi", "hai",
        "hain", "aur", "se", "ko", "par", "karein", "kya", "hum"
    }
    tokens = set(re.findall(r"\b[a-zA-Z]+\b", text.lower()))
    if len(tokens & hinglish_terms) >= 2:
        return "hi-en"
    return default


def format_indian_number(val: Any) -> str:
    """Formats numeric values into Indian numbering system (Lakh, Crore)."""
    try:
        n = float(val)
    except (ValueError, TypeError):
        return str(val)

    if abs(n) >= 10_000_000:
        cr = n / 10_000_000
        return f"{cr:.2f} Crore".rstrip("0").rstrip(".")
    elif abs(n) >= 100_000:
        lakh = n / 100_000
        return f"{lakh:.2f} Lakh".rstrip("0").rstrip(".")
    elif n.is_integer():
        return f"{int(n):,}"
    else:
        return f"{n:.2f}"
