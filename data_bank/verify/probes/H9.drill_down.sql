-- Probe ID: H9.drill_down
-- Parent ID: H9
-- Answer Type: sql
-- Question: Break down pending cases by category (promotion dispute, transfer challenge, disciplinary action, pay anomaly) across High Courts and CAT.
-- Personas: Director (HR)
-- Tables: grievances_litigation
-- Drill Dims: grievances_litigation.case_category, grievances_litigation.forum
-- Story IDs: S19
-- Expected Output: table
-- Handcrafted: true

SELECT
    case_category,
    forum,
    COUNT(DISTINCT case_id) AS pending_cases_count
FROM grievances_litigation
WHERE LOWER(status) = 'pending'
GROUP BY case_category, forum
ORDER BY case_category, forum;
