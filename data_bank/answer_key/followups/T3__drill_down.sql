-- Answer Key Follow-up SQL: T3__drill_down
-- Question: List the 47 E7+ officers retiring in FY27–FY29, highlighting the 11 critical operational roles with succession gaps.
-- Type: chain
-- Semantic audit 2026-10-20: Old SQL counted succession_plan positions by role/readiness for all years (no FY27-FY29 window, no E7+ list, no gap flag).
-- Semantic audit 2026-10-20: Now: every active E7+ officer retiring between 19-Oct-2026 and 31-Mar-2029 (rest of FY27-FY29) with retirement FY, plan position, tier and a succession-gap flag (no plan or no Ready-Now successor).

SELECT
    e.emp_id,
    e.current_grade_id AS grade_id,
    e.current_designation,
    e.current_wc_id,
    e.discipline_id,
    e.retirement_date,
    CONCAT('FY', FORMAT('%02d', MOD(EXTRACT(YEAR FROM DATE_ADD(e.retirement_date, INTERVAL 9 MONTH)), 100))) AS retirement_fy,
    sp.position_id,
    sp.criticality_tier,
    sp.successor_1_readiness,
    sp.successor_2_readiness,
    (sp.position_id IS NULL
     OR NOT (LOWER(IFNULL(sp.successor_1_readiness, '')) = 'ready_now' OR LOWER(IFNULL(sp.successor_2_readiness, '')) = 'ready_now')) AS succession_gap
FROM employee_master e
LEFT JOIN succession_plan sp ON sp.incumbent_emp_id = e.emp_id
WHERE LOWER(e.employment_status) = 'active'
  AND e.current_grade_id IN ('E7', 'E8', 'E9')
  AND e.retirement_date BETWEEN DATE '2026-10-19' AND DATE '2029-03-31'
ORDER BY succession_gap DESC, e.retirement_date, e.emp_id;
