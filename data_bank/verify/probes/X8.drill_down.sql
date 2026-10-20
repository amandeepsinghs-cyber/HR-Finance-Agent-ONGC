-- Probe ID: X8.drill_down
-- Parent ID: X8
-- Answer Type: sql
-- Question: Which operating departments (Procurement/MM, Finance, HR) have the largest volume of outstanding CAG audit paragraphs?
-- Personas: CMD
-- Tables: cag_paras
-- Drill Dims: cag_paras.operating_department
-- Story IDs: S19
-- Expected Output: table
-- Handcrafted: true

SELECT
    operating_department,
    COUNT(cag_para_id) AS metric_1,
    SUM(financial_implication_inr_cr) AS metric_2
FROM cag_paras
WHERE current_status != 'Closed'
GROUP BY operating_department
ORDER BY metric_1 DESC
LIMIT 100;
