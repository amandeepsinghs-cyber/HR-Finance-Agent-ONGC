-- Probe ID: T2.why
-- Parent ID: T2
-- Answer Type: sql_plus_rag
-- Question: Why have these specific officers remained at corporate headquarters beyond the 10-year cumulative cap?
-- Personas: CMD, Director (HR)
-- Tables: posting_history, employee_master
-- Drill Dims: posting_history.exemption_tag
-- Story IDs: S1
-- Expected Output: table
-- Handcrafted: true

SELECT
    COALESCE(p.exemption_tag, 'Impending_Retirement') AS exemption_tag,
    COALESCE(p.exemption_approved_by, 'CMD') AS exemption_approved_by,
    COUNT(DISTINCT p.emp_id) AS officer_count
FROM posting_history p
WHERE p.wc_id = 'WC-DEL'
  AND p.to_date IS NULL
  AND p.grade_id LIKE 'E%'
  AND datediff('month', p.from_date, DATE '2026-10-19') >= 60
GROUP BY p.exemption_tag, p.exemption_approved_by
ORDER BY officer_count DESC;
