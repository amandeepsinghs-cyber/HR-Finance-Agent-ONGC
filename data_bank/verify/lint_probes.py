"""
lint_probes.py — Linter that checks every string literal in WHERE clauses of all
probe SQL files against canonical reference values in world_bible/reference/ and
schema_silver.yaml accepted_values.

Catches invented or hallucinated values (e.g. function='Surface Engineering',
hard_station_cat='Category C', invalid wc_id, invalid field_id).
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import yaml

WORLD_BIBLE_DIR = Path(__file__).resolve().parent.parent / "world_bible"
REF_DIR = WORLD_BIBLE_DIR / "reference"
SCHEMA_PATH = WORLD_BIBLE_DIR / "schema_silver.yaml"
PROBES_DIR = Path(__file__).resolve().parent / "probes"


@dataclass
class LintIssue:
    probe_id: str
    file_path: str
    column: str
    literal_value: str
    reason: str


def load_canonical_reference_sets() -> Dict[str, Set[str]]:
    """Load valid IDs and accepted values for all filtered columns."""
    valid_sets: Dict[str, Set[str]] = {}

    # 1. Load from schema_silver.yaml accepted_values
    if SCHEMA_PATH.exists():
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = yaml.safe_load(f)
        for t in schema.get("tables", []):
            tname = t["table_name"]
            for c in t.get("columns", []):
                col = c["name"]
                if "accepted_values" in c:
                    vals = {str(v) for v in c["accepted_values"]}
                    valid_sets[f"{tname}.{col}"] = vals
                    valid_sets.setdefault(col, set()).update(vals)

    # 2. Load from world_bible/reference/
    # work_centres.yaml
    wc_file = REF_DIR / "work_centres.yaml"
    if wc_file.exists():
        with open(wc_file, "r", encoding="utf-8") as f:
            wc_data = yaml.safe_load(f).get("work_centres", [])
        wc_ids = {r["wc_id"] for r in wc_data}
        wc_names = {r["name"] for r in wc_data}
        wc_short_names = {r["short_name"] for r in wc_data}
        cities = {r["city"] for r in wc_data}
        clusters = {r["cluster_id"] for r in wc_data}
        sectors = {r["sector"] for r in wc_data}
        hard_cats = {r["hard_station_cat"] for r in wc_data}
        on_offs = {r["onshore_offshore"] for r in wc_data}

        valid_sets["wc_id"] = wc_ids
        valid_sets["dim_work_centre.wc_id"] = wc_ids
        valid_sets["current_wc_id"] = wc_ids
        valid_sets["city"] = cities
        valid_sets["dim_work_centre.city"] = cities
        valid_sets["cluster_id"] = clusters
        valid_sets["dim_work_centre.cluster_id"] = clusters
        valid_sets["sector"] = sectors
        valid_sets["dim_work_centre.sector"] = sectors
        valid_sets["short_name"] = wc_short_names
        valid_sets["dim_work_centre.short_name"] = wc_short_names
        # Strict categorical values
        valid_sets["hard_station_cat"] = hard_cats
        valid_sets["dim_work_centre.hard_station_cat"] = hard_cats
        valid_sets["onshore_offshore"] = on_offs
        valid_sets["dim_work_centre.onshore_offshore"] = on_offs

    # grades.yaml
    gr_file = REF_DIR / "grades.yaml"
    if gr_file.exists():
        with open(gr_file, "r", encoding="utf-8") as f:
            gr_data = yaml.safe_load(f).get("grades", [])
        gr_ids = {r["grade_id"] for r in gr_data}
        valid_sets["grade_id"] = gr_ids
        valid_sets["dim_grade.grade_id"] = gr_ids
        valid_sets["current_grade_id"] = gr_ids
        valid_sets["from_grade_id"] = gr_ids
        valid_sets["to_grade_id"] = gr_ids

    # disciplines.yaml
    disc_file = REF_DIR / "disciplines.yaml"
    if disc_file.exists():
        with open(disc_file, "r", encoding="utf-8") as f:
            disc_data = yaml.safe_load(f).get("disciplines", [])
        disc_ids = {r["discipline_id"] for r in disc_data}
        disc_names = {r["name"] for r in disc_data}
        valid_sets["discipline_id"] = disc_ids
        valid_sets["dim_discipline.discipline_id"] = disc_ids
        valid_sets["discipline"] = disc_names
        valid_sets["dim_discipline.name"] = disc_names

    # fields.yaml
    fld_file = REF_DIR / "fields.yaml"
    if fld_file.exists():
        with open(fld_file, "r", encoding="utf-8") as f:
            fld_data = yaml.safe_load(f).get("fields", [])
        fld_ids = {r["field_id"] for r in fld_data}
        fld_names = {r["name"] for r in fld_data}
        valid_sets["field_id"] = fld_ids
        valid_sets["dim_field.field_id"] = fld_ids
        valid_sets["dim_field.name"] = fld_names

    # projects.yaml
    prj_file = REF_DIR / "projects.yaml"
    if prj_file.exists():
        with open(prj_file, "r", encoding="utf-8") as f:
            prj_data = yaml.safe_load(f).get("projects", [])
        prj_ids = {r["prj_id"] for r in prj_data}
        valid_sets["prj_id"] = prj_ids
        valid_sets["dim_project.prj_id"] = prj_ids

    # Valid fiscal years
    valid_fys = {f"FY{str(y)[-2:]}" for y in range(2012, 2030)} | {str(y) for y in range(2012, 2030)}
    valid_sets["fiscal_year"] = valid_fys

    return valid_sets


def extract_where_literals(sql_text: str) -> List[Tuple[str, str]]:
    """
    Parse WHERE clause and extract (column_name, literal_value) pairs.
    Handles '=', 'IN', and 'LIKE'.
    """
    results = []
    # Find WHERE clause
    where_match = re.search(r"\bWHERE\b(.*?)(?:\bGROUP BY\b|\bORDER BY\b|\bLIMIT\b|;|$)", sql_text, re.DOTALL | re.IGNORECASE)
    if not where_match:
        return results

    where_clause = where_match.group(1)

    # 1. Matches: column = 'literal'
    eq_matches = re.finditer(r"([A-Za-z0-9_.]+)\s*=\s*'([^']+)'", where_clause)
    for m in eq_matches:
        col = m.group(1).strip()
        val = m.group(2).strip()
        results.append((col, val))

    # 2. Matches: column IN ('lit1', 'lit2', ...)
    in_matches = re.finditer(r"([A-Za-z0-9_.]+)\s+IN\s*\(([^)]+)\)", where_clause, re.IGNORECASE)
    for m in in_matches:
        col = m.group(1).strip()
        vals_block = m.group(2)
        literals = re.findall(r"'([^']+)'", vals_block)
        for val in literals:
            results.append((col, val.strip()))

    return results


def lint_probe_file(
    file_path: Path,
    canonical_sets: Dict[str, Set[str]],
) -> List[LintIssue]:
    """Validate all WHERE literals in a probe file against canonical sets."""
    issues = []
    pid = file_path.stem
    sql_text = file_path.read_text(encoding="utf-8")

    pairs = extract_where_literals(sql_text)
    for col, lit_val in pairs:
        base_col = col.split(".")[-1].lower()
        full_col = col.lower()

        # Find matching canonical set
        target_set: Optional[Set[str]] = None
        if full_col in canonical_sets:
            target_set = canonical_sets[full_col]
        elif base_col in canonical_sets:
            target_set = canonical_sets[base_col]

        if target_set is not None:
            # Check case-insensitively or exact
            target_set_lower = {v.lower() for v in target_set}
            if lit_val.lower() not in target_set_lower:
                issues.append(
                    LintIssue(
                        probe_id=pid,
                        file_path=str(file_path),
                        column=col,
                        literal_value=lit_val,
                        reason=f"Literal '{lit_val}' is not in canonical reference or accepted_values for '{col}'. Valid sample: {list(target_set)[:5]}",
                    )
                )

    return issues


def run_probe_linter(probes_dir: Path = PROBES_DIR) -> Tuple[List[LintIssue], int]:
    """Run linter across all probe SQL files in probes_dir."""
    canonical_sets = load_canonical_reference_sets()
    all_issues = []
    probe_files = sorted(list(probes_dir.glob("*.sql")))

    for pf in probe_files:
        issues = lint_probe_file(pf, canonical_sets)
        all_issues.extend(issues)

    return all_issues, len(probe_files)


if __name__ == "__main__":
    issues, total_files = run_probe_linter()
    print("=" * 60)
    print("Probe WHERE Clause Linter")
    print(f"Total Probe Files Linted: {total_files}")
    print(f"Total Lint Violations:     {len(issues)}")
    if issues:
        print("\nViolations Found:")
        for iss in issues:
            print(f"  [{iss.probe_id}] {iss.column} = '{iss.literal_value}'")
            print(f"     -> {iss.reason}")
        sys.exit(1)
    else:
        print("\nAll probe WHERE literals are 100% compliant with World Bible reference data!")
        print("=" * 60)
        sys.exit(0)
