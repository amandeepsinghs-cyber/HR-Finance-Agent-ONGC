-- Answer Key SQL: E1
-- Question: What is my leave balance, and how many earned leave days can I encash?
-- Type: data
-- Semantic audit 2026-10-20: Latest ledger row per leave type (no hard-coded FY), plus in-service encashment per Leave Rules 4.3 (up to 30 days, retain 30) next to the ledger field.

WITH latest AS (
    SELECT fiscal_year, leave_type, closing_balance_days, encashable_balance_days
    FROM leave_ledger
    WHERE emp_id = 'EMP-102451'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY leave_type ORDER BY fiscal_year DESC, to_date DESC) = 1
)
SELECT
    fiscal_year,
    leave_type,
    closing_balance_days,
    encashable_balance_days AS encashable_days_per_ledger,
    IF(LOWER(leave_type) = 'earned_leave_el', LEAST(30, GREATEST(closing_balance_days - 30, 0)), NULL) AS in_service_encashable_per_rule_4_3
FROM latest
ORDER BY leave_type;
