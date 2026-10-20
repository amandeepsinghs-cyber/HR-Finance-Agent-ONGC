-- Probe ID: H9.compare_or_so_what
-- Parent ID: H9
-- Answer Type: sql
-- Question: What is the average disposal time of internal employee grievances compared to the statutory 60-day charter target?
-- Personas: Director (HR)
-- Tables: grievances_litigation
-- Drill Dims: grievances_litigation.case_type
-- Story IDs: S19
-- Expected Output: number
-- Handcrafted: true

SELECT
    case_type,
    ROUND(AVG(age_days), 1) AS avg_age_days
FROM grievances_litigation
GROUP BY case_type
ORDER BY case_type;
