-- Answer Key Follow-up SQL: X10__why
-- Question: What specific maintenance or compressor downtime event caused the 12% lifting cost spike in Field X this week?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL hard-coded FLD-CAM monthly downtime with no link to lifting cost. Now the fields with the largest
-- FY26 vs FY25 lifting-cost change next to their well-downtime and uptime change (production_monthly, 12 vs 12 months).
-- GAP: no weekly cost or compressor-event data; no field shows a 12% rise.
WITH f AS (
    SELECT field_id, fiscal_year, lifting_cost_per_boe_usd, total_production_boe
    FROM field_pnl_annual
    WHERE LOWER(line_type) = 'field' AND fiscal_year IN ('FY25', 'FY26')
),
lift AS (
    SELECT a.field_id, d.name AS field_name, a.lifting_cost_per_boe_usd AS lifting_fy25_usd_boe,
        b.lifting_cost_per_boe_usd AS lifting_fy26_usd_boe,
        ROUND((b.lifting_cost_per_boe_usd - a.lifting_cost_per_boe_usd) * 100 / a.lifting_cost_per_boe_usd, 1) AS lifting_change_pct
    FROM f a
    JOIN f b ON a.field_id = b.field_id AND a.fiscal_year = 'FY25' AND b.fiscal_year = 'FY26'
    LEFT JOIN dim_field d ON d.field_id = a.field_id
),
ops AS (
    SELECT field_id,
        SUM(IF(fiscal_year = 'FY25', well_downtime_hours, 0)) AS downtime_fy25_h,
        SUM(IF(fiscal_year = 'FY26', well_downtime_hours, 0)) AS downtime_fy26_h,
        AVG(IF(fiscal_year = 'FY25', operational_uptime_pct, NULL)) AS uptime_fy25_pct,
        AVG(IF(fiscal_year = 'FY26', operational_uptime_pct, NULL)) AS uptime_fy26_pct,
        SUM(IF(fiscal_year = 'FY25', total_production_boe, 0)) AS boe_fy25,
        SUM(IF(fiscal_year = 'FY26', total_production_boe, 0)) AS boe_fy26
    FROM production_monthly
    WHERE fiscal_year IN ('FY25', 'FY26')
    GROUP BY field_id
)
SELECT
    l.field_name,
    l.lifting_fy25_usd_boe,
    l.lifting_fy26_usd_boe,
    l.lifting_change_pct,
    ROUND((o.boe_fy26 - o.boe_fy25) * 100 / NULLIF(o.boe_fy25, 0), 1) AS production_change_pct,
    ROUND(o.downtime_fy26_h - o.downtime_fy25_h, 1) AS downtime_change_hours,
    ROUND(o.uptime_fy26_pct - o.uptime_fy25_pct, 2) AS uptime_change_pp
FROM lift l
LEFT JOIN ops o ON o.field_id = l.field_id
ORDER BY l.lifting_change_pct DESC
LIMIT 10;
