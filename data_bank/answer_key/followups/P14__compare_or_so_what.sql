-- Answer Key Follow-up SQL: P14__compare_or_so_what
-- Question: What is the estimated monetary difference in PRP payout for an E5 Manager and an E7 General Manager?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Old SQL repeated the MoU parameter list. Now FY26 average annual PRP per full-time-equivalent
-- Semantic audit 2026-10-20: (payroll rows / 12) for E5 and E7, at Excellent basis vs Very Good (x0.875), and the per-head loss.
SELECT
    p.grade_id,
    ROUND(COUNT(*) / 12, 0) AS avg_monthly_headcount_paid,
    ROUND(SUM(p.prp_inr) / (COUNT(*) / 12), 0) AS prp_per_fte_excellent_inr,
    ROUND(0.875 * SUM(p.prp_inr) / (COUNT(*) / 12), 0) AS prp_per_fte_very_good_inr,
    ROUND(0.125 * SUM(p.prp_inr) / (COUNT(*) / 12), 0) AS loss_per_fte_inr,
    ROUND(100 * SUM(p.prp_inr) / SUM(p.basic_pay_inr), 2) AS prp_pct_of_basic
FROM payroll_monthly p
WHERE p.fiscal_year = 'FY26' AND p.grade_id IN ('E5', 'E7')
GROUP BY p.grade_id
ORDER BY p.grade_id;
