-- Probe ID: H4
-- Parent ID: None
-- Answer Type: sql
-- Question: What are attrition and voluntary-exit numbers by grade over the last 3 years? Is mid-career attrition (E3–E5) rising?
-- Personas: Director (HR)
-- Tables: separations, dim_grade
-- Drill Dims: separations.fiscal_year, separations.last_grade_id
-- Story IDs: S12
-- Expected Output: chart
-- Handcrafted: true
-- Story Target: 182.0 (total_executive_resignations_fy26)
-- Expected Range: 163.8 - 200.2 (tolerance: ±10.0%)

SELECT
    fiscal_year,
    last_grade_id,
    COUNT(DISTINCT emp_id) AS resignation_count
FROM separations
WHERE LOWER(separation_type) = 'resignation'
  AND fiscal_year IN ('FY24', 'FY25', 'FY26')
GROUP BY fiscal_year, last_grade_id
ORDER BY fiscal_year, last_grade_id;
