"""Numeric token parser for AR tables (SPEC-01 §4.2 rule 3).

``parse_token(s) -> (value, is_nil, unit_hint)``

* ``"1,325,081"`` -> (1325081.0, False, None)
* ``"(7,720)"``   -> (-7720.0, False, None)   (accounting negative)
* ``"17,988)"``   -> (-17988.0, False, None)  (pdftotext dropped the "(": AR FY24 p.24 OCI FY19)
* ``"-"``         -> (0.0, True, None)        (nil cell)
* ``"1.66 : 1"`` / ``"1.55:1"`` -> (1.66 / 1.55, False, "ratio")
* ``"20.9"``      -> (20.9, False, None)

Raises ``ValueError`` for anything that is not a numeric cell.
"""
from __future__ import annotations

import re

NIL_TOKENS = {"-", "–", "—"}
_RATIO = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*:\s*1\s*$")
_NUM = re.compile(r"^(\()?(-)?(\d{1,3}(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?)(\))?$")
# Used to glue "1.66 : 1" into one whitespace-free token before splitting a line.
RATIO_IN_TEXT = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*:\s*1(?![\d.])")


def is_numeric_token(tok: str) -> bool:
    tok = tok.strip()
    return tok in NIL_TOKENS or bool(_RATIO.match(tok)) or bool(_NUM.match(tok))


def parse_token(s: str) -> tuple[float, bool, str | None]:
    tok = s.strip()
    if tok in NIL_TOKENS:
        return 0.0, True, None
    m = _RATIO.match(tok)
    if m:
        return float(m.group(1)), False, "ratio"
    m = _NUM.match(tok)
    if not m:
        raise ValueError(f"not a numeric token: {s!r}")
    open_p, minus, digits, close_p = m.groups()
    value = float(digits.replace(",", ""))
    if open_p or close_p or minus:
        value = -value
    return value, False, None
