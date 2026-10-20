-- Answer Key SQL: C4
-- Question: How many E7+ (GM and above) officers retire in the next 3 years, and which of those roles have no ready successor?
-- Type: data
-- Semantic audit 2026-10-20: (1) the retirement window was a DOB band 1966-04-01..1969-03-31 (= retirements
-- Apr-2026..Mar-2029, partly in the past) instead of the next 3 years from 2026-10-19; it found 39 retirees.
-- Now retirement_date BETWEEN 2026-10-19 AND 2029-10-18 on active staff; (2) E7+ now includes board-level
-- incumbents (DIR, CMD) as "GM and above"; (3) the old output only had grade x readiness counts and never named
-- a role. Two sections:
--   'grade_summary'           : per grade - active E7+, retiring in 3 years, of which in a succession-plan
--                               position, of which without any 'Ready_Now' successor, and not in any plan;
--   'role_no_ready_successor' : the succession-plan positions whose active incumbent retires within 3 years
--                               and where neither successor_1 nor successor_2 is 'Ready_Now'.

WITH e AS (
    SELECT emp_id, current_grade_id, current_wc_id, retirement_date
    FROM employee_master
    WHERE LOWER(employment_status) = 'active'
      AND current_grade_id IN ('E7', 'E8', 'E9', 'DIR', 'CMD')
),
j AS (
    SELECT e.*, sp.position_id, sp.role_title, sp.wc_id AS position_wc_id, sp.criticality_tier,
           sp.successor_1_readiness, sp.successor_2_readiness, sp.readiness_gap_reason,
           (sp.position_id IS NOT NULL
            AND COALESCE(LOWER(sp.successor_1_readiness), '') != 'ready_now'
            AND COALESCE(LOWER(sp.successor_2_readiness), '') != 'ready_now') AS no_ready_successor,
           e.retirement_date BETWEEN DATE '2026-10-19' AND DATE '2029-10-18' AS retires_3yr
    FROM e
    LEFT JOIN succession_plan sp ON sp.incumbent_emp_id = e.emp_id
)
SELECT
    'grade_summary' AS section,
    current_grade_id AS grade_id,
    CAST(NULL AS STRING) AS role_title,
    CAST(NULL AS STRING) AS work_centre,
    CAST(NULL AS STRING) AS criticality_tier,
    CAST(NULL AS DATE) AS retirement_date,
    CAST(NULL AS STRING) AS successor_1_readiness,
    CAST(NULL AS STRING) AS readiness_gap_reason,
    COUNT(DISTINCT emp_id) AS active_officers,
    COUNT(DISTINCT IF(retires_3yr, emp_id, NULL)) AS retiring_next_3yr,
    COUNT(DISTINCT IF(retires_3yr AND position_id IS NOT NULL, emp_id, NULL)) AS retiring_in_plan_position,
    COUNT(DISTINCT IF(retires_3yr AND no_ready_successor, emp_id, NULL)) AS retiring_no_ready_successor,
    COUNT(DISTINCT IF(retires_3yr AND position_id IS NULL, emp_id, NULL)) AS retiring_not_in_succession_plan
FROM j
GROUP BY current_grade_id
UNION ALL
SELECT
    'role_no_ready_successor',
    j.current_grade_id,
    j.role_title,
    w.short_name,
    j.criticality_tier,
    j.retirement_date,
    j.successor_1_readiness,
    j.readiness_gap_reason,
    1, 1, 1, 1, 0
FROM j
JOIN dim_work_centre w ON w.wc_id = j.position_wc_id
WHERE j.retires_3yr AND j.no_ready_successor
ORDER BY section, grade_id, retirement_date;
