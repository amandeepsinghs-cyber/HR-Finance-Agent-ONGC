-- Answer Key Follow-up SQL: H10__compare_or_so_what
-- Question: How does the proposed transfer list balance regional deficit clearance against the approved annual transfer budget?
-- Type: document
-- Semantic audit 2026-10-20: old SQL summed total_transfer_cost_inr over ALL postings since 1974 (rupees, all years) as the
-- 'budget'. No approved transfer budget exists in the data (GAP). Now by station category: executives due for FY27 rotation,
-- FY26 executive vacancies, estimated cost at the FY26 average cost per transfer (rupees -> crore) vs FY26 actual spend.
-- Rev 2 (coordinator): 'due' = continuous stay >= 60 months (v_continuous_stay, C1 rule); 3-5 yr eligible pool shown separately.
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
, fy26 AS (
    SELECT w.hard_station_cat, COUNT(*) AS fy26_transfers, SUM(p.total_transfer_cost_inr) AS fy26_spend_inr
    FROM posting_history p JOIN dim_work_centre w ON w.wc_id = p.wc_id
    WHERE p.fiscal_year = 'FY26' AND LOWER(p.posting_type) IN ('rotation', 'hard_station')
    GROUP BY 1
),
unit AS (
    SELECT SUM(fy26_spend_inr) / SUM(fy26_transfers) AS avg_cost_inr FROM fy26
),
vac AS (
    SELECT w.hard_station_cat, SUM(sp.vacancy_count) AS exec_vacancies_fy26
    FROM sanctioned_posts sp
    JOIN dim_grade g ON g.grade_id = sp.grade_id
    JOIN dim_work_centre w ON w.wc_id = sp.wc_id
    WHERE sp.fiscal_year = 'FY26' AND LOWER(g.cadre) = 'executive'
    GROUP BY 1
),
due AS (
    SELECT w.hard_station_cat, COUNTIF(f.due_for_rotation) AS due_for_rotation, COUNTIF(f.eligible_3_to_5y) AS eligible_3_to_5y
    FROM flags f JOIN dim_work_centre w ON w.wc_id = f.wc_id
    GROUP BY 1
)
SELECT
    CONCAT('Category ', d.hard_station_cat) AS station_category,
    d.due_for_rotation,
    d.eligible_3_to_5y,
    IFNULL(v.exec_vacancies_fy26, 0) AS exec_vacancies_fy26,
    ROUND(d.due_for_rotation * u.avg_cost_inr / 1e7, 2) AS est_cost_if_all_due_moved_inr_cr,
    IFNULL(f.fy26_transfers, 0) AS fy26_transfers_in,
    ROUND(IFNULL(f.fy26_spend_inr, 0) / 1e7, 2) AS fy26_spend_inr_cr,
    ROUND(u.avg_cost_inr / 1e5, 2) AS avg_cost_per_transfer_inr_lakh
FROM due d
CROSS JOIN unit u
LEFT JOIN vac v ON v.hard_station_cat = d.hard_station_cat
LEFT JOIN fy26 f ON f.hard_station_cat = d.hard_station_cat
ORDER BY station_category DESC;
