-- Answer Key Follow-up SQL: P14__drill_down
-- Question: What is the percentage reduction in the total distributable PRP corpus across E1–E9 grades between 'Excellent' and 'Very Good'?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Old SQL repeated the MoU parameter list (no PRP corpus). Now FY26 PRP outgo per executive grade
-- Semantic audit 2026-10-20: (payroll_monthly) at Excellent basis vs Very Good (MoU component 50% x 75% eligibility -> 87.5% of pool).
SELECT
    p.grade_id,
    ROUND(COUNT(*) / 12, 0) AS avg_monthly_headcount_paid,
    ROUND(SUM(p.prp_inr) / 1e7, 2) AS prp_excellent_basis_cr,
    ROUND(SUM(p.prp_inr) * 0.875 / 1e7, 2) AS prp_very_good_cr,
    ROUND(SUM(p.prp_inr) * 0.125 / 1e7, 2) AS reduction_cr,
    -12.5 AS reduction_pct
FROM payroll_monthly p
JOIN dim_grade g ON g.grade_id = p.grade_id
WHERE p.fiscal_year = 'FY26' AND LOWER(g.cadre) = 'executive'
GROUP BY p.grade_id
ORDER BY p.grade_id;
