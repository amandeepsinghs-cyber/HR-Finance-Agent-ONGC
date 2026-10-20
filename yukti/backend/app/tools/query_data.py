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

    # Group / Rank by primary dimension (e.g. grade_id, field_name, discipline_id)
    dim_cols = [c for c in columns if any(k in c.lower() for k in ["grade", "discipline", "field", "asset", "wc_", "city", "state"])]
    if dim_cols and count_cols:
        dim = dim_cols[0]
        cnt = count_cols[0]
        dim_totals: Dict[str, int] = {}
        for r in rows:
            d_val = str(r.get(dim, "Unknown"))
            try:
                c_val = int(r.get(cnt, 0) or 0)
            except Exception:
                c_val = 1
            dim_totals[d_val] = dim_totals.get(d_val, 0) + c_val

        # Sort descending
        ranked = sorted(dim_totals.items(), key=lambda x: x[1], reverse=True)
        summary["ranked_by_" + dim] = [{"name": k, "count": v} for k, v in ranked[:5]]
        top_str = ", ".join(f"{k} {v}" for k, v in ranked[:3])
        summary["top_ranked_text"] = f"Largest groups: {top_str}"

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

    # 4. Direct Execution with maximum_bytes_billed cap (eliminates dry-run overhead per latency plan)
    try:
        job_config = bigquery.QueryJobConfig(
            labels=JOB_LABELS,
            maximum_bytes_billed=MAX_BYTES_BILLED,
        )
        query_job = sl.client.query(safe_sql, job_config=job_config)
        result = query_job.result()

        rows: List[Dict[str, Any]] = []
        columns = [f.name for f in result.schema] if result.schema else []

        for row in result:
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
            rows.append(row_dict)

        elapsed_sec = round(time.perf_counter() - t0, 3)
        elapsed_ms = round(elapsed_sec * 1000, 2)
        total_bytes = query_job.total_bytes_processed or 0

        # 4. Deterministic summary arithmetic in Python
        det_summary = compute_deterministic_summary(columns=columns, rows=rows)

        # 5. Determine chart selection per UX Spec §6
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

    except Exception as e:
        logger.warning(f"BigQuery query execution error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "sql": safe_sql,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        }
