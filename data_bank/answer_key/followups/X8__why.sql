-- Answer Key Follow-up SQL: X8__why
-- Question: What procedural bottlenecks or documentation delays have prevented closure of audit paras aged over 3 years?
-- Type: data
-- Semantic audit 2026-10-20: Excludes closed paras (old SQL counted 8 closed paras as a NULL 'bottleneck'), and adds status and
-- financial implication per bottleneck.
SELECT
    bottleneck_reason,
    current_status,
    COUNT(cag_para_id) AS open_paras_over_3_years,
    ROUND(SUM(financial_implication_inr_cr), 2) AS financial_implication_cr,
    ROUND(AVG(DATE_DIFF(DATE '2026-10-19', notification_date, DAY)) / 365.25, 1) AS avg_age_years
FROM cag_paras
WHERE is_aged_over_3_years AND LOWER(current_status) != 'closed'
GROUP BY bottleneck_reason, current_status
ORDER BY open_paras_over_3_years DESC, financial_implication_cr DESC;
