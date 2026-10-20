-- Probe ID: E3.compare_or_so_what
-- Parent ID: E3
-- Answer Type: sql
-- Question: How does the turnaround time for my claim compare with the standard 15-day settlement service level agreement?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: medical_claims
-- Drill Dims: medical_claims.claim_id
-- Story IDs: S38
-- Expected Output: table
-- Handcrafted: false

SELECT
    medical_claims.claim_id,
    medical_claims.turnaround_days AS turnaround_days
FROM medical_claims
WHERE medical_claims.emp_id = 'EMP-102451'
ORDER BY medical_claims.claim_id
LIMIT 100;
