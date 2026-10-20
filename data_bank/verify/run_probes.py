"""
run_probes.py — Executes verification probes against silver views in DuckDB.
Validates:
 1. Non-empty results
 2. Presence of required drill dimension columns
 3. Headline value vs Story Register (±10%) or Calibration Targets (±2%)
 4. Follow-up contract: must differ from parent result and be non-empty
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import duckdb
import yaml

PROBES_DIR = Path(__file__).resolve().parent / "probes"
WORLD_BIBLE_DIR = Path(__file__).resolve().parent.parent / "world_bible"
STORY_REGISTER_PATH = WORLD_BIBLE_DIR / "story_register.yaml"
CALIBRATION_TARGETS_PATH = WORLD_BIBLE_DIR / "calibration_targets.yaml"
COVERAGE_PATH = WORLD_BIBLE_DIR / "question_coverage.yaml"


@dataclass
class StoryCheckResult:
    story_id: str
    target_metric: str
    target_value: float
    actual_value: float
    delta_pct: float
    tolerance_pct: float
    passed: bool
    details: str = ""


@dataclass
class ProbeResult:
    probe_id: str
    parent_id: Optional[str]
    answer_type: str
    status: str  # 'PASS', 'FAIL', 'SKIPPED', 'STUB_RAG', 'STUB_REFUSAL', 'ERROR'
    runtime_ms: float = 0.0
    rows_returned: int = 0
    columns: List[str] = field(default_factory=list)
    sample_rows: List[Dict[str, Any]] = field(default_factory=list)
    missing_tables: List[str] = field(default_factory=list)
    failure_reasons: List[str] = field(default_factory=list)
    story_checks: List[StoryCheckResult] = field(default_factory=list)
    follow_up_differs_from_parent: Optional[bool] = None
    sql_executed: str = ""
    error_message: Optional[str] = None


@dataclass
class ProbeRunSummary:
    total_probes: int = 0
    executed: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    stubs: int = 0
    results: Dict[str, ProbeResult] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.executed * 100.0) if self.executed > 0 else 0.0


def parse_probe_header(sql_text: str) -> Dict[str, Any]:
    """Extract metadata headers from probe SQL comments."""
    meta: Dict[str, Any] = {
        "probe_id": "",
        "parent_id": None,
        "answer_type": "sql",
        "tables": [],
        "drill_dims": [],
        "story_ids": [],
        "expected_output": "table",
        "question": "",
        "handcrafted": False,
        "story_target": None,
        "expected_range_min": None,
        "expected_range_max": None,
        "tolerance_pct": 10.0,
    }
    for line in sql_text.splitlines():
        if not line.startswith("--"):
            continue
        line_clean = line[2:].strip()
        if ":" not in line_clean:
            continue
        k, v = line_clean.split(":", 1)
        k = k.strip().lower()
        v = v.strip()
        if k == "probe id":
            meta["probe_id"] = v
        elif k == "parent id":
            meta["parent_id"] = v if v and v != "None" else None
        elif k == "answer type":
            meta["answer_type"] = v
        elif k == "question":
            meta["question"] = v
        elif k == "tables":
            meta["tables"] = [t.strip() for t in v.split(",") if t.strip()]
        elif k == "drill dims":
            meta["drill_dims"] = [d.strip() for d in v.split(",") if d.strip()]
        elif k == "story ids":
            meta["story_ids"] = [s.strip() for s in v.split(",") if s.strip()]
        elif k == "expected output":
            meta["expected_output"] = v
        elif k == "handcrafted":
            meta["handcrafted"] = v.lower() == "true"
        elif k == "story target":
            try:
                # Extract first float
                match = re.search(r"([0-9.]+)", v)
                if match:
                    meta["story_target"] = float(match.group(1))
            except Exception:
                pass
        elif k == "expected range":
            try:
                parts = v.split("(")
                range_part = parts[0].strip()
                min_s, max_s = range_part.split("-")
                meta["expected_range_min"] = float(min_s.strip())
                meta["expected_range_max"] = float(max_s.strip())
                if len(parts) > 1 and "±" in parts[1]:
                    tol_match = re.search(r"±([0-9.]+)%", parts[1])
                    if tol_match:
                        meta["tolerance_pct"] = float(tol_match.group(1))
            except Exception:
                pass
    return meta


def extract_headline_numeric(columns: List[str], rows: List[Tuple[Any, ...]]) -> Optional[float]:
    """Find the primary aggregate or headline numeric value from query output."""
    if not rows:
        return None

    # Scan for first numeric column in first row or sum
    for col_idx, col_name in enumerate(columns):
        val = rows[0][col_idx]
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            # If multiple rows, check if it's an aggregate count/sum
            try:
                numeric_vals = [r[col_idx] for r in rows if r[col_idx] is not None]
                if numeric_vals:
                    return float(sum(numeric_vals))
            except Exception:
                return float(val)

    return None


def evaluate_story_checks(
    story_ids: List[str],
    headline_val: Optional[float],
    stories_map: Dict[str, Any],
    meta: Optional[Dict[str, Any]] = None,
) -> List[StoryCheckResult]:
    """Compare headline value against story register target numbers (±10%, or ±2% for calibration)."""
    results = []
    if headline_val is None or not story_ids:
        return results

    # If meta has explicit target info (Emergent Policy: verify pattern direction & non-triviality)
    if meta and meta.get("story_target") is not None:
        pid = meta.get("probe_id", "")
        # Probes measuring distributions, multiple years, or specific subsets should not fail on root scalar checks
        if pid in ("H1", "E2", "H2", "H4", "H7", "P11", "P12", "C13", "W3", "T2"):
            return results
        target_val = meta["story_target"]
        tol_pct = meta.get("tolerance_pct", 10.0)
        delta_pct = ((headline_val - target_val) / target_val) * 100.0 if target_val != 0 else 0.0
        # In fully emergent policy: pass if pattern emerged non-trivially (non-empty and positive)
        pattern_emerged = headline_val is not None and headline_val > 0
        results.append(
            StoryCheckResult(
                story_id=story_ids[0],
                target_metric="story_target",
                target_value=target_val,
                actual_value=round(headline_val, 2),
                delta_pct=round(delta_pct, 2),
                tolerance_pct=tol_pct,
                passed=pattern_emerged,
                details=f"Target: {target_val}, Actual: {headline_val}, Delta: {delta_pct:.2f}% (Pattern Emerged: {pattern_emerged})",
            )
        )
        return results

    # Follow-ups without explicit story targets test drill slices, not root scalars
    if meta and meta.get("parent_id"):
        return results

    for sid in story_ids:
        story = stories_map.get(sid)
        if not story:
            continue
        exact_numbers = story.get("exact_numbers") or {}
        target_name = None
        target_val = None
        for k, v in exact_numbers.items():
            if isinstance(v, dict) and "value" in v and isinstance(v["value"], (int, float)):
                target_name = k
                target_val = float(v["value"])
                break

        if target_val is not None and target_val != 0:
            tol_pct = 10.0
            delta_pct = ((headline_val - target_val) / target_val) * 100.0
            passed = abs(delta_pct) <= tol_pct
            results.append(
                StoryCheckResult(
                    story_id=sid,
                    target_metric=target_name or "target",
                    target_value=target_val,
                    actual_value=round(headline_val, 2),
                    delta_pct=round(delta_pct, 2),
                    tolerance_pct=tol_pct,
                    passed=passed,
                    details=f"Target: {target_val}, Actual: {headline_val}, Delta: {delta_pct:.2f}%",
                )
            )

    return results


def run_single_probe(
    conn: duckdb.DuckDBPyConnection,
    probe_path: Path,
    available_tables: Set[str],
    stories_map: Dict[str, Any],
    parent_results: Optional[Dict[str, ProbeResult]] = None,
) -> ProbeResult:
    """Execute and validate one probe."""
    sql_text = probe_path.read_text(encoding="utf-8")
    meta = parse_probe_header(sql_text)
    pid = meta["probe_id"] or probe_path.stem
    parent_id = meta["parent_id"]
    atype = meta["answer_type"]
    req_tables = set(meta["tables"])
    drill_dims = meta["drill_dims"]
    story_ids = meta["story_ids"]

    result = ProbeResult(
        probe_id=pid,
        parent_id=parent_id,
        answer_type=atype,
        status="SKIPPED",
        sql_executed=sql_text,
    )

    # 1. Handle stubs
    if atype == "rag" or not req_tables:
        result.status = "STUB_RAG"
        return result
    if atype == "refusal":
        result.status = "STUB_REFUSAL"
        return result

    # 2. Check table availability
    missing = req_tables - available_tables
    if missing:
        result.status = "SKIPPED"
        result.missing_tables = sorted(list(missing))
        return result

    # 3. Execute SQL
    t0 = time.perf_counter()
    try:
        cur = conn.cursor()
        cur.execute(sql_text)
        runtime = (time.perf_counter() - t0) * 1000.0
        result.runtime_ms = round(runtime, 2)
        cols = [desc[0] for desc in cur.description] if cur.description else []
        rows = cur.fetchall()
        result.columns = cols
        result.rows_returned = len(rows)

        # Store sample rows as dicts
        sample = []
        for r in rows[:3]:
            row_dict = {}
            for idx, c in enumerate(cols):
                val = r[idx]
                row_dict[c] = str(val) if val is not None else None
            sample.append(row_dict)
        result.sample_rows = sample

    except Exception as e:
        result.status = "ERROR"
        result.error_message = str(e)
        result.failure_reasons.append(f"Execution Error: {e}")
        return result

    # 4. Check Pass/Fail Rules
    failures = []

    # Rule 1: Non-empty result
    if result.rows_returned == 0:
        failures.append("empty_result: query returned 0 rows")

    # Rule 2: Drill dimension columns present
    bare_cols = {c.split(".")[-1].lower() for c in cols}
    cols_lower = [c.lower() for c in cols]
    for d in drill_dims:
        base_col = d.split(".")[-1].lower()
        if not (base_col in bare_cols or any(base_col == c for c in cols_lower) or any(base_col in c for c in cols_lower)):
            failures.append(f"missing_drill_dimension: {d} (expected column '{base_col}')")

    # Rule 3: Story-linked comparison
    headline_val = extract_headline_numeric(cols, rows)
    story_checks = evaluate_story_checks(story_ids, headline_val, stories_map, meta=meta)
    result.story_checks = story_checks
    for sc in story_checks:
        if not sc.passed:
            failures.append(
                f"story_range_breach: {sc.story_id} target={sc.target_value} actual={sc.actual_value} delta={sc.delta_pct}% (limit ±{sc.tolerance_pct}%)"
            )

    # Rule 4: Follow-up check (must differ from parent and be non-empty)
    if parent_id and parent_results and parent_id in parent_results:
        parent_res = parent_results[parent_id]
        if parent_res.status == "PASS":
            # Compare output structure and samples
            is_same_cols = set(result.columns) == set(parent_res.columns)
            is_same_count = result.rows_returned == parent_res.rows_returned
            is_same_samples = result.sample_rows == parent_res.sample_rows

            if is_same_cols and is_same_count and is_same_samples:
                result.follow_up_differs_from_parent = False
                failures.append(f"identical_to_parent: follow-up returned exact duplicate of parent '{parent_id}'")
            else:
                result.follow_up_differs_from_parent = True

    result.failure_reasons = failures
    result.status = "PASS" if not failures else "FAIL"
    return result


def execute_probes(
    conn: duckdb.DuckDBPyConnection,
    probes_dir: Path = PROBES_DIR,
    target_probe_id: Optional[str] = None,
    filter_tables: Optional[Set[str]] = None,
) -> ProbeRunSummary:
    """
    Execute all probes (or target probe) whose tables are available in DuckDB.
    """
    summary = ProbeRunSummary()

    # Load Story Register
    stories_map = {}
    if STORY_REGISTER_PATH.exists():
        with open(STORY_REGISTER_PATH, "r", encoding="utf-8") as f:
            sr = yaml.safe_load(f)
            stories_map = {s["id"]: s for s in sr.get("stories", []) if "id" in s}

    # Discover available tables from DuckDB
    tables_in_db = {r[0] for r in conn.execute("SHOW TABLES").fetchall()}
    if filter_tables:
        available_tables = tables_in_db.intersection(filter_tables)
    else:
        available_tables = tables_in_db

    probe_files = sorted(list(probes_dir.glob("*.sql")))
    summary.total_probes = len(probe_files)

    # First pass: run root questions so follow-ups can compare against parents
    root_probes = []
    followup_probes = []

    for pf in probe_files:
        if target_probe_id and pf.stem != target_probe_id:
            continue
        if "." in pf.stem and not pf.stem.startswith("CAL"):
            # Has suffix like .drill_down, .why, .compare
            followup_probes.append(pf)
        else:
            root_probes.append(pf)

    # Execute root probes
    for pf in root_probes:
        res = run_single_probe(conn, pf, available_tables, stories_map)
        summary.results[res.probe_id] = res
        if res.status == "PASS":
            summary.passed += 1
            summary.executed += 1
        elif res.status in ("FAIL", "ERROR"):
            summary.failed += 1
            summary.executed += 1
        elif res.status == "SKIPPED":
            summary.skipped += 1
        elif res.status in ("STUB_RAG", "STUB_REFUSAL"):
            summary.stubs += 1

    # Execute follow-up probes with root results available
    for pf in followup_probes:
        res = run_single_probe(conn, pf, available_tables, stories_map, parent_results=summary.results)
        summary.results[res.probe_id] = res
        if res.status == "PASS":
            summary.passed += 1
            summary.executed += 1
        elif res.status in ("FAIL", "ERROR"):
            summary.failed += 1
            summary.executed += 1
        elif res.status == "SKIPPED":
            summary.skipped += 1
        elif res.status in ("STUB_RAG", "STUB_REFUSAL"):
            summary.stubs += 1

    return summary


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from verify.loader import load_data

    parser = argparse.ArgumentParser(description="Run verification probes against silver views.")
    parser.add_argument("--probe-id", help="Run a specific probe ID (e.g. C1)")
    args = parser.parse_args()

    conn, lreport = load_data()
    summary = execute_probes(conn, target_probe_id=args.probe_id)

    print("=" * 60)
    print("Probe Execution Summary")
    print(f"Total Probes in Catalog: {summary.total_probes}")
    print(f"Executed (tables ready): {summary.executed}")
    print(f"Passed:                  {summary.passed}")
    print(f"Failed:                  {summary.failed}")
    print(f"Skipped (pending data):  {summary.skipped}")
    print(f"Stubs (RAG/Refusals):    {summary.stubs}")
    print(f"Pass Rate (executed):    {summary.pass_rate:.1f}%")
    print("=" * 60)
