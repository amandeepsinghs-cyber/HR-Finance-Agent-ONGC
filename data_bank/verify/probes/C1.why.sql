-- Probe ID: C1.why
-- Parent ID: C1
-- Answer Type: sql_plus_rag
-- Question: What are the approved administrative justifications or exemption tags recorded in SAP for those exceeding 5 years in Delhi?
-- Personas: CMD
-- Tables: posting_history, dim_work_centre
-- Drill Dims: posting_history.exemption_reason_code, posting_history.exemption_approved_by
-- Story IDs: S1
-- Expected Output: table
-- Handcrafted: true

SELECT
    COALESCE(p.exemption_reason_code, 'NO_CODE') AS exemption_reason_code,
    COALESCE(p.exemption_approved_by, 'CMD') AS exemption_approved_by,
    COUNT(DISTINCT p.emp_id) AS officer_count
FROM posting_history p
WHERE p.wc_id = 'WC-DEL'
  AND p.to_date IS NULL
  AND p.grade_id LIKE 'E%'
  AND datediff('month', p.from_date, DATE '2026-10-19') >= 60
GROUP BY p.exemption_reason_code, p.exemption_approved_by
ORDER BY officer_count DESC;
