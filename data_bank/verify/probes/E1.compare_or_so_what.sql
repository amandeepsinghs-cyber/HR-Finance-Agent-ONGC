-- Probe ID: E1.compare_or_so_what
-- Parent ID: E1
-- Answer Type: sql
-- Question: What would be the gross monetary value of encashing 30 days of earned leave based on my current basic pay and DA?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: payroll_monthly, leave_ledger
-- Drill Dims: 
-- Story IDs: S38
-- Expected Output: number
-- Handcrafted: true

SELECT
    ROUND(((p.basic_pay_inr + p.da_inr) / 30.0) * LEAST(30, l.encashable_balance_days), 2) AS metric_1
FROM payroll_monthly p
JOIN leave_ledger l ON l.emp_id = p.emp_id
WHERE p.emp_id = 'EMP-102451'
  AND p.month = (SELECT MAX(month) FROM payroll_monthly WHERE emp_id = 'EMP-102451')
ORDER BY 1
LIMIT 1;
