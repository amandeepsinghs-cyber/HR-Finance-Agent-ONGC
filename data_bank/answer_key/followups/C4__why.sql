-- Answer Key Follow-up SQL: C4__why
-- Question: Why are certain critical E7+ positions identified as having zero 'Ready Now' successors in the latest succession board review?
-- Type: data
-- Semantic audit 2026-10-20: old SQL only counted positions by successor_1 readiness (no reason), across all
-- positions. Now: positions in the latest review (succession_plan, FY26) where NEITHER successor is
-- 'Ready_Now', grouped by the recorded readiness_gap_reason and criticality tier, with how many of those
-- positions are held by an active E7+ incumbent, retire within 3 years, and whose successors lack the
-- mandatory NE/hard-station tenure (successor_*_has_ne_hard_station).

SELECT
    COALESCE(NULLIF(sp.readiness_gap_reason, 'None'), 'Not recorded') AS readiness_gap_reason,
    sp.criticality_tier,
    COUNT(DISTINCT sp.position_id) AS positions_no_ready_now,
    COUNT(DISTINCT IF(LOWER(e.employment_status) = 'active' AND e.current_grade_id IN ('E7', 'E8', 'E9', 'DIR', 'CMD'), sp.position_id, NULL)) AS held_by_active_e7_plus,
    COUNT(DISTINCT IF(sp.incumbent_retire_date BETWEEN DATE '2026-10-19' AND DATE '2029-10-18', sp.position_id, NULL)) AS incumbent_retires_3yr,
    COUNT(DISTINCT IF(NOT COALESCE(sp.successor_1_has_ne_hard_station, FALSE), sp.position_id, NULL)) AS successor_1_lacks_ne_hard_station,
    COUNT(DISTINCT IF(NOT COALESCE(sp.successor_1_has_ne_hard_station, FALSE) AND NOT COALESCE(sp.successor_2_has_ne_hard_station, FALSE), sp.position_id, NULL)) AS both_successors_lack_ne_hard_station,
    STRING_AGG(DISTINCT sp.role_title, '; ') AS roles
FROM succession_plan sp
LEFT JOIN employee_master e ON e.emp_id = sp.incumbent_emp_id
WHERE COALESCE(LOWER(sp.successor_1_readiness), '') != 'ready_now'
  AND COALESCE(LOWER(sp.successor_2_readiness), '') != 'ready_now'
GROUP BY 1, 2
ORDER BY positions_no_ready_now DESC;
