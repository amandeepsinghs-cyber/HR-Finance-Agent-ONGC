-- Answer Key Follow-up SQL: X3__drill_down
-- Question: Which offshore platforms in Mumbai High and Neelam-Heera recorded the highest monthly overtime hours per technician?
-- Type: data
-- Semantic audit 2026-10-20: FY26 (last full year) per installation for Mumbai High and Neelam & Heera: overtime per worker, LTIs,
-- man-hours, pooled LTIFR. Old SQL averaged over FY22-FY27 with no period filter.
-- GAP: hse_incidents has one installation per asset ('<asset> Installation') and a single overtime value (54 h) for all
-- offshore assets; platform- and technician-level overtime is not recorded.
SELECT
    h.installation_name,
    w.short_name,
    AVG(h.monthly_overtime_hours_per_worker) AS overtime_hours_per_worker_month_fy26,
    COUNTIF(h.lost_time_injury_flag) AS ltis_fy26,
    ROUND(SUM(h.total_manhours_worked) / 1e6, 2) AS million_manhours_fy26,
    ROUND(COUNTIF(h.lost_time_injury_flag) * 1e6 / SUM(h.total_manhours_worked), 3) AS ltifr_fy26
FROM hse_incidents h
JOIN dim_work_centre w ON h.wc_id = w.wc_id
WHERE h.wc_id IN ('WC-MUM', 'WC-NEH') AND h.fiscal_year = 'FY26'
GROUP BY h.installation_name, w.short_name
ORDER BY overtime_hours_per_worker_month_fy26 DESC, ltifr_fy26 DESC;
