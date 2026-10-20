-- Answer Key Follow-up SQL: W2__compare_or_so_what
-- Question: How would a hiring freeze impact our statutory reservation rosters and succession bench strength by FY28?
-- Type: what_if
-- Semantic audit 2026-10-20: Old SQL returned one total executive retirement % - nothing on reservation rosters or succession bench.
-- Semantic audit 2026-10-20: Now: to end-FY28 (31-Mar-2028), by reservation category (whole workforce) and by leadership-pipeline grade E5-E9: current, retirements, projected, and share before/after.

WITH a AS (
    SELECT * FROM employee_master WHERE LOWER(employment_status) = 'active'
),
g AS (
    SELECT 'reservation_category' AS dimension, a.category AS group_name,
           COUNT(*) AS current_headcount, COUNTIF(a.retirement_date BETWEEN DATE '2026-10-20' AND DATE '2028-03-31') AS retirements_by_fy28
    FROM a GROUP BY a.category
    UNION ALL
    SELECT 'succession_bench_grade', a.current_grade_id,
           COUNT(*), COUNTIF(a.retirement_date BETWEEN DATE '2026-10-20' AND DATE '2028-03-31')
    FROM a WHERE a.current_grade_id IN ('E5', 'E6', 'E7', 'E8', 'E9') GROUP BY a.current_grade_id
)
SELECT
    dimension,
    group_name,
    current_headcount,
    retirements_by_fy28,
    current_headcount - retirements_by_fy28 AS projected_fy28,
    ROUND(retirements_by_fy28 * 100.0 / NULLIF(current_headcount, 0), 1) AS attrition_pct,
    ROUND(current_headcount * 100.0 / SUM(current_headcount) OVER (PARTITION BY dimension), 2) AS current_share_pct,
    ROUND((current_headcount - retirements_by_fy28) * 100.0
          / SUM(current_headcount - retirements_by_fy28) OVER (PARTITION BY dimension), 2) AS projected_share_pct
FROM g
ORDER BY dimension, group_name;
