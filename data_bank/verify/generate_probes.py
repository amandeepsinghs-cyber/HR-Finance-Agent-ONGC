"""
generate_probes.py — Generates 356 probe SQL files under data_bank/verify/probes/
derived strictly from question_coverage.yaml, schema_silver.yaml, and questions.yaml.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

PROBES_DIR = Path(__file__).resolve().parent / "probes"
WORLD_BIBLE_DIR = Path(__file__).resolve().parent.parent / "world_bible"
SCHEMA_PATH = WORLD_BIBLE_DIR / "schema_silver.yaml"
COVERAGE_PATH = WORLD_BIBLE_DIR / "question_coverage.yaml"
QUESTIONS_PATH = WORLD_BIBLE_DIR / "reference" / "questions.yaml"


def normalize_datediff(text: str) -> str:
    """Translate BigQuery DATE_DIFF(d1, d2, UNIT) to DuckDB datediff('unit', d2, d1)."""
    if not text:
        return text
    # Pattern: DATE_DIFF(end, start, unit)
    pattern = re.compile(r"DATE_DIFF\(([^,]+),\s*([^,]+),\s*([A-Za-z]+)\)", re.IGNORECASE)

    def repl(m: re.Match) -> str:
        end_d = m.group(1).strip()
        start_d = m.group(2).strip()
        unit = m.group(3).strip().lower()
        return f"datediff('{unit}', {start_d}, {end_d})"

    return pattern.sub(repl, text)


def normalize_fy(text: str) -> str:
    """Normalize fiscal_year integer references to ONGC FY conventions (e.g. 2026 -> 'FY26')."""
    if not text:
        return text

    def repl_between(m: re.Match) -> str:
        col = m.group(1)
        y1 = int(m.group(2))
        y2 = int(m.group(3))
        vals = []
        for y in range(y1, y2 + 1):
            vals.extend([f"'FY{str(y)[-2:]}'", f"'{y}'"])
        return f"{col} IN ({', '.join(vals)})"

    text = re.sub(
        r"([A-Za-z0-9_.]*fiscal_year)\s+BETWEEN\s+(20\d\d)\s+AND\s+(20\d\d)",
        repl_between,
        text,
        flags=re.IGNORECASE,
    )

    def repl_in(m: re.Match) -> str:
        col = m.group(1)
        years = re.findall(r"20\d\d", m.group(2))
        vals = []
        for y in years:
            vals.extend([f"'FY{y[-2:]}'", f"'{y}'"])
        return f"{col} IN ({', '.join(vals)})"

    text = re.sub(
        r"([A-Za-z0-9_.]*fiscal_year)\s+IN\s*\(([0-9,\s]+)\)",
        repl_in,
        text,
        flags=re.IGNORECASE,
    )

    def repl_eq(m: re.Match) -> str:
        col = m.group(1)
        y = m.group(2)
        return f"{col} IN ('FY{y[-2:]}', '{y}')"

    text = re.sub(
        r"([A-Za-z0-9_.]*fiscal_year)\s*=\s*(20\d\d)",
        repl_eq,
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"([A-Za-z0-9_.]*fiscal_year)\s*=\s*\'(20\d\d)\'",
        repl_eq,
        text,
        flags=re.IGNORECASE,
    )
    return text


def build_join_graph(schema_data: Dict[str, Any]) -> Tuple[Dict[str, Set[str]], Dict[Tuple[str, str], str]]:
    """Build foreign key and semantic connection graph across all silver tables."""
    adj: Dict[str, Set[str]] = {}
    join_conds: Dict[Tuple[str, str], str] = {}

    tables = schema_data.get("tables", [])
    for t in tables:
        adj[t["table_name"]] = set()

    # 1. Explicit FKs declared in schema_silver.yaml
    for t in tables:
        tname = t["table_name"]
        for c in t.get("columns", []):
            fk = c.get("fk")
            if fk and "." in fk:
                ptable, pcol = fk.split(".")
                cond = f"{tname}.{c['name']} = {ptable}.{pcol}"
                adj[tname].add(ptable)
                adj.setdefault(ptable, set()).add(tname)
                join_conds[(tname, ptable)] = cond
                join_conds[(ptable, tname)] = cond

    # 2. Semantic domain connections
    tbl_cols = {t["table_name"]: [c["name"] for c in t.get("columns", [])] for t in tables}
    for t1, cols1 in tbl_cols.items():
        for t2, cols2 in tbl_cols.items():
            if t1 >= t2 or t2 in adj[t1]:
                continue
            cond = None
            if "asset_wc_id" in cols1 and "wc_id" in cols2:
                cond = f"{t1}.asset_wc_id = {t2}.wc_id"
            elif "wc_id" in cols1 and "asset_wc_id" in cols2:
                cond = f"{t1}.wc_id = {t2}.asset_wc_id"
            elif "field_id" in cols1 and "field_id" in cols2:
                cond = f"{t1}.field_id = {t2}.field_id"
            elif "prj_id" in cols1 and "prj_id" in cols2:
                cond = f"{t1}.prj_id = {t2}.prj_id"
            elif "emp_id" in cols1 and "emp_id" in cols2:
                cond = f"{t1}.emp_id = {t2}.emp_id"
            elif "fiscal_year" in cols1 and "fiscal_year" in cols2:
                cond = f"{t1}.fiscal_year = {t2}.fiscal_year"
            elif "discipline_id" in cols1 and "discipline_id" in cols2:
                cond = f"{t1}.discipline_id = {t2}.discipline_id"
            elif "grade_id" in cols1 and "grade_id" in cols2:
                cond = f"{t1}.grade_id = {t2}.grade_id"

            if cond:
                adj[t1].add(t2)
                adj.setdefault(t2, set()).add(t1)
                join_conds[(t1, t2)] = cond
                join_conds[(t2, t1)] = cond

    return adj, join_conds


def find_shortest_path(
    src: str, dst: str, adj: Dict[str, Set[str]]
) -> Optional[List[str]]:
    """BFS shortest path in graph."""
    if src == dst:
        return [src]
    queue = [[src]]
    visited = {src}
    while queue:
        path = queue.pop(0)
        node = path[-1]
        for neighbor in adj.get(node, []):
            if neighbor == dst:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])
    return None


def generate_sql_probe(
    entry: Dict[str, Any],
    adj: Dict[str, Set[str]],
    join_conds: Dict[Tuple[str, str], str],
) -> str:
    """Generate SQL query for a coverage entry."""
    tables = entry.get("tables", [])
    metric_raw = entry.get("metric_definition") or "COUNT(*)"
    filters_raw = entry.get("filters")
    drill_dims = entry.get("grouping_drill_dims") or []

    # If no tables specified
    if not tables:
        return f"-- STUB: No tables declared\nSELECT '{entry.get('id')}' AS probe_id, 'NO_TABLES' AS status;"

    base_table = tables[0]
    joined_tables = [base_table]
    join_clauses = []

    # Build join tree for tables[1:]
    for target in tables[1:]:
        if target in joined_tables:
            continue
        # Find shortest path from any already joined table to target
        best_path: Optional[List[str]] = None
        for j in joined_tables:
            path = find_shortest_path(j, target, adj)
            if path and (best_path is None or len(path) < len(best_path)):
                best_path = path

        if best_path:
            # Walk along the path and add intermediate joins
            for i in range(len(best_path) - 1):
                u = best_path[i]
                v = best_path[i + 1]
                if v not in joined_tables:
                    cond = join_conds.get((u, v)) or join_conds.get((v, u)) or f"{u}.id = {v}.id"
                    join_clauses.append(f"LEFT JOIN {v} ON {cond}")
                    joined_tables.append(v)
        else:
            # Fallback cross join if completely disconnected
            join_clauses.append(f"CROSS JOIN {target}")
            joined_tables.append(target)

    # Process metrics
    # Handle inline ORDER BY / LIMIT in metric_definition
    inline_order = ""
    order_match = re.search(r"\s+(ORDER BY\s+.*)$", metric_raw, re.IGNORECASE)
    if order_match:
        inline_order = " " + order_match.group(1).strip()
        metric_raw = metric_raw[:order_match.start()].strip()

    # Handle inline GROUP BY in metric_definition
    group_match = re.search(r"\s+GROUP BY\s+([A-Za-z0-9_.,\s]+)$", metric_raw, re.IGNORECASE)
    if group_match:
        extra_group = [g.strip() for g in group_match.group(1).split(",") if g.strip()]
        for eg in extra_group:
            if eg not in drill_dims:
                drill_dims.append(eg)
        metric_raw = metric_raw[:group_match.start()].strip()

    # Handle inline WHERE in metric definition (e.g. "col WHERE cond" -> "CASE WHEN cond THEN col END")
    where_match = re.search(r"^(.*?)\s+WHERE\s+(.*?)$", metric_raw, re.IGNORECASE)
    if where_match and not metric_raw.upper().startswith("SELECT"):
        val_expr = where_match.group(1).strip()
        cond_expr = where_match.group(2).strip()
        if "COUNT(" in val_expr.upper() or "SUM(" in val_expr.upper() or "AVG(" in val_expr.upper():
            # Use FILTER (WHERE ...)
            metric_raw = f"{val_expr} FILTER (WHERE {cond_expr})"
        else:
            metric_raw = f"CASE WHEN {cond_expr} THEN {val_expr} END"

    # Split multiple metrics by semicolon
    metric_parts = [m.strip() for m in metric_raw.split(";") if m.strip()]
    select_items = []

    # Add drill dimensions first
    for d in drill_dims:
        select_items.append(d)

    # Add metrics
    for idx, m in enumerate(metric_parts):
        m_norm = normalize_fy(normalize_datediff(m))
        alias = f"metric_{idx + 1}"
        # Determine natural alias if possible
        col_match = re.search(r"([A-Za-z0-9_]+)\.([A-Za-z_][A-Za-z0-9_]*)$", m_norm)
        if col_match and not col_match.group(2).isdigit():
            alias = col_match.group(2)
        select_items.append(f"{m_norm} AS {alias}")

    select_str = ",\n    ".join(select_items)
    from_str = f"FROM {base_table}"
    joins_str = "\n".join(join_clauses) if join_clauses else ""

    where_str = ""
    if filters_raw:
        norm_filter = normalize_fy(normalize_datediff(filters_raw))
        where_str = f"WHERE {norm_filter}"

    group_str = ""
    # Check if aggregates exist
    has_agg = any(re.search(r"\b(COUNT|SUM|AVG|MIN|MAX)\b", m, re.IGNORECASE) for m in metric_parts)
    if drill_dims and has_agg:
        group_str = f"GROUP BY {', '.join(drill_dims)}"

    # Order by
    order_str = inline_order
    if not order_str and drill_dims:
        order_str = f"ORDER BY {drill_dims[0]}"
    elif not order_str and metric_parts:
        order_str = "ORDER BY 1"

    # Assemble query
    query_parts = [
        f"SELECT\n    {select_str}",
        from_str,
    ]
    if joins_str:
        query_parts.append(joins_str)
    if where_str:
        query_parts.append(where_str)
    if group_str:
        query_parts.append(group_str)
    if order_str:
        query_parts.append(order_str.strip())
    query_parts.append("LIMIT 100;")

    return "\n".join(query_parts)


def generate_all_probes() -> Dict[str, Any]:
    """Read question_coverage.yaml and write one probe file per entry."""
    PROBES_DIR.mkdir(parents=True, exist_ok=True)

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_data = yaml.safe_load(f)

    with open(COVERAGE_PATH, "r", encoding="utf-8") as f:
        cov_data = yaml.safe_load(f)

    adj, join_conds = build_join_graph(schema_data)
    entries = cov_data.get("entries", [])

    stats: Dict[str, int] = {}
    table_usage: Dict[str, int] = {}

    for entry in entries:
        eid = entry["id"]
        atype = entry.get("answer_type", "sql")
        stats[atype] = stats.get(atype, 0) + 1

        for t in entry.get("tables", []):
            table_usage[t] = table_usage.get(t, 0) + 1

        # File header
        header_lines = [
            f"-- Probe ID: {eid}",
            f"-- Parent ID: {entry.get('parent_id')}",
            f"-- Answer Type: {atype}",
            f"-- Question: {entry.get('text', '')}",
            f"-- Personas: {', '.join(entry.get('personas') or [])}",
            f"-- Tables: {', '.join(entry.get('tables') or [])}",
            f"-- Drill Dims: {', '.join(entry.get('grouping_drill_dims') or [])}",
            f"-- Story IDs: {', '.join(entry.get('story_ids') or [])}",
            f"-- Expected Output: {entry.get('expected_output')}",
        ]

        if atype == "rag":
            # Pure RAG stub
            docs = ", ".join(entry.get("documents") or [])
            sql_body = f"""-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: {docs}
SELECT
    '{eid}' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    '{docs}' AS expected_documents;"""
        elif atype == "refusal":
            # Refusal stub
            docs = ", ".join(entry.get("documents") or [])
            metric = (entry.get("metric_definition") or "REFUSAL").replace("'", "''")
            sql_body = f"""-- STUB: Refusal entry (verified against policy boundaries)
-- Refusal Policy: {metric}
-- Reference Documents: {docs}
SELECT
    '{eid}' AS probe_id,
    'STUB_REFUSAL' AS status,
    '{metric}' AS refusal_metric,
    '{docs}' AS reference_documents;"""
        else:
            # SQL / SQL+RAG / What-If / Document-Gen
            sql_body = generate_sql_probe(entry, adj, join_conds)

        full_content = "\n".join(header_lines) + "\n\n" + sql_body + "\n"
        probe_file = PROBES_DIR / f"{eid}.sql"
        with open(probe_file, "w", encoding="utf-8") as pf:
            pf.write(full_content)

    return {
        "total_probes": len(entries),
        "by_answer_type": stats,
        "table_usage": table_usage,
    }


if __name__ == "__main__":
    result = generate_all_probes()
    print("=" * 60)
    print("Probe Generation Complete")
    print(f"Total probes written: {result['total_probes']}")
    print("\nProbes by answer_type:")
    for at, cnt in sorted(result["by_answer_type"].items()):
        print(f"  {at:<20}: {cnt}")
    print(f"\nTables referenced across probes ({len(result['table_usage'])} unique):")
    for tbl, cnt in sorted(result["table_usage"].items(), key=lambda x: -x[1])[:15]:
        print(f"  {tbl:<28}: {cnt}")
    print("=" * 60)
