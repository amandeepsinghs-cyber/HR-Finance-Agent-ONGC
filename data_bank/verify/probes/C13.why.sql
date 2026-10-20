-- Probe ID: C13.why
-- Parent ID: C13
-- Answer Type: what_if_sim
-- Question: What one-time transfer grant, composite transfer allowance (CTA), and baggage transportation costs would be incurred?
-- Personas: CMD
-- Tables: posting_history
-- Drill Dims: 
-- Story IDs: S31
-- Expected Output: table
-- Handcrafted: true

SELECT
    wc.city,
    COUNT(DISTINCT p.emp_id) AS current_delhi_deh_executives
FROM posting_history p
JOIN dim_work_centre wc ON p.wc_id = wc.wc_id
WHERE wc.wc_id IN ('WC-DEL', 'WC-DDN')
  AND p.to_date IS NULL
  AND p.grade_id LIKE 'E%'
GROUP BY wc.city;
