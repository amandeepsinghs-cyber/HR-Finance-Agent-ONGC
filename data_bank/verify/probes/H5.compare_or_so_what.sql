-- Probe ID: H5.compare_or_so_what
-- Parent ID: H5
-- Answer Type: sql
-- Question: How many eligible executives have completed the required residency period but are still awaiting promotion notification?
-- Personas: Director (HR)
-- Tables: promotion_history, dpc_cases
-- Drill Dims: dpc_cases.from_grade_id
-- Story IDs: S11
-- Expected Output: number
-- Handcrafted: true

SELECT
    from_grade_id,
    AVG(delay_months) AS avg_delay_months
FROM dpc_cases
WHERE delay_months >= 6
GROUP BY from_grade_id
ORDER BY from_grade_id;
