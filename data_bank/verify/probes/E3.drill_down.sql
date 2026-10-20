-- Probe ID: E3.drill_down
-- Parent ID: E3
-- Answer Type: sql
-- Question: What is the settlement breakdown between approved claim amount, deduction heads, and net payable for my recent medical claims?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: medical_claims
-- Drill Dims: medical_claims.claim_id
-- Story IDs: S38
-- Expected Output: table
-- Handcrafted: false

SELECT
    medical_claims.claim_id,
    medical_claims.claimed_amount_inr, medical_claims.approved_amount_inr, medical_claims.deduction_amount_inr AS deduction_amount_inr
FROM medical_claims
WHERE medical_claims.emp_id = 'EMP-102451'
ORDER BY medical_claims.claim_id
LIMIT 100;
