-- Answer Key Follow-up SQL: W2__drill_down
-- Question: What will be the net deficit in Drilling, Reservoir, and Production engineering disciplines by 2028?
-- Type: what_if
-- Semantic audit 2026-10-20: Old SQL listed 5 disciplines (added GEO, GPS) and never computed a deficit against sanctioned strength.
-- Semantic audit 2026-10-20: Now: Drilling, Reservoir, Production executives - FY26 sanctioned executive posts, current, retirements to Oct-2028, projected, and net deficit vs sanctioned.

WITH cur AS (
    SELECT e.discipline_id,
           COUNT(DISTINCT e.emp_id) AS exec_now,
           COUNT(DISTINCT IF(e.retirement_date BETWEEN DATE '2026-10-20' AND DATE '2028-10-19', e.emp_id, NULL)) AS retirements
    FROM employee_master e
    WHERE LOWER(e.employment_status) = 'active' AND e.current_grade_id LIKE 'E%'
      AND e.discipline_id IN ('DISC-DRL', 'DISC-RES', 'DISC-PRD')
    GROUP BY e.discipline_id
),
san AS (
    SELECT discipline_id, SUM(sanctioned_strength) AS sanctioned
    FROM sanctioned_posts
    WHERE fiscal_year = 'FY26' AND LOWER(grade_band) != 'non_executive'
      AND discipline_id IN ('DISC-DRL', 'DISC-RES', 'DISC-PRD')
    GROUP BY discipline_id
)
SELECT
    d.discipline_id,
    d.name AS discipline_name,
    san.sanctioned AS sanctioned_exec_posts,
    cur.exec_now AS current_executives,
    san.sanctioned - cur.exec_now AS current_deficit,
    cur.retirements AS retirements_by_oct2028,
    cur.exec_now - cur.retirements AS projected_executives_oct2028,
    san.sanctioned - (cur.exec_now - cur.retirements) AS net_deficit_oct2028,
    ROUND((san.sanctioned - (cur.exec_now - cur.retirements)) * 100.0 / NULLIF(san.sanctioned, 0), 1) AS deficit_pct_of_sanctioned
FROM cur
JOIN san USING (discipline_id)
JOIN dim_discipline d ON d.discipline_id = cur.discipline_id
ORDER BY net_deficit_oct2028 DESC;
