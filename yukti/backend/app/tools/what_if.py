"""Parameterized What-If Scenario Engine for Yukti AI.
Implements executive what-if simulations over live BigQuery data:
1. Brent Price Shocks: Adjusts crude net realization and recalculates field operating EBITDA and PBT.
2. Recruitment Freeze: Evaluates impact of N months moratorium on natural superannuations across disciplines.
3. Relocation Outlay: Models Composite Transfer Allowance (CTA) expenditure for redeploying N executive engineers to field assets.
4. SAED Windfall Tax Removal: Models quarterly EBITDA expansion from statutory levy withdrawal.
"""

import logging
import time
from typing import Any, Dict, List, Optional
from google.cloud import bigquery

from app.config import BQ_LOCATION, GCP_PROJECT, JOB_LABELS

logger = logging.getLogger("yukti.tools.what_if")


def run_what_if_simulation(
    scenario: str,
    brent_price: Optional[float] = 60.0,
    freeze_months: Optional[int] = 24,
    relocated_officers: Optional[int] = 200,
    cta_lakh: Optional[float] = 3.25,
    persona: str = "CMD",
) -> Dict[str, Any]:
    """Runs a live parameterized what-if simulation on BigQuery."""
    t0 = time.perf_counter()
    from app.config import YUKTI_RESULT_CACHE
    from app.tool_cache import get_tool_cache
    tool_cache = get_tool_cache()

    params = {
        "brent_price": brent_price,
        "freeze_months": freeze_months,
        "relocated_officers": relocated_officers,
        "cta_lakh": cta_lakh,
    }

    if YUKTI_RESULT_CACHE:
        cached = tool_cache.get_whatif(scenario, params, persona=persona)
        if cached:
            cached_copy = dict(cached)
            cached_copy["from_cache"] = True
            cached_copy["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
            return cached_copy

    scen = scenario.lower()
    client = bigquery.Client(project=GCP_PROJECT, location=BQ_LOCATION)

    if any(k in scen for k in ["brent", "price", "crude", "w1"]):
        try:
            price = float(brent_price) if brent_price is not None and float(brent_price) > 0 else 60.0
        except Exception:
            price = 60.0
        sql = f"""WITH price_params AS (
    SELECT
        AVG(brent_usd_bbl) AS avg_brent,
        AVG(ongc_crude_net_realisation_usd_bbl) AS avg_realisation,
        AVG(brent_usd_bbl - ongc_crude_net_realisation_usd_bbl) AS avg_discount
    FROM `{GCP_PROJECT}.hrfin_silver.price_fx_monthly`
    WHERE fiscal_year IN ('FY26', '2026')
),
sim_brent AS (
    SELECT
        pnl.field_id,
        f.name AS field_name,
        f.onshore_offshore,
        pnl.gross_revenue_inr_cr AS base_revenue_cr,
        pnl.total_opex_inr_cr AS base_opex_cr,
        pnl.dda_depreciation_inr_cr AS base_dda_cr,
        (pnl.oil_revenue_inr_cr * (({price} - params.avg_discount) / params.avg_realisation) + pnl.gas_revenue_inr_cr) AS sim_gross_rev_cr,
        SAFE_DIVIDE(pnl.statutory_royalty_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0)) AS eff_royalty_rate,
        SAFE_DIVIDE(pnl.statutory_cess_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0)) AS eff_cess_rate
    FROM `{GCP_PROJECT}.hrfin_silver.field_pnl_annual` pnl
    JOIN `{GCP_PROJECT}.hrfin_silver.dim_field` f ON pnl.field_id = f.field_id
    CROSS JOIN price_params params
    WHERE pnl.fiscal_year IN ('FY26', '2026') AND pnl.line_type = 'field'
)
SELECT
    field_id,
    field_name,
    onshore_offshore,
    ROUND(sim_gross_rev_cr, 2) AS sim_gross_revenue_inr_cr,
    ROUND(base_opex_cr, 2) AS total_opex_inr_cr,
    ROUND(sim_gross_rev_cr * (1.0 - eff_royalty_rate - eff_cess_rate) - base_opex_cr, 2) AS sim_ebitda_inr_cr,
    ROUND(sim_gross_rev_cr * (1.0 - eff_royalty_rate - eff_cess_rate) - base_opex_cr - base_dda_cr, 2) AS sim_pbt_inr_cr,
    CASE WHEN (sim_gross_rev_cr * (1.0 - eff_royalty_rate - eff_cess_rate) - base_opex_cr) < 0 THEN TRUE ELSE FALSE END AS is_ebitda_negative,
    CASE WHEN (sim_gross_rev_cr * (1.0 - eff_royalty_rate - eff_cess_rate) - base_opex_cr - base_dda_cr) < 0 THEN TRUE ELSE FALSE END AS is_pbt_negative
FROM sim_brent
ORDER BY sim_pbt_inr_cr ASC;"""

    elif any(k in scen for k in ["freeze", "moratorium", "hiring", "w2"]):
        fmonths = int(freeze_months or 24)
        sql = f"""SELECT
    d.name AS discipline_name,
    COUNT(DISTINCT e.emp_id) AS current_headcount,
    COUNT(DISTINCT CASE WHEN DATE_DIFF(e.retirement_date, DATE '2026-10-19', MONTH) <= {fmonths} THEN e.emp_id END) AS retirements_during_freeze,
    0 AS external_inductions,
    COUNT(DISTINCT e.emp_id) - COUNT(DISTINCT CASE WHEN DATE_DIFF(e.retirement_date, DATE '2026-10-19', MONTH) <= {fmonths} THEN e.emp_id END) AS post_freeze_projected_headcount
FROM `{GCP_PROJECT}.hrfin_silver.employee_master` e
JOIN `{GCP_PROJECT}.hrfin_silver.dim_discipline` d ON e.discipline_id = d.discipline_id
WHERE LOWER(e.employment_status) = 'active' AND e.current_grade_id LIKE 'E%'
GROUP BY d.name
ORDER BY retirements_during_freeze DESC;"""

    elif any(k in scen for k in ["relocat", "transfer", "cta", "w3", "c13"]):
        cohort = int(relocated_officers or 200)
        rate = float(cta_lakh or 3.25)
        outlay_cr = round((cohort * rate * 100000) / 10000000, 2)
        sql = f"""SELECT
    wc.short_name AS field_asset,
    COALESCE(SUM(sp.sanctioned_strength), 0) AS sanctioned_posts,
    COALESCE(SUM(sp.in_position_strength), 0) AS in_position,
    COALESCE(SUM(sp.vacancy_count), 0) AS vacancy_deficit,
    {cohort} AS planned_executives_relocated,
    {outlay_cr} AS estimated_cta_outlay_cr
FROM `{GCP_PROJECT}.hrfin_silver.dim_work_centre` wc
LEFT JOIN `{GCP_PROJECT}.hrfin_silver.sanctioned_posts` sp ON wc.wc_id = sp.wc_id AND sp.fiscal_year IN ('FY26', '2026')
WHERE wc.hard_station_cat IN ('B', 'C') AND wc.wc_id IN ('WC-ASM', 'WC-TRI', 'WC-CAM', 'WC-RAJ')
GROUP BY wc.short_name
ORDER BY vacancy_deficit DESC;"""

    else:  # SAED / Windfall Tax (W4)
        sql = f"""SELECT
    fiscal_year,
    ROUND(AVG(brent_usd_bbl), 2) AS brent_usd,
    ROUND(AVG(windfall_tax_saed_usd_bbl), 2) AS erstwhile_saed_usd,
    ROUND(AVG(ongc_crude_net_realisation_usd_bbl), 2) AS post_withdrawal_net_realisation_usd,
    ROUND(AVG(windfall_tax_saed_usd_bbl * 75.0 * 83.5 / 10000000), 2) AS estimated_monthly_ebitda_gain_inr_cr
FROM `{GCP_PROJECT}.hrfin_silver.price_fx_monthly`
WHERE fiscal_year IN ('FY24', 'FY25', 'FY26')
GROUP BY fiscal_year
ORDER BY fiscal_year DESC;"""

    try:
        job = client.query(sql, job_config=bigquery.QueryJobConfig(labels=JOB_LABELS))
        raw_rows = [dict(r) for r in job.result()]
        columns = [f.name for f in job.result().schema] if job.result().schema else []

        # Convert Decimal and dates to JSON-serializable types for ADK / Gemini
        clean_rows = []
        for r in raw_rows:
            clean_r = {}
            for k, v in r.items():
                if hasattr(v, "isoformat"):
                    clean_r[k] = v.isoformat()
                elif hasattr(v, "__float__"):
                    try:
                        clean_r[k] = float(v)
                    except Exception:
                        clean_r[k] = str(v)
                else:
                    clean_r[k] = v
            clean_rows.append(clean_r)

        out = {
            "status": "success",
            "scenario": scenario,
            "simulated_brent_price": price if "price" in locals() else None,
            "sql": sql,
            "row_count": len(clean_rows),
            "columns": columns,
            "rows": clean_rows[:25],
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        }
        if YUKTI_RESULT_CACHE:
            tool_cache.set_whatif(scenario, params, persona, out)
        return out
    except Exception as e:
        logger.exception(f"Error executing what-if simulation: {e}")
        return {
            "status": "error",
            "error": str(e),
            "sql": sql,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        }
