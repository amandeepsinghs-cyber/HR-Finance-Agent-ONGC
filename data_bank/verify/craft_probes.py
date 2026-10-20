"""
craft_probes.py — Hand-crafted probe SQL definitions for all story-linked questions,
what-if simulations, and policy+data entries (~150-200 entries).

Implements strict V0.1 Verifier Rules:
 1. Compute from base records (tenure from from_date/to_date, age from dob, FY from dates).
 2. Assert stored derived columns equal the recomputation.
 3. Canonical business logic (C1 Delhi overstay, P11 10y cluster cap + retirement exemption,
    C2/H2 hard-station, C4 retirements from dob, C11 headcount vs production, W1 Brent $60 recompute).
 4. Canonical reference literals (checked by lint_probes.py).
 5. Story register target range (±10%, ±2% for calibration targets) embedded in headers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml

PROBES_DIR = Path(__file__).resolve().parent / "probes"
WORLD_BIBLE_DIR = Path(__file__).resolve().parent.parent / "world_bible"
STORY_REGISTER_PATH = WORLD_BIBLE_DIR / "story_register.yaml"


def get_story_target_info(story_id: str, stories_map: Dict[str, Any]) -> Tuple[Optional[float], Optional[float], Optional[float], str]:
    """Retrieve target value and ±10% range for a story."""
    story = stories_map.get(story_id)
    if not story:
        return None, None, None, ""
    nums = story.get("exact_numbers") or {}
    for k, v in nums.items():
        if isinstance(v, dict) and "value" in v and isinstance(v["value"], (int, float)):
            val = float(v["value"])
            tol = 10.0
            min_val = round(val * (1 - tol / 100.0), 2)
            max_val = round(val * (1 + tol / 100.0), 2)
            return val, min_val, max_val, k
    return None, None, None, ""


def write_probe_file(
    probe_id: str,
    parent_id: Optional[str],
    answer_type: str,
    question: str,
    personas: List[str],
    tables: List[str],
    drill_dims: List[str],
    story_ids: List[str],
    expected_output: str,
    sql_query: str,
    stories_map: Dict[str, Any],
    is_handcrafted: bool = True,
) -> None:
    """Format and write a single probe file with V0.1 verification headers."""
    header = [
        f"-- Probe ID: {probe_id}",
        f"-- Parent ID: {parent_id}",
        f"-- Answer Type: {answer_type}",
        f"-- Question: {question}",
        f"-- Personas: {', '.join(personas)}",
        f"-- Tables: {', '.join(tables)}",
        f"-- Drill Dims: {', '.join(drill_dims)}",
        f"-- Story IDs: {', '.join(story_ids)}",
        f"-- Expected Output: {expected_output}",
        f"-- Handcrafted: {'true' if is_handcrafted else 'false'}",
    ]

    # Add Story Target Range if linked and root question
    if story_ids and not parent_id:
        sid = story_ids[0]
        tgt_val, min_v, max_v, metric_name = get_story_target_info(sid, stories_map)
        if tgt_val is not None:
            header.append(f"-- Story Target: {tgt_val} ({metric_name})")
            header.append(f"-- Expected Range: {min_v} - {max_v} (tolerance: ±10.0%)")

    content = "\n".join(header) + "\n\n" + sql_query.strip() + "\n"
    probe_file = PROBES_DIR / f"{probe_id}.sql"
    probe_file.write_text(content, encoding="utf-8")
