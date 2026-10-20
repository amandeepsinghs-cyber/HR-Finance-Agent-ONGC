-- Answer Key Follow-up SQL: C4__compare_or_so_what
-- Question: What percentage of eligible E6 Chief Engineers / Chief Geologists meet the DPC benchmark for accelerated promotion to GM?
-- Type: data
-- Semantic audit 2026-10-20: old SQL counted historical E6->E7 dpc_cases rows FY13-FY26 by status (all
-- 'completed', 1,520) - a count of past promotions, not a percentage of eligible officers meeting a benchmark
-- (dpc_cases.accelerated_merit_benchmark_score is a constant 85 for every row, so it cannot discriminate).
-- Now: currently active E6 officers in technical disciplines (Chief Engineers / Chief Geologists) with an
-- FY26 APAR, split geoscience (Geology, Geophysics, Reservoir) vs engineering; % whose APAR numerical score
-- meets the DPC benchmark (benchmark_score, 7.5) and % rated 'Outstanding' (accelerated-merit band).

WITH e6 AS (
    SELECT e.emp_id,
           CASE WHEN e.discipline_id IN ('DISC-GEO', 'DISC-GPS', 'DISC-GPW', 'DISC-RES') THEN 'Geoscience (Chief Geologist / Geophysicist / Reservoir)'
                ELSE 'Engineering (Chief Engineer)' END AS cadre_family
    FROM employee_master e
    JOIN dim_discipline d ON e.discipline_id = d.discipline_id
    WHERE LOWER(e.employment_status) = 'active'
      AND e.current_grade_id = 'E6'
      AND LOWER(d.function) = 'technical'
),
a AS (
    SELECT e6.cadre_family, ap.emp_id, ap.numerical_score, ap.benchmark_score, ap.final_rating
    FROM e6
    JOIN apar_ratings ap ON ap.emp_id = e6.emp_id AND ap.fiscal_year = 'FY26'
),
g AS (
    SELECT cadre_family, 0 AS ord,
           COUNT(DISTINCT emp_id) AS e6_with_fy26_apar,
           COUNT(DISTINCT IF(numerical_score >= benchmark_score, emp_id, NULL)) AS meet_dpc_benchmark,
           COUNT(DISTINCT IF(LOWER(final_rating) = 'outstanding', emp_id, NULL)) AS outstanding_accelerated,
           ANY_VALUE(benchmark_score) AS benchmark_score
    FROM a GROUP BY cadre_family
    UNION ALL
    SELECT 'All technical E6', 1,
           COUNT(DISTINCT emp_id),
           COUNT(DISTINCT IF(numerical_score >= benchmark_score, emp_id, NULL)),
           COUNT(DISTINCT IF(LOWER(final_rating) = 'outstanding', emp_id, NULL)),
           ANY_VALUE(benchmark_score)
    FROM a
)
SELECT
    cadre_family,
    e6_with_fy26_apar,
    benchmark_score,
    meet_dpc_benchmark,
    ROUND(meet_dpc_benchmark * 100.0 / NULLIF(e6_with_fy26_apar, 0), 1) AS pct_meet_benchmark,
    outstanding_accelerated,
    ROUND(outstanding_accelerated * 100.0 / NULLIF(e6_with_fy26_apar, 0), 1) AS pct_outstanding
FROM g
ORDER BY ord, cadre_family;
