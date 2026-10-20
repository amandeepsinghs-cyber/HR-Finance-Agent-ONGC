-- Answer Key Follow-up SQL: C5__drill_down
-- Question: What is the projected cumulative superannuation count in Geology, Geophysics, and Reservoir Engineering by FY30?
-- Type: data
-- Semantic audit 2026-10-20: old SQL grouped by individual date of birth (719 rows of count = 1), so no
-- cumulative projection was visible. Now: active executives in Geology, Geophysics (Surface + Wells) and
-- Reservoir by superannuation fiscal year (Indian FY from retirement_date, FY27 = remainder from 2026-10-19)
-- through FY30, with the running cumulative total per discipline.

WITH r AS (
    SELECT
        CASE WHEN e.discipline_id IN ('DISC-GPS', 'DISC-GPW') THEN 'Geophysics' ELSE d.name END AS discipline,
        CONCAT('FY', FORMAT_DATE('%y', DATE_ADD(e.retirement_date, INTERVAL 9 MONTH))) AS retirement_fy,
        e.emp_id
    FROM employee_master e
    JOIN dim_discipline d ON e.discipline_id = d.discipline_id
    WHERE e.discipline_id IN ('DISC-GEO', 'DISC-GPS', 'DISC-GPW', 'DISC-RES')
      AND e.current_grade_id LIKE 'E%'
      AND LOWER(e.employment_status) = 'active'
      AND e.retirement_date BETWEEN DATE '2026-10-19' AND DATE '2030-03-31'
)
SELECT
    discipline,
    retirement_fy,
    COUNT(DISTINCT emp_id) AS superannuations,
    SUM(COUNT(DISTINCT emp_id)) OVER (PARTITION BY discipline ORDER BY retirement_fy) AS cumulative_to_date
FROM r
GROUP BY discipline, retirement_fy
ORDER BY discipline, retirement_fy;
