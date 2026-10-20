-- Probe ID: P11.why
-- Parent ID: P11
-- Answer Type: sql_plus_rag
-- Question: Why have 31 senior executives been granted superannuation exemptions from the upcoming transfer order?
-- Personas: CMD, Director (HR)
-- Tables: posting_history, employee_master
-- Drill Dims: posting_history.exemption_tag
-- Story IDs: S1
-- Expected Output: table
-- Handcrafted: true

SELECT
    p.exemption_tag,
    COUNT(DISTINCT p.emp_id) AS exempt_officer_count
FROM posting_history p
JOIN employee_master e ON p.emp_id = e.emp_id
WHERE p.wc_id = 'WC-DEL' AND p.to_date IS NULL AND p.grade_id LIKE 'E%'
  AND e.dob <= DATE '1969-10-19'
GROUP BY p.exemption_tag
ORDER BY exempt_officer_count DESC;
