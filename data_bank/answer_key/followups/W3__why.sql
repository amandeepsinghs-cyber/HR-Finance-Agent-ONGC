-- Answer Key Follow-up SQL: W3__why
-- Question: Why does shifting senior technical officers from corporate headquarters directly improve field maintenance and facility uptime?
-- Type: what_if
-- Semantic audit 2026-10-20: Old SQL listed the 10 B/C work centres with the fewest technical staff (LIMIT 10, absolute counts) - no link to maintenance or uptime.
-- Semantic audit 2026-10-20: Now: per producing asset, FY26 technical-executive vacancy rate vs operational uptime and well downtime per well-month, with the cross-asset correlation (tests the causal claim).

WITH vac AS (
    SELECT s.wc_id, SUM(s.sanctioned_strength) AS sanc, SUM(s.vacancy_count) AS vac
    FROM sanctioned_posts s
    JOIN dim_discipline d ON d.discipline_id = s.discipline_id
    WHERE s.fiscal_year = 'FY26' AND LOWER(s.grade_band) != 'non_executive' AND LOWER(d.function) = 'technical'
    GROUP BY s.wc_id
),
ops AS (
    SELECT asset_wc_id AS wc_id,
           AVG(operational_uptime_pct) AS uptime,
           SUM(well_downtime_hours) / NULLIF(SUM(active_producing_wells), 0) AS downtime_per_well_month
    FROM production_monthly
    WHERE fiscal_year = 'FY26'
    GROUP BY asset_wc_id
)
SELECT
    w.short_name AS asset,
    ROUND(vac.vac * 100.0 / vac.sanc, 1) AS technical_exec_vacancy_pct,
    ROUND(ops.uptime, 2) AS fy26_uptime_pct,
    ROUND(ops.downtime_per_well_month, 1) AS downtime_hrs_per_well_month,
    ROUND(CORR(vac.vac / vac.sanc, ops.uptime) OVER (), 2) AS corr_vacancy_vs_uptime,
    ROUND(CORR(vac.vac / vac.sanc, ops.downtime_per_well_month) OVER (), 2) AS corr_vacancy_vs_downtime
FROM ops
JOIN vac USING (wc_id)
JOIN dim_work_centre w USING (wc_id)
ORDER BY technical_exec_vacancy_pct DESC, asset;
