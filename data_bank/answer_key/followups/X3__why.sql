-- Answer Key Follow-up SQL: X3__why
-- Question: What role does fatigue from extended shift overtime play in near-misses and Lost Time Injuries (LTI)?
-- Type: data
-- Semantic audit 2026-10-20: Covers both near-misses and LTIs (old SQL counted only LTIs over all years incl. partial FY27, ignoring
-- near-misses and overtime). FY22-FY26 incident counts, fatigue-flagged counts and rate per million man-hours by overtime band.
WITH b AS (
    SELECT
        incident_type,
        CASE WHEN monthly_overtime_hours_per_worker >= 50 THEN 'High overtime (54 h)' ELSE 'Standard overtime (36 h)' END AS overtime_band,
        fatigue_factor_flag,
        total_manhours_worked
    FROM hse_incidents
    WHERE fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26')
),
mh AS (
    SELECT overtime_band, SUM(total_manhours_worked) AS band_manhours FROM b GROUP BY overtime_band
)
SELECT
    b.incident_type,
    b.overtime_band,
    COUNT(*) AS incidents_fy22_fy26,
    COUNTIF(b.fatigue_factor_flag) AS fatigue_flagged_fy22_fy26,
    ROUND(COUNTIF(b.fatigue_factor_flag) * 100 / COUNT(*), 1) AS fatigue_flagged_pct,
    ROUND(COUNT(*) * 1e6 / ANY_VALUE(mh.band_manhours), 3) AS incidents_per_million_manhours
FROM b
JOIN mh USING (overtime_band)
WHERE LOWER(b.incident_type) IN ('lost_time_injury_lti', 'near_miss')
GROUP BY b.incident_type, b.overtime_band
ORDER BY b.incident_type, b.overtime_band;
