-- Answer Key Follow-up SQL: P13__compare_or_so_what
-- Question: How much financial headroom in crore remains under the 30% cap based on the FY26 executive payroll?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Old SQL listed retiree payouts by scheme (no headroom, no executive filter). Now FY26 payroll_monthly
-- Semantic audit 2026-10-20: split by cadre (dim_grade): employer superannuation contribution vs 30% of (Basic+DA), headroom in crore.
SELECT
    CASE LOWER(g.cadre) WHEN 'executive' THEN 'Executives E1-E9' WHEN 'non_executive' THEN 'Non-executives' ELSE 'Board' END AS cadre_group,
    COUNT(DISTINCT p.emp_id) AS employees_paid,
    ROUND(SUM(p.basic_pay_inr + p.da_inr) / 1e7, 1) AS basic_plus_da_cr,
    ROUND(SUM(p.superannuation_benefit_pct / 100 * (p.basic_pay_inr + p.da_inr)) / 1e7, 1) AS employer_super_contribution_cr,
    ROUND(100 * SUM(p.superannuation_benefit_pct / 100 * (p.basic_pay_inr + p.da_inr)) / SUM(p.basic_pay_inr + p.da_inr), 2) AS employer_super_pct,
    ROUND(0.30 * SUM(p.basic_pay_inr + p.da_inr) / 1e7, 1) AS cap_amount_cr,
    ROUND((0.30 * SUM(p.basic_pay_inr + p.da_inr) - SUM(p.superannuation_benefit_pct / 100 * (p.basic_pay_inr + p.da_inr))) / 1e7, 1) AS headroom_cr
FROM payroll_monthly p
JOIN dim_grade g ON g.grade_id = p.grade_id
WHERE p.fiscal_year = 'FY26'
GROUP BY 1
ORDER BY headroom_cr DESC;
