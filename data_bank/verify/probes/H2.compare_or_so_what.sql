-- Probe ID: H2.compare_or_so_what
-- Parent ID: H2
-- Answer Type: sql
-- Question: How does the percentage of hard-station unserved officers in HR and Finance compare with Drilling and Production disciplines?
-- Personas: Director (HR)
-- Tables: employee_master, dim_discipline
-- Drill Dims: dim_discipline.name
-- Story IDs: S2
-- Expected Output: chart
-- Handcrafted: true

SELECT
    d.name,
    COUNT(DISTINCT e.emp_id) AS executive_count
FROM employee_master e
JOIN dim_discipline d ON e.discipline_id = d.discipline_id
WHERE e.current_wc_id IN ('WC-ASM', 'WC-JOR', 'WC-TRI', 'WC-SIL')
GROUP BY d.name;
