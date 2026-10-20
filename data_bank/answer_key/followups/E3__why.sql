-- Answer Key Follow-up SQL: E3__why
-- Question: Why was a specific deduction applied to the room rent or investigation charges under the ONGC medical trust schedule?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL selected deduction_reason twice. Now returns the claim, amount and reason and flags whether it is room-rent/investigation (it is not).

SELECT
    claim_id,
    claim_type,
    hospital_name,
    is_empanelled_hospital,
    deduction_amount_inr,
    deduction_reason,
    REGEXP_CONTAINS(LOWER(deduction_reason), r'room|investigation') AS is_room_rent_or_investigation
FROM medical_claims
WHERE emp_id = 'EMP-102451' AND deduction_amount_inr > 0
ORDER BY claim_id;
