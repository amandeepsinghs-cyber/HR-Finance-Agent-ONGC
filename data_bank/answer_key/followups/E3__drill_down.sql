-- Answer Key Follow-up SQL: E3__drill_down
-- Question: What is the settlement breakdown between approved claim amount, deduction heads, and net payable for my recent medical claims?
-- Type: data
-- Semantic audit 2026-10-20: Added status, deduction head (reason) and net payable (= approved amount); no logic change.

SELECT
    claim_id,
    claim_status,
    claimed_amount_inr,
    approved_amount_inr,
    deduction_amount_inr,
    deduction_reason,
    approved_amount_inr AS net_payable_inr
FROM medical_claims
WHERE emp_id = 'EMP-102451'
ORDER BY submission_date DESC;
