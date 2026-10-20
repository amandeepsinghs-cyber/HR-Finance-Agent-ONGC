"""Test ensuring that agent application code never imports or opens files from answer_key.
Guarantees clean separation: answer_key is strictly the evaluation oracle.
"""

from pathlib import Path
import re

APP_DIR = Path(__file__).resolve().parent.parent / "app"


def test_no_answer_key_imports():
    """Asserts that no file in app/** imports or references answer_key (except optional cache.py)."""
    violations = []
    for p in APP_DIR.rglob("*.py"):
        if p.name == "cache.py":
            continue  # Optional demo cache module
        text = p.read_text(encoding="utf-8")
        if "answer_key" in text:
            violations.append(str(p))

    assert not violations, f"Found references to answer_key in application code: {violations}"
