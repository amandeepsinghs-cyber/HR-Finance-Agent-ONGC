-- Probe ID: C4
-- Parent ID: None
-- Answer Type: sql
-- Question: How many E7+ (GM and above) officers retire in the next 3 years, and which of those roles have no ready successor?
-- Personas: CMD
-- Tables: employee_master, succession_plan, dim_grade, dim_work_centre
-- Drill Dims: employee_master.current_grade_id, succession_plan.successor_1_readiness
-- Story IDs: S4
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 1142.0 (total_e7_plus_in_position)
-- Expected Range: 1027.8 - 1256.2 (tolerance: ±10.0%)

SELECT
    e.current_grade_id,
    COALESCE(sp.successor_1_readiness, 'No_Successor_Mapped') AS successor_1_readiness,
    COUNT(DISTINCT e.emp_id) AS e7_plus_in_position,
    COUNT(DISTINCT CASE WHEN e.dob BETWEEN DATE '1966-04-01' AND DATE '1969-03-31' THEN e.emp_id END) AS retiring_fy27_to_fy29
FROM employee_master e
LEFT JOIN succession_plan sp ON e.emp_id = sp.incumbent_emp_id
WHERE e.current_grade_id IN ('E7', 'E8', 'E9')
  AND (e.employment_status = 'Active' OR e.separation_date IS NULL)
GROUP BY e.current_grade_id, COALESCE(sp.successor_1_readiness, 'No_Successor_Mapped')
ORDER BY e.current_grade_id, successor_1_readiness;
