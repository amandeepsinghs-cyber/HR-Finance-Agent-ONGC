"""Live BigQuery Data Query Tool for Yukti AI.
Executes read-only SQL queries over hrfin_gold and hrfin_silver, applies query-craft rules,
enforces SELECT-only safety and byte billing caps, computes deterministic arithmetic summary,
and returns structured rows with declarative chart specs.
"""

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional
from google.cloud import bigquery

from app.config import BQ_LOCATION, GCP_PROJECT, JOB_LABELS, MAX_BYTES_BILLED
from app.tools.chart_rules import build_chart_spec, select_chart_kind
from app.semantic.entities import get_entities
from app.tools.semantic_layer import SemanticLayer

logger = logging.getLogger("yukti.tools.query_data")


def compute_deterministic_summary(columns: List[str], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Computes exact, deterministic totals, sums, and rankings across all rows in Python code."""
    if not rows:
        return {"total_rows": 0, "message": "Zero records found."}

    summary: Dict[str, Any] = {
        "total_rows": len(rows),
    }

    # Find count or numeric sum columns
    count_cols = [c for c in columns if any(k in c.lower() for k in ["count", "num_", "executives", "headcount", "strength", "posts", "vacanc"])]
    amount_cols = [c for c in columns if any(k in c.lower() for k in ["amount", "revenue", "cost", "opex", "capex", "ebitda", "pbt", "pat", "spend", "loss"])]

    # Compute exact sum of primary count column if present
    if count_cols:
        primary_count = count_cols[0]
        try:
            total_sum = sum(int(r.get(primary_count, 0) or 0) for r in rows)
            summary["primary_count_column"] = primary_count
            summary["total_count"] = total_sum
        except Exception:
            pass

    elif amount_cols:
        primary_amount = amount_cols[0]
        try:
            total_sum = round(sum(float(r.get(primary_amount, 0.0) or 0.0) for r in rows), 2)
            summary["primary_amount_column"] = primary_amount
            summary["total_sum"] = total_sum
        except Exception:
            pass

    # Friendly names come from the single entity dictionary (B1.2)
    ents = get_entities()

    # Group / Rank by ALL present dimensions (e.g. discipline_id, grade_id, field_name, asset_name)
    dim_cols = [c for c in columns if any(k in c.lower() for k in ["discipline", "grade", "field", "asset", "wc_", "city", "state"])]
    if dim_cols and count_cols:
        cnt = count_cols[0]
        dimension_facts = []
        summary["dimension_totals"] = {}

        for dim in dim_cols:
            dim_totals: Dict[str, int] = {}
            for r in rows:
                raw_d = str(r.get(dim, "Unknown")).strip()
                # Apply friendly name
                d_val = ents.friendly(raw_d)
                try:
                    c_val = int(r.get(cnt, 0) or 0)
                except Exception:
                    c_val = 1
                dim_totals[d_val] = dim_totals.get(d_val, 0) + c_val

            ranked = sorted(dim_totals.items(), key=lambda x: x[1], reverse=True)
            summary["ranked_by_" + dim] = [{"name": k, "count": v} for k, v in ranked[:10]]
            summary["dimension_totals"][dim] = dict(ranked)

            top_items = [f"{k} ({v})" for k, v in ranked[:3] if v > 0]
            if top_items:
                dim_clean = "Discipline" if "disc" in dim.lower() else ("Grade" if "grade" in dim.lower() else dim)
                dimension_facts.append(f"{dim_clean}: {', '.join(top_items)}")

        summary["top_ranked_text"] = ". ".join(dimension_facts)
        # Store structured label->value pairs for validation
        summary["label_value_pairs"] = summary["dimension_totals"]

    return summary


def query_data(
    sql_query: str,
    title: Optional[str] = None,
    persona: str = "CMD",
    voice_override: Optional[str] = None,
    semantic_layer: Optional[SemanticLayer] = None,
) -> Dict[str, Any]:
    """Executes a validated, read-only BigQuery query over hrfin_gold / hrfin_silver.

    Args:
        sql_query: The SQL query to execute.
        title: Optional title for the visual.
        persona: Executive persona access scope (for cache partition safety).
        voice_override: Presenter voice override (e.g. 'as bars', 'as a table').
        semantic_layer: Optional SemanticLayer instance.

    Returns:
        Dict with status, row_count, columns, rows, chart_spec, deterministic summary, and metadata.
    """
    t0 = time.perf_counter()
    sl = semantic_layer or SemanticLayer()

    # 1. Apply Query-Craft Rules & Project Qualification
    safe_sql = sl.apply_query_craft_rules(sql_query)

    # 2. Strict In-Process Safety Validation
    is_safe, safety_err = sl.validate_sql_safety(safe_sql)
    if not is_safe:
        return {
            "status": "error",
            "error": safety_err,
            "sql": sql_query,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        }

    # 3. Check Option A Tool-Result Cache (if enabled)
    from app.config import YUKTI_RESULT_CACHE
    from app.tool_cache import get_tool_cache
    tool_cache = get_tool_cache()

    if YUKTI_RESULT_CACHE:
        cached_result = tool_cache.get_sql(safe_sql, persona=persona)
        if cached_result:
            res_copy = dict(cached_result)
            res_copy["from_cache"] = True
            res_copy["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
            return res_copy

    # 4. Direct Execution with default_dataset and maximum_bytes_billed cap
    job_config = bigquery.QueryJobConfig(
        default_dataset=f"{GCP_PROJECT}.hrfin_silver",
        labels=JOB_LABELS,
        maximum_bytes_billed=MAX_BYTES_BILLED,
    )

    try:
        query_job = sl.client.query(safe_sql, job_config=job_config)
        result = query_job.result()

        rows: List[Dict[str, Any]] = []
        raw_columns = [f.name for f in result.schema] if result.schema else []
        col_rename_map = {}
        for idx_c, c_name in enumerate(raw_columns):
            if re.match(r"^f\d+_$", c_name, flags=re.IGNORECASE):
                col_rename_map[c_name] = "employees" if any(w in safe_sql.lower() for w in ["workforce", "employee", "headcount", "stay", "post"]) else ("total_count" if idx_c == 0 else f"metric_{idx_c + 1}")
            else:
                col_rename_map[c_name] = c_name
        columns = [col_rename_map[c] for c in raw_columns]

        for row in result:
            row_dict = {}
            for k, v in dict(row).items():
                clean_k = col_rename_map.get(k, k)
                if hasattr(v, "isoformat"):
                    row_dict[clean_k] = v.isoformat()
                elif isinstance(v, (bool, int)):
                    # Keep counts as ints (float() turned 419 into 419.0 in tables/charts).
                    row_dict[clean_k] = v
                elif hasattr(v, "__float__"):
                    try:
                        row_dict[clean_k] = float(v)
                    except Exception:
                        row_dict[clean_k] = str(v)
                else:
                    row_dict[clean_k] = v
            rows.append(row_dict)

        elapsed_sec = round(time.perf_counter() - t0, 3)
        elapsed_ms = round(elapsed_sec * 1000, 2)
        total_bytes = query_job.total_bytes_processed or 0

        # Deterministic summary arithmetic in Python
        det_summary = compute_deterministic_summary(columns=columns, rows=rows)

        # Determine chart selection per UX Spec §6
        chart_kind = select_chart_kind(
            columns=columns,
            rows=rows,
            question_type="data",
            voice_override=voice_override,
        )
        chart_spec = None
        if chart_kind != "table":
            chart_spec = build_chart_spec(
                kind=chart_kind,
                columns=columns,
                rows=rows,
                title=title,
            )

        out = {
            "status": "success",
            "sql": safe_sql,
            "row_count": len(rows),
            "columns": columns,
            "deterministic_summary": det_summary,
            "rows": rows[:15],  # preview for model
            "all_rows": rows,   # full dataset for canvas
            "total_bytes_processed": total_bytes,
            "elapsed_seconds": elapsed_sec,
            "latency_ms": elapsed_ms,
            "chart_kind": chart_kind,
            "chart_spec": chart_spec,
        }
        if YUKTI_RESULT_CACHE:
            tool_cache.set_sql(safe_sql, persona, out)
        return out

    except Exception as e1:
        err_msg = str(e1)
        logger.warning(f"BigQuery query execution error: {err_msg[:120]}. Running silent self-repair...")
        # Phase 2: Silent self-repair retry (H1.2: re-apply query-craft rules + re-validate SQL safety + dry-run)
        try:
            from app.tools.sql_generator import get_sql_generator
            sql_gen = get_sql_generator()
            raw_repaired = sql_gen.repair_sql(sql=safe_sql, error_message=err_msg)
            repaired_sql = sl.apply_query_craft_rules(raw_repaired)
            is_safe2, safety_err2 = sl.validate_sql_safety(repaired_sql)
            if not is_safe2:
                raise ValueError(f"Repaired SQL failed safety validation: {safety_err2}")
            ok_dry, _bytes2, dry_err2 = sl.dry_run_check(repaired_sql)
            if not ok_dry:
                raise ValueError(f"Repaired SQL failed dry-run check: {dry_err2}")
            query_job2 = sl.client.query(repaired_sql, job_config=job_config)
            result2 = query_job2.result()

            rows2: List[Dict[str, Any]] = []
            columns2 = [f.name for f in result2.schema] if result2.schema else []
            for row in result2:
                row_dict = {}
                for k, v in dict(row).items():
                    if hasattr(v, "isoformat"):
                        row_dict[k] = v.isoformat()
                    elif hasattr(v, "__float__"):
                        try:
                            row_dict[k] = float(v)
                        except Exception:
                            row_dict[k] = str(v)
                    else:
                        row_dict[k] = v
                rows2.append(row_dict)

            elapsed_sec2 = round(time.perf_counter() - t0, 3)
            det_summary2 = compute_deterministic_summary(columns=columns2, rows=rows2)
            out2 = {
                "status": "success",
                "sql": repaired_sql,
                "row_count": len(rows2),
                "columns": columns2,
                "deterministic_summary": det_summary2,
                "rows": rows2[:15],
                "all_rows": rows2,
                "total_bytes_processed": query_job2.total_bytes_processed or 0,
                "elapsed_seconds": elapsed_sec2,
                "latency_ms": round(elapsed_sec2 * 1000, 2),
                "chart_kind": "table",
                "chart_spec": None,
                "repaired": True,
            }
            if YUKTI_RESULT_CACHE:
                tool_cache.set_sql(repaired_sql, persona, out2)
            return out2
        except Exception as e2:
            logger.error(f"BigQuery silent self-repair failed: {e2}")
            # Clean natural fallback without surfacing database error messages
            return {
                "status": "error",
                "error": "Verified data not available for this query.",
                "sql": safe_sql,
                "row_count": 0,
                "rows": [],
                "columns": [],
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            }


async def query_data_async(
    sql_query: str,
    title: Optional[str] = None,
    persona: str = "CMD",
    voice_override: Optional[str] = None,
    semantic_layer: Optional[SemanticLayer] = None,
) -> Dict[str, Any]:
    """Non-blocking async wrapper for query_data (H1.1: offloads BigQuery I/O to worker thread)."""
    import asyncio
    return await asyncio.to_thread(
        query_data,
        sql_query=sql_query,
        title=title,
        persona=persona,
        voice_override=voice_override,
        semantic_layer=semantic_layer,
    )
