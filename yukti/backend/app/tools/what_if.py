"""Parameterized What-If Scenario Engine for Yukti AI.
Implements executive what-if simulations over live BigQuery data:
1. Brent Price Shocks: Adjusts crude net realization and recalculates field operating EBITDA and PBT.
2. Recruitment Freeze: Evaluates impact of N months moratorium on natural superannuations across disciplines.
3. Relocation Outlay: Models Composite Transfer Allowance (CTA) expenditure for redeploying N executive engineers to field assets.
4. SAED Windfall Tax Removal: Models quarterly EBITDA expansion from statutory levy withdrawal.
"""

import logging
import os
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
        pnl.field_name,
        pnl.onshore_offshore,
        COALESCE(pnl.recomputed_gross_revenue_inr_cr, pnl.gross_revenue_inr_cr) AS base_revenue_cr,
        pnl.total_opex_inr_cr AS base_opex_cr,
        pnl.dda_depreciation_inr_cr AS base_dda_cr,
        (pnl.oil_revenue_inr_cr * (({price} - params.avg_discount) / params.avg_realisation) + pnl.gas_revenue_inr_cr) AS sim_gross_rev_cr,
        SAFE_DIVIDE(pnl.statutory_royalty_inr_cr, NULLIF(COALESCE(pnl.recomputed_gross_revenue_inr_cr, pnl.gross_revenue_inr_cr), 0)) AS eff_royalty_rate,
        SAFE_DIVIDE(pnl.statutory_cess_inr_cr, NULLIF(COALESCE(pnl.recomputed_gross_revenue_inr_cr, pnl.gross_revenue_inr_cr), 0)) AS eff_cess_rate
    FROM `{GCP_PROJECT}.hrfin_gold.ssot_field_economics_360` pnl
    CROSS JOIN price_params params
    WHERE pnl.fiscal_year IN ('FY26', '2026') AND pnl.field_id IS NOT NULL
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
        from app.config import rewrite_dataset_sql
        sql = rewrite_dataset_sql(sql)
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
        if os.getenv("YUKTI_FORCE_BQ_FAIL", "0") not in ("1", "true", "yes"):
            try:
                import csv as _csv
                import datetime as _dt
                import pandas as _pd
                import yaml as _yaml
                from app.config import DATA_BANK_DIR
                from app.semantic.entities import get_entities
                ents = get_entities()
                fb_rows = []
                if any(k in scen for k in ["brent", "price", "crude", "w1"]):
                    copa_v3_p = DATA_BANK_DIR / "landing" / "sap" / "CO_PA_v3.csv"
                    pfx_p = DATA_BANK_DIR / "landing" / "excel" / "_clean" / "price_fx.xlsx"
                    if not pfx_p.exists():
                        pfx_p = DATA_BANK_DIR / "landing" / "excel" / "price_fx.xlsx"
                    co_p = DATA_BANK_DIR / "world_bible" / "reference" / "cost_objects.yaml"
                    if copa_v3_p.exists() and pfx_p.exists():
                        pfx_df = _pd.read_excel(pfx_p, sheet_name="price_fx_monthly")
                        pfx_26 = pfx_df[pfx_df["fiscal_year"] == "FY26"]
                        if not pfx_26.empty:
                            avg_brent = float(pfx_26["brent_usd_bbl"].mean())
                            avg_real = float(pfx_26["ongc_crude_net_realisation_usd_bbl"].mean())
                            avg_disc = avg_brent - avg_real
                            p_val = float(price) if "price" in locals() else 60.0

                            co_map = {}
                            if co_p.exists():
                                co_raw = _yaml.safe_load(co_p.read_text(encoding="utf-8")) or {}
                                for co in co_raw.get("cost_objects") or []:
                                    if co.get("object_id"):
                                        co_map[str(co["object_id"])] = co

                            opex_codes = {
                                "N35.STAFF_EXPENDITURE", "N35.WORKOVER_OPS", "N35.WATER_INJECTION_DESALTING",
                                "N35.CONSUMPTION_STORES_SPARES", "N35.POLLUTION_CONTROL", "N35.TRANSPORT_EXPENDITURE",
                                "N35.INSURANCE", "N35.POWER_FUEL", "N35.REPAIRS_MAINTENANCE", "N35.CONTRACTUAL_HIRE",
                                "N35.OTHER_PRODUCTION_EXP", "N35.TRANSPORT_FREIGHT_PRODUCTS", "N35.R_AND_D",
                                "N35.GAE", "N35.CSR", "N35.EXCHANGE_LOSS", "N35.MISC_EXP", "N35.FV_LOSS",
                            }
                            non_oil_rev_codes = {"REV.GAS", "REV.VAP", "REV.OTHER_OP"}
                            # [oil_rev_mn, non_oil_rev_mn, royalty_mn, cess_mn, opex_mn, dda_mn]
                            f_acc = {}
                            with copa_v3_p.open("r", encoding="utf-8") as f:
                                for r in _csv.DictReader(f):
                                    if str(r.get("fy") or "").strip() != "FY26":
                                        continue
                                    oid = str(r.get("object_id") or "").strip()
                                    co = co_map.get(oid, {})
                                    otype = str(co.get("object_type") or r.get("object_type") or "").lower()
                                    if otype != "field":
                                        continue
                                    lc = str(r.get("line_code") or "").strip().upper()
                                    amt = float(r.get("amount_inr_mn") or 0.0)
                                    acc = f_acc.setdefault(oid, [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
                                    if lc == "REV.CRUDE":
                                        acc[0] += amt
                                    elif lc in non_oil_rev_codes:
                                        acc[1] += amt
                                    elif lc == "N35.ROYALTY":
                                        acc[2] += amt
                                    elif lc == "N35.OIDB_CESS":
                                        acc[3] += amt
                                    elif lc in opex_codes:
                                        acc[4] += amt
                                    elif lc == "PL.DDA":
                                        acc[5] += amt

                            for oid, acc in f_acc.items():
                                co = co_map.get(oid, {})
                                oil_rev = acc[0] / 10.0
                                gas_rev = acc[1] / 10.0
                                gross_rev = oil_rev + gas_rev
                                if gross_rev <= 0 or avg_real <= 0:
                                    continue
                                roy_rate = (acc[2] / 10.0) / gross_rev
                                cess_rate = (acc[3] / 10.0) / gross_rev
                                opex = acc[4] / 10.0
                                dda = acc[5] / 10.0
                                sim_rev = round(oil_rev * ((p_val - avg_disc) / avg_real) + gas_rev, 2)
                                sim_ebitda = round(sim_rev * (1.0 - roy_rate - cess_rate) - opex, 2)
                                sim_pbt = round(sim_ebitda - dda, 2)
                                fb_rows.append({
                                    "field_id": oid,
                                    "field_name": str(co.get("object_name") or ents.friendly(oid)),
                                    "onshore_offshore": str(co.get("segment") or "onshore").lower(),
                                    "sim_gross_revenue_inr_cr": sim_rev,
                                    "total_opex_inr_cr": round(opex, 2),
                                    "sim_ebitda_inr_cr": sim_ebitda,
                                    "sim_pbt_inr_cr": sim_pbt,
                                    "is_ebitda_negative": sim_ebitda < 0,
                                    "is_pbt_negative": sim_pbt < 0,
                                })
                            fb_rows.sort(key=lambda x: float(x["sim_pbt_inr_cr"]))
                elif any(k in scen for k in ["freeze", "moratorium", "hiring", "w2"]):
                    pa2_p = DATA_BANK_DIR / "landing" / "sap" / "PA0002_PA0001.csv"
                    if pa2_p.exists():
                        fmonths = int(freeze_months or 24)
                        by_d = {}
                        for r in _csv.DictReader(pa2_p.open("r", encoding="utf-8")):
                            if r.get("STAT2") != "Active" or not str(r.get("PERSK", "")).startswith("E"):
                                continue
                            dname = ents.friendly(r.get("discipline_id", ""))
                            rec = by_d.setdefault(dname, [0, 0])
                            rec[0] += 1
                            ret_s = r.get("retirement_date")
                            if ret_s and (_dt.date.fromisoformat(ret_s) - _dt.date(2026, 10, 19)).days <= fmonths * 30.4375:
                                rec[1] += 1
                        for dname, (tot_hc, ret_hc) in sorted(by_d.items(), key=lambda kv: -kv[1][1]):
                            fb_rows.append({
                                "discipline_name": dname,
                                "current_headcount": tot_hc,
                                "retirements_during_freeze": ret_hc,
                                "external_inductions": 0,
                                "post_freeze_projected_headcount": tot_hc - ret_hc,
                            })
                elif any(k in scen for k in ["relocat", "transfer", "cta", "w3", "c13"]):
                    mp_p = DATA_BANK_DIR / "landing" / "excel" / "_clean" / "manpower_plan.xlsx"
                    if not mp_p.exists():
                        mp_p = DATA_BANK_DIR / "landing" / "excel" / "manpower_plan.xlsx"
                    if mp_p.exists():
                        cohort = int(relocated_officers or 200)
                        rate = float(cta_lakh or 3.25)
                        outlay_cr = round((cohort * rate * 100000) / 10000000, 2)
                        mp_df = _pd.read_excel(mp_p)
                        target_wcs = ["WC-ASM", "WC-TRI", "WC-CAM", "WC-RAJ"]
                        sub_mp = mp_df[(mp_df["fiscal_year"] == "FY26") & (mp_df["wc_id"].isin(target_wcs))]
                        if not sub_mp.empty:
                            grp = sub_mp.groupby("wc_id", as_index=False)[
                                ["sanctioned_strength", "in_position_strength", "vacancy_count"]
                            ].sum()
                            for _, r in grp.iterrows():
                                wcid = str(r["wc_id"])
                                fb_rows.append({
                                    "field_asset": ents.friendly(wcid),
                                    "sanctioned_posts": int(r["sanctioned_strength"]),
                                    "in_position": int(r["in_position_strength"]),
                                    "vacancy_deficit": int(r["vacancy_count"]),
                                    "planned_executives_relocated": cohort,
                                    "estimated_cta_outlay_cr": outlay_cr,
                                })
                            fb_rows.sort(key=lambda x: -int(x["vacancy_deficit"]))
                else:
                    pfx_p = DATA_BANK_DIR / "landing" / "excel" / "_clean" / "price_fx.xlsx"
                    if not pfx_p.exists():
                        pfx_p = DATA_BANK_DIR / "landing" / "excel" / "price_fx.xlsx"
                    copa_v3_p = DATA_BANK_DIR / "landing" / "sap" / "CO_PA_v3.csv"
                    if pfx_p.exists() and copa_v3_p.exists():
                        pfx_df = _pd.read_excel(pfx_p, sheet_name="price_fx_monthly")
                        saed_by_fy = {"FY24": 0.0, "FY25": 0.0, "FY26": 0.0}
                        with copa_v3_p.open("r", encoding="utf-8") as f:
                            for r in _csv.DictReader(f):
                                fy_r = str(r.get("fy") or "").strip()
                                if fy_r in saed_by_fy and str(r.get("line_code") or "").strip().upper() == "N35.EXCISE_SAED":
                                    saed_by_fy[fy_r] += float(r.get("amount_inr_mn") or 0.0)
                        for fy_k in ["FY26", "FY25", "FY24"]:
                            sub_pf = pfx_df[pfx_df["fiscal_year"] == fy_k]
                            if sub_pf.empty:
                                continue
                            fb_rows.append({
                                "fiscal_year": fy_k,
                                "brent_usd": round(float(sub_pf["brent_usd_bbl"].mean()), 2),
                                "erstwhile_saed_usd": round(float(sub_pf["windfall_tax_saed_usd_bbl"].mean()), 2),
                                "post_withdrawal_net_realisation_usd": round(float(sub_pf["ongc_crude_net_realisation_usd_bbl"].mean()), 2),
                                "estimated_monthly_ebitda_gain_inr_cr": round((saed_by_fy.get(fy_k, 0.0) / 10.0) / 12.0, 2),
                            })
                if fb_rows:
                    out = {
                        "status": "success",
                        "scenario": scenario,
                        "simulated_brent_price": price if "price" in locals() else None,
                        "sql": sql,
                        "row_count": len(fb_rows),
                        "columns": list(fb_rows[0].keys()),
                        "rows": fb_rows[:25],
                        "source": "local_snapshot",
                        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                    }
                    if YUKTI_RESULT_CACHE:
                        tool_cache.set_whatif(scenario, params, persona, out)
                    return out
            except Exception:
                pass
        logger.exception(f"Error executing what-if simulation: {e}")
        return {
            "status": "error",
            "error": str(e),
            "sql": sql,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        }
