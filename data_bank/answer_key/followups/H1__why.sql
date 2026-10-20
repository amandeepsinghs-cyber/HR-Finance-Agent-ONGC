-- Answer Key Follow-up SQL: H1__why
-- Question: What operational dependencies or retention justifications have kept these officers beyond their 3-year tenure?
-- Type: data
-- Semantic audit 2026-10-20: old SQL only counted rows with an exemption tag (MAX over the whole island, ~1 row) and ignored
-- that most overstayers have no justification. Now: every active executive >3y at current station classified (priority order)
-- into recorded exemption / age 57+ pre-retirement protection (JRTP 7.1) / critical technical cadre within 5-yr extension
-- (JRTP 3.3: Drilling, Reservoir, Production) / within 3-5 yr window / beyond 5 yrs - no justification recorded.
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
, classified AS (
    SELECT ae.*,
        CASE
            WHEN ae.exemption_tag IS NOT NULL THEN CONCAT('Recorded exemption: ', ae.exemption_tag, ' (', IFNULL(ae.exemption_reason_code, 'n/a'), ')')
            WHEN ae.age_years >= 57 THEN 'Age 57+ pre-retirement protection (JRTP 7.1), no exemption recorded'
            WHEN LOWER(d.name) IN ('drilling', 'reservoir', 'production') AND ae.station_tenure_months <= 60
                THEN 'Critical technical cadre within 5-yr extension (JRTP 3.3)'
            WHEN ae.station_tenure_months <= 60 THEN 'Within 3-5 yr rotation window, no justification recorded'
            ELSE 'Beyond 5 yrs, no justification recorded'
        END AS retention_basis
    FROM active_execs ae
    LEFT JOIN dim_discipline d ON d.discipline_id = ae.discipline_id
    WHERE ae.over_3_years
)
SELECT
    retention_basis,
    COUNT(*) AS executives,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS share_pct,
    ROUND(AVG(station_tenure_months) / 12, 1) AS avg_station_years
FROM classified
GROUP BY retention_basis
ORDER BY executives DESC;
