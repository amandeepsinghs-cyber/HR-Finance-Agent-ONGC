-- Answer Key Follow-up SQL: H4__compare_or_so_what
-- Question: How does ONGC's mid-career executive attrition rate compare between onshore field postings and corporate offices?
-- Type: data
-- Semantic audit 2026-10-20: old SQL counted FY26 resignations of all grades by WC type (no rate, not mid-career). Now: E3-E5
-- voluntary exits FY24-FY26 by location class of the last work centre, divided by the sum of the three opening (March)
-- E3-E5 headcounts at those work centres = average annual voluntary attrition rate.
WITH loc AS (
    SELECT wc_id,
        CASE LOWER(onshore_offshore) WHEN 'corporate' THEN 'Corporate offices & institutes'
             WHEN 'offshore' THEN 'Offshore assets' ELSE 'Onshore field assets' END AS location_class
    FROM dim_work_centre
),
exits AS (
    SELECT l.location_class, COUNT(*) AS voluntary_exits
    FROM separations s JOIN loc l ON l.wc_id = s.last_wc_id
    WHERE LOWER(s.separation_type) IN ('resignation', 'vrs')
      AND s.fiscal_year IN ('FY24', 'FY25', 'FY26')
      AND s.last_grade_id IN ('E3', 'E4', 'E5')
    GROUP BY 1
),
exposure AS (
    SELECT l.location_class, SUM(h.headcount) AS opening_person_years
    FROM headcount_snapshot h JOIN loc l ON l.wc_id = h.wc_id
    WHERE h.month IN ('2023-03', '2024-03', '2025-03') AND h.grade_id IN ('E3', 'E4', 'E5')
    GROUP BY 1
)
SELECT
    x.location_class,
    IFNULL(e.voluntary_exits, 0) AS mid_career_voluntary_exits,
    x.opening_person_years,
    ROUND(IFNULL(e.voluntary_exits, 0) * 100.0 / x.opening_person_years, 2) AS avg_annual_voluntary_rate_pct
FROM exposure x
LEFT JOIN exits e ON e.location_class = x.location_class
ORDER BY avg_annual_voluntary_rate_pct DESC;
