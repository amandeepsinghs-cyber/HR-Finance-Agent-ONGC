-- Answer Key Follow-up SQL: D3__drill_down
-- Question: Which grades and disciplines are being considered in the current DPC cycle?
-- Type: refusal
-- Semantic audit 2026-10-20: Old SQL counted distinct candidates across ALL DPC history FY01-FY27 (e.g. 8,528 for E4->E5) - not the current cycle (FY_MAPPING).
-- Semantic audit 2026-10-20: Now: current cycle = FY27 DPC cases + FY26 delayed cases still not held, by grade transition and discipline.

WITH cycle AS (
    SELECT *
    FROM dpc_cases
    WHERE fiscal_year = 'FY27'
       OR (LOWER(status) = 'delayed' AND held_date IS NULL)
)
SELECT
    from_grade_id,
    to_grade_id,
    discipline_id,
    COUNT(DISTINCT IF(fiscal_year = 'FY27', emp_id, NULL)) AS fy27_cases_held,
    COUNT(DISTINCT IF(held_date IS NULL, emp_id, NULL)) AS pending_carryover_cases
FROM cycle
GROUP BY from_grade_id, to_grade_id, discipline_id
ORDER BY from_grade_id, discipline_id;
