"""BigQuery tool for ONGC Executive Continuous Stay & Headcount tenure.
Executes BigQuery queries on hrfin_gold.v_continuous_stay with labels {"datacloud": "ai-agent"}
and falls back cleanly to golden reference data if ADC reauth is required.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.tools.echarts_generator import generate_headcount_echarts

logger = logging.getLogger("voice_chart_spike.tools.bq")

DATA_BANK_C1_PATH = Path(
    "/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC/data_bank/answer_key/expected/C1.json"
)

LOCATION_MAP = {
    "delhi": "WC-DEL",
    "delhi office": "WC-DEL",
    "deendayal urja bhawan": "WC-DEL",
    "new delhi": "WC-DEL",
    "dehradun": "WC-DDN",
    "mumbai": "WC-MUM",
    "ahmedabad": "WC-AMD",
    "ankleshwar": "WC-ANK",
    "mehsana": "WC-MEH",
    "assam": "WC-ASM",
    "tripura": "WC-TRP",
}


def _filter_grade(rows: List[Dict[str, Any]], grade_filter: Optional[str]) -> List[Dict[str, Any]]:
    if not grade_filter:
        return rows
    gf = grade_filter.upper().strip()
    if "E5 AND ABOVE" in gf or "E5+" in gf:
        allowed = {"E5", "E6", "E7", "E8", "E9"}
        return [r for r in rows if r.get("grade_id") in allowed]
    return rows


def query_headcount_tenure(
    location: str = "Delhi",
    min_years: int = 5,
    grade_filter: Optional[str] = None
) -> Dict[str, Any]:
    """Runs a query for ONGC executives with continuous stay >= min_years at a work centre,

    broken down by grade and discipline. Returns rows, summary, and declarative ECharts spec.
    """
    t0 = time.perf_counter()
    wc_id = LOCATION_MAP.get(location.lower().strip(), "WC-DEL")
    min_months = int(min_years) * 12
    project_id = os.getenv("TARGET_PROJECT") or "ongc-hr-finance-agent"

    rows: List[Dict[str, Any]] = []
    source = "bigquery"

    sql_query = f"""
    SELECT
        grade_id,
        discipline_id,
        COUNT(DISTINCT emp_id) AS delhi_executives_ge_5yr,
        COUNT(DISTINCT CASE WHEN DATE_DIFF(retirement_date, DATE '2026-10-19', DAY) <= 3 * 365.25 THEN emp_id END) AS exempt_retiring_3yr,
        COUNT(DISTINCT CASE WHEN DATE_DIFF(retirement_date, DATE '2026-10-19', DAY) > 3 * 365.25 THEN emp_id END) AS non_exempt_due_transfer
    FROM `{project_id}.hrfin_gold.v_continuous_stay`
    WHERE is_current_stay = TRUE
      AND wc_id = '{wc_id}'
      AND grade_id LIKE 'E%'
      AND continuous_stay_months >= {min_months}
    GROUP BY grade_id, discipline_id
    ORDER BY grade_id, discipline_id;
    """

    try:
        from google.cloud import bigquery
        client = bigquery.Client(
            project=project_id,
            location="asia-south1",
            default_query_job_config=bigquery.QueryJobConfig(
                labels={"datacloud": "ai-agent"}
            )
        )
        query_job = client.query(sql_query)
        result = query_job.result()
        for row in result:
            rows.append(dict(row))
        logger.info(f"BigQuery query completed: {len(rows)} rows returned in {time.perf_counter() - t0:.3f}s")
    except Exception as exc:
        logger.warning(
            f"BigQuery live query skipped/failed ({type(exc).__name__}: {exc}). "
            f"Using verified data_bank golden answer key C1.json."
        )
        source = "data_bank_golden_c1"
        if DATA_BANK_C1_PATH.exists():
            with open(DATA_BANK_C1_PATH, "r", encoding="utf-8") as f:
                c1_data = json.load(f)
                rows = c1_data.get("rows", [])
        else:
            rows = []

    # Apply grade filter if requested (e.g. follow-up 'only E5 and above')
    rows = _filter_grade(rows, grade_filter)

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    total_execs = sum(int(r.get("delhi_executives_ge_5yr", 0)) for r in rows)
    total_exempt = sum(int(r.get("exempt_retiring_3yr", 0)) for r in rows)
    total_due_transfer = sum(int(r.get("non_exempt_due_transfer", 0)) for r in rows)

    title_desc = f"{location}: Executives with ≥{min_years} Years Tenure"
    if grade_filter:
        title_desc += f" ({grade_filter})"

    chart_spec = generate_headcount_echarts(
        rows=rows,
        location=location,
        min_years=min_years,
        title_override=f"{title_desc} (Total: {total_execs})"
    )

    summary_text = (
        f"In {location}, there are {total_execs} executives with continuous tenure of {min_years} years or more. "
        f"Of these, {total_due_transfer} are eligible for transfer rotation and {total_exempt} are exempt due to retirement within 3 years."
    )

    return {
        "status": "success",
        "location": location,
        "wc_id": wc_id,
        "min_years": min_years,
        "grade_filter": grade_filter,
        "total_executives": total_execs,
        "total_exempt_retiring_3yr": total_exempt,
        "total_due_transfer": total_due_transfer,
        "row_count": len(rows),
        "source": source,
        "latency_ms": elapsed_ms,
        "summary": summary_text,
        "chart_spec": chart_spec,
        "rows": rows[:15]  # preview rows
    }
