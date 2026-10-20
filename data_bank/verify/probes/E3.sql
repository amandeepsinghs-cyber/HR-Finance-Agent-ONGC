-- Probe ID: E3
-- Parent ID: None
-- Answer Type: sql
-- Question: What is my medical reimbursement claim status?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: medical_claims
-- Drill Dims: medical_claims.claim_id
-- Story IDs: S38
-- Expected Output: table
-- Handcrafted: false
-- Story Target: 5.0 (demo_personas_count)
-- Expected Range: 4.5 - 5.5 (tolerance: ±10.0%)

SELECT
    medical_claims.claim_id,
    medical_claims.claim_status, medical_claims.approved_amount_inr AS approved_amount_inr
FROM medical_claims
WHERE medical_claims.emp_id = 'EMP-102451'
ORDER BY medical_claims.claim_id
LIMIT 100;
