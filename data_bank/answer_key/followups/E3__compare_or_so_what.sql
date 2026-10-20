-- Answer Key Follow-up SQL: E3__compare_or_so_what
-- Question: How does the turnaround time for my claim compare with the standard 15-day settlement service level agreement?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL returned turnaround_days, which is NULL for every claim in silver (35,134/35,134) -> no answer.
-- Semantic audit 2026-10-20: Now derives days from submission to settlement (or to 2026-10-19 if open) vs the 15-day SLA.

SELECT
    claim_id,
    claim_status,
    submission_date,
    settlement_date,
    COALESCE(turnaround_days, DATE_DIFF(COALESCE(settlement_date, DATE '2026-10-19'), submission_date, DAY)) AS days_elapsed,
    settlement_date IS NULL AS still_open,
    15 AS sla_days,
    COALESCE(turnaround_days, DATE_DIFF(COALESCE(settlement_date, DATE '2026-10-19'), submission_date, DAY)) > 15 AS sla_breached
FROM medical_claims
WHERE emp_id = 'EMP-102451'
ORDER BY submission_date;
