"""Answer Composer & Validator for Yukti AI.
Provides contract validation against answer_contract.schema.json,
language code-switching detection, and Indian number system formatting.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
import jsonschema

from app.config import CONTRACT_SCHEMA_PATH

logger = logging.getLogger("yukti.answer_composer")

_CONTRACT_VALIDATOR: Optional[jsonschema.Draft202012Validator] = None


def get_contract_validator() -> jsonschema.Draft202012Validator:
    global _CONTRACT_VALIDATOR
    if _CONTRACT_VALIDATOR is None:
        if CONTRACT_SCHEMA_PATH.exists():
            schema_data = json.loads(CONTRACT_SCHEMA_PATH.read_text(encoding="utf-8"))
            _CONTRACT_VALIDATOR = jsonschema.Draft202012Validator(schema_data)
        else:
            raise FileNotFoundError(f"Contract schema not found at {CONTRACT_SCHEMA_PATH}")
    return _CONTRACT_VALIDATOR


_VALID_LANGUAGES = {"en", "hi", "hi-en"}
_VALID_PERSONAS = {
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
_VALID_VISUAL_TYPES = {
    "kpi",
    "chart",
    "table",
    "statement",
    "sensitivity_grid",
    "tornado",
    "dcf_model",
    "actions",
    "clause",
    "document",
    "email_draft",
    "map",
    "refusal",
    "none",
}
_VALID_VISUAL_MODES = {"replace", "refine", "compare", "restore"}


def validate_and_repair_contract(contract: Dict[str, Any]) -> Dict[str, Any]:
    """Validates an Answer Contract against answer_contract.schema.json, repairing common
    drift (e.g. language='en-IN' -> 'en', missing defaults, overlong strings) so schema
    validation never crashes a turn with an unhandled HTTP 500 (H1.3b / Audit 2.14).
    """
    validator = get_contract_validator()
    try:
        validator.validate(contract)
        return contract
    except jsonschema.ValidationError as first_err:
        logger.warning(f"Contract validation warning (repairing): {first_err.message}")

    # Normalize language (e.g., 'en-IN', 'en-US' -> 'en'; 'hi-IN' -> 'hi')
    lang = str(contract.get("language") or "en").strip().lower()
    if lang not in _VALID_LANGUAGES:
        if lang.startswith("hi") and "en" in lang:
            contract["language"] = "hi-en"
        elif lang.startswith("hi"):
            contract["language"] = "hi"
        else:
            contract["language"] = "en"

    # Normalize persona
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

    try:
        validator.validate(contract)
    except jsonschema.ValidationError as second_err:
        logger.error(f"Contract validation still had issue after repair ({second_err.message}); stripping optional v2 fields if invalid.")
        for opt_key in ("insights_v2", "drilldowns", "context_chips", "query_spec"):
            if opt_key in list(second_err.absolute_path):
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
