-- Answer Key SQL: H4
-- Question: What are attrition and voluntary-exit numbers by grade over the last 3 years? Is mid-career attrition (E3–E5) rising?
-- Type: data
-- Semantic audit 2026-10-20: old SQL counted only resignations (no total attrition, no VRS, no rates), so 'rising' could not be
-- judged against a shrinking base. Now: per grade, FY24-FY26 (last 3 full FYs) total separations, voluntary exits
-- (resignation + VRS) and voluntary-exit rate on opening headcount (headcount_snapshot March of the prior FY, a stock).
WITH seps AS (
    SELECT last_grade_id AS grade_id, fiscal_year,
           COUNT(*) AS total_exits,
           COUNTIF(LOWER(separation_type) IN ('resignation', 'vrs')) AS voluntary_exits
    FROM separations
    WHERE fiscal_year IN ('FY24', 'FY25', 'FY26')
    GROUP BY 1, 2
),
opening AS (
    SELECT grade_id,
           CASE month WHEN '2023-03' THEN 'FY24' WHEN '2024-03' THEN 'FY25' WHEN '2025-03' THEN 'FY26' END AS fiscal_year,
           SUM(headcount) AS opening_hc
    FROM headcount_snapshot
    WHERE month IN ('2023-03', '2024-03', '2025-03')
    GROUP BY 1, 2
),
grid AS (
    SELECT o.grade_id, o.fiscal_year, o.opening_hc, IFNULL(s.total_exits, 0) AS total_exits, IFNULL(s.voluntary_exits, 0) AS voluntary_exits
    FROM opening o LEFT JOIN seps s ON s.grade_id = o.grade_id AND s.fiscal_year = o.fiscal_year
)
SELECT
    g.grade_id,
    g.grade_id IN ('E3', 'E4', 'E5') AS is_mid_career,
    SUM(IF(fiscal_year = 'FY24', total_exits, 0)) AS total_exits_fy24,
    SUM(IF(fiscal_year = 'FY25', total_exits, 0)) AS total_exits_fy25,
    SUM(IF(fiscal_year = 'FY26', total_exits, 0)) AS total_exits_fy26,
    SUM(IF(fiscal_year = 'FY24', voluntary_exits, 0)) AS voluntary_fy24,
    SUM(IF(fiscal_year = 'FY25', voluntary_exits, 0)) AS voluntary_fy25,
    SUM(IF(fiscal_year = 'FY26', voluntary_exits, 0)) AS voluntary_fy26,
    SUM(IF(fiscal_year = 'FY24', opening_hc, 0)) AS opening_hc_fy24,
    SUM(IF(fiscal_year = 'FY25', opening_hc, 0)) AS opening_hc_fy25,
    SUM(IF(fiscal_year = 'FY26', opening_hc, 0)) AS opening_hc_fy26,
    ROUND(SUM(IF(fiscal_year = 'FY24', voluntary_exits, 0)) * 100.0 / NULLIF(SUM(IF(fiscal_year = 'FY24', opening_hc, 0)), 0), 2) AS voluntary_rate_fy24_pct,
    ROUND(SUM(IF(fiscal_year = 'FY25', voluntary_exits, 0)) * 100.0 / NULLIF(SUM(IF(fiscal_year = 'FY25', opening_hc, 0)), 0), 2) AS voluntary_rate_fy25_pct,
    ROUND(SUM(IF(fiscal_year = 'FY26', voluntary_exits, 0)) * 100.0 / NULLIF(SUM(IF(fiscal_year = 'FY26', opening_hc, 0)), 0), 2) AS voluntary_rate_fy26_pct
FROM grid
JOIN dim_grade g ON g.grade_id = grid.grade_id
GROUP BY g.grade_id, g.level_order
ORDER BY g.level_order;
