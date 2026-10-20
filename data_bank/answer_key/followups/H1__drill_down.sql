-- Answer Key Follow-up SQL: H1__drill_down
-- Question: How many of these executives are in non-executive and junior executive grades (E1–E4) versus senior management (E6–E9)?
-- Type: data
-- Semantic audit 2026-10-20: old SQL grouped by dim_grade.group (every executive is 'Group A' -> one meaningless row) and
-- included non-executives. Now: same population as corrected H1 (active executives >3y at current station) banded
-- E0 / E1-E4 / E5 / E6-E9 with share of the band's active executives.
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
, banded AS (
    SELECT *,
        CASE
            WHEN grade_id = 'E0' THEN '1. E0 (trainee)'
            WHEN grade_id IN ('E1', 'E2', 'E3', 'E4') THEN '2. E1-E4 (junior/middle)'
            WHEN grade_id = 'E5' THEN '3. E5 (DGM)'
            ELSE '4. E6-E9 (senior management)'
        END AS grade_band
    FROM active_execs
)
SELECT
    grade_band,
    COUNTIF(over_3_years) AS executives_over_3y,
    COUNT(*) AS active_executives_in_band,
    ROUND(COUNTIF(over_3_years) * 100.0 / COUNT(*), 1) AS pct_of_band_over_3y,
    ROUND(COUNTIF(over_3_years) * 100.0 / SUM(COUNTIF(over_3_years)) OVER (), 1) AS share_of_over_3y_pct
FROM banded
GROUP BY grade_band
ORDER BY grade_band;
