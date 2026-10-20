-- Probe ID: C4.drill_down
-- Parent ID: C4
-- Answer Type: sql
-- Question: Which key operational roles in Offshore (Mumbai High, Neelam-Heera) and Drilling have retirement vacancies within 12 months?
-- Personas: CMD
-- Tables: succession_plan, dim_work_centre, dim_discipline
-- Drill Dims: succession_plan.role_title, dim_work_centre.name
-- Story IDs: S4
-- Expected Output: list
-- Handcrafted: true

SELECT
    sp.role_title,
    wc.name,
    COUNT(DISTINCT sp.position_id) AS critical_positions_count
FROM succession_plan sp
JOIN dim_work_centre wc ON sp.wc_id = wc.wc_id
WHERE sp.incumbent_retire_date BETWEEN DATE '2026-10-19' AND DATE '2027-10-19'
GROUP BY sp.role_title, wc.name
ORDER BY sp.role_title, wc.name;
