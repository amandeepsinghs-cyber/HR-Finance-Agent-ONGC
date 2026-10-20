-- Answer Key Follow-up SQL: C1__drill_down
-- Question: Which specific disciplines in Delhi (e.g. F&A, HR, MM, Legal) have the highest concentration of E5–E7 officers past 5 years?
-- Type: data
-- Semantic audit 2026-10-20: previously returned grade x discipline rows ordered by grade, which does not
-- rank disciplines by concentration. Now one row per discipline: E5-E7 officers in Delhi HQ (WC-DEL) with
-- >=60 months continuous stay, the discipline's total current E5-E7 strength in Delhi, the concentration
-- (share past 5 years) and the share of all Delhi E5-E7 officers past 5 years; ranked by count.

WITH d AS (
    SELECT
        v.discipline_id,
        COUNT(DISTINCT v.emp_id) AS e5_e7_in_delhi,
        COUNT(DISTINCT CASE WHEN v.continuous_stay_months >= 60 THEN v.emp_id END) AS e5_e7_past_5yr,
        COUNT(DISTINCT CASE WHEN v.continuous_stay_months >= 60 AND v.grade_id = 'E5' THEN v.emp_id END) AS e5_past_5yr,
        COUNT(DISTINCT CASE WHEN v.continuous_stay_months >= 60 AND v.grade_id = 'E6' THEN v.emp_id END) AS e6_past_5yr,
        COUNT(DISTINCT CASE WHEN v.continuous_stay_months >= 60 AND v.grade_id = 'E7' THEN v.emp_id END) AS e7_past_5yr
    FROM `ongc-hr-finance-agent.hrfin_gold.v_continuous_stay` v
    WHERE v.is_current_stay = TRUE
      AND v.wc_id = 'WC-DEL'
      AND v.grade_id IN ('E5', 'E6', 'E7')
    GROUP BY v.discipline_id
)
SELECT
    d.discipline_id,
    dd.name AS discipline_name,
    d.e5_e7_past_5yr,
    d.e5_past_5yr,
    d.e6_past_5yr,
    d.e7_past_5yr,
    d.e5_e7_in_delhi,
    ROUND(d.e5_e7_past_5yr * 100.0 / NULLIF(d.e5_e7_in_delhi, 0), 1) AS pct_of_discipline_past_5yr,
    ROUND(d.e5_e7_past_5yr * 100.0 / NULLIF(SUM(d.e5_e7_past_5yr) OVER (), 0), 1) AS share_of_delhi_e5_e7_past_5yr
FROM d
JOIN dim_discipline dd ON d.discipline_id = dd.discipline_id
WHERE d.e5_e7_past_5yr > 0
ORDER BY d.e5_e7_past_5yr DESC, pct_of_discipline_past_5yr DESC;
