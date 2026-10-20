-- Probe ID: H4.drill_down
-- Parent ID: H4
-- Answer Type: sql
-- Question: Which technical disciplines (IT, Drilling, Reservoir, Finance) account for the highest share of voluntary resignations in E3–E5?
-- Personas: Director (HR)
-- Tables: separations, dim_discipline
-- Drill Dims: dim_discipline.name
-- Story IDs: S12
-- Expected Output: table
-- Handcrafted: true

SELECT
    d.name,
    COUNT(DISTINCT s.emp_id) AS resignation_count
FROM separations s
JOIN dim_discipline d ON s.discipline_id = d.discipline_id
WHERE LOWER(s.separation_type) = 'resignation'
  AND s.fiscal_year = 'FY26'
GROUP BY d.name
ORDER BY resignation_count DESC;
