-- Answer Key Follow-up SQL: H8__drill_down
-- Question: What were the average training man-days completed at ONGC Academy (Dehradun), IOGPT, and KDMIPE by discipline?
-- Type: data
-- Semantic audit 2026-10-20: old SQL averaged days per record over ALL fiscal years and all employees. Now: FY26 only,
-- executives, man-days per participant at ONGC Academy, IOGPT and KDMIPE by discipline.
SELECT
    tr.institute,
    d.name AS discipline,
    COUNT(DISTINCT tr.emp_id) AS participants,
    SUM(tr.training_days) AS man_days,
    ROUND(SUM(tr.training_days) / COUNT(DISTINCT tr.emp_id), 2) AS man_days_per_participant
FROM training_records tr
JOIN employee_master e ON tr.emp_id = e.emp_id
JOIN dim_grade g ON g.grade_id = e.current_grade_id
JOIN dim_discipline d ON e.discipline_id = d.discipline_id
WHERE tr.fiscal_year = 'FY26'
  AND LOWER(g.cadre) = 'executive'
  AND tr.institute IN ('ONGC_Academy_Dehradun', 'IOGPT_Navi_Mumbai', 'KDMIPE')
GROUP BY tr.institute, d.name
ORDER BY tr.institute, man_days_per_participant DESC, discipline;
