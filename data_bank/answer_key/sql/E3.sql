-- Answer Key SQL: E3
-- Question: What is my medical reimbursement claim status?
-- Type: data
-- Semantic audit 2026-10-20: Added claim type, patient, submission/settlement dates and claimed amount so status can be stated; ordered by recency.

SELECT
    claim_id,
    claim_type,
    patient_relationship,
    submission_date,
    claim_status,
    claimed_amount_inr,
    approved_amount_inr,
    settlement_date
FROM medical_claims
WHERE emp_id = 'EMP-102451'
ORDER BY submission_date DESC;
