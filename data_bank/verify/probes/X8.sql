-- Probe ID: X8
-- Parent ID: None
-- Answer Type: sql
-- Question: How many audit (CAG) objections and right-to-information (RTI) applications are pending, and how old are they?
-- Personas: CMD
-- Tables: cag_paras, rti_applications
-- Drill Dims: 
-- Story IDs: S19
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 38.0 (open_cag_audit_paras)
-- Expected Range: 34.2 - 41.8 (tolerance: ±10.0%)

WITH c AS (
    SELECT COUNT(*) AS open_cag_paras
    FROM cag_paras
    WHERE current_status != 'Closed'
),
r AS (
    SELECT COUNT(*) AS pending_rti_appeals
    FROM rti_applications
    WHERE status LIKE '%Pending%'
)
SELECT c.open_cag_paras, r.pending_rti_appeals
FROM c, r;
