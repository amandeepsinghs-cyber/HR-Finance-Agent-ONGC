-- Answer Key SQL: T3
-- Question: "Which GMs retire in 2027?" → "Who is ready to succeed each?" → "Which successors haven't served in the North East?"
-- Type: chain
-- Semantic audit 2026-10-20: Old SQL was not restricted to GMs (included the CMD and a CGM), used a 19-Oct-2026..Dec-2027 window, and only saw GMs who already have a succession_plan row (4 of 12).
-- Semantic audit 2026-10-20: Now: every active GM (E7) retiring in calendar 2027 from employee_master, LEFT JOINed to succession_plan (successor, readiness, NE flag, no-plan flag).

SELECT
    e.emp_id AS gm_emp_id,
    e.current_designation,
    e.current_wc_id,
    e.discipline_id,
    e.retirement_date,
    sp.position_id,
    sp.criticality_tier,
    sp.successor_1_emp_id,
    sp.successor_1_readiness,
    sp.successor_1_has_ne_hard_station,
    sp.position_id IS NULL AS no_succession_plan
FROM employee_master e
LEFT JOIN succession_plan sp ON sp.incumbent_emp_id = e.emp_id
WHERE LOWER(e.employment_status) = 'active'
  AND e.current_grade_id = 'E7'
  AND e.retirement_date BETWEEN DATE '2027-01-01' AND DATE '2027-12-31'
ORDER BY e.retirement_date, e.emp_id;
