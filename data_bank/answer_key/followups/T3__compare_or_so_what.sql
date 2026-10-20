-- Answer Key Follow-up SQL: T3__compare_or_so_what
-- Question: What accelerated leadership development or rotational posting is required to qualify successors before retirement dates?
-- Type: chain
-- Semantic audit 2026-10-20: Old SQL listed Tier-1 positions with NE flags only - no timing vs retirement or requirement.
-- Semantic audit 2026-10-20: Now: each named successor lacking NE/hard-station service on a position whose incumbent has not yet retired - months to incumbent retirement vs the 36-month mandatory hard-station stint (JRTP 6.1), and whether the alternate successor already qualifies.

WITH s AS (
    SELECT position_id, role_title, criticality_tier, incumbent_retire_date, 1 AS successor_slot,
           successor_1_emp_id AS successor_emp_id, successor_1_readiness AS readiness, successor_1_has_ne_hard_station AS has_ne,
           successor_2_has_ne_hard_station AS alternate_has_ne, successor_2_readiness AS alternate_readiness
    FROM succession_plan
    UNION ALL
    SELECT position_id, role_title, criticality_tier, incumbent_retire_date, 2,
           successor_2_emp_id, successor_2_readiness, successor_2_has_ne_hard_station,
           successor_1_has_ne_hard_station, successor_1_readiness
    FROM succession_plan
)
SELECT
    position_id,
    role_title,
    criticality_tier,
    incumbent_retire_date,
    successor_slot,
    successor_emp_id,
    readiness,
    DATE_DIFF(incumbent_retire_date, DATE '2026-10-19', MONTH) AS months_to_incumbent_retirement,
    GREATEST(36 - DATE_DIFF(incumbent_retire_date, DATE '2026-10-19', MONTH), 0) AS months_short_of_36m_ne_stint,
    DATE_DIFF(incumbent_retire_date, DATE '2026-10-19', MONTH) >= 36 AS can_complete_ne_stint_before_retirement,
    alternate_has_ne,
    alternate_readiness
FROM s
WHERE NOT has_ne
  AND incumbent_retire_date >= DATE '2026-10-19'
ORDER BY incumbent_retire_date, position_id, successor_slot;
