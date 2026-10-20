-- Answer Key Follow-up SQL: H4__why
-- Question: What primary exit reasons (compensation gap with private E&P, location hardship, career progression) were cited in exit interviews?
-- Type: data
-- Semantic audit 2026-10-20: old SQL COALESCEd missing reasons to 'career_progression' (fabricating the top reason) and looked
-- at FY26 only. Now: exit-interview reasons for voluntary exits FY24-FY26, all grades and the E3-E5 subset, no imputation.
SELECT
    IFNULL(exit_interview_reason, 'not recorded') AS exit_interview_reason,
    COUNT(*) AS voluntary_exits,
    COUNTIF(last_grade_id IN ('E3', 'E4', 'E5')) AS mid_career_e3_e5,
    COUNTIF(fiscal_year = 'FY26') AS exits_fy26,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS share_pct
FROM separations
WHERE LOWER(separation_type) IN ('resignation', 'vrs')
  AND fiscal_year IN ('FY24', 'FY25', 'FY26')
GROUP BY 1
ORDER BY voluntary_exits DESC;
