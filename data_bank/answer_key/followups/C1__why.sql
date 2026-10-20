-- Answer Key Follow-up SQL: C1__why
-- Question: What are the approved administrative justifications or exemption tags recorded in SAP for those exceeding 5 years in Delhi?
-- Type: data
-- Semantic audit 2026-10-20: (1) population was posting_history rows with from_date >= 60 months ago (226+4),
-- which is not the parent's population (continuous stay >= 60 months in WC-DEL, 419 executives, from
-- hrfin_gold.v_continuous_stay); (2) COALESCE(exemption_approved_by, 'CMD') fabricated a CMD approval for
-- officers with no record. Now: the parent's 419 executives joined to their current posting's exemption
-- fields; missing values are reported as 'None recorded', and validity is checked against 2026-10-19.

SELECT
    COALESCE(NULLIF(p.exemption_tag, 'None'), 'None recorded') AS exemption_tag,
    COALESCE(NULLIF(p.exemption_reason_code, 'None'), 'None recorded') AS exemption_reason_code,
    COALESCE(NULLIF(p.exemption_approved_by, 'None'), 'None recorded') AS exemption_approved_by,
    COUNT(DISTINCT v.emp_id) AS officer_count,
    COUNT(DISTINCT CASE WHEN p.exemption_valid_until >= DATE '2026-10-19' THEN v.emp_id END) AS valid_as_of_2026_10_19,
    COUNT(DISTINCT CASE WHEN DATE_DIFF(v.retirement_date, DATE '2026-10-19', DAY) <= 3 * 365.25 THEN v.emp_id END) AS retiring_within_3yr,
    ROUND(COUNT(DISTINCT v.emp_id) * 100.0 / SUM(COUNT(DISTINCT v.emp_id)) OVER (), 1) AS pct_of_delhi_5yr_plus
FROM `ongc-hr-finance-agent.hrfin_gold.v_continuous_stay` v
LEFT JOIN posting_history p
    ON p.emp_id = v.emp_id
   AND p.is_current_posting = TRUE
WHERE v.is_current_stay = TRUE
  AND v.wc_id = 'WC-DEL'
  AND v.grade_id LIKE 'E%'
  AND v.continuous_stay_months >= 60
GROUP BY 1, 2, 3
ORDER BY officer_count DESC;
