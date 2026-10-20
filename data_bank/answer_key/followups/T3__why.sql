-- Answer Key Follow-up SQL: T3__why
-- Question: Why do certain identified successor candidates lack the mandatory hard-station or North-East service prerequisite?
-- Type: chain
-- Semantic audit 2026-10-20: Old SQL counted readiness_gap_reason over all positions; it never looked at the successors who lack NE/hard-station service.
-- Semantic audit 2026-10-20: Now: profile of the named successors without NE/hard-station service - current posting type, function, tenure, postings and Category-C/NE postings in their career.

WITH s AS (
    SELECT successor_1_emp_id AS sid, successor_1_readiness AS rd FROM succession_plan WHERE NOT successor_1_has_ne_hard_station
    UNION DISTINCT
    SELECT successor_2_emp_id, successor_2_readiness FROM succession_plan WHERE NOT successor_2_has_ne_hard_station
),
cp AS (
    SELECT p.emp_id,
           COUNT(*) AS postings,
           COUNTIF(w.hard_station_cat = 'C' OR LOWER(w.sector) = 'ne') AS c_or_ne_postings
    FROM posting_history p
    JOIN dim_work_centre w ON w.wc_id = p.wc_id
    GROUP BY p.emp_id
)
SELECT
    CASE WHEN w.is_corporate_hq THEN 'Corporate HQ (Delhi/Dehradun)'
         WHEN LOWER(w.type) = 'office' THEN 'Regional office'
         ELSE CONCAT('Field asset/service (Cat ', w.hard_station_cat, ')') END AS current_posting,
    d.function AS discipline_function,
    COUNT(DISTINCT s.sid) AS successors_without_ne,
    ROUND(AVG(e.total_tenure_years), 1) AS avg_tenure_years,
    ROUND(AVG(cp.postings), 1) AS avg_postings,
    SUM(cp.c_or_ne_postings) AS c_or_ne_postings,
    STRING_AGG(DISTINCT s.rd, ', ') AS readiness
FROM s
JOIN employee_master e ON e.emp_id = s.sid
JOIN dim_work_centre w ON w.wc_id = e.current_wc_id
JOIN dim_discipline d ON d.discipline_id = e.discipline_id
LEFT JOIN cp ON cp.emp_id = s.sid
GROUP BY current_posting, discipline_function
ORDER BY successors_without_ne DESC, current_posting;
