-- Answer Key Follow-up SQL: C2__drill_down
-- Question: What is the discipline-wise deficit in Assam Asset (Nazira/Sivasagar) and Tripura Asset (Agartala) versus sanctioned posts?
-- Type: data
-- Semantic audit 2026-10-20: previous SQL counted employees by discipline with no sanctioned-post comparison
-- (no deficit at all) and included separated staff (no employment_status filter). Now FY26 sanctioned vs
-- in-position executive strength (E-grades) by discipline from sanctioned_posts for WC-ASM and WC-TRI,
-- with the current active executive count from employee_master as a cross-check.

WITH sp AS (
    SELECT wc_id, discipline_id,
           SUM(sanctioned_strength) AS exec_sanctioned,
           SUM(in_position_strength) AS exec_in_position,
           SUM(vacancy_count) AS exec_deficit
    FROM sanctioned_posts
    WHERE fiscal_year = 'FY26'
      AND wc_id IN ('WC-ASM', 'WC-TRI')
      AND grade_id LIKE 'E%'
    GROUP BY wc_id, discipline_id
),
em AS (
    SELECT current_wc_id AS wc_id, discipline_id, COUNT(DISTINCT emp_id) AS active_executives_today
    FROM employee_master
    WHERE current_wc_id IN ('WC-ASM', 'WC-TRI')
      AND current_grade_id LIKE 'E%'
      AND LOWER(employment_status) = 'active'
    GROUP BY 1, 2
)
SELECT
    wc.short_name,
    d.name AS discipline_name,
    sp.exec_sanctioned,
    sp.exec_in_position,
    sp.exec_deficit,
    ROUND(sp.exec_deficit * 100.0 / NULLIF(sp.exec_sanctioned, 0), 1) AS deficit_pct,
    em.active_executives_today
FROM sp
JOIN dim_work_centre wc ON sp.wc_id = wc.wc_id
JOIN dim_discipline d ON sp.discipline_id = d.discipline_id
LEFT JOIN em ON em.wc_id = sp.wc_id AND em.discipline_id = sp.discipline_id
ORDER BY sp.exec_deficit DESC, wc.short_name, d.name;
