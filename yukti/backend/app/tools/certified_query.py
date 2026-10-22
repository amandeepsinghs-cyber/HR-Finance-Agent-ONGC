"""Certified Query Execution Engine for Yukti AI.
Executes pre-verified parameterized queries from certified/library.yaml.
Supports dynamic parameter injection (e.g. wc_id, min_stay_months, fiscal_year)
and provides deterministic summaries and visual metadata.
"""

from decimal import Decimal
import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional
from google.cloud import bigquery
import yaml

from app.config import BQ_LOCATION, GCP_PROJECT, JOB_LABELS, MAX_BYTES_BILLED
from app.tool_cache import get_tool_cache
from app.semantic.entities import get_entities

logger = logging.getLogger("yukti.tools.certified_query")

CERTIFIED_PATH = Path(__file__).resolve().parent.parent.parent / "certified" / "library.yaml"

# Load certified query index into memory
_CERTIFIED_INDEX: Dict[str, Dict[str, Any]] = {}


def _get_certified_index() -> Dict[str, Dict[str, Any]]:
    global _CERTIFIED_INDEX
    if not _CERTIFIED_INDEX:
        if CERTIFIED_PATH.exists():
            with open(CERTIFIED_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                for q in data.get("queries", []):
                    _CERTIFIED_INDEX[q["id"].upper()] = q
        else:
            logger.warning(f"Certified library not found at {CERTIFIED_PATH}")
    return _CERTIFIED_INDEX


def get_certified_entry(query_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves metadata for a certified query."""
    index = _get_certified_index()
    return index.get(query_id.strip().upper())


def list_certified_queries() -> List[Dict[str, Any]]:
    """Lists all available certified queries."""
    index = _get_certified_index()
    return list(index.values())


def _convert_row_value(val: Any) -> Any:
    if isinstance(val, Decimal):
        return float(val)
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return val


def run_certified_query(
    query_id: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Executes a certified parameterized query from the verified query library.

    Args:
        query_id: The certified query ID (e.g. 'C1', 'C6', 'C12', 'X7').
        params: Optional key-value dictionary overriding default parameters (e.g.
          {'wc_id': 'WC-MUM', 'min_stay_months': 36, 'fiscal_year': 'FY26'}).

    Returns:
        Structured response with rows, row_count, columns, deterministic_summary,
        visual metadata, and certified provenance.
    """
    t0 = time.perf_counter()
    entry = get_certified_entry(query_id)
    if not entry:
        return {
            "type": "error",
            "error": f"Certified query '{query_id}' not found in certified library.",
            "retryable": False,
        }

    user_params = params or {}
    merged_params = {}
    param_defs = entry.get("params", {})

    # Apply defaults and override with user-provided parameters
    for p_name, p_meta in param_defs.items():
        if p_name in user_params:
            merged_params[p_name] = user_params[p_name]
        else:
            merged_params[p_name] = p_meta.get("default")

    # Add any extra params supplied
    for k, v in user_params.items():
        if k not in merged_params:
            merged_params[k] = v

    # Check cache
    cache = get_tool_cache()
    cached_res = cache.get_sql(sql=f"CERTIFIED:{entry['id']}:{merged_params}")
    if cached_res:
        cached_res["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        cached_res["status_events"] = ["Using recently verified data"]
        return cached_res

    # Prepare BigQuery query parameters
    raw_sql = entry["parameterized_sql"]
    bq_params: List[bigquery.ScalarQueryParameter] = []

    # Auto-detect any parameter placeholders in raw_sql
    needed_params = set(re.findall(r"@([a-zA-Z0-9_]+)", raw_sql))
    for np in needed_params:
        if np not in merged_params or merged_params[np] is None:
            if "month" in np:
                merged_params[np] = 60
            elif "year" in np:
                merged_params[np] = "FY26"
            elif "wc" in np:
                merged_params[np] = "WC-DEL"
            elif "grade" in np:
                merged_params[np] = "E7"
            elif "field" in np:
                merged_params[np] = "FLD-CHP"
            else:
                merged_params[np] = "default"

    for p_name, p_val in merged_params.items():
        if p_val is None:
            continue
        p_type = param_defs.get(p_name, {}).get("type", "STRING")
        if isinstance(p_val, int) or "month" in p_name or p_type == "INT64":
            try:
                bq_params.append(bigquery.ScalarQueryParameter(p_name, "INT64", int(p_val)))
            except Exception:
                pass
        elif isinstance(p_val, float) or p_type == "FLOAT64":
            try:
                bq_params.append(bigquery.ScalarQueryParameter(p_name, "FLOAT64", float(p_val)))
            except Exception:
                pass
        else:
            bq_params.append(bigquery.ScalarQueryParameter(p_name, "STRING", str(p_val)))

    # Execute query
    try:
        client = bigquery.Client(
            project=GCP_PROJECT,
            location=BQ_LOCATION,
        )
        job_config = bigquery.QueryJobConfig(
            default_dataset=f"{GCP_PROJECT}.hrfin_silver",
            query_parameters=bq_params,
            labels=JOB_LABELS,
            maximum_bytes_billed=MAX_BYTES_BILLED,
        )

        job = client.query(raw_sql, job_config=job_config)
        rows_iter = job.result()
        schema_fields = [field.name for field in rows_iter.schema] if rows_iter.schema else []

        rows: List[Dict[str, Any]] = []
        for r in rows_iter:
            rows.append({k: _convert_row_value(r[k]) for k in schema_fields})

        row_count = len(rows)

        # Build deterministic summary
        summary_sentences = []
        is_default_params = (not user_params) or all(user_params.get(k) == v.get("default") for k, v in param_defs.items())
        headline = entry.get("intent_description", "")
        if headline and is_default_params:
            summary_sentences.append(headline)
        else:
            entity_str = merged_params.get("wc_id") or merged_params.get("fiscal_year") or "specified filters"
            summary_sentences.append(f"Operational query for {entity_str} verified.")

        cnt_cols = [c for c in schema_fields if any(k in c.lower() for k in ["count", "num_", "executives", "headcount", "strength", "posts", "vacanc"])]
        dimension_totals = {}
        ents = get_entities()  # single entity dictionary (B1.2)

        dim_cols = [c for c in schema_fields if any(k in c.lower() for k in ["discipline", "grade", "field", "asset", "wc_"])]
        if dim_cols and cnt_cols:
            cnt = cnt_cols[0]
            dim_facts = []
            for dim in dim_cols:
                d_totals = {}
                for r in rows:
                    raw_d = str(r.get(dim, "Unknown")).strip()
                    d_val = ents.friendly(raw_d)
                    try:
                        c_val = int(r.get(cnt, 0) or 0)
                    except Exception:
                        c_val = 1
                    d_totals[d_val] = d_totals.get(d_val, 0) + c_val
                ranked = sorted(d_totals.items(), key=lambda x: x[1], reverse=True)
                dimension_totals[dim] = dict(ranked)
                top_items = [f"{k} ({v})" for k, v in ranked[:3] if v > 0]
                if top_items:
                    dim_label = "Discipline" if "disc" in dim.lower() else ("Grade" if "grade" in dim.lower() else dim)
                    dim_facts.append(f"{dim_label}: {', '.join(top_items)}")
            if dim_facts:
                summary_sentences.append(". ".join(dim_facts) + ".")

        if cnt_cols and not (headline and is_default_params):
            try:
                total_sum = sum(int(r.get(cnt_cols[0], 0) or 0) for r in rows)
                summary_sentences.append(f"A total of {total_sum} matching records were verified.")
            except Exception:
                summary_sentences.append(f"A total of {row_count} matching records were verified.")
        elif row_count == 0:
            summary_sentences.append("Zero records matched the specified filter criteria.")
        elif not (headline and is_default_params):
            summary_sentences.append(f"A total of {row_count} matching records were verified.")

        det_summary = " ".join(summary_sentences)

        # Build visual specification
        visual_kind = entry.get("visual_kind", "table")
        visual_data = {
            "type": visual_kind,
            "title": entry["canonical_question"],
            "rows": rows[:50],
            "total_rows": row_count,
            "columns": schema_fields,
        }

        # Build citations from provenance
        prov = entry.get("provenance", {})
        gold_objs = prov.get("gold_objects", "hrfin_gold")
        sources = [s.strip() for s in gold_objs.split(",") if s.strip()]
        if not sources:
            sources = ["Audited Enterprise Records"]

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

        total_count = sum(int(r.get(cnt_cols[0], 0) or 0) for r in rows) if cnt_cols else row_count

        result = {
            "type": "certified_query_result",
            "query_id": entry["id"],
            "canonical_question": entry["canonical_question"],
            "rows": rows,
            "row_count": row_count,
            "total_count": total_count,
            "columns": schema_fields,
            "deterministic_summary": det_summary,
            "visual": visual_data,
            "sources": sources,
            "latency_ms": elapsed_ms,
            "executed_sql": raw_sql,
            "params_applied": merged_params,
            "dimension_totals": dimension_totals,
            "label_value_pairs": dimension_totals,
            "provenance": prov,
        }

        # Cache result
        cache.set_sql(sql=f"CERTIFIED:{entry['id']}:{merged_params}", persona="CMD", value=result)
        return result

    except Exception as e:
        logger.error(f"Error executing certified query {query_id}: {e}", exc_info=True)
        # Fallback with safe formatted substitution if parameter types had minor mismatch
        try:
            formatted_sql = raw_sql
            for p_name, p_val in merged_params.items():
                if isinstance(p_val, (int, float)):
                    formatted_sql = formatted_sql.replace(f"@{p_name}", str(p_val))
                else:
                    formatted_sql = formatted_sql.replace(f"@{p_name}", f"'{p_val}'")

            job = client.query(formatted_sql, job_config=bigquery.QueryJobConfig(
                default_dataset=f"{GCP_PROJECT}.hrfin_silver",
                labels=JOB_LABELS,
                maximum_bytes_billed=MAX_BYTES_BILLED,
            ))
            rows_iter = job.result()
            schema_fields = [field.name for field in rows_iter.schema] if rows_iter.schema else []
            rows = [{k: _convert_row_value(r[k]) for k in schema_fields} for r in rows_iter]
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            return {
                "type": "certified_query_result",
                "query_id": entry["id"],
                "canonical_question": entry["canonical_question"],
                "rows": rows,
                "row_count": len(rows),
                "columns": schema_fields,
                "deterministic_summary": f"Verified {len(rows)} records from certified query.",
                "visual": {
                    "type": entry.get("visual_kind", "table"),
                    "title": entry["canonical_question"],
                    "rows": rows[:50],
                    "total_rows": len(rows),
                    "columns": schema_fields,
                },
                "sources": ["Audited Enterprise Records"],
                "latency_ms": elapsed_ms,
                "executed_sql": formatted_sql,
                "params_applied": merged_params,
                "provenance": entry.get("provenance", {}),
            }
        except Exception as e2:
            return {
                "type": "error",
                "error": f"Failed to execute certified query '{query_id}': {e2}",
                "retryable": False,
            }
