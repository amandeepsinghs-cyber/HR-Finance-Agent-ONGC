-- Probe ID: H7.compare_or_so_what
-- Parent ID: H7
-- Answer Type: sql
-- Question: How does women's representation in technical disciplines compare with corporate and support functions (HR, F&A, Medical)?
-- Personas: Director (HR)
-- Tables: employee_master, dim_discipline
-- Drill Dims: dim_discipline.function
-- Story IDs: S17
-- Expected Output: chart
-- Handcrafted: true

SELECT
    d.function,
    COUNT(DISTINCT e.emp_id) AS female_count,
    ROUND(COUNT(DISTINCT e.emp_id) * 100.0 / NULLIF(SUM(COUNT(DISTINCT e.emp_id)) OVER(), 0), 2) AS pct_share
FROM employee_master e
JOIN dim_discipline d ON e.discipline_id = d.discipline_id
WHERE e.gender = 'Female'
  AND e.employment_status = 'Active'
GROUP BY d.function;
