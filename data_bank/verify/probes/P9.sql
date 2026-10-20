-- Probe ID: P9
-- Parent ID: None
-- Answer Type: sql_plus_rag
-- Question: How do I file a POSH complaint, and who is on the committee at my station?
-- Personas: CMD, Director (HR), Director (Finance), E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: icc_committees
-- Drill Dims: icc_committees.wc_id
-- Story IDs: 
-- Expected Output: table
-- Handcrafted: true

SELECT
    wc_id,
    presiding_officer_name,
    external_member_name
FROM icc_committees
WHERE LOWER(status) = 'active'
ORDER BY wc_id
LIMIT 100;
