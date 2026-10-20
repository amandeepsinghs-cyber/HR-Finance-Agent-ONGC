-- Answer Key Follow-up SQL: E1__drill_down
-- Question: Break down my current leave balances across Earned Leave (EL), Half Pay Leave (HPL), and Casual Leave (CL).
-- Type: data
-- Semantic audit 2026-10-20: Shows all three asked leave types; HPL and CL are absent from the ledger for this employee (GAP) and now surface as NULL instead of silently disappearing.

WITH asked AS (
    SELECT leave_type FROM UNNEST(['Earned_Leave_EL', 'Half_Pay_Leave_HPL', 'Casual_Leave_CL']) AS leave_type
),
latest AS (
    SELECT fiscal_year, leave_type, closing_balance_days
    FROM leave_ledger
    WHERE emp_id = 'EMP-102451'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY leave_type ORDER BY fiscal_year DESC, to_date DESC) = 1
)
SELECT
    a.leave_type,
    l.fiscal_year,
    l.closing_balance_days,
    l.leave_type IS NOT NULL AS recorded_in_ledger
FROM asked a
LEFT JOIN latest l ON l.leave_type = a.leave_type
ORDER BY a.leave_type;
