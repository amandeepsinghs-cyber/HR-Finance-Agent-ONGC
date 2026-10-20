-- Probe ID: W3.drill_down
-- Parent ID: W3
-- Answer Type: what_if_sim
-- Question: What is the estimated budget required for Composite Transfer Allowance (CTA) and relocation grants for 200 officers?
-- Personas: CMD
-- Tables: posting_history
-- Drill Dims: 
-- Story IDs: S31
-- Expected Output: number
-- Handcrafted: true

SELECT
    wc.wc_id,
    wc.short_name,
    COUNT(DISTINCT p.emp_id) AS transferable_executives,
    200 * 150000.0 AS estimated_ctg_budget_inr
FROM posting_history p
JOIN dim_work_centre wc ON p.wc_id = wc.wc_id
WHERE wc.wc_id IN ('WC-DEL', 'WC-DDN')
  AND p.to_date IS NULL
  AND p.grade_id LIKE 'E%'
GROUP BY wc.wc_id, wc.short_name;
