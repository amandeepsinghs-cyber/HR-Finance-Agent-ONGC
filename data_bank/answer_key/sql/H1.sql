-- Answer Key SQL: H1
-- Question: List the executives with more than 3 years at their current station (rotation policy), by asset and grade.
-- Type: data
-- Semantic audit 2026-10-20: old SQL counted ALL current executives per WC/grade (no tenure test, LIMIT 20). Now: active executives
-- (cadre='executive') whose continuous stay at the current work centre began more than 3 years before 2026-10-19
-- (posting islands, so in-place promotions do not reset station tenure); all WC x grade rows, no LIMIT.
WITH numbered_postings AS (
    SELECT
        p.emp_id, p.wc_id, p.from_date, p.is_current_posting, p.grade_id,
        -- exemption columns hold the literal string 'None' when no exemption exists
        IF(LOWER(IFNULL(p.exemption_tag, 'none')) IN ('none', ''), NULL, p.exemption_tag) AS exemption_tag,
        IF(LOWER(IFNULL(p.exemption_reason_code, 'none')) IN ('none', ''), NULL, p.exemption_reason_code) AS exemption_reason_code,
        ROW_NUMBER() OVER (PARTITION BY p.emp_id ORDER BY p.from_date, p.posting_id) -
        ROW_NUMBER() OVER (PARTITION BY p.emp_id, p.wc_id ORDER BY p.from_date, p.posting_id) AS island_id
    FROM posting_history p
),
current_station AS (
    -- continuous stay at the current work centre (in-place promotions do not reset station tenure)
    SELECT
        emp_id, wc_id,
        MIN(from_date) AS station_from_date,
        MAX(IF(is_current_posting, grade_id, NULL)) AS grade_id,
        MAX(IF(is_current_posting, exemption_tag, NULL)) AS exemption_tag,
        MAX(IF(is_current_posting, exemption_reason_code, NULL)) AS exemption_reason_code
    FROM numbered_postings
    GROUP BY emp_id, wc_id, island_id
    HAVING LOGICAL_OR(is_current_posting)
),
active_execs AS (
    SELECT cs.*, e.age_years, e.discipline_id,
           DATE_DIFF(DATE '2026-10-19', cs.station_from_date, MONTH) AS station_tenure_months,
           cs.station_from_date < DATE_SUB(DATE '2026-10-19', INTERVAL 3 YEAR) AS over_3_years
    FROM current_station cs
    JOIN dim_grade g ON g.grade_id = cs.grade_id
    JOIN employee_master e ON e.emp_id = cs.emp_id
    WHERE LOWER(g.cadre) = 'executive'
      AND LOWER(e.employment_status) = 'active'
)
SELECT
    wc.short_name AS work_centre,
    wc.hard_station_cat,
    ae.grade_id,
    COUNT(*) AS executives_over_3y,
    ROUND(AVG(ae.station_tenure_months) / 12, 1) AS avg_station_years,
    COUNTIF(ae.exemption_tag IS NOT NULL) AS with_recorded_exemption,
    SUM(COUNT(*)) OVER (PARTITION BY wc.short_name) AS work_centre_total_over_3y,
    SUM(COUNT(*)) OVER () AS company_total_over_3y,
    (SELECT COUNT(*) FROM active_execs) AS company_active_executives
FROM active_execs ae
JOIN dim_work_centre wc ON wc.wc_id = ae.wc_id
WHERE ae.over_3_years
GROUP BY wc.short_name, wc.hard_station_cat, ae.grade_id
ORDER BY work_centre_total_over_3y DESC, wc.short_name, executives_over_3y DESC;
