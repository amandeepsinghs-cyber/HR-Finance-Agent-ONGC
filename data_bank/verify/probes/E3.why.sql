-- Probe ID: E3.why
-- Parent ID: E3
-- Answer Type: sql_plus_rag
-- Question: Why was a specific deduction applied to the room rent or investigation charges under the ONGC medical trust schedule?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: medical_claims
-- Drill Dims: medical_claims.deduction_reason
-- Story IDs: S38
-- Expected Output: table
-- Handcrafted: false

SELECT
    medical_claims.deduction_reason,
    medical_claims.deduction_reason AS deduction_reason
FROM medical_claims
WHERE medical_claims.emp_id = 'EMP-102451' AND medical_claims.deduction_amount_inr > 0
ORDER BY medical_claims.deduction_reason
LIMIT 100;
