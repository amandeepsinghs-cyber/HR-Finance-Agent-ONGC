-- Answer Key Follow-up SQL: C12__compare_or_so_what
-- Question: How does ONGC's overall manpower cost per BOE compare with Indian peer upstream operators (e.g. Oil India Limited)?
-- Type: data
-- Semantic audit 2026-10-20: old SQL returned revenue, opex and LIFTING cost per BOE for all years - not
-- manpower cost. GAP: no peer (Oil India or other operator) data exists in hrfin_silver/gold/docs, so the peer
-- comparison cannot be answered from the data. Closest honest result: ONGC's own company-level manpower cost
-- per BOE FY21-FY26 (corporate_financials.employee_cost_total_inr_cr x 1e7 / production_monthly BOE, all 12
-- months per FY) in INR and USD (dim_price_fx FY average), next to lifting cost for context.

WITH prod AS (
    SELECT fiscal_year, SUM(total_production_boe) AS boe, COUNT(DISTINCT month) AS months
    FROM production_monthly
    WHERE fiscal_year IN ('FY21', 'FY22', 'FY23', 'FY24', 'FY25', 'FY26')
    GROUP BY 1
),
fx AS (
    SELECT fiscal_year, AVG(inr_usd_fx_rate) AS fx
    FROM dim_price_fx
    WHERE fiscal_year IN ('FY21', 'FY22', 'FY23', 'FY24', 'FY25', 'FY26')
    GROUP BY 1
)
SELECT
    cf.fiscal_year,
    cf.employee_cost_total_inr_cr,
    ROUND(prod.boe / 1e6, 2) AS mmboe,
    prod.months,
    ROUND(cf.employee_cost_total_inr_cr * 1e7 / NULLIF(prod.boe, 0), 0) AS manpower_cost_inr_per_boe,
    ROUND(cf.employee_cost_total_inr_cr * 1e7 / NULLIF(prod.boe, 0) / fx.fx, 2) AS manpower_cost_usd_per_boe,
    ROUND(fx.fx, 2) AS inr_usd,
    cf.lifting_cost_average_usd_boe,
    CAST(NULL AS NUMERIC) AS peer_manpower_cost_usd_per_boe
FROM corporate_financials cf
JOIN prod ON prod.fiscal_year = cf.fiscal_year
JOIN fx ON fx.fiscal_year = cf.fiscal_year
ORDER BY cf.fiscal_year;
