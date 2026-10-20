-- Answer Key Follow-up SQL: H10__drill_down
-- Question: Which specific executives meet the criteria for transfer from Delhi/Dehradun to Assam and Tripura assets?
-- Type: document
-- Semantic audit 2026-10-20: old SQL returned a head-count per city (2 rows, all grades) - not 'specific executives'.
-- Rev 2 (coordinator): 'due' = continuous stay >= 60 months (v_continuous_stay, C1 rule), no valid exemption, not within 3 yrs of
-- superannuation; plus never served a Category C station (JRTP 6.1) and technical discipline, at New Delhi / Dehradun work centres.
WITH stay AS (
    -- current continuous stay per hrfin_gold.v_continuous_stay (same source as C1 / MET-HR-011)
    SELECT v.emp_id, v.wc_id, v.grade_id, v.discipline_id, v.retirement_date,
           v.continuous_from_date, v.continuous_stay_months,
           IF(LOWER(IFNULL(p.exemption_tag, 'none')) IN ('none', ''), NULL, p.exemption_tag) AS exemption_tag,
           p.exemption_valid_until
    FROM `ongc-hr-finance-agent.hrfin_gold.v_continuous_stay` v
    JOIN dim_grade g ON g.grade_id = v.grade_id
    JOIN employee_master e ON e.emp_id = v.emp_id
    LEFT JOIN posting_history p ON p.emp_id = v.emp_id AND p.is_current_posting
    WHERE v.is_current_stay
      AND LOWER(g.cadre) = 'executive'
      AND LOWER(e.employment_status) = 'active'
),
ever_hard AS (
    SELECT p.emp_id, LOGICAL_OR(LOWER(w.hard_station_cat) = 'c') AS served_cat_c
    FROM posting_history p JOIN dim_work_centre w ON w.wc_id = p.wc_id
    GROUP BY p.emp_id
),
rotation AS (
    -- JRTP 3.1/3.2: 3 yrs is the MINIMUM; rotation normally after 3-5 yrs -> 'due' = continuous stay >= 60 months (C1 rule).
    -- Protected: within 3 yrs of superannuation (JRTP 7.1, C1 rule: retirement_date - 2026-10-19 <= 3*365.25 days)
    -- or a recorded exemption still valid on 2026-10-19.
    SELECT s.*, IFNULL(h.served_cat_c, FALSE) AS served_cat_c,
           DATE_DIFF(s.retirement_date, DATE '2026-10-19', DAY) <= 3 * 365.25 AS retiring_3y,
           s.exemption_tag IS NOT NULL AND IFNULL(s.exemption_valid_until, DATE '9999-12-31') >= DATE '2026-10-19' AS valid_exemption,
           s.continuous_stay_months >= 60 AS stay_ge_5y,
           s.continuous_stay_months BETWEEN 36 AND 59 AS stay_3_to_5y,
           s.continuous_from_date = DATE '2020-07-01' AS censored_2020_07_01
    FROM stay s
    LEFT JOIN ever_hard h ON h.emp_id = s.emp_id
),
flags AS (
    SELECT r.*,
           r.stay_ge_5y AND NOT r.retiring_3y AND NOT r.valid_exemption AS due_for_rotation,
           r.stay_3_to_5y AND NOT r.retiring_3y AND NOT r.valid_exemption AS eligible_3_to_5y
    FROM rotation r
)
SELECT
    f.emp_id,
    e.name,
    f.grade_id,
    d.name AS discipline,
    wc.short_name AS current_work_centre,
    ROUND(f.continuous_stay_months / 12, 1) AS station_years,
    f.continuous_from_date,
    e.age_years,
    COUNT(*) OVER () AS total_candidates,
    COUNTIF(f.censored_2020_07_01) OVER () AS candidates_stay_starts_2020_07_01
FROM flags f
JOIN employee_master e ON e.emp_id = f.emp_id
JOIN dim_work_centre wc ON wc.wc_id = f.wc_id
JOIN dim_discipline d ON d.discipline_id = f.discipline_id
WHERE wc.city IN ('New Delhi', 'Dehradun')
  AND f.due_for_rotation
  AND NOT f.served_cat_c
  AND LOWER(d.function) = 'technical'
ORDER BY f.continuous_stay_months DESC, f.grade_id, f.emp_id;
