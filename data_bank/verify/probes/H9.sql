-- Probe ID: H9
-- Parent ID: None
-- Answer Type: sql
-- Question: How many grievances and service litigations are pending, and how old are they?
-- Personas: Director (HR)
-- Tables: grievances_litigation, dim_work_centre
-- Drill Dims: grievances_litigation.is_aged_over_3_years
-- Story IDs: S19
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 312.0 (active_employee_grievances)
-- Expected Range: 280.8 - 343.2 (tolerance: ±10.0%)

SELECT
    is_aged_over_3_years,
    COUNT(DISTINCT case_id) AS pending_cases_count
FROM grievances_litigation
WHERE LOWER(status) = 'pending'
GROUP BY is_aged_over_3_years
ORDER BY is_aged_over_3_years DESC;
