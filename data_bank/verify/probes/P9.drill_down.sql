-- Probe ID: P9.drill_down
-- Parent ID: P9
-- Answer Type: sql
-- Question: What external NGO members are appointed to each ICC across work centres to meet the statutory POSH quorum?
-- Personas: Director (HR)
-- Tables: icc_committees
-- Drill Dims: icc_committees.wc_id, icc_committees.external_member_ngo
-- Story IDs: 
-- Expected Output: table
-- Handcrafted: true

SELECT
    wc_id,
    external_member_ngo,
    external_member_name
FROM icc_committees
WHERE LOWER(status) = 'active'
ORDER BY wc_id
LIMIT 100;
