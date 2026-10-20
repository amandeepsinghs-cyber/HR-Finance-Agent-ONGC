-- Answer Key Follow-up SQL: H1__compare_or_so_what
-- Question: How does the tenure compliance rate in Corporate HQ Delhi compare with field assets like Ankleshwar and Cambay?
-- Type: data
-- Semantic audit 2026-10-20: old SQL mixed non-executives into the rate and had no company benchmark. Now: share of active
-- executives at each named work centre whose current station stay is <=3 years (JRTP 3.1 compliant), plus company-wide row.
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
    COUNT(*) AS active_executives,
    COUNTIF(NOT ae.over_3_years) AS within_3y,
    COUNTIF(ae.over_3_years) AS over_3y,
    ROUND(COUNTIF(NOT ae.over_3_years) * 100.0 / COUNT(*), 1) AS tenure_compliance_pct
FROM active_execs ae
JOIN dim_work_centre wc ON wc.wc_id = ae.wc_id
WHERE wc.short_name IN ('Delhi HQ', 'Ankleshwar Asset', 'Cambay Asset')
GROUP BY wc.short_name
UNION ALL
SELECT 'All work centres', COUNT(*), COUNTIF(NOT over_3_years), COUNTIF(over_3_years),
       ROUND(COUNTIF(NOT over_3_years) * 100.0 / COUNT(*), 1)
FROM active_execs
ORDER BY tenure_compliance_pct;
