-- Probe ID: E1
-- Parent ID: None
-- Answer Type: sql
-- Question: What is my leave balance, and how many earned leave days can I encash?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: leave_ledger, employee_master
-- Drill Dims: leave_ledger.leave_type
-- Story IDs: S38
-- Expected Output: table
-- Handcrafted: false
-- Story Target: 5.0 (demo_personas_count)
-- Expected Range: 4.5 - 5.5 (tolerance: ±10.0%)

SELECT
    leave_ledger.leave_type,
    leave_ledger.closing_balance_days, leave_ledger.encashable_balance_days AS encashable_balance_days
FROM leave_ledger
LEFT JOIN employee_master ON leave_ledger.emp_id = employee_master.emp_id
WHERE leave_ledger.emp_id = 'EMP-102451' AND leave_ledger.fiscal_year IN ('FY26', '2026')
ORDER BY leave_ledger.leave_type
LIMIT 100;
