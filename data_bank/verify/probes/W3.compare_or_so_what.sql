-- Probe ID: W3.compare_or_so_what
-- Parent ID: W3
-- Answer Type: what_if_sim
-- Question: How does the one-time relocation expenditure compare against the multi-year production gains from enhanced field coverage?
-- Personas: CMD
-- Tables: field_pnl_annual, posting_history
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
