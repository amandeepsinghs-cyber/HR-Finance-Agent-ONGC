-- Answer Key SQL: T2
-- Question: "Who in Delhi has 5+ years?" → "Which of them breach the transfer policy?" → "Match them to vacancies at hard stations." → "Export as an Excel transfer proposal."
-- Type: chain
-- Semantic audit 2026-10-20: Old SQL truncated the list at LIMIT 100 (419 qualify); its COALESCE(exemption_tag,'Impending_Retirement') was intended to impute exemptions (silver stores the literal string 'None', so it showed 'None').
-- Semantic audit 2026-10-20: Now: all executives currently in Delhi HQ with >= 5 years continuous stay (v_continuous_stay, consistent with C1), exemption tag with 'None' mapped to NULL, and 3-year pre-retirement flag.

SELECT
    v.emp_id,
    v.grade_id,
    v.discipline_id,
    d.name AS discipline_name,
    v.continuous_from_date,
    ROUND(v.continuous_stay_months / 12.0, 1) AS delhi_years,
    v.retirement_date,
    DATE_DIFF(v.retirement_date, DATE '2026-10-19', DAY) <= 3 * 365.25 AS within_3yr_of_superannuation,
    NULLIF(p.exemption_tag, 'None') AS exemption_tag
FROM `ongc-hr-finance-agent.hrfin_gold.v_continuous_stay` v
JOIN dim_discipline d ON d.discipline_id = v.discipline_id
LEFT JOIN posting_history p ON p.emp_id = v.emp_id AND p.is_current_posting AND p.wc_id = 'WC-DEL'
WHERE v.is_current_stay AND v.wc_id = 'WC-DEL' AND v.grade_id LIKE 'E%' AND v.continuous_stay_months >= 60
ORDER BY delhi_years DESC, v.emp_id;
