"""
verify_step.py — Orchestrates data loading, probe execution, consistency audits,
and story emergence checks for a specified generation step (e.g. 2.1, 2.3, V0).
Generates verify/reports/<step_id>_verification.md and .json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Ensure project root in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verify.consistency import run_consistency_audits
from verify.loader import load_data, DEFAULT_DB_PATH, DEFAULT_LANDING_DIR
from verify.run_probes import execute_probes, ProbeResult
from verify.story_actuals import record_step_story_actuals

REPORTS_DIR = Path(__file__).resolve().parent / "reports"
WORLD_BIBLE_DIR = Path(__file__).resolve().parent.parent / "world_bible"
STORY_REGISTER_PATH = WORLD_BIBLE_DIR / "story_register.yaml"
CHECKLIST_PATH = WORLD_BIBLE_DIR.parent / "DATA_GENERATION_CHECKLIST.md"

# Mapping from generation step to domain silver tables
STEP_TABLE_MAP: Dict[str, List[str]] = {
    "2.1": [
        "employee_master",
        "posting_history",
        "promotion_history",
        "dpc_cases",
        "separations",
    ],
    "2.2": [
        "sanctioned_posts",
        "headcount_snapshot",
        "payroll_monthly",
        "apar_ratings",
        "succession_plan",
        "training_records",
        "training_calendar",
        "leave_ledger",
        "medical_claims",
        "grievances_litigation",
        "contract_workforce",
        "hse_incidents",
        "travel_claims",
        "icc_committees",
        "vigilance_cases",
    ],
    "2.3": [
        "production_monthly",
        "reserves_annual",
        "wells_drilled",
        "price_fx_monthly",
    ],
    "2.4": [
        "field_pnl_annual",
        "cost_ledger",
        "capex_budget",
        "project_progress",
        "purchase_orders",
        "receivables",
        "forex_hedges",
    ],
    "2.5": [
        "csr_projects",
        "mou_targets",
        "benefit_liabilities",
        "subsidiary_financials",
        "energy_transition",
        "corporate_financials",
        "parliament_questions",
        "cag_paras",
        "rti_applications",
        "board_agenda_index",
        "access_audit_log",
    ],
}


def compute_landing_manifest(landing_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Compute SHA-256 (first 16 chars) and mtime for all landing files."""
    manifest: Dict[str, Dict[str, Any]] = {}
    if not landing_dir.exists():
        return manifest

    for root, _, files in os.walk(landing_dir):
        for f in sorted(files):
            p = Path(root) / f
            try:
                h = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
                mtime = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(os.path.getmtime(p)))
                manifest[f] = {
                    "name": f,
                    "sha256": h,
                    "mtime": mtime,
                    "size_bytes": os.path.getsize(p),
                    "relative_path": str(p.relative_to(landing_dir.parent)),
                }
            except Exception:
                pass
    return manifest


def verify_step(
    step_id: str,
    db_path: Optional[Path] = None,
    landing_dir: Optional[Path] = None,
    output_dir: Path = REPORTS_DIR,
) -> Dict[str, Any]:
    """Execute complete verification harness for a step."""
    output_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    target_landing_dir = landing_dir if landing_dir else DEFAULT_LANDING_DIR

    # Mandate 1: Compute landing manifest (SHA256 first 16 chars + mtime)
    manifest = compute_landing_manifest(target_landing_dir)

    # Mandate 2: Rebuild verify/local.duckdb from scratch (delete it first)
    target_db = str(db_path) if db_path else str(DEFAULT_DB_PATH)
    if target_db != ":memory:":
        dbp = Path(target_db)
        if dbp.exists():
            dbp.unlink()
        wal = Path(f"{target_db}.wal")
        if wal.exists():
            wal.unlink()

    # 1. Load Data from scratch
    conn, load_report = load_data(
        db_path=Path(target_db) if target_db != ":memory:" else None,
        landing_dir=target_landing_dir,
    )
    available_tables = set(load_report.available_tables)

    # 2. Filter step target tables
    step_key = step_id.strip()
    target_tables = STEP_TABLE_MAP.get(step_key)

    ref_dims = {
        "dim_work_centre", "dim_field", "dim_discipline", "dim_grade",
        "dim_project", "dim_cost_centre", "dim_customer", "dim_vendor",
        "dim_geography", "dim_calendar", "dim_price_fx",
    }
    scoped_tables = (set(target_tables) | ref_dims) if target_tables else None
    
    # 3. Consistency Audits
    consistency_rep = run_consistency_audits(conn, filter_tables=scoped_tables)

    # 4. Probe Execution
    probe_summary = execute_probes(conn)

    # 5. Filter probes relevant to step if target_tables specified
    step_probes = {}
    for pid, res in probe_summary.results.items():
        if target_tables:
            # Check if probe uses any of the step's target tables
            sql_meta_tables = set(res.sql_executed.split("Tables:")[1].splitlines()[0].split(",")) if "Tables:" in res.sql_executed else set()
            sql_meta_tables = {t.strip() for t in sql_meta_tables if t.strip()}
            if sql_meta_tables.intersection(set(target_tables)):
                # If probe requires tables outside this step's target_tables and ref_dims, it is PENDING
                other_needed = sql_meta_tables - (set(target_tables) | ref_dims)
                if other_needed:
                    res_pending = ProbeResult(
                        probe_id=res.probe_id,
                        parent_id=res.parent_id,
                        answer_type=res.answer_type,
                        status="SKIPPED",
                        missing_tables=sorted(list(other_needed)),
                        sql_executed=res.sql_executed,
                    )
                    step_probes[pid] = res_pending
                else:
                    step_probes[pid] = res
        else:
            step_probes[pid] = res

    # Compile step stats
    probed_count = len(step_probes)
    executed_probes = [r for r in step_probes.values() if r.status in ("PASS", "FAIL", "ERROR")]
    passed_probes = [r for r in executed_probes if r.status == "PASS"]
    failed_probes = [r for r in executed_probes if r.status in ("FAIL", "ERROR")]
    pending_probes = [r for r in step_probes.values() if r.status == "SKIPPED"]
    stub_probes = [r for r in step_probes.values() if r.status in ("STUB_RAG", "STUB_REFUSAL")]

    pass_rate = (len(passed_probes) / len(executed_probes) * 100.0) if executed_probes else 0.0

    # Overall verdict
    is_step_ready = (
        len(set(target_tables).intersection(available_tables)) == len(target_tables)
        if target_tables
        else len(available_tables) > 0
    )
    has_critical_failures = len(failed_probes) > 0 or consistency_rep.failed_audits > 0

    if not is_step_ready:
        verdict = "INCOMPLETE"
        verdict_msg = f"Step {step_id} source tables are still pending generation or partially missing."
    elif has_critical_failures:
        verdict = "FAIL"
        verdict_msg = f"Step {step_id} verification failed: {len(failed_probes)} probes failed, {consistency_rep.failed_audits} consistency audits failed."
    else:
        verdict = "PASS"
        verdict_msg = f"Step {step_id} verification passed: 100% available probes answered ({len(passed_probes)}/{len(executed_probes)}), {len(pending_probes)} pending cross-domain tables, 0 consistency violations."

    # 5. Compute Story Emergence Actuals from live DuckDB
    story_actuals = record_step_story_actuals(conn, step_id, manifest=manifest)

    # Generate Markdown Report
    md_content = build_markdown_report(
        step_id=step_id,
        verdict=verdict,
        verdict_msg=verdict_msg,
        load_report=load_report,
        consistency_rep=consistency_rep,
        executed_probes=executed_probes,
        passed_probes=passed_probes,
        failed_probes=failed_probes,
        pending_probes=pending_probes,
        stub_probes=stub_probes,
        pass_rate=pass_rate,
        target_tables=target_tables,
        duration_sec=time.time() - t_start,
        conn=conn,
        manifest=manifest,
        story_actuals=story_actuals,
    )

    md_path = output_dir / f"{step_id}_verification.md"
    md_path.write_text(md_content, encoding="utf-8")

    # Generate JSON Report
    json_data = {
        "step_id": step_id,
        "verdict": verdict,
        "verdict_msg": verdict_msg,
        "execution_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "duration_seconds": round(time.time() - t_start, 2),
        "tables": {
            "available_count": len(load_report.available_tables),
            "available": load_report.available_tables,
            "skipped_count": len(load_report.skipped_tables),
            "skipped": load_report.skipped_tables,
        },
        "consistency": {
            "total_audits": consistency_rep.total_audits,
            "passed": consistency_rep.passed_audits,
            "failed": consistency_rep.failed_audits,
            "calibration_targets_checked": len(consistency_rep.calibration_results),
            "calibration_targets_passed": sum(1 for c in consistency_rep.calibration_results if c.passed),
        },
        "probes": {
            "total_in_step_scope": probed_count,
            "answered": len(passed_probes),
            "failed": len(failed_probes),
            "pending": len(pending_probes),
            "stubs": len(stub_probes),
            "pass_rate_pct": round(pass_rate, 2),
        },
        "failed_probe_details": [
            {
                "probe_id": r.probe_id,
                "status": r.status,
                "failure_reasons": r.failure_reasons,
                "sample_rows": r.sample_rows,
            }
            for r in failed_probes
        ],
        "pending_probes": [
            {
                "probe_id": r.probe_id,
                "missing_tables": r.missing_tables,
            }
            for r in pending_probes
        ],
    }

    json_path = output_dir / f"{step_id}_verification.json"
    json_path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")

    return json_data


def build_markdown_report(
    step_id: str,
    verdict: str,
    verdict_msg: str,
    load_report: Any,
    consistency_rep: Any,
    executed_probes: List[Any],
    passed_probes: List[Any],
    failed_probes: List[Any],
    pending_probes: List[Any],
    stub_probes: List[Any],
    pass_rate: float,
    target_tables: Optional[List[str]],
    duration_sec: float,
    conn: Optional[duckdb.DuckDBPyConnection] = None,
    manifest: Optional[Dict[str, Dict[str, Any]]] = None,
    story_actuals: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Format verification findings according to Pyramid Principle."""
    alert_type = "IMPORTANT" if verdict == "PASS" else ("WARNING" if verdict == "INCOMPLETE" else "CAUTION")

    lines = [
        f"# Step {step_id} Verification Report",
        "",
        f"> [{alert_type}]",
        f"> **VERDICT: {verdict}** — {verdict_msg}",
        "",
        "## 1. Landing Data Provenance Manifest (SHA-256 & mtime)",
        "| Landing File | SHA-256 (16-char) | Modified Time (UTC) | File Size |",
        "|---|---|---|---|",
    ]

    if manifest:
        for fname, info in sorted(manifest.items()):
            lines.append(f"| `{fname}` | `{info['sha256']}` | {info['mtime']} | {info['size_bytes']:,} bytes |")
    else:
        lines.append("| - | No landing files recorded | - | - |")
    lines.append("")

    lines.extend([
        "## 2. Executive Summary",
        f"- **Verification Target:** Step `{step_id}`",
        f"- **Execution Duration:** `{duration_sec:.2f}s`",
        f"- **Probes Answered (Passed):** `{len(passed_probes)}/{len(executed_probes)}` (`{pass_rate:.1f}%` pass rate on available tables)",
        f"- **Probes Failed:** `{len(failed_probes)}`",
        f"- **Probes Pending Cross-Domain Tables:** `{len(pending_probes)}` (requires tables from pending steps, e.g. HR, P&L, Capex)",
        f"- **Probes Stubs (RAG / Refusals):** `{len(stub_probes)}`",
        f"- **Consistency Audits:** `{consistency_rep.passed_audits}/{consistency_rep.total_audits}` passed ({consistency_rep.failed_audits} violations)",
        f"- **Calibration Targets:** `{sum(1 for c in consistency_rep.calibration_results if c.passed)}/{len(consistency_rep.calibration_results)}` within tolerance",
        "",
        "## 3. Table Availability",
        f"Available ({len(load_report.available_tables)}): `" + ", ".join(sorted(load_report.available_tables)) + "`",
        "",
    ])

    if target_tables:
        lines.append("### Step Target Tables Status")
        lines.append("| Target Table | Status | Row Count | Source File |")
        lines.append("|---|---|---|---|")
        for tt in target_tables:
            st = load_report.table_statuses.get(tt)
            if st and st.status == "loaded":
                lines.append(f"| `{tt}` | **LOADED** | {st.row_count} | `{st.source_file}` |")
            else:
                lines.append(f"| `{tt}` | PENDING / MISSING | 0 | - |")
        lines.append("")

    # Story Emergence Table (100% computed from live records, expectations loaded from YAML)
    if story_actuals:
        lines.append(f"## 4. Story Emergence Validation (Step {step_id})")
        lines.append("| Story ID | Story Title / Narrative | Target Metric | Expected Benchmark | Actual Computed | Delta % | Verdict |")
        lines.append("|---|---|---|---|---|---|---|")
        for e in story_actuals:
            exp_str = f"{e['expected_value']}" if e['expected_value'] is not None else "-"
            act_str = f"{e['actual_value']}" if e['actual_value'] is not None else "-"
            delta_str = f"{e['delta_pct']:+.2f}%" if e['expected_value'] is not None else "-"
            lines.append(f"| `{e['story_id']}` | {e.get('story_title', '')} | `{e['metric']}` | {exp_str} | {act_str} | {delta_str} | {e['verdict']} |")
        lines.append("")

    # Consistency Findings
    lines.append("## 5. Consistency Audits")
    lines.append("| Category | Audit Name | Entity | Status | Details |")
    lines.append("|---|---|---|---|---|")
    for a in consistency_rep.audit_results:
        st_icon = "PASS" if a.status == "PASS" else f"**{a.status}**"
        lines.append(f"| {a.audit_category} | {a.audit_name} | `{a.target_entity}` | {st_icon} | {a.details} |")
    lines.append("")

    # Calibration targets
    if consistency_rep.calibration_results:
        lines.append("## 6. Calibration Targets")
        lines.append("| Target ID | Domain | Period | Metric | Target | Actual | Delta % | Tolerance | Status |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for c in consistency_rep.calibration_results:
            st_icon = "PASS" if c.passed else "**FAIL**"
            lines.append(f"| `{c.target_id}` | {c.domain} | {c.period} | {c.metric} | {c.target_value} | {c.actual_value} | {c.delta_pct}% | {c.tolerance} | {st_icon} |")
        lines.append("")

    # Probes Detailed Table
    lines.append("## 7. Probes Detailed Findings")
    if failed_probes:
        lines.append("### Failed / Error Probes")
        lines.append("| Probe ID | Answer Type | Status | Rows | Runtime (ms) | Failure Reasons |")
        lines.append("|---|---|---|---|---|---|")
        for p in failed_probes:
            reasons = "; ".join(p.failure_reasons)
            lines.append(f"| `{p.probe_id}` | {p.answer_type} | **{p.status}** | {p.rows_returned} | {p.runtime_ms} | {reasons} |")
        lines.append("")

    if passed_probes:
        lines.append("### Sample Passed Probes")
        lines.append("| Probe ID | Answer Type | Status | Rows | Runtime (ms) | Sample Output |")
        lines.append("|---|---|---|---|---|---|")
        for p in passed_probes[:10]:
            sample_str = str(p.sample_rows[0]) if p.sample_rows else "-"
            # Truncate sample str for table display
            if len(sample_str) > 60:
                sample_str = sample_str[:57] + "..."
            lines.append(f"| `{p.probe_id}` | {p.answer_type} | {p.status} | {p.rows_returned} | {p.runtime_ms} | `{sample_str}` |")
        lines.append("")

    lines.append("---")
    lines.append("*Generated by ONGC Independent Verification Harness V1*")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify generation step and generate reports.")
    parser.add_argument("step_id", help="Step ID (e.g. 2.1, 2.3, V0, all)")
    args = parser.parse_args()

    res = verify_step(args.step_id)
    print("=" * 60)
    print(f"Verification Run Complete: Step {args.step_id}")
    print(f"Verdict: {res['verdict']}")
    print(f"Details: {res['verdict_msg']}")
    print(f"Report written to: verify/reports/{args.step_id}_verification.md")
    print(f"JSON written to:   verify/reports/{args.step_id}_verification.json")
    print("=" * 60)
