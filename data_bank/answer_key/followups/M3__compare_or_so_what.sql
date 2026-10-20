-- Answer Key Follow-up SQL: M3__compare_or_so_what
-- Question: What is the designated salary pay scale and promotion criteria for employee 104523's grade?
-- Type: refusal
-- Semantic audit 2026-10-20: Old SQL hard-coded grade E3; employee EMP-104523 is actually in GRP-C (non-executive).
-- Semantic audit 2026-10-20: Now: looks up the employee's grade and returns only grade-level (public) pay band and promotion criteria plus the next grade - no individual pay.

SELECT
    g.grade_id,
    g.cadre,
    g.designation,
    g.pay_scale_min_inr,
    g.pay_scale_max_inr,
    g.scale_type,
    g.promotion_mode,
    g.typical_residency_years,
    g.dpc_evaluation_type,
    nxt.grade_id AS next_grade_id,
    nxt.designation AS next_grade_designation
FROM employee_master e
JOIN dim_grade g ON g.grade_id = e.current_grade_id
LEFT JOIN dim_grade nxt ON nxt.level_order = g.level_order - 1 AND LOWER(nxt.cadre) = LOWER(g.cadre)
WHERE e.emp_id = 'EMP-104523';
