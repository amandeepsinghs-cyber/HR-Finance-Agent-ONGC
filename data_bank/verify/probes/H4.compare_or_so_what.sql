-- Probe ID: H4.compare_or_so_what
-- Parent ID: H4
-- Answer Type: sql
-- Question: How does ONGC's mid-career executive attrition rate compare between onshore field postings and corporate offices?
-- Personas: Director (HR)
-- Tables: separations, dim_work_centre
-- Drill Dims: dim_work_centre.type
-- Story IDs: S12
-- Expected Output: table
-- Handcrafted: true

SELECT
    wc.type,
    COUNT(DISTINCT s.emp_id) AS resignation_count
FROM separations s
JOIN dim_work_centre wc ON s.last_wc_id = wc.wc_id
WHERE LOWER(s.separation_type) = 'resignation'
  AND s.fiscal_year = 'FY26'
GROUP BY wc.type
ORDER BY resignation_count DESC;
