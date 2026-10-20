"""
test_v1_harness_no_literals.py — Independent Verifier Self-Test

Verifies that verify/*.py contains NO hard-coded numbers or fake verdicts:
 1. Report lines (e.g. lines.append) contain NO raw numeric story/calibration literals.
 2. Verdict tokens like 'PASS (EXACT)' or 'PASS' in reports must be produced by computed expressions,
    never embedded as raw string constants.
 3. In story_actuals.py, expected values must be loaded from YAML, never hardcoded as numeric literals.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

VERIFY_DIR = Path(__file__).resolve().parent.parent / "verify"


def test_verify_step_no_hardcoded_report_literals():
    """Ensure verify_step.py report generator does not hardcode story numbers or verdicts."""
    verify_step_file = VERIFY_DIR / "verify_step.py"
    assert verify_step_file.exists(), "verify_step.py not found"

    content = verify_step_file.read_text(encoding="utf-8")
    
    # Specific known bad hardcoded literals from V0 verifier
    forbidden_literals = [
        "412", "138", "1929", "260", "6420", "2215", "587",
        "0.00%", "PASS (EXACT)", "PASS (EMERGED)", "1.012 -> 0.789",
    ]

    for line_idx, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        # Only check report generation lines
        if "lines.append" in stripped:
            for bad in forbidden_literals:
                # Disallow raw occurrences in report lines
                assert bad not in stripped, (
                    f"Line {line_idx} in verify_step.py contains forbidden literal '{bad}': {stripped}"
                )


def test_story_actuals_no_numeric_expected_literals():
    """Ensure story_actuals.py does not contain hardcoded expected_value numeric literals."""
    story_actuals_file = VERIFY_DIR / "story_actuals.py"
    assert story_actuals_file.exists(), "story_actuals.py not found"

    content = story_actuals_file.read_text(encoding="utf-8")

    # Look for "expected_value": <number>
    pattern = re.compile(r'["\']expected_value["\']\s*:\s*(\d+(?:\.\d+)?)')
    matches = pattern.findall(content)
    assert not matches, (
        f"story_actuals.py contains hardcoded numeric expected_value literals: {matches}"
    )


def test_no_unconditional_pass_in_reports():
    """Ensure no report lines append a literal 'PASS' without a conditional expression."""
    verify_step_file = VERIFY_DIR / "verify_step.py"
    content = verify_step_file.read_text(encoding="utf-8")

    for line_idx, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if "lines.append" in stripped and ("PASS" in stripped):
            # Must be a format expression or conditional like `if ... else ...`
            # Cannot be a bare string constant like `lines.append("| ... | PASS |")`
            # or `lines.append(f"| ... | **PASS** |")` without variable
            assert ("{" in stripped and "}" in stripped) or ("if" in stripped and "else" in stripped), (
                f"Line {line_idx} has uncomputed PASS in report: {stripped}"
            )
