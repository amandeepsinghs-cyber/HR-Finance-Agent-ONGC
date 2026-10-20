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
