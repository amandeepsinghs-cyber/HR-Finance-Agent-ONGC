-- Probe ID: E1.drill_down
-- Parent ID: E1
-- Answer Type: sql
-- Question: Break down my current leave balances across Earned Leave (EL), Half Pay Leave (HPL), and Casual Leave (CL).
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: leave_ledger
-- Drill Dims: leave_ledger.leave_type
-- Story IDs: S38
-- Expected Output: table
-- Handcrafted: false

SELECT
    leave_ledger.leave_type,
    leave_ledger.closing_balance_days AS closing_balance_days
FROM leave_ledger
WHERE leave_ledger.emp_id = 'EMP-102451' AND leave_ledger.leave_type IN ('Earned_Leave_EL', 'Half_Pay_Leave_HPL', 'Casual_Leave_CL')
ORDER BY leave_ledger.leave_type
LIMIT 100;
