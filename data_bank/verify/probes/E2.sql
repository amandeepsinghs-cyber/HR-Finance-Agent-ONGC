-- Probe ID: E2
-- Parent ID: None
-- Answer Type: sql_plus_rag
-- Question: When am I due for transfer, and what is the rotation policy for my grade?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: posting_history, employee_master
-- Drill Dims: 
-- Story IDs: S38
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 5.0 (demo_personas_count)
-- Expected Range: 4.5 - 5.5 (tolerance: ±10.0%)

SELECT
    p.emp_id,
    wc.wc_id,
    p.from_date,
    COALESCE(p.to_date, DATE '2026-10-19') AS to_date,
    datediff('month', p.from_date, COALESCE(p.to_date, DATE '2026-10-19')) AS tenure_months
FROM posting_history p
JOIN dim_work_centre wc ON p.wc_id = wc.wc_id
WHERE p.emp_id = 'EMP-102451'
ORDER BY p.from_date;
