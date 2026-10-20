-- Answer Key Follow-up SQL: D1__compare_or_so_what
-- Question: How does my own total compensation compare to the midpoint of the E2 pay scale band?
-- Type: refusal
-- Semantic audit 2026-10-20: Old SQL joined every payroll month (62 rows) and returned only the E2 midpoint repeated - never the employee's pay (JOIN_FANOUT/WRONG_QUESTION).
-- Semantic audit 2026-10-20: Now: latest payslip (basic + gross) vs the E2 IDA band (min/max/midpoint) in one row.

WITH me AS (
    SELECT month, grade_id, basic_pay_inr, da_inr, gross_salary_inr
    FROM payroll_monthly
    WHERE emp_id = 'EMP-102451'
    QUALIFY ROW_NUMBER() OVER (ORDER BY month DESC) = 1
)
SELECT
    me.month AS payslip_month,
    me.grade_id,
    g.pay_scale_min_inr,
    g.pay_scale_max_inr,
    (g.pay_scale_min_inr + g.pay_scale_max_inr) / 2.0 AS band_midpoint_inr,
    me.basic_pay_inr,
    me.da_inr,
    me.gross_salary_inr,
    ROUND(me.basic_pay_inr * 100.0 / ((g.pay_scale_min_inr + g.pay_scale_max_inr) / 2.0), 1) AS basic_pct_of_midpoint,
    ROUND((me.basic_pay_inr - g.pay_scale_min_inr) * 100.0 / (g.pay_scale_max_inr - g.pay_scale_min_inr), 1) AS basic_position_in_band_pct,
    ROUND(me.gross_salary_inr * 100.0 / ((g.pay_scale_min_inr + g.pay_scale_max_inr) / 2.0), 1) AS gross_pct_of_midpoint
FROM me
JOIN dim_grade g ON g.grade_id = 'E2';
