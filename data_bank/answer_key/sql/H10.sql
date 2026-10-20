-- Answer Key SQL: H10
-- Question: Generate an Excel transfer proposal for FY27 using rotation rules.
-- Type: document
-- Semantic audit 2026-10-20: old SQL counted ALL employees (incl. non-executives, exempt and age 57+) with >=36 months per WC, and
-- the legacy document prose reported the 46-row count as '{eligible_officers_count}'.
-- Semantic audit 2026-10-20 (rev 2, coordinator): 'due' redefined per JRTP 3.1/3.2 and C1/MET-HR-011 as continuous stay >= 60
-- months (hrfin_gold.v_continuous_stay) with no valid exemption and not within 3 yrs of superannuation; 3-5 yr stays shown
-- separately as eligible_3_to_5y; stays starting exactly 2020-07-01 (left-censored posting history) counted per WC.
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
, vac AS (
    SELECT sp.wc_id, SUM(sp.vacancy_count) AS exec_vacancies_fy26
    FROM sanctioned_posts sp JOIN dim_grade g ON g.grade_id = sp.grade_id
    WHERE sp.fiscal_year = 'FY26' AND LOWER(g.cadre) = 'executive'
    GROUP BY sp.wc_id
)
SELECT
    wc.short_name AS work_centre,
    wc.hard_station_cat,
    COUNT(*) AS active_executives,
    COUNTIF(f.stay_ge_5y) AS stay_ge_5y,
    COUNTIF(f.due_for_rotation) AS due_for_rotation,
    COUNTIF(f.stay_ge_5y AND f.retiring_3y) AS protected_retiring_3y,
    COUNTIF(f.stay_ge_5y AND NOT f.retiring_3y AND f.valid_exemption) AS protected_exemption_only,
    COUNTIF(f.eligible_3_to_5y) AS eligible_3_to_5y,
    COUNTIF(f.due_for_rotation AND NOT f.served_cat_c) AS due_never_served_cat_c,
    COUNTIF(f.censored_2020_07_01) AS stay_starts_2020_07_01,
    IFNULL(MAX(v.exec_vacancies_fy26), 0) AS exec_vacancies_fy26,
    SUM(COUNTIF(f.due_for_rotation)) OVER () AS company_due_for_rotation,
    SUM(COUNTIF(f.eligible_3_to_5y)) OVER () AS company_eligible_3_to_5y,
    SUM(COUNTIF(f.censored_2020_07_01)) OVER () AS company_stay_starts_2020_07_01,
    SUM(COUNTIF(f.due_for_rotation AND f.censored_2020_07_01)) OVER () AS company_due_stay_starts_2020_07_01,
    SUM(COUNT(*)) OVER () AS company_active_executives
FROM flags f
JOIN dim_work_centre wc ON wc.wc_id = f.wc_id
LEFT JOIN vac v ON v.wc_id = f.wc_id
GROUP BY wc.short_name, wc.hard_station_cat
ORDER BY wc.hard_station_cat DESC, due_for_rotation DESC, work_centre;
