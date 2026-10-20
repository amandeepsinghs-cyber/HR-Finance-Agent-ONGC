-- Answer Key Follow-up SQL: H4__drill_down
-- Question: Which technical disciplines (IT, Drilling, Reservoir, Finance) account for the highest share of voluntary resignations in E3–E5?
-- Type: data
-- Semantic audit 2026-10-20: old SQL had no E3-E5 filter (all grades, FY26 only) and no share. Now: voluntary exits
-- (resignation + VRS) of E3-E5 executives over FY24-FY26 by discipline, with share of the mid-career total.
SELECT
    d.name AS discipline,
    COUNT(*) AS mid_career_voluntary_exits,
    COUNTIF(s.fiscal_year = 'FY26') AS exits_fy26,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS share_pct
FROM separations s
JOIN dim_discipline d ON s.discipline_id = d.discipline_id
WHERE LOWER(s.separation_type) IN ('resignation', 'vrs')
  AND s.fiscal_year IN ('FY24', 'FY25', 'FY26')
  AND s.last_grade_id IN ('E3', 'E4', 'E5')
GROUP BY d.name
ORDER BY mid_career_voluntary_exits DESC, discipline;
