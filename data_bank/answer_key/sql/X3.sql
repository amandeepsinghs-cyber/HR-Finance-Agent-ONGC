-- Answer Key SQL: X3
-- Question: Do assets with higher offshore overtime show a higher lost-time injury rate?
-- Type: data
-- Semantic audit 2026-10-20: Answers the yes/no directly: pooled LTIFR (LTIs x 1e6 / man-hours) for the high-overtime (54 h/month,
-- offshore) vs standard (36 h) bands, FY26 and FY22-FY26 (5 full years, equal coverage). Old SQL listed 46 work centres
-- with an average of monthly LTIFRs and never compared the bands.
SELECT
    CASE WHEN h.monthly_overtime_hours_per_worker >= 50 THEN 'High overtime (54 h/month, offshore)' ELSE 'Standard overtime (36 h/month)' END AS overtime_band,
    MAX(h.monthly_overtime_hours_per_worker) AS overtime_hours_per_worker_month,
    COUNT(DISTINCT h.wc_id) AS work_centres,
    COUNTIF(h.fiscal_year = 'FY26' AND h.lost_time_injury_flag) AS ltis_fy26,
    ROUND(SUM(IF(h.fiscal_year = 'FY26', h.total_manhours_worked, 0)) / 1e6, 2) AS million_manhours_fy26,
    ROUND(COUNTIF(h.fiscal_year = 'FY26' AND h.lost_time_injury_flag) * 1e6 / SUM(IF(h.fiscal_year = 'FY26', h.total_manhours_worked, 0)), 3) AS ltifr_fy26,
    COUNTIF(h.lost_time_injury_flag) AS ltis_fy22_fy26,
    ROUND(SUM(h.total_manhours_worked) / 1e6, 2) AS million_manhours_fy22_fy26,
    ROUND(COUNTIF(h.lost_time_injury_flag) * 1e6 / SUM(h.total_manhours_worked), 3) AS ltifr_fy22_fy26,
    COUNTIF(h.lost_time_injury_flag AND h.fatigue_factor_flag) AS fatigue_linked_ltis_fy22_fy26
FROM hse_incidents h
WHERE h.fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26')
GROUP BY overtime_band
ORDER BY overtime_hours_per_worker_month DESC;
