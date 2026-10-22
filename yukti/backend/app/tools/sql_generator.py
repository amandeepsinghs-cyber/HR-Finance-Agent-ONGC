"""Dedicated Live NL->SQL Generation Engine for Yukti AI.
Executes on gemini-3.8-flash with thinking_level='low' for rigorous,
high-precision BigQuery SQL authoring with automated silent self-repair.
Keeps the primary voice/text agent lightweight and fast.
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from google import genai
from google.genai import types

from app.config import (
    BQ_LOCATION,
    GCP_PROJECT,
    JOB_LABELS,
    MAX_BYTES_BILLED,
    VERTEX_TEXT_LOCATION,
)
from app.tools.semantic_layer import SEMANTIC_LAYER_PROMPT

logger = logging.getLogger("yukti.sql_generator")

SQL_GEN_MODEL = "gemini-3.8-flash"


class DedicatedSQLGenerator:
    """Specialized NL->SQL engine using thinking reasoning and silent self-repair."""

    def __init__(
        self,
        project_id: str = GCP_PROJECT,
        location: str = VERTEX_TEXT_LOCATION,
        model_name: str = SQL_GEN_MODEL,
    ):
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        self._client: Optional[genai.Client] = None
        self._bq_client = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location=self.location,
            )
        return self._client

    @property
    def bq_client(self):
        if self._bq_client is None:
            from google.cloud import bigquery
            self._bq_client = bigquery.Client(
                project=self.project_id,
                location=BQ_LOCATION,
            )
        return self._bq_client

    def _extract_sql_from_response(self, text: str) -> str:
        """Extracts SQL query string from markdown code fence or raw text."""
        code_block = re.search(r"```(?:sql)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if code_block:
            sql = code_block.group(1).strip()
        else:
            lines = [l for l in text.strip().splitlines() if not l.startswith("#")]
            sql = "\n".join(lines).strip()

        # Remove trailing semicolon
        sql = sql.rstrip(";").strip()
        return sql

    def generate_sql(
        self,
        query: str,
        active_query_state: Optional[Dict[str, Any]] = None,
        context_hint: Optional[str] = None,
    ) -> str:
        """Generates a clean BigQuery SQL query using gemini-3.8-flash thinking."""
        prompt_parts = [
            f"You are the senior BigQuery SQL engineer for ONGC enterprise data ({self.project_id}).",
            f"Generate a single, clean, highly-optimized BigQuery SQL query to answer the question.",
            SEMANTIC_LAYER_PROMPT,
        ]

        if active_query_state:
            prev_sql = active_query_state.get("sql", "")
            prev_params = active_query_state.get("params", {})
            if prev_sql:
                prompt_parts.append(
                    f"\nACTIVE CONVERSATION QUERY CONTEXT:\nPrevious Query SQL: {prev_sql}\nActive Parameters: {prev_params}\n"
                    "If this is a follow-up (e.g. drill-down, entity change, new filter), modify or build upon the previous query rather than starting from scratch."
                )

        if context_hint:
            prompt_parts.append(f"\nCONTEXT HINT:\n{context_hint}")

        prompt_parts.append(
            f"\nUSER INQUIRY:\n{query}\n\n"
            "INSTRUCTIONS:\n"
            "- Output ONLY the BigQuery SQL inside a ```sql code block.\n"
            "- Never explain, never apologize, never output comments outside the block.\n"
            "- Strictly obey the 5 Query-Craft rules (recompute weighted per-barrel ratios, LOWER on categoricals, exact column catalog).\n"
        )

        full_prompt = "\n".join(prompt_parts)

        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level="low"),
            temperature=0.0,
        )

        res = self.client.models.generate_content(
            model=self.model_name,
            contents=full_prompt,
            config=config,
        )

        return self._extract_sql_from_response(res.text or "")

    def repair_sql(self, sql: str, error_message: str) -> str:
        """Performs 1 silent self-repair on a query that failed BigQuery validation."""
        repair_prompt = f"""You are the senior BigQuery SQL engineer for ONGC enterprise data ({self.project_id}).
The following SQL query failed during BigQuery execution:

FAILED SQL:
```sql
{sql}
```

BIGQUERY ERROR MESSAGE:
{error_message}

{SEMANTIC_LAYER_PROMPT}

TASK:
Correct the SQL query to resolve the exact BigQuery error.
Ensure all referenced column and table names match the catalog above.
Output ONLY the corrected SQL inside a ```sql code block.
"""
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level="low"),
            temperature=0.0,
        )
        res = self.client.models.generate_content(
            model=self.model_name,
            contents=repair_prompt,
            config=config,
        )
        return self._extract_sql_from_response(res.text or "")

    def execute_with_silent_repair(
        self,
        query: str,
        active_query_state: Optional[Dict[str, Any]] = None,
        given_sql: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generates SQL (or takes given SQL) and executes on BigQuery with 1 silent retry."""
        t0 = time.perf_counter()

        sql = given_sql or self.generate_sql(query, active_query_state=active_query_state)

        from google.cloud import bigquery
        job_config = bigquery.QueryJobConfig(
            default_dataset=f"{self.project_id}.hrfin_silver",
            labels=JOB_LABELS,
            maximum_bytes_billed=MAX_BYTES_BILLED,
        )

        # Attempt 1
        try:
            job = self.bq_client.query(sql, job_config=job_config)
            rows_iter = job.result()
            schema_fields = [f.name for f in rows_iter.schema] if rows_iter.schema else []
            rows = [{k: r[k] for k in schema_fields} for r in rows_iter]

            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            logger.info(f"Dedicated SQL Generator executed successfully in {elapsed_ms}ms ({len(rows)} rows)")
            return {
                "status": "success",
                "sql": sql,
                "rows": rows,
                "row_count": len(rows),
                "columns": schema_fields,
                "latency_ms": elapsed_ms,
                "repaired": False,
            }
        except Exception as e1:
            err_str = str(e1)
            logger.warning(f"SQL execution Attempt 1 failed: {err_str[:120]}. Running silent self-repair...")

            # Attempt 2: Silent Self-Repair
            try:
                repaired_sql = self.repair_sql(sql=sql, error_message=err_str)
                job2 = self.bq_client.query(repaired_sql, job_config=job_config)
                rows_iter2 = job2.result()
                schema_fields2 = [f.name for f in rows_iter2.schema] if rows_iter2.schema else []
                rows2 = [{k: r[k] for k in schema_fields2} for r in rows_iter2]

                elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
                logger.info(f"Dedicated SQL Generator silent self-repair SUCCEEDED in {elapsed_ms}ms ({len(rows2)} rows)")
                return {
                    "status": "success",
                    "sql": repaired_sql,
                    "rows": rows2,
                    "row_count": len(rows2),
                    "columns": schema_fields2,
                    "latency_ms": elapsed_ms,
                    "repaired": True,
                }
            except Exception as e2:
                logger.error(f"SQL execution Attempt 2 (repair) failed: {e2}")
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
                # Return clean structured fallback without surfacing raw DB tracebacks to user
                return {
                    "status": "error",
                    "sql": sql,
                    "error": "Verified data not available for this query.",
                    "raw_error": str(e2)[:100],
                    "rows": [],
                    "row_count": 0,
                    "columns": [],
                    "latency_ms": elapsed_ms,
                    "repaired": False,
                }


_GLOBAL_SQL_GEN: Optional[DedicatedSQLGenerator] = None


def get_sql_generator() -> DedicatedSQLGenerator:
    """Singleton getter for DedicatedSQLGenerator."""
    global _GLOBAL_SQL_GEN
    if _GLOBAL_SQL_GEN is None:
        _GLOBAL_SQL_GEN = DedicatedSQLGenerator()
    return _GLOBAL_SQL_GEN
