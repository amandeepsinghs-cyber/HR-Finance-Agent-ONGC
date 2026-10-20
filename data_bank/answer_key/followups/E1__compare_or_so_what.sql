-- Answer Key Follow-up SQL: E1__compare_or_so_what
-- Question: What would be the gross monetary value of encashing 30 days of earned leave based on my current basic pay and DA?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL joined every leave_ledger row and silently capped at 18 days (LEAST(30, encashable)) - the question asks for 30 days.
-- Semantic audit 2026-10-20: Now: Leave Rules 4.2 formula (Basic + DA)/30 x 30 days, and separately x ledger-encashable days.

WITH pay AS (
    SELECT month, basic_pay_inr, da_inr
    FROM payroll_monthly
    WHERE emp_id = 'EMP-102451'
    QUALIFY ROW_NUMBER() OVER (ORDER BY month DESC) = 1
),
el AS (
    SELECT closing_balance_days, encashable_balance_days
    FROM leave_ledger
    WHERE emp_id = 'EMP-102451' AND LOWER(leave_type) = 'earned_leave_el'
    QUALIFY ROW_NUMBER() OVER (ORDER BY fiscal_year DESC, to_date DESC) = 1
)
SELECT
    pay.month AS payslip_month,
    pay.basic_pay_inr,
    pay.da_inr,
    ROUND((pay.basic_pay_inr + pay.da_inr) / 30.0, 2) AS leave_salary_per_day_inr,
    30 AS days_requested,
    ROUND((pay.basic_pay_inr + pay.da_inr) / 30.0 * 30, 2) AS gross_value_30_days_inr,
    el.closing_balance_days AS el_balance_days,
    el.encashable_balance_days AS ledger_encashable_days,
    ROUND((pay.basic_pay_inr + pay.da_inr) / 30.0 * LEAST(30, el.encashable_balance_days), 2) AS gross_value_ledger_cap_inr
FROM pay CROSS JOIN el;
